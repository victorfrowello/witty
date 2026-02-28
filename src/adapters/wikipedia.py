"""
WikipediaAdapter for live knowledge retrieval.

Uses the Wikipedia REST API to fetch article summaries for entity grounding
and enrichment. No API key required.

Author: Victor Rowello
Sprint: 7
"""
from __future__ import annotations
import urllib.parse
import urllib.request
import json
from typing import Any, Dict, List, Optional
import logging

from src.adapters.retrieval import BaseRetrievalAdapter
from src.witty_types import RetrievalSource

logger = logging.getLogger(__name__)


class WikipediaAdapter(BaseRetrievalAdapter):
    """
    Retrieval adapter using Wikipedia REST API.
    
    Features:
    - No API key required
    - Fetches article summaries for entity context
    - Search endpoint for entity discovery
    - Respects Wikipedia API guidelines (User-Agent, rate limits)
    """
    
    SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
    SEARCH_URL = "https://en.wikipedia.org/w/api.php"
    USER_AGENT = "Witty/1.0 (Epistemic Formalization Engine; https://github.com/victorfrowello/witty)"
    
    def __init__(
        self,
        adapter_id: str = "wikipedia",
        version: str = "1.0",
        timeout: float = 10.0
    ):
        """
        Initialize WikipediaAdapter.
        
        Args:
            adapter_id: Identifier for provenance tracking
            version: Adapter version
            timeout: HTTP request timeout in seconds
        """
        super().__init__(adapter_id, version)
        self.timeout = timeout
    
    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to Wikipedia API.
        
        Args:
            url: Full URL to request
            
        Returns:
            Parsed JSON response or None on failure
        """
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": self.USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.debug(f"Wikipedia article not found: {url}")
            else:
                logger.warning(f"Wikipedia API HTTP error {e.code}: {url}")
            return None
        except urllib.error.URLError as e:
            logger.warning(f"Wikipedia API URL error: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Wikipedia API JSON decode error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Wikipedia API unexpected error: {e}")
            return None
    
    def _search_wikipedia(self, query: str, limit: int = 5) -> List[str]:
        """
        Search Wikipedia for article titles matching query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of article titles
        """
        params = {
            "action": "opensearch",
            "search": query,
            "limit": str(limit),
            "namespace": "0",
            "format": "json"
        }
        url = f"{self.SEARCH_URL}?{urllib.parse.urlencode(params)}"
        
        result = self._make_request(url)
        if result and len(result) >= 2:
            # OpenSearch returns [query, [titles], [descriptions], [urls]]
            return result[1]
        return []
    
    def _get_summary(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get article summary for a title.
        
        Args:
            title: Wikipedia article title
            
        Returns:
            Summary data or None
        """
        # URL-encode the title, replacing spaces with underscores
        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        url = f"{self.SUMMARY_URL}{encoded_title}"
        return self._make_request(url)
    
    def _do_retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> List[RetrievalSource]:
        """
        Retrieve Wikipedia article summaries for query.
        
        Strategy:
        1. Search Wikipedia for matching articles
        2. Fetch summary for each match
        3. Return as RetrievalSource objects
        
        Args:
            query: Search query (entity name, concept, etc.)
            top_k: Maximum results to return
            ctx: Pipeline context
            
        Returns:
            List of RetrievalSource with Wikipedia content
        """
        sources = []
        
        # Search for matching articles
        titles = self._search_wikipedia(query, limit=top_k)
        
        if not titles:
            logger.debug(f"No Wikipedia articles found for: {query}")
            return sources
        
        # Fetch summary for each title
        for i, title in enumerate(titles[:top_k]):
            summary = self._get_summary(title)
            
            if summary and "extract" in summary:
                source = RetrievalSource(
                    source_id=f"wikipedia_{i}_{hash(title) % 10000:04d}",
                    content=summary.get("extract", ""),
                    score=1.0 - (i * 0.1),  # Decrease score by position
                    redacted=False,
                    metadata={
                        "type": "wikipedia",
                        "title": summary.get("title", title),
                        "url": summary.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "description": summary.get("description", ""),
                        "page_id": summary.get("pageid")
                    }
                )
                sources.append(source)
        
        return sources
