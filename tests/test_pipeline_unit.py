from src.pipeline import orchestrator
from src.pipeline.orchestrator import ingest, preprocess, deterministic_concision, formalize_statement
from src.witty.types import FormalizeOptions, ModuleResult, ProvenanceRecord


def test_ingest_creates_normalized_text_and_provenance():
    opts = FormalizeOptions()
    ctx = orchestrator.AgentContext("req_test", opts)
    raw = "  Hello world.  "
    res = ingest(raw, ctx)
    assert isinstance(res, ModuleResult)
    assert res.payload["normalized_text"] == "Hello world."
    assert isinstance(res.provenance_record, ProvenanceRecord)
    assert res.provenance_record.origin_spans[0][0] == 0


def test_preprocess_splits_clauses_and_returns_origin_spans():
    opts = FormalizeOptions()
    ctx = orchestrator.AgentContext("req_test", opts)
    ingest_payload = {"normalized_text": "First sentence. Second."}
    res = preprocess(ingest_payload, ctx)
    assert isinstance(res, ModuleResult)
    assert "clauses" in res.payload
    assert len(res.payload["clauses"]) == 2
    assert isinstance(res.provenance_record, ProvenanceRecord)


def test_deterministic_concision_creates_atomic_candidates_and_provenance():
    opts = FormalizeOptions()
    ctx = orchestrator.AgentContext("req_test", opts)
    prep_payload = {"clauses": [{"text": "A.", "start": 0, "end": 2}], "origin_spans": [(0,2)]}
    res = deterministic_concision(prep_payload, ctx)
    assert isinstance(res, ModuleResult)
    payload = res.payload
    assert "canonical_text" in payload
    assert payload["atomic_candidates"]
    # Provenance must record fallback event for deterministic concision
    prov = res.provenance_record
    assert isinstance(prov, ProvenanceRecord)
    assert any(ev.get("event_type") == "fallback" for ev in prov.event_log)


def test_formalize_statement_end_to_end():
    opts = FormalizeOptions()
    text = "If Alice owns a red car then she likely prefers driving."
    result = formalize_statement(text, opts)
    # Basic validations
    assert result.original_text == text
    assert result.canonical_text
    assert result.atomic_claims
    # atomic_claims are typed AtomicClaim instances in the FormalizationResult model
    assert all(hasattr(c, "symbol") or isinstance(c, dict) for c in result.atomic_claims)
    assert result.provenance and isinstance(result.provenance[0], ProvenanceRecord)
