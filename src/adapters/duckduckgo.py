"""
DuckDuckGoAdapter for live knowledge retrieval.

Uses DuckDuckGo Instant Answer API for web search results.
No API key required. Used as fallback when Wikipedia doesn't have results.

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


class DuckDuckGoAdapter(BaseRetrievalAdapter):
    """
    Retrieval adapter using DuckDuckGo Instant Answer API.
    
    Features:
    - No API key required
    - Web search for current events and niche topics
    - Fallback when Wikipedia doesn't have coverage
    - Respects DuckDuckGo guidelines
    """
    
    API_URL = "https://api.duckduckgo.com/"
    USER_AGENT = "Witty/1.0 (Epistemic Formalization Engine)"
    
    def __init__(
        self,
        adapter_id: str = "duckduckgo",
        version: str = "1.0",
        timeout: float = 10.0
    ):
        """
        Initialize DuckDuckGoAdapter.
        
        Args:
            adapter_id: Identifier for provenance tracking
            version: Adapter version
            timeout: HTTP request timeout in seconds
        """
        super().__init__(adapter_id, version)
        self.timeout = timeout
    
    def _make_request(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Make request to DuckDuckGo Instant Answer API.
        
        Args:
            query: Search query
            
        Returns:
            Parsed JSON response or None on failure
        """
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        url = f"{self.API_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": self.USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            logger.warning(f"DuckDuckGo API HTTP error {e.code}")
            return None
        except urllib.error.URLError as e:
            logger.warning(f"DuckDuckGo API URL error: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"DuckDuckGo API JSON decode error: {e}")
            return None
        except Exception as e:
            logger.warning(f"DuckDuckGo API unexpected error: {e}")
            return None
    
    def _do_retrieve(
        self,
        query: str,
        top_k: int,
        ctx: Any
    ) -> List[RetrievalSource]:
        """
        Retrieve DuckDuckGo Instant Answer results.
        
        DuckDuckGo Instant Answer API returns:
        - Abstract: Main summary text
        - AbstractSource: Source of the abstract
        - RelatedTopics: Related search results
        
        Args:
            query: Search query
            top_k: Maximum results to return
            ctx: Pipeline context
            
        Returns:
            List of RetrievalSource with DuckDuckGo content
        """
        sources = []
        
        result = self._make_request(query)
        if not result:
            logger.debug(f"No DuckDuckGo results for: {query}")
            return sources
        
        idx = 0
        
        # Main abstract (if available)
        abstract = result.get("Abstract", "")
        if abstract and idx < top_k:
            source = RetrievalSource(
                source_id=f"ddg_abstract_{hash(query) % 10000:04d}",
                content=abstract,
                score=1.0,
                redacted=False,
                metadata={
                    "type": "duckduckgo_abstract",
                    "title": result.get("Heading", query),
                    "url": result.get("AbstractURL", ""),
                    "source": result.get("AbstractSource", ""),
                    "entity_type": result.get("Type", "")
                }
            )
            sources.append(source)
            idx += 1
        
        # Answer (instant answer, if available)
        answer = result.get("Answer", "")
        if answer and idx < top_k:
            source = RetrievalSource(
                source_id=f"ddg_answer_{hash(query) % 10000:04d}",
                content=answer,
                score=0.95,
                redacted=False,
                metadata={
                    "type": "duckduckgo_answer",
                    "title": "Instant Answer",
                    "answer_type": result.get("AnswerType", "")
                }
            )
            sources.append(source)
            idx += 1
        
        # Related topics
        related_topics = result.get("RelatedTopics", [])
        for topic in related_topics:
            if idx >= top_k:
                break
            
            # Skip nested topic groups
            if "Topics" in topic:
                continue
            
            text = topic.get("Text", "")
            if text:
                source = RetrievalSource(
                    source_id=f"ddg_related_{idx}_{hash(text) % 10000:04d}",
                    content=text,
                    score=0.9 - (idx * 0.05),
                    redacted=False,
                    metadata={
                        "type": "duckduckgo_related",
                        "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                        "url": topic.get("FirstURL", "")
                    }
                )
                sources.append(source)
                idx += 1
        
        return sources
