"""
World Construction & Quantifier Reduction Module for Witty Pipeline.

This module expands presuppositions and reduces quantifiers to deterministic
propositional placeholders. It handles universal quantifiers (all, every, each),
existential quantifiers (some, a, exists), and negative quantifiers (no, none),
converting them into propositional representatives suitable for CNF reasoning.

Key Features:
- Quantifier detection and scope extraction
- Deterministic propositional placeholder generation using SHA256
- Reduction rationale documentation for transparency
- Presupposition expansion for common patterns
- Origin span preservation throughout reduction
- Reproducible IDs for same input + salt combinations

Algorithm:
    Universal (ALL): "All students attend" → R{hash}_students_attend
    Existential (SOME): "Some students attend" → E{hash}_students_attend
    Negative (NO): "No cars allowed" → negated universal
    
    IDs are deterministic: SHA256(text + salt + variable + predicate)[:4]

Author: Victor Rowello
Sprint: 2, Task: 3
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import re
import hashlib
from datetime import datetime, timezone

from src.witty_types import (
    AtomicClaim,
    ConcisionResult,
    ModuleResult,
    ProvenanceRecord,
)


class QuantifierStructure(BaseModel):
    """
    Represents a detected quantified statement in text.
    
    Quantified statements have the form: Quantifier + Variable + Predicate
    Example: "All students must attend" where:
        - quantifier_type: UNIVERSAL
        - variable: "students"
        - predicate: "must attend"
        - scope: "must attend"
    
    Attributes:
        quantifier_type: Type of quantifier (UNIVERSAL, EXISTENTIAL, NEGATIVE)
        quantifier_text: Actual quantifier word(s) used
        variable: The quantified variable (e.g., "students", "cars")
        predicate: What is asserted about the variable
        scope: Full scope of the quantifier (may include nested structure)
        full_span: Character span of the entire quantified statement
        variable_span: Character span of the variable
        predicate_span: Character span of the predicate
        confidence: Confidence in this detection (0.0 to 1.0)
    """
    quantifier_type: str  # UNIVERSAL, EXISTENTIAL, NEGATIVE
    quantifier_text: str  # The actual quantifier word(s)
    variable: str  # The quantified variable
    predicate: str  # What is asserted about the variable
    scope: str  # Full scope of quantification
    full_span: Tuple[int, int]
    variable_span: Tuple[int, int]
    predicate_span: Tuple[int, int]
    confidence: float = Field(0.85, ge=0.0, le=1.0)


class PresuppositionStructure(BaseModel):
    """
    Represents an implicit presupposition detected in text.
    
    Presuppositions are implicit assumptions required for a statement to be
    meaningful. Example: "The king of France is bald" presupposes "There
    exists a king of France".
    
    Attributes:
        presupposition_type: Type of presupposition (EXISTENCE, STATE, etc.)
        implicit_claim: The implicit claim being presupposed
        trigger_span: Character span that triggered presupposition detection
        confidence: Confidence in this detection
    """
    presupposition_type: str  # EXISTENCE, STATE, DEFINITENESS, etc.
    implicit_claim: str
    trigger_span: Tuple[int, int]
    confidence: float = Field(0.70, ge=0.0, le=1.0)


class WorldResult(BaseModel):
    """
    Result from the world construction stage.
    
    This stage expands presuppositions and reduces quantifiers to propositional
    placeholders, preparing the logical structure for symbolization and CNF
    transformation.
    
    Attributes:
        atomic_claims: Updated list of atomic claims (may include new claims
                      from quantifier reduction and presupposition expansion)
        reduction_metadata: Metadata about quantifier reductions performed
        presupposition_metadata: Metadata about presuppositions expanded
        quantifier_map: Mapping from quantified statements to their reductions
        confidence: Overall confidence in the world construction
        warnings: Any warnings encountered during processing
    """
    atomic_claims: List[AtomicClaim]
    reduction_metadata: Dict[str, Any] = Field(default_factory=dict)
    presupposition_metadata: Dict[str, Any] = Field(default_factory=dict)
    quantifier_map: Dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)


# Quantifier patterns for detection
# Each pattern: (regex, quantifier_type, confidence)
QUANTIFIER_PATTERNS = [
    # Universal quantifiers
    (r'\b(all|every|each)\s+([\w\s]+?)\s+(.*?)(?:\.|,|;|$)', 'UNIVERSAL', 0.90),
    (r'\b(always)\s+(.*?)(?:\.|,|;|$)', 'UNIVERSAL', 0.85),
    (r'\b(everyone|everybody|everything)\s+(.*?)(?:\.|,|;|$)', 'UNIVERSAL', 0.88),
    
    # Existential quantifiers
    (r'\b(some|a|an)\s+([\w\s]+?)\s+(.*?)(?:\.|,|;|$)', 'EXISTENTIAL', 0.88),
    (r'\b(something|someone|somebody)\s+(.*?)(?:\.|,|;|$)', 'EXISTENTIAL', 0.85),
    (r'\bthere\s+(?:is|are|exists?)\s+(a|an)?\s*([\w\s]+?)\s*(.*?)(?:\.|,|;|$)', 'EXISTENTIAL', 0.90),
    
    # Negative quantifiers
    (r'\b(no|none)\s+([\w\s]+?)\s+(.*?)(?:\.|,|;|$)', 'NEGATIVE', 0.90),
    (r'\b(nothing|nobody|nowhere)\s+(.*?)(?:\.|,|;|$)', 'NEGATIVE', 0.88),
    (r'\b(never)\s+(.*?)(?:\.|,|;|$)', 'NEGATIVE', 0.85),
]

# Presupposition trigger patterns
# These patterns detect constructions that carry implicit presuppositions
# ORDER MATTERS: More specific patterns should come first
PRESUPPOSITION_PATTERNS = [
    # Change of state verbs (stop, continue, cease) - handles past tense
    (r'\b(stop(?:ped)?|cease(?:d)?|quit|discontinue(?:d)?|continue(?:d)?|resume(?:d)?)\s+(\w+ing)\s*(.*?)(?:\.|,|;|$)',
     'STATE_CHANGE', 0.85),
    
    # Factive verbs (know, realize, etc.) - should match before definiteness
    # Match forms like "knows that", "knew that", "knowing that"
    (r'\b(know(?:s|ing)?|knew|realize(?:s|d)?|understand(?:s)?|understood|discover(?:ed|s)?|reveal(?:ed|s)?|regret(?:s|ted)?|remember(?:s|ed)?)\s+(?:that\s+)?(.*?)(?:\.|,|;|$)',
     'FACTIVE', 0.80),
    
    # Definite descriptions (the X) - should come last as it's most general
    (r'\bthe\s+([\w\s]+?)\s+(is|are|was|were|has|have)\s+(.*?)(?:\.|,|;|$)', 
     'DEFINITENESS', 0.75),
]


def detect_quantifier(text: str, start_offset: int = 0) -> Optional[QuantifierStructure]:
    """
    Detect quantified statements in text.
    
    Scans text for universal, existential, and negative quantifiers, extracting
    the quantifier type, variable, and predicate (scope).
    
    Args:
        text: Input text to analyze
        start_offset: Character offset to add to spans (for original text mapping)
        
    Returns:
        QuantifierStructure if quantifier detected, None otherwise
        
    Examples:
        >>> detect_quantifier("All students must attend class")
        QuantifierStructure(
            quantifier_type='UNIVERSAL',
            quantifier_text='all',
            variable='students',
            predicate='must attend class',
            ...
        )
        
        >>> detect_quantifier("Some employees passed the test")
        QuantifierStructure(
            quantifier_type='EXISTENTIAL',
            variable='employees',
            predicate='passed the test',
            ...
        )
    
    Note:
        Variable extraction is heuristic and may need refinement for complex
        noun phrases. For Sprint 2, we handle simple cases and flag complex
        structures for human review.
    """
    text_lower = text.lower().strip()
    
    for pattern, quant_type, confidence in QUANTIFIER_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            groups = match.groups()
            quantifier_text = groups[0]
            
            # Extract variable and predicate based on pattern structure
            if len(groups) >= 3:
                # Pattern has quantifier, variable, predicate
                variable = groups[1].strip()
                predicate = groups[2].strip()
            elif len(groups) == 2:
                # Pattern has quantifier and predicate (no explicit variable)
                # e.g., "always rains" -> variable is implicit
                variable = "_implicit_"
                predicate = groups[1].strip()
            else:
                # Single group - use as predicate, no variable
                variable = "_implicit_"
                predicate = groups[0].strip() if len(groups) > 0 else ""
            
            # Calculate spans
            full_start = match.start() + start_offset
            full_end = match.end() + start_offset
            
            # Variable span (approximate - find variable text in matched region)
            var_start = text_lower.find(variable.lower(), match.start())
            if var_start != -1:
                variable_span = (var_start + start_offset, 
                               var_start + len(variable) + start_offset)
            else:
                variable_span = (full_start, full_start)  # Fallback
            
            # Predicate span (approximate - after variable)
            pred_start = text_lower.find(predicate.lower(), match.start())
            if pred_start != -1:
                predicate_span = (pred_start + start_offset,
                                pred_start + len(predicate) + start_offset)
            else:
                predicate_span = (full_start, full_end)  # Fallback
            
            return QuantifierStructure(
                quantifier_type=quant_type,
                quantifier_text=quantifier_text,
                variable=variable,
                predicate=predicate,
                scope=predicate,  # For simple cases, scope = predicate
                full_span=(full_start, full_end),
                variable_span=variable_span,
                predicate_span=predicate_span,
                confidence=confidence
            )
    
    return None


def generate_deterministic_id(
    text: str,
    salt: str,
    quantifier_type: str,
    variable: str,
    predicate: str
) -> str:
    """
    Generate a deterministic propositional placeholder ID.
    
    Uses SHA256 hashing to create a stable, reproducible ID for a quantified
    statement. Same inputs always produce the same ID, ensuring reproducibility
    across runs.
    
    Args:
        text: Original text of the quantified statement
        salt: Deterministic salt from AgentContext
        quantifier_type: Type of quantifier (UNIVERSAL, EXISTENTIAL, NEGATIVE)
        variable: The quantified variable
        predicate: The predicate applied to the variable
        
    Returns:
        Deterministic ID string in format: {prefix}{hash}_{variable}_{predicate_summary}
        where prefix is 'R' for universal, 'E' for existential, 'N' for negative
        
    Examples:
        >>> generate_deterministic_id("All students attend", "salt123", 
        ...                           "UNIVERSAL", "students", "attend")
        'R3a2f_students_attend'
        
        >>> generate_deterministic_id("Some employees passed", "salt123",
        ...                           "EXISTENTIAL", "employees", "passed")
        'E8b4c_employees_passed'
    
    Algorithm:
        1. Combine text + salt + variable + predicate
        2. Hash with SHA256
        3. Take first 4 hex digits of hash
        4. Format: {prefix}{hash[:4]}_{variable_clean}_{predicate_clean}
        
    Note:
        Variable and predicate are sanitized (alphanumeric + underscore only)
        to ensure valid symbol names.
    """
    # Create payload for hashing
    payload = f"{text}\n{salt}\n{variable}\n{predicate}".encode('utf-8')
    hash_value = hashlib.sha256(payload).hexdigest()
    hash_prefix = hash_value[:4]  # First 4 hex digits
    
    # Determine prefix based on quantifier type
    prefix_map = {
        'UNIVERSAL': 'R',      # Representative instance
        'EXISTENTIAL': 'E',    # Existential witness
        'NEGATIVE': 'N',       # Negative assertion
    }
    prefix = prefix_map.get(quantifier_type, 'Q')  # Q for unknown
    
    # Sanitize variable and predicate for symbol name
    # Keep only alphanumeric and underscore, replace spaces with underscore
    def sanitize(s: str, max_len: int = 20) -> str:
        """Clean string for use in symbol ID."""
        # Replace spaces with underscore, remove non-alphanumeric
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', s.replace(' ', '_'))
        # Truncate to max length
        return cleaned[:max_len] if len(cleaned) > max_len else cleaned
    
    variable_clean = sanitize(variable)
    predicate_clean = sanitize(predicate, max_len=30)
    
    # Construct ID: prefix + hash + variable + predicate
    # Example: R3a2f_students_attend
    id_str = f"{prefix}{hash_prefix}_{variable_clean}_{predicate_clean}"
    
    return id_str


def create_reduction_rationale(
    quantifier: QuantifierStructure,
    generated_id: str
) -> str:
    """
    Create a human-readable explanation of the quantifier reduction.
    
    This rationale is stored in provenance and helps users understand why
    and how a quantifier was reduced to a propositional placeholder.
    
    Args:
        quantifier: The quantifier structure being reduced
        generated_id: The deterministic ID generated for this reduction
        
    Returns:
        Human-readable rationale string
        
    Examples:
        >>> create_reduction_rationale(
        ...     QuantifierStructure(quantifier_type='UNIVERSAL', 
        ...                        quantifier_text='all',
        ...                        variable='students',
        ...                        predicate='attend'),
        ...     'R3a2f_students_attend'
        ... )
        'Universal quantifier "all students" reduced to representative instance R3a2f_students_attend'
    """
    type_descriptions = {
        'UNIVERSAL': 'Universal quantifier',
        'EXISTENTIAL': 'Existential quantifier',
        'NEGATIVE': 'Negative quantifier',
    }
    
    type_desc = type_descriptions.get(quantifier.quantifier_type, 'Quantifier')
    quant_phrase = f'"{quantifier.quantifier_text} {quantifier.variable}"'
    
    reduction_explanations = {
        'UNIVERSAL': f'reduced to representative instance {generated_id}',
        'EXISTENTIAL': f'reduced to existential witness {generated_id}',
        'NEGATIVE': f'reduced to negated instance {generated_id}',
    }
    
    reduction_exp = reduction_explanations.get(
        quantifier.quantifier_type,
        f'reduced to {generated_id}'
    )
    
    rationale = f"{type_desc} {quant_phrase} {reduction_exp}"
    
    # Add note about the transformation
    if quantifier.quantifier_type == 'UNIVERSAL':
        rationale += (
            " (representing 'for all x in domain, predicate(x)' as a "
            "propositional placeholder for CNF reasoning)"
        )
    elif quantifier.quantifier_type == 'EXISTENTIAL':
        rationale += (
            " (representing 'there exists x such that predicate(x)' as a "
            "propositional witness for CNF reasoning)"
        )
    elif quantifier.quantifier_type == 'NEGATIVE':
        rationale += (
            " (representing 'for no x in domain, predicate(x)' as a "
            "negated propositional placeholder)"
        )
    
    return rationale


def reduce_quantifiers(
    text: str,
    salt: str,
    quantifier: QuantifierStructure
) -> Tuple[AtomicClaim, str]:
    """
    Reduce a quantified statement to a propositional placeholder.
    
    Converts a quantified statement (e.g., "All students attend") into a
    deterministic propositional placeholder (e.g., R3a2f_students_attend)
    suitable for symbolic reasoning and CNF transformation.
    
    Args:
        text: Original text of the quantified statement
        salt: Deterministic salt for reproducible hashing
        quantifier: The quantifier structure to reduce
        
    Returns:
        Tuple of (AtomicClaim, reduction_rationale)
        - AtomicClaim: The reduced propositional claim
        - reduction_rationale: Human-readable explanation
        
    Examples:
        >>> q = QuantifierStructure(
        ...     quantifier_type='UNIVERSAL',
        ...     quantifier_text='all',
        ...     variable='students',
        ...     predicate='must attend',
        ...     scope='must attend',
        ...     full_span=(0, 24),
        ...     variable_span=(4, 12),
        ...     predicate_span=(13, 24)
        ... )
        >>> claim, rationale = reduce_quantifiers(
        ...     "All students must attend",
        ...     "salt123",
        ...     q
        ... )
        >>> assert claim.symbol.startswith('R')
        >>> assert 'students' in claim.symbol
    
    Note:
        The reduction is deterministic: same input + salt → same ID.
        This ensures reproducibility across runs when using the same salt.
    """
    # Generate deterministic ID
    generated_id = generate_deterministic_id(
        text=text,
        salt=salt,
        quantifier_type=quantifier.quantifier_type,
        variable=quantifier.variable,
        predicate=quantifier.predicate
    )
    
    # Create reduction rationale
    rationale = create_reduction_rationale(quantifier, generated_id)
    
    # Build the claim text - use the original predicate applied to the variable
    # For universal: "students must attend" (without "all")
    # For existential: "some student attends" 
    if quantifier.variable != "_implicit_":
        claim_text = f"{quantifier.variable} {quantifier.predicate}"
    else:
        claim_text = quantifier.predicate
    
    # Create atomic claim
    atomic_claim = AtomicClaim(
        text=claim_text,
        symbol=generated_id,
        origin_spans=[quantifier.full_span],
        modal_context=None
    )
    
    return atomic_claim, rationale


def detect_presupposition(text: str, start_offset: int = 0) -> Optional[PresuppositionStructure]:
    """
    Detect implicit presuppositions in text.
    
    Identifies constructions that carry implicit assumptions or presuppositions,
    such as definite descriptions ("the king of France"), factive verbs ("know that"),
    and change-of-state verbs ("stop smoking").
    
    Args:
        text: Input text to analyze
        start_offset: Character offset for span mapping
        
    Returns:
        PresuppositionStructure if presupposition detected, None otherwise
        
    Examples:
        >>> detect_presupposition("The king of France is bald")
        PresuppositionStructure(
            presupposition_type='DEFINITENESS',
            implicit_claim='There exists a king of France',
            ...
        )
        
        >>> detect_presupposition("John stopped smoking")
        PresuppositionStructure(
            presupposition_type='STATE_CHANGE',
            implicit_claim='John was smoking (before)',
            ...
        )
    
    Note:
        For Sprint 2, this is a basic implementation covering common patterns.
        Full presupposition handling requires deeper semantic analysis and may
        be enhanced in future sprints with LLM assistance.
    """
    text_lower = text.lower().strip()
    
    for pattern, presup_type, confidence in PRESUPPOSITION_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            # Build implicit claim based on presupposition type
            if presup_type == 'DEFINITENESS':
                # "the X is Y" presupposes "there exists an X"
                noun_phrase = groups[0] if len(groups) > 0 else "entity"
                implicit_claim = f"There exists a {noun_phrase}"
                
            elif presup_type == 'FACTIVE':
                # "X knows that P" presupposes P is true
                proposition = groups[1] if len(groups) > 1 else "something"
                implicit_claim = f"{proposition} (is true)"
                
            elif presup_type == 'STATE_CHANGE':
                # "X stopped Y-ing" presupposes X was Y-ing
                # Group 0: verb (stopped, ceased, etc.)
                # Group 1: gerund (smoking, running, etc.)
                verb_gerund = groups[1] if len(groups) > 1 else "doing something"
                implicit_claim = f"was {verb_gerund} (before)"
            
            else:
                implicit_claim = "implicit assumption"
            
            trigger_span = (match.start() + start_offset, match.end() + start_offset)
            
            return PresuppositionStructure(
                presupposition_type=presup_type,
                implicit_claim=implicit_claim,
                trigger_span=trigger_span,
                confidence=confidence
            )
    
    return None


def world_construct(
    concision_result: ConcisionResult,
    ctx: Any,  # AgentContext - avoiding import for now
    salt: str
) -> ModuleResult:
    """
    Main world construction function - expand presuppositions and reduce quantifiers.
    
    This is the primary entry point for the world construction stage. It processes
    atomic claims from concision, detects quantifiers, reduces them to propositional
    placeholders, and optionally expands presuppositions.
    
    Args:
        concision_result: Result from the concision stage
        ctx: AgentContext containing configuration and logging
        salt: Deterministic salt for reproducible ID generation
        
    Returns:
        ModuleResult containing:
            - payload: WorldResult with updated atomic claims
            - provenance_record: Tracking for this transformation
            - confidence: Overall confidence score
            - warnings: Any issues encountered
            
    Algorithm:
        1. Iterate through atomic claims from concision
        2. For each claim, check for quantifiers
        3. If quantifier found, reduce to propositional placeholder
        4. Optionally detect and expand presuppositions
        5. Build WorldResult with updated claims and metadata
        6. Create provenance record documenting all reductions
        
    Examples:
        >>> conc_result = ConcisionResult(
        ...     canonical_text="All students must attend",
        ...     atomic_candidates=[AtomicClaim(text="All students must attend", ...)]
        ... )
        >>> result = world_construct(conc_result, ctx, "salt123")
        >>> world_result = WorldResult(**result.payload)
        >>> # Check that quantifier was reduced
        >>> assert len(world_result.atomic_claims) >= 1
        >>> assert any('R' in claim.symbol for claim in world_result.atomic_claims)
    
    Note:
        This function is deterministic when given the same salt value.
        All reductions are documented in the provenance record.
    """
    # Start building the result
    updated_claims: List[AtomicClaim] = []
    reduction_metadata: Dict[str, Any] = {}
    presupposition_metadata: Dict[str, Any] = {}
    quantifier_map: Dict[str, str] = {}
    warnings: List[str] = []
    event_log: List[Dict[str, Any]] = []
    
    # Track overall confidence
    min_confidence = 1.0
    
    # Process each atomic claim
    for idx, claim in enumerate(concision_result.atomic_candidates):
        claim_text = claim.text
        
        # Check for quantifiers in this claim
        quantifier = detect_quantifier(claim_text)
        
        if quantifier:
            # Reduce quantifier to propositional placeholder
            reduced_claim, rationale = reduce_quantifiers(
                text=claim_text,
                salt=salt,
                quantifier=quantifier
            )
            
            # Preserve origin spans from original claim
            if claim.origin_spans:
                reduced_claim.origin_spans = claim.origin_spans
            
            # Add to results
            updated_claims.append(reduced_claim)
            
            # Track reduction in metadata
            quantifier_map[claim_text] = reduced_claim.symbol
            reduction_metadata[reduced_claim.symbol] = {
                'original_text': claim_text,
                'quantifier_type': quantifier.quantifier_type,
                'variable': quantifier.variable,
                'predicate': quantifier.predicate,
                'rationale': rationale,
                'confidence': quantifier.confidence
            }
            
            # Log event
            event_log.append({
                'ts': datetime.now(timezone.utc).isoformat(),
                'event_type': 'quantifier_reduction',
                'message': f'Reduced quantifier in claim {idx}',
                'meta': {
                    'original': claim_text,
                    'reduced_symbol': reduced_claim.symbol,
                    'quantifier_type': quantifier.quantifier_type
                }
            })
            
            # Update min confidence
            min_confidence = min(min_confidence, quantifier.confidence)
            
        else:
            # No quantifier - pass through unchanged
            updated_claims.append(claim)
        
        # Check for presuppositions (Sprint 2: basic implementation)
        presupposition = detect_presupposition(claim_text)
        if presupposition:
            # For Sprint 2, we document but don't expand
            # Full expansion can be added in Sprint 5
            presupposition_metadata[f'claim_{idx}'] = {
                'type': presupposition.presupposition_type,
                'implicit_claim': presupposition.implicit_claim,
                'confidence': presupposition.confidence
            }
            
            warnings.append(
                f"Presupposition detected in '{claim_text[:50]}...': "
                f"{presupposition.implicit_claim}"
            )
            
            # Log event
            event_log.append({
                'ts': datetime.now(timezone.utc).isoformat(),
                'event_type': 'presupposition_detected',
                'message': f'Presupposition in claim {idx}',
                'meta': {
                    'type': presupposition.presupposition_type,
                    'implicit': presupposition.implicit_claim
                }
            })
    
    # Build WorldResult payload
    world_result = WorldResult(
        atomic_claims=updated_claims,
        reduction_metadata=reduction_metadata,
        presupposition_metadata=presupposition_metadata,
        quantifier_map=quantifier_map,
        confidence=min_confidence,
        warnings=warnings
    )
    
    # Create provenance record
    # Generate deterministic provenance ID
    from src.pipeline.provenance import make_provenance_id
    
    prov_id = make_provenance_id(
        normalized_input=concision_result.canonical_text,
        module_id="world_construct",
        module_version="1.0.0",
        salt=salt
    )
    
    provenance = ProvenanceRecord(
        id=prov_id,
        created_at=datetime.now(timezone.utc),
        module_id="world_construct",
        module_version="1.0.0",
        confidence=min_confidence,
        reduction_rationale="; ".join(
            f"{k}: {v['rationale']}" 
            for k, v in reduction_metadata.items()
        ) if reduction_metadata else None,
        event_log=event_log
    )
    
    # Build ModuleResult
    result = ModuleResult(
        payload=world_result.model_dump(),
        provenance_record=provenance,
        confidence=min_confidence,
        warnings=warnings
    )
    
    return result
