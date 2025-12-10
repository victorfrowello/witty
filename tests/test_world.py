"""
Unit tests for the world construction module.

This test suite validates all aspects of the world construction pipeline including:
- Universal quantifier detection and reduction
- Existential quantifier detection and reduction
- Negative quantifier detection and reduction
- Deterministic ID generation (reproducibility)
- Presupposition detection
- Integration with concision module
- Edge cases and error handling

Author: Victor Rowello
Sprint: 2, Task: 3
"""
import pytest
from src.pipeline.world import (
    detect_quantifier,
    generate_deterministic_id,
    reduce_quantifiers,
    detect_presupposition,
    world_construct,
    create_reduction_rationale,
    QuantifierStructure,
    PresuppositionStructure,
    WorldResult,
)
from src.witty_types import (
    AtomicClaim,
    ConcisionResult,
    ModuleResult,
)


class TestQuantifierDetection:
    """Test quantifier detection for universal, existential, and negative cases."""
    
    def test_universal_all(self):
        """Test detection of 'all' universal quantifier."""
        text = "All students must attend class"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "UNIVERSAL"
        assert quantifier.quantifier_text == "all"
        assert "student" in quantifier.variable.lower()
        assert "attend" in quantifier.predicate.lower()
        assert quantifier.confidence >= 0.85
    
    def test_universal_every(self):
        """Test detection of 'every' universal quantifier."""
        text = "Every employee submits timesheets"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "UNIVERSAL"
        assert quantifier.quantifier_text == "every"
        assert "employee" in quantifier.variable.lower()
        assert "submit" in quantifier.predicate.lower()
    
    def test_universal_each(self):
        """Test detection of 'each' universal quantifier."""
        text = "Each participant receives a certificate"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "UNIVERSAL"
        assert quantifier.quantifier_text == "each"
        assert "participant" in quantifier.variable.lower()
    
    def test_existential_some(self):
        """Test detection of 'some' existential quantifier."""
        text = "Some students passed the test"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "EXISTENTIAL"
        assert quantifier.quantifier_text == "some"
        assert "student" in quantifier.variable.lower()
        assert "passed" in quantifier.predicate.lower()
    
    def test_existential_a(self):
        """Test detection of 'a' as existential quantifier."""
        text = "A student passed the exam"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "EXISTENTIAL"
        assert quantifier.quantifier_text in ["a", "an"]
        assert "student" in quantifier.variable.lower()
    
    def test_existential_there_exists(self):
        """Test detection of 'there exists' pattern."""
        text = "There exists a solution to this problem"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "EXISTENTIAL"
        # The pattern captures "solution" as the variable
        assert "solution" in quantifier.variable.lower()
    
    def test_negative_no(self):
        """Test detection of 'no' negative quantifier."""
        text = "No cars are allowed in this area"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "NEGATIVE"
        assert quantifier.quantifier_text == "no"
        assert "car" in quantifier.variable.lower()
        assert "allowed" in quantifier.predicate.lower()
    
    def test_negative_none(self):
        """Test detection of 'none' negative quantifier."""
        text = "None of the applicants were qualified"
        quantifier = detect_quantifier(text)
        
        assert quantifier is not None
        assert quantifier.quantifier_type == "NEGATIVE"
        assert quantifier.quantifier_text == "none"
    
    def test_no_quantifier_simple_sentence(self):
        """Test that simple declarative sentences don't trigger quantifier detection."""
        text = "The cat sat on the mat"
        quantifier = detect_quantifier(text)
        
        assert quantifier is None
    
    def test_no_quantifier_conditional(self):
        """Test that conditionals without quantifiers return None."""
        text = "If it rains then the match is cancelled"
        quantifier = detect_quantifier(text)
        
        assert quantifier is None


class TestDeterministicIDGeneration:
    """Test deterministic ID generation for reproducibility."""
    
    def test_universal_id_format(self):
        """Test that universal quantifiers generate IDs with 'R' prefix."""
        id_str = generate_deterministic_id(
            text="All students attend",
            salt="test_salt",
            quantifier_type="UNIVERSAL",
            variable="students",
            predicate="attend"
        )
        
        assert id_str.startswith("R")
        assert "students" in id_str
        assert "attend" in id_str
        # Format: R{hash}_variable_predicate
        parts = id_str.split("_")
        assert len(parts) >= 3  # At least prefix+hash, variable, predicate
    
    def test_existential_id_format(self):
        """Test that existential quantifiers generate IDs with 'E' prefix."""
        id_str = generate_deterministic_id(
            text="Some employees passed",
            salt="test_salt",
            quantifier_type="EXISTENTIAL",
            variable="employees",
            predicate="passed"
        )
        
        assert id_str.startswith("E")
        assert "employees" in id_str
        assert "passed" in id_str
    
    def test_negative_id_format(self):
        """Test that negative quantifiers generate IDs with 'N' prefix."""
        id_str = generate_deterministic_id(
            text="No cars allowed",
            salt="test_salt",
            quantifier_type="NEGATIVE",
            variable="cars",
            predicate="allowed"
        )
        
        assert id_str.startswith("N")
        assert "cars" in id_str
        assert "allowed" in id_str
    
    def test_determinism_same_inputs(self):
        """Test that same inputs produce same ID (determinism)."""
        id1 = generate_deterministic_id(
            text="All students attend",
            salt="salt123",
            quantifier_type="UNIVERSAL",
            variable="students",
            predicate="attend"
        )
        
        id2 = generate_deterministic_id(
            text="All students attend",
            salt="salt123",
            quantifier_type="UNIVERSAL",
            variable="students",
            predicate="attend"
        )
        
        assert id1 == id2, "Same inputs should produce same ID"
    
    def test_different_salt_different_id(self):
        """Test that different salts produce different IDs."""
        id1 = generate_deterministic_id(
            text="All students attend",
            salt="salt1",
            quantifier_type="UNIVERSAL",
            variable="students",
            predicate="attend"
        )
        
        id2 = generate_deterministic_id(
            text="All students attend",
            salt="salt2",
            quantifier_type="UNIVERSAL",
            variable="students",
            predicate="attend"
        )
        
        assert id1 != id2, "Different salts should produce different IDs"
    
    def test_different_text_different_id(self):
        """Test that different text produces different IDs."""
        id1 = generate_deterministic_id(
            text="All students attend",
            salt="salt123",
            quantifier_type="UNIVERSAL",
            variable="students",
            predicate="attend"
        )
        
        id2 = generate_deterministic_id(
            text="All teachers attend",
            salt="salt123",
            quantifier_type="UNIVERSAL",
            variable="teachers",
            predicate="attend"
        )
        
        assert id1 != id2, "Different text should produce different IDs"
    
    def test_sanitization_spaces(self):
        """Test that spaces in variable/predicate are sanitized."""
        id_str = generate_deterministic_id(
            text="All qualified employees receive benefits",
            salt="test_salt",
            quantifier_type="UNIVERSAL",
            variable="qualified employees",
            predicate="receive benefits"
        )
        
        # Spaces should be replaced with underscores
        assert " " not in id_str
        assert "qualified" in id_str.lower()
        assert "employees" in id_str.lower()
    
    def test_sanitization_special_chars(self):
        """Test that special characters are removed."""
        id_str = generate_deterministic_id(
            text="All students (aged 18+) must attend!",
            salt="test_salt",
            quantifier_type="UNIVERSAL",
            variable="students (aged 18+)",
            predicate="must attend!"
        )
        
        # Special chars should be removed
        assert "(" not in id_str
        assert ")" not in id_str
        assert "+" not in id_str
        assert "!" not in id_str


class TestQuantifierReduction:
    """Test quantifier reduction to propositional placeholders."""
    
    def test_universal_reduction(self):
        """Test reduction of universal quantifier."""
        quantifier = QuantifierStructure(
            quantifier_type="UNIVERSAL",
            quantifier_text="all",
            variable="students",
            predicate="must attend",
            scope="must attend",
            full_span=(0, 25),
            variable_span=(4, 12),
            predicate_span=(13, 25)
        )
        
        claim, rationale = reduce_quantifiers(
            text="All students must attend",
            salt="test_salt",
            quantifier=quantifier
        )
        
        assert claim.symbol.startswith("R")
        assert "students" in claim.symbol
        assert "attend" in claim.symbol.lower()
        assert claim.text == "students must attend"
        assert claim.origin_spans == [(0, 25)]
        assert "representative instance" in rationale.lower()
    
    def test_existential_reduction(self):
        """Test reduction of existential quantifier."""
        quantifier = QuantifierStructure(
            quantifier_type="EXISTENTIAL",
            quantifier_text="some",
            variable="employees",
            predicate="passed the test",
            scope="passed the test",
            full_span=(0, 30),
            variable_span=(5, 14),
            predicate_span=(15, 30)
        )
        
        claim, rationale = reduce_quantifiers(
            text="Some employees passed the test",
            salt="test_salt",
            quantifier=quantifier
        )
        
        assert claim.symbol.startswith("E")
        assert "employees" in claim.symbol
        assert "existential witness" in rationale.lower()
    
    def test_negative_reduction(self):
        """Test reduction of negative quantifier."""
        quantifier = QuantifierStructure(
            quantifier_type="NEGATIVE",
            quantifier_text="no",
            variable="cars",
            predicate="are allowed",
            scope="are allowed",
            full_span=(0, 20),
            variable_span=(3, 7),
            predicate_span=(8, 20)
        )
        
        claim, rationale = reduce_quantifiers(
            text="No cars are allowed",
            salt="test_salt",
            quantifier=quantifier
        )
        
        assert claim.symbol.startswith("N")
        assert "cars" in claim.symbol
        assert "negated" in rationale.lower()
    
    def test_reduction_preserves_origin_spans(self):
        """Test that reduction preserves origin spans from quantifier."""
        quantifier = QuantifierStructure(
            quantifier_type="UNIVERSAL",
            quantifier_text="every",
            variable="participant",
            predicate="receives a badge",
            scope="receives a badge",
            full_span=(10, 40),  # Custom span
            variable_span=(16, 27),
            predicate_span=(28, 40)
        )
        
        claim, rationale = reduce_quantifiers(
            text="Every participant receives a badge",
            salt="test_salt",
            quantifier=quantifier
        )
        
        assert claim.origin_spans == [(10, 40)]


class TestPresuppositionDetection:
    """Test presupposition detection for common patterns."""
    
    def test_definiteness_presupposition(self):
        """Test detection of presupposition from definite description."""
        text = "The king of France is bald"
        presup = detect_presupposition(text)
        
        assert presup is not None
        assert presup.presupposition_type == "DEFINITENESS"
        assert "exists" in presup.implicit_claim.lower()
        assert "king" in presup.implicit_claim.lower()
    
    def test_factive_verb_presupposition(self):
        """Test detection of presupposition from factive verb."""
        text = "John knows that the earth is round"
        presup = detect_presupposition(text)
        
        assert presup is not None
        assert presup.presupposition_type == "FACTIVE"
        # Factive verbs presuppose their complement is true
    
    def test_change_of_state_presupposition(self):
        """Test detection of presupposition from change-of-state verb."""
        text = "Alice stopped smoking"
        presup = detect_presupposition(text)
        
        assert presup is not None
        assert presup.presupposition_type == "STATE_CHANGE"
        assert "smoking" in presup.implicit_claim.lower()
    
    def test_no_presupposition_simple_sentence(self):
        """Test that simple sentences don't trigger presupposition detection."""
        text = "The cat is sleeping"
        presup = detect_presupposition(text)
        
        # "The cat" might trigger definiteness, but simple cases should be handled
        # This test documents current behavior; may be refined later
        if presup:
            assert presup.presupposition_type == "DEFINITENESS"


class TestWorldConstruct:
    """Test the main world construction function."""
    
    def test_universal_quantifier_integration(self):
        """Test world construction with universal quantifier."""
        # Create a simple concision result with universal quantifier
        concision = ConcisionResult(
            canonical_text="All employees must submit timesheets",
            atomic_candidates=[
                AtomicClaim(
                    text="All employees must submit timesheets",
                    origin_spans=[(0, 37)]
                )
            ]
        )
        
        # Mock AgentContext (minimal for testing)
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        
        assert isinstance(result, ModuleResult)
        world_result = WorldResult(**result.payload)
        
        # Should have reduced the quantifier
        assert len(world_result.atomic_claims) >= 1
        assert any(
            claim.symbol and claim.symbol.startswith("R")
            for claim in world_result.atomic_claims
        )
        
        # Should have reduction metadata
        assert len(world_result.reduction_metadata) > 0
        
        # Should have quantifier map
        assert len(world_result.quantifier_map) > 0
    
    def test_existential_quantifier_integration(self):
        """Test world construction with existential quantifier."""
        concision = ConcisionResult(
            canonical_text="Some students passed the exam",
            atomic_candidates=[
                AtomicClaim(
                    text="Some students passed the exam",
                    origin_spans=[(0, 30)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        world_result = WorldResult(**result.payload)
        
        # Should have reduced the existential quantifier
        assert any(
            claim.symbol and claim.symbol.startswith("E")
            for claim in world_result.atomic_claims
        )
    
    def test_no_quantifier_passthrough(self):
        """Test that claims without quantifiers pass through unchanged."""
        concision = ConcisionResult(
            canonical_text="The cat is sleeping",
            atomic_candidates=[
                AtomicClaim(
                    text="The cat is sleeping",
                    origin_spans=[(0, 19)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        world_result = WorldResult(**result.payload)
        
        # Should pass through unchanged
        assert len(world_result.atomic_claims) == 1
        assert world_result.atomic_claims[0].text == "The cat is sleeping"
        
        # No reduction metadata
        assert len(world_result.reduction_metadata) == 0
    
    def test_multiple_claims_mixed(self):
        """Test world construction with mix of quantified and non-quantified claims."""
        concision = ConcisionResult(
            canonical_text="All students attend and the teacher supervises",
            atomic_candidates=[
                AtomicClaim(
                    text="All students attend",
                    origin_spans=[(0, 19)]
                ),
                AtomicClaim(
                    text="the teacher supervises",
                    origin_spans=[(24, 46)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        world_result = WorldResult(**result.payload)
        
        # Should have 2 claims
        assert len(world_result.atomic_claims) == 2
        
        # First should be reduced (universal quantifier)
        assert world_result.atomic_claims[0].symbol.startswith("R")
        
        # Second should be unchanged (no quantifier)
        assert world_result.atomic_claims[1].text == "the teacher supervises"
        
        # Should have 1 reduction
        assert len(world_result.reduction_metadata) == 1
    
    def test_determinism_same_salt(self):
        """Test that same input + salt produces same IDs (reproducibility)."""
        concision = ConcisionResult(
            canonical_text="All students must attend",
            atomic_candidates=[
                AtomicClaim(
                    text="All students must attend",
                    origin_spans=[(0, 24)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        # Run twice with same salt
        result1 = world_construct(concision, MockContext(), salt="salt123")
        result2 = world_construct(concision, MockContext(), salt="salt123")
        
        world1 = WorldResult(**result1.payload)
        world2 = WorldResult(**result2.payload)
        
        # Should produce identical symbols
        assert world1.atomic_claims[0].symbol == world2.atomic_claims[0].symbol
    
    def test_different_salt_different_ids(self):
        """Test that different salts produce different IDs."""
        concision = ConcisionResult(
            canonical_text="All students must attend",
            atomic_candidates=[
                AtomicClaim(
                    text="All students must attend",
                    origin_spans=[(0, 24)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        # Run with different salts
        result1 = world_construct(concision, MockContext(), salt="salt1")
        result2 = world_construct(concision, MockContext(), salt="salt2")
        
        world1 = WorldResult(**result1.payload)
        world2 = WorldResult(**result2.payload)
        
        # Should produce different symbols (different hash)
        assert world1.atomic_claims[0].symbol != world2.atomic_claims[0].symbol
    
    def test_presupposition_warning(self):
        """Test that presuppositions are detected and warned about."""
        concision = ConcisionResult(
            canonical_text="The king of France is bald",
            atomic_candidates=[
                AtomicClaim(
                    text="The king of France is bald",
                    origin_spans=[(0, 27)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        world_result = WorldResult(**result.payload)
        
        # Should have presupposition metadata
        assert len(world_result.presupposition_metadata) > 0
        
        # Should have warning about presupposition
        assert len(world_result.warnings) > 0
        assert any("presupposition" in w.lower() for w in world_result.warnings)
    
    def test_provenance_record_created(self):
        """Test that provenance record is properly created."""
        concision = ConcisionResult(
            canonical_text="All employees submit reports",
            atomic_candidates=[
                AtomicClaim(
                    text="All employees submit reports",
                    origin_spans=[(0, 29)]
                )
            ]
        )
        
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        
        # Should have provenance record
        assert result.provenance_record is not None
        assert result.provenance_record.module_id == "world_construct"
        assert result.provenance_record.module_version == "1.0.0"
        
        # Should have event log
        assert len(result.provenance_record.event_log) > 0
        
        # Should have reduction rationale
        assert result.provenance_record.reduction_rationale is not None
    
    def test_confidence_propagation(self):
        """Test that confidence is properly calculated and propagated."""
        concision = ConcisionResult(
            canonical_text="Every participant receives a certificate",
            atomic_candidates=[
                AtomicClaim(
                    text="Every participant receives a certificate",
                    origin_spans=[(0, 41)]
                )
            ],
            confidence=0.95
        )
        
        class MockContext:
            pass
        
        result = world_construct(concision, MockContext(), salt="test_salt")
        
        # Confidence should be based on quantifier detection confidence
        assert result.confidence > 0.0
        assert result.confidence <= 1.0


class TestReductionRationale:
    """Test creation of reduction rationale strings."""
    
    def test_universal_rationale(self):
        """Test rationale for universal quantifier reduction."""
        quantifier = QuantifierStructure(
            quantifier_type="UNIVERSAL",
            quantifier_text="all",
            variable="students",
            predicate="attend",
            scope="attend",
            full_span=(0, 18),
            variable_span=(4, 12),
            predicate_span=(13, 18)
        )
        
        rationale = create_reduction_rationale(quantifier, "R3a2f_students_attend")
        
        assert "universal" in rationale.lower()
        assert "all students" in rationale.lower()
        assert "R3a2f_students_attend" in rationale
        assert "representative instance" in rationale.lower()
    
    def test_existential_rationale(self):
        """Test rationale for existential quantifier reduction."""
        quantifier = QuantifierStructure(
            quantifier_type="EXISTENTIAL",
            quantifier_text="some",
            variable="employees",
            predicate="passed",
            scope="passed",
            full_span=(0, 20),
            variable_span=(5, 14),
            predicate_span=(15, 20)
        )
        
        rationale = create_reduction_rationale(quantifier, "E8b4c_employees_passed")
        
        assert "existential" in rationale.lower()
        assert "some employees" in rationale.lower()
        assert "existential witness" in rationale.lower()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_text(self):
        """Test behavior with empty text."""
        quantifier = detect_quantifier("")
        assert quantifier is None
    
    def test_whitespace_only(self):
        """Test behavior with whitespace-only text."""
        quantifier = detect_quantifier("   ")
        assert quantifier is None
    
    def test_very_long_variable(self):
        """Test sanitization of very long variable names."""
        id_str = generate_deterministic_id(
            text="All very_long_complex_variable_name_that_exceeds_normal_length attend",
            salt="test",
            quantifier_type="UNIVERSAL",
            variable="very_long_complex_variable_name_that_exceeds_normal_length",
            predicate="attend"
        )
        
        # Should be truncated to reasonable length
        assert len(id_str) < 100  # Reasonable upper bound
    
    def test_unicode_in_text(self):
        """Test handling of unicode characters."""
        id_str = generate_deterministic_id(
            text="All étudients must attend",
            salt="test",
            quantifier_type="UNIVERSAL",
            variable="étudients",
            predicate="must attend"
        )
        
        # Should handle unicode gracefully (may be sanitized)
        assert id_str.startswith("R")
    
    def test_nested_quantifiers(self):
        """Test that nested quantifiers are detected (at least outer)."""
        text = "All students who passed some tests receive awards"
        quantifier = detect_quantifier(text)
        
        # Should detect at least the outer quantifier
        assert quantifier is not None
        assert quantifier.quantifier_type == "UNIVERSAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
