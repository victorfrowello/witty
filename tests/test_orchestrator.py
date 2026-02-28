"""
Integration test for orchestrator: deterministic mock path
Validates that orchestrator runs end-to-end and produces FormalizationResult matching schema.

Sprint 7 additions: Tests for structural metadata conversion.
"""

from src.pipeline.orchestrator import formalize_statement, _convert_indices_to_symbols
from src.witty.types import FormalizeOptions, FormalizationResult
from src.witty_types import AtomicClaim


class TestConvertIndicesToSymbols:
    """Test conversion of claim indices to symbols in structural metadata."""
    
    def test_convert_conditional_indices(self):
        """Test converting conditional indices to symbols."""
        claims = [
            AtomicClaim(text="it rains", symbol="P1", origin_spans=[(0, 8)]),
            AtomicClaim(text="ground is wet", symbol="P2", origin_spans=[(14, 27)]),
        ]
        metadata = {
            "structure_type": "conditional",
            "conditional": {
                "antecedent_indices": [0],
                "consequent_indices": [1],
            }
        }
        
        result = _convert_indices_to_symbols(metadata, claims)
        
        assert result["conditional"]["antecedent_claims"] == ["P1"]
        assert result["conditional"]["consequent_claims"] == ["P2"]
        
    def test_convert_mixed_structure(self):
        """Test converting mixed conjunction + conditional indices."""
        claims = [
            AtomicClaim(text="roses are red", symbol="P1", origin_spans=[(0, 13)]),
            AtomicClaim(text="violets are blue", symbol="P2", origin_spans=[(18, 34)]),
            AtomicClaim(text="it's tuesday", symbol="P3", origin_spans=[(40, 52)]),
            AtomicClaim(text="violets are purple", symbol="P4", origin_spans=[(59, 77)]),
        ]
        metadata = {
            "structure_type": "mixed",
            "conjunction": {"conjunct_indices": [0, 1]},
            "conditional": {
                "antecedent_indices": [2],
                "consequent_indices": [3],
            }
        }
        
        result = _convert_indices_to_symbols(metadata, claims)
        
        assert result["conjunction"]["conjunct_claims"] == ["P1", "P2"]
        assert result["conditional"]["antecedent_claims"] == ["P3"]
        assert result["conditional"]["consequent_claims"] == ["P4"]
        
    def test_convert_empty_metadata(self):
        """Test handling of empty metadata."""
        result = _convert_indices_to_symbols({}, [])
        assert result == {}
        
    def test_convert_with_invalid_indices(self):
        """Test handling of invalid indices (out of bounds)."""
        claims = [
            AtomicClaim(text="test", symbol="P1", origin_spans=[(0, 4)]),
        ]
        metadata = {
            "conditional": {
                "antecedent_indices": [0, 99],  # 99 is out of bounds
                "consequent_indices": [1000],   # Also out of bounds
            }
        }
        
        result = _convert_indices_to_symbols(metadata, claims)
        
        # Should only include valid indices
        assert result["conditional"]["antecedent_claims"] == ["P1"]
        assert result["conditional"]["consequent_claims"] == []


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
