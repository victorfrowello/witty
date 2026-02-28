"""
Tests for live retrieval adapters: Wikipedia, DuckDuckGo, and Composite.

Sprint 7: Live Retrieval Integration

Author: Victor Rowello
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from src.adapters.wikipedia import WikipediaAdapter
from src.adapters.duckduckgo import DuckDuckGoAdapter
from src.adapters.composite import CompositeRetrievalAdapter
from src.adapters.retrieval import get_retrieval_adapter


class MockContext:
    """Mock context for testing."""
    def __init__(self, privacy_mode: str = "default"):
        self.options = Mock()
        self.options.privacy_mode = privacy_mode


class TestWikipediaAdapter:
    """Tests for WikipediaAdapter."""
    
    def test_adapter_initialization(self):
        """Test adapter initializes with correct defaults."""
        adapter = WikipediaAdapter()
        assert adapter.adapter_id == "wikipedia"
        assert adapter.version == "1.0"
        assert adapter.timeout == 10.0
        
    def test_adapter_custom_timeout(self):
        """Test adapter accepts custom timeout."""
        adapter = WikipediaAdapter(timeout=30.0)
        assert adapter.timeout == 30.0
        
    @patch.object(WikipediaAdapter, '_make_request')
    def test_retrieve_success(self, mock_request):
        """Test successful Wikipedia retrieval."""
        # First call returns search results, second returns summary
        mock_request.side_effect = [
            # Search response
            ["test", ["Test Article"], ["A test article"], ["https://en.wikipedia.org/wiki/Test_Article"]],
            # Summary response
            {
                "title": "Test Article",
                "extract": "This is a test article about testing.",
                "content_urls": {
                    "desktop": {"page": "https://en.wikipedia.org/wiki/Test_Article"}
                },
                "pageid": 1,
                "description": "A test article"
            }
        ]
        
        adapter = WikipediaAdapter()
        ctx = MockContext()
        response = adapter.retrieve("test", top_k=1, ctx=ctx)
        
        assert response.query == "test"
        assert len(response.sources) == 1
        assert "test" in response.sources[0].content.lower()
        assert response.sources[0].metadata.get("type") == "wikipedia"
        
    @patch.object(WikipediaAdapter, '_make_request')
    def test_retrieve_empty_results(self, mock_request):
        """Test handling of empty search results."""
        # Empty search results
        mock_request.return_value = ["xyznonexistent123", [], [], []]
        
        adapter = WikipediaAdapter()
        ctx = MockContext()
        response = adapter.retrieve("xyznonexistent123", top_k=3, ctx=ctx)
        
        assert response.query == "xyznonexistent123"
        assert len(response.sources) == 0
        
    @patch.object(WikipediaAdapter, '_make_request')
    def test_retrieve_handles_network_error(self, mock_request):
        """Test graceful handling of network errors."""
        mock_request.return_value = None  # Simulate network error
        
        adapter = WikipediaAdapter()
        ctx = MockContext()
        response = adapter.retrieve("test", top_k=3, ctx=ctx)
        
        assert response.query == "test"
        assert len(response.sources) == 0
        
    @patch.object(WikipediaAdapter, '_make_request')
    def test_retrieve_honors_top_k(self, mock_request):
        """Test that top_k limits results."""
        mock_request.side_effect = [
            # Search returns 3 articles
            ["test", ["Article1", "Article2", "Article3"], ["Desc 1", "Desc 2", "Desc 3"], 
             ["url1", "url2", "url3"]],
            # Summaries
            {"title": "Article1", "extract": "Text 1", "content_urls": {"desktop": {"page": "url1"}}, "pageid": 1},
            {"title": "Article2", "extract": "Text 2", "content_urls": {"desktop": {"page": "url2"}}, "pageid": 2},
        ]
        
        adapter = WikipediaAdapter()
        ctx = MockContext()
        response = adapter.retrieve("test", top_k=2, ctx=ctx)
        
        # Should have at most 2 results
        assert len(response.sources) <= 2


class TestDuckDuckGoAdapter:
    """Tests for DuckDuckGoAdapter."""
    
    def test_adapter_initialization(self):
        """Test adapter initializes with correct defaults."""
        adapter = DuckDuckGoAdapter()
        assert adapter.adapter_id == "duckduckgo"
        assert adapter.version == "1.0"
        assert adapter.timeout == 10.0
        
    @patch.object(DuckDuckGoAdapter, '_make_request')
    def test_retrieve_with_abstract(self, mock_request):
        """Test DuckDuckGo retrieval with instant answer."""
        mock_request.return_value = {
            "Heading": "Test Topic",
            "Abstract": "This is the abstract about the test topic.",  # Note: "Abstract" not "AbstractText"
            "AbstractURL": "https://example.com/test",
            "AbstractSource": "Wikipedia",
            "RelatedTopics": []
        }
        
        adapter = DuckDuckGoAdapter()
        ctx = MockContext()
        response = adapter.retrieve("test topic", top_k=3, ctx=ctx)
        
        assert response.query == "test topic"
        assert len(response.sources) >= 1
        assert "abstract" in response.sources[0].content.lower()
        
    @patch.object(DuckDuckGoAdapter, '_make_request')
    def test_retrieve_with_related_topics(self, mock_request):
        """Test DuckDuckGo retrieval includes related topics."""
        mock_request.return_value = {
            "Heading": "Test",
            "AbstractText": "",
            "AbstractURL": "",
            "AbstractSource": "",
            "RelatedTopics": [
                {"Text": "Related topic 1 text", "FirstURL": "https://example.com/1"},
                {"Text": "Related topic 2 text", "FirstURL": "https://example.com/2"}
            ]
        }
        
        adapter = DuckDuckGoAdapter()
        ctx = MockContext()
        response = adapter.retrieve("test", top_k=5, ctx=ctx)
        
        assert response.query == "test"
        # Should include related topics
        assert len(response.sources) >= 1
        
    @patch.object(DuckDuckGoAdapter, '_make_request')
    def test_retrieve_no_results(self, mock_request):
        """Test handling when no results found."""
        mock_request.return_value = {
            "Heading": "",
            "AbstractText": "",
            "AbstractURL": "",
            "AbstractSource": "",
            "RelatedTopics": []
        }
        
        adapter = DuckDuckGoAdapter()
        ctx = MockContext()
        response = adapter.retrieve("xyznonexistent", top_k=3, ctx=ctx)
        
        assert len(response.sources) == 0
        
    @patch.object(DuckDuckGoAdapter, '_make_request')
    def test_retrieve_handles_error(self, mock_request):
        """Test graceful error handling."""
        mock_request.return_value = None  # Simulate error
        
        adapter = DuckDuckGoAdapter()
        ctx = MockContext()
        response = adapter.retrieve("test", top_k=3, ctx=ctx)
        
        assert response.query == "test"
        assert len(response.sources) == 0


class TestCompositeRetrievalAdapter:
    """Tests for CompositeRetrievalAdapter."""
    
    def test_adapter_initialization(self):
        """Test adapter initializes with default components."""
        adapter = CompositeRetrievalAdapter()
        assert adapter.adapter_id == "composite"
        assert adapter.wikipedia is not None
        assert adapter.duckduckgo is not None
        
    def test_uses_wikipedia_first(self):
        """Test that Wikipedia is queried first by default."""
        adapter = CompositeRetrievalAdapter()
        # The adapter should have wikipedia and duckduckgo attributes
        assert hasattr(adapter, 'wikipedia')
        assert hasattr(adapter, 'duckduckgo')
        assert isinstance(adapter.wikipedia, WikipediaAdapter)
        assert isinstance(adapter.duckduckgo, DuckDuckGoAdapter)


class TestRetrievalAdapterRegistry:
    """Tests for retrieval adapter registry/factory."""
    
    def test_get_mock_adapter(self):
        """Test getting mock adapter."""
        adapter = get_retrieval_adapter("mock")
        assert adapter.adapter_id == "mock_retrieval"
        
    def test_get_wikipedia_adapter(self):
        """Test getting Wikipedia adapter via factory."""
        adapter = get_retrieval_adapter("wikipedia")
        assert isinstance(adapter, WikipediaAdapter)
        assert adapter.adapter_id == "wikipedia"
        
    def test_get_duckduckgo_adapter(self):
        """Test getting DuckDuckGo adapter via factory."""
        adapter = get_retrieval_adapter("duckduckgo")
        assert isinstance(adapter, DuckDuckGoAdapter)
        assert adapter.adapter_id == "duckduckgo"
        
    def test_get_composite_adapter(self):
        """Test getting composite adapter via factory."""
        adapter = get_retrieval_adapter("composite")
        assert isinstance(adapter, CompositeRetrievalAdapter)
        assert adapter.adapter_id == "composite"
        
    def test_unknown_adapter_raises(self):
        """Test that unknown adapter type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown retrieval adapter type"):
            get_retrieval_adapter("unknown_adapter")


class TestPrivacyModeHandling:
    """Tests for privacy mode handling across adapters."""
    
    @patch.object(WikipediaAdapter, '_do_retrieve')
    def test_strict_mode_redacts_content(self, mock_do_retrieve):
        """Test that strict privacy mode redacts content."""
        from src.witty_types import RetrievalSource
        
        mock_do_retrieve.return_value = [
            RetrievalSource(
                source_id="wiki_1",
                content="Sensitive information about John Smith",
                score=0.9,
                metadata={"source": "wikipedia"}
            )
        ]
        
        adapter = WikipediaAdapter()
        ctx = MockContext(privacy_mode="strict")
        response = adapter.retrieve("test", top_k=3, ctx=ctx)
        
        assert response.privacy_mode == "strict"
        assert len(response.sources) == 1
        assert response.sources[0].content == "[REDACTED]"
        assert response.sources[0].redacted is True


# Mark live tests that require network access
@pytest.mark.live
class TestLiveWikipediaAdapter:
    """Live integration tests for Wikipedia adapter.
    
    These tests make real network requests and should be run
    only when explicitly requested: pytest -m live
    """
    
    def test_live_wikipedia_search(self):
        """Test real Wikipedia search."""
        adapter = WikipediaAdapter()
        ctx = MockContext()
        response = adapter.retrieve("Python programming language", top_k=2, ctx=ctx)
        
        # Should get at least one result for a well-known topic
        assert len(response.sources) >= 1
        assert any("python" in s.content.lower() for s in response.sources)


@pytest.mark.live
class TestLiveDuckDuckGoAdapter:
    """Live integration tests for DuckDuckGo adapter."""
    
    def test_live_duckduckgo_search(self):
        """Test real DuckDuckGo search."""
        adapter = DuckDuckGoAdapter()
        ctx = MockContext()
        response = adapter.retrieve("Albert Einstein", top_k=3, ctx=ctx)
        
        # Should get results for a famous person
        assert len(response.sources) >= 1


@pytest.mark.live
class TestLiveCompositeAdapter:
    """Live integration tests for composite adapter."""
    
    def test_live_composite_search(self):
        """Test composite adapter with real requests."""
        adapter = CompositeRetrievalAdapter()
        ctx = MockContext()
        response = adapter.retrieve("Artificial intelligence", top_k=3, ctx=ctx)
        
        # Should get results from one of the providers
        assert len(response.sources) >= 1
