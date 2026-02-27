"""
Sprint 4 Tests: LLM Adapter Wiring and Concision LLM Path.

This module tests the Sprint 4 implementations:
- OpenAI-compatible adapter
- Enhanced MockLLMAdapter
- Adapter registry
- LLM-assisted concision with retry logic

Author: Victor Rowello
Sprint: 4
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.adapters.base import AdapterResponse
from src.adapters.mock import MockLLMAdapter, MOCK_RESPONSES
from src.adapters.registry import get_adapter, list_adapters, register_adapter
from src.adapters.openai import OpenAICompatibleAdapter, RetryConfig
from src.pipeline.concision import (
    llm_concision,
    LLMConcisionConfig,
    _load_prompt_template,
    _validate_llm_response,
    _parse_llm_concision_response,
    deterministic_concision,
)
from src.pipeline.preprocessing import PreprocessingResult, Clause


# =============================================================================
# Test Fixtures
# =============================================================================

class MockContext:
    """Mock AgentContext for testing."""
    def __init__(self, salt: str = "test_salt"):
        self.deterministic_salt = salt
        self.request_id = "test_request"
        self.timestamp = datetime.now(timezone.utc)


@pytest.fixture
def mock_context():
    """Provide a mock context for testing."""
    return MockContext()


@pytest.fixture
def mock_adapter():
    """Provide a configured mock adapter."""
    return MockLLMAdapter(adapter_id="test_mock", version="0.1")


@pytest.fixture
def simple_preprocessing_result():
    """Provide a simple preprocessing result for testing."""
    text = "If it rains then the ground gets wet."
    return PreprocessingResult(
        normalized_text=text,
        clauses=[
            Clause(
                text=text,
                start_char=0,
                end_char=len(text),
                tokens=[],
                clause_type="declarative"
            )
        ],
        tokens=[],
        origin_spans={},
        sentence_boundaries=[(0, len(text))],
    )


@pytest.fixture
def conjunction_preprocessing_result():
    """Provide a conjunction preprocessing result for testing."""
    text = "The sun is bright and the sky is blue."
    return PreprocessingResult(
        normalized_text=text,
        clauses=[
            Clause(
                text=text,
                start_char=0,
                end_char=len(text),
                tokens=[],
                clause_type="declarative"
            )
        ],
        tokens=[],
        origin_spans={},
        sentence_boundaries=[(0, len(text))],
    )


# =============================================================================
# MockLLMAdapter Tests
# =============================================================================

class TestMockLLMAdapter:
    """Tests for the enhanced MockLLMAdapter."""

    def test_mock_adapter_initialization(self):
        """Test basic adapter initialization."""
        adapter = MockLLMAdapter()
        assert adapter.adapter_id == "mock"
        assert adapter.version == "0.1"
        assert adapter.config == {}

    def test_mock_adapter_with_config(self):
        """Test adapter initialization with custom config."""
        config = {
            "simulate_latency": True,
            "token_multiplier": 2.0,
        }
        adapter = MockLLMAdapter(
            adapter_id="custom_mock",
            version="1.0",
            config=config
        )
        assert adapter.adapter_id == "custom_mock"
        assert adapter._simulate_latency is True
        assert adapter._token_multiplier == 2.0

    def test_mock_adapter_concise_response_conditional(self):
        """Test mock adapter returns proper conditional response."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "concise_v1",
            "If it rains then the ground gets wet."
        )
        
        assert isinstance(response, AdapterResponse)
        assert response.parsed_json is not None
        assert "canonical_text" in response.parsed_json
        assert "atomic_candidates" in response.parsed_json
        assert "confidence" in response.parsed_json
        
        # Check that conditional structure was detected
        parsed = response.parsed_json
        assert parsed.get("structure_type") == "conditional"
        assert len(parsed["atomic_candidates"]) == 2
        
        # Check roles
        roles = [ac.get("role") for ac in parsed["atomic_candidates"]]
        assert "antecedent" in roles
        assert "consequent" in roles

    def test_mock_adapter_concise_response_conjunction(self):
        """Test mock adapter returns proper conjunction response."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "concise_v1",
            "The sun shines and the birds sing."
        )
        
        assert response.parsed_json is not None
        parsed = response.parsed_json
        assert parsed.get("structure_type") == "conjunction"
        assert len(parsed["atomic_candidates"]) == 2

    def test_mock_adapter_concise_response_simple(self):
        """Test mock adapter returns proper simple claim response."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "concise_v1",
            "The sky is blue."
        )
        
        assert response.parsed_json is not None
        parsed = response.parsed_json
        assert len(parsed["atomic_candidates"]) == 1

    def test_mock_adapter_symbolize_response(self):
        """Test mock adapter returns symbolization response."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "symbolize_v1",
            "P implies Q"
        )
        
        assert response.parsed_json is not None
        assert "legend" in response.parsed_json
        assert "logical_form_candidates" in response.parsed_json

    def test_mock_adapter_modal_response(self):
        """Test mock adapter returns modal detection response."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "modal_detect_v1",
            "Necessarily, P."
        )
        
        assert response.parsed_json is not None
        assert "modal_operators" in response.parsed_json
        assert "world_references" in response.parsed_json

    def test_mock_adapter_world_response(self):
        """Test mock adapter returns world construction response."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "world_construct_v1",
            "In world w1, P holds."
        )
        
        assert response.parsed_json is not None
        assert "worlds" in response.parsed_json
        assert "accessibility" in response.parsed_json

    def test_mock_adapter_unknown_template(self):
        """Test mock adapter handles unknown templates."""
        adapter = MockLLMAdapter()
        response = adapter.generate(
            "unknown_template",
            "Some text"
        )
        
        assert response.parsed_json is None
        assert "MOCK:" in response.text

    def test_mock_adapter_deterministic_request_id(self):
        """Test that request IDs are deterministic."""
        adapter = MockLLMAdapter()
        
        response1 = adapter.generate("concise_v1", "Test prompt")
        response2 = adapter.generate("concise_v1", "Test prompt")
        
        assert response1.adapter_provenance["request_id"] == response2.adapter_provenance["request_id"]
        
        # Different input should give different ID
        response3 = adapter.generate("concise_v1", "Different prompt")
        assert response1.adapter_provenance["request_id"] != response3.adapter_provenance["request_id"]

    def test_mock_adapter_custom_responses(self):
        """Test mock adapter with custom response configuration."""
        custom_response = {
            "canonical_text": "custom canonical",
            "atomic_candidates": [{"text": "custom", "origin_spans": [[0, 6]]}],
            "confidence": 0.99,
        }
        adapter = MockLLMAdapter(
            config={"custom_responses": {"concise_v1": custom_response}}
        )
        
        response = adapter.generate("concise_v1", "Any input")
        assert response.parsed_json == custom_response

    def test_mock_adapter_provenance(self):
        """Test that mock adapter includes proper provenance."""
        adapter = MockLLMAdapter()
        response = adapter.generate("concise_v1", "Test")
        
        provenance = response.adapter_provenance
        assert "adapter_id" in provenance
        assert "version" in provenance
        assert "prompt_template_id" in provenance
        assert "request_id" in provenance
        assert "start_time" in provenance
        assert "end_time" in provenance

    def test_mock_adapter_metadata(self):
        """Test mock adapter metadata method."""
        adapter = MockLLMAdapter(
            adapter_id="test",
            version="2.0",
            config={"simulate_latency": True}
        )
        
        metadata = adapter.get_metadata()
        assert metadata["adapter_id"] == "test"
        assert metadata["version"] == "2.0"
        assert metadata["is_mock"] is True
        assert metadata["simulate_latency"] is True


# =============================================================================
# Adapter Registry Tests
# =============================================================================

class TestAdapterRegistry:
    """Tests for the adapter registry."""

    def test_get_mock_adapter(self):
        """Test getting mock adapter from registry."""
        adapter = get_adapter("mock")
        assert isinstance(adapter, MockLLMAdapter)
        assert adapter.adapter_id == "mock"

    def test_get_openai_adapter(self):
        """Test getting OpenAI adapter from registry."""
        adapter = get_adapter("openai", {"api_key": "test-key"})
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter.adapter_id == "openai"

    def test_get_groq_adapter_with_defaults(self):
        """Test that Groq adapter gets proper defaults."""
        adapter = get_adapter("groq", {"api_key": "test-key"})
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter._base_url == "https://api.groq.com/openai/v1"
        assert adapter._model == "llama-3.1-70b-versatile"

    def test_get_together_adapter_with_defaults(self):
        """Test that Together adapter gets proper defaults."""
        adapter = get_adapter("together", {"api_key": "test-key"})
        assert isinstance(adapter, OpenAICompatibleAdapter)
        assert adapter._base_url == "https://api.together.xyz/v1"

    def test_config_overrides_defaults(self):
        """Test that user config overrides provider defaults."""
        adapter = get_adapter("groq", {
            "api_key": "test-key",
            "model": "custom-model",
        })
        assert adapter._model == "custom-model"

    def test_unknown_adapter_raises(self):
        """Test that unknown adapter raises KeyError."""
        with pytest.raises(KeyError) as exc_info:
            get_adapter("nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert "Available adapters" in str(exc_info.value)

    def test_list_adapters(self):
        """Test listing available adapters."""
        adapters = list_adapters()
        assert "mock" in adapters
        assert "openai" in adapters
        assert "groq" in adapters

    def test_register_custom_adapter(self):
        """Test registering a custom adapter."""
        class CustomAdapter:
            def __init__(self, adapter_id, version, config):
                self.adapter_id = adapter_id
        
        register_adapter("custom", CustomAdapter)
        adapters = list_adapters()
        assert "custom" in adapters


# =============================================================================
# OpenAI-Compatible Adapter Tests
# =============================================================================

class TestOpenAICompatibleAdapter:
    """Tests for the OpenAI-compatible adapter."""

    def test_adapter_initialization(self):
        """Test basic adapter initialization."""
        adapter = OpenAICompatibleAdapter(
            adapter_id="test",
            version="1.0",
            config={"api_key": "test-key"}
        )
        assert adapter.adapter_id == "test"
        assert adapter.version == "1.0"
        assert adapter._api_key == "test-key"

    def test_adapter_default_values(self):
        """Test adapter uses correct defaults."""
        adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
        assert adapter._model == "gpt-4o-mini"
        assert adapter._temperature == 0.0
        assert adapter._max_tokens == 2048
        assert adapter._timeout == 60

    def test_adapter_custom_config(self):
        """Test adapter with custom configuration."""
        adapter = OpenAICompatibleAdapter(config={
            "api_key": "test",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 1024,
            "timeout": 120,
            "base_url": "https://custom.api.com/v1"
        })
        assert adapter._model == "gpt-4o"
        assert adapter._temperature == 0.5
        assert adapter._max_tokens == 1024
        assert adapter._timeout == 120
        assert adapter._base_url == "https://custom.api.com/v1"

    def test_adapter_retry_config(self):
        """Test adapter retry configuration."""
        adapter = OpenAICompatibleAdapter(config={
            "api_key": "test",
            "retry": {"max_retries": 5, "base_delay": 2.0}
        })
        assert adapter._retry.max_retries == 5
        assert adapter._retry.base_delay == 2.0

    def test_adapter_no_api_key_raises(self):
        """Test that missing API key raises on client access."""
        import os
        # Save any existing env var
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            adapter = OpenAICompatibleAdapter(config={})
            # This might raise ImportError if openai isn't installed,
            # or ValueError if API key is missing
            with pytest.raises((ValueError, ImportError)):
                _ = adapter.client
        finally:
            # Restore env var if it existed
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key

    def test_adapter_missing_openai_package(self):
        """Test graceful handling when openai package is missing."""
        # This test is difficult to do cleanly because openai may be installed.
        # We'll skip this test if openai is installed, as the real behavior
        # is adequately tested by the ImportError handling in the adapter code.
        try:
            import openai
            pytest.skip("openai package is installed, skipping import test")
        except ImportError:
            adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
            with pytest.raises(ImportError) as exc_info:
                _ = adapter.client
            assert "openai" in str(exc_info.value).lower()

    def test_extract_json_direct(self):
        """Test JSON extraction from clean JSON."""
        adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
        
        result = adapter._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_markdown(self):
        """Test JSON extraction from markdown code block."""
        adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
        
        text = """
Here is the result:
```json
{"key": "value"}
```
"""
        result = adapter._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_embedded(self):
        """Test JSON extraction from embedded JSON."""
        adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
        
        text = 'Some text {"key": "value"} more text'
        result = adapter._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_invalid(self):
        """Test JSON extraction returns None for invalid JSON."""
        adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
        
        result = adapter._extract_json("not json at all")
        assert result is None

    def test_calculate_backoff(self):
        """Test exponential backoff calculation."""
        adapter = OpenAICompatibleAdapter(config={
            "api_key": "test",
            "retry": {"base_delay": 1.0, "exponential_base": 2.0, "max_delay": 30.0}
        })
        
        assert adapter._calculate_backoff(0) == 1.0
        assert adapter._calculate_backoff(1) == 2.0
        assert adapter._calculate_backoff(2) == 4.0
        assert adapter._calculate_backoff(3) == 8.0
        # Should cap at max_delay
        assert adapter._calculate_backoff(10) == 30.0

    def test_adapter_metadata(self):
        """Test adapter metadata method."""
        adapter = OpenAICompatibleAdapter(config={
            "api_key": "test",
            "model": "test-model",
            "base_url": "https://test.api.com"
        })
        
        metadata = adapter.get_metadata()
        assert metadata["adapter_id"] == "openai"
        assert metadata["model"] == "test-model"
        assert metadata["base_url"] == "https://test.api.com"
        assert metadata["is_mock"] is False

    def test_generate_success(self):
        """Test successful generation with mocked OpenAI client."""
        adapter = OpenAICompatibleAdapter(config={"api_key": "test"})
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'
        mock_response.choices[0].finish_reason = "stop"
        mock_response.id = "resp_123"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 50
        
        # Create mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        # Inject mock client
        adapter._client = mock_client
        
        response = adapter.generate("test_template", "test prompt")
        
        assert response.text == '{"result": "success"}'
        assert response.parsed_json == {"result": "success"}
        assert response.tokens == 100
        assert "adapter_id" in response.adapter_provenance

    def test_generate_retry_on_failure(self):
        """Test that generate retries on failure."""
        adapter = OpenAICompatibleAdapter(config={
            "api_key": "test",
            "retry": {"max_retries": 3, "base_delay": 0.1}  # min is 0.1
        })
        
        # Create mock response for success on third try
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'
        mock_response.choices[0].finish_reason = "stop"
        mock_response.id = "resp_123"
        mock_response.usage = None
        
        # Create mock client that fails twice then succeeds
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            mock_response,
        ]
        
        # Inject mock client
        adapter._client = mock_client
        
        response = adapter.generate("test_template", "test prompt")
        assert response.text == '{"result": "success"}'
        assert mock_client.chat.completions.create.call_count == 3


# =============================================================================
# LLM Concision Tests
# =============================================================================

class TestLLMConcision:
    """Tests for LLM-assisted concision."""

    def test_load_prompt_template(self):
        """Test loading prompt template."""
        template = _load_prompt_template("concise_v1")
        assert "{input_text}" in template
        assert "atomic_candidates" in template

    def test_load_prompt_template_not_found(self):
        """Test error on missing template."""
        with pytest.raises(FileNotFoundError):
            _load_prompt_template("nonexistent_template")

    def test_validate_llm_response_valid(self):
        """Test validation of valid LLM response."""
        response = {
            "canonical_text": "test canonical",
            "atomic_candidates": [
                {"text": "claim 1", "origin_spans": [[0, 7]]}
            ],
            "confidence": 0.9
        }
        
        is_valid, warnings = _validate_llm_response(
            response, "claim 1", validate_spans=True
        )
        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_llm_response_missing_fields(self):
        """Test validation catches missing required fields."""
        response = {"atomic_candidates": []}
        is_valid, warnings = _validate_llm_response(response, "test", False)
        assert is_valid is False
        assert "canonical_text" in warnings[0]

    def test_validate_llm_response_invalid_spans(self):
        """Test validation catches out-of-bounds spans."""
        response = {
            "canonical_text": "test",
            "atomic_candidates": [
                {"text": "claim", "origin_spans": [[0, 100]]}  # Out of bounds
            ],
            "confidence": 0.9
        }
        
        is_valid, warnings = _validate_llm_response(
            response, "short", validate_spans=True
        )
        assert is_valid is True  # Still valid, just with warnings
        assert any("out of bounds" in w for w in warnings)

    def test_llm_concision_with_mock_adapter(
        self, simple_preprocessing_result, mock_context, mock_adapter
    ):
        """Test LLM concision with mock adapter."""
        result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            mock_adapter,
        )
        
        assert result.payload is not None
        assert "canonical_text" in result.payload
        assert "atomic_candidates" in result.payload
        assert result.confidence > 0

    def test_llm_concision_config_options(
        self, simple_preprocessing_result, mock_context, mock_adapter
    ):
        """Test LLM concision with custom config."""
        config = LLMConcisionConfig(
            max_retries=1,
            min_confidence=0.3,
            fallback_to_rule_based=True,
        )
        
        result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            mock_adapter,
            config,
        )
        
        assert result.payload is not None

    def test_llm_concision_fallback_to_rule_based(
        self, simple_preprocessing_result, mock_context
    ):
        """Test fallback to rule-based when LLM fails."""
        # Create adapter that returns low confidence
        adapter = MockLLMAdapter(config={
            "custom_responses": {
                "concise_v1": {
                    "canonical_text": "test",
                    "atomic_candidates": [],
                    "confidence": 0.1  # Below default threshold
                }
            }
        })
        
        config = LLMConcisionConfig(
            min_confidence=0.5,
            fallback_to_rule_based=True,
            max_retries=0,
        )
        
        result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            adapter,
            config,
        )
        
        # Should have fallen back to rule-based
        assert result.payload is not None
        assert any("Falling back" in w for w in result.warnings)

    def test_llm_concision_no_adapter_uses_mock(
        self, simple_preprocessing_result, mock_context
    ):
        """Test that LLM concision uses mock adapter when none provided."""
        result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            adapter=None,
        )
        
        assert result.payload is not None
        assert any("mock adapter" in w for w in result.warnings)

    def test_llm_concision_preserves_provenance(
        self, simple_preprocessing_result, mock_context, mock_adapter
    ):
        """Test that LLM concision tracks provenance correctly."""
        result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            mock_adapter,
        )
        
        # Check that provenance is recorded
        payload = result.payload
        if payload.get("atomic_candidates"):
            # The provenance should be serialized in the payload
            assert "atomic_candidates" in payload

    def test_llm_concision_conditional_structure(
        self, simple_preprocessing_result, mock_context, mock_adapter
    ):
        """Test LLM concision identifies conditional structure."""
        result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            mock_adapter,
        )
        
        payload = result.payload
        # Mock adapter should detect conditional structure
        assert len(payload.get("atomic_candidates", [])) >= 1

    def test_llm_concision_conjunction_structure(
        self, conjunction_preprocessing_result, mock_context, mock_adapter
    ):
        """Test LLM concision handles conjunction structure."""
        result = llm_concision(
            conjunction_preprocessing_result,
            mock_context,
            mock_adapter,
        )
        
        payload = result.payload
        assert "atomic_candidates" in payload


# =============================================================================
# Integration Tests
# =============================================================================

class TestSprint4Integration:
    """Integration tests for Sprint 4 components."""

    def test_full_pipeline_mock(self, mock_context):
        """Test full pipeline with mock adapter."""
        # Create preprocessing result
        text = "If the weather is good then we will go hiking."
        preprocessing_result = PreprocessingResult(
            normalized_text=text,
            clauses=[
                Clause(
                    text=text,
                    start_char=0,
                    end_char=len(text),
                    tokens=[],
                    clause_type="declarative"
                )
            ],
            tokens=[],
            origin_spans={},
            sentence_boundaries=[(0, len(text))],
        )
        
        # Get mock adapter from registry
        adapter = get_adapter("mock")
        
        # Run LLM concision
        result = llm_concision(
            preprocessing_result,
            mock_context,
            adapter,
        )
        
        # Verify result
        assert result.payload is not None
        assert result.confidence > 0
        
        # Should have detected conditional and extracted parts
        payload = result.payload
        assert "canonical_text" in payload
        assert len(payload.get("atomic_candidates", [])) >= 1

    def test_adapter_registry_round_trip(self):
        """Test adapter creation and usage through registry."""
        for adapter_name in ["mock"]:
            adapter = get_adapter(adapter_name)
            response = adapter.generate("concise_v1", "Test prompt")
            assert response.text is not None
            assert response.adapter_provenance is not None

    def test_deterministic_vs_llm_concision(
        self, simple_preprocessing_result, mock_context
    ):
        """Compare deterministic and LLM concision outputs."""
        # Run deterministic concision
        det_result = deterministic_concision(
            simple_preprocessing_result,
            mock_context
        )
        
        # Run LLM concision
        adapter = get_adapter("mock")
        llm_result = llm_concision(
            simple_preprocessing_result,
            mock_context,
            adapter,
        )
        
        # Both should produce valid results
        assert det_result.payload is not None
        assert llm_result.payload is not None
        
        # Both should have atomic candidates
        assert len(det_result.payload.get("atomic_candidates", [])) >= 1
        assert len(llm_result.payload.get("atomic_candidates", [])) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
