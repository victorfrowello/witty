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
    assert result is not None
    assert hasattr(result, 'request_id')
    assert result.original_text == text
    assert result.canonical_text
    assert len(result.atomic_claims) >= 1
    assert all(hasattr(claim, "symbol") for claim in result.atomic_claims)
    assert result.legend
    assert result.cnf
    assert result.cnf_clauses
    # Provenance checks
    assert result.provenance and len(result.provenance) > 0
    # Logical form
    assert result.logical_form_candidates and result.chosen_logical_form
    # Check that concision module was called (Sprint 2 uses deterministic_concision)
    concision_found = any(
        prov.module_id == "concision" 
        for prov in result.provenance
    )
    assert concision_found, "Concision module provenance not found"
    
    # Check that event logs exist and contain processing events
    has_events = any(
        len(prov.event_log) > 0
        for prov in result.provenance
    )
    assert has_events, "No event logs found in provenance"
