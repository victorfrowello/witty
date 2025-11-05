"""
Integration test for orchestrator: deterministic mock path
Validates that orchestrator runs end-to-end and produces FormalizationResult matching schema.
"""

from src.pipeline.orchestrator import formalize_statement
from src.witty.types import FormalizeOptions, FormalizationResult

def test_orchestrator_deterministic_path():
    opts = FormalizeOptions()
    text = "If Alice owns a red car then she likely prefers driving. She said she doesn't like long trips."
    result = formalize_statement(text, opts)
    # Basic checks
    assert isinstance(result, FormalizationResult)
    assert result.original_text == text
    assert result.canonical_text
    assert len(result.atomic_claims) >= 1
    assert all("symbol" in claim for claim in result.atomic_claims)
    assert result.legend
    assert result.cnf
    assert result.cnf_clauses
    # Provenance checks
    assert result.provenance and isinstance(result.provenance, list)
    # Logical form
    assert result.logical_form_candidates and result.chosen_logical_form
    # Deterministic fallback event
    fallback_found = any(
        "event_type" in ev and ev["event_type"] == "fallback"
        for prov in result.provenance
        for ev in getattr(prov, "event_log", [])
    )
    assert fallback_found, "Deterministic fallback event not found in provenance"
