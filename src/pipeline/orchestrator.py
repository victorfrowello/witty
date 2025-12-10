"""
Orchestrator module for the Witty formalization pipeline (Sprint 1).

Coordinates the sequential execution of pipeline stages to transform natural
language statements into formal logical representations. This implementation
provides a deterministic, reproducible path suitable for CI/CD and testing.

Pipeline Stages:
1. Ingest: Normalize and validate input text
2. Preprocessing: Segment text into clauses and tokens
3. Concision: Extract atomic claims from preprocessed text
4. Output Assembly: Build final FormalizationResult with symbols and CNF

All stages produce ModuleResult objects with comprehensive ProvenanceRecord
tracking for transparency and debugging.

Author: Victor Rowello
"""
from __future__ import annotations

import hashlib
import datetime
from typing import Any, Dict, Optional

from src.witty_types import (
    ModuleResult,
    ProvenanceRecord,
    FormalizationResult,
    FormalizeOptions,
    AtomicClaim,
)


def make_provenance_id(
    normalized_input: str,
    module_id: str,
    module_version: str,
    salt: str
) -> str:
    """
    Generate a deterministic provenance ID for reproducibility.
    
    Creates a hash-based identifier that will be identical for the same inputs,
    enabling deterministic testing and comparison of pipeline runs.
    
    Args:
        normalized_input: The normalized text being processed
        module_id: Identifier of the module creating this provenance
        module_version: Version of the module
        salt: Deterministic salt for additional uniqueness
        
    Returns:
        Provenance ID prefixed with 'pr_' followed by 12-char hash
    """
    payload = f"{normalized_input}\n{module_id}\n{module_version}\n{salt}"
    hash_digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return f"pr_{hash_digest[:12]}"


class AgentContext:
    """
    Context object passed through pipeline stages.
    
    Carries shared state and configuration through the pipeline, providing
    each stage with access to request metadata, options, and logging.
    
    Attributes:
        request_id: Unique identifier for this formalization request
        options: Configuration options controlling pipeline behavior
        reproducible_mode: Whether to run in deterministic mode
        deterministic_salt: Salt for deterministic ID generation
        logger: Optional logger instance for debugging (currently unused)
    """
    
    def __init__(
        self,
        request_id: str,
        options: FormalizeOptions,
        reproducible_mode: bool = True,
        deterministic_salt: str = "sprint1",
        logger: Optional[Any] = None
    ) -> None:
        """
        Initialize pipeline context.
        
        Args:
            request_id: Unique ID for this request
            options: Pipeline configuration options
            reproducible_mode: Enable deterministic behavior
            deterministic_salt: Salt for hash-based IDs
            logger: Optional logger instance
        """
        self.request_id = request_id
        self.options = options
        self.reproducible_mode = reproducible_mode
        self.deterministic_salt = deterministic_salt
        self.logger = logger



def ingest(raw_text: str, ctx: AgentContext) -> ModuleResult:
    """
    Stage 1: Ingest and normalize input text.
    
    Performs basic text normalization (stripping whitespace) and creates the
    initial provenance record. This is the entry point for all text into the
    pipeline.
    
    Args:
        raw_text: Original input text from user
        ctx: Pipeline context with request metadata
        
    Returns:
        ModuleResult containing normalized text and metadata
    """
    # Normalize: strip leading/trailing whitespace
    normalized = raw_text.strip()
    
    # Create provenance record for this transformation
    provenance = ProvenanceRecord(
        id=make_provenance_id(normalized, "ingest", "v1", ctx.deterministic_salt),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        module_id="ingest",
        module_version="v1",
        adapter_id=None,
        prompt_template_id=None,
        adapter_request_id=None,
        origin_spans=[(0, len(normalized))],  # Entire normalized text
        enrichment_sources=[],
        confidence=1.0,
        ambiguity_flags=[],
        reduction_rationale="",
        event_log=[]
    )
    
    # Build payload with normalized text and original for reference
    payload = {
        "normalized_text": normalized,
        "original_text": raw_text,
        "metadata": {}
    }
    
    return ModuleResult(
        payload=payload,
        provenance_record=provenance,
        confidence=1.0,
        warnings=[]
    )



def preprocess(ingest_result: Dict[str, Any], ctx: AgentContext) -> ModuleResult:
    """
    Stage 2: Preprocess text into clauses and tokens.
    
    Performs simple clause segmentation by splitting on sentence boundaries.
    In future iterations, this could use more sophisticated NLP tools for
    tokenization, dependency parsing, etc.
    
    Args:
        ingest_result: Payload from the ingest stage
        ctx: Pipeline context
        
    Returns:
        ModuleResult containing segmented clauses with position information
    """
    text = ingest_result["normalized_text"]
    
    # Simple clause segmentation: split by period
    # Each clause gets position metadata for traceability
    clauses = []
    for i, clause_text in enumerate(text.split(".")):
        clause_text = clause_text.strip()
        if clause_text:  # Skip empty clauses
            clauses.append({
                "text": clause_text,
                "start": i,
                "end": i + len(clause_text)
            })
    
    # Create provenance for preprocessing
    provenance = ProvenanceRecord(
        id=make_provenance_id(text, "preprocessing", "v1", ctx.deterministic_salt),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        module_id="preprocessing",
        module_version="v1",
        adapter_id=None,
        prompt_template_id=None,
        adapter_request_id=None,
        origin_spans=[(0, len(text))],
        enrichment_sources=[],
        confidence=1.0,
        ambiguity_flags=[],
        reduction_rationale="",
        event_log=[]
    )
    
    payload = {
        "clauses": clauses,
        "tokens": [],  # Token-level parsing reserved for future implementation
        "origin_spans": provenance.origin_spans
    }
    
    return ModuleResult(
        payload=payload,
        provenance_record=provenance,
        confidence=1.0,
        warnings=[]
    )



def deterministic_concision(
    prep_result: Dict[str, Any],
    ctx: AgentContext
) -> ModuleResult:
    """
    Stage 3: Extract atomic claims using deterministic fallback.
    
    This is a simplified, deterministic implementation suitable for testing
    and reproducible pipelines. In production, this would use LLM-based
    concision with the mock adapter replaced by a real model.
    
    The deterministic approach treats each preprocessed clause as a separate
    atomic claim, which works well enough for testing but lacks the semantic
    understanding of a full LLM implementation.
    
    Args:
        prep_result: Payload from preprocessing stage containing clauses
        ctx: Pipeline context
        
    Returns:
        ModuleResult with canonical text and atomic claim candidates
    """
    # Convert each clause into an atomic claim candidate
    atomic_candidates = []
    for clause in prep_result["clauses"]:
        atomic_candidates.append({
            "text": clause["text"],
            "origin_spans": [(clause["start"], clause["end"])],
            "confidence": 1.0
        })
    
    # Reconstruct canonical text by joining all clauses
    canonical_text = " ".join([c["text"] for c in prep_result["clauses"]])
    
    # Create provenance with fallback event log entry
    # This documents that we used deterministic logic instead of LLM
    event_log = [{
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event_type": "fallback",
        "message": "Used deterministic_concision",
        "meta": {}
    }]
    
    provenance = ProvenanceRecord(
        id=make_provenance_id(canonical_text, "concision", "v1", ctx.deterministic_salt),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        module_id="concision",
        module_version="v1",
        adapter_id="mock",  # Indicates fallback adapter used
        prompt_template_id=None,
        adapter_request_id=None,
        origin_spans=prep_result["origin_spans"],
        enrichment_sources=[],
        confidence=1.0,
        ambiguity_flags=[],
        reduction_rationale="deterministic fallback",
        event_log=event_log
    )
    
    payload = {
        "canonical_text": canonical_text,
        "atomic_candidates": atomic_candidates,
        "confidence": 1.0,
        "explanations": "Deterministic fallback"
    }
    
    return ModuleResult(
        payload=payload,
        provenance_record=provenance,
        confidence=1.0,
        warnings=[]
    )



def assemble_output(
    raw_text: str,
    concision_result: Dict[str, Any],
    ctx: AgentContext,
    provenance_record: ProvenanceRecord
) -> FormalizationResult:
    """
    Stage 4: Assemble final FormalizationResult from pipeline outputs.
    
    Converts atomic claim candidates into fully-formed AtomicClaim objects,
    assigns symbols (P1, P2, ...), constructs a legend, and builds simple
    logical forms and CNF representation.
    
    Args:
        raw_text: Original input text
        concision_result: Output from concision stage
        ctx: Pipeline context
        provenance_record: Provenance from concision stage
        
    Returns:
        Complete FormalizationResult ready for serialization
    """
    atomic_claims: list[AtomicClaim] = []
    legend: Dict[str, str] = {}
    
    # Assign symbols to each atomic claim (P1, P2, P3, ...)
    for i, candidate in enumerate(concision_result["atomic_candidates"]):
        symbol = f"P{i + 1}"
        
        # Create typed AtomicClaim instance
        claim = AtomicClaim(
            text=candidate["text"],
            symbol=symbol,
            origin_spans=candidate.get("origin_spans", []),
            provenance=provenance_record,
        )
        
        atomic_claims.append(claim)
        legend[symbol] = candidate["text"]
    
    # Build simple logical form representation
    # Uses conjunction (AND) of all atomic claims
    logical_form_candidates = [{
        "ast": {},  # Abstract syntax tree (reserved for future implementation)
        "notation": " AND ".join(legend.values()),  # Human-readable form
        "confidence": 1.0
    }]
    
    chosen_logical_form = logical_form_candidates[0]
    
    # Build CNF (Conjunctive Normal Form) representation
    # For simple cases, this is just the conjunction of all symbols
    cnf = " AND ".join(legend.keys())
    cnf_clauses = [[symbol] for symbol in legend.keys()]
    
    # Aggregate provenance records from all stages
    provenance = [provenance_record]
    
    return FormalizationResult(
        request_id=ctx.request_id,
        original_text=raw_text,
        canonical_text=concision_result["canonical_text"],
        atomic_claims=atomic_claims,
        legend=legend,
        logical_form_candidates=logical_form_candidates,
        chosen_logical_form=chosen_logical_form,
        cnf=cnf,
        cnf_clauses=cnf_clauses,
        confidence=1.0,
        provenance=provenance
    )



def formalize_statement(
    input_text: str,
    options: FormalizeOptions
) -> FormalizationResult:
    """
    Main orchestrator function - coordinates full pipeline execution (Sprint 2).
    
    Runs all pipeline stages sequentially and returns the final formalization
    result. This is the primary entry point for the formalization pipeline,
    integrating all Sprint 2 modules: preprocessing, concision, world construction,
    and symbolization.
    
    Pipeline flow (Sprint 2):
    1. Ingest: Normalize input text
    2. Preprocessing: Segment, tokenize, annotate special tokens
    3. Concision: Extract atomic claims with conditional/conjunction decomposition
    4. World Construction: Reduce quantifiers to propositional placeholders (if detected)
    5. Symbolization: Assign P1, P2, ... symbols and build legend
    6. CNF: Generate CNF representation (stub for Sprint 2)
    7. Assembly: Build complete FormalizationResult
    
    Args:
        input_text: Natural language statement to formalize
        options: Configuration options controlling pipeline behavior
        
    Returns:
        FormalizationResult containing symbols, legend, logical forms, CNF,
        and complete provenance chain for all transformations
        
    Example:
        >>> opts = FormalizeOptions()
        >>> result = formalize_statement("If it rains then the match is cancelled.", opts)
        >>> print(result.legend)
        {'P1': 'it rains', 'P2': 'the match is cancelled'}
        >>> print(len(result.atomic_claims))
        2
        
    Note:
        - Sprint 2 implementation uses deterministic modules for reproducibility
        - All modules record comprehensive provenance for transparency
        - Quantifier reduction is applied when quantifiers are detected
        - CNF transformation is a simplified stub pending Sprint 3
    """
    # Import the Sprint 2 pipeline modules
    # Local imports to avoid circular dependencies and ensure module availability
    from src.pipeline import preprocessing as prep_module
    from src.pipeline import concision as conc_module
    from src.pipeline import world as world_module
    from src.pipeline import symbolizer as sym_module
    
    # Generate unique request ID with timezone-aware timestamp
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    request_id = f"req_{timestamp.strftime('%Y%m%d%H%M%S')}"
    
    # Create pipeline context for Sprint 2
    # Use options.reproducible_mode if specified, otherwise default to True
    reproducible = getattr(options, 'reproducible_mode', True)
    ctx = AgentContext(
        request_id=request_id,
        options=options,
        reproducible_mode=reproducible,
        deterministic_salt=getattr(options, 'deterministic_salt', 'sprint2')
    )
    
    # Collect all provenance records for final assembly
    all_provenance = []
    all_warnings = []
    
    # Stage 1: Preprocessing - segment, tokenize, annotate
    try:
        prep_result = prep_module.preprocess(input_text)
        # Note: preprocessing module returns PreprocessingResult directly,
        # not wrapped in ModuleResult yet. We'll create provenance here.
        prep_provenance = ProvenanceRecord(
            id=make_provenance_id(input_text, "preprocessing", "2.0.0", ctx.deterministic_salt),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            module_id="preprocessing",
            module_version="2.0.0",
            adapter_id=None,
            prompt_template_id=None,
            adapter_request_id=None,
            origin_spans=[(0, len(input_text))],
            enrichment_sources=[],
            confidence=1.0,
            ambiguity_flags=[],
            reduction_rationale="",
            event_log=[]
        )
        all_provenance.append(prep_provenance)
    except Exception as e:
        # If preprocessing fails, create a minimal result for error reporting
        all_warnings.append(f"Preprocessing failed: {str(e)}")
        # Create a minimal preprocessing result to continue pipeline
        from src.pipeline.preprocessing import PreprocessingResult, Clause
        prep_result = PreprocessingResult(
            normalized_text=input_text.strip(),
            clauses=[Clause(text=input_text.strip(), start_char=0, end_char=len(input_text))],
            tokens=[],
            sentence_boundaries=[],
            origin_spans={}
        )
    
    # Stage 2: Concision - extract atomic claims with structural decomposition
    try:
        conc_module_result = conc_module.deterministic_concision(prep_result, ctx)
        # Extract ConcisionResult from the payload dict
        from src.witty_types import ConcisionResult
        concision_result = ConcisionResult(**conc_module_result.payload)
        all_provenance.append(conc_module_result.provenance_record)
        all_warnings.extend(conc_module_result.warnings)
    except Exception as e:
        all_warnings.append(f"Concision failed: {str(e)}")
        # Create minimal concision result
        from src.witty_types import ConcisionResult
        concision_result = ConcisionResult(
            canonical_text=prep_result.normalized_text,
            atomic_candidates=[],
            confidence=0.0
        )
    
    # Stage 3: World Construction - reduce quantifiers if detected
    # Check if any atomic candidates contain quantifiers
    has_quantifiers = False
    if hasattr(concision_result, 'atomic_candidates'):
        for candidate in concision_result.atomic_candidates:
            # Simple heuristic: check for common quantifier words
            text_lower = candidate.text.lower()
            if any(q in text_lower for q in ['all', 'every', 'each', 'some', 'any', 'no', 'none']):
                has_quantifiers = True
                break
    
    if has_quantifiers:
        try:
            world_module_result = world_module.world_construct(
                concision_result,
                ctx,
                salt=ctx.deterministic_salt
            )
            # Extract WorldResult from the payload dict
            from src.witty_types import WorldResult
            world_result = WorldResult(**world_module_result.payload)
            all_provenance.append(world_module_result.provenance_record)
            all_warnings.extend(world_module_result.warnings)
            
            # Use world-constructed claims for symbolization
            claims_for_symbolization = world_result
        except Exception as e:
            all_warnings.append(f"World construction failed: {str(e)}")
            # Fall back to using concision result directly
            claims_for_symbolization = concision_result
    else:
        # No quantifiers detected - skip world construction, use concision directly
        claims_for_symbolization = concision_result
    
    # Stage 4: Symbolization - assign P1, P2, ... symbols
    try:
        sym_module_result = sym_module.symbolizer(claims_for_symbolization, ctx)
        # Extract SymbolizerResult from the payload dict
        from src.witty_types import SymbolizerResult
        symbolizer_result = SymbolizerResult(**sym_module_result.payload)
        all_provenance.append(sym_module_result.provenance_record)
        all_warnings.extend(sym_module_result.warnings)
    except Exception as e:
        all_warnings.append(f"Symbolization failed: {str(e)}")
        # Create minimal symbolizer result
        from src.witty_types import SymbolizerResult
        symbolizer_result = SymbolizerResult(
            legend={},
            atomic_claims=[],
            confidence=0.0
        )
    
    # Stage 5: CNF Transformation (stub for Sprint 2, full implementation in Sprint 3)
    # For now, create simple CNF representation
    cnf = None
    cnf_clauses = []
    
    if symbolizer_result.legend:
        # Simple CNF: conjunction of all atomic symbols
        symbols = list(symbolizer_result.legend.keys())
        cnf = " ∧ ".join(symbols)
        # Each symbol is its own clause (unit clause)
        cnf_clauses = [[symbol] for symbol in symbols]
    
    # Stage 6: Assemble FormalizationResult
    # Build logical form candidates
    logical_form_candidates = []
    if symbolizer_result.legend:
        # Create a simple logical form using the legend
        notation = " ∧ ".join([
            f"{sym}:{text[:30]}..." if len(text) > 30 else f"{sym}:{text}"
            for sym, text in symbolizer_result.legend.items()
        ])
        logical_form_candidates.append({
            "ast": {},  # Reserved for future implementation
            "notation": notation,
            "confidence": symbolizer_result.confidence
        })
    
    chosen_logical_form = logical_form_candidates[0] if logical_form_candidates else None
    
    # Calculate overall confidence
    # Average across stages that provided results
    confidences = [
        conc_module_result.confidence if 'conc_module_result' in locals() else 1.0,
        symbolizer_result.confidence
    ]
    if has_quantifiers and 'world_module_result' in locals():
        confidences.append(world_module_result.confidence)
    
    overall_confidence = sum(confidences) / len(confidences) if confidences else 1.0
    
    # Build final FormalizationResult
    # Convert nested Pydantic models to dicts for proper validation
    result = FormalizationResult.model_validate({
        "request_id": request_id,
        "original_text": input_text,
        "canonical_text": concision_result.canonical_text if hasattr(concision_result, 'canonical_text') else input_text,
        "atomic_claims": [claim.model_dump() for claim in symbolizer_result.atomic_claims],
        "legend": symbolizer_result.legend,
        "logical_form_candidates": logical_form_candidates,
        "chosen_logical_form": chosen_logical_form,
        "cnf": cnf,
        "cnf_clauses": cnf_clauses,
        "confidence": overall_confidence,
        "provenance": [prov.model_dump() for prov in all_provenance],
        "warnings": all_warnings
    })
    
    # Ensure we return the validated Pydantic instance, not a dict
    return result


# Script execution support for debugging and development
if __name__ == "__main__":
    from src.witty.types import FormalizeOptions
    
    # Example usage for testing
    opts = FormalizeOptions()
    text = (
        "If Alice owns a red car then she likely prefers driving. "
        "She said she doesn't like long trips."
    )
    
    result = formalize_statement(text, opts)
    print(result.model_dump_json(indent=2))

