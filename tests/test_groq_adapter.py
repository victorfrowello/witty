"""
Tests for Groq LLM adapter.

Sprint 7: Live LLM Integration

Author: Victor Rowello
"""
import pytest
import os
from unittest.mock import patch, Mock
import json

from src.adapters.groq_adapter import GroqAdapter, get_groq_adapter
from src.adapters.registry import get_adapter


class MockResponse:
    """Mock HTTP response for testing."""
    def __init__(self, data: dict):
        self._data = json.dumps(data).encode('utf-8')
        
    def read(self):
        return self._data
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass


class TestGroqAdapterInit:
    """Tests for GroqAdapter initialization."""
    
    def test_default_initialization(self):
        """Test adapter initializes with correct defaults."""
        adapter = GroqAdapter()
        assert adapter.adapter_id == "groq"
        assert adapter.version == "1.0"
        assert adapter.model == "llama-3.3-70b-versatile"
        assert adapter.temperature == 0.1
        assert adapter.max_tokens == 4096
        assert adapter.timeout == 30.0
        
    def test_custom_model(self):
        """Test adapter accepts custom model."""
        adapter = GroqAdapter(model="llama-3.1-8b-instant")
        assert adapter.model == "llama-3.1-8b-instant"
        
    def test_custom_parameters(self):
        """Test adapter accepts custom parameters."""
        adapter = GroqAdapter(
            temperature=0.7,
            max_tokens=2048,
            timeout=60.0
        )
        assert adapter.temperature == 0.7
        assert adapter.max_tokens == 2048
        assert adapter.timeout == 60.0
        
    def test_config_overrides(self):
        """Test that config dict overrides defaults."""
        adapter = GroqAdapter(config={
            "model": "mixtral-8x7b-32768",
            "temperature": 0.5
        })
        assert adapter.model == "mixtral-8x7b-32768"
        assert adapter.temperature == 0.5


class TestGroqAdapterAPIKey:
    """Tests for API key handling."""
    
    def test_missing_api_key_returns_error(self):
        """Test that missing API key returns error in response."""
        adapter = GroqAdapter()
        # Clear any existing key
        adapter._api_key = None
        
        with patch.dict(os.environ, {}, clear=True):
            response = adapter.generate("test_template", "test prompt")
            assert response.adapter_provenance.get("error") is not None
            assert "GROQ_API_KEY" in response.adapter_provenance.get("error", "")
            
    def test_api_key_from_environment(self):
        """Test that API key is read from environment."""
        adapter = GroqAdapter()
        adapter._api_key = None
        
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key-123"}):
            key = adapter._get_api_key()
            assert key == "test-key-123"


class TestGroqAdapterGenerate:
    """Tests for generate method with mocked HTTP."""
    
    @patch('urllib.request.urlopen')
    def test_successful_json_response(self, mock_urlopen):
        """Test successful JSON generation."""
        mock_response = MockResponse({
            "choices": [{
                "message": {
                    "content": '{"claims": ["test claim"], "confidence": 0.9}'
                }
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        })
        mock_urlopen.return_value = mock_response
        
        adapter = GroqAdapter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            response = adapter.generate("concise_v1", "Test prompt")
        
        assert response.parsed_json is not None
        assert response.parsed_json["claims"] == ["test claim"]
        assert response.parsed_json["confidence"] == 0.9
        assert response.adapter_provenance["model"] == "llama-3.3-70b-versatile"
        assert response.tokens == 30
        assert response.model_metadata["prompt_tokens"] == 10
        
    @patch('urllib.request.urlopen')
    def test_non_json_mode(self, mock_urlopen):
        """Test generation without JSON mode."""
        mock_response = MockResponse({
            "choices": [{
                "message": {
                    "content": "This is a plain text response."
                }
            }],
            "usage": {"total_tokens": 15}
        })
        mock_urlopen.return_value = mock_response
        
        adapter = GroqAdapter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            response = adapter.generate("test", "Test prompt", json_mode=False)
        
        assert response.text == "This is a plain text response."
        assert response.parsed_json is None  # Not parsed when json_mode=False
        
    @patch('urllib.request.urlopen')
    def test_malformed_json_response(self, mock_urlopen):
        """Test handling of malformed JSON from API."""
        mock_response = MockResponse({
            "choices": [{
                "message": {
                    "content": "Not valid JSON {{"
                }
            }],
            "usage": {}
        })
        mock_urlopen.return_value = mock_response
        
        adapter = GroqAdapter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            response = adapter.generate("test", "Test prompt", json_mode=True)
        
        assert response.text == "Not valid JSON {{"
        assert response.parsed_json is None
        assert response.model_metadata.get("parse_error") is not None
        
    @patch('urllib.request.urlopen')
    def test_http_error_handling(self, mock_urlopen):
        """Test handling of HTTP errors."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            url="https://api.groq.com",
            code=429,
            msg="Rate limited",
            hdrs={},
            fp=None
        )
        
        adapter = GroqAdapter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            response = adapter.generate("test", "Test prompt")
        
        assert response.adapter_provenance.get("error") == "HTTP 429"
        
    @patch('urllib.request.urlopen')
    def test_network_error_handling(self, mock_urlopen):
        """Test handling of network errors."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")
        
        adapter = GroqAdapter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            response = adapter.generate("test", "Test prompt")
        
        assert "URL error" in response.adapter_provenance.get("error", "")
        
    @patch('urllib.request.urlopen')
    def test_system_message_included(self, mock_urlopen):
        """Test that system message is included in request."""
        captured_request = None
        
        def capture_request(request, **kwargs):
            nonlocal captured_request
            captured_request = json.loads(request.data.decode('utf-8'))
            return MockResponse({
                "choices": [{"message": {"content": '{"result": "ok"}'}}],
                "usage": {}
            })
        
        mock_urlopen.side_effect = capture_request
        
        adapter = GroqAdapter()
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            adapter.generate(
                "test",
                "User prompt",
                system_message="You are a helpful assistant."
            )
        
        assert captured_request is not None
        messages = captured_request["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User prompt"


class TestGroqAdapterRegistry:
    """Tests for Groq adapter in registry."""
    
    def test_get_groq_from_registry(self):
        """Test getting Groq adapter from registry."""
        adapter = get_adapter("groq")
        assert isinstance(adapter, GroqAdapter)
        assert adapter.model == "llama-3.3-70b-versatile"
        
    def test_factory_function(self):
        """Test get_groq_adapter factory function."""
        adapter = get_groq_adapter(model="llama-3.1-8b-instant")
        assert isinstance(adapter, GroqAdapter)
        assert adapter.model == "llama-3.1-8b-instant"
        
    def test_get_metadata(self):
        """Test get_metadata returns correct info."""
        adapter = GroqAdapter()
        metadata = adapter.get_metadata()
        assert metadata["adapter_id"] == "groq"
        assert metadata["model"] == "llama-3.3-70b-versatile"
        assert "api_url" in metadata


# Live tests that require actual API access
@pytest.mark.live
class TestLiveGroqAdapter:
    """Live integration tests for Groq adapter.
    
    These tests make real API calls and require GROQ_API_KEY.
    Run with: pytest -m live
    """
    
    @pytest.fixture
    def adapter(self):
        """Get adapter with API key check."""
        if not os.environ.get("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")
        return GroqAdapter()
    
    def test_live_json_generation(self, adapter):
        """Test real JSON generation with Llama 3.3."""
        response = adapter.generate(
            prompt_template_id="test",
            prompt="Return a JSON object with a 'greeting' field containing 'Hello, World!'",
            system_message="You are a helpful assistant that returns valid JSON."
        )
        
        assert response.adapter_provenance.get("error") is None, f"API error: {response.adapter_provenance}"
        assert response.parsed_json is not None, f"Failed to parse: {response.text}"
        assert "greeting" in response.parsed_json
        assert response.adapter_provenance["model"] == "llama-3.3-70b-versatile"
        
    def test_live_concision_prompt(self, adapter):
        """Test concision-style prompt."""
        response = adapter.generate(
            prompt_template_id="concise_v1",
            prompt='''Decompose this sentence into atomic claims:
"If it rains, then the ground will be wet."

Return JSON with format: {"claims": [{"text": "...", "type": "..."}]}''',
            system_message="You are a logic assistant. Return valid JSON only."
        )
        
        assert response.adapter_provenance.get("error") is None
        assert response.parsed_json is not None
        assert "claims" in response.parsed_json
        assert len(response.parsed_json["claims"]) >= 1
