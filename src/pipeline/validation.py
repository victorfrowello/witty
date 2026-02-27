"""
Validation Module for Witty Pipeline.

This module performs sanity checks and validation on the formalization output
to ensure correctness, completeness, and coherence. It validates symbol coverage,
provenance coverage, detects contradictions/tautologies, aggregates confidence,
and performs entity coherence validation.

Key Features:
- Symbol coverage: ensures all symbols in CNF appear in legend
- Provenance coverage: ensures all atomic claims have provenance records
- Tautology detection: identifies trivially true formulas
- Contradiction detection: identifies unsatisfiable formulas
- Entity coherence: validates all entities are grounded
- Confidence aggregation: computes overall pipeline confidence
- Validation report generation with detailed diagnostics

Author: Victor Rowello
Sprint: 3
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import re

from src.witty_types import (
    AtomicClaim,
    ProvenanceRecord,
    ModuleResult,
    WorldResult,
    EntityGrounding,
    CoherenceReport,
)


class ValidationReport(BaseModel):
    """
    Comprehensive validation report for formalization output.
    
    Attributes:
        is_valid: Whether the output passes all required checks
        symbol_coverage: Result of symbol coverage check
        provenance_coverage: Result of provenance coverage check
        tautology_detected: Whether the formula is trivially true
        contradiction_detected: Whether the formula is unsatisfiable
        entity_coherence: Result of entity coherence validation
        aggregated_confidence: Overall pipeline confidence score
        issues: List of validation issues found
        warnings: Non-fatal warnings
        diagnostics: Detailed diagnostic information
    """
    is_valid: bool = True
    symbol_coverage: Dict[str, Any] = Field(default_factory=dict)
    provenance_coverage: Dict[str, Any] = Field(default_factory=dict)
    tautology_detected: bool = False
    contradiction_detected: bool = False
    entity_coherence: Dict[str, Any] = Field(default_factory=dict)
    aggregated_confidence: float = Field(1.0, ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Symbol Coverage Validation
# ============================================================================

def validate_symbol_coverage(
    cnf_clauses: List[List[str]],
    legend: Dict[str, str]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that all symbols in CNF clauses appear in the legend.
    
    Ensures consistency between the CNF representation and the symbol
    definitions. Missing symbols indicate a bug in the pipeline.
    
    Args:
        cnf_clauses: List of CNF clauses (each clause is a list of literals)
        legend: Mapping from symbols to their text definitions
        
    Returns:
        Tuple of (is_valid, details_dict)
        
    Example:
        >>> clauses = [['P1', '¬P2'], ['P3']]
        >>> legend = {'P1': 'it rains', 'P2': 'sunny'}
        >>> valid, details = validate_symbol_coverage(clauses, legend)
        >>> valid
        False  # P3 is missing from legend
        >>> details['missing_symbols']
        ['P3']
    """
    # Extract all symbols from clauses (strip negation)
    cnf_symbols: Set[str] = set()
    for clause in cnf_clauses:
        for literal in clause:
            # Strip negation prefix
            symbol = literal.lstrip('¬').strip()
            # Skip modal operators and complex expressions
            if symbol and not symbol.startswith(('□', '◇', '(')):
                cnf_symbols.add(symbol)
    
    # Get legend symbols
    legend_symbols = set(legend.keys())
    
    # Find missing symbols
    missing_in_legend = cnf_symbols - legend_symbols
    unused_in_cnf = legend_symbols - cnf_symbols
    
    is_valid = len(missing_in_legend) == 0
    
    details = {
        'total_cnf_symbols': len(cnf_symbols),
        'total_legend_symbols': len(legend_symbols),
        'missing_symbols': list(missing_in_legend),
        'unused_symbols': list(unused_in_cnf),
        'is_complete': is_valid
    }
    
    return is_valid, details


# ============================================================================
# Provenance Coverage Validation
# ============================================================================

def validate_provenance_coverage(
    atomic_claims: List[AtomicClaim],
    provenance_records: List[ProvenanceRecord]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that all atomic claims have associated provenance records.
    
    Ensures auditability by checking that every claim can be traced back
    to its source and transformation history.
    
    Args:
        atomic_claims: List of atomic claims
        provenance_records: List of provenance records from the pipeline
        
    Returns:
        Tuple of (is_valid, details_dict)
        
    Example:
        >>> claims = [AtomicClaim(text="it rains", symbol="P1", provenance=prov)]
        >>> valid, details = validate_provenance_coverage(claims, [prov])
        >>> valid
        True
    """
    # Check each claim has provenance
    claims_with_provenance = 0
    claims_without_provenance = []
    
    for i, claim in enumerate(atomic_claims):
        if claim.provenance is not None:
            claims_with_provenance += 1
        else:
            claims_without_provenance.append({
                'index': i,
                'symbol': claim.symbol,
                'text': claim.text[:50] + '...' if len(claim.text) > 50 else claim.text
            })
    
    total_claims = len(atomic_claims)
    coverage_ratio = claims_with_provenance / total_claims if total_claims > 0 else 1.0
    
    # Also check that pipeline modules have provenance
    module_provenance = {p.module_id for p in provenance_records}
    
    is_valid = len(claims_without_provenance) == 0
    
    details = {
        'total_claims': total_claims,
        'claims_with_provenance': claims_with_provenance,
        'claims_without_provenance': claims_without_provenance,
        'coverage_ratio': coverage_ratio,
        'pipeline_modules_tracked': list(module_provenance),
        'is_complete': is_valid
    }
    
    return is_valid, details


# ============================================================================
# Tautology and Contradiction Detection
# ============================================================================

def detect_tautology(cnf_clauses: List[List[str]]) -> Tuple[bool, Optional[str]]:
    """
    Detect if the CNF formula is a tautology (trivially true).
    
    A CNF formula is a tautology if every clause contains complementary
    literals (both P and ¬P for some P).
    
    Args:
        cnf_clauses: List of CNF clauses
        
    Returns:
        Tuple of (is_tautology, explanation)
        
    Example:
        >>> clauses = [['P1', '¬P1']]  # P ∨ ¬P is always true
        >>> is_taut, reason = detect_tautology(clauses)
        >>> is_taut
        True
    """
    if not cnf_clauses:
        return False, None
    
    tautologous_clauses = []
    
    for i, clause in enumerate(cnf_clauses):
        # Extract positive and negative literals
        positive = set()
        negative = set()
        
        for literal in clause:
            if literal.startswith('¬'):
                negative.add(literal[1:])  # Strip negation
            else:
                positive.add(literal)
        
        # Check for complementary literals
        if positive & negative:  # Intersection non-empty
            tautologous_clauses.append(i)
    
    # Formula is tautology if ALL clauses are tautologous
    is_tautology = len(tautologous_clauses) == len(cnf_clauses) and len(cnf_clauses) > 0
    
    if is_tautology:
        return True, "All clauses contain complementary literals (P ∨ ¬P)"
    elif tautologous_clauses:
        return False, f"Clauses {tautologous_clauses} are tautologous but formula is not"
    
    return False, None


def detect_contradiction(cnf_clauses: List[List[str]]) -> Tuple[bool, Optional[str]]:
    """
    Detect if the CNF formula is a contradiction (unsatisfiable).
    
    Simple detection: formula is contradictory if it contains an empty clause
    or if there are unit clauses P and ¬P.
    
    Args:
        cnf_clauses: List of CNF clauses
        
    Returns:
        Tuple of (is_contradiction, explanation)
        
    Example:
        >>> clauses = [['P1'], ['¬P1']]  # P ∧ ¬P is unsatisfiable
        >>> is_contra, reason = detect_contradiction(clauses)
        >>> is_contra
        True
    """
    if not cnf_clauses:
        return False, None
    
    # Check for empty clause (immediate contradiction)
    for i, clause in enumerate(cnf_clauses):
        if len(clause) == 0:
            return True, f"Empty clause at index {i} (immediate contradiction)"
    
    # Check for contradictory unit clauses
    unit_positive = set()
    unit_negative = set()
    
    for clause in cnf_clauses:
        if len(clause) == 1:
            literal = clause[0]
            if literal.startswith('¬'):
                unit_negative.add(literal[1:])
            else:
                unit_positive.add(literal)
    
    contradictory_symbols = unit_positive & unit_negative
    if contradictory_symbols:
        return True, f"Contradictory unit clauses for symbols: {contradictory_symbols}"
    
    return False, None


# ============================================================================
# Entity Coherence Validation
# ============================================================================

def validate_entity_coherence(
    atomic_claims: List[AtomicClaim],
    entity_groundings: Dict[str, EntityGrounding],
    threshold: float = 0.6
) -> Tuple[bool, CoherenceReport]:
    """
    Validate that all entities in atomic claims have corresponding groundings.
    
    Extracts entity mentions from claims and checks that each has an entry
    in the entity_groundings map. Reports completeness ratio and flags
    outputs with low coherence for human review.
    
    Args:
        atomic_claims: List of atomic claims
        entity_groundings: Map from entity text to grounding info
        threshold: Minimum acceptable coherence score (default 0.6)
        
    Returns:
        Tuple of (is_coherent, CoherenceReport)
        
    Example:
        >>> claims = [AtomicClaim(text="John runs", symbol="P1")]
        >>> groundings = {"John": EntityGrounding(entity_text="John", entity_type="PERSON")}
        >>> valid, report = validate_entity_coherence(claims, groundings)
        >>> report.entity_completeness
        1.0
    """
    # Extract potential entities from claims (simple heuristic: capitalized words)
    entity_mentions: Set[str] = set()
    entity_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')
    
    for claim in atomic_claims:
        matches = entity_pattern.findall(claim.text)
        entity_mentions.update(matches)
    
    # Check which entities are grounded
    grounded_entities = set(entity_groundings.keys())
    ungrounded = entity_mentions - grounded_entities
    
    # Calculate completeness
    total_entities = len(entity_mentions)
    grounded_count = len(entity_mentions) - len(ungrounded)
    completeness = grounded_count / total_entities if total_entities > 0 else 1.0
    
    # Check quantifier reduction coverage (all quantified claims should be reduced)
    quantifier_indicators = ['all', 'every', 'some', 'no', 'each']
    quantified_claims = 0
    reduced_claims = 0
    
    for claim in atomic_claims:
        text_lower = claim.text.lower()
        has_quantifier = any(q in text_lower for q in quantifier_indicators)
        if has_quantifier:
            quantified_claims += 1
            # Check if symbol indicates reduction (R, E, or N prefix)
            if claim.symbol and claim.symbol[0] in ('R', 'E', 'N'):
                reduced_claims += 1
    
    quantifier_coverage = reduced_claims / quantified_claims if quantified_claims > 0 else 1.0
    
    # Calculate overall coherence score
    score = (completeness + quantifier_coverage) / 2
    is_coherent = score >= threshold and len(ungrounded) == 0
    
    # Build warnings
    warnings = []
    if ungrounded:
        warnings.append(f"Ungrounded entities: {list(ungrounded)}")
    if score < threshold:
        warnings.append(f"Coherence score {score:.2f} below threshold {threshold}")
    
    report = CoherenceReport(
        is_coherent=is_coherent,
        entity_completeness=completeness,
        quantifier_coverage=quantifier_coverage,
        ungrounded_entities=list(ungrounded),
        warnings=warnings,
        score=score
    )
    
    return is_coherent, report


# ============================================================================
# Confidence Aggregation
# ============================================================================

def aggregate_confidence(
    provenance_records: List[ProvenanceRecord],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Aggregate confidence scores across pipeline modules.
    
    Computes a weighted average of confidence scores from all pipeline
    stages. By default, uses equal weights. Critical stages (concision,
    world construction) can be weighted higher.
    
    Args:
        provenance_records: List of provenance records with confidence scores
        weights: Optional module_id -> weight mapping
        
    Returns:
        Aggregated confidence score (0.0 to 1.0)
        
    Example:
        >>> provs = [
        ...     ProvenanceRecord(id="1", module_id="concision", module_version="1.0", confidence=0.9),
        ...     ProvenanceRecord(id="2", module_id="symbolizer", module_version="1.0", confidence=0.95)
        ... ]
        >>> aggregate_confidence(provs)
        0.925
    """
    if not provenance_records:
        return 1.0
    
    # Default weights (critical stages weighted higher)
    default_weights = {
        'preprocessing': 0.8,
        'concision': 1.2,
        'deterministic_concision': 1.2,
        'world_construct': 1.1,
        'symbolizer': 1.0,
        'cnf_transform': 1.0,
        'validation': 0.9,
    }
    
    weights = weights or default_weights
    
    total_weighted = 0.0
    total_weight = 0.0
    
    for prov in provenance_records:
        weight = weights.get(prov.module_id, 1.0)
        total_weighted += prov.confidence * weight
        total_weight += weight
    
    if total_weight == 0:
        return 1.0
    
    return min(1.0, total_weighted / total_weight)


# ============================================================================
# Main Validation Function
# ============================================================================

def validate_formalization(
    atomic_claims: List[AtomicClaim],
    legend: Dict[str, str],
    cnf_clauses: List[List[str]],
    provenance_records: List[ProvenanceRecord],
    entity_groundings: Optional[Dict[str, EntityGrounding]] = None,
    salt: str = ""
) -> ModuleResult:
    """
    Perform comprehensive validation of formalization output.
    
    Main entry point for the validation module. Runs all validation checks
    and produces a detailed report with provenance tracking.
    
    Args:
        atomic_claims: List of atomic claims
        legend: Symbol to text mapping
        cnf_clauses: CNF representation as list of clauses
        provenance_records: All provenance records from pipeline
        entity_groundings: Optional entity grounding map from world construction
        salt: Deterministic salt for provenance
        
    Returns:
        ModuleResult containing ValidationReport payload and provenance
        
    Example:
        >>> result = validate_formalization(
        ...     atomic_claims=[AtomicClaim(text="P", symbol="P1")],
        ...     legend={"P1": "P"},
        ...     cnf_clauses=[["P1"]],
        ...     provenance_records=[...],
        ...     salt="test"
        ... )
        >>> report = ValidationReport(**result.payload)
        >>> report.is_valid
        True
    """
    event_log = []
    issues = []
    warnings = []
    
    # 1. Symbol coverage validation
    symbol_valid, symbol_details = validate_symbol_coverage(cnf_clauses, legend)
    if not symbol_valid:
        issues.append(f"Symbol coverage incomplete: {symbol_details['missing_symbols']}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'symbol_coverage_check',
        'message': 'Checked symbol coverage',
        'meta': {'is_complete': symbol_valid}
    })
    
    # 2. Provenance coverage validation
    prov_valid, prov_details = validate_provenance_coverage(atomic_claims, provenance_records)
    if not prov_valid:
        warnings.append(f"Some claims lack provenance: {len(prov_details['claims_without_provenance'])} missing")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'provenance_coverage_check',
        'message': 'Checked provenance coverage',
        'meta': {'coverage_ratio': prov_details['coverage_ratio']}
    })
    
    # 3. Tautology detection
    is_tautology, taut_reason = detect_tautology(cnf_clauses)
    if is_tautology:
        warnings.append(f"Formula is a tautology: {taut_reason}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'tautology_check',
        'message': 'Checked for tautology',
        'meta': {'is_tautology': is_tautology}
    })
    
    # 4. Contradiction detection
    is_contradiction, contra_reason = detect_contradiction(cnf_clauses)
    if is_contradiction:
        issues.append(f"Formula is a contradiction: {contra_reason}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'contradiction_check',
        'message': 'Checked for contradiction',
        'meta': {'is_contradiction': is_contradiction}
    })
    
    # 5. Entity coherence validation
    entity_groundings = entity_groundings or {}
    entity_coherent, coherence_report = validate_entity_coherence(
        atomic_claims, entity_groundings
    )
    if not entity_coherent:
        warnings.extend(coherence_report.warnings)
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'entity_coherence_check',
        'message': 'Checked entity coherence',
        'meta': {
            'is_coherent': entity_coherent,
            'score': coherence_report.score
        }
    })
    
    # 6. Confidence aggregation
    aggregated_confidence = aggregate_confidence(provenance_records)
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'confidence_aggregation',
        'message': 'Aggregated pipeline confidence',
        'meta': {'aggregated_confidence': aggregated_confidence}
    })
    
    # Build validation report
    is_valid = (
        symbol_valid and
        not is_contradiction and
        aggregated_confidence >= 0.5
    )
    
    report = ValidationReport(
        is_valid=is_valid,
        symbol_coverage=symbol_details,
        provenance_coverage=prov_details,
        tautology_detected=is_tautology,
        contradiction_detected=is_contradiction,
        entity_coherence=coherence_report.model_dump(),
        aggregated_confidence=aggregated_confidence,
        issues=issues,
        warnings=warnings,
        diagnostics={
            'total_claims': len(atomic_claims),
            'total_symbols': len(legend),
            'total_clauses': len(cnf_clauses),
            'total_provenance_records': len(provenance_records)
        }
    )
    
    # Create provenance
    from src.pipeline.provenance import make_provenance_id
    
    prov_id = make_provenance_id(
        normalized_input=str(len(atomic_claims)) + str(len(cnf_clauses)),
        module_id="validation",
        module_version="1.0.0",
        salt=salt
    )
    
    provenance = ProvenanceRecord(
        id=prov_id,
        created_at=datetime.now(timezone.utc),
        module_id="validation",
        module_version="1.0.0",
        confidence=1.0 if is_valid else 0.8,
        event_log=event_log
    )
    
    return ModuleResult(
        payload=report.model_dump(),
        provenance_record=provenance,
        confidence=aggregated_confidence,
        warnings=warnings
    )
