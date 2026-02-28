"""
GroqAdapter for live LLM calls using Groq's API.

Uses Llama 3.3 70B for high-quality tool calling and JSON output.
API key must be provided via GROQ_API_KEY environment variable.

Author: Victor Rowello
Sprint: 7
"""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
import logging
import uuid

from src.adapters.base import BaseAdapter, AdapterResponse

logger = logging.getLogger(__name__)


class GroqAdapter:
    """
    LLM adapter using Groq's API for fast inference.
    
    Features:
    - Uses Llama 3.3 70B by default (excellent tool calling)
    - Fast inference via Groq's optimized infrastructure
    - JSON mode for structured outputs
    - API key from environment variable only (never hardcoded)
    """
    
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(
        self,
        adapter_id: str = "groq",
        version: str = "1.0",
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: float = 30.0,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Groq adapter.
        
        Args:
            adapter_id: Identifier for this adapter
            version: Adapter version
            model: Model to use (default: llama-3.3-70b-versatile)
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
            config: Optional config dict (for registry compatibility)
        """
        self.adapter_id = adapter_id
        self.version = version
        
        # Config can override individual parameters
        config = config or {}
        self.model = model or config.get("model") or self.DEFAULT_MODEL
        self.temperature = config.get("temperature", temperature)
        self.max_tokens = config.get("max_tokens", max_tokens)
        self.timeout = config.get("timeout", timeout)
        self._api_key: Optional[str] = config.get("api_key")
    
    def _get_api_key(self) -> str:
        """
        Get API key from environment variable.
        
        Raises:
            ValueError: If GROQ_API_KEY is not set
        """
        if self._api_key is None:
            self._api_key = os.environ.get("GROQ_API_KEY")
            if not self._api_key:
                raise ValueError(
                    "GROQ_API_KEY environment variable is not set. "
                    "Please set it before using the Groq adapter: "
                    "$env:GROQ_API_KEY = 'your-key-here'"
                )
        return self._api_key
    
    def generate(
        self,
        prompt_template_id: str,
        prompt: str,
        **kwargs
    ) -> AdapterResponse:
        """
        Generate a response from Groq's API.
        
        Args:
            prompt_template_id: Identifier for the prompt template being used
            prompt: User prompt
            **kwargs: Additional parameters:
                - system_message: Optional system prompt
                - json_mode: Whether to request JSON output (default: True)
                - model: Override default model
                - temperature: Override default temperature
            
        Returns:
            AdapterResponse with parsed content and provenance
        """
        request_id = str(uuid.uuid4())
        
        # Extract kwargs
        system_message = kwargs.get("system_message")
        json_mode = kwargs.get("json_mode", True)
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)
        
        # Build messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Build request body
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        
        # Add JSON mode if requested
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        
        try:
            api_key = self._get_api_key()
            
            # Make request
            request = urllib.request.Request(
                self.API_URL,
                data=json.dumps(body).encode('utf-8'),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Witty/1.0 (Python urllib)"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            # Extract response content
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            
            # Try to parse as JSON if json_mode was enabled
            parsed_json = None
            parse_error = None
            if json_mode:
                try:
                    parsed_json = json.loads(content)
                except json.JSONDecodeError as e:
                    parse_error = str(e)
                    logger.warning(f"Groq response was not valid JSON: {e}")
            
            return AdapterResponse(
                text=content,
                parsed_json=parsed_json,
                tokens=total_tokens,
                model_metadata={
                    "model": model,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": total_tokens,
                    "parse_error": parse_error
                },
                adapter_provenance={
                    "adapter_id": self.adapter_id,
                    "adapter_version": self.version,
                    "model": model,
                    "request_id": request_id,
                    "prompt_template_id": prompt_template_id,
                    "temperature": temperature,
                    "json_mode": json_mode
                }
            )
            
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
            logger.error(f"Groq API HTTP error {e.code}: {error_body}")
            
            return AdapterResponse(
                text="",
                parsed_json=None,
                tokens=0,
                model_metadata={
                    "error": f"HTTP {e.code}",
                    "error_details": error_body[:500] if error_body else None
                },
                adapter_provenance={
                    "adapter_id": self.adapter_id,
                    "adapter_version": self.version,
                    "model": model,
                    "request_id": request_id,
                    "prompt_template_id": prompt_template_id,
                    "error": f"HTTP {e.code}"
                }
            )
            
        except urllib.error.URLError as e:
            logger.error(f"Groq API URL error: {e.reason}")
            return AdapterResponse(
                text="",
                parsed_json=None,
                tokens=0,
                model_metadata={"error": f"URL error: {e.reason}"},
                adapter_provenance={
                    "adapter_id": self.adapter_id,
                    "adapter_version": self.version,
                    "model": model,
                    "request_id": request_id,
                    "prompt_template_id": prompt_template_id,
                    "error": f"URL error: {e.reason}"
                }
            )
            
        except ValueError as e:
            # API key not set
            logger.error(f"Groq adapter configuration error: {e}")
            return AdapterResponse(
                text="",
                parsed_json=None,
                tokens=0,
                model_metadata={"error": str(e)},
                adapter_provenance={
                    "adapter_id": self.adapter_id,
                    "adapter_version": self.version,
                    "model": model,
                    "request_id": request_id,
                    "prompt_template_id": prompt_template_id,
                    "error": str(e)
                }
            )
            
        except Exception as e:
            logger.error(f"Groq API unexpected error: {e}")
            return AdapterResponse(
                text="",
                parsed_json=None,
                tokens=0,
                model_metadata={"error": str(e)},
                adapter_provenance={
                    "adapter_id": self.adapter_id,
                    "adapter_version": self.version,
                    "model": model,
                    "request_id": request_id,
                    "prompt_template_id": prompt_template_id,
                    "error": str(e)
                }
            )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return metadata about this adapter's configuration."""
        return {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "api_url": self.API_URL
        }


def get_groq_adapter(**kwargs) -> GroqAdapter:
    """
    Factory function to get a Groq adapter.
    
    Args:
        **kwargs: Arguments passed to GroqAdapter constructor
        
    Returns:
        Configured GroqAdapter instance
    """
    return GroqAdapter(**kwargs)
