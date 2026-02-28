# Witty Quickstart Guide

Get up and running with Witty in 5 minutes.

## What is Witty?

Witty is an epistemic formalization engine that converts natural language statements into formal logical representations (CNF). It extracts atomic claims, handles modal logic (necessity/possibility), and produces machine-readable output.

**Witty is NOT a fact-checker.** It formalizes the logical structure of statements assuming they are true.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/victorfrowello/witty.git
cd witty

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## As a Python Library

### Basic Usage

```python
from src.pipeline.orchestrator import formalize

# Formalize a statement
result = formalize("If it rains, the match is cancelled.")

# Access the results
print(result.legend)
# {'P1': 'it rains', 'P2': 'the match is cancelled'}

print(result.cnf)
# '¬P1 ∨ P2'

print(result.cnf_clauses)
# [['¬P1', 'P2']]
```

### With Options

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

# Default - uses LLM for best quality (requires GROQ_API_KEY)
result = formalize("If it rains, the match is cancelled.")

# Reproducible mode (deterministic, no API key needed, simpler results)
opts = FormalizeOptions(reproducible_mode=True)
result = formalize("Alice is happy and Bob is sad.", opts)

# Disable auto-enrichment
opts = FormalizeOptions(no_retrieval=True)
result = formalize("All mammals are warm-blooded.", opts)
```

> **Note**: For best quality results with proper conditional/modal handling, use the default live mode. Reproducible mode uses rule-based extraction optimized for consistency rather than accuracy.

### Setting Up an API Key

For live mode (the default), you need an API key. Create a `.env` file in your project root:

```env
# Groq (recommended - free tier: 100K tokens/day)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

Get a free key at [console.groq.com](https://console.groq.com).

Alternatively, use OpenAI or any OpenAI-compatible provider:
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
# For providers like Together AI, also set:
# OPENAI_API_BASE=https://api.together.xyz/v1
```

### Accessing Rich Output

```python
result = formalize("Squares are necessarily rectangles.")

# Atomic claims with their assigned symbols
for claim in result.atomic_claims:
    print(f"{claim.symbol}: {claim.text}")
    if claim.modal_context:
        print(f"  Modal: {claim.modal_context}")

# Modal metadata for programmatic access
print(result.modal_metadata)
# {'P1': 'NECESSARY'}

# Full provenance chain
for prov in result.provenance:
    print(f"{prov.module_id} v{prov.module_version}: confidence={prov.confidence}")

# Warnings
if result.warnings:
    print(f"Warnings: {result.warnings}")
```

---

## As a CLI Tool

### Basic Command

```bash
python -m src.cli --input input.txt --output result.json
```

### With Options

```bash
# Default mode uses LLM (requires GROQ_API_KEY in .env)
python -m src.cli --input input.txt --output result.json

# Reproducible mode (deterministic, no API key needed)
python -m src.cli --input input.txt --output result.json --reproducible

# Explicitly use live mode (same as default)
python -m src.cli --input input.txt --output result.json --live

# Force enrichment
python -m src.cli --input input.txt --output result.json --retrieval

# Disable auto-enrichment
python -m src.cli --input input.txt --output result.json --no-retrieval

# Debug output
python -m src.cli --input input.txt --output result.json --verbosity debug
```

### Example Input File

Create `input.txt`:
```
If it rains, then the match is cancelled.
```

Run:
```bash
python -m src.cli --input input.txt --output result.json --reproducible
```

Output (`result.json`):
```json
{
  "request_id": "req_20260228120000",
  "original_text": "If it rains, then the match is cancelled.",
  "legend": {
    "P1": "it rains",
    "P2": "the match is cancelled"
  },
  "cnf": "¬P1 ∨ P2",
  "cnf_clauses": [["¬P1", "P2"]],
  "confidence": 0.95
}
```

---

## Common Patterns

### Conditionals (If-Then)

```python
result = formalize("If P then Q.")
# CNF: ¬P ∨ Q
```

### Conjunctions (And)

```python
result = formalize("A and B and C.")
# CNF: A ∧ B ∧ C
```

### Disjunctions (Or)

```python
result = formalize("Either X or Y.")
# CNF: X ∨ Y
```

### Negations

```python
result = formalize("It is not the case that Alice is happy.")
# CNF: ¬P1
```

### Modal Operators

```python
result = formalize("It is necessary that squares have four sides.")
# CNF: □P1

result = formalize("It is possible that it will rain.")
# CNF: ◇P1
```

### Complex Combinations

```python
result = formalize("If necessarily both X and Y, then not possibly Z.")
# Preserves modal structure in CNF
```

---

## Agent-Driven Enrichment

By default, Witty's agent automatically decides when to fetch external context (Wikipedia, DuckDuckGo) to improve formalization.

**Triggers enrichment:**
- Domain quantifiers: "all mammals", "every country"
- Factual claims: dates, statistics, proper nouns
- Underspecified references: "the current president"

**Control enrichment:**
```python
# Let agent decide (default)
result = formalize("All mammals are warm-blooded.")

# Force enrichment
opts = FormalizeOptions(retrieval_enabled=True)
result = formalize("The capital of France is Paris.", opts)

# Disable enrichment
opts = FormalizeOptions(no_retrieval=True)
result = formalize("All mammals are warm-blooded.", opts)
```

---

## Environment Setup

For live mode (LLM-assisted processing), create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

---

## Next Steps

- **[API Reference](API.md)** - Complete API documentation
- **[CLI Usage Guide](public/project-wide/CLI_Usage_Guide.md)** - Detailed CLI options
- **[Examples](../examples/)** - Sample input files

---

## Troubleshooting

### Import Errors

Make sure you're running from the project root:
```bash
cd witty
python -c "from src.pipeline.orchestrator import formalize; print('OK')"
```

### Rate Limits (Live Mode)

Groq free tier has a 100k token/day limit. Use `--reproducible` for unlimited deterministic processing.

### Low Confidence Results

Check `result.warnings` and `result.confidence`. Consider:
- Simplifying input
- Using reproducible mode
- Manual review
