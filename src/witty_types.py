"""
Pydantic models used across the Witty pipeline.

This module defines the core data structures for the formalization pipeline,
including provenance tracking, module results, and formalization outputs.
All models use Pydantic for validation and serialization.

Note: Renamed from types.py to witty_types.py to avoid name collision with
the Python standard library 'types' module.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ModuleStage(str, Enum):
    """
    Enumeration of pipeline processing stages.
    
    Each stage represents a distinct phase in the formalization pipeline,
    allowing for structured tracking and validation of processing flow.
    """
    PREPROCESSING = "preprocessing"      # Text normalization and segmentation
    CONCISION = "concision"              # Extraction of atomic claims
    ENRICHMENT = "enrichment"            # Context and knowledge enrichment
    MODALITY = "modality"                # Modal operator detection
    WORLD = "world"                      # Possible worlds construction
    SYMBOLIZATION = "symbolization"      # Symbol assignment and legend creation
    CNF = "cnf"                          # Conjunctive normal form conversion
    VALIDATION = "validation"            # Output validation and verification


class ProvenanceRecord(BaseModel):
    """
    Comprehensive tracking record for pipeline transformations.
    
    Captures metadata about each processing step to ensure transparency,
    reproducibility, and debugging capability. Every module that transforms
    data should create a ProvenanceRecord documenting the transformation.
    
    Attributes:
        id: Unique identifier for this provenance record
        created_at: Timestamp when this record was created (UTC timezone-aware)
        module_id: Identifier of the module that created this record
        module_version: Version of the module for reproducibility
        adapter_id: Optional LLM adapter identifier if an adapter was used
        prompt_template_id: Optional prompt template identifier
        adapter_request_id: Optional request ID from the adapter
        origin_spans: Character spans in the original text this record refers to
        enrichment_sources: External sources used for enrichment
        confidence: Confidence score for this transformation (0.0 to 1.0)
        ambiguity_flags: List of detected ambiguities or uncertainties
        reduction_rationale: Explanation for reductions or simplifications
        event_log: Detailed log of events during processing
    """
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
    """
    Standardized result structure for pipeline modules.
    
    Each pipeline module returns a ModuleResult containing the transformation
    payload, provenance tracking, confidence score, and any warnings.
    
    Attributes:
        payload: Module-specific output data as a dictionary
        provenance_record: Provenance tracking for this transformation
        confidence: Overall confidence in this result (0.0 to 1.0)
        warnings: List of warning messages for non-fatal issues
    """
    payload: Dict[str, Any]
    provenance_record: ProvenanceRecord
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class FormalizeOptions(BaseModel):
    """
    Runtime configuration options for the formalization pipeline.
    
    Controls pipeline behavior including LLM provider selection, verbosity,
    and feature flags. Designed to be minimal for Sprint 1 with extensibility
    for future enhancements.
    
    Attributes:
        retrieval_enabled: Whether to enable knowledge retrieval/enrichment
        top_k_symbolizations: Number of top symbolization candidates to keep
        llm_provider: Optional LLM provider identifier
        verbosity: Logging verbosity (integer or string like 'normal'/'debug')
        quantifier_reduction_detail: Enable detailed quantifier reduction logging
        allow_modal_advanced_cnf: Allow advanced modal CNF transformations
        privacy_mode: Privacy level ('default', 'strict', etc.)
        reproducible_mode: Use deterministic/cached adapters for reproducibility
    """
    retrieval_enabled: bool = False
    top_k_symbolizations: int = 1
    llm_provider: Optional[str] = None
    verbosity: Union[int, str] = 0
    quantifier_reduction_detail: bool = False
    allow_modal_advanced_cnf: bool = False
    privacy_mode: str = "default"
    reproducible_mode: bool = False


class AtomicClaim(BaseModel):
    """
    Represents a single atomic claim extracted from natural language.
    
    Atomic claims are the fundamental units of formalization - indivisible
    statements that can be assigned truth values and formal symbols.
    
    Attributes:
        text: The natural language text of the claim
        symbol: Formal symbol assigned to this claim (e.g., 'P1', 'Q2')
        origin_spans: Character spans in the original text this claim derives from
        modal_context: Optional modal context (necessity, possibility, etc.)
        provenance: Optional provenance tracking for this claim
    """
    text: str
    symbol: Optional[str] = None
    origin_spans: List[Tuple[int, int]] = Field(default_factory=list)
    modal_context: Optional[str] = None
    provenance: Optional[ProvenanceRecord] = None


class ConcisionResult(BaseModel):
    """
    Result from the concision stage of the pipeline.
    
    The concision stage extracts atomic claims from preprocessed text and
    produces a canonical simplified representation.
    
    Attributes:
        canonical_text: Simplified, canonical version of the input text
        atomic_candidates: List of extracted atomic claims
        confidence: Overall confidence in the concision result
        explanations: Optional human-readable explanation of the concision
        error: Optional error message if concision failed
    """
    canonical_text: str
    atomic_candidates: List[AtomicClaim]
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    explanations: Optional[str] = None
    error: Optional[str] = None


class FormalizationResult(BaseModel):
    """
    Complete result of the formalization pipeline.
    
    Represents the full output of formalizing natural language into logic,
    including all intermediate representations, metadata, and provenance.
    This is the primary output format returned to users.
    
    Attributes:
        request_id: Unique identifier for this formalization request
        original_text: Original input text before any processing
        canonical_text: Simplified canonical version of the input
        enrichment_sources: External knowledge sources used for enrichment
        atomic_claims: List of extracted atomic claims with symbols
        legend: Mapping from symbols to their natural language meanings
        logical_form_candidates: Alternative logical form representations
        chosen_logical_form: The selected logical form from candidates
        cnf: Conjunctive normal form representation
        cnf_clauses: CNF broken into individual clauses
        modal_metadata: Metadata about modal operators detected
        warnings: Non-fatal warnings encountered during processing
        confidence: Overall confidence in the formalization result
        provenance: Complete provenance chain for all transformations
    """
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
