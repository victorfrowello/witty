"""
Modal Detection Module - Modal Operator Identification.

DesignSpec 6a.2: Modal detection identifies necessity, possibility,
obligation, and permission operators.

Author: Victor Rowello
Sprint: 5
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
import uuid
import re
import logging
from datetime import datetime, timezone

from src.witty_types import (
    EnrichmentResult,
    ModalResult,
    ModalContext,
    ProvenanceRecord,
    ModuleResult,
)

logger = logging.getLogger(__name__)

# Module identification
MODULE_ID = "modality"
MODULE_VERSION = "0.1.0"


# Modal keyword mappings per DesignSpec 6a.2
MODAL_KEYWORDS: Dict[str, str] = {
    # Necessity (□)
    "must": "necessity",
    "necessarily": "necessity",
    "certainly": "necessity",
    "always": "necessity",
    "required": "necessity",
    "have to": "necessity",
    "has to": "necessity",
    
    # Possibility (◇)
    "might": "possibility",
    "may": "possibility",
    "possibly": "possibility",
    "possible": "possibility",
    "could": "possibility",
    "can": "possibility",
    "perhaps": "possibility",
    
    # Obligation (O)
    "should": "obligation",
    "ought": "obligation",
    "ought to": "obligation",
    "supposed to": "obligation",
    
    # Permission (P)
    "allowed": "permission",
    "permitted": "permission",
    "may": "permission",  # Context-dependent, also possibility
}

# Operator precedence for selecting modal type when multiple detected
MODAL_PRECEDENCE = ["necessity", "obligation", "possibility", "permission"]


def _detect_modal_keywords(text: str) -> List[Dict[str, Any]]:
    """
    Detect modal keywords in text.
    
    Returns list of detected modals with positions.
    """
    text_lower = text.lower()
    detections = []
    
    # Sort keywords by length (longest first) to match multi-word phrases
    sorted_keywords = sorted(MODAL_KEYWORDS.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        for match in re.finditer(pattern, text_lower):
            modal_type = MODAL_KEYWORDS[keyword]
            detections.append({
                "keyword": keyword,
                "modal_type": modal_type,
                "start": match.start(),
                "end": match.end()
            })
    
    return detections


def _select_frame(modal_types: Set[str], ctx: Any) -> str:
    """
    Select appropriate modal frame based on detected modalities.
    
    DesignSpec 6a.2: Default to S5 frame.
    """
    # Check for explicit frame in options
    options = getattr(ctx, 'options', None)
    explicit_frame = getattr(options, 'modal_frame', None) if options else None
    if explicit_frame and explicit_frame != 'auto':
        return explicit_frame
    
    # Default to S5 per spec
    if not modal_types:
        return "none"
    
    # S5 handles necessity and possibility well
    if "necessity" in modal_types or "possibility" in modal_types:
        return "S5"
    
    # Deontic modality (obligation/permission) could use D frame
    if "obligation" in modal_types or "permission" in modal_types:
        return "S5"  # Still use S5 as default per spec
    
    return "S5"


def detect_modal(
    input_result: Any,
    ctx: Any
) -> ModuleResult:
    """
    Detect modal operators in claims.
    
    DesignSpec 6a.2 Acceptance Criteria:
    - Identify necessity, possibility, obligation, permission
    - Keyword detection: must, should, possible, ought
    - Default to S5 frame
    
    Args:
        input_result: EnrichmentResult or ConcisionResult with claims
        ctx: Pipeline context
        
    Returns:
        ModuleResult containing ModalResult
    """
    modal_contexts: List[ModalContext] = []
    all_modal_types: Set[str] = set()
    
    # Support both EnrichmentResult (expanded_claims) and ConcisionResult (atomic_candidates)
    if hasattr(input_result, 'expanded_claims'):
        claims = input_result.expanded_claims
    elif hasattr(input_result, 'atomic_candidates'):
        claims = input_result.atomic_candidates
    else:
        claims = []
    
    for claim in claims:
        if not claim.text:
            continue
        
        # Detect modal keywords in claim text
        detections = _detect_modal_keywords(claim.text)
        
        if detections:
            # Use highest precedence modal type if multiple detected
            detected_types = {d["modal_type"] for d in detections}
            all_modal_types.update(detected_types)
            
            # Select primary modal type by precedence
            primary_type = None
            primary_keyword = None
            for modal_type in MODAL_PRECEDENCE:
                if modal_type in detected_types:
                    primary_type = modal_type
                    # Find the keyword for this type
                    for d in detections:
                        if d["modal_type"] == modal_type:
                            primary_keyword = d["keyword"]
                            break
                    break
            
            if primary_type:
                # Handle both ExpandedClaim (claim_id) and AtomicClaim (symbol)
                claim_id = getattr(claim, 'claim_id', None) or getattr(claim, 'symbol', 'unknown')
                modal_contexts.append(ModalContext(
                    claim_id=claim_id,
                    modal_type=primary_type,
                    operator_text=primary_keyword or "",
                    frame="S5",  # Default per spec
                    confidence=0.9
                ))
    
    # Select overall frame
    frame_selection = _select_frame(all_modal_types, ctx)
    
    start_time = datetime.now(timezone.utc)
    
    modal_result = ModalResult(
        modal_contexts=modal_contexts,
        frame_selection=frame_selection,
        has_modality=len(modal_contexts) > 0,
        confidence=0.9 if modal_contexts else 1.0,
        warnings=[]
    )
    
    # Create provenance record
    provenance = ProvenanceRecord(
        id=str(uuid.uuid4()),
        created_at=start_time,
        module_id=MODULE_ID,
        module_version=MODULE_VERSION,
        confidence=modal_result.confidence,
        event_log=[{
            "event": "modal_detection_complete",
            "modality_count": len(modal_result.modal_contexts),
            "frame_selection": modal_result.frame_selection,
            "detected_types": list({mc.modal_type for mc in modal_result.modal_contexts})
        }]
    )
    
    return ModuleResult(
        payload=modal_result.model_dump(),
        provenance_record=provenance,
        confidence=modal_result.confidence,
        warnings=modal_result.warnings
    )


def detect_modal_with_provenance(
    enrichment_result: EnrichmentResult,
    ctx: Any
) -> ModuleResult:
    """
    Detect modality with full provenance tracking.
    
    Args:
        enrichment_result: Enrichment result with expanded claims
        ctx: Pipeline context
        
    Returns:
        ModuleResult containing ModalResult
    """
    start_time = datetime.now(timezone.utc)
    
    result = detect_modal(enrichment_result, ctx)
    
    # Create provenance record
    provenance = ProvenanceRecord(
        id=str(uuid.uuid4()),
        created_at=start_time,
        module_id=MODULE_ID,
        module_version=MODULE_VERSION,
        confidence=result.confidence,
        event_log=[{
            "event": "modal_detection_complete",
            "modality_count": len(result.modal_contexts),
            "frame_selection": result.frame_selection,
            "detected_types": list({mc.modal_type for mc in result.modal_contexts})
        }]
    )
    
    return ModuleResult(
        payload={
            "modal_contexts": [mc.model_dump() for mc in result.modal_contexts],
            "frame_selection": result.frame_selection,
            "has_modality": result.has_modality
        },
        provenance_record=provenance,
        confidence=result.confidence,
        warnings=result.warnings
    )
