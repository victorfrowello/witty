"""
CNF (Conjunctive Normal Form) Transformation Module for Witty Pipeline.

This module provides AST node types and transformation functions to convert
logical formulas into CNF form. CNF is required for many automated reasoning
systems and SAT solvers.

Key Features:
- AST node types for logical formulas (AND, OR, NOT, IMPLIES, IFF, ATOM)
- Elimination of IMPLIES and IFF operators
- Negation Normal Form (NNF) conversion
- Distribution of OR over AND
- Modal operator preservation at atom level
- Provenance tracking for all transformations

Algorithm:
    1. Parse logical formula into AST
    2. Eliminate IMPLIES: A → B becomes ¬A ∨ B
    3. Eliminate IFF: A ↔ B becomes (A → B) ∧ (B → A)
    4. Convert to NNF: push negations inward to atoms
    5. Distribute OR over AND to get CNF
    6. Flatten nested conjunctions and disjunctions

CNF Form:
    A formula is in CNF if it's a conjunction of disjunctions of literals.
    Example: (P ∨ ¬Q) ∧ (R ∨ S) ∧ (¬T)

Author: Victor Rowello
Sprint: 3
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Union, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timezone
import hashlib

from src.witty_types import (
    ModuleResult,
    ProvenanceRecord,
    AtomicClaim,
)


class NodeType(str, Enum):
    """Types of AST nodes for logical formulas."""
    ATOM = "ATOM"           # Atomic proposition (P, Q, R, etc.)
    NOT = "NOT"             # Negation (¬)
    AND = "AND"             # Conjunction (∧)
    OR = "OR"               # Disjunction (∨)
    IMPLIES = "IMPLIES"     # Implication (→)
    IFF = "IFF"             # Biconditional (↔)
    MODAL = "MODAL"         # Modal operator wrapper (□, ◇)


class ASTNode(BaseModel):
    """
    Abstract Syntax Tree node for logical formulas.
    
    Represents a node in the logical formula tree. Can be an atom (leaf)
    or a compound expression (internal node with children).
    
    Attributes:
        node_type: Type of this node (ATOM, NOT, AND, OR, etc.)
        symbol: For ATOM nodes, the propositional symbol
        children: For compound nodes, the child expressions
        modal_operator: For MODAL nodes, the modal operator type
        original_text: Original text this node represents (for provenance)
    """
    model_config = {"use_enum_values": True}
    
    node_type: NodeType
    symbol: Optional[str] = None
    children: List["ASTNode"] = Field(default_factory=list)
    modal_operator: Optional[str] = None  # "NECESSARY", "POSSIBLE"
    original_text: Optional[str] = None


class CNFResult(BaseModel):
    """
    Result from CNF transformation.
    
    Attributes:
        cnf_string: Human-readable CNF string representation
        cnf_clauses: List of clauses, each clause is a list of literals
        clause_legend: Mapping from clause index to source information
        ast: The final CNF AST (conjunction of disjunctions)
        modal_atoms: For compound modal statements, maps symbol to expansion
                     (e.g., {"M1": {"operator": "POSSIBLE", "scope": {"type": "AND", ...}}})
        transformation_steps: Record of transformation steps applied
        confidence: Confidence in the transformation
        warnings: Any warnings encountered
    """
    cnf_string: str
    cnf_clauses: List[List[str]]
    clause_legend: Dict[int, Dict[str, Any]] = Field(default_factory=dict)
    ast: Optional[Dict[str, Any]] = None
    modal_atoms: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    transformation_steps: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)

# ============================================================================
# AST Construction Helpers
# ============================================================================

def atom(symbol: str, original_text: Optional[str] = None) -> ASTNode:
    """Create an atomic proposition node."""
    return ASTNode(
        node_type=NodeType.ATOM,
        symbol=symbol,
        original_text=original_text
    )


def not_(child: ASTNode) -> ASTNode:
    """Create a negation node."""
    return ASTNode(
        node_type=NodeType.NOT,
        children=[child]
    )


def and_(*children: ASTNode) -> ASTNode:
    """Create a conjunction node."""
    return ASTNode(
        node_type=NodeType.AND,
        children=list(children)
    )


def or_(*children: ASTNode) -> ASTNode:
    """Create a disjunction node."""
    return ASTNode(
        node_type=NodeType.OR,
        children=list(children)
    )


def implies(antecedent: ASTNode, consequent: ASTNode) -> ASTNode:
    """Create an implication node: antecedent → consequent."""
    return ASTNode(
        node_type=NodeType.IMPLIES,
        children=[antecedent, consequent]
    )


def iff(left: ASTNode, right: ASTNode) -> ASTNode:
    """Create a biconditional node: left ↔ right."""
    return ASTNode(
        node_type=NodeType.IFF,
        children=[left, right]
    )


def modal(operator: str, child: ASTNode) -> ASTNode:
    """Create a modal operator node."""
    return ASTNode(
        node_type=NodeType.MODAL,
        modal_operator=operator,
        children=[child]
    )


# ============================================================================
# CNF Transformation Functions
# ============================================================================

def eliminate_implies(node: ASTNode) -> ASTNode:
    """
    Eliminate implication operators.
    
    Transforms A → B into ¬A ∨ B.
    
    Args:
        node: AST node to transform
        
    Returns:
        Transformed AST with IMPLIES eliminated
        
    Example:
        >>> n = implies(atom("P"), atom("Q"))
        >>> result = eliminate_implies(n)
        >>> # Result: OR(NOT(P), Q)
    """
    if node.node_type == NodeType.ATOM:
        return node
    
    if node.node_type == NodeType.MODAL:
        # Preserve modal, recurse into child
        return ASTNode(
            node_type=NodeType.MODAL,
            modal_operator=node.modal_operator,
            children=[eliminate_implies(node.children[0])]
        )
    
    if node.node_type == NodeType.IMPLIES:
        # A → B becomes ¬A ∨ B
        antecedent = eliminate_implies(node.children[0])
        consequent = eliminate_implies(node.children[1])
        return or_(not_(antecedent), consequent)
    
    if node.node_type == NodeType.IFF:
        # A ↔ B becomes (A → B) ∧ (B → A)
        # First convert to implications, then eliminate those
        left = eliminate_implies(node.children[0])
        right = eliminate_implies(node.children[1])
        # (¬A ∨ B) ∧ (¬B ∨ A)
        return and_(
            or_(not_(left), right),
            or_(not_(right), left)
        )
    
    # Recurse for AND, OR, NOT
    return ASTNode(
        node_type=node.node_type,
        symbol=node.symbol,
        children=[eliminate_implies(c) for c in node.children],
        modal_operator=node.modal_operator
    )


def push_negation(node: ASTNode) -> ASTNode:
    """
    Push negations inward to create Negation Normal Form (NNF).
    
    Applies De Morgan's laws and double negation elimination:
    - ¬(A ∧ B) → ¬A ∨ ¬B
    - ¬(A ∨ B) → ¬A ∧ ¬B
    - ¬¬A → A
    
    Args:
        node: AST node to transform
        
    Returns:
        AST in Negation Normal Form
        
    Example:
        >>> n = not_(and_(atom("P"), atom("Q")))
        >>> result = push_negation(n)
        >>> # Result: OR(NOT(P), NOT(Q))
    """
    if node.node_type == NodeType.ATOM:
        return node
    
    if node.node_type == NodeType.MODAL:
        return ASTNode(
            node_type=NodeType.MODAL,
            modal_operator=node.modal_operator,
            children=[push_negation(node.children[0])]
        )
    
    if node.node_type == NodeType.NOT:
        child = node.children[0]
        
        # Double negation: ¬¬A → A
        if child.node_type == NodeType.NOT:
            return push_negation(child.children[0])
        
        # De Morgan: ¬(A ∧ B) → ¬A ∨ ¬B
        if child.node_type == NodeType.AND:
            return or_(*[push_negation(not_(c)) for c in child.children])
        
        # De Morgan: ¬(A ∨ B) → ¬A ∧ ¬B
        if child.node_type == NodeType.OR:
            return and_(*[push_negation(not_(c)) for c in child.children])
        
        # Negation of atom stays as is
        if child.node_type == NodeType.ATOM:
            return node
        
        # Modal negation: treat modal-wrapped atom as atomic for CNF
        if child.node_type == NodeType.MODAL:
            return not_(push_negation(child))
    
    # Recurse for AND, OR
    return ASTNode(
        node_type=node.node_type,
        symbol=node.symbol,
        children=[push_negation(c) for c in node.children],
        modal_operator=node.modal_operator
    )


def distribute_or_over_and(node: ASTNode) -> ASTNode:
    """
    Distribute OR over AND to achieve CNF.
    
    Transforms A ∨ (B ∧ C) into (A ∨ B) ∧ (A ∨ C).
    
    Args:
        node: AST node in NNF
        
    Returns:
        AST in CNF form
        
    Example:
        >>> n = or_(atom("P"), and_(atom("Q"), atom("R")))
        >>> result = distribute_or_over_and(n)
        >>> # Result: AND(OR(P, Q), OR(P, R))
    """
    if node.node_type == NodeType.ATOM:
        return node
    
    if node.node_type == NodeType.NOT:
        return node  # In NNF, NOT only applies to atoms
    
    if node.node_type == NodeType.MODAL:
        return node  # Treat modal expressions as atomic
    
    if node.node_type == NodeType.AND:
        # Recurse and flatten nested ANDs
        distributed_children = [distribute_or_over_and(c) for c in node.children]
        # Flatten: AND(AND(A, B), C) → AND(A, B, C)
        flattened = []
        for child in distributed_children:
            if child.node_type == NodeType.AND:
                flattened.extend(child.children)
            else:
                flattened.append(child)
        return and_(*flattened) if len(flattened) > 1 else flattened[0]
    
    if node.node_type == NodeType.OR:
        # First recurse
        distributed_children = [distribute_or_over_and(c) for c in node.children]
        
        # Check if any child is an AND - if so, distribute
        and_child_idx = None
        for i, child in enumerate(distributed_children):
            if child.node_type == NodeType.AND:
                and_child_idx = i
                break
        
        if and_child_idx is not None:
            # Distribute: A ∨ (B ∧ C) → (A ∨ B) ∧ (A ∨ C)
            and_child = distributed_children[and_child_idx]
            other_children = (
                distributed_children[:and_child_idx] + 
                distributed_children[and_child_idx + 1:]
            )
            
            # Create OR of each AND child with the other children
            new_clauses = []
            for and_subchild in and_child.children:
                new_or = or_(and_subchild, *other_children)
                new_clauses.append(distribute_or_over_and(new_or))
            
            result = and_(*new_clauses)
            return distribute_or_over_and(result)  # Recurse until fully distributed
        
        # No AND children - flatten nested ORs
        flattened = []
        for child in distributed_children:
            if child.node_type == NodeType.OR:
                flattened.extend(child.children)
            else:
                flattened.append(child)
        return or_(*flattened) if len(flattened) > 1 else flattened[0]
    
    return node


def to_cnf(node: ASTNode) -> ASTNode:
    """
    Convert an AST to Conjunctive Normal Form.
    
    Applies the full CNF transformation pipeline:
    1. Eliminate IMPLIES and IFF
    2. Push negations inward (NNF)
    3. Distribute OR over AND
    
    Args:
        node: Input AST
        
    Returns:
        AST in CNF form
        
    Example:
        >>> # P → (Q ∧ R)
        >>> n = implies(atom("P"), and_(atom("Q"), atom("R")))
        >>> cnf = to_cnf(n)
        >>> # Result: (¬P ∨ Q) ∧ (¬P ∨ R)
    """
    # Step 1: Eliminate implications and biconditionals
    step1 = eliminate_implies(node)
    
    # Step 2: Push negations inward (NNF)
    step2 = push_negation(step1)
    
    # Step 3: Distribute OR over AND
    step3 = distribute_or_over_and(step2)
    
    return step3


# ============================================================================
# AST to String/Clause Conversion
# ============================================================================

def ast_to_string(node: ASTNode) -> str:
    """
    Convert an AST node to a human-readable string.
    
    Args:
        node: AST node
        
    Returns:
        String representation using logical symbols
        
    Example:
        >>> n = and_(or_(atom("P"), not_(atom("Q"))), atom("R"))
        >>> ast_to_string(n)
        '(P ∨ ¬Q) ∧ R'
    """
    if node.node_type == NodeType.ATOM:
        return node.symbol or "?"
    
    if node.node_type == NodeType.NOT:
        child_str = ast_to_string(node.children[0])
        if node.children[0].node_type == NodeType.ATOM:
            return f"¬{child_str}"
        return f"¬({child_str})"
    
    if node.node_type == NodeType.AND:
        child_strs = [ast_to_string(c) for c in node.children]
        return " ∧ ".join(f"({s})" if " " in s else s for s in child_strs)
    
    if node.node_type == NodeType.OR:
        child_strs = [ast_to_string(c) for c in node.children]
        return " ∨ ".join(child_strs)
    
    if node.node_type == NodeType.IMPLIES:
        return f"{ast_to_string(node.children[0])} → {ast_to_string(node.children[1])}"
    
    if node.node_type == NodeType.IFF:
        return f"{ast_to_string(node.children[0])} ↔ {ast_to_string(node.children[1])}"
    
    if node.node_type == NodeType.MODAL:
        # Map modal_operator to symbol
        modal_symbols = {
            "NECESSARY": "□",
            "POSSIBLE": "◇",
            "NOT_POSSIBLE": "¬◇",
            "NOT_NECESSARY": "¬□"
        }
        op = modal_symbols.get(node.modal_operator, "?")
        return f"{op}{ast_to_string(node.children[0])}"
    
    return "?"


def extract_clauses(cnf_node: ASTNode) -> List[List[str]]:
    """
    Extract clauses from a CNF AST.
    
    A CNF formula is a conjunction of disjunctions (clauses).
    Each clause is a list of literals (positive or negated atoms).
    
    Args:
        cnf_node: AST in CNF form
        
    Returns:
        List of clauses, where each clause is a list of literal strings
        
    Example:
        >>> # (P ∨ ¬Q) ∧ (R ∨ S)
        >>> cnf = and_(or_(atom("P"), not_(atom("Q"))), or_(atom("R"), atom("S")))
        >>> extract_clauses(cnf)
        [['P', '¬Q'], ['R', 'S']]
    """
    def extract_literals(clause_node: ASTNode) -> List[str]:
        """Extract literals from a disjunction (clause)."""
        if clause_node.node_type == NodeType.ATOM:
            return [clause_node.symbol or "?"]
        
        if clause_node.node_type == NodeType.NOT:
            child = clause_node.children[0]
            if child.node_type == NodeType.ATOM:
                return [f"¬{child.symbol}"]
            # Modal negation
            if child.node_type == NodeType.MODAL:
                return [f"¬{ast_to_string(child)}"]
        
        if clause_node.node_type == NodeType.MODAL:
            return [ast_to_string(clause_node)]
        
        if clause_node.node_type == NodeType.OR:
            literals = []
            for child in clause_node.children:
                literals.extend(extract_literals(child))
            return literals
        
        return [ast_to_string(clause_node)]
    
    # Handle single clause (no AND at top level)
    if cnf_node.node_type != NodeType.AND:
        return [extract_literals(cnf_node)]
    
    # Multiple clauses
    clauses = []
    for clause_child in cnf_node.children:
        clauses.append(extract_literals(clause_child))
    
    return clauses


# ============================================================================
# AST Construction from Claims
# ============================================================================

def _make_atom_with_modal(symbol: str, claim: Optional[AtomicClaim]) -> ASTNode:
    """
    Create an atom node, optionally wrapped with a modal operator.
    
    If the claim has a modal_context (NECESSARY or POSSIBLE), wraps the atom
    in a MODAL node to preserve the modal semantics in the CNF.
    
    Args:
        symbol: The propositional symbol (e.g., "P1")
        claim: The AtomicClaim (may have modal_context)
        
    Returns:
        ASTNode - either a plain ATOM or MODAL(ATOM)
    """
    base_atom = atom(symbol, original_text=claim.text if claim else None)
    
    if claim and claim.modal_context:
        return modal(claim.modal_context, base_atom)
    
    return base_atom


def build_ast_from_claims(
    claims: List[AtomicClaim],
    structural_metadata: Dict[str, Any]
) -> ASTNode:
    """
    Build an AST from atomic claims and structural metadata.
    
    Uses the structural_metadata from concision to reconstruct the logical
    relationships between atomic claims (conditionals, conjunctions, etc.).
    Modal operators from claims are preserved by wrapping atoms in MODAL nodes.
    
    Args:
        claims: List of atomic claims with assigned symbols
        structural_metadata: Metadata about logical structure from concision
        
    Returns:
        AST representing the logical formula
        
    Note:
        Supports mixed structures (e.g., conjunction + conditional) as of Sprint 7.
        Modal operators are preserved at the atom level for simple cases.
    """
    if not claims:
        # Empty formula
        return atom("⊤")  # Tautology
    
    # Build symbol lookup
    symbol_map = {c.symbol: c for c in claims if c.symbol}
    all_symbols = [c.symbol for c in claims if c.symbol]
    
    def make_node(symbol: str) -> ASTNode:
        """Create atom node with modal wrapper if applicable."""
        claim = symbol_map.get(symbol)
        return _make_atom_with_modal(symbol, claim)
    
    # Track which symbols are used in relationships
    used_in_relationships = set()
    ast_parts = []
    
    # Check for conditional structure
    conditional_info = structural_metadata.get("conditional", {})
    if conditional_info:
        # Conditional: antecedent → consequent
        antecedent_symbols = conditional_info.get("antecedent_claims", [])
        consequent_symbols = conditional_info.get("consequent_claims", [])
        
        # Track symbols used in conditional
        used_in_relationships.update(antecedent_symbols)
        used_in_relationships.update(consequent_symbols)
        
        # Build antecedent (conjunction if multiple)
        ant_nodes = [make_node(s) for s in antecedent_symbols if s in symbol_map or s.startswith(("P", "R", "E"))]
        if not ant_nodes:
            ant_nodes = [make_node(claims[0].symbol)] if claims else [atom("P1")]
        antecedent = and_(*ant_nodes) if len(ant_nodes) > 1 else ant_nodes[0]
        
        # Build consequent (conjunction if multiple)
        cons_nodes = [make_node(s) for s in consequent_symbols if s in symbol_map or s.startswith(("P", "R", "E"))]
        if not cons_nodes and len(claims) > 1:
            cons_nodes = [make_node(claims[-1].symbol)] if claims[-1].symbol else [atom("P2")]
        elif not cons_nodes:
            cons_nodes = [atom("P2")]
        consequent = and_(*cons_nodes) if len(cons_nodes) > 1 else cons_nodes[0]
        
        ast_parts.append(implies(antecedent, consequent))
    
    # Check for biconditional structure
    biconditional_info = structural_metadata.get("biconditional", {})
    if biconditional_info:
        left_symbols = biconditional_info.get("left_claims", [])
        right_symbols = biconditional_info.get("right_claims", [])
        
        used_in_relationships.update(left_symbols)
        used_in_relationships.update(right_symbols)
        
        left_nodes = [make_node(s) for s in left_symbols if s in symbol_map or s.startswith(("P", "R", "E"))]
        right_nodes = [make_node(s) for s in right_symbols if s in symbol_map or s.startswith(("P", "R", "E"))]
        
        if left_nodes and right_nodes:
            left = and_(*left_nodes) if len(left_nodes) > 1 else left_nodes[0]
            right = and_(*right_nodes) if len(right_nodes) > 1 else right_nodes[0]
            ast_parts.append(iff(left, right))
    
    # Check for explicit conjunction structure
    conjunction_info = structural_metadata.get("conjunction", {})
    if conjunction_info:
        conjunct_symbols = conjunction_info.get("conjunct_claims", [])
        used_in_relationships.update(conjunct_symbols)
        
        # Conjuncts are individual atoms to be ANDed
        conj_nodes = [make_node(s) for s in conjunct_symbols if s in symbol_map or s.startswith(("P", "R", "E"))]
        ast_parts.extend(conj_nodes)
    
    # Check for disjunction structure
    disjunction_info = structural_metadata.get("disjunction", {})
    if disjunction_info:
        disjunct_symbols = disjunction_info.get("disjunct_claims", [])
        used_in_relationships.update(disjunct_symbols)
        
        disj_nodes = [make_node(s) for s in disjunct_symbols if s in symbol_map or s.startswith(("P", "R", "E"))]
        if disj_nodes:
            ast_parts.append(or_(*disj_nodes) if len(disj_nodes) > 1 else disj_nodes[0])
    
    # Add any remaining claims not in explicit relationships as conjuncts
    # (for backwards compatibility with rule-based concision)
    structure_type = structural_metadata.get("structure_type", "")
    if not ast_parts or structure_type not in ("conditional", "biconditional", "disjunction", "mixed"):
        remaining_symbols = [s for s in all_symbols if s not in used_in_relationships]
        if remaining_symbols:
            remaining_nodes = [make_node(s) for s in remaining_symbols]
            ast_parts.extend(remaining_nodes)
    
    # Combine all parts with AND
    if not ast_parts:
        # No structure found, default to conjunction of all claims
        nodes = [make_node(c.symbol) for c in claims if c.symbol]
        if nodes:
            return and_(*nodes) if len(nodes) > 1 else nodes[0]
        return atom("P1")
    
    if len(ast_parts) == 1:
        return ast_parts[0]
    
    return and_(*ast_parts)


# ============================================================================
# Main CNF Transform Function
# ============================================================================

def cnf_transform(
    claims: List[AtomicClaim],
    legend: Dict[str, str],
    structural_metadata: Dict[str, Any],
    salt: str
) -> ModuleResult:
    """
    Transform atomic claims into CNF representation.
    
    Main entry point for CNF transformation. Builds an AST from the claims
    and structural metadata, converts to CNF, and returns the result with
    provenance tracking.
    
    Args:
        claims: List of atomic claims with assigned symbols
        legend: Symbol to text mapping
        structural_metadata: Logical structure metadata from concision
        salt: Deterministic salt for provenance
        
    Returns:
        ModuleResult containing CNFResult payload and provenance
        
    Example:
        >>> claims = [
        ...     AtomicClaim(text="it rains", symbol="P1"),
        ...     AtomicClaim(text="match is cancelled", symbol="P2")
        ... ]
        >>> legend = {"P1": "it rains", "P2": "match is cancelled"}
        >>> meta = {"conditional": {"antecedent_claims": ["P1"], "consequent_claims": ["P2"]}}
        >>> result = cnf_transform(claims, legend, meta, "salt")
        >>> # CNF: ¬P1 ∨ P2 (equivalent to P1 → P2)
    """
    event_log = []
    warnings = []
    transformation_steps = []
    
    # Step 1: Build AST from claims
    ast = build_ast_from_claims(claims, structural_metadata)
    transformation_steps.append(f"Built AST: {ast_to_string(ast)}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'ast_construction',
        'message': 'Built AST from claims and structural metadata'
    })
    
    # Step 2: Eliminate implications
    step1 = eliminate_implies(ast)
    transformation_steps.append(f"After IMPLIES elimination: {ast_to_string(step1)}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'eliminate_implies',
        'message': 'Eliminated IMPLIES and IFF operators'
    })
    
    # Step 3: Push negations (NNF)
    step2 = push_negation(step1)
    transformation_steps.append(f"After NNF conversion: {ast_to_string(step2)}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'nnf_conversion',
        'message': 'Converted to Negation Normal Form'
    })
    
    # Step 4: Distribute OR over AND (CNF)
    cnf_ast = distribute_or_over_and(step2)
    transformation_steps.append(f"Final CNF: {ast_to_string(cnf_ast)}")
    
    event_log.append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'event_type': 'cnf_distribution',
        'message': 'Distributed OR over AND to achieve CNF'
    })
    
    # Extract clauses
    cnf_clauses = extract_clauses(cnf_ast)
    cnf_string = ast_to_string(cnf_ast)
    
    # Build clause legend
    clause_legend = {}
    for i, clause in enumerate(cnf_clauses):
        clause_legend[i] = {
            'literals': clause,
            'sources': [legend.get(lit.replace('¬', '').replace('□', '').replace('◇', ''), lit) for lit in clause]
        }
    
    # Extract modal atoms (compound modal statements)
    modal_atoms = {}
    for claim in claims:
        if claim.symbol and claim.modal_scope:
            modal_atoms[claim.symbol] = {
                'operator': claim.modal_context,
                'scope': claim.modal_scope,
                'text': claim.text
            }
    
    # Create CNF result
    cnf_result = CNFResult(
        cnf_string=cnf_string,
        cnf_clauses=cnf_clauses,
        clause_legend=clause_legend,
        ast=cnf_ast.model_dump(),
        modal_atoms=modal_atoms,
        transformation_steps=transformation_steps,
        confidence=1.0,  # Deterministic transformation
        warnings=warnings
    )
    
    # Create provenance
    from src.pipeline.provenance import make_provenance_id
    
    prov_id = make_provenance_id(
        normalized_input=cnf_string,
        module_id="cnf_transform",
        module_version="1.0.0",
        salt=salt
    )
    
    provenance = ProvenanceRecord(
        id=prov_id,
        created_at=datetime.now(timezone.utc),
        module_id="cnf_transform",
        module_version="1.0.0",
        confidence=1.0,
        event_log=event_log
    )
    
    return ModuleResult(
        payload=cnf_result.model_dump(),
        provenance_record=provenance,
        confidence=1.0,
        warnings=warnings
    )
