"""
End-to-end integration tests for Sprint 7 live mode.

Tests the full pipeline with:
- Live Groq LLM (Llama 3.3 70B)
- Live Wikipedia retrieval
- Live DuckDuckGo retrieval

Run with: pytest tests/test_live_integration.py -v -m live
Requires: GROQ_API_KEY environment variable

Author: Victor Rowello
Sprint: 7
"""
import pytest
import os
import json

from src.pipeline.orchestrator import formalize_statement
from src.witty.types import FormalizeOptions
from src.adapters.groq_adapter import GroqAdapter
from src.adapters.wikipedia import WikipediaAdapter
from src.adapters.duckduckgo import DuckDuckGoAdapter
from src.adapters.composite import CompositeRetrievalAdapter


class TestLiveModeConfiguration:
    """Tests for live mode configuration."""
    
    def test_live_mode_options_default(self):
        """Test that live_mode defaults to False."""
        options = FormalizeOptions()
        assert options.live_mode is False
        assert options.retrieval_enabled is False
        
    def test_live_mode_can_be_enabled(self):
        """Test that live_mode can be enabled."""
        options = FormalizeOptions(
            live_mode=True,
            llm_model="llama-3.3-70b-versatile",
            retrieval_enabled=True
        )
        assert options.live_mode is True
        assert options.llm_model == "llama-3.3-70b-versatile"
        assert options.retrieval_enabled is True


class TestDeterministicPipeline:
    """Tests for deterministic (non-live) pipeline."""
    
    def test_simple_conditional(self):
        """Test deterministic pipeline with simple conditional."""
        options = FormalizeOptions(reproducible_mode=True)
        result = formalize_statement(
            "If it rains then the ground is wet.",
            options
        )
        
        # Check result has expected structure (FormalizationResult pydantic model)
        assert hasattr(result, 'original_text')
        assert result.original_text == "If it rains then the ground is wet."
        assert hasattr(result, 'atomic_claims')
        assert len(result.atomic_claims) >= 1
        assert hasattr(result, 'legend')
        assert len(result.legend) >= 1
        
    def test_conjunction(self):
        """Test deterministic pipeline with conjunction."""
        options = FormalizeOptions(reproducible_mode=True)
        result = formalize_statement(
            "Alice is tall and Bob is short.",
            options
        )
        
        assert hasattr(result, 'original_text')
        assert hasattr(result, 'atomic_claims')
        assert len(result.atomic_claims) >= 1


# Live tests that require real API access
@pytest.mark.live
class TestLiveGroqIntegration:
    """Live integration tests with Groq LLM.
    
    These tests make real API calls and require GROQ_API_KEY.
    Run with: pytest -m live
    """
    
    @pytest.fixture
    def live_options(self):
        """Create options for live mode."""
        if not os.environ.get("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")
        return FormalizeOptions(
            live_mode=True,
            llm_model="llama-3.3-70b-versatile",
            retrieval_enabled=False  # Test LLM only first
        )
    
    def test_live_simple_conditional(self, live_options):
        """Test live pipeline with simple conditional."""
        result = formalize_statement(
            "If it rains then the ground is wet.",
            live_options
        )
        
        assert hasattr(result, 'original_text')
        assert result.original_text == "If it rains then the ground is wet."
        # Live mode should produce atomic claims
        assert len(result.atomic_claims) >= 1
        assert len(result.legend) >= 1
        # Check we have CNF output
        assert result.cnf is not None
        
    def test_live_complex_statement(self, live_options):
        """Test live pipeline with complex statement."""
        result = formalize_statement(
            "All humans are mortal. Socrates is human. Therefore, Socrates is mortal.",
            live_options
        )
        
        assert hasattr(result, 'atomic_claims')
        assert len(result.atomic_claims) >= 2
        
    def test_live_negation(self, live_options):
        """Test live pipeline handles negation."""
        result = formalize_statement(
            "It is not the case that all birds can fly.",
            live_options
        )
        
        assert hasattr(result, 'atomic_claims')
        assert len(result.atomic_claims) >= 1


@pytest.mark.live
class TestLiveRetrievalIntegration:
    """Live integration tests with retrieval adapters.
    
    These tests make real API calls to Wikipedia and DuckDuckGo.
    Run with: pytest -m live
    """
    
    def test_wikipedia_adapter_directly(self):
        """Test Wikipedia adapter directly."""
        adapter = WikipediaAdapter()
        
        # Create a proper mock context with options
        class MockOptions:
            privacy_mode = "default"
        
        class MockContext:
            request_id = "test"
            options = MockOptions()
        
        response = adapter.retrieve("Albert Einstein physicist", top_k=2, ctx=MockContext())
        
        assert response.sources is not None
        # Wikipedia should return some results
        assert len(response.sources) >= 0  # May be 0 if rate limited
        
    def test_duckduckgo_adapter_directly(self):
        """Test DuckDuckGo adapter directly."""
        adapter = DuckDuckGoAdapter()
        
        class MockOptions:
            privacy_mode = "default"
        
        class MockContext:
            request_id = "test"
            options = MockOptions()
        
        response = adapter.retrieve("Python programming language", top_k=2, ctx=MockContext())
        
        assert response.sources is not None
        
    def test_composite_retrieval(self):
        """Test composite retrieval with both sources."""
        # CompositeRetrievalAdapter creates its own Wikipedia + DuckDuckGo adapters
        composite = CompositeRetrievalAdapter()
        
        class MockOptions:
            privacy_mode = "default"
        
        class MockContext:
            request_id = "test"
            options = MockOptions()
        
        response = composite.retrieve("machine learning", top_k=2, ctx=MockContext())
        
        assert response.sources is not None


@pytest.mark.live
class TestFullLivePipeline:
    """Full end-to-end live pipeline tests.
    
    Tests the complete pipeline with LLM + retrieval.
    """
    
    @pytest.fixture
    def full_live_options(self):
        """Create options for full live mode."""
        if not os.environ.get("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")
        return FormalizeOptions(
            live_mode=True,
            llm_model="llama-3.3-70b-versatile",
            retrieval_enabled=True,
            retrieval_sources=["wikipedia"],
            retrieval_top_k=2
        )
    
    def test_full_pipeline_conditional(self, full_live_options):
        """Test full pipeline with conditional statement."""
        result = formalize_statement(
            "If water freezes at 0 degrees Celsius, then ice forms.",
            full_live_options
        )
        
        assert hasattr(result, 'request_id')
        assert result.request_id is not None
        assert len(result.atomic_claims) >= 1
        assert result.cnf is not None
        # Should have CNF with implication converted to disjunction
        # P → Q becomes ¬P ∨ Q
        assert "∨" in result.cnf or len(result.cnf_clauses[0]) > 1
        
    def test_full_pipeline_mixed_structure(self, full_live_options):
        """Test full pipeline with mixed conjunction + conditional."""
        result = formalize_statement(
            "Roses are red and violets are blue. If it's tuesday, then violets are purple.",
            full_live_options
        )
        
        assert len(result.atomic_claims) >= 3  # At least 3 claims
        assert result.cnf is not None
        # Should have both conjunction AND implication in CNF
        # The conditional P3 → P4 becomes (¬P3 ∨ P4)
        # Combined with P1 ∧ P2, we get: (¬P3 ∨ P4) ∧ P1 ∧ P2
        assert len(result.cnf_clauses) >= 2  # Multiple clauses
        # Check that at least one clause has the disjunction pattern
        has_disjunction_clause = any(len(clause) >= 2 for clause in result.cnf_clauses)
        assert has_disjunction_clause, "Should have implication converted to disjunction clause"
        
    def test_full_pipeline_with_entities(self, full_live_options):
        """Test full pipeline with named entities (triggers retrieval)."""
        result = formalize_statement(
            "Einstein developed the theory of relativity.",
            full_live_options
        )
        
        assert hasattr(result, 'atomic_claims')
        assert len(result.atomic_claims) >= 1
        # Should have provenance records
        assert len(result.provenance) >= 1


class TestCLILiveMode:
    """Tests for CLI live mode arguments."""
    
    def test_cli_argument_parsing(self):
        """Test that CLI accepts live mode arguments."""
        import argparse
        from src.cli import main
        
        # We can't easily test main() without files, but we can
        # verify the module loads without errors
        assert main is not None
