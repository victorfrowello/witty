"""
RetrievalAdapter Protocol and Implementations.

DesignSpec 6a.1: RetrievalAdapter interface for knowledge retrieval
with privacy mode support.

Author: Victor Rowello
Sprint: 5
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from src.witty_types import RetrievalSource, RetrievalResponse
import uuid


@runtime_checkable
class RetrievalAdapter(Protocol):
    """
    Protocol defining the retrieval adapter interface.
    
    DesignSpec 6a.1 Acceptance Criteria:
    - retrieve(query, top_k, ctx) -> RetrievalResponse
    - Privacy redaction in strict mode
    - Source tracking for provenance
    """
    
    def retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> RetrievalResponse:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: The search query
            top_k: Maximum number of results to return
            ctx: Pipeline context with options
            
        Returns:
            RetrievalResponse with sources and metadata
        """
        ...


class BaseRetrievalAdapter(ABC):
    """
    Abstract base class for retrieval adapters.
    
    Provides common functionality for privacy handling and
    response construction.
    """
    
    def __init__(self, adapter_id: str = "base", version: str = "0.1"):
        self.adapter_id = adapter_id
        self.version = version
    
    def _should_redact(self, ctx: Any) -> bool:
        """Check if privacy mode requires redaction."""
        privacy_mode = getattr(ctx.options, 'privacy_mode', 'default')
        return privacy_mode == 'strict'
    
    def _should_audit(self, ctx: Any) -> bool:
        """Check if privacy mode requires audit logging."""
        privacy_mode = getattr(ctx.options, 'privacy_mode', 'default')
        return privacy_mode == 'audit'
    
    def _redact_content(self, content: str) -> str:
        """Redact content for privacy compliance."""
        return "[REDACTED]"
    
    def _log_audit(self, ctx: Any, query: str, sources: List[RetrievalSource]) -> None:
        """Log retrieval for audit mode."""
        if hasattr(ctx, 'audit_log'):
            ctx.audit_log.append({
                'type': 'retrieval',
                'query': query,
                'source_count': len(sources),
                'source_ids': [s.source_id for s in sources]
            })
    
    @abstractmethod
    def _do_retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> List[RetrievalSource]:
        """
        Perform the actual retrieval. Implemented by subclasses.
        """
        pass
    
    def retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> RetrievalResponse:
        """
        Retrieve documents with privacy handling.
        
        Args:
            query: Search query
            top_k: Maximum results
            ctx: Pipeline context
            
        Returns:
            RetrievalResponse with privacy-compliant sources
        """
        request_id = str(uuid.uuid4())
        privacy_mode = getattr(ctx.options, 'privacy_mode', 'default')
        
        # Perform retrieval
        sources = self._do_retrieve(query, top_k, ctx)
        
        # Apply privacy redaction if needed
        if self._should_redact(ctx):
            for source in sources:
                source.content = self._redact_content(source.content)
                source.redacted = True
        
        # Audit logging
        if self._should_audit(ctx):
            self._log_audit(ctx, query, sources)
        
        return RetrievalResponse(
            query=query,
            sources=sources,
            total_results=len(sources),
            request_id=request_id,
            privacy_mode=privacy_mode
        )


class MockRetrievalAdapter(BaseRetrievalAdapter):
    """
    Mock retrieval adapter for testing.
    
    Returns canned responses for testing the enrichment pipeline
    without external dependencies.
    """
    
    def __init__(
        self,
        adapter_id: str = "mock_retrieval",
        version: str = "0.1",
        mock_sources: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(adapter_id, version)
        self.mock_sources = mock_sources or self._default_sources()
    
    def _default_sources(self) -> List[Dict[str, Any]]:
        """Default mock sources for testing."""
        return [
            {
                "source_id": "mock_src_1",
                "content": "Alice is a project manager at TechCorp.",
                "score": 0.92,
                "metadata": {"type": "employee_db"}
            },
            {
                "source_id": "mock_src_2",
                "content": "Bob is a senior engineer specializing in Python.",
                "score": 0.88,
                "metadata": {"type": "employee_db"}
            },
            {
                "source_id": "mock_src_3",
                "content": "All employees must complete annual training.",
                "score": 0.85,
                "metadata": {"type": "policy_doc"}
            }
        ]
    
    def _do_retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> List[RetrievalSource]:
        """Return mock sources, limited by top_k."""
        sources = []
        for i, src_data in enumerate(self.mock_sources[:top_k]):
            sources.append(RetrievalSource(
                source_id=src_data.get("source_id", f"mock_{i}"),
                content=src_data.get("content", ""),
                score=src_data.get("score", 0.5),
                redacted=False,
                metadata=src_data.get("metadata", {})
            ))
        return sources


class VectorRetrievalAdapter(BaseRetrievalAdapter):
    """
    Vector-based retrieval adapter stub.
    
    Placeholder for future integration with vector databases
    like Pinecone, Weaviate, or FAISS.
    """
    
    def __init__(
        self,
        adapter_id: str = "vector_retrieval",
        version: str = "0.1",
        endpoint: Optional[str] = None
    ):
        super().__init__(adapter_id, version)
        self.endpoint = endpoint
    
    def _do_retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> List[RetrievalSource]:
        """
        Placeholder for vector retrieval.
        
        In production, this would:
        1. Embed the query using a sentence transformer
        2. Query the vector database
        3. Return ranked results
        """
        # For now, return empty - actual implementation in future sprint
        return []


# Registry of available retrieval adapters
RETRIEVAL_ADAPTERS: Dict[str, type] = {
    "mock": MockRetrievalAdapter,
    "vector": VectorRetrievalAdapter,
}

# Lazy imports for live adapters to avoid import overhead if not used
def _get_wikipedia_adapter():
    from src.adapters.wikipedia import WikipediaAdapter
    return WikipediaAdapter

def _get_duckduckgo_adapter():
    from src.adapters.duckduckgo import DuckDuckGoAdapter
    return DuckDuckGoAdapter

def _get_composite_adapter():
    from src.adapters.composite import CompositeRetrievalAdapter
    return CompositeRetrievalAdapter


LIVE_RETRIEVAL_ADAPTERS: Dict[str, callable] = {
    "wikipedia": _get_wikipedia_adapter,
    "duckduckgo": _get_duckduckgo_adapter,
    "composite": _get_composite_adapter,
}


def get_retrieval_adapter(
    adapter_type: str = "mock",
    **kwargs
) -> BaseRetrievalAdapter:
    """
    Factory function to get a retrieval adapter.
    
    Args:
        adapter_type: Type of adapter ('mock', 'vector', 'wikipedia', 
                      'duckduckgo', 'composite')
        **kwargs: Additional arguments for the adapter
        
    Returns:
        Configured retrieval adapter instance
    """
    # Check standard adapters first
    adapter_cls = RETRIEVAL_ADAPTERS.get(adapter_type)
    if adapter_cls is not None:
        return adapter_cls(**kwargs)
    
    # Check live adapters (lazy loaded)
    adapter_getter = LIVE_RETRIEVAL_ADAPTERS.get(adapter_type)
    if adapter_getter is not None:
        adapter_cls = adapter_getter()
        return adapter_cls(**kwargs)
    
    raise ValueError(f"Unknown retrieval adapter type: {adapter_type}")
