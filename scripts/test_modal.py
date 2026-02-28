#!/usr/bin/env python3
"""Test modal operator extraction."""

import json
from src.pipeline.orchestrator import formalize_statement
from src.witty.types import FormalizeOptions

opts = FormalizeOptions(live_mode=True, llm_model='llama-3.3-70b-versatile')

# Test 1: Simple modal conjunction
print("=" * 60)
print("TEST 1: Simple modal conjunction")
print("=" * 60)
r = formalize_statement('Squares are necessarily rectangles. Rectangles are possibly squares', opts)
print(f"Input: {r.original_text}")
print(f"CNF: {r.cnf}")
print(f"CNF Clauses: {r.cnf_clauses}")
print(f"Modal Metadata: {r.modal_metadata}")
print()

# Test 2: Complex modal with conditional and disjunction
print("=" * 60)
print("TEST 2: Complex modal with conditional and disjunction")
print("=" * 60)
r2 = formalize_statement('if I am possibly the president, I am necessarily a citizen. Either way, I am either a man or a woman', opts)
print(f"Input: {r2.original_text}")
print(f"CNF: {r2.cnf}")
print(f"CNF Clauses: {r2.cnf_clauses}")
print(f"Modal Metadata: {r2.modal_metadata}")
print()

print("=" * 60)
print("FULL JSON (Test 2):")
print("=" * 60)
d = r2.model_dump()
subset = {
    'atomic_claims': [{'symbol': c['symbol'], 'text': c['text'], 'modal_context': c['modal_context']} for c in d['atomic_claims']],
    'legend': d['legend'],
    'modal_metadata': d['modal_metadata'],
    'cnf': d['cnf'],
    'cnf_clauses': d['cnf_clauses']
}
print(json.dumps(subset, indent=2))
