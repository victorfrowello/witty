"""Unit tests for core Pydantic models used in Sprint 1.

These tests exercise basic construction and (de)serialization behaviors so
that future changes to the models are quickly caught by CI.
"""

import json
from datetime import timezone

from src.types import (
    AtomicClaim,
    ConcisionResult,
    FormalizationResult,
    FormalizeOptions,
    ModuleResult,
    ProvenanceRecord,
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
