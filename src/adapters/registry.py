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
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .mock import MockLLMAdapter


# Global registry mapping adapter names to their implementation classes
# Extend this dictionary to add new adapter types
_REGISTRY: Dict[str, type] = {
    "mock": MockLLMAdapter,
    # Future adapters can be added here:
    # "openai": OpenAIAdapter,
    # "anthropic": AnthropicAdapter,
    # etc.
}


def get_adapter(
    adapter_name: str = "mock",
    config: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Retrieve an adapter instance by name.
    
    Factory function that instantiates the appropriate adapter class based on
    the provided name. Configuration is passed through to the adapter's
    constructor.
    
    Args:
        adapter_name: Name of the adapter to instantiate (e.g., 'mock', 'openai')
        config: Optional configuration dictionary for adapter initialization.
               May include API keys, model names, timeout settings, etc.
    
    Returns:
        An initialized adapter instance conforming to the BaseAdapter protocol
        
    Raises:
        KeyError: If the requested adapter name is not registered
        
    Example:
        >>> adapter = get_adapter("mock", {"version": "0.2"})
        >>> response = adapter.generate("concise_v1", "Test prompt")
    """
    config = config or {}
    
    # Look up the adapter class in the registry
    adapter_cls = _REGISTRY.get(adapter_name)
    if adapter_cls is None:
        available = ", ".join(_REGISTRY.keys())
        raise KeyError(
            f"Unknown adapter: '{adapter_name}'. "
            f"Available adapters: {available}"
        )
    
    # Extract version from config or use default
    version = config.get("version", "0.1")
    
    # Instantiate and return the adapter
    return adapter_cls(
        adapter_id=adapter_name,
        version=version,
        config=config
    )
