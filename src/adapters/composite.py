"""
CompositeRetrievalAdapter - Default retrieval with Wikipedia + DuckDuckGo fallback.

Tries Wikipedia first (authoritative, structured) and falls back to DuckDuckGo
if Wikipedia returns no results. No API keys required.

Author: Victor Rowello
Sprint: 7
"""
from __future__ import annotations
from typing import Any, List
import logging

from src.adapters.retrieval import BaseRetrievalAdapter
from src.adapters.wikipedia import WikipediaAdapter
from src.adapters.duckduckgo import DuckDuckGoAdapter
from src.witty_types import RetrievalSource, RetrievalResponse

logger = logging.getLogger(__name__)


class CompositeRetrievalAdapter(BaseRetrievalAdapter):
    """
    Composite retrieval adapter that combines Wikipedia and DuckDuckGo.
    
    Strategy (deterministic, no LLM routing):
    1. Try Wikipedia first - best for named entities and concepts
    2. If Wikipedia returns no results, fall back to DuckDuckGo
    3. Return combined results with source tracking
    
    Features:
    - No API keys required
    - Zero configuration for users
    - Deterministic fallback logic
    - Full provenance tracking
    """
    
    def __init__(
        self,
        adapter_id: str = "composite",
        version: str = "1.0",
        timeout: float = 10.0
    ):
        """
        Initialize CompositeRetrievalAdapter.
        
        Args:
            adapter_id: Identifier for provenance tracking
            version: Adapter version
            timeout: HTTP request timeout for sub-adapters
        """
        super().__init__(adapter_id, version)
        self.wikipedia = WikipediaAdapter(timeout=timeout)
        self.duckduckgo = DuckDuckGoAdapter(timeout=timeout)
    
    def _do_retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> List[RetrievalSource]:
        """
        Retrieve from Wikipedia, fallback to DuckDuckGo.
        
        Args:
            query: Search query
            top_k: Maximum results to return
            ctx: Pipeline context
            
        Returns:
            List of RetrievalSource from best available source
        """
        # Try Wikipedia first
        logger.debug(f"CompositeRetrieval: Trying Wikipedia for '{query}'")
        wiki_sources = self.wikipedia._do_retrieve(query, top_k, ctx)
        
        if wiki_sources:
            logger.debug(f"CompositeRetrieval: Wikipedia returned {len(wiki_sources)} results")
            return wiki_sources
        
        # Fallback to DuckDuckGo
        logger.debug(f"CompositeRetrieval: Wikipedia empty, falling back to DuckDuckGo")
        ddg_sources = self.duckduckgo._do_retrieve(query, top_k, ctx)
        
        if ddg_sources:
            logger.debug(f"CompositeRetrieval: DuckDuckGo returned {len(ddg_sources)} results")
        else:
            logger.debug(f"CompositeRetrieval: No results from either source for '{query}'")
        
        return ddg_sources
    
    def retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> RetrievalResponse:
        """
        Retrieve with full response including fallback tracking.
        
        Overrides parent to add fallback metadata.
        
        Args:
            query: Search query
            top_k: Maximum results
            ctx: Pipeline context
            
        Returns:
            RetrievalResponse with sources and fallback info
        """
        response = super().retrieve(query, top_k, ctx)
        
        # Track which adapter provided results
        if response.sources:
            first_source_type = response.sources[0].metadata.get("type", "")
            if first_source_type.startswith("wikipedia"):
                response.metadata = response.metadata or {}
                response.metadata["retrieval_source"] = "wikipedia"
            elif first_source_type.startswith("duckduckgo"):
                response.metadata = response.metadata or {}
                response.metadata["retrieval_source"] = "duckduckgo"
                response.metadata["fallback_used"] = True
        
        return response
