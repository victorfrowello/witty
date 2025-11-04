"""Adapter base types and contracts.

This module defines the AdapterResponse model and the BaseAdapter protocol
that concrete adapters should implement. Adapters isolate network/auth
behavior and present a stable interface to the pipeline.

Keep implementations lightweight for the mock adapter used in CI.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol
from pydantic import BaseModel, Field


class AdapterResponse(BaseModel):
    """Standardized response returned by adapters.

    Fields:
    - text: raw textual output from model/adapter
    - parsed_json: optional parsed JSON object if adapter was able to parse
    - tokens: optional token count metadata
    - model_metadata: provider-specific metadata (model name, latency, etc.)
    - adapter_provenance: structured provenance about the adapter call
    """

    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    tokens: Optional[int] = None
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    adapter_provenance: Dict[str, Any] = Field(default_factory=dict)


class BaseAdapter(Protocol):
    """Contract for adapter implementations.

    Implementations must provide `generate()` and `get_metadata()` methods.
    `stream_generate()` is optional and may be omitted by simple adapters.
    """

    adapter_id: str
    version: str

    def __init__(self, adapter_id: str, version: str, config: Dict[str, Any]):
        ...

    def generate(self, prompt_template_id: str, prompt: str, **kwargs) -> AdapterResponse:
        ...

    def get_metadata(self) -> Dict[str, Any]:
        ...
