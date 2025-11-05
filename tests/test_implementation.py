"""Fixed integration tests to match current adapter and types implementations."""

import pytest
from datetime import datetime, timezone
from src.witty.types import ModuleStage, ProvenanceRecord, ModuleResult
from src.adapters.mock import MockLLMAdapter
from src.adapters.base import AdapterResponse


def test_module_stage_enum_completeness():
    """Verify ModuleStage enum contains all required pipeline stages."""
    stages = set(ModuleStage)
    required_stages = {
        ModuleStage.PREPROCESSING,
        ModuleStage.CONCISION,
        ModuleStage.ENRICHMENT,
        ModuleStage.MODALITY,
        ModuleStage.WORLD,
        ModuleStage.SYMBOLIZATION,
        ModuleStage.CNF,
        ModuleStage.VALIDATION,
    }
    assert required_stages.issubset(stages), "Missing required pipeline stages"


def test_provenance_record_required_fields():
    record = ProvenanceRecord(
        id="test-001",
        created_at=datetime.now(timezone.utc),
        module_id="concision",
        module_version="0.1",
        adapter_id="mock",
        prompt_template_id="concise_v1",
        confidence=0.95,
    )

    assert isinstance(record.id, str)
    assert isinstance(record.created_at, datetime)
    assert isinstance(record.module_id, str)
    assert isinstance(record.confidence, float)
    assert 0 <= record.confidence <= 1.0


def test_mock_adapter_protocol_compliance():
    """Verify MockLLMAdapter exposes required attributes/methods.

    BaseAdapter is a typing.Protocol and not runtime-checkable; avoid
    isinstance checks and verify the presence of required members instead.
    """
    adapter = MockLLMAdapter()

    # Check basic attributes
    assert hasattr(adapter, "adapter_id")
    assert hasattr(adapter, "version")
    assert adapter.adapter_id == "mock"

    # Check required methods exist and are callable
    assert hasattr(adapter, "generate") and callable(adapter.generate)
    assert hasattr(adapter, "get_metadata") and callable(adapter.get_metadata)

    # Call generate and verify AdapterResponse
    response = adapter.generate("concise_v1", "test input")
    assert isinstance(response, AdapterResponse)

    metadata = adapter.get_metadata()
    assert isinstance(metadata, dict)
    assert "adapter_id" in metadata
    assert "version" in metadata


def test_mock_adapter_response_format():
    adapter = MockLLMAdapter()
    response = adapter.generate("concise_v1", "test input")

    assert response.text
    assert response.parsed_json is not None
    assert isinstance(response.tokens, (int, type(None)))
    assert isinstance(response.model_metadata, dict)

    prov = response.adapter_provenance
    required_keys = {"adapter_id", "version", "prompt_template_id", "request_id", "raw_output_summary"}
    assert all(key in prov for key in required_keys)


def test_mock_symbolization_coverage():
    """Verify symbolization maps back to candidate texts as expected by mock.

    The mock `concise` response returns atomic_candidates without symbols.
    The mock `symbolize` response returns a legend mapping (e.g., P1 -> claim).
    """
    adapter = MockLLMAdapter()
    response = adapter.generate("concise_v1", "test input")

    candidates = response.parsed_json["atomic_candidates"]
    # concise returns atomic candidates with text and origin_spans
    assert all("text" in c and "origin_spans" in c for c in candidates)

    # symbolization step should provide a legend tying P1 -> candidate text
    symbol_response = adapter.generate("symbolize_v1", "test input")
    legend = symbol_response.parsed_json["legend"]
    assert len(legend) == len(candidates)
    # Verify the first legend value equals the first candidate text
    first_leg_value = list(legend.values())[0]
    assert first_leg_value == candidates[0]["text"]


def test_module_result_validation():
    record = ProvenanceRecord(
        id="test-001",
        created_at=datetime.now(timezone.utc),
        module_id="test_module",
        module_version="0.1",
    )

    result = ModuleResult(
        payload={"test": "data"},
        provenance_record=record,
        confidence=0.95,
        warnings=[],
    )

    assert 0 <= result.confidence <= 1.0
    with pytest.raises(ValueError):
        ModuleResult(
            payload={"test": "data"},
            provenance_record=record,
            confidence=1.5,  # Should fail validation
        )
