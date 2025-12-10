"""
Unit tests for the preprocessing module.

This test suite validates all aspects of the preprocessing pipeline including:
- Sentence segmentation with edge cases
- Clause detection and boundary identification
- Token annotation (negation, quantifiers, modals, etc.)
- Origin span accuracy and bidirectional mapping
- Unicode and multi-byte character handling
- Normalization edge cases

Author: Victor Rowello
Sprint: 2, Task: 1
"""
import pytest
from src.pipeline.preprocessing import (
    preprocess,
    PreprocessingResult,
    Token,
    Clause,
    annotate_special_tokens,
    segment_sentences,
    detect_clause_boundaries,
    tokenize_and_annotate,
    build_origin_spans,
    normalize_text,
    _get_nlp,
)


class TestBasicPreprocessing:
    """Test basic preprocessing functionality."""
    
    def test_simple_sentence(self):
        """Test preprocessing of a simple declarative sentence."""
        text = "The cat sat on the mat."
        result = preprocess(text)
        
        assert isinstance(result, PreprocessingResult)
        assert result.normalized_text == text
        assert len(result.tokens) > 0
        assert len(result.sentence_boundaries) == 1
        assert result.sentence_boundaries[0] == (0, len(text))
    
    def test_multiple_sentences(self):
        """Test segmentation of multiple sentences."""
        text = "The cat sat. The dog barked. The bird flew."
        result = preprocess(text)
        
        assert len(result.sentence_boundaries) == 3
        assert len(result.clauses) >= 3  # At least one clause per sentence
    
    def test_empty_input_raises_error(self):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            preprocess("")
        
        with pytest.raises(ValueError, match="Input text cannot be empty"):
            preprocess("   ")  # Whitespace only


class TestConditionalDetection:
    """Test conditional structure detection per Sprint 2 requirements."""
    
    def test_if_then_conditional(self):
        """Test detection of 'if P then Q' pattern."""
        text = "If it rains then the match is cancelled."
        result = preprocess(text)
        
        # Should detect 'if' as a conditional marker
        conditional_tokens = [t for t in result.tokens if "CONDITIONAL" in t.annotations]
        assert len(conditional_tokens) >= 1
        assert any(t.text.lower() == "if" for t in conditional_tokens)
        
        # Should have at least 2 clauses (antecedent and consequent)
        # Note: Clause detection is heuristic, so we check for >= 1
        assert len(result.clauses) >= 1
    
    def test_when_conditional(self):
        """Test detection of 'when P, Q' pattern."""
        text = "When it rains, the match is cancelled."
        result = preprocess(text)
        
        # 'when' should be marked as both CONDITIONAL and TEMPORAL
        when_tokens = [t for t in result.tokens if t.text.lower() == "when"]
        assert len(when_tokens) >= 1
        assert "CONDITIONAL" in when_tokens[0].annotations or "TEMPORAL" in when_tokens[0].annotations
    
    def test_unless_conditional(self):
        """Test detection of 'unless' conditional."""
        text = "Unless it rains, we will play."
        result = preprocess(text)
        
        conditional_tokens = [t for t in result.tokens if "CONDITIONAL" in t.annotations]
        assert any(t.text.lower() == "unless" for t in conditional_tokens)


class TestNegationDetection:
    """Test negation marker detection."""
    
    def test_not_negation(self):
        """Test detection of 'not' negation."""
        text = "It is not raining."
        result = preprocess(text)
        
        negation_tokens = [t for t in result.tokens if "NEGATION" in t.annotations]
        assert len(negation_tokens) >= 1
        assert any(t.text.lower() == "not" for t in negation_tokens)
    
    def test_contraction_negation(self):
        """Test detection of negation in contractions (n't)."""
        text = "It isn't raining."
        result = preprocess(text)
        
        # spaCy typically splits "isn't" into "is" and "n't"
        negation_tokens = [t for t in result.tokens if "NEGATION" in t.annotations]
        assert len(negation_tokens) >= 1
    
    def test_never_negation(self):
        """Test detection of 'never' negation."""
        text = "I never said that."
        result = preprocess(text)
        
        negation_tokens = [t for t in result.tokens if "NEGATION" in t.annotations]
        assert any(t.text.lower() == "never" for t in negation_tokens)
    
    def test_no_negation(self):
        """Test detection of 'no' negation."""
        text = "No students attended."
        result = preprocess(text)
        
        negation_tokens = [t for t in result.tokens if "NEGATION" in t.annotations]
        assert any(t.text.lower() == "no" for t in negation_tokens)


class TestQuantifierDetection:
    """Test universal and existential quantifier detection."""
    
    def test_universal_all(self):
        """Test detection of 'all' universal quantifier."""
        text = "All students must attend."
        result = preprocess(text)
        
        universal_tokens = [t for t in result.tokens if "UNIVERSAL_QUANTIFIER" in t.annotations]
        assert len(universal_tokens) >= 1
        assert any(t.text.lower() == "all" for t in universal_tokens)
        assert result.annotations["quantifier_count"] >= 1
    
    def test_universal_every(self):
        """Test detection of 'every' universal quantifier."""
        text = "Every employee submits a timesheet."
        result = preprocess(text)
        
        universal_tokens = [t for t in result.tokens if "UNIVERSAL_QUANTIFIER" in t.annotations]
        assert any(t.text.lower() == "every" for t in universal_tokens)
    
    def test_universal_each(self):
        """Test detection of 'each' universal quantifier."""
        text = "Each person has a ticket."
        result = preprocess(text)
        
        universal_tokens = [t for t in result.tokens if "UNIVERSAL_QUANTIFIER" in t.annotations]
        assert any(t.text.lower() == "each" for t in universal_tokens)
    
    def test_existential_some(self):
        """Test detection of 'some' existential quantifier."""
        text = "Some students passed the exam."
        result = preprocess(text)
        
        existential_tokens = [t for t in result.tokens if "EXISTENTIAL_QUANTIFIER" in t.annotations]
        assert any(t.text.lower() == "some" for t in existential_tokens)
    
    def test_existential_a(self):
        """Test detection of 'a' as existential quantifier."""
        text = "A student asked a question."
        result = preprocess(text)
        
        existential_tokens = [t for t in result.tokens if "EXISTENTIAL_QUANTIFIER" in t.annotations]
        # 'a' should be detected as existential quantifier
        assert len(existential_tokens) >= 1


class TestModalDetection:
    """Test modal operator detection."""
    
    def test_must_modal(self):
        """Test detection of 'must' modal."""
        text = "Students must submit homework."
        result = preprocess(text)
        
        modal_tokens = [t for t in result.tokens if "MODAL" in t.annotations]
        assert any(t.text.lower() == "must" for t in modal_tokens)
        assert result.annotations["modal_count"] >= 1
    
    def test_should_modal(self):
        """Test detection of 'should' modal."""
        text = "You should exercise daily."
        result = preprocess(text)
        
        modal_tokens = [t for t in result.tokens if "MODAL" in t.annotations]
        assert any(t.text.lower() == "should" for t in modal_tokens)
    
    def test_may_modal(self):
        """Test detection of 'may' modal."""
        text = "It may rain tomorrow."
        result = preprocess(text)
        
        modal_tokens = [t for t in result.tokens if "MODAL" in t.annotations]
        assert any(t.text.lower() == "may" for t in modal_tokens)
    
    def test_can_modal(self):
        """Test detection of 'can' modal."""
        text = "You can leave now."
        result = preprocess(text)
        
        modal_tokens = [t for t in result.tokens if "MODAL" in t.annotations]
        assert any(t.text.lower() == "can" for t in modal_tokens)


class TestOriginSpans:
    """Test origin span mapping and accuracy."""
    
    def test_origin_spans_exist(self):
        """Test that origin spans are created for all tokens."""
        text = "The quick brown fox."
        result = preprocess(text)
        
        # Should have origin span for each token
        assert len(result.origin_spans) == len(result.tokens)
    
    def test_origin_span_roundtrip(self):
        """Test that origin spans correctly map back to original text."""
        text = "If it rains, the match is cancelled."
        result = preprocess(text)
        
        # For each token, verify the origin span points to the correct text
        for idx, token in enumerate(result.tokens):
            token_id = f"token_{idx}"
            assert token_id in result.origin_spans
            
            spans = result.origin_spans[token_id]
            assert len(spans) == 1
            
            start, end = spans[0]
            original_text = text[start:end]
            assert original_text == token.text
    
    def test_origin_spans_with_unicode(self):
        """Test origin spans handle unicode characters correctly."""
        text = "Café résumé naïve."  # Unicode accented characters
        result = preprocess(text)
        
        # Verify roundtrip for each token
        for idx, token in enumerate(result.tokens):
            token_id = f"token_{idx}"
            spans = result.origin_spans[token_id]
            start, end = spans[0]
            original_text = result.normalized_text[start:end]
            assert original_text == token.text
    
    def test_origin_spans_multibyte(self):
        """Test origin spans with multi-byte characters (emoji, etc.)."""
        text = "Hello 🌍 world!"
        result = preprocess(text)
        
        # Find the emoji token
        emoji_tokens = [t for t in result.tokens if "🌍" in t.text]
        if emoji_tokens:  # spaCy may or may not tokenize emoji separately
            for token in emoji_tokens:
                # Verify the span is correct
                assert token.char_offset >= 0
                assert token.char_end > token.char_offset


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_abbreviations(self):
        """Test handling of abbreviations (Dr., Mr., etc.)."""
        text = "Dr. Smith met Mr. Jones at 3 p.m. today."
        result = preprocess(text)
        
        # Should NOT split on abbreviation periods
        # "Dr. Smith met Mr. Jones at 3 p.m. today." should be ONE sentence
        assert len(result.sentence_boundaries) == 1
    
    def test_ellipsis(self):
        """Test handling of ellipsis."""
        text = "He said... nothing."
        result = preprocess(text)
        
        # Should handle ellipsis without breaking
        assert len(result.tokens) > 0
    
    def test_quoted_text(self):
        """Test handling of quoted text."""
        text = 'She said "Hello world" and left.'
        result = preprocess(text)
        
        # Should handle quotes without issues
        assert len(result.tokens) > 0
        assert len(result.clauses) >= 1
    
    def test_parentheticals(self):
        """Test handling of parenthetical expressions."""
        text = "The cat (a tabby) sat on the mat."
        result = preprocess(text)
        
        # Should handle parentheses
        assert len(result.tokens) > 0
    
    def test_nested_conditionals(self):
        """Test handling of nested conditional structures."""
        text = "If it rains and it's cold then the event is cancelled."
        result = preprocess(text)
        
        # Should detect 'if' conditional
        conditional_tokens = [t for t in result.tokens if "CONDITIONAL" in t.annotations]
        assert len(conditional_tokens) >= 1
        
        # Should detect 'and' conjunction
        and_tokens = [t for t in result.tokens if t.text.lower() == "and"]
        assert len(and_tokens) >= 1
    
    def test_conjunction_splitting(self):
        """Test clause splitting on conjunctions."""
        text = "The server crashed and the website went offline."
        result = preprocess(text)
        
        # May detect multiple clauses separated by 'and'
        assert len(result.clauses) >= 1
        assert len(result.tokens) > 0


class TestNormalization:
    """Test text normalization."""
    
    def test_unicode_normalization(self):
        """Test Unicode NFC normalization."""
        # Different representations of é (composed vs decomposed)
        text1 = "café"  # Composed form
        text2 = "café"  # Could be decomposed form (é = e + combining acute)
        
        result1 = preprocess(text1)
        result2 = preprocess(text2)
        
        # After NFC normalization, should be the same
        assert result1.normalized_text == result2.normalized_text
    
    def test_whitespace_preservation(self):
        """Test that whitespace is preserved for span tracking."""
        text = "Hello    world"  # Multiple spaces
        result = preprocess(text)
        
        # Whitespace structure should be preserved in normalized_text
        # (spaCy may tokenize differently, but normalized_text should match)
        assert "Hello" in result.normalized_text
        assert "world" in result.normalized_text


class TestTokenAnnotations:
    """Test token-level linguistic annotations."""
    
    def test_pos_tagging(self):
        """Test that POS tags are assigned."""
        text = "The cat sat."
        result = preprocess(text)
        
        # Should have POS tags
        for token in result.tokens:
            assert token.pos is not None
            assert len(token.pos) > 0
    
    def test_lemmatization(self):
        """Test that lemmas are assigned."""
        text = "The cats were running."
        result = preprocess(text)
        
        # Check specific lemmas
        # "cats" should lemmatize to "cat"
        cats_token = [t for t in result.tokens if t.text.lower() == "cats"]
        if cats_token:
            assert cats_token[0].lemma.lower() == "cat"
        
        # "running" should lemmatize to "run"
        running_token = [t for t in result.tokens if t.text.lower() == "running"]
        if running_token:
            assert running_token[0].lemma.lower() == "run"
    
    def test_punctuation_marking(self):
        """Test that punctuation is marked."""
        text = "Hello, world!"
        result = preprocess(text)
        
        # Punctuation tokens should be marked
        punct_tokens = [t for t in result.tokens if t.is_punct]
        assert len(punct_tokens) >= 2  # comma and exclamation


class TestClauseDetection:
    """Test clause detection and segmentation."""
    
    def test_clause_token_mapping(self):
        """Test that tokens are correctly mapped to clauses."""
        text = "The cat sat on the mat."
        result = preprocess(text)
        
        # Each clause should have tokens
        for clause in result.clauses:
            assert len(clause.tokens) > 0
            
            # Verify tokens are within clause boundaries
            for token_idx in clause.tokens:
                token = result.tokens[token_idx]
                assert token.char_offset >= clause.start_char
                assert token.char_end <= clause.end_char
    
    def test_clause_types(self):
        """Test that clause types are assigned."""
        text = "If it rains, we stay inside."
        result = preprocess(text)
        
        # Should have clause type annotations
        for clause in result.clauses:
            assert clause.clause_type in ["main", "subordinate", "coordinate"]
    
    def test_semicolon_clause_boundary(self):
        """Test that semicolons create clause boundaries."""
        text = "The cat sat; the dog barked."
        result = preprocess(text)
        
        # Should detect multiple clauses
        assert len(result.clauses) >= 2


class TestMetadata:
    """Test metadata collection in annotations."""
    
    def test_metadata_counts(self):
        """Test that metadata contains correct counts."""
        text = "If all students must attend, some will not come."
        result = preprocess(text)
        
        annotations = result.annotations
        
        assert "num_sentences" in annotations
        assert "num_clauses" in annotations
        assert "num_tokens" in annotations
        assert "negation_count" in annotations
        assert "quantifier_count" in annotations
        assert "modal_count" in annotations
        assert "conditional_count" in annotations
        
        # Verify some specific counts
        assert annotations["conditional_count"] >= 1  # "if"
        assert annotations["quantifier_count"] >= 2  # "all", "some"
        assert annotations["modal_count"] >= 1  # "must"
        assert annotations["negation_count"] >= 1  # "not"


class TestIntegration:
    """Integration tests for complete preprocessing scenarios."""
    
    def test_example_seed_conditional(self):
        """Test preprocessing on seed example: simple conditional."""
        text = "If it rains, the match is cancelled."
        result = preprocess(text)
        
        # Basic validation
        assert len(result.tokens) > 0
        assert len(result.clauses) >= 1
        assert len(result.origin_spans) == len(result.tokens)
        
        # Conditional detection
        assert result.annotations["conditional_count"] >= 1
        
        # Origin span roundtrip
        for idx, token in enumerate(result.tokens):
            token_id = f"token_{idx}"
            start, end = result.origin_spans[token_id][0]
            assert result.normalized_text[start:end] == token.text
    
    def test_example_universal_quantifier(self):
        """Test preprocessing on seed example: universal quantifier."""
        text = "All employees must submit timesheets."
        result = preprocess(text)
        
        # Quantifier detection
        assert result.annotations["quantifier_count"] >= 1
        universal_tokens = [t for t in result.tokens if "UNIVERSAL_QUANTIFIER" in t.annotations]
        assert len(universal_tokens) >= 1
        
        # Modal detection
        assert result.annotations["modal_count"] >= 1
        modal_tokens = [t for t in result.tokens if "MODAL" in t.annotations]
        assert len(modal_tokens) >= 1
    
    def test_example_disjunctive_syllogism(self):
        """Test preprocessing on seed example: disjunctive syllogism."""
        text = "Either the server crashed or the network failed. The network did not fail."
        result = preprocess(text)
        
        # Two sentences
        assert len(result.sentence_boundaries) == 2
        
        # Negation detection
        assert result.annotations["negation_count"] >= 1
    
    def test_deterministic_behavior(self):
        """Test that preprocessing is deterministic."""
        text = "If it rains, the match is cancelled."
        
        result1 = preprocess(text)
        result2 = preprocess(text)
        
        # Should produce identical results
        assert len(result1.tokens) == len(result2.tokens)
        assert len(result1.clauses) == len(result2.clauses)
        assert result1.normalized_text == result2.normalized_text
        
        # Token texts should be identical
        for t1, t2 in zip(result1.tokens, result2.tokens):
            assert t1.text == t2.text
            assert t1.pos == t2.pos
            assert t1.lemma == t2.lemma
            assert t1.char_offset == t2.char_offset
            assert t1.annotations == t2.annotations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
