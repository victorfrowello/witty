"""
Pydantic models for Witty, moved into package `src.witty.types`.
This file is copied from src/witty_types.py and slightly refactored.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ModuleStage(str, Enum):
    PREPROCESSING = "preprocessing"
    CONCISION = "concision"
    ENRICHMENT = "enrichment"
    MODALITY = "modality"
    WORLD = "world"
    SYMBOLIZATION = "symbolization"
    CNF = "cnf"
    VALIDATION = "validation"

class ProvenanceRecord(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    module_id: str
    module_version: str
    adapter_id: Optional[str] = None
    prompt_template_id: Optional[str] = None
    adapter_request_id: Optional[str] = None
    origin_spans: List[Tuple[int, int]] = Field(default_factory=list)
    enrichment_sources: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    ambiguity_flags: List[str] = Field(default_factory=list)
    reduction_rationale: Optional[str] = None
    event_log: List[Dict[str, Any]] = Field(default_factory=list)

class ModuleResult(BaseModel):
    payload: Dict[str, Any]
    provenance_record: ProvenanceRecord
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)

class FormalizeOptions(BaseModel):
    """Runtime options controlling pipeline behavior.

    Kept minimal for Sprint 1. CLI may set `reproducible_mode` and `verbosity`.
    """

    retrieval_enabled: bool = False
    top_k_symbolizations: int = 1
    llm_provider: Optional[str] = None
    # Verbosity may be an int (legacy) or a short string coming from the CLI
    verbosity: Union[int, str] = 0
    quantifier_reduction_detail: bool = False
    allow_modal_advanced_cnf: bool = False
    privacy_mode: str = "default"
    # Whether to run the pipeline deterministically (mock/cached adapters)
    reproducible_mode: bool = False

class AtomicClaim(BaseModel):
    text: str
    symbol: Optional[str] = None
    origin_spans: List[Tuple[int, int]] = Field(default_factory=list)
    modal_context: Optional[str] = None
    provenance: Optional[ProvenanceRecord] = None
    def __contains__(self, item: str) -> bool:
        try:
            if hasattr(self, item):
                return True
            return item in getattr(self, "model_fields", {})
        except Exception:
            return False

class ConcisionResult(BaseModel):
    canonical_text: str
    atomic_candidates: List[AtomicClaim]
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    explanations: Optional[str] = None
    error: Optional[str] = None

class FormalizationResult(BaseModel):
    request_id: str
    original_text: str
    canonical_text: Optional[str] = None
    enrichment_sources: List[str] = Field(default_factory=list)
    atomic_claims: List[AtomicClaim] = Field(default_factory=list)
    legend: Dict[str, str] = Field(default_factory=dict)
    logical_form_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    chosen_logical_form: Optional[Dict[str, Any]] = None
    cnf: Optional[str] = None
    cnf_clauses: List[List[str]] = Field(default_factory=list)
    modal_metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
