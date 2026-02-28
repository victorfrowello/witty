# Witty API Reference

This document provides comprehensive API documentation for using Witty as a Python library.

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Functions](#core-functions)
- [Types Reference](#types-reference)
- [Pipeline Modules](#pipeline-modules)
- [Adapters](#adapters)
- [Configuration Options](#configuration-options)

---

## Installation

```bash
pip install -r requirements.txt
```

Or for development:
```bash
git clone https://github.com/victorfrowello/witty.git
cd witty
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

---

## Quick Start

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

# Simple usage - agent orchestrator with auto-enrichment
result = formalize("If it rains, the match is cancelled.")

print(result.legend)
# {'P1': 'it rains', 'P2': 'the match is cancelled'}

print(result.cnf)
# '¬P1 ∨ P2'

print(result.cnf_clauses)
# [['¬P1', 'P2']]
```

---

## Core Functions

### `formalize(input_text, options=None)`

Main entry point for formalization. Uses the agent orchestrator by default with automatic fallback to deterministic processing.

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

# Default behavior - agent decides on enrichment
result = formalize("All mammals are warm-blooded.")

# With custom options
options = FormalizeOptions(
    no_retrieval=True,        # Disable auto-enrichment
    reproducible_mode=True,   # Use deterministic pipeline
    verbosity=2
)
result = formalize("Squares are necessarily rectangles.", options)
```

**Parameters:**
- `input_text` (str): Natural language statement to formalize
- `options` (FormalizeOptions, optional): Configuration options

**Returns:** `FormalizationResult`

**Behavior:**
- In `reproducible_mode`: Uses classic deterministic orchestrator
- Otherwise: Uses agent orchestrator (tries first, falls back to classic on failure)

---

### `formalize_statement(input_text, options)`

Direct access to the classic deterministic orchestrator. Use this when you need guaranteed reproducible results.

```python
from src.pipeline.orchestrator import formalize_statement
from src.witty_types import FormalizeOptions

options = FormalizeOptions(reproducible_mode=True)
result = formalize_statement("If P then Q.", options)
```

---

### `formalize_with_agent(input_text, options=None, model=None)`

Direct access to the agent-based orchestrator with intelligent pipeline decisions.

```python
from src.pipeline.orchestrator_agent import formalize_with_agent

result = formalize_with_agent("The capital of France is Paris.")
```

---

## Types Reference

All types are available from `src.witty_types` or `src.witty.types`:

```python
from src.witty_types import (
    FormalizeOptions,
    FormalizationResult,
    AtomicClaim,
    ConcisionResult,
    CNFResult,
    CNFClause,
    ProvenanceRecord,
    ModuleResult,
)
```

### FormalizeOptions

Configuration options for pipeline execution.

```python
@dataclass
class FormalizeOptions:
    # Retrieval control
    no_retrieval: bool = False          # Opt-out of auto-enrichment
    retrieval_enabled: bool = False     # Force enrichment (legacy)
    retrieval_sources: List[str] = ["wikipedia", "duckduckgo"]
    retrieval_top_k: int = 3
    
    # Pipeline behavior
    reproducible_mode: bool = False     # Use deterministic pipeline
    privacy_mode: str = "default"       # "default" or "strict"
    verbosity: int = 0
    
    # LLM settings (live mode)
    live_mode: bool = False
    llm_model: str = None               # e.g., "llama-3.3-70b-versatile"
    llm_provider: str = None
    
    # Advanced
    top_k_symbolizations: int = 1
    quantifier_reduction_detail: bool = False
    allow_modal_advanced_cnf: bool = False
```

### FormalizationResult

Complete output of the formalization pipeline.

```python
@dataclass
class FormalizationResult:
    request_id: str                     # Unique request identifier
    original_text: str                  # Input text
    canonical_text: str                 # Normalized text
    
    # Core outputs
    atomic_claims: List[AtomicClaim]    # Extracted claims with symbols
    legend: Dict[str, str]              # Symbol -> claim text mapping
    cnf: str                            # CNF formula string
    cnf_clauses: List[List[str]]        # CNF as nested lists
    
    # Logical forms
    logical_form_candidates: List[Dict]
    chosen_logical_form: Dict
    
    # Metadata
    modal_metadata: Dict[str, Any]      # Modal operators by symbol
    confidence: float                   # Aggregate confidence (0-1)
    warnings: List[str]
    provenance: List[ProvenanceRecord]  # Full transformation history
    enrichment_sources: List[str]
```

### AtomicClaim

Individual atomic proposition extracted from input.

```python
@dataclass
class AtomicClaim:
    text: str                           # Claim text
    symbol: str                         # Assigned symbol (P1, P2, ...)
    origin_spans: List[Tuple[int, int]] # Character spans in original
    modal_context: str                  # "NECESSARY", "POSSIBLE", etc.
    provenance: ProvenanceRecord
```

---

## Pipeline Modules

For advanced usage, you can access individual pipeline stages:

### Preprocessing

```python
from src.pipeline.preprocessing import preprocess

result = preprocess("If it rains, then the match is cancelled.")
print(result.normalized_text)
print(result.clauses)
print(result.tokens)
```

### Concision

```python
from src.pipeline.concision import deterministic_concision, llm_concision

# Deterministic (rule-based)
result = deterministic_concision(prep_result, ctx)

# LLM-assisted (requires adapter)
result = llm_concision(prep_result, ctx, adapter=llm_adapter)
```

### CNF Transformation

```python
from src.pipeline.cnf import cnf_transform

cnf_result = cnf_transform(symbolizer_result, ctx)
print(cnf_result.cnf_string)      # "¬P1 ∨ P2"
print(cnf_result.clauses)         # [CNFClause(...)]
print(cnf_result.modal_atoms)     # {"P1": "NECESSARY", ...}
```

### Symbolization

```python
from src.pipeline.symbolizer import deterministic_symbolizer

result = deterministic_symbolizer(concision_result, ctx)
print(result.legend)              # {"P1": "it rains", ...}
print(result.atomic_claims)
```

---

## Adapters

### LLM Adapters

```python
from src.adapters.groq_adapter import GroqAdapter
from src.adapters.mock import MockLLMAdapter

# Live LLM (requires GROQ_API_KEY)
adapter = GroqAdapter(model="llama-3.3-70b-versatile")
response = adapter.complete(prompt, ctx)

# Mock for testing
mock = MockLLMAdapter()
```

### Retrieval Adapters

```python
from src.adapters.wikipedia import WikipediaAdapter
from src.adapters.duckduckgo import DuckDuckGoAdapter
from src.adapters.composite import CompositeRetrievalAdapter

# Individual adapters
wiki = WikipediaAdapter()
ddg = DuckDuckGoAdapter()

# Composite (searches both)
composite = CompositeRetrievalAdapter([wiki, ddg])
response = composite.retrieve("capital of France", top_k=3, ctx=ctx)
```

---

## Configuration Options

### Environment Variables

Create a `.env` file in your project root:

```env
# Groq API (default provider - free tier: 100K tokens/day)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Alternative: OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# Alternative: Any OpenAI-compatible API (Together AI, Azure, etc.)
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.together.xyz/v1

# Pipeline defaults (optional)
LLM_MODEL=llama-3.3-70b-versatile
REPRODUCIBLE_MODE=false
PRIVACY_MODE=default
```

### Supported API Providers

Witty uses the OpenAI client library, which means any OpenAI-compatible API works:

| Provider | Environment Variables | Model Example |
|----------|----------------------|---------------|
| **Groq** (default) | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` |
| **Together AI** | `OPENAI_API_KEY`, `OPENAI_API_BASE=https://api.together.xyz/v1` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| **Azure OpenAI** | `OPENAI_API_KEY`, `OPENAI_API_BASE=https://your-endpoint.openai.azure.com/` | `gpt-4` |
| **Ollama** | `OPENAI_API_BASE=http://localhost:11434/v1` | `llama3.2` |

### Getting API Keys

1. **Groq** (recommended - free tier): [console.groq.com](https://console.groq.com)
2. **OpenAI**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. **Together AI**: [api.together.ai](https://api.together.ai)

### Programmatic Configuration

```python
from src.witty_types import FormalizeOptions
from src.pipeline.orchestrator import formalize

# Live mode (default - uses LLM, best results)
opts = FormalizeOptions()

# Reproducible mode (deterministic, no external calls)
opts = FormalizeOptions(reproducible_mode=True)

# Specify LLM model
opts = FormalizeOptions(llm_model="llama-3.3-70b-versatile")

# Disable auto-enrichment
opts = FormalizeOptions(no_retrieval=True)

# Force enrichment
opts = FormalizeOptions(retrieval_enabled=True)

# Privacy-conscious mode
opts = FormalizeOptions(privacy_mode="strict")
```

### Mode Comparison

| Mode | API Key Required | LLM Used | Best For |
|------|-----------------|----------|----------|
| **Live** (default) | Yes | Yes | Production, best accuracy |
| **Reproducible** | No | No | Testing, CI/CD, consistent output |

---

## Modal Logic Support

Witty preserves modal operators (necessity □, possibility ◇) through the pipeline:

```python
result = formalize("Squares are necessarily rectangles. Rectangles are possibly squares.")

print(result.cnf)
# '□P1 ∧ ◇P2'

print(result.modal_metadata)
# {'P1': 'NECESSARY', 'P2': 'POSSIBLE'}

# Negated modals are also supported
result = formalize("It is not possible that triangles have four sides.")
# CNF: '¬◇P1' (it's not possible that...)
```

---

## Error Handling

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

try:
    result = formalize("Some input text")
    
    if result.warnings:
        print(f"Warnings: {result.warnings}")
    
    if result.confidence < 0.7:
        print("Low confidence result - consider human review")
        
except Exception as e:
    print(f"Pipeline error: {e}")
```

---

## Examples

### Basic Conditional

```python
result = formalize("If it rains, the match is cancelled.")

assert result.legend == {'P1': 'it rains', 'P2': 'the match is cancelled'}
assert result.cnf == '¬P1 ∨ P2'
```

### Conjunction

```python
result = formalize("Alice is tall and Bob is short.")

assert len(result.atomic_claims) == 2
assert result.cnf == 'P1 ∧ P2'
```

### Disjunction

```python
result = formalize("Either it rains or the sun shines.")

assert result.cnf == 'P1 ∨ P2'
```

### Complex Modal

```python
result = formalize("If necessarily both X and Y, then not possibly Z.")

# CNF preserves modal structure
assert '□' in result.cnf or '◇' in result.cnf
```

### With Enrichment

```python
opts = FormalizeOptions(retrieval_enabled=True)
result = formalize("All mammals are warm-blooded.", opts)

# Check if enrichment was used
if result.enrichment_sources:
    print(f"Sources: {result.enrichment_sources}")
```

---

## See Also

- [CLI Usage Guide](docs/public/project-wide/CLI_Usage_Guide.md)
- [Quickstart Guide](docs/QUICKSTART.md)
- [Design Specification](docs/public/project-wide/DesignSpec_public.md)
