"""
Preprocessing Module for Witty Pipeline.

This module transforms raw text into structured, annotated tokens and clauses
with origin span tracking. It handles sentence segmentation, clause detection,
tokenization, POS tagging, and special token annotation (negation, quantifiers,
modals, conditionals, temporals).

Key Features:
- Sentence and clause segmentation with edge case handling
- Token-level linguistic annotation (POS, lemma, dependencies)
- Special token detection (negation, quantifiers, modals, etc.)
- Bidirectional origin span mapping (tokens ↔ character offsets)
- Unicode and multi-byte character support

Author: Victor Rowello
Sprint: 2, Task: 1
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import spacy
from spacy.language import Language
import re


# Global spaCy model instance (lazy-loaded)
_nlp: Optional[Language] = None


def _get_nlp() -> Language:
    """
    Lazy-load and return the spaCy language model.
    
    Returns:
        Language: Loaded spaCy model for English
        
    Note:
        The model is loaded once and cached for subsequent calls to improve
        performance. Uses en_core_web_sm which provides good balance between
        speed and accuracy for our preprocessing needs.
    """
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


class Token(BaseModel):
    """
    Represents a single token with linguistic annotations.
    
    Attributes:
        text: The actual text of the token
        pos: Part-of-speech tag (e.g., 'NOUN', 'VERB', 'ADJ')
        lemma: Lemmatized form of the token
        char_offset: Starting character offset in the original text
        char_end: Ending character offset in the original text
        annotations: Special annotations (negation, quantifier, modal, etc.)
        dep: Dependency relation tag (optional)
        is_punct: Whether this token is punctuation
        is_stop: Whether this token is a stop word
    """
    text: str
    pos: str
    lemma: str
    char_offset: int
    char_end: int
    annotations: List[str] = Field(default_factory=list)
    dep: Optional[str] = None
    is_punct: bool = False
    is_stop: bool = False
    
    def __str__(self) -> str:
        """Human-readable string representation for debugging."""
        annot = f" [{', '.join(self.annotations)}]" if self.annotations else ""
        return f"{self.text}({self.pos}){annot}"


class Clause(BaseModel):
    """
    Represents a clause or sentence segment with origin tracking.
    
    Clauses are natural divisions in text, typically separated by punctuation
    (commas, semicolons, conjunctions) or representing complete sentences.
    
    Attributes:
        text: The text content of the clause
        start_char: Starting character offset in the original text
        end_char: Ending character offset in the original text
        tokens: List of token indices belonging to this clause
        clause_type: Type of clause (e.g., 'main', 'subordinate', 'conditional')
    """
    text: str
    start_char: int
    end_char: int
    tokens: List[int] = Field(default_factory=list)  # Indices into the tokens list
    clause_type: str = "main"
    
    def __str__(self) -> str:
        """Human-readable string representation for debugging."""
        return f"Clause[{self.start_char}:{self.end_char}]: {self.text[:50]}..."


class PreprocessingResult(BaseModel):
    """
    Complete result of the preprocessing stage.
    
    This model contains all the structured information extracted from the raw
    text, including normalized text, clauses, tokens, origin spans, and metadata.
    
    Attributes:
        normalized_text: Cleaned and normalized version of the input
        clauses: List of detected clauses with origin spans
        tokens: List of annotated tokens
        origin_spans: Mapping from token IDs to character spans
        annotations: Additional metadata about the preprocessing
        sentence_boundaries: List of (start, end) character offsets for sentences
    """
    normalized_text: str
    clauses: List[Clause]
    tokens: List[Token]
    origin_spans: Dict[str, List[Tuple[int, int]]]
    annotations: Dict[str, Any] = Field(default_factory=dict)
    sentence_boundaries: List[Tuple[int, int]] = Field(default_factory=list)
    
    def __str__(self) -> str:
        """Human-readable string representation for debugging."""
        return (
            f"PreprocessingResult:\n"
            f"  Sentences: {len(self.sentence_boundaries)}\n"
            f"  Clauses: {len(self.clauses)}\n"
            f"  Tokens: {len(self.tokens)}\n"
            f"  Text: {self.normalized_text[:100]}..."
        )


# Special token patterns for annotation
# These patterns are used to identify tokens that have special logical significance

NEGATION_MARKERS = {
    "not", "no", "never", "neither", "nor", "none", "nobody", 
    "nothing", "nowhere", "n't", "nt"
}

UNIVERSAL_QUANTIFIERS = {
    "all", "every", "each", "any", "always", "everywhere", 
    "everyone", "everybody", "everything"
}

EXISTENTIAL_QUANTIFIERS = {
    "some", "something", "someone", "somebody", "somewhere", 
    "sometimes", "a", "an", "exists", "exist"
}

MODAL_OPERATORS = {
    "must", "should", "ought", "may", "might", "can", "could", 
    "would", "will", "shall", "need", "dare"
}

CONDITIONAL_MARKERS = {
    "if", "when", "unless", "provided", "suppose", "assuming", 
    "given", "whether"
}

TEMPORAL_MARKERS = {
    "before", "after", "while", "during", "until", "since", 
    "as", "whenever", "once"
}


def annotate_special_tokens(token: spacy.tokens.Token) -> List[str]:
    """
    Identify and annotate special tokens with logical significance.
    
    This function checks if a token belongs to any of the special categories
    (negation, quantifiers, modals, conditionals, temporals) and returns
    appropriate annotations.
    
    Args:
        token: A spaCy token object
        
    Returns:
        List of annotation strings (e.g., ['NEGATION'], ['UNIVERSAL_QUANTIFIER'])
        
    Examples:
        >>> # "not" would return ['NEGATION']
        >>> # "all" would return ['UNIVERSAL_QUANTIFIER']
        >>> # "if" would return ['CONDITIONAL']
    """
    annotations = []
    text_lower = token.text.lower()
    lemma_lower = token.lemma_.lower()
    
    # Check for negation markers
    # Handle contractions like "n't" and full forms like "not"
    if text_lower in NEGATION_MARKERS or lemma_lower in NEGATION_MARKERS:
        annotations.append("NEGATION")
    
    # Check for universal quantifiers
    if text_lower in UNIVERSAL_QUANTIFIERS or lemma_lower in UNIVERSAL_QUANTIFIERS:
        annotations.append("UNIVERSAL_QUANTIFIER")
    
    # Check for existential quantifiers
    if text_lower in EXISTENTIAL_QUANTIFIERS or lemma_lower in EXISTENTIAL_QUANTIFIERS:
        annotations.append("EXISTENTIAL_QUANTIFIER")
    
    # Check for modal operators
    if text_lower in MODAL_OPERATORS or lemma_lower in MODAL_OPERATORS:
        annotations.append("MODAL")
    
    # Check for conditional markers
    if text_lower in CONDITIONAL_MARKERS or lemma_lower in CONDITIONAL_MARKERS:
        annotations.append("CONDITIONAL")
    
    # Check for temporal markers
    if text_lower in TEMPORAL_MARKERS or lemma_lower in TEMPORAL_MARKERS:
        annotations.append("TEMPORAL")
    
    return annotations


def segment_sentences(text: str, nlp: Language) -> List[Tuple[int, int, str]]:
    """
    Segment text into sentences with character-level span tracking.
    
    This function uses spaCy's sentence segmentation, which handles:
    - Common abbreviations (Dr., Mr., etc.)
    - Ellipses and multiple punctuation marks
    - Sentence boundaries within quoted text
    
    Args:
        text: The input text to segment
        nlp: Loaded spaCy language model
        
    Returns:
        List of (start_char, end_char, sentence_text) tuples
        
    Note:
        Character offsets are preserved exactly from the original text,
        including any leading/trailing whitespace within sentence boundaries.
    """
    doc = nlp(text)
    sentences = []
    
    for sent in doc.sents:
        # Use token-level character offsets for precise span tracking
        start_char = sent.start_char
        end_char = sent.end_char
        sentence_text = text[start_char:end_char]
        sentences.append((start_char, end_char, sentence_text))
    
    return sentences


def detect_clause_boundaries(
    text: str, 
    sentence_start: int,
    sentence_end: int,
    nlp: Language
) -> List[Tuple[int, int, str, str]]:
    """
    Detect clause boundaries within a sentence.
    
    Clauses are identified by:
    - Coordinating conjunctions (and, but, or) at the top level
    - Subordinating conjunctions (if, when, because)
    - Comma-separated segments that form complete thoughts
    - Semicolons
    
    Args:
        text: The full text (for character offset calculation)
        sentence_start: Starting character offset of the sentence
        sentence_end: Ending character offset of the sentence
        nlp: Loaded spaCy language model
        
    Returns:
        List of (start_char, end_char, clause_text, clause_type) tuples
        
    Note:
        Clause detection is heuristic and may not capture all linguistic
        nuances. Complex nested clauses may be simplified. The clause_type
        helps identify the role of each clause (main, subordinate, etc.).
    """
    sentence_text = text[sentence_start:sentence_end]
    doc = nlp(sentence_text)
    clauses = []
    
    # Strategy: Look for coordinating and subordinating conjunctions,
    # semicolons, and comma-separated segments
    
    # Find all potential clause boundary markers
    boundary_indices = []
    
    for i, token in enumerate(doc):
        # Semicolons always mark clause boundaries
        if token.text == ";":
            boundary_indices.append((i, "semicolon"))
        
        # Coordinating conjunctions at the top level (not in subordinate clauses)
        elif token.dep_ == "cc" and token.head.dep_ == "ROOT":
            boundary_indices.append((i, "coordination"))
        
        # Subordinating conjunctions - IMPORTANT: Don't treat as boundary if at start
        # The conditional marker should be INCLUDED in the clause, not excluded
        # Only mark as boundary if it's in the middle of the sentence
        elif (token.dep_ in {"mark", "prep"} and 
              token.text.lower() in CONDITIONAL_MARKERS | TEMPORAL_MARKERS):
            # Skip if it's at the very beginning (position 0) - it's part of the clause
            if i > 0 and (doc[i-1].is_punct or doc[i-1].dep_ == "punct"):
                boundary_indices.append((i, "subordinate"))
        
        # Commas that separate major constituents
        elif token.text == "," and token.dep_ == "punct":
            # Check if this comma separates clausal elements
            # This is a simplification - real clause detection is more complex
            if i > 0 and i < len(doc) - 1:
                # Look for verb phrases on both sides
                has_verb_before = any(t.pos_ == "VERB" for t in doc[:i])
                has_verb_after = any(t.pos_ == "VERB" for t in doc[i+1:])
                if has_verb_before and has_verb_after:
                    boundary_indices.append((i, "comma_clause"))
    
    # If no boundaries found, the whole sentence is one clause
    if not boundary_indices:
        clause_type = "main"
        clauses.append((sentence_start, sentence_end, sentence_text, clause_type))
        return clauses
    
    # Split into clauses based on boundaries
    clause_start_idx = 0
    
    for boundary_idx, boundary_type in boundary_indices:
        # Create clause from clause_start_idx to boundary_idx
        if boundary_idx > clause_start_idx:
            clause_tokens = doc[clause_start_idx:boundary_idx]
            if clause_tokens:
                clause_start_char = sentence_start + clause_tokens[0].idx
                clause_end_char = sentence_start + clause_tokens[-1].idx + len(clause_tokens[-1].text)
                clause_text = text[clause_start_char:clause_end_char].strip()
                
                # Determine clause type
                if boundary_type == "subordinate":
                    clause_type = "subordinate"
                elif boundary_type == "coordination":
                    clause_type = "coordinate"
                else:
                    clause_type = "main"
                
                if clause_text:  # Only add non-empty clauses
                    clauses.append((clause_start_char, clause_end_char, clause_text, clause_type))
        
        # Move past the boundary marker
        clause_start_idx = boundary_idx + 1
    
    # Add the final clause after the last boundary
    if clause_start_idx < len(doc):
        clause_tokens = doc[clause_start_idx:]
        if clause_tokens:
            clause_start_char = sentence_start + clause_tokens[0].idx
            clause_end_char = sentence_start + clause_tokens[-1].idx + len(clause_tokens[-1].text)
            clause_text = text[clause_start_char:clause_end_char].strip()
            if clause_text:
                clauses.append((clause_start_char, clause_end_char, clause_text, "main"))
    
    # If we still have no clauses, treat the whole sentence as one clause
    if not clauses:
        clauses.append((sentence_start, sentence_end, sentence_text, "main"))
    
    return clauses


def tokenize_and_annotate(text: str, nlp: Language) -> List[Token]:
    """
    Tokenize text and add linguistic annotations.
    
    This function:
    1. Tokenizes the text using spaCy
    2. Extracts POS tags, lemmas, and dependency relations
    3. Annotates special tokens (negation, quantifiers, modals, etc.)
    4. Preserves exact character offsets for origin span mapping
    
    Args:
        text: The input text to tokenize
        nlp: Loaded spaCy language model
        
    Returns:
        List of Token objects with full annotations
        
    Note:
        Character offsets handle multi-byte unicode characters correctly
        by using spaCy's character-based indexing rather than byte offsets.
    """
    doc = nlp(text)
    tokens = []
    
    for spacy_token in doc:
        # Get special annotations
        annotations = annotate_special_tokens(spacy_token)
        
        # Create Token object
        token = Token(
            text=spacy_token.text,
            pos=spacy_token.pos_,
            lemma=spacy_token.lemma_,
            char_offset=spacy_token.idx,
            char_end=spacy_token.idx + len(spacy_token.text),
            annotations=annotations,
            dep=spacy_token.dep_,
            is_punct=spacy_token.is_punct,
            is_stop=spacy_token.is_stop
        )
        
        tokens.append(token)
    
    return tokens


def build_origin_spans(tokens: List[Token]) -> Dict[str, List[Tuple[int, int]]]:
    """
    Build bidirectional mapping between token IDs and character offsets.
    
    This creates a dictionary mapping token identifiers to their character
    spans in the original text, enabling precise tracing of where each
    token came from.
    
    Args:
        tokens: List of Token objects with char_offset and char_end
        
    Returns:
        Dictionary mapping token_id to list of (start, end) character spans
        
    Example:
        {
            "token_0": [(0, 4)],      # "If" at position 0-4
            "token_1": [(5, 7)],      # "it" at position 5-7
            ...
        }
        
    Note:
        Token IDs are formatted as "token_{index}" where index is the
        position in the tokens list. This provides stable identifiers
        for provenance tracking.
    """
    origin_spans = {}
    
    for idx, token in enumerate(tokens):
        token_id = f"token_{idx}"
        origin_spans[token_id] = [(token.char_offset, token.char_end)]
    
    return origin_spans


def normalize_text(text: str) -> str:
    """
    Normalize text while preserving character positions for span tracking.
    
    This function performs minimal normalization to clean the text without
    losing the ability to map back to original character positions:
    - Normalizes unicode characters to NFC form
    - Preserves whitespace structure
    - Does NOT modify character positions
    
    Args:
        text: Raw input text
        
    Returns:
        Normalized text with same character positions as input
        
    Note:
        We intentionally keep normalization minimal in preprocessing to
        maintain accurate origin spans. More aggressive normalization
        (like whitespace collapsing) happens in later pipeline stages
        after span tracking is complete.
    """
    import unicodedata
    
    # Normalize unicode to NFC (canonical composition)
    # This ensures consistent representation of accented characters
    normalized = unicodedata.normalize('NFC', text)
    
    return normalized


def preprocess(input_text: str) -> PreprocessingResult:
    """
    Main preprocessing function that orchestrates the full preprocessing pipeline.
    
    This function:
    1. Normalizes the input text
    2. Segments into sentences
    3. Detects clause boundaries within sentences
    4. Tokenizes and annotates all tokens
    5. Builds origin span mappings
    6. Returns a complete PreprocessingResult
    
    Args:
        input_text: Raw text to preprocess
        
    Returns:
        PreprocessingResult containing normalized text, clauses, tokens,
        origin spans, and metadata
        
    Raises:
        ValueError: If input_text is empty or None
        
    Example:
        >>> result = preprocess("If it rains, the match is cancelled.")
        >>> print(f"Found {len(result.clauses)} clauses")
        >>> print(f"Found {len(result.tokens)} tokens")
        
    Note:
        This function is deterministic - the same input will always produce
        the same output (assuming the same spaCy model version). This is
        critical for reproducibility in CI/CD pipelines.
    """
    if not input_text or not input_text.strip():
        raise ValueError("Input text cannot be empty")
    
    # Load spaCy model
    nlp = _get_nlp()
    
    # Step 1: Normalize text
    normalized_text = normalize_text(input_text)
    
    # Step 2: Segment into sentences
    sentences = segment_sentences(normalized_text, nlp)
    sentence_boundaries = [(s[0], s[1]) for s in sentences]
    
    # Step 3: Detect clauses within each sentence
    all_clauses = []
    for sent_start, sent_end, sent_text in sentences:
        clause_tuples = detect_clause_boundaries(
            normalized_text, sent_start, sent_end, nlp
        )
        for clause_start, clause_end, clause_text, clause_type in clause_tuples:
            clause = Clause(
                text=clause_text,
                start_char=clause_start,
                end_char=clause_end,
                clause_type=clause_type
            )
            all_clauses.append(clause)
    
    # Step 4: Tokenize and annotate
    tokens = tokenize_and_annotate(normalized_text, nlp)
    
    # Step 5: Map tokens to clauses
    # For each clause, find which tokens belong to it
    for clause in all_clauses:
        clause.tokens = [
            idx for idx, token in enumerate(tokens)
            if token.char_offset >= clause.start_char and token.char_end <= clause.end_char
        ]
    
    # Step 6: Build origin spans
    origin_spans = build_origin_spans(tokens)
    
    # Step 7: Collect metadata
    annotations = {
        "num_sentences": len(sentences),
        "num_clauses": len(all_clauses),
        "num_tokens": len(tokens),
        "negation_count": sum(1 for t in tokens if "NEGATION" in t.annotations),
        "quantifier_count": sum(
            1 for t in tokens 
            if "UNIVERSAL_QUANTIFIER" in t.annotations or "EXISTENTIAL_QUANTIFIER" in t.annotations
        ),
        "modal_count": sum(1 for t in tokens if "MODAL" in t.annotations),
        "conditional_count": sum(1 for t in tokens if "CONDITIONAL" in t.annotations),
        "temporal_count": sum(1 for t in tokens if "TEMPORAL" in t.annotations),
    }
    
    # Step 8: Build and return result
    result = PreprocessingResult(
        normalized_text=normalized_text,
        clauses=all_clauses,
        tokens=tokens,
        origin_spans=origin_spans,
        annotations=annotations,
        sentence_boundaries=sentence_boundaries
    )
    
    return result
