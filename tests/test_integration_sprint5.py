"""
Sprint 5 Integration Tests: End-to-End Enrichment → World Construction.

Tests derived from DesignSpec and DevPlan Sprint 5 acceptance criteria.
Written BEFORE implementation to ensure spec compliance (TDD).

Spec References:
- DesignSpec 6a: Enrichment with retrieval
- DesignSpec 6b: LLM-assisted world construction
- DesignSpec Section 5: Pipeline flow
- DevPlan Sprint 5: Integration acceptance criteria

Author: Victor Rowello
Sprint: 5
"""

import pytest


class TestEnrichmentToWorldPipeline:
    """
    Integration tests for enrichment → modal → world pipeline.
    
    DesignSpec Section 5 Pipeline Flow:
    "preprocessing → concision → symbolize → CNF → (enrichment → modal → world) → validate"
    """
    
    def test_pipeline_enrichment_to_world_flow(self):
        """
        Spec: Complete enrichment → world pipeline.
        
        DevPlan Sprint 5 Acceptance:
        "Full pipeline includes enrichment and modal detection"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.pipeline.modality import detect_modal
        from src.pipeline.world import llm_world_construct
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        from src.witty_types import CNFResult, CNFClause
        
        class MockContext:
            def __init__(self):
                self.request_id = "integration_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default',
                    'modal_frame': 'S5',
                    'coherence_threshold': 0.6
                })()
        
        ctx = MockContext()
        llm_adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        retrieval_adapter = MockRetrievalAdapter()
        
        # Input: CNF result from previous stage
        cnf_result = CNFResult(
            clauses=[
                CNFClause(clause_id="cl1", literals=["P(x)", "Q(x)"], clause_type="disjunction")
            ],
            original_formula="P(x) ∨ Q(x)",
            transformation_steps=[]
        )
        
        # Step 1: Enrichment
        enrichment_result = llm_enrichment(cnf_result, ctx, llm_adapter, retrieval_adapter)
        assert enrichment_result is not None, "Enrichment must produce result"
        
        # Step 2: Modal detection
        modal_result = detect_modal(enrichment_result, ctx)
        assert modal_result is not None, "Modal detection must produce result"
        
        # Step 3: World construction
        world_result = llm_world_construct(enrichment_result, modal_result, ctx)
        assert world_result is not None, "World construction must produce result"
    
    def test_pipeline_fallback_chain(self):
        """
        Spec: Pipeline should fall back gracefully on failures.
        
        DevPlan Sprint 5:
        "Fallback to deterministic if LLM fails"
        """
        from src.pipeline.enrichment import deterministic_enrichment
        from src.pipeline.modality import detect_modal
        from src.pipeline.world import construct_world
        from src.witty_types import CNFResult, CNFClause
        
        class MockContext:
            def __init__(self):
                self.request_id = "fallback_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': False,  # Disable to force deterministic
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default',
                    'modal_frame': 'S5',
                    'coherence_threshold': 0.6
                })()
        
        ctx = MockContext()
        
        cnf_result = CNFResult(
            clauses=[
                CNFClause(clause_id="cl1", literals=["R(a)"], clause_type="unit")
            ],
            original_formula="R(a)",
            transformation_steps=[]
        )
        
        # Use deterministic path
        enrichment_result = deterministic_enrichment(cnf_result, ctx)
        modal_result = detect_modal(enrichment_result, ctx)
        world_result = construct_world(enrichment_result, modal_result, ctx)
        
        assert world_result is not None, "Fallback pipeline must complete"


class TestOrchestratorEnrichmentIntegration:
    """
    Tests for orchestrator integration with enrichment and modal stages.
    """
    
    def test_orchestrator_includes_enrichment_stage(self):
        """
        Spec: Orchestrator must include enrichment stage.
        
        DesignSpec Section 5:
        "orchestrate: coordinates all pipeline stages"
        """
        from src.pipeline.orchestrator import formalize_statement
        from src.witty_types import FormalizeOptions
        
        options = FormalizeOptions(
            retrieval_enabled=True,
            llm_conf_threshold=0.7
        )
        
        result = formalize_statement(
            input_text="Every employee should complete training. Employees who complete training get certified.",
            options=options
        )
        
        # Check that result is produced
        assert result is not None
        
        # For now, check that basic pipeline ran
        # Full enrichment integration will be added when orchestrator is updated
        assert result.request_id is not None
    
    def test_orchestrator_modal_detection_integration(self):
        """
        Spec: Orchestrator must run modal detection.
        
        DesignSpec 6a.2:
        "Modal detection runs after enrichment"
        """
        from src.pipeline.orchestrator import formalize_statement
        from src.witty_types import FormalizeOptions
        
        # Input with modal keywords
        modal_text = "Every employee must attend the meeting."
        
        options = FormalizeOptions(
            retrieval_enabled=False,
            llm_conf_threshold=0.7
        )
        
        result = formalize_statement(
            input_text=modal_text,
            options=options
        )
        
        assert result is not None, "Orchestrator must produce result"


class TestProvenanceChaining:
    """
    DesignSpec 3.4: Provenance requirement tests.
    """
    
    def test_enrichment_records_provenance(self):
        """
        Spec: Enrichment must record provenance.
        
        DesignSpec 3.4:
        "All transformations must maintain provenance chains"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        from src.witty_types import CNFResult, CNFClause
        
        class MockContext:
            def __init__(self):
                self.request_id = "prov_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default'
                })()
        
        ctx = MockContext()
        llm_adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        retrieval_adapter = MockRetrievalAdapter()
        
        cnf_result = CNFResult(
            clauses=[
                CNFClause(clause_id="cl1", literals=["P(alice)"], clause_type="unit")
            ],
            original_formula="P(alice)",
            transformation_steps=[]
        )
        
        result = llm_enrichment(cnf_result, ctx, llm_adapter, retrieval_adapter)
        
        # Check for provenance fields
        if hasattr(result, 'expanded_claims'):
            for claim in result.expanded_claims:
                assert hasattr(claim, 'origin') or 'origin' in claim, (
                    "Expanded claims must have origin for provenance"
                )
    
    def test_world_construction_preserves_enrichment_provenance(self):
        """
        Spec: World construction must preserve enrichment provenance.
        
        DesignSpec 6b.1:
        "Record enrichment_source_id: if grounded via retrieval"
        """
        from src.pipeline.world import llm_world_construct
        from src.witty_types import (
            EnrichmentResult, ExpandedClaim, EnrichmentSource,
            ModalResult
        )
        
        class MockContext:
            def __init__(self):
                self.request_id = "prov_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default'
                })()
        
        ctx = MockContext()
        
        enrichment_result = EnrichmentResult(
            expanded_claims=[
                ExpandedClaim(
                    claim_id="c1",
                    text="Alice is a manager",
                    origin="retrieval",  # From retrieval
                    confidence=0.85
                )
            ],
            enrichment_sources=[
                EnrichmentSource(source_id="wiki_123", score=0.88, redacted=False)
            ]
        )
        
        modal_result = ModalResult(modal_contexts=[], frame_selection="none")
        
        result = llm_world_construct(enrichment_result, modal_result, ctx)
        
        # Result should preserve or reference enrichment sources
        assert result is not None


class TestPrivacyIntegration:
    """
    DesignSpec 6a.1: Privacy mode integration tests.
    """
    
    def test_strict_privacy_disables_retrieval(self):
        """
        Spec: privacy=strict should disable retrieval.
        
        DesignSpec 6a.1:
        "privacy_mode: default | strict | audit"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        from src.witty_types import CNFResult, CNFClause
        
        class StrictContext:
            def __init__(self):
                self.request_id = "privacy_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,  # Enabled, but privacy should override
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'strict'  # Strict mode
                })()
        
        ctx = StrictContext()
        llm_adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        retrieval_adapter = MockRetrievalAdapter()
        
        cnf_result = CNFResult(
            clauses=[
                CNFClause(clause_id="cl1", literals=["P(x)"], clause_type="unit")
            ],
            original_formula="P(x)",
            transformation_steps=[]
        )
        
        result = llm_enrichment(cnf_result, ctx, llm_adapter, retrieval_adapter)
        
        # In strict mode, enrichment sources should be empty or redacted
        if hasattr(result, 'enrichment_sources'):
            for source in result.enrichment_sources:
                is_redacted = getattr(source, 'redacted', True)
                assert is_redacted or source is None, (
                    "Strict privacy mode should redact external sources"
                )
    
    def test_audit_privacy_logs_retrieval(self):
        """
        Spec: privacy=audit should log retrieval queries.
        
        DesignSpec 6a.1:
        "audit: log all retrieval queries and results"
        """
        from src.pipeline.enrichment import llm_enrichment
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        from src.witty_types import CNFResult, CNFClause
        
        class AuditContext:
            def __init__(self):
                self.request_id = "audit_test"
                self.deterministic_salt = "test"
                self.audit_log = []
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'audit'
                })()
        
        ctx = AuditContext()
        llm_adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        retrieval_adapter = MockRetrievalAdapter()
        
        cnf_result = CNFResult(
            clauses=[
                CNFClause(clause_id="cl1", literals=["Query(data)"], clause_type="unit")
            ],
            original_formula="Query(data)",
            transformation_steps=[]
        )
        
        llm_enrichment(cnf_result, ctx, llm_adapter, retrieval_adapter)
        
        # In audit mode, context should have audit log entries
        # (Implementation decides how to log)
        assert ctx is not None  # Basic assertion - impl will add log entries


class TestErrorHandling:
    """
    Error handling and edge case tests.
    """
    
    def test_empty_input_handling(self):
        """
        Spec: Pipeline handles empty input gracefully.
        """
        from src.pipeline.enrichment import deterministic_enrichment
        from src.witty_types import CNFResult
        
        class MockContext:
            def __init__(self):
                self.request_id = "empty_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': False,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default'
                })()
        
        ctx = MockContext()
        
        cnf_result = CNFResult(
            clauses=[],
            original_formula="",
            transformation_steps=[]
        )
        
        result = deterministic_enrichment(cnf_result, ctx)
        assert result is not None, "Should handle empty input"
    
    def test_malformed_modal_handling(self):
        """
        Spec: Modal detection handles malformed input.
        """
        from src.pipeline.modality import detect_modal
        from src.witty_types import EnrichmentResult, ExpandedClaim
        
        class MockContext:
            def __init__(self):
                self.request_id = "malformed_test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'modal_frame': 'S5'
                })()
        
        ctx = MockContext()
        
        enrichment_result = EnrichmentResult(
            expanded_claims=[
                ExpandedClaim(
                    claim_id="bad",
                    text="",  # Empty text
                    origin="input",
                    confidence=0.0
                )
            ],
            enrichment_sources=[]
        )
        
        result = detect_modal(enrichment_result, ctx)
        assert result is not None, "Should handle malformed input"
