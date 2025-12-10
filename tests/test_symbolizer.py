"""
Unit tests for the symbolization module.

This test suite validates all aspects of the symbolization pipeline including:
- Simple symbol assignment (P1, P2, ...)
- Duplicate claim detection (same text → same symbol)
- Deterministic ordering by origin spans
- Extended legend creation with metadata
- Edge cases: empty input, missing origin spans, empty text, large datasets
- Integration with WorldResult and ConcisionResult inputs
- Provenance tracking and confidence scoring

Author: Victor Rowello
Sprint: 2, Task: 4
"""
import pytest
from src.pipeline.symbolizer import (
    assign_symbols,
    symbolizer,
)
from src.witty_types import (
    AtomicClaim,
    ConcisionResult,
    WorldResult,
    FormalizeOptions,
)
from src.pipeline.orchestrator import AgentContext


class TestSymbolAssignment:
    """Test basic symbol assignment functionality."""
    
    def test_simple_two_claims(self):
        """Test simple case: 2 claims → P1, P2."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="it rains", origin_spans=[(0, 8)]),
            AtomicClaim(text="match cancelled", origin_spans=[(13, 28)])
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Verify legend
        assert len(legend) == 2
        assert legend["P1"] == "it rains"
        assert legend["P2"] == "match cancelled"
        
        # Verify symbols assigned to claims
        assert claims_out[0].symbol == "P1"
        assert claims_out[0].text == "it rains"
        assert claims_out[1].symbol == "P2"
        assert claims_out[1].text == "match cancelled"
        
        # Verify extended legend
        assert "P1" in ext_legend
        assert "P2" in ext_legend
        assert ext_legend["P1"]["text"] == "it rains"
        assert ext_legend["P1"]["origin_spans"] == [(0, 8)]
    
    def test_duplicate_text_same_symbol(self):
        """Test duplicate claim text receives same symbol."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="it rains", origin_spans=[(0, 8)]),
            AtomicClaim(text="match cancelled", origin_spans=[(13, 28)]),
            AtomicClaim(text="it rains", origin_spans=[(35, 43)])  # Duplicate
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Should only have 2 unique symbols
        assert len(legend) == 2
        assert legend["P1"] == "it rains"
        assert legend["P2"] == "match cancelled"
        
        # First and third claim should have same symbol
        assert claims_out[0].symbol == "P1"
        assert claims_out[2].symbol == "P1"
        assert claims_out[1].symbol == "P2"
        
        # Extended legend should only have 2 entries
        assert len(ext_legend) == 2
    
    def test_deterministic_ordering_by_origin_span(self):
        """Test claims are ordered by origin span start position."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        # Create claims in non-sorted order
        claims = [
            AtomicClaim(text="third claim", origin_spans=[(20, 31)]),
            AtomicClaim(text="first claim", origin_spans=[(0, 11)]),
            AtomicClaim(text="second claim", origin_spans=[(12, 24)])
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Verify symbols assigned by origin span order, not input order
        # Find claim by text to verify symbol
        first = [c for c in claims_out if c.text == "first claim"][0]
        second = [c for c in claims_out if c.text == "second claim"][0]
        third = [c for c in claims_out if c.text == "third claim"][0]
        
        assert first.symbol == "P1"
        assert second.symbol == "P2"
        assert third.symbol == "P3"
        
        # Verify legend reflects this ordering
        assert legend["P1"] == "first claim"
        assert legend["P2"] == "second claim"
        assert legend["P3"] == "third claim"
    
    def test_claims_without_origin_spans_sorted_last(self):
        """Test claims without origin spans are sorted to the end."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="no span claim", origin_spans=[]),
            AtomicClaim(text="has span", origin_spans=[(5, 13)]),
            AtomicClaim(text="another no span", origin_spans=[])
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Claim with origin span should get P1
        has_span = [c for c in claims_out if c.text == "has span"][0]
        assert has_span.symbol == "P1"
        
        # Claims without spans should get P2, P3 (in original order)
        no_span_1 = [c for c in claims_out if c.text == "no span claim"][0]
        no_span_2 = [c for c in claims_out if c.text == "another no span"][0]
        assert no_span_1.symbol == "P2"
        assert no_span_2.symbol == "P3"
    
    def test_empty_input(self):
        """Test handling of empty atomic claims list."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = []
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        assert legend == {}
        assert claims_out == []
        assert ext_legend == {}
    
    def test_large_claim_set_100_claims(self):
        """Test edge case: 100 claims → P1...P100."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text=f"claim {i}", origin_spans=[(i*10, i*10 + 7)])
            for i in range(100)
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Should have 100 symbols
        assert len(legend) == 100
        assert len(claims_out) == 100
        assert len(ext_legend) == 100
        
        # Verify first and last symbols
        assert "P1" in legend
        assert "P100" in legend
        assert legend["P1"] == "claim 0"
        assert legend["P100"] == "claim 99"
        
        # Verify all claims have symbols assigned
        for claim in claims_out:
            assert claim.symbol is not None
            assert claim.symbol.startswith("P")


class TestSymbolizerFunction:
    """Test the main symbolizer function with different input types."""
    
    def test_symbolizer_with_concision_result(self):
        """Test symbolizer accepts ConcisionResult input."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="it rains", origin_spans=[(3, 11)]),
            AtomicClaim(text="match is cancelled", origin_spans=[(16, 34)])
        ]
        conc_result = ConcisionResult(
            canonical_text="if it rains then match is cancelled",
            atomic_candidates=claims,
            structural_metadata={"connective": "IMPLIES"}
        )
        
        result = symbolizer(conc_result, ctx)
        
        # Verify ModuleResult structure
        assert result.payload is not None
        assert result.provenance_record is not None
        assert result.confidence > 0.0
        
        # Verify payload contains SymbolizerResult fields
        payload = result.payload
        assert "legend" in payload
        assert "atomic_claims" in payload
        assert "extended_legend" in payload
        
        # Verify legend content
        assert payload["legend"]["P1"] == "it rains"
        assert payload["legend"]["P2"] == "match is cancelled"
        
        # Verify claims have symbols
        assert payload["atomic_claims"][0]["symbol"] == "P1"
        assert payload["atomic_claims"][1]["symbol"] == "P2"
    
    def test_symbolizer_with_world_result(self):
        """Test symbolizer accepts WorldResult input."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="all students attend", origin_spans=[(0, 19)]),
        ]
        world_result = WorldResult(
            atomic_claims=claims,
            reduction_metadata={"quantifier_count": 1},
            quantifier_map={"all students": "R1234_students_attend"}
        )
        
        result = symbolizer(world_result, ctx)
        
        assert result.payload is not None
        assert "legend" in result.payload
        assert result.payload["legend"]["P1"] == "all students attend"
    
    def test_symbolizer_with_dict_input(self):
        """Test symbolizer accepts dict input with atomic_claims."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="test claim", origin_spans=[(0, 10)])
        ]
        dict_input = {
            "atomic_claims": claims,
            "metadata": "test"
        }
        
        result = symbolizer(dict_input, ctx)
        
        assert result.payload is not None
        assert result.payload["legend"]["P1"] == "test claim"
    
    def test_symbolizer_invalid_input_type(self):
        """Test symbolizer raises error for invalid input type."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        
        with pytest.raises(ValueError, match="Unsupported input type"):
            symbolizer("invalid input", ctx)
    
    def test_symbolizer_missing_atomic_claims_in_dict(self):
        """Test symbolizer raises error if dict missing atomic_claims."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        dict_input = {"wrong_key": []}
        
        with pytest.raises(ValueError, match="must contain 'atomic_claims'"):
            symbolizer(dict_input, ctx)
    
    def test_symbolizer_empty_claims_warning(self):
        """Test symbolizer generates warning for empty claims list."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        conc_result = ConcisionResult(
            canonical_text="",
            atomic_candidates=[]
        )
        
        result = symbolizer(conc_result, ctx)
        
        # Should have warning about empty input
        assert len(result.warnings) > 0
        assert any("No atomic claims" in w for w in result.warnings)
        
        # Should have empty legend
        assert result.payload["legend"] == {}
    
    def test_symbolizer_claims_without_origin_spans_warning(self):
        """Test symbolizer warns about claims missing origin spans."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="claim 1", origin_spans=[(0, 7)]),
            AtomicClaim(text="claim 2", origin_spans=[]),  # Missing span
            AtomicClaim(text="claim 3", origin_spans=[])   # Missing span
        ]
        conc_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=claims
        )
        
        result = symbolizer(conc_result, ctx)
        
        # Should have warning about missing origin spans
        assert any("missing origin spans" in w for w in result.warnings)
        
        # Should still produce valid output
        assert len(result.payload["legend"]) == 3
    
    def test_symbolizer_empty_claim_text_warning(self):
        """Test symbolizer warns about claims with empty text."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="valid claim", origin_spans=[(0, 11)]),
            AtomicClaim(text="", origin_spans=[(12, 12)]),  # Empty text
            AtomicClaim(text="   ", origin_spans=[(13, 16)])  # Whitespace only
        ]
        conc_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=claims
        )
        
        result = symbolizer(conc_result, ctx)
        
        # Should have warning about empty text
        assert any("empty text" in w for w in result.warnings)
    
    def test_symbolizer_provenance_tracking(self):
        """Test symbolizer creates proper provenance record."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="claim 1", origin_spans=[(0, 7)]),
            AtomicClaim(text="claim 2", origin_spans=[(8, 15)])
        ]
        conc_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=claims
        )
        
        result = symbolizer(conc_result, ctx)
        
        # Verify provenance record
        prov = result.provenance_record
        assert prov.module_id == "symbolizer"
        assert prov.module_version == "1.0.0"
        assert prov.id.startswith("pr_")
        assert len(prov.event_log) > 0
        
        # Verify event log contains symbolization event
        events = [e for e in prov.event_log if e["event_type"] == "symbolization"]
        assert len(events) > 0
        assert events[0]["meta"]["num_symbols"] == 2
        assert events[0]["meta"]["num_claims"] == 2
    
    def test_symbolizer_confidence_reduction_for_issues(self):
        """Test symbolizer reduces confidence for data quality issues."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        
        # Perfect claims - should have high confidence
        perfect_claims = [
            AtomicClaim(text="claim 1", origin_spans=[(0, 7)]),
            AtomicClaim(text="claim 2", origin_spans=[(8, 15)])
        ]
        perfect_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=perfect_claims
        )
        perfect_output = symbolizer(perfect_result, ctx)
        
        # Imperfect claims - should have reduced confidence
        imperfect_claims = [
            AtomicClaim(text="claim 1", origin_spans=[]),  # Missing span
            AtomicClaim(text="", origin_spans=[(0, 0)])     # Empty text
        ]
        imperfect_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=imperfect_claims
        )
        imperfect_output = symbolizer(imperfect_result, ctx)
        
        # Imperfect should have lower confidence
        assert imperfect_output.confidence < perfect_output.confidence
        assert imperfect_output.confidence >= 0.5  # Should never go below 0.5


class TestDeterminism:
    """Test deterministic behavior and reproducibility."""
    
    def test_same_input_same_output(self):
        """Test identical input produces identical output."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="claim A", origin_spans=[(10, 17)]),
            AtomicClaim(text="claim B", origin_spans=[(0, 7)]),
            AtomicClaim(text="claim C", origin_spans=[(20, 27)])
        ]
        
        # Run symbolizer twice
        conc_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=claims
        )
        result1 = symbolizer(conc_result, ctx)
        result2 = symbolizer(conc_result, ctx)
        
        # Results should be identical
        assert result1.payload["legend"] == result2.payload["legend"]
        
        # Symbols should be same
        for i, claim in enumerate(result1.payload["atomic_claims"]):
            assert claim["symbol"] == result2.payload["atomic_claims"][i]["symbol"]
    
    def test_different_salt_different_provenance_id(self):
        """Test different salt produces different provenance ID."""
        claims = [
            AtomicClaim(text="test claim", origin_spans=[(0, 10)])
        ]
        conc_result = ConcisionResult(
            canonical_text="test",
            atomic_candidates=claims
        )
        
        ctx1 = AgentContext("req_test", FormalizeOptions(), deterministic_salt="salt1")
        ctx2 = AgentContext("req_test", FormalizeOptions(), deterministic_salt="salt2")
        
        result1 = symbolizer(conc_result, ctx1)
        result2 = symbolizer(conc_result, ctx2)
        
        # Legend should be same (deterministic symbols)
        assert result1.payload["legend"] == result2.payload["legend"]
        
        # Provenance IDs should differ (different salt)
        assert result1.provenance_record.id != result2.provenance_record.id
    
    def test_origin_span_ordering_stability(self):
        """Test origin span sorting is stable and deterministic."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        
        # Create claims with same origin span (tie-breaker tests)
        claims = [
            AtomicClaim(text="claim 1", origin_spans=[(0, 10)]),
            AtomicClaim(text="claim 2", origin_spans=[(0, 10)]),
            AtomicClaim(text="claim 3", origin_spans=[(0, 10)])
        ]
        
        legend, claims_out, _ = assign_symbols(claims, ctx)
        
        # Should maintain original order for ties
        assert claims_out[0].text == "claim 1"
        assert claims_out[0].symbol == "P1"
        assert claims_out[1].text == "claim 2"
        assert claims_out[1].symbol == "P2"
        assert claims_out[2].text == "claim 3"
        assert claims_out[2].symbol == "P3"


class TestExtendedLegend:
    """Test extended legend creation and metadata."""
    
    def test_extended_legend_contains_metadata(self):
        """Test extended legend includes all required metadata."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        from src.witty_types import ProvenanceRecord
        
        prov = ProvenanceRecord(
            id="pr_test123",
            module_id="test",
            module_version="1.0.0"
        )
        
        claims = [
            AtomicClaim(
                text="test claim",
                origin_spans=[(5, 15)],
                modal_context="necessity",
                provenance=prov
            )
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Verify extended legend has full metadata
        assert "P1" in ext_legend
        entry = ext_legend["P1"]
        assert entry["text"] == "test claim"
        assert entry["origin_spans"] == [(5, 15)]
        assert entry["provenance_id"] == "pr_test123"
        assert entry["modal_context"] == "necessity"
        assert "first_appearance_index" in entry
    
    def test_extended_legend_only_first_occurrence(self):
        """Test extended legend only includes first occurrence of duplicates."""
        ctx = AgentContext("req_test", FormalizeOptions(), deterministic_salt="test")
        claims = [
            AtomicClaim(text="duplicate", origin_spans=[(0, 9)]),
            AtomicClaim(text="unique", origin_spans=[(10, 16)]),
            AtomicClaim(text="duplicate", origin_spans=[(20, 29)])
        ]
        
        legend, claims_out, ext_legend = assign_symbols(claims, ctx)
        
        # Extended legend should only have 2 entries (P1 and P2)
        assert len(ext_legend) == 2
        assert "P1" in ext_legend
        assert "P2" in ext_legend
        
        # P1 should reference first occurrence
        assert ext_legend["P1"]["origin_spans"] == [(0, 9)]
        assert ext_legend["P1"]["first_appearance_index"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
