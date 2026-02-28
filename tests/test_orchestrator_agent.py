"""
Integration Tests for Agentic Orchestrator (Sprint 6).

Tests the WittyPipelineAgent with MockToolCallingModel to validate:
- Tool invocation and coordination
- Retry/fallback policy enforcement
- Provenance aggregation
- Different pipeline paths (simple, enrichment, modal)

Author: Victor Rowello
Sprint: 6
"""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone

from src.witty_types import FormalizeOptions, FormalizationResult
from src.pipeline.orchestrator import AgentContext
from src.pipeline.orchestrator_agent import (
    WittyPipelineAgent,
    AgentPolicy,
    formalize_with_agent,
)
from src.adapters.mock_agent_model import (
    MockToolCallingModel,
    MockScenario,
    MockToolCall,
    create_mock_model_for_input,
    create_custom_scenario,
    validate_smolagents_format,
    parse_tool_call_from_response,
    PIPELINE_SCENARIOS,
)


class TestMockToolCallingModel:
    """Tests for the MockToolCallingModel."""
    
    def test_model_returns_smolagents_format(self):
        """Model responses should be in valid smolagents format."""
        model = MockToolCallingModel(scenario="simple_statement")
        
        response = model(messages=[], tools=[])
        
        assert validate_smolagents_format(response)
        assert "Thought:" in response
        assert "Action:" in response
    
    def test_model_sequences_through_scenario(self):
        """Model should sequence through all tool calls in scenario."""
        model = MockToolCallingModel(scenario="simple_statement")
        scenario = PIPELINE_SCENARIOS["simple_statement"]
        
        for i, expected_tool_call in enumerate(scenario.tool_calls):
            response = model(messages=[], tools=[])
            parsed = parse_tool_call_from_response(response)
            
            assert parsed is not None
            assert parsed["tool_name"] == expected_tool_call.tool_name
        
        # Next call should be final answer
        response = model(messages=[], tools=[])
        assert "Final Answer:" in response
    
    def test_model_reset(self):
        """Model should reset to beginning of scenario."""
        model = MockToolCallingModel(scenario="simple_statement")
        
        # Make some calls
        model(messages=[], tools=[])
        model(messages=[], tools=[])
        assert model.call_index == 2
        
        # Reset
        model.reset()
        assert model.call_index == 0
        assert len(model.history) == 0
    
    def test_model_tracks_history(self):
        """Model should track call history."""
        model = MockToolCallingModel(scenario="simple_statement")
        
        model(messages=[{"role": "user", "content": "test"}], tools=[])
        model(messages=[], tools=[])
        
        history = model.get_call_history()
        assert len(history) == 2
        assert history[0]["call_index"] == 0
        assert history[1]["call_index"] == 1
    
    def test_custom_scenario(self):
        """Custom scenarios should work correctly."""
        scenario = create_custom_scenario([
            {"tool_name": "preprocess", "arguments": {"text": "test"}},
            {"tool_name": "symbolize", "arguments": {"input": "..."}}
        ], name="custom_test")
        
        model = MockToolCallingModel(scenario=scenario)
        
        response = model(messages=[], tools=[])
        parsed = parse_tool_call_from_response(response)
        
        assert parsed["tool_name"] == "preprocess"
    
    def test_factory_selects_modal_scenario(self):
        """Factory should select modal scenario for modal inputs."""
        model = create_mock_model_for_input("Alice must attend the meeting.")
        
        # First call should still be preprocess
        response = model(messages=[], tools=[])
        assert "preprocess" in response
    
    def test_factory_selects_enrichment_scenario(self):
        """Factory should select enrichment scenario for underspecified inputs."""
        model = create_mock_model_for_input("The prototype passed all tests.")
        
        assert model.scenario.name == "with_enrichment"


class TestWittyPipelineAgent:
    """Tests for the WittyPipelineAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a test agent with mock model."""
        return WittyPipelineAgent()
    
    @pytest.fixture
    def options(self):
        """Create test options."""
        return FormalizeOptions(reproducible_mode=True)
    
    def test_agent_creates_with_defaults(self):
        """Agent should create with default configuration."""
        agent = WittyPipelineAgent()
        
        assert agent.model is not None
        assert len(agent.tools) > 0
        assert agent.policy is not None
    
    def test_agent_has_all_pipeline_tools(self):
        """Agent should have all required pipeline tools."""
        agent = WittyPipelineAgent()
        
        required_tools = [
            "preprocess", "concision", "enrich", "detect_modal",
            "world_construct", "symbolize", "cnf_transform", "validate"
        ]
        
        for tool_name in required_tools:
            assert tool_name in agent.tool_map, f"Missing tool: {tool_name}"
    
    def test_run_simple_statement(self, agent, options):
        """Agent should formalize a simple statement."""
        result = agent.run("The sky is blue.", options)
        
        assert isinstance(result, FormalizationResult)
        assert result.original_text == "The sky is blue."
        assert result.request_id.startswith("agent_")
    
    def test_run_produces_atomic_claims(self, agent, options):
        """Agent should produce atomic claims."""
        result = agent.run("Alice likes cats and Bob likes dogs.", options)
        
        assert len(result.atomic_claims) >= 1
    
    def test_run_produces_legend(self, agent, options):
        """Agent should produce a symbol legend."""
        result = agent.run("If it rains then the match is cancelled.", options)
        
        assert len(result.legend) >= 1
        # Symbols should start with P
        for symbol in result.legend.keys():
            assert symbol.startswith("P")
    
    def test_run_produces_cnf(self, agent, options):
        """Agent should produce CNF representation."""
        result = agent.run("The cat sat on the mat.", options)
        
        # CNF string or clauses should exist
        assert result.cnf or result.cnf_clauses
    
    def test_run_records_invocation_history(self, agent, options):
        """Agent should record tool invocation history."""
        result = agent.run("Simple test.", options)
        
        history = agent.get_invocation_history()
        assert len(history) > 0
        
        # Should have at least preprocess, concision, symbolize
        tool_names = [inv["tool_name"] for inv in history]
        assert "preprocess" in tool_names
    
    def test_run_creates_provenance(self, agent, options):
        """Agent should create provenance records."""
        result = agent.run("Test statement.", options)
        
        assert len(result.provenance) > 0
        
        # Each provenance record should have required fields
        for prov in result.provenance:
            # prov is a ProvenanceRecord object, not a dict
            assert prov.id is not None
            assert prov.module_id is not None
            assert prov.event_log is not None
    
    def test_run_with_enrichment(self, options):
        """Agent should run enrichment when enabled."""
        options.retrieval_enabled = True
        agent = WittyPipelineAgent()
        
        result = agent.run("The prototype passed all safety tests.", options)
        
        assert isinstance(result, FormalizationResult)
        # Check enrichment was invoked
        history = agent.get_invocation_history()
        tool_names = [inv["tool_name"] for inv in history]
        assert "enrich" in tool_names


class TestAgentPolicy:
    """Tests for agent retry/fallback policy."""
    
    def test_default_policy(self):
        """Default policy should have sensible defaults."""
        policy = AgentPolicy()
        
        assert policy.max_retries == 1
        assert policy.confidence_threshold == 0.7
        assert policy.fallback_on_error is True
        assert policy.human_review_on_fallback is True
    
    def test_custom_policy(self):
        """Custom policy should override defaults."""
        policy = AgentPolicy(
            max_retries=3,
            confidence_threshold=0.9,
            fallback_on_error=False
        )
        
        assert policy.max_retries == 3
        assert policy.confidence_threshold == 0.9
        assert policy.fallback_on_error is False
    
    def test_agent_uses_policy(self):
        """Agent should use provided policy."""
        policy = AgentPolicy(max_retries=2)
        agent = WittyPipelineAgent(policy=policy)
        
        assert agent.policy.max_retries == 2


class TestToolWrappers:
    """Tests for individual tool wrappers."""
    
    @pytest.fixture
    def agent(self):
        """Create test agent."""
        return WittyPipelineAgent()
    
    def test_preprocess_tool(self, agent):
        """Preprocess tool should segment text."""
        tool = agent.tool_map["preprocess"]
        
        result = tool.forward(text="Hello world. How are you?")
        result_data = json.loads(result)
        
        assert result_data.get("success") is True
        assert "clauses" in result_data
        assert len(result_data["clauses"]) >= 1
    
    def test_concision_tool(self, agent):
        """Concision tool should extract atomic claims."""
        # First preprocess
        prep_tool = agent.tool_map["preprocess"]
        prep_result = prep_tool.forward(text="Alice likes cats.")
        
        # Then concision
        conc_tool = agent.tool_map["concision"]
        result = conc_tool.forward(preprocessing_result=prep_result)
        result_data = json.loads(result)
        
        assert result_data.get("success") is True
        assert "atomic_candidates" in result_data
    
    def test_modal_detection_tool(self, agent):
        """Modal detection tool should detect modalities."""
        # Preprocess and concision first
        prep_result = agent.tool_map["preprocess"].forward(
            text="Alice must attend the meeting."
        )
        conc_result = agent.tool_map["concision"].forward(
            preprocessing_result=prep_result
        )
        
        # Modal detection
        modal_tool = agent.tool_map["detect_modal"]
        result = modal_tool.forward(input_result=conc_result)
        result_data = json.loads(result)
        
        assert result_data.get("success") is True
        assert "has_modality" in result_data
    
    def test_symbolize_tool(self, agent):
        """Symbolize tool should assign symbols."""
        # Run through pipeline
        prep_result = agent.tool_map["preprocess"].forward(text="The sky is blue.")
        conc_result = agent.tool_map["concision"].forward(
            preprocessing_result=prep_result
        )
        
        # Symbolize
        sym_tool = agent.tool_map["symbolize"]
        result = sym_tool.forward(input_result=conc_result)
        result_data = json.loads(result)
        
        assert result_data.get("success") is True
        assert "legend" in result_data


class TestConvenienceFunction:
    """Tests for the formalize_with_agent convenience function."""
    
    def test_formalize_with_agent_basic(self):
        """Convenience function should return FormalizationResult."""
        result = formalize_with_agent("The cat sat on the mat.")
        
        assert isinstance(result, FormalizationResult)
        assert result.original_text == "The cat sat on the mat."
    
    def test_formalize_with_agent_with_options(self):
        """Convenience function should accept options."""
        options = FormalizeOptions(reproducible_mode=True)
        result = formalize_with_agent("Test.", options)
        
        assert isinstance(result, FormalizationResult)
    
    def test_formalize_with_agent_with_model(self):
        """Convenience function should accept custom model."""
        model = MockToolCallingModel(scenario="simple_statement")
        result = formalize_with_agent("Test.", model=model)
        
        assert isinstance(result, FormalizationResult)


class TestProvenanceTracking:
    """Tests for provenance tracking in agent execution."""
    
    @pytest.fixture
    def agent(self):
        """Create test agent."""
        return WittyPipelineAgent()
    
    def test_provenance_includes_tool_invocations(self, agent):
        """Provenance should include tool invocation records."""
        result = agent.run("Test statement.")
        
        # Check provenance has entries
        assert len(result.provenance) > 0
        
        # Check event_log structure - prov is ProvenanceRecord object
        for prov in result.provenance:
            event_log = prov.event_log
            assert len(event_log) > 0
            assert event_log[0].get("event_type") == "tool_invocation"
    
    def test_provenance_tracks_retries(self, agent):
        """Provenance should track retry attempts."""
        result = agent.run("Test.")
        
        # Get invocation history
        history = agent.get_invocation_history()
        
        for inv in history:
            assert "retries" in inv
            assert isinstance(inv["retries"], int)
    
    def test_provenance_tracks_fallback(self, agent):
        """Provenance should track fallback usage."""
        result = agent.run("Test.")
        
        history = agent.get_invocation_history()
        
        for inv in history:
            assert "used_fallback" in inv
            assert isinstance(inv["used_fallback"], bool)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_input(self):
        """Agent should handle empty input gracefully."""
        agent = WittyPipelineAgent()
        result = agent.run("")
        
        # Should still return a result, even if empty
        assert isinstance(result, FormalizationResult)
    
    def test_very_long_input(self):
        """Agent should handle long input."""
        agent = WittyPipelineAgent()
        long_text = "This is a test sentence. " * 100
        
        result = agent.run(long_text)
        
        assert isinstance(result, FormalizationResult)
    
    def test_special_characters(self):
        """Agent should handle special characters."""
        agent = WittyPipelineAgent()
        result = agent.run("Alice's cat isn't happy. Bob—unlike Alice—is content.")
        
        assert isinstance(result, FormalizationResult)
    
    def test_unicode_input(self):
        """Agent should handle unicode."""
        agent = WittyPipelineAgent()
        result = agent.run("The café serves crème brûlée.")
        
        assert isinstance(result, FormalizationResult)


class TestSmolagentsFormatValidation:
    """Tests for smolagents format compliance."""
    
    def test_tool_call_format(self):
        """Tool call format should match smolagents spec."""
        model = MockToolCallingModel()
        response = model(messages=[], tools=[])
        
        # Must have Thought, Action, Action Input
        assert "Thought:" in response
        assert "Action:" in response
        assert "Action Input:" in response
    
    def test_final_answer_format(self):
        """Final answer format should match smolagents spec."""
        model = MockToolCallingModel(scenario="simple_statement")
        
        # Exhaust tool calls
        for _ in range(len(PIPELINE_SCENARIOS["simple_statement"].tool_calls)):
            model(messages=[], tools=[])
        
        # Get final answer
        response = model(messages=[], tools=[])
        
        assert "Thought:" in response
        assert "Final Answer:" in response
    
    def test_action_input_is_valid_json(self):
        """Action Input should be valid JSON."""
        model = MockToolCallingModel()
        response = model(messages=[], tools=[])
        
        parsed = parse_tool_call_from_response(response)
        
        assert parsed is not None
        assert isinstance(parsed["arguments"], dict)


class TestIntegrationScenarios:
    """Integration tests for complete pipeline scenarios."""
    
    def test_simple_conditional(self):
        """Test formalization of a simple conditional."""
        agent = WittyPipelineAgent()
        result = agent.run("If it rains then the match is cancelled.")
        
        assert isinstance(result, FormalizationResult)
        assert len(result.legend) >= 1
    
    def test_conjunction(self):
        """Test formalization of a conjunction."""
        agent = WittyPipelineAgent()
        result = agent.run("Alice is tall and Bob is short.")
        
        assert isinstance(result, FormalizationResult)
        assert len(result.atomic_claims) >= 1
    
    def test_modal_statement(self):
        """Test formalization of a modal statement."""
        agent = WittyPipelineAgent()
        result = agent.run("Every employee must complete training.")
        
        assert isinstance(result, FormalizationResult)
        
        # Check modal detection was invoked
        history = agent.get_invocation_history()
        tool_names = [inv["tool_name"] for inv in history]
        assert "detect_modal" in tool_names
    
    def test_disjunction(self):
        """Test formalization of a disjunction."""
        agent = WittyPipelineAgent()
        result = agent.run("Either Alice wins or Bob wins.")
        
        assert isinstance(result, FormalizationResult)
    
    def test_negation(self):
        """Test formalization with negation."""
        agent = WittyPipelineAgent()
        result = agent.run("Alice is not happy.")
        
        assert isinstance(result, FormalizationResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
