"""Mock adapter implementation for deterministic CI and unit tests.

This adapter returns canned, deterministic AdapterResponse objects so that
the pipeline can be exercised without live model keys. It is intentionally
simple and well-documented to make tests easy to reason about.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from .base import AdapterResponse, BaseAdapter


class MockLLMAdapter:
    """A small deterministic adapter used for tests and CI.

    Behavior:
    - If the prompt_template_id is provided and matches known templates the
      adapter returns a simple parsed_json object useful for unit tests.
    - Otherwise it returns a text string prefixed with 'MOCK:' and no parsed_json.

    The adapter also populates `adapter_provenance` with a deterministic
    request id (SHA256 of the prompt and template id) to simulate real
    adapter metadata.
    """

    def __init__(self, adapter_id: str = "mock", version: str = "0.1", config: Optional[Dict[str, Any]] = None):
        self.adapter_id = adapter_id
        self.version = version
        self.config = config or {}

    def _make_request_id(self, prompt_template_id: str, prompt: str) -> str:
        key = f"{self.adapter_id}:{self.version}:{prompt_template_id}:{prompt}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

    def generate(self, prompt_template_id: str, prompt: str, **kwargs) -> AdapterResponse:
        request_id = self._make_request_id(prompt_template_id or "", prompt or "")

        # Example deterministic parsed JSON for commonly used prompt ids
        if prompt_template_id and prompt_template_id.startswith("concise"):
            parsed = {
                "canonical_text": "mock canonical",
                "atomic_candidates": [{"text": "mock claim", "origin_spans": [[0, 10]]}],
                "confidence": 0.95,
            }
            text = json.dumps(parsed)
        elif prompt_template_id and prompt_template_id.startswith("symbolize"):
            parsed = {"legend": {"P1": "mock claim"}, "logical_form_candidates": []}
            text = json.dumps(parsed)
        else:
            parsed = None
            text = f"MOCK: {prompt}"

        adapter_provenance = {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "prompt_template_id": prompt_template_id,
            "request_id": request_id,
            "raw_output_summary": (text[:200] + "...") if len(text) > 200 else text,
        }

        return AdapterResponse(
            text=text,
            parsed_json=parsed,
            tokens=len(text.split()) if text else None,
            model_metadata={"mock": True},
            adapter_provenance=adapter_provenance,
        )

    def get_metadata(self) -> Dict[str, Any]:
        return {"adapter_id": self.adapter_id, "version": self.version}
