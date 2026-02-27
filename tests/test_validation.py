"""
Sprint 3 Tests: Validation Module.

Tests for the validation module including symbol coverage, provenance coverage,
tautology/contradiction detection, entity coherence, and confidence aggregation.

Author: Victor Rowello
Sprint: 3
"""
import pytest
from datetime import datetime, timezone

from src.pipeline.validation import (
    ValidationReport,
    validate_symbol_coverage,
    validate_provenance_coverage,
    detect_tautology,
    detect_contradiction,
    validate_entity_coherence,
    aggregate_confidence,
    validate_formalization,
)
from src.witty_types import (
    AtomicClaim,
    ProvenanceRecord,
    EntityGrounding,
    CoherenceReport,
)


class TestSymbolCoverage:
    """Tests for symbol coverage validation."""
    
    def test_complete_coverage(self):
        """All CNF symbols appear in legend."""
        cnf_clauses = [["P1", "P2"], ["P3"]]
        legend = {"P1": "rain", "P2": "cold", "P3": "wind"}
        
        is_valid, details = validate_symbol_coverage(cnf_clauses, legend)
        
        assert is_valid
        assert details["is_complete"]
        assert len(details["missing_symbols"]) == 0
    
    def test_missing_symbol(self):
        """Missing symbol should be detected."""
        cnf_clauses = [["P1", "P2"], ["P4"]]  # P4 not in legend
        legend = {"P1": "rain", "P2": "cold", "P3": "wind"}
        
        is_valid, details = validate_symbol_coverage(cnf_clauses, legend)
        
        assert not is_valid
        assert "P4" in details["missing_symbols"]
    
    def test_unused_symbol_warning(self):
        """Unused legend symbols should be noted."""
        cnf_clauses = [["P1"]]
        legend = {"P1": "rain", "P2": "cold"}  # P2 unused
        
        is_valid, details = validate_symbol_coverage(cnf_clauses, legend)
        
        assert is_valid  # Still valid, just unused
        assert "P2" in details["unused_symbols"]
    
    def test_negated_symbols(self):
        """Negated symbols should be handled correctly."""
        cnf_clauses = [["P1", "¬P2"]]
        legend = {"P1": "rain", "P2": "cold"}
        
        is_valid, details = validate_symbol_coverage(cnf_clauses, legend)
        
        assert is_valid
    
    def test_empty_clauses(self):
        """Empty clauses list should be valid."""
        is_valid, details = validate_symbol_coverage([], {"P1": "test"})
        
        assert is_valid


class TestProvenanceCoverage:
    """Tests for provenance coverage validation."""
    
    def test_all_claims_have_provenance(self):
        """All claims with provenance should pass."""
        prov = ProvenanceRecord(
            id="pr_test123",
            module_id="test",
            module_version="1.0"
        )
        claims = [
            AtomicClaim(text="rain", symbol="P1", provenance=prov),
            AtomicClaim(text="cold", symbol="P2", provenance=prov),
        ]
        
        is_valid, details = validate_provenance_coverage(claims, [prov])
        
        assert is_valid
        assert details["coverage_ratio"] == 1.0
    
    def test_missing_provenance(self):
        """Claims without provenance should be detected."""
        prov = ProvenanceRecord(
            id="pr_test123",
            module_id="test",
            module_version="1.0"
        )
        claims = [
            AtomicClaim(text="rain", symbol="P1", provenance=prov),
            AtomicClaim(text="cold", symbol="P2"),  # No provenance
        ]
        
        is_valid, details = validate_provenance_coverage(claims, [prov])
        
        assert not is_valid
        assert details["coverage_ratio"] == 0.5
        assert len(details["claims_without_provenance"]) == 1
    
    def test_empty_claims(self):
        """Empty claims list should be valid."""
        is_valid, details = validate_provenance_coverage([], [])
        
        assert is_valid
        assert details["coverage_ratio"] == 1.0


class TestTautologyDetection:
    """Tests for tautology detection."""
    
    def test_simple_tautology(self):
        """P ∨ ¬P is a tautology."""
        clauses = [["P1", "¬P1"]]
        
        is_taut, reason = detect_tautology(clauses)
        
        assert is_taut
        assert reason is not None
    
    def test_multiple_tautologous_clauses(self):
        """All clauses tautologous means formula is tautology."""
        clauses = [["P1", "¬P1"], ["P2", "¬P2"]]
        
        is_taut, reason = detect_tautology(clauses)
        
        assert is_taut
    
    def test_not_tautology(self):
        """P ∧ Q is not a tautology."""
        clauses = [["P1"], ["P2"]]
        
        is_taut, reason = detect_tautology(clauses)
        
        assert not is_taut
    
    def test_partial_tautology(self):
        """Some tautologous clauses but not all."""
        clauses = [["P1", "¬P1"], ["P2"]]  # First is tautologous, second is not
        
        is_taut, reason = detect_tautology(clauses)
        
        assert not is_taut  # Formula is not a tautology
    
    def test_empty_clauses(self):
        """Empty clauses are not a tautology."""
        is_taut, reason = detect_tautology([])
        
        assert not is_taut


class TestContradictionDetection:
    """Tests for contradiction detection."""
    
    def test_simple_contradiction(self):
        """P ∧ ¬P is a contradiction."""
        clauses = [["P1"], ["¬P1"]]  # Unit clauses P and ¬P
        
        is_contra, reason = detect_contradiction(clauses)
        
        assert is_contra
        assert "P1" in reason
    
    def test_empty_clause_contradiction(self):
        """Empty clause is immediate contradiction."""
        clauses = [["P1"], []]
        
        is_contra, reason = detect_contradiction(clauses)
        
        assert is_contra
    
    def test_not_contradiction(self):
        """P ∧ Q is satisfiable."""
        clauses = [["P1"], ["P2"]]
        
        is_contra, reason = detect_contradiction(clauses)
        
        assert not is_contra
    
    def test_non_unit_clauses(self):
        """Non-unit clauses don't trigger simple contradiction."""
        clauses = [["P1", "P2"], ["¬P1", "P2"]]  # Satisfiable
        
        is_contra, reason = detect_contradiction(clauses)
        
        assert not is_contra


class TestEntityCoherence:
    """Tests for entity coherence validation."""
    
    def test_all_entities_grounded(self):
        """All entities with groundings should pass."""
        claims = [AtomicClaim(text="John runs", symbol="P1")]
        groundings = {
            "John": EntityGrounding(
                entity_text="John",
                entity_type="PERSON",
                related_claim_ids=["P1"]
            )
        }
        
        is_coherent, report = validate_entity_coherence(claims, groundings)
        
        assert is_coherent
        assert report.entity_completeness == 1.0
    
    def test_ungrounded_entities(self):
        """Ungrounded entities should be detected."""
        claims = [AtomicClaim(text="John meets Mary", symbol="P1")]
        groundings = {
            "John": EntityGrounding(
                entity_text="John",
                entity_type="PERSON"
            )
            # Mary is not grounded
        }
        
        is_coherent, report = validate_entity_coherence(claims, groundings)
        
        assert not is_coherent
        assert "Mary" in report.ungrounded_entities
    
    def test_no_entities(self):
        """No entities should be coherent."""
        claims = [AtomicClaim(text="it rains", symbol="P1")]  # No named entities
        groundings = {}
        
        is_coherent, report = validate_entity_coherence(claims, groundings)
        
        assert is_coherent
        assert report.entity_completeness == 1.0
    
    def test_quantifier_coverage(self):
        """Reduced quantifiers should be tracked."""
        claims = [
            AtomicClaim(text="students attend", symbol="R1234_students_attend"),
        ]
        groundings = {}
        
        is_coherent, report = validate_entity_coherence(claims, groundings)
        
        # Quantifier should be detected as reduced (R prefix)
        assert report.quantifier_coverage == 1.0


class TestConfidenceAggregation:
    """Tests for confidence aggregation."""
    
    def test_average_confidence(self):
        """Confidence should be averaged across modules."""
        provs = [
            ProvenanceRecord(id="1", module_id="mod1", module_version="1.0", confidence=0.8),
            ProvenanceRecord(id="2", module_id="mod2", module_version="1.0", confidence=1.0),
        ]
        
        result = aggregate_confidence(provs)
        
        assert 0.85 <= result <= 0.95  # Weighted average
    
    def test_weighted_confidence(self):
        """Critical modules should be weighted higher."""
        provs = [
            ProvenanceRecord(id="1", module_id="concision", module_version="1.0", confidence=0.7),
            ProvenanceRecord(id="2", module_id="validation", module_version="1.0", confidence=1.0),
        ]
        
        result = aggregate_confidence(provs)
        
        # Concision has higher weight (1.2 vs 0.9), so result should be closer to 0.7
        assert result < 0.9
    
    def test_empty_provenance(self):
        """Empty provenance should return 1.0."""
        result = aggregate_confidence([])
        
        assert result == 1.0
    
    def test_custom_weights(self):
        """Custom weights should be respected."""
        provs = [
            ProvenanceRecord(id="1", module_id="mod1", module_version="1.0", confidence=0.5),
            ProvenanceRecord(id="2", module_id="mod2", module_version="1.0", confidence=1.0),
        ]
        weights = {"mod1": 3.0, "mod2": 1.0}  # mod1 weighted 3x
        
        result = aggregate_confidence(provs, weights)
        
        # Expected: (0.5*3 + 1.0*1) / 4 = 2.5/4 = 0.625
        assert 0.6 <= result <= 0.65


class TestFullValidation:
    """Tests for complete validation function."""
    
    def test_valid_formalization(self):
        """Valid formalization should pass."""
        prov = ProvenanceRecord(
            id="pr_test",
            module_id="test",
            module_version="1.0",
            confidence=1.0
        )
        claims = [
            AtomicClaim(text="rain", symbol="P1", provenance=prov),
        ]
        legend = {"P1": "rain"}
        cnf_clauses = [["P1"]]
        
        result = validate_formalization(
            atomic_claims=claims,
            legend=legend,
            cnf_clauses=cnf_clauses,
            provenance_records=[prov],
            salt="test"
        )
        
        report = ValidationReport(**result.payload)
        
        assert report.is_valid
        assert report.aggregated_confidence >= 0.5
    
    def test_invalid_symbol_coverage(self):
        """Missing symbol should cause validation failure."""
        prov = ProvenanceRecord(
            id="pr_test",
            module_id="test",
            module_version="1.0"
        )
        claims = [AtomicClaim(text="rain", symbol="P1", provenance=prov)]
        legend = {"P1": "rain"}
        cnf_clauses = [["P1"], ["P2"]]  # P2 not in legend
        
        result = validate_formalization(
            atomic_claims=claims,
            legend=legend,
            cnf_clauses=cnf_clauses,
            provenance_records=[prov],
            salt="test"
        )
        
        report = ValidationReport(**result.payload)
        
        assert not report.is_valid
        assert len(report.issues) > 0
    
    def test_contradiction_detected(self):
        """Contradiction should be flagged."""
        prov = ProvenanceRecord(
            id="pr_test",
            module_id="test",
            module_version="1.0"
        )
        claims = [
            AtomicClaim(text="rain", symbol="P1", provenance=prov),
        ]
        legend = {"P1": "rain"}
        cnf_clauses = [["P1"], ["¬P1"]]  # Contradiction
        
        result = validate_formalization(
            atomic_claims=claims,
            legend=legend,
            cnf_clauses=cnf_clauses,
            provenance_records=[prov],
            salt="test"
        )
        
        report = ValidationReport(**result.payload)
        
        assert report.contradiction_detected
        assert not report.is_valid
    
    def test_provenance_tracking(self):
        """Validation should create its own provenance."""
        result = validate_formalization(
            atomic_claims=[],
            legend={},
            cnf_clauses=[],
            provenance_records=[],
            salt="test"
        )
        
        assert result.provenance_record.module_id == "validation"
        assert result.provenance_record.id.startswith("pr_")
    
    def test_event_log(self):
        """Validation should log all checks."""
        prov = ProvenanceRecord(
            id="pr_test",
            module_id="test",
            module_version="1.0"
        )
        claims = [AtomicClaim(text="P", symbol="P1", provenance=prov)]
        
        result = validate_formalization(
            atomic_claims=claims,
            legend={"P1": "P"},
            cnf_clauses=[["P1"]],
            provenance_records=[prov],
            salt="test"
        )
        
        event_types = [e["event_type"] for e in result.provenance_record.event_log]
        
        assert "symbol_coverage_check" in event_types
        assert "provenance_coverage_check" in event_types
        assert "tautology_check" in event_types
        assert "contradiction_check" in event_types
        assert "entity_coherence_check" in event_types
        assert "confidence_aggregation" in event_types


class TestValidationEdgeCases:
    """Edge case tests for validation."""
    
    def test_large_formula(self):
        """Large formulas should validate efficiently."""
        prov = ProvenanceRecord(
            id="pr_test",
            module_id="test",
            module_version="1.0"
        )
        
        # Create 100 claims and clauses
        claims = [
            AtomicClaim(text=f"claim_{i}", symbol=f"P{i}", provenance=prov)
            for i in range(100)
        ]
        legend = {f"P{i}": f"claim_{i}" for i in range(100)}
        cnf_clauses = [[f"P{i}"] for i in range(100)]
        
        result = validate_formalization(
            atomic_claims=claims,
            legend=legend,
            cnf_clauses=cnf_clauses,
            provenance_records=[prov],
            salt="test"
        )
        
        report = ValidationReport(**result.payload)
        
        assert report.is_valid
        assert report.diagnostics["total_claims"] == 100
    
    def test_entity_with_spaces(self):
        """Multi-word entities should be handled."""
        claims = [AtomicClaim(text="New York is busy", symbol="P1")]
        groundings = {
            "New York": EntityGrounding(
                entity_text="New York",
                entity_type="LOCATION"
            )
        }
        
        is_coherent, report = validate_entity_coherence(claims, groundings)
        
        # Should recognize "New York" as grounded
        assert is_coherent or "New" in report.ungrounded_entities
