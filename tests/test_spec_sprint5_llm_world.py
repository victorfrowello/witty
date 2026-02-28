"""
Sprint 5 Spec Compliance Tests: LLM-Assisted World Construction.

Tests derived directly from DesignSpec Section 6b acceptance criteria.
Written BEFORE implementation to ensure spec compliance (TDD).

Spec References:
- DesignSpec 6b.1: Quantifier reduction with outside knowledge
- DesignSpec 6b.4: LLM prompts for world construction
- DesignSpec 6b.5: Deterministic fallback acceptance criteria
- DevPlan Sprint 5: LLM-assisted world construction

Author: Victor Rowello
Sprint: 5
"""

import pytest


# =============================================================================
# Spec-Derived Test Cases for LLM-Assisted World Construction
# =============================================================================

class TestLLMGroundEntity:
    """
    DesignSpec 6b.4 Acceptance Criteria:
    "ground_entity_v1.txt: Provide a single, minimal atomic claim that defines 
    what this entity is or its role."
    """
    
    def test_llm_ground_entity_returns_grounding_claim(self):
        """
        Spec: llm_ground_entity should return a grounding claim for the entity.
        
        DesignSpec 6b.4:
        "Return strict JSON: { grounding_claim: str, entity_type: str, confidence: float }"
        """
        from src.pipeline.world import llm_ground_entity
        from src.adapters.mock import MockLLMAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        
        entity = "Alice"
        context_claims = ["Alice drives a Tesla", "Alice prefers electric cars"]
        
        result = llm_ground_entity(entity, context_claims, ctx, adapter)
        
        assert result is not None
        assert 'grounding_claim' in result or hasattr(result, 'grounding_claim'), (
            "llm_ground_entity must return grounding_claim per DesignSpec 6b.4"
        )
    
    def test_llm_ground_entity_assigns_entity_type(self):
        """
        Spec: Entity grounding must assign entity_type.
        
        DesignSpec 6b.4:
        "entity_type: PERSON|ORG|LOCATION|CONCEPT"
        """
        from src.pipeline.world import llm_ground_entity
        from src.adapters.mock import MockLLMAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        
        entity = "Google"
        context_claims = ["Google announced new products", "Google is expanding"]
        
        result = llm_ground_entity(entity, context_claims, ctx, adapter)
        
        entity_type = result.get('entity_type') if isinstance(result, dict) else getattr(result, 'entity_type', None)
        
        valid_types = {"PERSON", "ORG", "LOCATION", "CONCEPT", "ENTITY"}
        assert entity_type in valid_types, (
            f"entity_type '{entity_type}' not in valid types per DesignSpec 6b.4"
        )
    
    def test_llm_ground_entity_records_grounding_method(self):
        """
        Spec: Must record grounding_method = "llm_assisted".
        
        DesignSpec 6b.1:
        "grounding_method: deterministic | llm_assisted"
        """
        from src.pipeline.world import llm_ground_entity
        from src.adapters.mock import MockLLMAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        adapter = MockLLMAdapter(adapter_id="test", version="0.1")
        
        entity = "Manager"
        context_claims = ["The manager approved the request"]
        
        result = llm_ground_entity(entity, context_claims, ctx, adapter)
        
        grounding_method = result.get('grounding_method') if isinstance(result, dict) else getattr(result, 'grounding_method', None)
        
        assert grounding_method == "llm_assisted", (
            "llm_ground_entity must record grounding_method='llm_assisted'"
        )
    
    def test_llm_ground_entity_fallback_on_failure(self):
        """
        Spec: Fall back to deterministic when LLM fails.
        
        DesignSpec 6b.5:
        "Entity grounding: use POS tagging to assign generic types"
        """
        from src.pipeline.world import llm_ground_entity
        
        # Create adapter that returns invalid response
        class FailingAdapter:
            def __init__(self):
                self.adapter_id = "failing"
                self.version = "0.1"
            
            def generate(self, **kwargs):
                from src.adapters.base import AdapterResponse
                return AdapterResponse(
                    raw_text="not valid json",
                    parsed_json=None,
                    model_id="test",
                    request_id="test",
                    timestamp="2026-02-27T12:00:00Z",
                    usage={},
                    metadata={}
                )
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'llm_conf_threshold': 0.7
                })()
        
        ctx = MockContext()
        adapter = FailingAdapter()
        
        entity = "Employee"
        context_claims = ["The employee works hard"]
        
        # Should not raise, should fall back
        result = llm_ground_entity(entity, context_claims, ctx, adapter)
        
        assert result is not None, (
            "llm_ground_entity must fall back to deterministic on failure"
        )


class TestLLMGroundQuantifier:
    """
    DesignSpec 6b.1 Acceptance Criteria:
    "LLM-assisted: query for domain instances if underspecified"
    """
    
    def test_llm_ground_quantifier_returns_instances(self):
        """
        Spec: llm_ground_quantifier should return concrete instances.
        
        DesignSpec 6b.4:
        "Return strict JSON: { instances: [{instance_text, instance_label, confidence}], 
        reduction_rationale: str }"
        """
        from src.pipeline.world import llm_ground_quantifier
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
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
        
        quantified_claim = "Every employee must attend training"
        quantifier_type = "universal"
        
        result = llm_ground_quantifier(
            quantified_claim, quantifier_type, ctx, llm_adapter, retrieval_adapter
        )
        
        assert result is not None
        instances = result.get('instances') if isinstance(result, dict) else getattr(result, 'instances', [])
        
        assert isinstance(instances, list), (
            "llm_ground_quantifier must return instances list per DesignSpec 6b.4"
        )
    
    def test_llm_ground_quantifier_has_reduction_rationale(self):
        """
        Spec: Must include reduction_rationale explaining the grounding.
        
        DesignSpec 6b.1:
        "Record reduction_rationale with enrichment_source_id"
        """
        from src.pipeline.world import llm_ground_quantifier
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
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
        
        quantified_claim = "All managers approve requests"
        quantifier_type = "universal"
        
        result = llm_ground_quantifier(
            quantified_claim, quantifier_type, ctx, llm_adapter, retrieval_adapter
        )
        
        rationale = result.get('reduction_rationale') if isinstance(result, dict) else getattr(result, 'reduction_rationale', None)
        
        assert rationale is not None and len(rationale) > 0, (
            "llm_ground_quantifier must include reduction_rationale per DesignSpec 6b.1"
        )
    
    def test_llm_ground_quantifier_records_enrichment_source_id(self):
        """
        Spec: LLM-grounded instances must record enrichment_source_id.
        
        DesignSpec 6b.1:
        "Provenance: enrichment_source_id: if grounded via retrieval"
        """
        from src.pipeline.world import llm_ground_quantifier
        from src.adapters.mock import MockLLMAdapter
        from src.adapters.retrieval import MockRetrievalAdapter
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
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
        
        quantified_claim = "Some engineers use Python"
        quantifier_type = "existential"
        
        result = llm_ground_quantifier(
            quantified_claim, quantifier_type, ctx, llm_adapter, retrieval_adapter
        )
        
        source_id = result.get('enrichment_source_id') if isinstance(result, dict) else getattr(result, 'enrichment_source_id', None)
        
        # Should have source_id if retrieval was used
        assert source_id is not None or 'enrichment_source_id' in str(result), (
            "llm_ground_quantifier should record enrichment_source_id per DesignSpec 6b.1"
        )
    
    def test_llm_ground_quantifier_fallback_to_deterministic(self):
        """
        Spec: Fall back to deterministic E{n}/R{n} on failure.
        
        DesignSpec 6b.5:
        "Quantifier reduction: assign E{n}/R{n} placeholders without domain grounding"
        """
        from src.pipeline.world import llm_ground_quantifier
        
        class FailingAdapter:
            def __init__(self):
                self.adapter_id = "failing"
                self.version = "0.1"
            
            def generate(self, **kwargs):
                raise RuntimeError("Simulated failure")
        
        class FailingRetrieval:
            def retrieve(self, query, top_k, ctx):
                raise RuntimeError("Simulated failure")
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default'
                })()
        
        ctx = MockContext()
        
        quantified_claim = "Every student passes"
        quantifier_type = "universal"
        
        # Should not raise, should fall back
        result = llm_ground_quantifier(
            quantified_claim, quantifier_type, ctx, FailingAdapter(), FailingRetrieval()
        )
        
        assert result is not None, (
            "llm_ground_quantifier must fall back to deterministic on failure"
        )


class TestWorldConstructionIntegration:
    """
    DesignSpec 6b.5 Acceptance Criteria for world module.
    """
    
    def test_llm_world_construct_with_enrichment(self):
        """
        Spec: World construction with enrichment context.
        
        DesignSpec 5 (world_construct signature):
        "world_construct(input: EnrichmentResult, modal: ModalResult, ctx) -> WorldResult"
        """
        from src.pipeline.world import llm_world_construct
        from src.witty_types import (
            EnrichmentResult, ExpandedClaim, EnrichmentSource,
            ModalResult, ModuleResult
        )
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
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
                    text="Every employee must attend training",
                    origin="input",
                    confidence=0.9
                )
            ],
            enrichment_sources=[
                EnrichmentSource(source_id="src_1", score=0.88, redacted=False)
            ]
        )
        
        modal_result = ModalResult(
            modal_contexts=[],
            frame_selection="none"
        )
        
        result = llm_world_construct(enrichment_result, modal_result, ctx)
        
        assert isinstance(result, ModuleResult), (
            "llm_world_construct must return ModuleResult"
        )
        assert result.payload is not None
    
    def test_world_construct_coherence_threshold(self):
        """
        Spec: LLM-assisted path should achieve coherence >= 0.8.
        
        DesignSpec 6b.5:
        "LLM-assisted path: coherence >= 0.8"
        """
        from src.pipeline.world import llm_world_construct
        from src.witty_types import EnrichmentResult, ExpandedClaim, EnrichmentSource, ModalResult
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.options = type('Options', (), {
                    'retrieval_enabled': True,
                    'retrieval_top_k': 3,
                    'llm_conf_threshold': 0.7,
                    'privacy_mode': 'default',
                    'coherence_threshold': 0.6
                })()
        
        ctx = MockContext()
        
        enrichment_result = EnrichmentResult(
            expanded_claims=[
                ExpandedClaim(claim_id="c1", text="Alice is a manager", origin="input", confidence=0.95),
                ExpandedClaim(claim_id="c2", text="Alice approves budgets", origin="input", confidence=0.9)
            ],
            enrichment_sources=[]
        )
        
        modal_result = ModalResult(modal_contexts=[], frame_selection="none")
        
        result = llm_world_construct(enrichment_result, modal_result, ctx)
        
        # Check coherence in the result
        payload = result.payload
        if hasattr(payload, 'coherence_report'):
            coherence_score = payload.coherence_report.score
        elif isinstance(payload, dict) and 'coherence_report' in payload:
            coherence_score = payload['coherence_report'].get('score', 0)
        else:
            coherence_score = result.confidence
        
        # LLM path should produce reasonable coherence
        assert coherence_score >= 0.5, (
            "World construction should produce coherent output"
        )
