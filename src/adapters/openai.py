"""
OpenAI-compatible adapter for the Witty pipeline.

This module provides a production-ready adapter for OpenAI API and compatible
services (OpenAI, Azure OpenAI, Groq, Together AI, etc.). It implements the
BaseAdapter protocol with retry logic, structured JSON extraction, and
comprehensive provenance tracking.

Key Features:
- Provider-agnostic: Works with any OpenAI-compatible API by changing base_url
- Structured JSON extraction with fallback parsing
- Exponential backoff retry with configurable attempts
- Full provenance tracking for debugging and auditing
- Token usage tracking
- Async-ready design (sync wrappers for current interface)

Configuration:
- OPENAI_API_KEY: Environment variable for API key (or pass in config)
- OPENAI_BASE_URL: Optional base URL for API-compatible services

Example usage with Groq:
    adapter = OpenAICompatibleAdapter(
        adapter_id="groq",
        version="0.1",
        config={
            "api_key": "your-groq-key",
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.1-70b-versatile"
        }
    )

Author: Victor Rowello
Sprint: 4
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import AdapterResponse


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_retries: int = Field(default=3, ge=0, le=10)
    base_delay: float = Field(default=1.0, ge=0.1, le=30.0)
    max_delay: float = Field(default=30.0, ge=1.0, le=120.0)
    exponential_base: float = Field(default=2.0, ge=1.5, le=4.0)


class OpenAICompatibleAdapter:
    """
    Production adapter for OpenAI API and compatible services.
    
    This adapter provides a unified interface for interacting with OpenAI-style
    APIs, including OpenAI, Azure OpenAI, Groq, Together AI, and other compatible
    services. It handles authentication, request formatting, response parsing,
    retry logic, and provenance tracking.
    
    Attributes:
        adapter_id: Unique identifier for this adapter instance
        version: Semantic version of this adapter implementation
        config: Configuration dictionary with API settings
        client: Lazy-initialized OpenAI client instance
        
    Configuration keys:
        api_key: API key (falls back to OPENAI_API_KEY env var)
        base_url: API base URL (optional, for Groq/Together/etc.)
        model: Default model name (default: gpt-4o-mini)
        temperature: Sampling temperature (default: 0.0 for determinism)
        max_tokens: Maximum response tokens (default: 2048)
        timeout: Request timeout in seconds (default: 60)
        retry: RetryConfig for retry behavior
    """

    def __init__(
        self,
        adapter_id: str = "openai",
        version: str = "0.1",
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the OpenAI-compatible adapter.
        
        Args:
            adapter_id: Unique identifier for this adapter instance
            version: Semantic version of the adapter
            config: Configuration dictionary with API settings
        """
        self.adapter_id = adapter_id
        self.version = version
        self.config = config or {}
        self._client: Optional[Any] = None
        
        # Extract and validate configuration with defaults
        self._api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self._base_url = self.config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        self._model = self.config.get("model", "gpt-4o-mini")
        self._temperature = self.config.get("temperature", 0.0)
        self._max_tokens = self.config.get("max_tokens", 2048)
        self._timeout = self.config.get("timeout", 60)
        
        # Retry configuration
        retry_config = self.config.get("retry", {})
        self._retry = RetryConfig(**retry_config) if isinstance(retry_config, dict) else retry_config

    @property
    def client(self) -> Any:
        """
        Lazily initialize and return the OpenAI client.
        
        Delays client creation until first use to allow configuration
        validation and avoid import errors when openai is not installed.
        
        Returns:
            Initialized OpenAI client
            
        Raises:
            ImportError: If the openai package is not installed
            ValueError: If no API key is configured
        """
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "The 'openai' package is required for OpenAICompatibleAdapter. "
                    "Install it with: pip install openai"
                )
            
            if not self._api_key:
                raise ValueError(
                    "No API key configured. Set OPENAI_API_KEY environment variable "
                    "or pass 'api_key' in config."
                )
            
            client_kwargs: Dict[str, Any] = {
                "api_key": self._api_key,
                "timeout": self._timeout,
            }
            if self._base_url:
                client_kwargs["base_url"] = self._base_url
                
            self._client = OpenAI(**client_kwargs)
        
        return self._client

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from model response text.
        
        Attempts multiple strategies to parse JSON from the response:
        1. Direct JSON parsing of entire text
        2. Extract from markdown code blocks (```json ... ```)
        3. Find first JSON object in text using bracket matching
        
        Args:
            text: Raw response text from the model
            
        Returns:
            Parsed JSON dictionary, or None if parsing fails
        """
        # Strategy 1: Try direct parsing
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code block
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(code_block_pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
        
        # Strategy 3: Find first JSON object by bracket matching
        start_idx = text.find('{')
        if start_idx >= 0:
            depth = 0
            in_string = False
            escape_next = False
            for i, char in enumerate(text[start_idx:], start=start_idx):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start_idx:i + 1])
                            except json.JSONDecodeError:
                                break
        
        return None

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay for retries.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds before next retry
        """
        delay = self._retry.base_delay * (self._retry.exponential_base ** attempt)
        return min(delay, self._retry.max_delay)

    def generate(
        self,
        prompt_template_id: str,
        prompt: str,
        **kwargs: Any
    ) -> AdapterResponse:
        """
        Generate a response from the model with retry logic.
        
        Sends the prompt to the configured OpenAI-compatible API and returns
        a standardized AdapterResponse with parsed JSON (if available),
        token counts, and comprehensive provenance.
        
        Args:
            prompt_template_id: Identifier for the prompt template being used
            prompt: The actual prompt text to send
            **kwargs: Override parameters:
                - model: Override default model
                - temperature: Override default temperature
                - max_tokens: Override default max_tokens
                - system_message: Optional system message to prepend
                
        Returns:
            AdapterResponse with model output and metadata
            
        Raises:
            Exception: If all retries fail
        """
        request_id = str(uuid.uuid4())[:12]
        start_time = datetime.now(timezone.utc)
        
        # Build messages
        messages: List[Dict[str, str]] = []
        if system_message := kwargs.get("system_message"):
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Merge parameters with kwargs overrides
        model = kwargs.get("model", self._model)
        temperature = kwargs.get("temperature", self._temperature)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        
        last_error: Optional[Exception] = None
        attempts_made = 0
        
        for attempt in range(self._retry.max_retries + 1):
            attempts_made = attempt + 1
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                # Extract response content
                text = response.choices[0].message.content or ""
                parsed_json = self._extract_json(text)
                
                # Calculate tokens
                tokens = None
                if response.usage:
                    tokens = response.usage.total_tokens
                
                # Build provenance
                end_time = datetime.now(timezone.utc)
                adapter_provenance = {
                    "adapter_id": self.adapter_id,
                    "version": self.version,
                    "prompt_template_id": prompt_template_id,
                    "request_id": request_id,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "attempts": attempts_made,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "latency_ms": int((end_time - start_time).total_seconds() * 1000),
                    "raw_output_summary": (text[:200] + "...") if len(text) > 200 else text,
                }
                
                model_metadata = {
                    "model": model,
                    "provider": self._base_url or "openai",
                    "finish_reason": response.choices[0].finish_reason,
                    "response_id": response.id,
                }
                if response.usage:
                    model_metadata["usage"] = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                
                return AdapterResponse(
                    text=text,
                    parsed_json=parsed_json,
                    tokens=tokens,
                    model_metadata=model_metadata,
                    adapter_provenance=adapter_provenance,
                )
                
            except Exception as e:
                last_error = e
                if attempt < self._retry.max_retries:
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
        
        # All retries exhausted - raise the last error
        end_time = datetime.now(timezone.utc)
        error_msg = f"All {attempts_made} attempts failed. Last error: {last_error}"
        raise RuntimeError(error_msg) from last_error

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about this adapter instance.
        
        Returns:
            Dictionary containing adapter configuration and capabilities
        """
        return {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "model": self._model,
            "base_url": self._base_url,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "retry_config": self._retry.model_dump(),
            "is_mock": False,
        }
