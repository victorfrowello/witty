"""
Enrichment Module - Knowledge Retrieval and Context Expansion.

DesignSpec 6a: Enrichment with retrieval for quantifier grounding
and context expansion.

Author: Victor Rowello
Sprint: 5
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import uuid
import logging
from datetime import datetime, timezone

from src.witty_types import (
    CNFResult,
    EnrichmentResult,
    ExpandedClaim,
    EnrichmentSource,
    ProvenanceRecord,
    ModuleResult,
)
from src.adapters.retrieval import RetrievalAdapter, MockRetrievalAdapter

logger = logging.getLogger(__name__)

# Module identification
MODULE_ID = "enrichment"
MODULE_VERSION = "0.1.0"


def llm_enrichment(
    input_result: Any,  # CNFResult or ConcisionResult
    ctx: Any,
    llm_adapter: Any,
    retrieval_adapter: Optional[RetrievalAdapter] = None
) -> EnrichmentResult:
    """
    Enrich claims using LLM and retrieval.
    
    DesignSpec 6a.2 Acceptance Criteria:
    - Query retrieval adapter for relevant context
    - Expand claims with retrieved knowledge
    - Record provenance for enrichment sources
    
    Args:
        input_result: CNFResult or ConcisionResult from previous stage
        ctx: Pipeline context
        llm_adapter: LLM adapter for context synthesis
        retrieval_adapter: Optional retrieval adapter for knowledge
        
    Returns:
        EnrichmentResult with expanded claims
    """
    privacy_mode = getattr(ctx.options, 'privacy_mode', 'default')
    
    # Check if retrieval is enabled and not blocked by privacy
    retrieval_enabled = getattr(ctx.options, 'retrieval_enabled', False)
    if privacy_mode == 'strict':
        retrieval_enabled = False
    
    expanded_claims: List[ExpandedClaim] = []
    enrichment_sources: List[EnrichmentSource] = []
    
    # Handle both CNFResult (has clauses) and ConcisionResult (has atomic_candidates)
    if hasattr(input_result, 'clauses'):
        # CNFResult path
        for clause in input_result.clauses:
            claim_id = f"claim_{clause.clause_id}"
            claim_text = " ∨ ".join(clause.literals) if clause.literals else ""
            
            expanded_claims.append(ExpandedClaim(
                claim_id=claim_id,
                text=claim_text,
                origin="input",
                confidence=1.0,
                source_ids=[],
                origin_spans=[]
            ))
    elif hasattr(input_result, 'atomic_candidates'):
        # ConcisionResult path
        for idx, claim in enumerate(input_result.atomic_candidates):
            claim_id = f"claim_{idx}"
            claim_text = claim.text if hasattr(claim, 'text') else str(claim)
            origin_spans = list(claim.origin_spans) if hasattr(claim, 'origin_spans') and claim.origin_spans else []
            
            expanded_claims.append(ExpandedClaim(
                claim_id=claim_id,
                text=claim_text,
                origin="input",
                confidence=1.0,
                source_ids=[],
                origin_spans=origin_spans
            ))
    original_count = len(expanded_claims)
    
    # Perform retrieval if enabled
    if retrieval_enabled and retrieval_adapter is not None:
        try:
            top_k = getattr(ctx.options, 'retrieval_top_k', 3)
            
            # Build query from claims
            query_text = " ".join([c.text for c in expanded_claims[:3]])
            
            # Retrieve relevant context
            retrieval_response = retrieval_adapter.retrieve(query_text, top_k, ctx)
            
            # Add enrichment sources
            for source in retrieval_response.sources:
                enrichment_sources.append(EnrichmentSource(
                    source_id=source.source_id,
                    score=source.score,
                    redacted=source.redacted,
                    source_type="retrieval"
                ))
                
                # If not redacted, we could expand claims with retrieved content
                if not source.redacted and source.content:
                    # Add retrieved content as additional context claims
                    expanded_claims.append(ExpandedClaim(
                        claim_id=f"enriched_{source.source_id}",
                        text=source.content,
                        origin="retrieval",
                        confidence=source.score,
                        source_ids=[source.source_id]
                    ))
                    
        except Exception as e:
            logger.warning(f"Retrieval failed, falling back: {e}")
            # Fall through to deterministic path
    
    return EnrichmentResult(
        expanded_claims=expanded_claims,
        enrichment_sources=enrichment_sources,
        original_claim_count=original_count,
        enriched_claim_count=len(expanded_claims),
        confidence=0.9 if enrichment_sources else 0.8,
        warnings=[]
    )


def deterministic_enrichment(
    input_result: Any,  # CNFResult or ConcisionResult
    ctx: Any
) -> EnrichmentResult:
    """
    Deterministic enrichment without external retrieval.
    
    DesignSpec 6a.3 Fallback:
    - Use local context only
    - No external API calls
    - Maintain provenance chain
    
    Args:
        input_result: CNF result or ConcisionResult from previous stage
        ctx: Pipeline context
        
    Returns:
        EnrichmentResult with input claims only
    """
    expanded_claims: List[ExpandedClaim] = []
    
    # Handle both CNFResult (has clauses) and ConcisionResult (has atomic_candidates)
    if hasattr(input_result, 'clauses'):
        # CNFResult path
        for clause in input_result.clauses:
            claim_id = f"claim_{clause.clause_id}"
            claim_text = " ∨ ".join(clause.literals) if clause.literals else ""
            
            expanded_claims.append(ExpandedClaim(
                claim_id=claim_id,
                text=claim_text,
                origin="input",
                confidence=1.0,
                source_ids=[],
                origin_spans=[]
            ))
    elif hasattr(input_result, 'atomic_candidates'):
        # ConcisionResult path
        for idx, claim in enumerate(input_result.atomic_candidates):
            claim_id = f"claim_{idx}"
            claim_text = claim.text if hasattr(claim, 'text') else str(claim)
            origin_spans = list(claim.origin_spans) if hasattr(claim, 'origin_spans') and claim.origin_spans else []
            
            expanded_claims.append(ExpandedClaim(
                claim_id=claim_id,
                text=claim_text,
                origin="input",
                confidence=1.0,
                source_ids=[],
                origin_spans=origin_spans
            ))
    
    return EnrichmentResult(
        expanded_claims=expanded_claims,
        enrichment_sources=[],
        original_claim_count=len(expanded_claims),
        enriched_claim_count=len(expanded_claims),
        confidence=0.4,  # Low confidence for deterministic fallback per DesignSpec 6a.3
        warnings=["Using deterministic fallback enrichment - no external retrieval"]
    )


def enrich(
    input_result: Any,  # CNFResult or ConcisionResult
    ctx: Any,
    llm_adapter: Optional[Any] = None,
    retrieval_adapter: Optional[RetrievalAdapter] = None
) -> ModuleResult:
    """
    Main enrichment entry point.
    
    Chooses between LLM-assisted and deterministic enrichment
    based on configuration and adapter availability.
    
    Args:
        input_result: CNFResult or ConcisionResult from previous stage
        ctx: Pipeline context
        llm_adapter: Optional LLM adapter
        retrieval_adapter: Optional retrieval adapter
        
    Returns:
        ModuleResult containing EnrichmentResult
    """
    start_time = datetime.now(timezone.utc)
    
    # Decide enrichment path
    retrieval_enabled = getattr(ctx.options, 'retrieval_enabled', False)
    privacy_mode = getattr(ctx.options, 'privacy_mode', 'default')
    
    if retrieval_enabled and privacy_mode != 'strict' and retrieval_adapter is not None:
        result = llm_enrichment(input_result, ctx, llm_adapter, retrieval_adapter)
        enrichment_method = "llm_assisted"
    else:
        result = deterministic_enrichment(input_result, ctx)
        enrichment_method = "deterministic"
    
    # Create provenance record
    provenance = ProvenanceRecord(
        id=str(uuid.uuid4()),
        created_at=start_time,
        module_id=MODULE_ID,
        module_version=MODULE_VERSION,
        enrichment_sources=[s.source_id for s in result.enrichment_sources],
        confidence=result.confidence,
        event_log=[{
            "event": "enrichment_complete",
            "method": enrichment_method,
            "claim_count": len(result.expanded_claims),
            "source_count": len(result.enrichment_sources)
        }]
    )
    
    return ModuleResult(
        payload={
            "expanded_claims": [c.model_dump() for c in result.expanded_claims],
            "enrichment_sources": [s.model_dump() for s in result.enrichment_sources],
            "original_claim_count": result.original_claim_count,
            "enriched_claim_count": result.enriched_claim_count,
            "enrichment_method": enrichment_method
        },
        provenance_record=provenance,
        confidence=result.confidence,
        warnings=result.warnings
    )
