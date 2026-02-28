# Witty v1.0 — Epistemic Formalization Engine

[![Tests](https://img.shields.io/badge/tests-549%20passed-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.9+-blue)]()
[![License](https://img.shields.io/badge/license-GPL--3.0-green)]()

Witty converts natural language statements into machine-readable logical formalizations. It extracts atomic claims, handles modal logic (necessity/possibility), and produces CNF (Conjunctive Normal Form) output with complete provenance tracking.

**Witty is NOT a fact-checker.** It formalizes the logical structure of statements assuming they are true.

---

## Quick Start

### Installation

```bash
git clone https://github.com/victorfrowello/witty.git
cd witty
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### As a Python Library

```python
from src.pipeline.orchestrator import formalize

result = formalize("If it rains, the match is cancelled.")

print(result.legend)      # {'P1': 'it rains', 'P2': 'the match is cancelled'}
print(result.cnf)         # '¬P1 ∨ P2'
print(result.cnf_clauses) # [['¬P1', 'P2']]
```

### As a CLI Tool

```bash
# Create input file
echo "If it rains, the match is cancelled." > input.txt

# Run formalization
python -m src.cli --input input.txt --output result.json --reproducible

# View result
cat result.json
```

---

## Features

- **Atomic Claim Extraction**: Breaks complex statements into minimal propositions
- **Modal Logic Support**: Preserves necessity (□) and possibility (◇) operators
- **CNF Transformation**: Algorithmic conversion to Conjunctive Normal Form
- **Agent-Driven Enrichment**: Automatically fetches context when beneficial
- **Complete Provenance**: Full audit trail of all transformations
- **Dual Interface**: Use as library or CLI

---

## What Witty Produces

```json
{
  "legend": {"P1": "it rains", "P2": "the match is cancelled"},
  "cnf": "¬P1 ∨ P2",
  "cnf_clauses": [["¬P1", "P2"]],
  "atomic_claims": [...],
  "modal_metadata": {"P1": "NECESSARY"},
  "confidence": 0.95,
  "provenance": [...]
}
```

| Field | Description |
|-------|-------------|
| `legend` | Symbol → claim text mapping |
| `cnf` | CNF formula as string |
| `cnf_clauses` | CNF as nested lists |
| `atomic_claims` | Extracted claims with metadata |
| `modal_metadata` | Modal operators by symbol |
| `confidence` | Aggregate confidence (0-1) |
| `provenance` | Full transformation history |

---

## Examples

### Conditionals
```python
formalize("If P then Q.")
# CNF: ¬P ∨ Q
```

### Conjunctions
```python
formalize("A and B and C.")
# CNF: A ∧ B ∧ C
```

### Disjunctions
```python
formalize("Either X or Y.")
# CNF: X ∨ Y
```

### Modal Logic
```python
formalize("Squares are necessarily rectangles.")
# CNF: □P1
# modal_metadata: {'P1': 'NECESSARY'}

formalize("It is possible that it will rain.")
# CNF: ◇P1
# modal_metadata: {'P1': 'POSSIBLE'}
```

---

## CLI Reference

```bash
python -m src.cli --input INPUT --output OUTPUT [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--input FILE` | Input text file (required) |
| `--output FILE` | Output JSON file (required) |
| `--reproducible` | Deterministic mode (no external calls) |
| `--live` | Enable LLM processing (requires API key) |
| `--retrieval` | Force external context retrieval |
| `--no-retrieval` | Disable auto-enrichment |
| `--verbosity LEVEL` | `normal` or `debug` |
| `--model MODEL` | LLM model override |

### Examples

```bash
# Reproducible mode (deterministic)
python -m src.cli --input input.txt --output result.json --reproducible

# Live mode with LLM
python -m src.cli --input input.txt --output result.json --live

# Debug output
python -m src.cli --input input.txt --output result.json --verbosity debug
```

---

## Library API

### Basic Usage

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

# Default (agent orchestrator with auto-enrichment)
result = formalize("All mammals are warm-blooded.")

# With options
opts = FormalizeOptions(
    reproducible_mode=True,  # Deterministic
    no_retrieval=True,       # Disable enrichment
)
result = formalize("If X then Y.", opts)
```

### Available Options

```python
FormalizeOptions(
    reproducible_mode=False,  # Use deterministic pipeline
    no_retrieval=False,       # Disable auto-enrichment
    retrieval_enabled=False,  # Force enrichment
    live_mode=False,          # Enable live LLM
    llm_model=None,           # LLM model name
    privacy_mode="default",   # "default" or "strict"
    verbosity=0,              # Logging level
)
```

See [API Reference](docs/API.md) for complete documentation.

---

## Pipeline Architecture

```
Input Text
    ↓
┌─────────────────┐
│  Preprocessing  │ → Tokenization, segmentation
└─────────────────┘
    ↓
┌─────────────────┐
│    Concision    │ → Extract atomic claims
└─────────────────┘
    ↓
┌─────────────────┐
│   Enrichment    │ → (Optional) Fetch external context
└─────────────────┘
    ↓
┌─────────────────┐
│ Modal Detection │ → Identify necessity/possibility
└─────────────────┘
    ↓
┌─────────────────┐
│  Symbolization  │ → Assign P1, P2, ... symbols
└─────────────────┘
    ↓
┌─────────────────┐
│ CNF Transform   │ → Convert to Conjunctive Normal Form
└─────────────────┘
    ↓
FormalizationResult
```

---

## Agent-Driven Enrichment

Witty's agent automatically decides when to fetch external context (Wikipedia, DuckDuckGo).

**Triggers enrichment:**
- Domain quantifiers: "all mammals", "every country"
- Factual claims: dates, statistics, proper nouns
- Underspecified references: "the current president"

**Control behavior:**
```python
# Let agent decide (default)
result = formalize("All mammals are warm-blooded.")

# Force enrichment
opts = FormalizeOptions(retrieval_enabled=True)

# Disable enrichment
opts = FormalizeOptions(no_retrieval=True)
```

---

## Configuration

### Environment Variables

For live LLM mode, create a `.env` file in the project root:

```env
# Groq API (default provider - free tier available)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Alternative: OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# Alternative: Other OpenAI-compatible APIs
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.together.xyz/v1  # Together AI
# OPENAI_API_BASE=https://your-azure-endpoint.openai.azure.com/  # Azure OpenAI
```

### Getting API Keys

| Provider | Free Tier | Signup |
|----------|-----------|--------|
| **Groq** (default) | 100K tokens/day | [console.groq.com](https://console.groq.com) |
| **OpenAI** | $5 credit | [platform.openai.com](https://platform.openai.com) |
| **Together AI** | Free tier | [together.ai](https://together.ai) |
| **Azure OpenAI** | Pay-as-you-go | [azure.microsoft.com](https://azure.microsoft.com) |

### Using Alternative Providers

Witty uses OpenAI-compatible APIs, so most LLM providers work out of the box:

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

# Groq (default)
opts = FormalizeOptions(llm_model="llama-3.3-70b-versatile")

# OpenAI
opts = FormalizeOptions(llm_provider="openai", llm_model="gpt-4o-mini")

# Custom endpoint via environment variables
import os
os.environ["OPENAI_API_BASE"] = "https://api.together.xyz/v1"
os.environ["OPENAI_API_KEY"] = "your_key"
```

### Mode Selection

Witty has two operating modes:

| Mode | Description | When to Use |
|------|-------------|-------------|
| **Live** (default) | Uses LLM for intelligent extraction | Production, best results |
| **Reproducible** | Deterministic rule-based | Testing, CI/CD, consistent output |

```bash
# Live mode (default - requires API key)
python -m src.cli --input input.txt --output result.json

# Reproducible mode (no API key needed)
python -m src.cli --input input.txt --output result.json --reproducible
```

---

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -q

# Skip live integration tests
python -m pytest tests/ --ignore=tests/test_live_integration.py

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

Current status: **537 tests passing**

---

## Project Structure

```
witty/
├── src/
│   ├── pipeline/           # Core pipeline modules
│   │   ├── orchestrator.py     # Main entry point
│   │   ├── orchestrator_agent.py
│   │   ├── concision.py
│   │   ├── cnf.py
│   │   ├── symbolizer.py
│   │   └── ...
│   ├── adapters/           # LLM and retrieval adapters
│   ├── prompts/            # LLM prompt templates
│   ├── witty_types.py      # Type definitions
│   └── cli.py              # Command-line interface
├── tests/                  # Test suite
├── examples/               # Sample inputs
├── docs/                   # Documentation
│   ├── API.md              # API reference
│   └── QUICKSTART.md       # Getting started
└── schemas/                # JSON schemas
```

---

## Documentation

- **[Quickstart Guide](docs/QUICKSTART.md)** - Get started in 5 minutes
- **[API Reference](docs/API.md)** - Complete library documentation
- **[CLI Usage Guide](docs/public/project-wide/CLI_Usage_Guide.md)** - Detailed CLI options
- **[Examples](examples/)** - Sample input files

---

## License

GPL-3.0 License - see [LICENSE.txt](LICENSE.txt)

**Copyright © 2026 Victor Rowello**

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests (`pytest`)
4. Submit a pull request

---

## Acknowledgments

Built with:
- [Pydantic](https://pydantic.dev/) - Data validation
- [spaCy](https://spacy.io/) - NLP preprocessing
- [Groq](https://groq.com/) - LLM inference (live mode)
