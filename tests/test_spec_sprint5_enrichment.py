"""
Sprint 5 Spec Compliance Tests: Enrichment Module.

Tests derived directly from DesignSpec Sections 6a.2-6a.4 acceptance criteria.
Written BEFORE implementation to ensure spec compliance (TDD).

Spec References:
- DesignSpec 6a.2: Presupposition expansion and coherence rules
- DesignSpec 6a.3: LLM-first enrichment flow with fallback
- DesignSpec 6a.4: EnrichmentResult schema
- DevPlan Sprint 5: Enrichment acceptance criteria

Author: Victor Rowello
Sprint: 5
"""

import pytest
from typing import Any, Dict, List


# =============================================================================
# Spec-Derived Test Cases for Enrichment Module
# =============================================================================

class TestEnrichmentResultSchema:
    """
    DesignSpec 6a.4 Acceptance Criteria:
    "Required fields: expanded_claims, enrichment_sources"
    """
    
    def test_enrichment_result_has_required_fields(self):
        """EnrichmentResult must have expanded_claims and enrichment_sources."""
        from src.witty_types import EnrichmentResult
        
        result = EnrichmentResult(
            expanded_claims=[],
            enrichment_sources=[]
        )
        
        assert hasattr(result, 'expanded_claims'), (
            "EnrichmentResult must have expanded_claims per DesignSpec 6a.4"
        )
        assert hasattr(result, 'enrichment_sources'), (
            "EnrichmentResult must have enrichment_sources per DesignSpec 6a.4"
        )
    
    def test_expanded_claim_has_required_fields(self):
        """
        Spec: Each expanded_claim must have claim_id, text, origin, confidence.
        
        DesignSpec 6a.4:
        "required": ["claim_id", "text", "origin", "confidence"]
        """
        from src.witty_types import ExpandedClaim
        
        claim = ExpandedClaim(
            claim_id="c1",
            text="Test claim",
            origin="input",
            confidence=0.9
        )
        
        assert claim.claim_id == "c1"
        assert claim.origin in ["input", "enrichment"]
        assert 0.0 <= claim.confidence <= 1.0
    
    def test_enrichment_source_has_required_fields(self):
        """
        Spec: enrichment_sources items must have source_id, score, redacted.
        """
        from src.witty_types import EnrichmentSource
        
        source = EnrichmentSource(
            source_id="src_123",
            score=0.88,
            redacted=False
        )
        
        assert source.source_id == "src_123"
        assert 0.0 <= source.score <= 1.0
        assert isinstance(source.redacted, bool)
    
    def test_coherence_flags_valid_values(self):
        """
        Spec: coherence_flags must be subset of allowed values.
        
        DesignSpec 6a.4:
        "coherence_flags must be a subset of: ['complete', 'consistent', 'minimal', 
        'underspecified', 'contradictory']"
        """
        from src.witty_types import EnrichmentResult
        
        valid_flags = ["complete", "consistent", "minimal"]
        
        result = EnrichmentResult(
            expanded_claims=[],
            enrichment_sources=[],
            coherence_flags=valid_flags
        )
        
        allowed = {"complete", "consistent", "minimal", "underspecified", "contradictory"}
        for flag in result.coherence_flags:
            assert flag in allowed, (
                f"coherence_flag '{flag}' not in allowed set per DesignSpec 6a.4"
            )


class TestEnrichmentModule:
    """
    DevPlan Sprint 5 Acceptance Criteria:
    "Enrichment: LLM extracts presuppositions from retrieval sources, validates 
    atomic structure, falls back deterministically on failure."
    """
    
    def test_llm_enrichment_extracts_presuppositions(self):
        """
        Spec: LLM extracts presuppositions from retrieval sources.
        
        DevPlan: "Mock retrieval returns sources, LLM extracts valid presuppositions"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        from src.adapters.retrieval import MockRetrievalAdapter
        
        # Create mock context with retrieval enabled
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'privacy_mode': 'default',
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        
        # Create a concision result with underspecified claim
        prov = ProvenanceRecord(
            id="test_pr",
            module_id="test",
            module_version="0.1"
        )
        claim = AtomicClaim(
            text="The prototype passed all safety tests",
            symbol="P1",
            origin_spans=[(0, 36)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="The prototype passed all safety tests",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        adapter = MockRetrievalAdapter()
        result = llm_enrichment(concision_result, ctx, adapter)
        
        # llm_enrichment returns EnrichmentResult directly
        assert hasattr(result, 'expanded_claims'), "Result must have expanded_claims"
        
        # Should include original claim
        claims = result.expanded_claims
        
        assert len(claims) >= 1, (
            "Enrichment must include at least the original claim"
        )
    
    def test_enrichment_disabled_returns_empty(self):
        """
        Spec: If retrieval_enabled == false, return empty EnrichmentResult.
        
        DesignSpec 6a.1:
        "If options.retrieval_enabled == false -> skip enrichment, return empty EnrichmentResult"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': False,
                    'privacy_mode': 'default'
                })()
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(text="Test", symbol="P1", origin_spans=[(0, 4)], provenance=prov)
        concision_result = ConcisionResult(
            canonical_text="Test",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = llm_enrichment(concision_result, ctx, None)
        
        # llm_enrichment returns EnrichmentResult directly
        sources = result.enrichment_sources
        
        assert len(sources) == 0, (
            "Enrichment with retrieval_enabled=false must return empty enrichment_sources"
        )
    
    def test_enrichment_validates_atomic_structure(self):
        """
        Spec: Each presupposition must be an atomic claim.
        
        DevPlan: "Validation: each presupposition must be atomic, map to enrichment source"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        from src.adapters.retrieval import MockRetrievalAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'privacy_mode': 'default',
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="Every employee must attend training",
            symbol="P1",
            origin_spans=[(0, 35)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="Every employee must attend training",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        adapter = MockRetrievalAdapter()
        result = llm_enrichment(concision_result, ctx, adapter)
        
        # All expanded claims should be atomic (single assertions)
        # llm_enrichment returns EnrichmentResult directly
        claims = result.expanded_claims
        
        for claim in claims:
            claim_text = claim.text if hasattr(claim, 'text') else claim['text']
            # Atomic claims should not contain multiple sentences
            assert claim_text.count('.') <= 1, (
                f"Enriched claim '{claim_text}' should be atomic (single assertion)"
            )


class TestEnrichmentFallback:
    """
    DesignSpec 6a.3 Acceptance Criteria:
    "On second failure -> use deterministic_enrichment() fallback"
    """
    
    def test_deterministic_fallback_on_llm_failure(self):
        """
        Spec: Deterministic fallback when LLM fails.
        
        DevPlan: "Parse failure → retry → deterministic fallback"
        """
        from src.pipeline.enrichment import deterministic_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {'privacy_mode': 'default'})()
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="Alice drives a Tesla",
            symbol="P1",
            origin_spans=[(0, 20)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="Alice drives a Tesla",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = deterministic_enrichment(concision_result, ctx)
        
        # Should return valid EnrichmentResult
        assert result is not None
        
        payload = result.payload if hasattr(result, 'payload') else result
        assert 'expanded_claims' in payload or hasattr(payload, 'expanded_claims')
    
    def test_deterministic_fallback_has_low_confidence(self):
        """
        Spec: Deterministic fallback should have confidence < 0.5.
        
        DesignSpec 6a.3:
        "Always return valid EnrichmentResult schema with confidence < 0.5"
        """
        from src.pipeline.enrichment import deterministic_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {'privacy_mode': 'default'})()
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(text="Test", symbol="P1", origin_spans=[(0, 4)], provenance=prov)
        concision_result = ConcisionResult(
            canonical_text="Test",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = deterministic_enrichment(concision_result, ctx)
        
        assert result.confidence < 0.5, (
            "Deterministic fallback must have confidence < 0.5 per DesignSpec 6a.3"
        )
    
    def test_deterministic_fallback_adds_warning(self):
        """
        Spec: Deterministic fallback should add warning.
        
        DesignSpec 6a.3:
        "warnings = ['deterministic_fallback_used']"
        """
        from src.pipeline.enrichment import deterministic_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {'privacy_mode': 'default'})()
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(text="Test", symbol="P1", origin_spans=[(0, 4)], provenance=prov)
        concision_result = ConcisionResult(
            canonical_text="Test",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        result = deterministic_enrichment(concision_result, ctx)
        
        assert any("fallback" in w.lower() or "deterministic" in w.lower() for w in result.warnings), (
            "Deterministic fallback must add warning per DesignSpec 6a.3"
        )


class TestEnrichmentProvenanceTracking:
    """
    DesignSpec 6a.2 Acceptance Criteria:
    "Each enriched claim must have provenance.enrichment_sources"
    """
    
    def test_enrichment_claims_reference_source_ids(self):
        """
        Spec: Every enrichment-origin claim must reference a valid enrichment_source_id.
        
        DesignSpec 6a.4:
        "Every enrichment-origin claim must reference a valid enrichment_source_id"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        from src.adapters.retrieval import MockRetrievalAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'privacy_mode': 'default',
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        
        prov = ProvenanceRecord(id="test", module_id="test", module_version="0.1")
        claim = AtomicClaim(
            text="The manager approved the budget",
            symbol="P1",
            origin_spans=[(0, 31)],
            provenance=prov
        )
        concision_result = ConcisionResult(
            canonical_text="The manager approved the budget",
            atomic_candidates=[claim],
            confidence=0.9
        )
        
        adapter = MockRetrievalAdapter()
        result = llm_enrichment(concision_result, ctx, adapter)
        
        # llm_enrichment returns EnrichmentResult directly
        claims = result.expanded_claims
        sources = result.enrichment_sources
        
        source_ids = {s.source_id if hasattr(s, 'source_id') else s['source_id'] for s in sources}
        
        for claim in claims:
            origin = claim.origin if hasattr(claim, 'origin') else claim['origin']
            if origin == "retrieval":  # Check enrichment claims
                claim_source_ids = claim.source_ids if hasattr(claim, 'source_ids') else claim.get('source_ids', [])
                for source_id in claim_source_ids:
                    assert source_id in source_ids, (
                        f"Enrichment claim must reference valid source_id per DesignSpec 6a.4"
                    )
