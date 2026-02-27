"""
Sprint 3 Tests: CNF Transformation Module.

Tests for the CNF (Conjunctive Normal Form) transformer, including AST
construction, implication elimination, NNF conversion, and distribution.

Author: Victor Rowello
Sprint: 3
"""
import pytest
from src.pipeline.cnf import (
    ASTNode,
    NodeType,
    CNFResult,
    atom,
    not_,
    and_,
    or_,
    implies,
    iff,
    modal,
    eliminate_implies,
    push_negation,
    distribute_or_over_and,
    to_cnf,
    ast_to_string,
    extract_clauses,
    build_ast_from_claims,
    cnf_transform,
)
from src.witty_types import AtomicClaim


class TestASTConstruction:
    """Tests for AST node construction helpers."""
    
    def test_atom_creation(self):
        """Test creating atomic proposition nodes."""
        node = atom("P")
        assert node.node_type == NodeType.ATOM
        assert node.symbol == "P"
        assert node.children == []
    
    def test_negation_creation(self):
        """Test creating negation nodes."""
        p = atom("P")
        neg_p = not_(p)
        assert neg_p.node_type == NodeType.NOT
        assert len(neg_p.children) == 1
        assert neg_p.children[0].symbol == "P"
    
    def test_conjunction_creation(self):
        """Test creating conjunction nodes."""
        p = atom("P")
        q = atom("Q")
        conj = and_(p, q)
        assert conj.node_type == NodeType.AND
        assert len(conj.children) == 2
    
    def test_disjunction_creation(self):
        """Test creating disjunction nodes."""
        p = atom("P")
        q = atom("Q")
        disj = or_(p, q)
        assert disj.node_type == NodeType.OR
        assert len(disj.children) == 2
    
    def test_implication_creation(self):
        """Test creating implication nodes."""
        p = atom("P")
        q = atom("Q")
        impl = implies(p, q)
        assert impl.node_type == NodeType.IMPLIES
        assert len(impl.children) == 2
    
    def test_biconditional_creation(self):
        """Test creating biconditional nodes."""
        p = atom("P")
        q = atom("Q")
        bicon = iff(p, q)
        assert bicon.node_type == NodeType.IFF
        assert len(bicon.children) == 2


class TestImplicationElimination:
    """Tests for implication and biconditional elimination."""
    
    def test_eliminate_simple_implies(self):
        """P → Q becomes ¬P ∨ Q."""
        p = atom("P")
        q = atom("Q")
        impl = implies(p, q)
        
        result = eliminate_implies(impl)
        
        # Should be OR(NOT(P), Q)
        assert result.node_type == NodeType.OR
        assert len(result.children) == 2
        assert result.children[0].node_type == NodeType.NOT
        assert result.children[1].symbol == "Q"
    
    def test_eliminate_iff(self):
        """P ↔ Q becomes (¬P ∨ Q) ∧ (¬Q ∨ P)."""
        p = atom("P")
        q = atom("Q")
        bicon = iff(p, q)
        
        result = eliminate_implies(bicon)
        
        # Should be AND of two disjunctions
        assert result.node_type == NodeType.AND
        assert len(result.children) == 2
    
    def test_eliminate_nested_implies(self):
        """(P → Q) → R elimination."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        nested = implies(implies(p, q), r)
        
        result = eliminate_implies(nested)
        
        # Should not contain any IMPLIES nodes
        def has_implies(node):
            if node.node_type == NodeType.IMPLIES:
                return True
            return any(has_implies(c) for c in node.children)
        
        assert not has_implies(result)
    
    def test_atom_unchanged(self):
        """Atoms should pass through unchanged."""
        p = atom("P")
        result = eliminate_implies(p)
        assert result.node_type == NodeType.ATOM
        assert result.symbol == "P"


class TestNNFConversion:
    """Tests for Negation Normal Form conversion."""
    
    def test_double_negation_elimination(self):
        """¬¬P becomes P."""
        p = atom("P")
        double_neg = not_(not_(p))
        
        result = push_negation(double_neg)
        
        assert result.node_type == NodeType.ATOM
        assert result.symbol == "P"
    
    def test_de_morgan_and(self):
        """¬(P ∧ Q) becomes ¬P ∨ ¬Q."""
        p = atom("P")
        q = atom("Q")
        neg_conj = not_(and_(p, q))
        
        result = push_negation(neg_conj)
        
        assert result.node_type == NodeType.OR
        assert all(c.node_type == NodeType.NOT for c in result.children)
    
    def test_de_morgan_or(self):
        """¬(P ∨ Q) becomes ¬P ∧ ¬Q."""
        p = atom("P")
        q = atom("Q")
        neg_disj = not_(or_(p, q))
        
        result = push_negation(neg_disj)
        
        assert result.node_type == NodeType.AND
        assert all(c.node_type == NodeType.NOT for c in result.children)
    
    def test_negation_on_atom(self):
        """¬P stays as ¬P."""
        p = atom("P")
        neg_p = not_(p)
        
        result = push_negation(neg_p)
        
        assert result.node_type == NodeType.NOT
        assert result.children[0].symbol == "P"


class TestCNFDistribution:
    """Tests for OR distribution over AND."""
    
    def test_simple_distribution(self):
        """P ∨ (Q ∧ R) becomes (P ∨ Q) ∧ (P ∨ R)."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        formula = or_(p, and_(q, r))
        
        result = distribute_or_over_and(formula)
        
        # Should be AND at top level
        assert result.node_type == NodeType.AND
        # With two OR children
        assert all(c.node_type == NodeType.OR for c in result.children)
    
    def test_no_distribution_needed(self):
        """P ∨ Q stays as P ∨ Q."""
        p = atom("P")
        q = atom("Q")
        formula = or_(p, q)
        
        result = distribute_or_over_and(formula)
        
        assert result.node_type == NodeType.OR
    
    def test_conjunction_recurses(self):
        """(P ∧ Q) ∧ R stays as AND."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        formula = and_(and_(p, q), r)
        
        result = distribute_or_over_and(formula)
        
        # Should be flattened AND
        assert result.node_type == NodeType.AND


class TestFullCNFConversion:
    """Tests for complete CNF conversion."""
    
    def test_implies_to_cnf(self):
        """P → Q in CNF is ¬P ∨ Q."""
        p = atom("P")
        q = atom("Q")
        impl = implies(p, q)
        
        cnf = to_cnf(impl)
        
        # Single clause: ¬P ∨ Q
        assert cnf.node_type == NodeType.OR
    
    def test_complex_formula_to_cnf(self):
        """P → (Q ∧ R) in CNF is (¬P ∨ Q) ∧ (¬P ∨ R)."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        impl = implies(p, and_(q, r))
        
        cnf = to_cnf(impl)
        
        # Should be conjunction of two clauses
        assert cnf.node_type == NodeType.AND
    
    def test_conjunction_is_cnf(self):
        """P ∧ Q is already in CNF."""
        p = atom("P")
        q = atom("Q")
        conj = and_(p, q)
        
        cnf = to_cnf(conj)
        
        assert cnf.node_type == NodeType.AND


class TestASTToString:
    """Tests for AST to string conversion."""
    
    def test_atom_string(self):
        """Atom P prints as P."""
        p = atom("P")
        assert ast_to_string(p) == "P"
    
    def test_negation_string(self):
        """¬P prints correctly."""
        p = atom("P")
        neg = not_(p)
        assert ast_to_string(neg) == "¬P"
    
    def test_conjunction_string(self):
        """P ∧ Q prints correctly."""
        p = atom("P")
        q = atom("Q")
        conj = and_(p, q)
        result = ast_to_string(conj)
        assert "∧" in result
        assert "P" in result
        assert "Q" in result
    
    def test_disjunction_string(self):
        """P ∨ Q prints correctly."""
        p = atom("P")
        q = atom("Q")
        disj = or_(p, q)
        result = ast_to_string(disj)
        assert "∨" in result


class TestClauseExtraction:
    """Tests for extracting clauses from CNF."""
    
    def test_single_clause(self):
        """Single disjunction gives one clause."""
        p = atom("P")
        q = atom("Q")
        disj = or_(p, not_(q))
        
        clauses = extract_clauses(disj)
        
        assert len(clauses) == 1
        assert set(clauses[0]) == {"P", "¬Q"}
    
    def test_multiple_clauses(self):
        """Conjunction of disjunctions gives multiple clauses."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        cnf = and_(or_(p, q), or_(r, not_(p)))
        
        clauses = extract_clauses(cnf)
        
        assert len(clauses) == 2
    
    def test_unit_clause(self):
        """Single atom is a unit clause."""
        p = atom("P")
        
        clauses = extract_clauses(p)
        
        assert len(clauses) == 1
        assert clauses[0] == ["P"]


class TestBuildASTFromClaims:
    """Tests for building AST from atomic claims."""
    
    def test_empty_claims(self):
        """Empty claims gives tautology."""
        result = build_ast_from_claims([], {})
        assert result.symbol == "⊤"
    
    def test_single_claim(self):
        """Single claim gives single atom."""
        claims = [AtomicClaim(text="it rains", symbol="P1")]
        result = build_ast_from_claims(claims, {})
        assert result.symbol == "P1"
    
    def test_multiple_claims_conjunction(self):
        """Multiple claims give conjunction."""
        claims = [
            AtomicClaim(text="it rains", symbol="P1"),
            AtomicClaim(text="it is cold", symbol="P2"),
        ]
        result = build_ast_from_claims(claims, {})
        assert result.node_type == NodeType.AND
    
    def test_conditional_metadata(self):
        """Conditional metadata builds implication."""
        claims = [
            AtomicClaim(text="it rains", symbol="P1"),
            AtomicClaim(text="match cancelled", symbol="P2"),
        ]
        metadata = {
            "conditional": {
                "antecedent_claims": ["P1"],
                "consequent_claims": ["P2"]
            }
        }
        result = build_ast_from_claims(claims, metadata)
        assert result.node_type == NodeType.IMPLIES


class TestCNFTransform:
    """Tests for the main CNF transform function."""
    
    def test_transform_simple_claims(self):
        """Transform simple claims to CNF."""
        claims = [
            AtomicClaim(text="it rains", symbol="P1"),
            AtomicClaim(text="match cancelled", symbol="P2"),
        ]
        legend = {"P1": "it rains", "P2": "match cancelled"}
        
        result = cnf_transform(claims, legend, {}, "test_salt")
        
        assert result.confidence == 1.0
        assert result.provenance_record.module_id == "cnf_transform"
        
        cnf_data = CNFResult(**result.payload)
        assert cnf_data.cnf_string is not None
        assert len(cnf_data.cnf_clauses) >= 1
    
    def test_transform_conditional(self):
        """Transform conditional structure to CNF."""
        claims = [
            AtomicClaim(text="it rains", symbol="P1"),
            AtomicClaim(text="match cancelled", symbol="P2"),
        ]
        legend = {"P1": "it rains", "P2": "match cancelled"}
        metadata = {
            "conditional": {
                "antecedent_claims": ["P1"],
                "consequent_claims": ["P2"]
            }
        }
        
        result = cnf_transform(claims, legend, metadata, "test_salt")
        cnf_data = CNFResult(**result.payload)
        
        # P → Q in CNF should have ¬P in some clause
        all_literals = [lit for clause in cnf_data.cnf_clauses for lit in clause]
        assert any("¬" in lit for lit in all_literals)
    
    def test_transformation_steps_recorded(self):
        """Transformation steps should be recorded."""
        claims = [AtomicClaim(text="P", symbol="P1")]
        legend = {"P1": "P"}
        
        result = cnf_transform(claims, legend, {}, "test_salt")
        cnf_data = CNFResult(**result.payload)
        
        assert len(cnf_data.transformation_steps) > 0
    
    def test_deterministic_provenance(self):
        """Provenance ID should be deterministic."""
        claims = [AtomicClaim(text="P", symbol="P1")]
        legend = {"P1": "P"}
        
        result1 = cnf_transform(claims, legend, {}, "same_salt")
        result2 = cnf_transform(claims, legend, {}, "same_salt")
        
        # Same inputs should give same provenance ID
        assert result1.provenance_record.id == result2.provenance_record.id


class TestCNFEdgeCases:
    """Edge case tests for CNF transformation."""
    
    def test_deeply_nested_formula(self):
        """Deep nesting should be handled."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        
        # ((P → Q) ∧ R) → P
        nested = implies(and_(implies(p, q), r), p)
        cnf = to_cnf(nested)
        
        # Should complete without error
        clauses = extract_clauses(cnf)
        assert len(clauses) >= 1
    
    def test_triple_conjunction(self):
        """Triple conjunction should be handled."""
        p = atom("P")
        q = atom("Q")
        r = atom("R")
        
        triple = and_(p, q, r)
        cnf = to_cnf(triple)
        
        # Should give 3 unit clauses
        clauses = extract_clauses(cnf)
        assert len(clauses) == 3
    
    def test_modal_preservation(self):
        """Modal operators should be preserved at atom level."""
        p = atom("P")
        necessary_p = modal("NECESSARY", p)
        
        # Modal should pass through CNF unchanged (at atom level)
        cnf = to_cnf(necessary_p)
        string = ast_to_string(cnf)
        assert "□" in string
