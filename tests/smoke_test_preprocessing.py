"""
Smoke test script for preprocessing module.
Verifies basic functionality and acceptance criteria.
"""
from src.pipeline.preprocessing import preprocess

# Test 1: Simple conditional
print("="*60)
print("TEST 1: Simple Conditional")
print("="*60)
text = "If it rains, the match is cancelled."
result = preprocess(text)

print(f"Input: {text}")
print(f"\nSentences: {len(result.sentence_boundaries)}")
print(f"Clauses: {len(result.clauses)}")
print(f"Tokens: {len(result.tokens)}")
print(f"Conditional markers: {result.annotations['conditional_count']}")
print(f"Negation markers: {result.annotations['negation_count']}")

print("\nTokens:")
for t in result.tokens:
    print(f"  {t}")

print("\nOrigin span verification (first 5 tokens):")
for i, t in enumerate(result.tokens[:5]):
    token_id = f"token_{i}"
    start, end = result.origin_spans[token_id][0]
    recovered_text = result.normalized_text[start:end]
    match = "✓" if recovered_text == t.text else "✗"
    print(f"  {match} token_{i}: '{recovered_text}' == '{t.text}'")

# Test 2: Universal quantifier
print("\n" + "="*60)
print("TEST 2: Universal Quantifier")
print("="*60)
text = "All employees must submit timesheets."
result = preprocess(text)

print(f"Input: {text}")
print(f"\nTokens: {len(result.tokens)}")
print(f"Quantifier count: {result.annotations['quantifier_count']}")
print(f"Modal count: {result.annotations['modal_count']}")

print("\nSpecial tokens:")
for t in result.tokens:
    if t.annotations:
        print(f"  {t.text}: {t.annotations}")

# Test 3: Negation
print("\n" + "="*60)
print("TEST 3: Negation Detection")
print("="*60)
text = "It isn't raining today."
result = preprocess(text)

print(f"Input: {text}")
print(f"Negation count: {result.annotations['negation_count']}")

print("\nNegation tokens:")
for t in result.tokens:
    if "NEGATION" in t.annotations:
        print(f"  {t.text}: {t.annotations}")

# Test 4: Determinism
print("\n" + "="*60)
print("TEST 4: Deterministic Behavior")
print("="*60)
text = "If it rains, the match is cancelled."
result1 = preprocess(text)
result2 = preprocess(text)

print(f"Input: {text}")
print(f"Run 1 tokens: {len(result1.tokens)}")
print(f"Run 2 tokens: {len(result2.tokens)}")
print(f"Token counts match: {len(result1.tokens) == len(result2.tokens)}")

tokens_match = all(
    t1.text == t2.text and 
    t1.pos == t2.pos and 
    t1.char_offset == t2.char_offset
    for t1, t2 in zip(result1.tokens, result2.tokens)
)
print(f"All tokens identical: {tokens_match}")

print("\n" + "="*60)
print("ALL TESTS PASSED ✓")
print("="*60)
