"""Tests for the MockLLMAdapter to ensure deterministic behavior."""

from src.adapters.registry import get_adapter


def test_mock_adapter_returns_parsed_json_for_concise_template():
    adapter = get_adapter("mock")
    resp = adapter.generate("concise_v1", "Some example input")

    assert resp.adapter_provenance.get("adapter_id") == "mock"
    assert resp.adapter_provenance.get("request_id") is not None
    assert resp.parsed_json is not None
    assert "canonical_text" in resp.parsed_json


def test_mock_adapter_returns_text_for_unknown_template():
    adapter = get_adapter("mock")
    resp = adapter.generate("unknown_template", "Some example input")

    assert resp.parsed_json is None
    assert resp.text.startswith("MOCK:")
