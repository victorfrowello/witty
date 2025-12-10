"""
Symbolization Module for Witty Pipeline.

This module assigns deterministic propositional symbols (P1, P2, P3, ...) to
atomic claims and builds a legend mapping symbols to their natural language
meanings. The symbolization process is deterministic and reproducible:
- Claims are ordered by their first origin span (earliest appearance in text)
- Duplicate claim texts receive the same symbol
- Symbol assignment is stable across runs with same input

Key Features:
- Deterministic symbol assignment based on origin spans
- Legend creation mapping symbols to claim text
- Extended legend with metadata (origin spans, provenance IDs)
- Duplicate claim detection and unification
- Validation and warning generation for edge cases

Algorithm:
    1. Sort atomic claims by first origin span start position
    2. Assign symbols P1, P2, P3, ... in order
    3. Detect duplicates: same claim text → same symbol
    4. Build legend: {symbol: claim_text}
    5. Build extended_legend with full metadata

Author: Victor Rowello
Sprint: 2, Task: 4
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from src.witty_types import (
    AtomicClaim,
    ModuleResult,
    ProvenanceRecord,
    SymbolizerResult,
    WorldResult,
    ConcisionResult,
)
from src.pipeline.orchestrator import AgentContext, make_provenance_id


def assign_symbols(
    atomic_claims: List[AtomicClaim],
    ctx: AgentContext
) -> Tuple[Dict[str, str], List[AtomicClaim], Dict[str, Dict[str, Any]]]:
    """
    Assign deterministic symbols P1, P2, ... to atomic claims.
    
    Symbols are assigned in deterministic order based on the first origin span
    of each claim. Claims with identical text receive the same symbol. This
    ensures reproducibility across runs.
    
    Args:
        atomic_claims: List of atomic claims to symbolize
        ctx: Agent context with request metadata and configuration
        
    Returns:
        Tuple of:
        - legend: {symbol: claim_text} mapping
        - claims_with_symbols: Updated atomic claims with symbols assigned
        - extended_legend: {symbol: {text, origin_spans, provenance_id, ...}}
        
    Algorithm:
        1. Create indexed list of (claim, original_index)
        2. Sort by first origin span start position (deterministic ordering)
        3. Track seen claim texts to detect duplicates
        4. Assign P1, P2, ... sequentially, reusing for duplicates
        5. Build legend and extended_legend
        
    Examples:
        >>> claims = [
        ...     AtomicClaim(text="it rains", origin_spans=[(3, 11)]),
        ...     AtomicClaim(text="match cancelled", origin_spans=[(16, 31)])
        ... ]
        >>> legend, claims_out, ext = assign_symbols(claims, ctx)
        >>> legend
        {'P1': 'it rains', 'P2': 'match cancelled'}
        >>> claims_out[0].symbol
        'P1'
        
    Note:
        - Claims without origin spans are sorted last
        - Empty claim text is allowed but generates a warning
        - Determinism guaranteed by stable sort on origin spans
    """
    # Handle empty input
    if not atomic_claims:
        return {}, [], {}
    
    # Create indexed list for stable ordering
    # Track original index to preserve relative order for claims at same position
    indexed_claims = list(enumerate(atomic_claims))
    
    # Sort by first origin span start position, then by original index (stable sort)
    # Claims without origin spans are sorted to the end
    def sort_key(item: Tuple[int, AtomicClaim]) -> Tuple[int, int]:
        index, claim = item
        if claim.origin_spans and len(claim.origin_spans) > 0:
            # Sort by first origin span start position
            return (claim.origin_spans[0][0], index)
        else:
            # Claims without origin spans go last, preserving original order
            return (float('inf'), index)
    
    sorted_indexed = sorted(indexed_claims, key=sort_key)
    
    # Track seen claim texts to detect duplicates
    # Map: normalized_claim_text -> symbol
    text_to_symbol: Dict[str, str] = {}
    
    # Track next symbol number to assign
    next_symbol_num = 1
    
    # Build output structures
    legend: Dict[str, str] = {}
    extended_legend: Dict[str, Dict[str, Any]] = {}
    claims_with_symbols: List[AtomicClaim] = []
    
    # Assign symbols in sorted order
    for original_index, claim in sorted_indexed:
        # Normalize claim text for duplicate detection (strip whitespace, lowercase)
        normalized_text = claim.text.strip().lower()
        
        # Check if we've seen this claim text before
        if normalized_text in text_to_symbol:
            # Reuse existing symbol for duplicate claim
            symbol = text_to_symbol[normalized_text]
        else:
            # Assign new symbol
            symbol = f"P{next_symbol_num}"
            text_to_symbol[normalized_text] = symbol
            next_symbol_num += 1
            
            # Add to legend (use original text, not normalized)
            legend[symbol] = claim.text.strip()
        
        # Create updated claim with symbol assigned
        # Preserve all original claim fields
        updated_claim = AtomicClaim(
            text=claim.text,
            symbol=symbol,
            origin_spans=claim.origin_spans,
            modal_context=claim.modal_context,
            provenance=claim.provenance
        )
        claims_with_symbols.append(updated_claim)
        
        # Build extended legend entry (only once per symbol)
        if symbol not in extended_legend:
            extended_legend[symbol] = {
                "text": claim.text.strip(),
                "origin_spans": claim.origin_spans,
                "provenance_id": claim.provenance.id if claim.provenance else None,
                "modal_context": claim.modal_context,
                "first_appearance_index": original_index
            }
    
    return legend, claims_with_symbols, extended_legend


def symbolizer(
    input_result: WorldResult | ConcisionResult | Dict[str, Any],
    ctx: AgentContext
) -> ModuleResult:
    """
    Main symbolization function for the pipeline.
    
    Takes atomic claims from world construction or concision stages and assigns
    deterministic propositional symbols. Returns a ModuleResult containing
    SymbolizerResult with legend, symbolized claims, and metadata.
    
    Args:
        input_result: Either WorldResult or ConcisionResult containing atomic_claims,
                     or a dict with an 'atomic_claims' key
        ctx: Agent context for provenance and configuration
        
    Returns:
        ModuleResult containing SymbolizerResult payload and provenance
        
    Raises:
        ValueError: If input_result doesn't contain atomic_claims
        
    Algorithm:
        1. Extract atomic_claims from input (WorldResult, ConcisionResult, or dict)
        2. Call assign_symbols() to generate symbols and legend
        3. Build SymbolizerResult with legend and symbolized claims
        4. Create provenance record documenting the transformation
        5. Return ModuleResult with payload and provenance
        
    Examples:
        >>> from src.witty_types import AtomicClaim, ConcisionResult
        >>> claims = [AtomicClaim(text="it rains", origin_spans=[(0, 8)])]
        >>> conc_result = ConcisionResult(
        ...     canonical_text="if it rains",
        ...     atomic_candidates=claims
        ... )
        >>> result = symbolizer(conc_result, ctx)
        >>> result.payload['legend']
        {'P1': 'it rains'}
        
    Note:
        - Handles both WorldResult and ConcisionResult inputs
        - Generates warnings for edge cases (empty claims, missing spans)
        - Always produces deterministic output for same input + ctx
    """
    # Extract atomic claims from input
    # Support multiple input types: WorldResult, ConcisionResult, or dict
    atomic_claims: List[AtomicClaim] = []
    
    if isinstance(input_result, WorldResult):
        atomic_claims = input_result.atomic_claims
    elif isinstance(input_result, ConcisionResult):
        # ConcisionResult uses atomic_candidates instead of atomic_claims
        atomic_claims = input_result.atomic_candidates
    elif isinstance(input_result, dict):
        # Handle dict input (for flexibility)
        if 'atomic_claims' in input_result:
            atomic_claims = input_result['atomic_claims']
        elif 'atomic_candidates' in input_result:
            atomic_claims = input_result['atomic_candidates']
        else:
            raise ValueError(
                "Input dict must contain 'atomic_claims' or 'atomic_candidates' key"
            )
    else:
        raise ValueError(
            f"Unsupported input type: {type(input_result)}. "
            "Expected WorldResult, ConcisionResult, or dict"
        )
    
    # Collect warnings for edge cases
    warnings: List[str] = []
    
    # Validate input
    if not atomic_claims:
        warnings.append("No atomic claims provided to symbolizer - empty result")
    
    # Check for claims without origin spans
    claims_without_spans = [c for c in atomic_claims if not c.origin_spans]
    if claims_without_spans:
        warnings.append(
            f"{len(claims_without_spans)} claim(s) missing origin spans - "
            "may affect deterministic ordering"
        )
    
    # Check for empty claim text
    empty_claims = [c for c in atomic_claims if not c.text or not c.text.strip()]
    if empty_claims:
        warnings.append(
            f"{len(empty_claims)} claim(s) have empty text - "
            "will generate symbols but may indicate upstream issue"
        )
    
    # Assign symbols
    legend, claims_with_symbols, extended_legend = assign_symbols(atomic_claims, ctx)
    
    # Calculate confidence based on data quality
    # Start with perfect confidence, reduce for warnings
    confidence = 1.0
    if claims_without_spans:
        # Reduce confidence if origin spans missing (affects determinism)
        confidence -= 0.1 * min(len(claims_without_spans) / max(len(atomic_claims), 1), 0.3)
    if empty_claims:
        # Reduce confidence for empty claims
        confidence -= 0.15 * min(len(empty_claims) / max(len(atomic_claims), 1), 0.2)
    
    # Ensure confidence stays in valid range
    confidence = max(0.5, min(1.0, confidence))
    
    # Build SymbolizerResult
    symbolizer_result = SymbolizerResult(
        legend=legend,
        atomic_claims=claims_with_symbols,
        extended_legend=extended_legend,
        confidence=confidence,
        warnings=warnings
    )
    
    # Create provenance record
    # Generate deterministic ID based on input claims
    input_text = "|".join(sorted([c.text for c in atomic_claims]))
    provenance_id = make_provenance_id(
        normalized_input=input_text,
        module_id="symbolizer",
        module_version="1.0.0",
        salt=ctx.deterministic_salt
    )
    
    provenance = ProvenanceRecord(
        id=provenance_id,
        created_at=datetime.now(timezone.utc),
        module_id="symbolizer",
        module_version="1.0.0",
        confidence=confidence,
        event_log=[
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event_type": "symbolization",
                "message": f"Assigned {len(legend)} symbols to {len(atomic_claims)} claims",
                "meta": {
                    "num_symbols": len(legend),
                    "num_claims": len(atomic_claims),
                    "num_duplicates": len(atomic_claims) - len(legend),
                    "has_warnings": len(warnings) > 0
                }
            }
        ]
    )
    
    # Add warning events to event log
    for warning in warnings:
        provenance.event_log.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": "warning",
            "message": warning,
            "meta": {}
        })
    
    # Convert SymbolizerResult to dict for ModuleResult payload
    payload = symbolizer_result.model_dump()
    
    # Return ModuleResult
    return ModuleResult(
        payload=payload,
        provenance_record=provenance,
        confidence=confidence,
        warnings=warnings
    )
