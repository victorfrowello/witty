"""
Mock adapter implementation for deterministic testing and CI.

Provides a lightweight, deterministic LLM adapter that returns canned responses
without making any network calls. This enables reliable unit testing, CI/CD
pipelines, and reproducible demonstrations without requiring API keys or
network connectivity.

The mock adapter recognizes common prompt template IDs and returns appropriate
structured responses that match the expected format for each pipeline stage.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from .base import AdapterResponse


class MockLLMAdapter:
    """
    Deterministic mock adapter for testing and reproducible pipelines.
    
    Returns pre-defined responses based on prompt template IDs, enabling
    predictable testing without live model calls. All outputs are deterministic
    and suitable for CI environments.
    
    Behavior:
    - Recognizes known prompt template IDs (concise_v1, symbolize_v1, etc.)
      and returns appropriate parsed JSON responses
    - For unknown templates, returns simple text responses prefixed with 'MOCK:'
    - Generates deterministic request IDs based on SHA256 hash of inputs
    - Populates full adapter_provenance for testing provenance tracking
    
    Attributes:
        adapter_id: Identifier for this adapter (default: 'mock')
        version: Version string for this adapter implementation
        config: Optional configuration dictionary (unused in mock but kept
               for interface compatibility)
    """

    def __init__(
        self,
        adapter_id: str = "mock",
        version: str = "0.1",
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the mock adapter.
        
        Args:
            adapter_id: Unique identifier for this adapter instance
            version: Semantic version of the adapter
            config: Optional configuration (unused but kept for compatibility)
        """
        self.adapter_id = adapter_id
        self.version = version
        self.config = config or {}

    def _make_request_id(self, prompt_template_id: str, prompt: str) -> str:
        """
        Generate a deterministic request ID based on inputs.
        
        Creates a reproducible hash-based ID that will be identical for the
        same inputs, enabling deterministic testing and comparison.
        
        Args:
            prompt_template_id: Template identifier used in the request
            prompt: The actual prompt text
            
        Returns:
            Truncated SHA256 hash as a 12-character hex string
        """
        # Combine all inputs to create a unique but deterministic key
        key = f"{self.adapter_id}:{self.version}:{prompt_template_id}:{prompt}"
        hash_digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return hash_digest[:12]  # Use first 12 characters for brevity

    def generate(
        self,
        prompt_template_id: str,
        prompt: str,
        **kwargs: Any
    ) -> AdapterResponse:
        """
        Generate a mock response based on the prompt template ID.
        
        Returns deterministic, template-specific responses suitable for testing
        each stage of the pipeline. The responses are crafted to match the
        expected structure for each template type.
        
        Args:
            prompt_template_id: Identifier for the prompt template (e.g.,
                               'concise_v1', 'symbolize_v1')
            prompt: The prompt text (used for deterministic hashing)
            **kwargs: Additional parameters (ignored in mock implementation)
            
        Returns:
            AdapterResponse with appropriate parsed_json for known templates,
            or simple text response for unknown templates
        """
        # Generate deterministic request ID for provenance tracking
        request_id = self._make_request_id(prompt_template_id or "", prompt or "")

        # Return template-specific mock responses for known templates
        parsed_json: Optional[Dict[str, Any]] = None
        text: str
        
        if prompt_template_id and prompt_template_id.startswith("concise"):
            # Mock response for concision stage
            parsed_json = {
                "canonical_text": "mock canonical",
                "atomic_candidates": [
                    {
                        "text": "mock claim",
                        "origin_spans": [[0, 10]]
                    }
                ],
                "confidence": 0.95,
            }
            text = json.dumps(parsed_json)
            
        elif prompt_template_id and prompt_template_id.startswith("symbolize"):
            # Mock response for symbolization stage
            parsed_json = {
                "legend": {"P1": "mock claim"},
                "logical_form_candidates": []
            }
            text = json.dumps(parsed_json)
            
        else:
            # Generic mock response for unknown templates
            parsed_json = None
            text = f"MOCK: {prompt}"

        # Build comprehensive adapter provenance for testing
        adapter_provenance = {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "prompt_template_id": prompt_template_id,
            "request_id": request_id,
            "raw_output_summary": (
                (text[:200] + "...") if len(text) > 200 else text
            ),
        }

        return AdapterResponse(
            text=text,
            parsed_json=parsed_json,
            tokens=len(text.split()) if text else None,
            model_metadata={"mock": True},
            adapter_provenance=adapter_provenance,
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about this mock adapter instance.
        
        Returns:
            Dictionary containing adapter ID and version
        """
        return {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "is_mock": True,
        }
