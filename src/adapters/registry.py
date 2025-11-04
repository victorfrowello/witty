"""Adapter registry and resolution helpers.

This module provides a simple registry used by the orchestrator to obtain
an adapter instance by name or config. It is intentionally small — as
more adapters are added this can be extended to support dynamic loading.
"""

from __future__ import annotations

from typing import Dict, Any

from .mock import MockLLMAdapter


_REGISTRY = {
    "mock": MockLLMAdapter,
}


def get_adapter(adapter_name: str = "mock", config: Dict[str, Any] | None = None):
    """Return an adapter instance for the given adapter_name.

    Raises KeyError if the adapter is not registered.
    """
    config = config or {}
    adapter_cls = _REGISTRY.get(adapter_name)
    if adapter_cls is None:
        raise KeyError(f"Unknown adapter: {adapter_name}")
    return adapter_cls(adapter_id=adapter_name, version=config.get("version", "0.1"), config=config)
