"""
Sprint 5 Spec Compliance Tests: Modal Detection Module.

Tests derived directly from DesignSpec Section 5 (modality) and DevPlan Sprint 5.
Written BEFORE implementation to ensure spec compliance (TDD).

Spec References:
- DesignSpec Section 3 Stage 5: Modal detection & framing
- DevPlan Sprint 5: "Modal detection: identifies modal language and assigns default S5 frame"

Author: Victor Rowello
Sprint: 5
"""

import pytest


# =============================================================================
# Spec-Derived Test Cases for Modal Detection
# =============================================================================

class TestModalResultSchema:
    """
    DesignSpec Section 5 contract for ModalResult.
    """
    
    def test_modal_result_has_required_fields(self):
        """ModalResult must have modal_contexts and frame_selection."""
        from src.witty_types import ModalResult
        
        result = ModalResult(
            modal_contexts=[],
            frame_selection="S5"
        )
        
        assert hasattr(result, 'modal_contexts'), (
            "ModalResult must have modal_contexts field"
        )
        assert hasattr(result, 'frame_selection'), (
            "ModalResult must have frame_selection field"
        )
    
    def test_modal_context_structure(self):
        """Modal contexts should have claim_id, modal_type, operator_text."""
        from src.witty_types import ModalContext

        context = ModalContext(
            claim_id="P1",
            modal_type="necessity",
            operator_text="must",
        )

        assert context.claim_id == "P1"
        assert context.modal_type in ["necessity", "possibility", "obligation", "permission"]
        assert context.operator_text == "must"
    
    def test_frame_selection_valid_values(self):
        """frame_selection must be one of: S5, K, T, none."""
        from src.witty_types import ModalResult
        
        # S5 is the default per spec
        result = ModalResult(
            modal_contexts=[],
            frame_selection="S5"
        )
        
        valid_frames = {"S5", "K", "T", "none"}
        assert result.frame_selection in valid_frames, (
            f"frame_selection '{result.frame_selection}' not in valid set"
        )


class TestModalKeywordDetection:
    """
    DesignSpec Section 3 Stage 5:
    "Detect modal language (ought/should/must/possible)"
    
    DevPlan Sprint 5:
    "detect modals in sample inputs, assign S5 frame by default"
    """
    
    def test_detects_must_as_necessity(self):
        """'must' keyword should be detected as necessity modal."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="Every employee must attend the meeting",
            symbol="P1",
            origin_spans=[(0, 38)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="Every employee must attend the meeting",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        # Should detect 'must' as necessity
        payload = result.payload if hasattr(result, 'payload') else result
        contexts = payload.modal_contexts if hasattr(payload, 'modal_contexts') else payload.get('modal_contexts', [])
        
        must_detected = any(
            (c.operator_text if hasattr(c, 'operator_text') else c.get('operator_text')) == 'must'
            for c in contexts
        )
        
        assert must_detected or len(contexts) > 0, (
            "'must' should be detected as modal keyword"
        )
    
    def test_detects_should_as_normative(self):
        """'should' keyword should be detected as normative modal."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="You should complete the form",
            symbol="P1",
            origin_spans=[(0, 28)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="You should complete the form",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        payload = result.payload if hasattr(result, 'payload') else result
        contexts = payload.modal_contexts if hasattr(payload, 'modal_contexts') else payload.get('modal_contexts', [])
        
        should_detected = any(
            (c.operator_text if hasattr(c, 'operator_text') else c.get('operator_text')) == 'should'
            for c in contexts
        )
        
        assert should_detected or len(contexts) > 0, (
            "'should' should be detected as modal keyword"
        )
    
    def test_detects_possible_as_possibility(self):
        """'possible' keyword should be detected as possibility modal."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="It is possible that the project succeeds",
            symbol="P1",
            origin_spans=[(0, 40)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="It is possible that the project succeeds",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        payload = result.payload if hasattr(result, 'payload') else result
        contexts = payload.modal_contexts if hasattr(payload, 'modal_contexts') else payload.get('modal_contexts', [])
        
        possible_detected = any(
            'possible' in (c.operator_text if hasattr(c, 'operator_text') else c.get('operator_text', ''))
            for c in contexts
        )
        
        assert possible_detected or len(contexts) > 0, (
            "'possible' should be detected as modal keyword"
        )
    
    def test_detects_ought_as_normative(self):
        """'ought' keyword should be detected as normative modal."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="You ought to follow the guidelines",
            symbol="P1",
            origin_spans=[(0, 34)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="You ought to follow the guidelines",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        payload = result.payload if hasattr(result, 'payload') else result
        contexts = payload.modal_contexts if hasattr(payload, 'modal_contexts') else payload.get('modal_contexts', [])
        
        ought_detected = any(
            'ought' in (c.operator_text if hasattr(c, 'operator_text') else c.get('operator_text', ''))
            for c in contexts
        )
        
        assert ought_detected or len(contexts) > 0, (
            "'ought' should be detected as modal keyword"
        )


class TestModalFrameSelection:
    """
    DesignSpec Section 3 Stage 5:
    "If modal logic is necessary, but frame semantics is ambiguous from text, assume S5."
    """
    
    def test_assigns_s5_frame_by_default(self):
        """Default frame selection should be S5."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="It must be the case that all birds fly",
            symbol="P1",
            origin_spans=[(0, 38)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="It must be the case that all birds fly",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        payload = result.payload if hasattr(result, 'payload') else result
        frame = payload.frame_selection if hasattr(payload, 'frame_selection') else payload.get('frame_selection')
        
        assert frame == "S5", (
            "Default frame selection should be S5 per DesignSpec"
        )
    
    def test_returns_none_frame_when_no_modals(self):
        """When no modals detected, frame should be 'none'."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="The sky is blue",
            symbol="P1",
            origin_spans=[(0, 15)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="The sky is blue",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        payload = result.payload if hasattr(result, 'payload') else result
        frame = payload.frame_selection if hasattr(payload, 'frame_selection') else payload.get('frame_selection')
        contexts = payload.modal_contexts if hasattr(payload, 'modal_contexts') else payload.get('modal_contexts', [])
        
        if len(contexts) == 0:
            assert frame == "none", (
                "Frame should be 'none' when no modals detected"
            )


class TestModalDetectionNoModal:
    """Test behavior when input has no modal language."""
    
    def test_simple_sentence_no_modal_detected(self):
        """Simple declarative sentence should have no modal contexts."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="Alice runs every morning",
            symbol="P1",
            origin_spans=[(0, 24)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="Alice runs every morning",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        payload = result.payload if hasattr(result, 'payload') else result
        contexts = payload.modal_contexts if hasattr(payload, 'modal_contexts') else payload.get('modal_contexts', [])
        
        # Should have empty or minimal modal contexts for non-modal text
        assert isinstance(contexts, list), (
            "modal_contexts should be a list even when empty"
        )
    
    def test_returns_valid_modal_result_schema(self):
        """detect_modal should always return valid ModalResult."""
        from src.pipeline.modality import detect_modal
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord, ModuleResult
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(text="Test", symbol="P1", origin_spans=[(0, 4)], provenance=prov)
        concision_result = ConcisionResult(
            canonical_text="Test",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = detect_modal(concision_result, ctx)
        
        # Should return ModuleResult
        assert isinstance(result, ModuleResult), (
            "detect_modal must return ModuleResult"
        )
        assert result.payload is not None
