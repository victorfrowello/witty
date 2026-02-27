"""
Adapter registry and resolution for the Witty pipeline.

Provides a centralized registry for discovering and instantiating adapter
implementations. This module acts as a factory for adapters, allowing the
pipeline to obtain adapter instances by name without tight coupling to
specific implementations.

The registry pattern enables:
- Easy addition of new adapters without modifying pipeline code
- Configuration-driven adapter selection
- Testing with mock adapters
- Future support for dynamic adapter loading

Currently supported adapters:
- 'mock': Deterministic mock adapter for testing
- 'openai': OpenAI-compatible adapter (works with OpenAI, Groq, Together AI, etc.)

Author: Victor Rowello
Sprint: 4
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from .mock import MockLLMAdapter
from .openai import OpenAICompatibleAdapter


# Type alias for adapter instances
AdapterType = Union[MockLLMAdapter, OpenAICompatibleAdapter]


# Global registry mapping adapter names to their implementation classes
# Extend this dictionary to add new adapter types
_REGISTRY: Dict[str, type] = {
    "mock": MockLLMAdapter,
    "openai": OpenAICompatibleAdapter,
    # Aliases for common OpenAI-compatible providers
    "groq": OpenAICompatibleAdapter,
    "together": OpenAICompatibleAdapter,
    "azure": OpenAICompatibleAdapter,
}


# Default configurations for specific providers
_PROVIDER_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-70b-versatile",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.1-70B-Instruct-Turbo",
    },
    "azure": {
        # Azure requires api_version and azure_endpoint in config
        "api_version": "2024-02-15-preview",
    },
}


def get_adapter(
    adapter_name: str = "mock",
    config: Optional[Dict[str, Any]] = None
) -> AdapterType:
    """
    Retrieve an adapter instance by name.
    
    Factory function that instantiates the appropriate adapter class based on
    the provided name. Configuration is passed through to the adapter's
    constructor. For known providers (groq, together), default configurations
    are merged with user-provided config.
    
    Args:
        adapter_name: Name of the adapter to instantiate (e.g., 'mock', 'openai',
                     'groq', 'together')
        config: Optional configuration dictionary for adapter initialization.
               May include API keys, model names, timeout settings, etc.
    
    Returns:
        An initialized adapter instance conforming to the BaseAdapter protocol
        
    Raises:
        KeyError: If the requested adapter name is not registered
        
    Example:
        >>> # Use mock adapter for testing
        >>> adapter = get_adapter("mock")
        >>> response = adapter.generate("concise_v1", "Test prompt")
        
        >>> # Use Groq with automatic defaults
        >>> adapter = get_adapter("groq", {"api_key": "your-key"})
        
        >>> # Use OpenAI with custom model
        >>> adapter = get_adapter("openai", {"model": "gpt-4o"})
    """
    config = config or {}
    
    # Look up the adapter class in the registry
    adapter_cls = _REGISTRY.get(adapter_name)
    if adapter_cls is None:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(
            f"Unknown adapter: '{adapter_name}'. "
            f"Available adapters: {available}"
        )
    
    # Merge provider defaults with user config (user config takes precedence)
    if adapter_name in _PROVIDER_DEFAULTS:
        merged_config = {**_PROVIDER_DEFAULTS[adapter_name], **config}
    else:
        merged_config = config
    
    # Extract version from config or use default
    version = merged_config.get("version", "0.1")
    
    # Instantiate and return the adapter
    return adapter_cls(
        adapter_id=adapter_name,
        version=version,
        config=merged_config
    )


def list_adapters() -> Dict[str, str]:
    """
    List all registered adapter names and their types.
    
    Returns:
        Dictionary mapping adapter names to their class names
    """
    return {name: cls.__name__ for name, cls in _REGISTRY.items()}


def register_adapter(name: str, adapter_cls: type) -> None:
    """
    Register a new adapter class.
    
    Allows dynamic registration of additional adapters at runtime.
    
    Args:
        name: Name to register the adapter under
        adapter_cls: The adapter class to register
    """
    _REGISTRY[name] = adapter_cls
