"""Unit tests for core Pydantic models used in Sprint 1.

These tests exercise basic construction and (de)serialization behaviors so
that future changes to the models are quickly caught by CI.
"""

import json
from datetime import timezone
from pydantic import ValidationError
import pytest

from src.witty.types import (
    AtomicClaim,
    ConcisionResult,
    FormalizationResult,
    FormalizeOptions,
    ModuleResult,
    ProvenanceRecord,
    ModuleStage,
)


def test_provenance_record_and_module_result_roundtrip():
    prov = ProvenanceRecord(
        id="prov1",
        module_id="concision",
        module_version="0.1",
    )

    payload = {"canonical_text": "A sample."}
    mr = ModuleResult(payload=payload, provenance_record=prov, confidence=0.95)

    assert mr.payload["canonical_text"] == "A sample."
    assert mr.provenance_record.id == "prov1"


def test_formalization_result_serialization_roundtrip():
    prov = ProvenanceRecord(
        id="prov2",
        module_id="symbolizer",
        module_version="0.1",
    )

    claim = AtomicClaim(text="The sky is blue.", symbol="P1", provenance=prov)
    fr = FormalizationResult(
        request_id="r1",
        original_text="The sky appears blue today.",
        canonical_text="The sky is blue.",
        atomic_claims=[claim],
        legend={"P1": "The sky is blue."},
        confidence=0.9,
        provenance=[prov],
    )

    dumped = fr.model_dump()
    assert dumped["request_id"] == "r1"
    assert isinstance(dumped["atomic_claims"], list)

    # roundtrip via json
    json_text = json.dumps(dumped, default=str)
    reloaded = json.loads(json_text)
    assert reloaded["request_id"] == "r1"


def test_concision_result_structure():
    cr = ConcisionResult(
        canonical_text="Test.",
        atomic_candidates=[AtomicClaim(text="Test.")],
        confidence=0.8,
    )

    assert cr.canonical_text == "Test."
    assert cr.atomic_candidates[0].text == "Test."


def test_provenance_timestamp_is_timezone_aware():
    # Ensure default created_at is timezone-aware UTC
    prov = ProvenanceRecord(id="p-ts", module_id="m", module_version="0.1")
    assert prov.created_at.tzinfo is not None
    assert prov.created_at.tzinfo.utcoffset(prov.created_at) == timezone.utc.utcoffset(prov.created_at)


def test_module_stage_enum_values():
    """Test that ModuleStage enum has expected values and behavior"""
    assert ModuleStage.PREPROCESSING == "preprocessing"
    assert ModuleStage.CONCISION == "concision"
    assert ModuleStage.ENRICHMENT == "enrichment"
    assert ModuleStage.MODALITY == "modality"
    assert ModuleStage.WORLD == "world"
    assert ModuleStage.SYMBOLIZATION == "symbolization"
    assert ModuleStage.CNF == "cnf"
    assert ModuleStage.VALIDATION == "validation"


def test_formalize_options_validation():
    """Test FormalizeOptions validation rules"""
    # Test valid options
    opts = FormalizeOptions(
        retrieval_enabled=True,
        top_k_symbolizations=3,
        privacy_mode="strict"
    )
    assert opts.retrieval_enabled is True
    assert opts.top_k_symbolizations == 3
    assert opts.privacy_mode == "strict"

    # Test defaults
    default_opts = FormalizeOptions()
    assert default_opts.retrieval_enabled is False
    assert default_opts.privacy_mode == "default"
    assert default_opts.verbosity == 0


def test_confidence_validation():
    """Test confidence value constraints"""
    # Valid confidence values
    assert ModuleResult(
        payload={},
        provenance_record=ProvenanceRecord(
            id="test",
            module_id="test",
            module_version="0.1"
        ),
        confidence=0.5
    ).confidence == 0.5

    # Invalid confidence values
    with pytest.raises(ValidationError):
        ModuleResult(
            payload={},
            provenance_record=ProvenanceRecord(
                id="test",
                module_id="test",
                module_version="0.1"
            ),
            confidence=1.5
        )
    
    with pytest.raises(ValidationError):
        ModuleResult(
            payload={},
            provenance_record=ProvenanceRecord(
                id="test",
                module_id="test",
                module_version="0.1"
            ),
            confidence=-0.1
        )


def test_atomic_claim_validation():
    """Test AtomicClaim validation and structure"""
    prov = ProvenanceRecord(
        id="prov3",
        module_id="test",
        module_version="0.1"
    )

    # Test valid atomic claim
    claim = AtomicClaim(
        text="Test claim",
        symbol="P1",
        origin_spans=[(0, 10)],
        modal_context="POSSIBLE",
        provenance=prov
    )
    assert claim.text == "Test claim"
    assert claim.symbol == "P1"
    assert claim.origin_spans == [(0, 10)]

    # Test optional fields
    min_claim = AtomicClaim(text="Minimal claim")
    assert min_claim.symbol is None
    assert min_claim.origin_spans == []
    assert min_claim.modal_context is None
    assert min_claim.provenance is None
