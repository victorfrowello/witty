"""Tests for the MockLLMAdapter to ensure deterministic behavior."""

from src.adapters.registry import get_adapter
from src.adapters.base import AdapterResponse


def test_mock_adapter_returns_parsed_json_for_concise_template():
    adapter = get_adapter("mock")
    resp = adapter.generate("concise_v1", "Some example input")

    assert resp.adapter_provenance.get("adapter_id") == "mock"
    assert resp.adapter_provenance.get("request_id") is not None
    assert resp.parsed_json is not None
    assert "canonical_text" in resp.parsed_json
    assert "atomic_candidates" in resp.parsed_json
    assert "confidence" in resp.parsed_json
    assert isinstance(resp.parsed_json["atomic_candidates"], list)


def test_mock_adapter_returns_text_for_unknown_template():
    adapter = get_adapter("mock")
    resp = adapter.generate("unknown_template", "Some example input")

    assert resp.parsed_json is None
    assert resp.text.startswith("MOCK:")


def test_mock_adapter_request_id_is_deterministic():
    """Test that the same input produces the same request_id"""
    adapter = get_adapter("mock")
    
    resp1 = adapter.generate("test_template", "test input")
    resp2 = adapter.generate("test_template", "test input")
    
    assert resp1.adapter_provenance["request_id"] == resp2.adapter_provenance["request_id"]
    
    # Different input should produce different request_id
    resp3 = adapter.generate("test_template", "different input")
    assert resp1.adapter_provenance["request_id"] != resp3.adapter_provenance["request_id"]


def test_mock_adapter_response_validation():
    """Test that adapter responses conform to AdapterResponse schema"""
    adapter = get_adapter("mock")
    resp = adapter.generate("concise_v1", "test input")
    
    # Verify it's a valid AdapterResponse
    assert isinstance(resp, AdapterResponse)
    assert resp.text is not None
    assert isinstance(resp.adapter_provenance, dict)
    assert "adapter_id" in resp.adapter_provenance
    assert "version" in resp.adapter_provenance
    assert "request_id" in resp.adapter_provenance
    assert "raw_output_summary" in resp.adapter_provenance


def test_mock_adapter_registry():
    """Test adapter registry functionality"""
    # Test getting adapter with default config
    adapter1 = get_adapter("mock")
    assert adapter1.adapter_id == "mock"
    assert adapter1.version == "0.1"

    # Test getting adapter with custom config
    adapter2 = get_adapter("mock", {"version": "0.2"})
    assert adapter2.version == "0.2"

    # Test invalid adapter name
    try:
        get_adapter("nonexistent")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass
