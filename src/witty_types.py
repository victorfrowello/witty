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
        llm_model: Specific LLM model to use (e.g., 'llama-3.3-70b-versatile')
        verbosity: Logging verbosity (integer or string like 'normal'/'debug')
        quantifier_reduction_detail: Enable detailed quantifier reduction logging
        allow_modal_advanced_cnf: Allow advanced modal CNF transformations
        privacy_mode: Privacy level ('default', 'strict', etc.)
        reproducible_mode: Use deterministic/cached adapters for reproducibility
        live_mode: Enable live LLM integration (deprecated, use reproducible_mode=False)
        no_retrieval: Opt out of automatic retrieval enrichment
    """
    retrieval_enabled: bool = False
    top_k_symbolizations: int = 1
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    verbosity: Union[int, str] = 0
    quantifier_reduction_detail: bool = False
    allow_modal_advanced_cnf: bool = False
    privacy_mode: str = "default"
    reproducible_mode: bool = False
    live_mode: bool = False  # Deprecated: use reproducible_mode=False instead
    no_retrieval: bool = False


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
        modal_scope: For compound modal statements, the internal structure
                     (e.g., {"type": "AND", "components": [{"text": "...", "id": "m1.1"}, ...]})
        provenance: Optional provenance tracking for this claim
    """
    text: str
    symbol: Optional[str] = None
    origin_spans: List[Tuple[int, int]] = Field(default_factory=list)
    modal_context: Optional[str] = None
    modal_scope: Optional[Dict[str, Any]] = None
    provenance: Optional[ProvenanceRecord] = None


class ConcisionResult(BaseModel):
    """
    Result from the concision stage of the pipeline.
    
    The concision stage extracts atomic claims from preprocessed text and
    produces a canonical simplified representation. It decomposes logical
    structures (implications, conjunctions) and records the relationships
    in structural metadata.
    
    Attributes:
        canonical_text: Simplified, canonical version of the input text
        atomic_candidates: List of extracted atomic claims
        structural_metadata: Metadata about logical connectives and relationships
        confidence: Overall confidence in the concision result
        explanations: Optional human-readable explanation of the concision
        error: Optional error message if concision failed
    """
    canonical_text: str
    atomic_candidates: List[AtomicClaim]
    structural_metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    explanations: Optional[str] = None
    error: Optional[str] = None


class EntityGrounding(BaseModel):
    """
    Represents a grounded entity with its type and related claims.
    
    Entity groundings map named entities to their semantic roles and
    the atomic claims that reference them. This enables coherence
    validation and ensures all entities are properly tracked.
    
    Attributes:
        entity_text: The surface text of the entity
        entity_type: Semantic type (PERSON, ORG, LOCATION, GENERIC, etc.)
        grounding_method: How the entity was grounded (deterministic, llm_assisted)
        related_claim_ids: IDs of atomic claims referencing this entity
        confidence: Confidence in the grounding
    """
    entity_text: str
    entity_type: str = "GENERIC"
    grounding_method: str = "deterministic"
    related_claim_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(0.8, ge=0.0, le=1.0)


class CoherenceReport(BaseModel):
    """
    Report on the coherence of world construction output.
    
    Validates that all entities are grounded, quantifiers are reduced,
    and the overall construction is logically coherent.
    
    Attributes:
        is_coherent: Whether the construction passes coherence checks
        entity_completeness: Fraction of entities that are grounded (0.0-1.0)
        quantifier_coverage: Fraction of quantifiers properly reduced
        ungrounded_entities: List of entities without groundings
        warnings: Coherence-related warnings
        score: Overall coherence score (0.0-1.0)
    """
    is_coherent: bool = True
    entity_completeness: float = Field(1.0, ge=0.0, le=1.0)
    quantifier_coverage: float = Field(1.0, ge=0.0, le=1.0)
    ungrounded_entities: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    score: float = Field(1.0, ge=0.0, le=1.0)


class WorldResult(BaseModel):
    """
    Result from the world construction stage.
    
    This stage expands presuppositions and reduces quantifiers to propositional
    placeholders, preparing the logical structure for symbolization and CNF
    transformation. Sprint 3 adds entity grounding and coherence validation.
    
    Attributes:
        atomic_claims: Updated list of atomic claims (may include new claims
                      from quantifier reduction and presupposition expansion)
        atomic_instances: List of grounded atomic instances with entity types
        entity_groundings: Map from entity text to EntityGrounding objects
        reduction_metadata: Metadata about quantifier reductions performed
        presupposition_metadata: Metadata about presuppositions expanded
        quantifier_map: Mapping from quantified statements to their reductions
        coherence_report: Report on entity and quantifier coherence
        confidence: Overall confidence in the world construction
        warnings: Any warnings encountered during processing
    """
    atomic_claims: List[AtomicClaim]
    atomic_instances: List[Dict[str, Any]] = Field(default_factory=list)
    entity_groundings: Dict[str, EntityGrounding] = Field(default_factory=dict)
    reduction_metadata: Dict[str, Any] = Field(default_factory=dict)
    presupposition_metadata: Dict[str, Any] = Field(default_factory=dict)
    quantifier_map: Dict[str, str] = Field(default_factory=dict)
    coherence_report: Optional[CoherenceReport] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class SymbolizerResult(BaseModel):
    """
    Result from the symbolization stage.
    
    This stage assigns deterministic propositional symbols (P1, P2, ...) to
    atomic claims and builds a legend mapping symbols to their natural language
    meanings. Symbols are assigned in deterministic order based on origin spans
    to ensure reproducibility.
    
    Attributes:
        legend: Mapping from symbols (P1, P2, ...) to claim text
        atomic_claims: List of atomic claims with symbols assigned
        extended_legend: Optional detailed metadata per symbol including
                        origin spans, provenance IDs, and confidence scores
        confidence: Overall confidence in the symbolization result
        warnings: Any warnings encountered during processing
    """
    legend: Dict[str, str]
    atomic_claims: List[AtomicClaim]
    extended_legend: Optional[Dict[str, Dict[str, Any]]] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


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
        config_metadata: Configuration options used for this request (for reproducibility)
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
    config_metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Sprint 5 Types: Enrichment, Retrieval, and Modal Detection
# =============================================================================


class RetrievalSource(BaseModel):
    """
    Represents a source document or snippet from retrieval.
    
    DesignSpec 6a.1: RetrievalAdapter interface returns RetrievalSource objects
    with privacy redaction support.
    
    Attributes:
        source_id: Unique identifier for this source
        content: The retrieved text content (may be redacted)
        score: Relevance score from retrieval (0.0-1.0)
        redacted: Whether content has been redacted for privacy
        metadata: Additional metadata about the source
    """
    source_id: str
    content: str
    score: float = Field(0.0, ge=0.0, le=1.0)
    redacted: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    """
    Response from a retrieval adapter query.
    
    DesignSpec 6a.1: RetrievalAdapter.retrieve() returns RetrievalResponse
    containing sources and query metadata.
    
    Attributes:
        query: The original query text
        sources: List of retrieved sources
        total_results: Total number of results available
        request_id: Unique identifier for this retrieval request
        privacy_mode: Privacy mode used for this retrieval
        metadata: Additional metadata (e.g., fallback tracking)
    """
    query: str
    sources: List[RetrievalSource] = Field(default_factory=list)
    total_results: int = 0
    request_id: str = ""
    privacy_mode: str = "default"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExpandedClaim(BaseModel):
    """
    A claim expanded with enrichment context.
    
    DesignSpec 6a.2: EnrichmentResult contains ExpandedClaims with
    provenance tracking back to retrieval sources.
    
    Attributes:
        claim_id: Unique identifier for this claim
        text: The claim text
        origin: Origin of this claim (input, retrieval, inference)
        confidence: Confidence score (0.0-1.0)
        source_ids: IDs of retrieval sources that contributed
        origin_spans: Character spans in original text
    """
    claim_id: str
    text: str
    origin: str = "input"  # input | retrieval | inference
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    source_ids: List[str] = Field(default_factory=list)
    origin_spans: List[Tuple[int, int]] = Field(default_factory=list)


class EnrichmentSource(BaseModel):
    """
    Metadata about an enrichment source used in context expansion.
    
    DesignSpec 6a.1: Track all external sources used for enrichment
    with privacy redaction support.
    
    Attributes:
        source_id: Unique identifier for this source
        score: Relevance score (0.0-1.0)
        redacted: Whether the source content was redacted
        source_type: Type of source (retrieval, knowledge_base, inference)
    """
    source_id: str
    score: float = Field(0.0, ge=0.0, le=1.0)
    redacted: bool = False
    source_type: str = "retrieval"


class EnrichmentResult(BaseModel):
    """
    Result from the enrichment stage.
    
    DesignSpec 6a.2: Enrichment expands claims with external knowledge
    and context, preparing for world construction.
    
    Attributes:
        expanded_claims: List of claims with enrichment context
        enrichment_sources: Sources used for enrichment
        original_claim_count: Number of claims before enrichment
        enriched_claim_count: Number of claims after enrichment
        coherence_flags: Subset of ["complete", "consistent", "minimal", "underspecified", "contradictory"]
        confidence: Overall confidence in enrichment
        warnings: Warnings encountered during enrichment
    """
    expanded_claims: List[ExpandedClaim] = Field(default_factory=list)
    enrichment_sources: List[EnrichmentSource] = Field(default_factory=list)
    original_claim_count: int = 0
    enriched_claim_count: int = 0
    coherence_flags: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class ModalContext(BaseModel):
    """
    Modal context detected for a claim.
    
    DesignSpec 6a.2: Modal detection identifies necessity, possibility,
    obligation, and permission operators.
    
    Attributes:
        claim_id: ID of the claim this context applies to
        modal_type: Type of modality (necessity, possibility, obligation, permission)
        operator_text: The modal operator text from input
        frame: Modal logic frame (S5, K, etc.)
        confidence: Confidence in this detection
    """
    claim_id: str
    modal_type: str  # necessity | possibility | obligation | permission
    operator_text: str = ""
    frame: str = "S5"
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class ModalResult(BaseModel):
    """
    Result from modal detection.
    
    DesignSpec 6a.2: Modal detection identifies modal operators and
    selects appropriate frame semantics.
    
    Attributes:
        modal_contexts: List of detected modal contexts
        frame_selection: Selected modal frame for the document
        has_modality: Whether any modality was detected
        confidence: Overall confidence in modal detection
        warnings: Warnings encountered during detection
    """
    modal_contexts: List[ModalContext] = Field(default_factory=list)
    frame_selection: str = "none"  # none | S5 | K | D | T
    has_modality: bool = False
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


class CNFClause(BaseModel):
    """
    A single clause in Conjunctive Normal Form.
    
    Used in CNFResult to represent individual clauses with their
    constituent literals and provenance.
    
    Attributes:
        clause_id: Unique identifier for this clause
        literals: List of literals in this clause (disjunction)
        clause_type: Type of clause (unit, disjunction, horn)
        origin_claim_ids: IDs of claims this clause derives from
    """
    clause_id: str
    literals: List[str] = Field(default_factory=list)
    clause_type: str = "disjunction"  # unit | disjunction | horn
    origin_claim_ids: List[str] = Field(default_factory=list)


class CNFResult(BaseModel):
    """
    Result from CNF transformation.
    
    Contains the Conjunctive Normal Form representation of the
    formalized input, broken into individual clauses.
    
    Attributes:
        clauses: List of CNF clauses
        original_formula: The formula before CNF transformation
        transformation_steps: Steps taken to reach CNF
        confidence: Confidence in the transformation
        warnings: Warnings encountered during transformation
    """
    clauses: List[CNFClause] = Field(default_factory=list)
    original_formula: str = ""
    transformation_steps: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)
