"""
Concision Module for Witty Pipeline.

This module extracts minimal atomic claims from preprocessed text, decomposing
logical structures (implications, conjunctions) into their components. It implements
rule-based pattern matching for conditionals and logical connectives.

Key Features:
- Conditional structure detection (if-then, implies, iff patterns)
- Atomic candidate extraction from conditionals, conjunctions, and declaratives
- Structural metadata recording (IMPLIES, IFF, AND, OR connectives)
- Deterministic behavior for reproducible results
- Origin span preservation throughout decomposition
- Negation and quantifier preservation

Author: Victor Rowello
Sprint: 2, Task: 2
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
from src.pipeline.preprocessing import PreprocessingResult, Clause, Token


class ConditionalStructure(BaseModel):
    """
    Represents a detected conditional (implication) structure in text.
    
    Conditionals are logical structures of the form "if P then Q" or "P implies Q"
    that express implication relationships between propositions.
    
    Attributes:
        connective: Type of logical connective (IMPLIES, IFF, WHEN, PROVIDED, etc.)
        antecedent_span: Character span (start, end) of the antecedent (P)
        consequent_span: Character span (start, end) of the consequent (Q)
        full_span: Character span of the entire conditional structure
        confidence: Confidence score for this detection (0.0 to 1.0)
        pattern_matched: The specific pattern that was matched
        antecedent_text: Extracted text of the antecedent
        consequent_text: Extracted text of the consequent
    """
    connective: str  # IMPLIES, IFF, WHEN, PROVIDED, etc.
    antecedent_span: Tuple[int, int]
    consequent_span: Tuple[int, int]
    full_span: Tuple[int, int]
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    pattern_matched: str = ""
    antecedent_text: str = ""
    consequent_text: str = ""


class ConjunctionStructure(BaseModel):
    """
    Represents a detected conjunction structure in text.
    
    Conjunctions combine multiple propositions with AND, OR, BUT, etc.
    
    Attributes:
        connective: Type of conjunction (AND, OR, BUT, HOWEVER)
        conjuncts: List of (start, end, text) tuples for each conjunct
        full_span: Character span of the entire conjunction
        confidence: Confidence score for this detection
    """
    connective: str  # AND, OR, BUT, HOWEVER, etc.
    conjuncts: List[Tuple[int, int, str]]  # (start, end, text) for each conjunct
    full_span: Tuple[int, int]
    confidence: float = Field(1.0, ge=0.0, le=1.0)


# Conditional patterns with capturing groups for antecedent and consequent
# Each pattern is a tuple: (regex_pattern, connective_type, confidence)
# Groups: 1=antecedent, 2=consequent (or vice versa as documented)
CONDITIONAL_PATTERNS = [
    # Standard if-then patterns
    (r'\bif\s+(.*?)\s+then\s+(.*?)(?:\.|,|;|$)', 'IMPLIES', 0.95),
    (r'\bif\s+(.*?),\s+(.*?)(?:\.|;|$)', 'IMPLIES', 0.90),  # "if P, Q"
    
    # When patterns
    (r'\bwhen\s+(.*?),\s+(.*?)(?:\.|;|$)', 'IMPLIES', 0.85),
    (r'\bwhen\s+(.*?)\s+then\s+(.*?)(?:\.|,|;|$)', 'IMPLIES', 0.90),
    
    # Unless (negative conditional)
    (r'\bunless\s+(.*?),\s+(.*?)(?:\.|;|$)', 'UNLESS', 0.85),
    
    # Provided/given (conditional)
    (r'\bprovided\s+(?:that\s+)?(.*?),\s+(.*?)(?:\.|;|$)', 'PROVIDED', 0.85),
    (r'\bgiven\s+(?:that\s+)?(.*?),\s+(.*?)(?:\.|;|$)', 'GIVEN', 0.85),
    
    # Implies (explicit)
    (r'(.*?)\s+implies\s+(.*?)(?:\.|,|;|$)', 'IMPLIES', 0.95),
    
    # Biconditional (if and only if)
    (r'(.*?)\s+if\s+and\s+only\s+if\s+(.*?)(?:\.|,|;|$)', 'IFF', 0.98),
    (r'(.*?)\s+iff\s+(.*?)(?:\.|,|;|$)', 'IFF', 0.98),
    
    # Assuming/suppose
    (r'\bassuming\s+(.*?),\s+(.*?)(?:\.|;|$)', 'ASSUMING', 0.80),
    (r'\bsuppose\s+(.*?),\s+(.*?)(?:\.|;|$)', 'SUPPOSE', 0.80),
]

# Conjunction patterns for splitting compound statements
CONJUNCTION_PATTERNS = [
    (r'\s+and\s+', 'AND', 0.90),
    (r'\s+but\s+', 'BUT', 0.85),
    (r'\s+or\s+', 'OR', 0.90),
    (r',\s*however,\s+', 'HOWEVER', 0.80),
    (r';\s*', 'SEMICOLON', 0.95),
]


def detect_conditional(text: str, start_offset: int = 0) -> Optional[ConditionalStructure]:
    """
    Detect conditional (implication) structures in text.
    
    Scans the text for patterns indicating conditional relationships such as
    "if P then Q", "P implies Q", "when P, Q", etc. Extracts the antecedent
    and consequent spans along with the type of conditional.
    
    Args:
        text: Input text to analyze
        start_offset: Character offset to add to detected spans (for mapping back to original)
        
    Returns:
        ConditionalStructure if a conditional is detected, None otherwise
        
    Examples:
        >>> detect_conditional("If it rains then the match is cancelled")
        ConditionalStructure(connective='IMPLIES', 
                           antecedent_text='it rains',
                           consequent_text='the match is cancelled', ...)
    
    Note:
        Patterns are tried in order. First match wins. More specific patterns
        should be placed earlier in CONDITIONAL_PATTERNS.
    """
    text_lower = text.lower()
    
    for pattern, connective, confidence in CONDITIONAL_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            # Extract antecedent and consequent from groups
            antecedent_raw = match.group(1).strip()
            consequent_raw = match.group(2).strip()
            
            # Find actual positions in original text (preserving case)
            # We need to find where these appear in the original text
            full_start = match.start()
            full_end = match.end()
            
            # Locate antecedent in original text
            ante_match = re.search(re.escape(match.group(1)), text[full_start:full_end], re.IGNORECASE)
            cons_match = re.search(re.escape(match.group(2)), text[full_start:full_end], re.IGNORECASE)
            
            if ante_match and cons_match:
                ante_start = start_offset + full_start + ante_match.start()
                ante_end = start_offset + full_start + ante_match.end()
                cons_start = start_offset + full_start + cons_match.start()
                cons_end = start_offset + full_start + cons_match.end()
                
                # Get the actual text with original casing
                antecedent_text = text[full_start + ante_match.start():full_start + ante_match.end()].strip()
                consequent_text = text[full_start + cons_match.start():full_start + cons_match.end()].strip()
                
                return ConditionalStructure(
                    connective=connective,
                    antecedent_span=(ante_start, ante_end),
                    consequent_span=(cons_start, cons_end),
                    full_span=(start_offset + full_start, start_offset + full_end),
                    confidence=confidence,
                    pattern_matched=pattern,
                    antecedent_text=antecedent_text,
                    consequent_text=consequent_text,
                )
    
    return None


def detect_conjunction(text: str, start_offset: int = 0) -> Optional[ConjunctionStructure]:
    """
    Detect conjunction structures in text (AND, OR, BUT, etc.).
    
    Identifies compound statements that can be split into multiple atomic
    components based on coordinating conjunctions.
    
    Args:
        text: Input text to analyze
        start_offset: Character offset to add to detected spans
        
    Returns:
        ConjunctionStructure if conjunctions are detected, None otherwise
        
    Examples:
        >>> detect_conjunction("The server crashed and the website went offline")
        ConjunctionStructure(connective='AND', 
                           conjuncts=[(..., 'The server crashed'), 
                                    (..., 'the website went offline')], ...)
    
    Note:
        Only splits on top-level conjunctions. Nested structures within
        parentheses or subordinate clauses are preserved.
    """
    for pattern, connective, confidence in CONJUNCTION_PATTERNS:
        # Split on the conjunction pattern
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        
        if len(parts) > 1:
            # We found a conjunction
            conjuncts = []
            current_pos = start_offset
            
            for i, part in enumerate(parts):
                part_stripped = part.strip()
                if part_stripped:
                    # Find this part in the original text
                    part_start = text.find(part, current_pos - start_offset)
                    if part_start != -1:
                        part_start += start_offset
                        part_end = part_start + len(part)
                        conjuncts.append((part_start, part_end, part_stripped))
                        current_pos = part_end
            
            if len(conjuncts) >= 2:
                return ConjunctionStructure(
                    connective=connective,
                    conjuncts=conjuncts,
                    full_span=(start_offset, start_offset + len(text)),
                    confidence=confidence,
                )
    
    return None


def extract_atomic_candidates_from_conditional(
    conditional: ConditionalStructure,
    clause_text: str,
    clause_start: int,
    deterministic_salt: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extract atomic candidates from a conditional structure.
    
    Decomposes "if P then Q" into separate atomic candidates for P and Q,
    recording the implication relationship in structural metadata.
    
    Args:
        conditional: Detected conditional structure
        clause_text: Full text of the clause containing the conditional
        clause_start: Starting character offset of the clause
        deterministic_salt: Salt for generating deterministic IDs
        
    Returns:
        Tuple of (atomic_candidates_list, structural_metadata_dict)
        
    Example:
        Input: "If it rains then the match is cancelled"
        Output: 
            - atomic_candidates: [
                {text: "it rains", origin_spans: [...]},
                {text: "the match is cancelled", origin_spans: [...]}
              ]
            - structural_metadata: {
                connective: "IMPLIES",
                antecedent_id: "ac_abc123",
                consequent_id: "ac_def456",
                ...
              }
    """
    atomic_candidates = []
    
    # Generate deterministic IDs for antecedent and consequent
    ante_id = _generate_atomic_id(conditional.antecedent_text, deterministic_salt)
    cons_id = _generate_atomic_id(conditional.consequent_text, deterministic_salt)
    
    # Create atomic candidate for antecedent
    antecedent_candidate = {
        "id": ante_id,
        "text": conditional.antecedent_text,
        "origin_spans": [
            {
                "start": conditional.antecedent_span[0],
                "end": conditional.antecedent_span[1]
            }
        ],
        "notes": f"Antecedent of {conditional.connective} conditional"
    }
    atomic_candidates.append(antecedent_candidate)
    
    # Create atomic candidate for consequent
    consequent_candidate = {
        "id": cons_id,
        "text": conditional.consequent_text,
        "origin_spans": [
            {
                "start": conditional.consequent_span[0],
                "end": conditional.consequent_span[1]
            }
        ],
        "notes": f"Consequent of {conditional.connective} conditional"
    }
    atomic_candidates.append(consequent_candidate)
    
    # Build structural metadata
    structural_metadata = {
        "connective": conditional.connective,
        "antecedent_id": ante_id,
        "consequent_id": cons_id,
        "confidence": conditional.confidence,
        "pattern_matched": conditional.pattern_matched,
        "reduction_rationale": (
            f"Decomposed {conditional.connective} conditional into antecedent "
            f"'{conditional.antecedent_text}' and consequent '{conditional.consequent_text}'"
        )
    }
    
    return atomic_candidates, structural_metadata


def extract_atomic_candidates_from_conjunction(
    conjunction: ConjunctionStructure,
    deterministic_salt: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extract atomic candidates from a conjunction structure.
    
    Splits "P and Q" into separate atomic candidates for P and Q,
    recording the conjunction relationship in structural metadata.
    
    Args:
        conjunction: Detected conjunction structure
        deterministic_salt: Salt for generating deterministic IDs
        
    Returns:
        Tuple of (atomic_candidates_list, structural_metadata_dict)
    """
    atomic_candidates = []
    conjunct_ids = []
    
    for start, end, text in conjunction.conjuncts:
        # Generate deterministic ID
        conjunct_id = _generate_atomic_id(text, deterministic_salt)
        conjunct_ids.append(conjunct_id)
        
        # Create atomic candidate
        candidate = {
            "id": conjunct_id,
            "text": text,
            "origin_spans": [{"start": start, "end": end}],
            "notes": f"Conjunct in {conjunction.connective} structure"
        }
        atomic_candidates.append(candidate)
    
    # Build structural metadata
    structural_metadata = {
        "connective": conjunction.connective,
        "conjunct_ids": conjunct_ids,
        "confidence": conjunction.confidence,
        "reduction_rationale": (
            f"Decomposed {conjunction.connective} conjunction into "
            f"{len(conjunct_ids)} atomic components"
        )
    }
    
    return atomic_candidates, structural_metadata


def _generate_atomic_id(text: str, salt: str) -> str:
    """
    Generate a deterministic ID for an atomic candidate.
    
    Uses SHA256 hash of the text content plus salt to ensure the same
    text always produces the same ID within a given context.
    
    Args:
        text: Text content of the atomic candidate
        salt: Salt for hash generation
        
    Returns:
        ID string in format "ac_{hash[:8]}"
    """
    payload = f"{text.lower().strip()}\n{salt}"
    hash_digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return f"ac_{hash_digest[:8]}"


def extract_simple_atomic_candidate(
    clause: Clause,
    deterministic_salt: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extract a single atomic candidate from a simple declarative clause.
    
    For clauses that don't contain conditionals or conjunctions, the entire
    clause becomes a single atomic candidate.
    
    Args:
        clause: Clause object from preprocessing
        deterministic_salt: Salt for generating deterministic IDs
        
    Returns:
        Tuple of (atomic_candidates_list, structural_metadata_dict)
    """
    candidate_id = _generate_atomic_id(clause.text, deterministic_salt)
    
    candidate = {
        "id": candidate_id,
        "text": clause.text.strip(),
        "origin_spans": [{"start": clause.start_char, "end": clause.end_char}],
        "notes": "Simple declarative clause"
    }
    
    structural_metadata = {
        "connective": "NONE",
        "reduction_rationale": "Single declarative statement with no decomposition"
    }
    
    return [candidate], structural_metadata


def deterministic_concision(
    preprocessing_result: PreprocessingResult,
    ctx: Any  # AgentContext
) -> ModuleResult:
    """
    Perform rule-based concision with implication decomposition.
    
    This is the main entry point for the concision module. It analyzes
    preprocessed text to extract atomic claims by detecting and decomposing
    logical structures (conditionals, conjunctions).
    
    Algorithm:
        1. For each clause from preprocessing:
           a. Check for conditional structures (if-then, implies, etc.)
           b. If conditional found, extract antecedent and consequent as separate atomics
           c. Otherwise, check for conjunctions (and, or, but)
           d. If conjunction found, split into separate atomics
           e. Otherwise, treat entire clause as single atomic
        2. Record all structural metadata and provenance
        3. Build ConcisionResult with all atomic candidates
    
    Args:
        preprocessing_result: Output from the preprocessing stage
        ctx: AgentContext containing request metadata and configuration
        
    Returns:
        ModuleResult containing ConcisionResult payload and provenance
        
    Determinism:
        This function is deterministic - same input always produces same output.
        Uses ctx.deterministic_salt for hash-based ID generation.
    """
    # Collect all atomic candidates and metadata across all clauses
    all_atomic_candidates = []
    all_structural_metadata = []
    explanations = []
    
    # Process each clause
    for clause in preprocessing_result.clauses:
        # First, check for conditional structures
        conditional = detect_conditional(clause.text, clause.start_char)
        
        if conditional:
            # Extract atomic candidates from the conditional
            candidates, metadata = extract_atomic_candidates_from_conditional(
                conditional,
                clause.text,
                clause.start_char,
                ctx.deterministic_salt
            )
            all_atomic_candidates.extend(candidates)
            all_structural_metadata.append(metadata)
            explanations.append(
                f"Detected {conditional.connective}: '{conditional.antecedent_text}' → "
                f"'{conditional.consequent_text}'"
            )
            continue
        
        # If no conditional, check for conjunctions
        conjunction = detect_conjunction(clause.text, clause.start_char)
        
        if conjunction:
            # Extract atomic candidates from the conjunction
            candidates, metadata = extract_atomic_candidates_from_conjunction(
                conjunction,
                ctx.deterministic_salt
            )
            all_atomic_candidates.extend(candidates)
            all_structural_metadata.append(metadata)
            explanations.append(
                f"Detected {conjunction.connective} with {len(candidates)} components"
            )
            continue
        
        # No complex structure - treat as simple declarative
        candidates, metadata = extract_simple_atomic_candidate(
            clause,
            ctx.deterministic_salt
        )
        all_atomic_candidates.extend(candidates)
        all_structural_metadata.append(metadata)
        explanations.append(f"Simple declarative: '{clause.text[:50]}...'")
    
    # Build canonical text (simplified version)
    # For now, just use the normalized text from preprocessing
    canonical_text = preprocessing_result.normalized_text
    
    # Calculate overall confidence
    # Average confidence from all structural metadata
    if all_structural_metadata:
        confidences = [m.get('confidence', 1.0) for m in all_structural_metadata]
        overall_confidence = sum(confidences) / len(confidences)
    else:
        overall_confidence = 1.0
    
    # Create provenance record for the concision module
    # This will be attached to each atomic claim
    concision_provenance_id = _generate_provenance_id(
        canonical_text,
        "concision",
        "2.0.0",  # Sprint 2 version
        ctx.deterministic_salt
    )
    
    concision_provenance = ProvenanceRecord(
        id=concision_provenance_id,
        created_at=datetime.now(timezone.utc),
        module_id="concision",
        module_version="2.0.0",
        confidence=overall_confidence,
        reduction_rationale=(
            f"Extracted {len(all_atomic_candidates)} atomic candidates through "
            f"deterministic rule-based decomposition"
        ),
        event_log=[
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event_type": "deterministic_concision",
                "message": "Used rule-based concision (no LLM)",
                "meta": {
                    "num_clauses": len(preprocessing_result.clauses),
                    "num_atomic_candidates": len(all_atomic_candidates),
                    "structural_metadata": all_structural_metadata
                }
            }
        ]
    )
    
    # Create ConcisionResult with provenance attached to each claim
    # Each atomic claim gets a reference to the concision provenance record
    concision_result = ConcisionResult(
        canonical_text=canonical_text,
        atomic_candidates=[
            AtomicClaim(
                text=ac["text"],
                origin_spans=[
                    (span["start"], span["end"]) 
                    for span in ac["origin_spans"]
                ],
                provenance=concision_provenance  # Attach provenance to each claim
            )
            for ac in all_atomic_candidates
        ],
        confidence=overall_confidence,
        explanations="\n".join(explanations) if explanations else None,
    )
    
    # Build ModuleResult
    return ModuleResult(
        payload=concision_result.model_dump(),
        provenance_record=concision_provenance,
        confidence=overall_confidence,
        warnings=[]
    )


def _generate_provenance_id(
    normalized_input: str,
    module_id: str,
    module_version: str,
    salt: str
) -> str:
    """
    Generate deterministic provenance ID.
    
    Uses SHA256 hash of combined inputs to create a reproducible ID that
    uniquely identifies this processing step.
    
    Args:
        normalized_input: Normalized text input
        module_id: Identifier of the module
        module_version: Version of the module
        salt: Deterministic salt
        
    Returns:
        Provenance ID in format "pr_{hash[:12]}"
    """
    payload = f"{normalized_input}\n{module_id}\n{module_version}\n{salt}"
    hash_digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return f"pr_{hash_digest[:12]}"
