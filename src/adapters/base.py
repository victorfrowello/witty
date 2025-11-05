"""
Adapter base types and contracts for the Witty pipeline.

This module defines the standardized interface for LLM adapters, which isolate
network communication, authentication, and model-specific behavior from the
core pipeline logic. All adapters must conform to the BaseAdapter protocol.

Key components:
- AdapterResponse: Standardized response format from all adapters
- BaseAdapter: Protocol defining the adapter interface contract
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol
from pydantic import BaseModel, Field


class AdapterResponse(BaseModel):
    """
    Standardized response structure returned by all adapters.
    
    Provides a consistent interface for pipeline modules to consume LLM outputs
    regardless of the underlying model provider or implementation.
    
    Attributes:
        text: Raw textual output from the model
        parsed_json: Optional structured JSON if the adapter successfully parsed
                     the response (None if parsing failed or wasn't attempted)
        tokens: Optional token count for usage tracking and billing
        model_metadata: Provider-specific metadata (model name, version, latency,
                       temperature, etc.) for debugging and provenance
        adapter_provenance: Structured provenance information about this adapter
                           call including request ID, timestamp, parameters used
    """
    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    tokens: Optional[int] = None
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    adapter_provenance: Dict[str, Any] = Field(default_factory=dict)


class BaseAdapter(Protocol):
    """
    Protocol defining the contract for all adapter implementations.
    
    Adapters must implement these methods to integrate with the pipeline.
    The protocol allows for type checking without requiring inheritance.
    
    Required Attributes:
        adapter_id: Unique identifier for this adapter (e.g., 'openai', 'mock')
        version: Semantic version string for the adapter implementation
    
    Required Methods:
        __init__: Initialize adapter with ID, version, and configuration
        generate: Generate a response given a prompt and template ID
        get_metadata: Return metadata about the adapter's configuration
    
    Optional Methods:
        stream_generate: Stream responses for long-running generations
                        (can be omitted by simple adapters)
    """

    adapter_id: str
    version: str

    def __init__(self, adapter_id: str, version: str, config: Dict[str, Any]) -> None:
        """
        Initialize the adapter with configuration.
        
        Args:
            adapter_id: Unique identifier for this adapter instance
            version: Semantic version of the adapter implementation
            config: Configuration dictionary with adapter-specific settings
        """
        ...

    def generate(
        self,
        prompt_template_id: str,
        prompt: str,
        **kwargs: Any
    ) -> AdapterResponse:
        """
        Generate a response from the model.
        
        Args:
            prompt_template_id: Identifier for the prompt template being used
                               (enables adapter-specific optimizations)
            prompt: The actual prompt text to send to the model
            **kwargs: Additional adapter-specific parameters (temperature,
                     max_tokens, etc.)
        
        Returns:
            AdapterResponse containing the model's output and metadata
            
        Raises:
            Exception: On network errors, authentication failures, or
                      model-specific errors
        """
        ...

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about this adapter's configuration.
        
        Useful for debugging, provenance tracking, and logging.
        
        Returns:
            Dictionary containing adapter metadata (ID, version, provider,
            model name, configuration parameters, etc.)
        """
        ...

