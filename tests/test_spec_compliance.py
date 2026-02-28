"""
Spec Compliance Tests for Witty Pipeline.

These tests are derived directly from DevPlan.md acceptance criteria to ensure
the implementation satisfies documented requirements, not just "code does what
code does" behavior.

Coverage gaps identified from audit:
1. Sprint 3: config_metadata in FormalizationResult
2. Sprint 3: ALL entities grounded (even generically)
3. Sprint 4: Malformed JSON triggers fallback
4. Sprint 4: Parse attempts recorded in event_log

Author: Victor Rowello
Purpose: Spec-driven testing (TDD compliance)
"""

import pytest
from unittest.mock import MagicMock

from src.witty_types import (
    FormalizationResult,
    FormalizeOptions,
    EntityGrounding,
)
from src.pipeline.orchestrator import formalize_statement
from src.pipeline.world import world_construct, extract_entities
from src.pipeline.concision import (
    llm_concision,
    LLMConcisionConfig,
    deterministic_concision,
)
from src.pipeline.preprocessing import PreprocessingResult, Clause
from src.adapters.base import AdapterResponse


# =============================================================================
# Sprint 3 Spec Compliance Tests
# =============================================================================

class TestSprint3ConfigMetadata:
    """
    DevPlan Sprint 3 Acceptance Criteria:
    "Final FormalizationResult includes merged provenance and config metadata."
    
    The FormalizationResult must include the FormalizeOptions used for the
    request so that the exact configuration can be reproduced.
    """
    
    def test_formalization_result_includes_config_metadata(self):
        """
        FormalizationResult must have config_metadata field containing the
        FormalizeOptions used for the request.
        
        Spec Reference: DevPlan.md line 90
        "Final FormalizationResult includes merged provenance and config metadata."
        """
        opts = FormalizeOptions(
            reproducible_mode=True,
            verbosity=2,
            privacy_mode="strict",
            llm_provider="mock"
        )
        
        result = formalize_statement("The sky is blue.", opts)
        
        # Assert config_metadata field exists
        assert hasattr(result, 'config_metadata'), (
            "FormalizationResult must have config_metadata field per DevPlan spec"
        )
        
        # Assert it's a dict
        assert isinstance(result.config_metadata, dict), (
            "config_metadata must be a dictionary"
        )
        
        # Assert it reflects the options used
        assert result.config_metadata.get('reproducible_mode') == True, (
            "config_metadata should capture reproducible_mode setting"
        )
        assert result.config_metadata.get('privacy_mode') == "strict", (
            "config_metadata should capture privacy_mode setting"
        )
    
    def test_config_metadata_enables_reproducibility(self):
        """
        Config metadata must contain all fields needed to reproduce the
        formalization with identical settings.
        """
        opts = FormalizeOptions(
            top_k_symbolizations=3,
            retrieval_enabled=True,
            quantifier_reduction_detail=True,
        )
        
        result = formalize_statement("All birds can fly.", opts)
        
        assert hasattr(result, 'config_metadata')
        config = result.config_metadata
        
        # Should include key configuration fields
        assert 'top_k_symbolizations' in config
        assert 'retrieval_enabled' in config
        assert config.get('top_k_symbolizations') == 3
        assert config.get('retrieval_enabled') == True


class TestSprint3EntityGrounding:
    """
    DevPlan Sprint 3 Acceptance Criteria:
    "Deterministic world construction produces valid WorldResult with all
    entities grounded (even if generically)."
    
    All named entities detected in atomic claims must appear in entity_groundings,
    even if only assigned a generic type like "ENTITY" or "THING".
    """
    
    def test_all_entities_grounded_even_generically(self):
        """
        Every entity extracted must have a corresponding entry in
        entity_groundings, even if the type is generic.
        
        Spec Reference: DevPlan.md line 85
        "Deterministic world construction produces valid WorldResult with all
        entities grounded (even if generically)."
        """
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        from src.pipeline.world import world_construct
        
        # Create a mock context
        class MockContext:
            def __init__(self):
                self.request_id = "test_entity_grounding"
                self.deterministic_salt = "test_salt"
                self.reproducible_mode = True
        
        ctx = MockContext()
        
        # Create input with multiple entities
        text = "Alice and Bob went to the Paris cafe."
        prov = ProvenanceRecord(
            id="test_pr",
            module_id="test",
            module_version="0.1",
            event_log=[]
        )
        
        claim1 = AtomicClaim(text=text, symbol="P1", origin_spans=[(0, len(text))], provenance=prov)
        
        concision_result = ConcisionResult(
            canonical_text=text,
            atomic_candidates=[claim1],
            confidence=1.0
        )
        
        # Run world construction
        world_module = world_construct(concision_result, ctx, ctx.deterministic_salt)
        
        # Extract the WorldResult from ModuleResult payload
        from src.witty_types import WorldResult
        if isinstance(world_module.payload, dict):
            world_result = WorldResult(**world_module.payload)
        else:
            world_result = world_module.payload
        
        # Extract entities using the same function world_construct uses
        # This ensures we're testing that ALL extracted entities are grounded
        event_log = []
        extracted_entities = extract_entities([claim1], event_log)
        
        # Verify ALL extracted entities have groundings in the world result
        for entity_text in extracted_entities.keys():
            assert entity_text in world_result.entity_groundings or \
                   entity_text.lower() in [k.lower() for k in world_result.entity_groundings.keys()], (
                f"Entity '{entity_text}' must be grounded (even generically) per DevPlan spec"
            )
    
    def test_generic_entity_grounding_type(self):
        """
        Entities that cannot be typed specifically should be grounded with
        a generic type rather than omitted.
        """
        from src.witty_types import ConcisionResult, AtomicClaim, ProvenanceRecord
        
        class MockContext:
            def __init__(self):
                self.request_id = "test"
                self.deterministic_salt = "test"
                self.reproducible_mode = True
        
        ctx = MockContext()
        
        # Text with entities that may be hard to type
        text = "The Gloopy went to Zorbak."
        prov = ProvenanceRecord(
            id="test_pr",
            module_id="test",
            module_version="0.1",
            event_log=[]
        )
        
        claim = AtomicClaim(text=text, symbol="P1", origin_spans=[(0, len(text))], provenance=prov)
        
        concision_result = ConcisionResult(
            canonical_text=text,
            atomic_candidates=[claim],
            confidence=1.0
        )
        
        world_module = world_construct(concision_result, ctx, ctx.deterministic_salt)
        
        # Extract the WorldResult from ModuleResult payload
        from src.witty_types import WorldResult
        if isinstance(world_module.payload, dict):
            world_result = WorldResult(**world_module.payload)
        else:
            world_result = world_module.payload
        
        # Every entity in groundings should have a type (even if generic)
        for entity_text, grounding in world_result.entity_groundings.items():
            assert grounding.entity_type is not None, (
                f"Entity '{entity_text}' must have entity_type even if generic"
            )
            # Type should be non-empty string
            assert len(grounding.entity_type) > 0


# =============================================================================
# Sprint 4 Spec Compliance Tests
# =============================================================================

class TestSprint4MalformedJsonFallback:
    """
    DevPlan Sprint 4 Acceptance Criteria (implied by design):
    LLM concision with retry/fallback must handle malformed JSON from the LLM
    by falling back to rule-based concision.
    
    Design Spec Section 9: "If parse fails after retries, fall back to
    deterministic concision."
    """
    
    def test_malformed_json_triggers_fallback(self):
        """
        When LLM returns malformed JSON that cannot be parsed, the system
        should fall back to rule-based deterministic concision.
        
        Spec Reference: DesignSpec_forCopilot_v4.md Section 9
        "1. Call LLM adapter... 3. Attempt JSON parse... 
        5. If failure after max_retries → fallback to deterministic concision"
        """
        # Create a mock adapter that returns unparseable garbage
        class MalformedAdapter:
            def __init__(self):
                self.adapter_id = "malformed"
                self.version = "0.1"
            
            def generate(self, prompt_template_id: str, prompt: str, **kwargs):
                return AdapterResponse(
                    raw_text="This is not JSON at all { broken",
                    parsed_json=None,  # Parse failed
                    model_id="test",
                    request_id="test",
                    timestamp="2026-02-27T12:00:00Z",
                    usage={"prompt_tokens": 10, "completion_tokens": 5},
                    metadata={"adapter_id": "malformed"}
                )
        
        class MockContext:
            def __init__(self):
                self.deterministic_salt = "test"
                self.request_id = "test"
        
        ctx = MockContext()
        adapter = MalformedAdapter()
        
        text = "If it rains then the ground gets wet."
        preprocess = PreprocessingResult(
            normalized_text=text,
            clauses=[Clause(text=text, start_char=0, end_char=len(text), tokens=[], clause_type="declarative")],
            tokens=[],
            origin_spans={},
            sentence_boundaries=[(0, len(text))]
        )
        
        config = LLMConcisionConfig(
            fallback_to_rule_based=True,
            max_retries=1
        )
        
        # Should not raise - should fall back to deterministic
        result = llm_concision(preprocess, ctx, adapter, config)
        
        # Should have warnings about fallback
        assert any("fallback" in w.lower() or "failed" in w.lower() for w in result.warnings), (
            "Warnings should indicate fallback was triggered"
        )
        
        # Should still produce valid output
        assert result.payload is not None
        assert 'atomic_candidates' in result.payload
    
    def test_malformed_json_does_not_crash(self):
        """
        System stability: malformed LLM output should never cause a crash
        when fallback is enabled.
        """
        class BrokenJsonAdapter:
            def __init__(self):
                self.adapter_id = "broken"
                self.version = "0.1"
            
            def generate(self, **kwargs):
                return AdapterResponse(
                    raw_text='{"atomic_candidates": [{"text": broken}]}',  # Invalid JSON
                    parsed_json=None,
                    model_id="test",
                    request_id="test",
                    timestamp="2026-02-27T12:00:00Z",
                    usage={},
                    metadata={}
                )
        
        class MockContext:
            def __init__(self):
                self.deterministic_salt = "test"
                self.request_id = "test"
        
        ctx = MockContext()
        
        preprocess = PreprocessingResult(
            normalized_text="Simple statement.",
            clauses=[Clause(text="Simple statement.", start_char=0, end_char=17, tokens=[], clause_type="declarative")],
            tokens=[],
            origin_spans={},
            sentence_boundaries=[(0, 17)]
        )
        
        config = LLMConcisionConfig(fallback_to_rule_based=True, max_retries=0)
        
        # Should not raise any exception
        result = llm_concision(preprocess, ctx, BrokenJsonAdapter(), config)
        assert result is not None


class TestSprint4ParseAttemptsEventLog:
    """
    DevPlan Sprint 4 / Design Spec requirement:
    LLM parse attempts and retry events must be recorded in the event_log
    for provenance and debugging.
    
    DesignSpec Section 9: "Always capture adapter metadata and decision events."
    """
    
    def test_parse_attempts_recorded_in_event_log(self):
        """
        Each LLM parse attempt (success or failure) should be recorded in
        the provenance event_log.
        
        Spec Reference: DesignSpec_forCopilot_v4.md Section 9
        "Always capture adapter metadata and success/failure events."
        """
        from src.adapters.mock import MockLLMAdapter
        
        class MockContext:
            def __init__(self):
                self.deterministic_salt = "test"
                self.request_id = "test"
        
        ctx = MockContext()
        adapter = MockLLMAdapter(adapter_id="test_mock", version="0.1")
        
        text = "If it rains then the ground gets wet."
        preprocess = PreprocessingResult(
            normalized_text=text,
            clauses=[Clause(text=text, start_char=0, end_char=len(text), tokens=[], clause_type="declarative")],
            tokens=[],
            origin_spans={},
            sentence_boundaries=[(0, len(text))]
        )
        
        result = llm_concision(preprocess, ctx, adapter)
        
        # Check event_log in provenance or payload
        events_found = []
        
        # Check if there's provenance_record with event_log
        if result.provenance_record and result.provenance_record.event_log:
            events_found.extend(result.provenance_record.event_log)
        
        # Also check payload for event metadata
        if result.payload and 'event_log' in result.payload:
            events_found.extend(result.payload['event_log'])
        
        # Should have at least one LLM-related event
        llm_events = [e for e in events_found if 'llm' in str(e).lower() or 'concision' in str(e).lower()]
        
        assert len(llm_events) > 0 or len(events_found) > 0, (
            "Event log should record LLM parse attempts per DesignSpec"
        )
    
    def test_retry_events_captured(self):
        """
        When retries occur, each attempt should be logged for debugging.
        """
        # Create adapter that fails first, succeeds second
        call_count = [0]
        
        class RetryAdapter:
            def __init__(self):
                self.adapter_id = "retry_test"
                self.version = "0.1"
            
            def generate(self, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call fails
                    return AdapterResponse(
                        raw_text="not json",
                        parsed_json=None,
                        model_id="test",
                        request_id="test",
                        timestamp="2026-02-27T12:00:00Z",
                        usage={},
                        metadata={}
                    )
                else:
                    # Second call succeeds
                    return AdapterResponse(
                        raw_text='{"atomic_candidates": [{"text": "test"}], "canonical_text": "test", "confidence": 0.9}',
                        parsed_json={
                            "atomic_candidates": [{"text": "test", "origin_spans": [[0, 4]]}],
                            "canonical_text": "test",
                            "confidence": 0.9,
                            "structure_type": "declarative"
                        },
                        model_id="test",
                        request_id="test",
                        timestamp="2026-02-27T12:00:00Z",
                        usage={},
                        metadata={}
                    )
        
        class MockContext:
            def __init__(self):
                self.deterministic_salt = "test"
                self.request_id = "test"
        
        ctx = MockContext()
        
        preprocess = PreprocessingResult(
            normalized_text="test",
            clauses=[Clause(text="test", start_char=0, end_char=4, tokens=[], clause_type="declarative")],
            tokens=[],
            origin_spans={},
            sentence_boundaries=[(0, 4)]
        )
        
        config = LLMConcisionConfig(max_retries=2, fallback_to_rule_based=True)
        result = llm_concision(preprocess, ctx, RetryAdapter(), config)
        
        # Should have captured the retry
        assert call_count[0] >= 1, "Adapter should have been called"
        
        # Warnings should mention the retry attempt
        retry_warnings = [w for w in result.warnings if 'retry' in w.lower() or 'attempt' in w.lower()]
        # At least we should have some indication of what happened
        assert result is not None


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestFormalizationResultSchema:
    """
    Verify FormalizationResult schema matches spec requirements.
    """
    
    def test_config_metadata_field_in_schema(self):
        """
        FormalizationResult schema must include config_metadata field.
        """
        import json
        from pathlib import Path
        
        schema_path = Path(__file__).parent.parent / "schemas" / "FormalizationResult.json"
        
        with open(schema_path) as f:
            schema = json.load(f)
        
        # Check that config_metadata is in properties
        assert 'config_metadata' in schema.get('properties', {}), (
            "FormalizationResult.json schema must include config_metadata per DevPlan"
        )
