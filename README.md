# Witty v0.1.0 — Epistemic Formalization Engine

Witty converts plain‑English declarative statements and long‑form arguments into machine‑readable formalizations that expose the minimal atomic claims and the inferences required for the input to be true. This README is a concise, high-level primer on what the system produces, the data pipeline, where LLMs are used versus deterministic code, and how provenance and reproducibility are handled.

Witty is **NOT** a fact checking engine. It formalizes the logical structure and minimal claims implied by an input under the assumption the input is true: it does not verify, validate, or assert the factual correctness of those claims.

---

## What Witty produces
- canonical_text (cleaned canonicalization of the input)  
- atomic_claims[] (each with a ProvenanceRecord and reduction rationale)  
- legend mapping symbols (P1, P2, …) → claims  
- logical_form_candidates[] (typed JSON AST + human notation) and a chosen logical form  
- propositional CNF (modal wrappers preserved at atom level)  
- validation report, warnings, aggregated confidence, and a chronological provenance event_log

---

## How to call it
```py
formalize_statement(input_text: str, options: FormalizeOptions) -> FormalizationResult
```
Every pipeline stage returns a ModuleResult:
- payload — typed (pydantic) output  
- provenance_record — module provenance entry  
- confidence — float 0..1  
- warnings — list[str]

---

## Data pipeline (stages, outputs, LLM vs deterministic)

1. Ingest — Deterministic  
   - Normalize text, set request metadata.  
   - Output: normalized_text + initial provenance.

2. Preprocessing — Deterministic  
   - Sentence/clause segmentation, tokenization, token annotations (negation, modals, quantifiers, temporals), origin_spans mapping.  
   - Output: PreprocessingResult.

3. Concision — LLM‑driven by default; Deterministic fallback  
   - Default: call LLM (concise_v1) to produce strict JSON: canonical_text, atomic_candidates (with origin_spans), confidence, explanations.  
   - Validate with pydantic and semantic checks (negation preserved, quantifier scope, origin_spans coverage).  
   - On parse failure or confidence < threshold: retry once, then run deterministic_concision() and flag human_review.  
   - Output: ConcisionResult + provenance recording attempts and path taken.

4. Context Enrichment (optional) — Deterministic retrieval; summarization LLM‑assisted  
   - RetrievalAdapter fetches sources deterministically; summaries may be LLM‑assisted and follow validate→retry→fallback rules.  
   - Output: enrichment_sources[] + provenance (snippets redacted under strict privacy).

5. Modal Detection & Framing — Deterministic rule-first; LLM confirmation optional  
   - Run lexical rules; when uncertain or configured, call modal_detect_v1 (LLM) for confirmation and recommended frame.  
   - Output: modal_metadata + provenance.

6. World Construction — Deterministic  
   - Assume canonical_text true; expand presuppositions; deterministically reduce quantifiers to propositional constants (readable IDs like E{n}_... / R{n}_...).  
   - Output: ordered atomic_claims[] each with ProvenanceRecord.

7. Symbolization — Deterministic core; LLM suggestions allowed  
   - Deterministic: assign stable symbols (P1, P2, …) and build legend.  
   - Optional: request LLM AST suggestions via symbolize_v1; validate suggestions and fall back to deterministic assignment.  
   - Output: legend, logical_form_candidates + provenance.

8. CNF Transformation — Deterministic  
   - Algorithmic steps: remove IMPLIES/IFF → NNF → distribute OR over AND; treat modal-wrapped atoms as atomic tokens by default.  
   - Output: cnf string, cnf_clauses[], clause→legend mapping + provenance.

9. Validation & Sanity Checks — Deterministic  
   - Ensure symbol coverage, provenance coverage for each atomic claim, detect trivial contradictions/tautologies, aggregate confidences.  
   - Output: validation_report, warnings + provenance.

10. Output Assembly — Deterministic  
   - Merge module provenance chronologically, attach config/thresholds used, emit final FormalizationResult JSON.

---

## Provenance, privacy, and determinism

- Every module emits a ProvenanceRecord: deterministic id, created_at, module_id/version, adapter_id/prompt_template_id (if LLM used), origin_spans, enrichment_sources (redactable), confidence, ambiguity_flags, reduction_rationale, and event_log of decisions.  
- Every LLM call records adapter_provenance: {adapter_id, version, prompt_template_id, request_id, raw_output_summary} (raw content redacted under strict privacy).  
- Deterministic id formula: SHA256(normalized_input + module_id + module_version + deterministic_salt) truncated with a readable suffix.  
- `privacy_mode == "strict"` redacts excerpts and URLs while keeping structured IDs.  
- `REPRODUCIBLE_MODE=true` forces Mock adapters and disables external retrieval for deterministic CI.

---

## LLM usage policy (applies to all LLM‑driven stages)

- Prompts must request strict JSON matching an embedded schema; adapters should attempt to parse and expose parsed_json.  
- Pattern for each LLM call: Validate → Retry (1 retry default) → Deterministic fallback. Record every attempt and decision in provenance.event_log.  
- Default runtime knobs (configurable): llm_conf_threshold = 0.70; max_retries_per_tool = 1; origin_spans_coverage_threshold = 0.80.

---

##  Project Structure
```
witty/
├── src/                      # Core source code
│   ├── adapters/             # LLMAdapter implementations and registry
│   │   ├── base.py           # Abstract LLMAdapter interface
│   │   ├── openai.py         # OpenAIAdapter (uses OPENAI_API_KEY)
│   │   ├── mock.py           # MockLLMAdapter (for testing)
│   │   ├── local.py          # LocalLLMAdapter (e.g., subprocess or localhost)
│   │   └── registry.py       # get_llm_adapter() factory
│   │
│   ├── pipeline/             # Core formalization pipeline modules
│   │   ├── orchestrator.py   # formalize_statement() entry point
│   │   ├── preprocessing.py  # Tokenization, segmentation, annotation
│   │   ├── concision.py      # Concision module (LLM + rules)
│   │   ├── modality.py       # Modal detection and framing
│   │   ├── world.py          # World construction logic
│   │   ├── symbolizer.py     # Symbol assignment and legend generation
│   │   ├── cnf.py            # CNF transformer (NNF, distribution)
│   │   ├── validation.py     # Sanity checks and confidence scoring
│   │   └── provenance.py     # Provenance tracking utilities
│   │
│   ├── prompts/              # Prompt templates (versioned)
│   │   ├── concise_v1.txt
│   │   ├── modal_detect_v1.txt
│   │   ├── world_construct_v1.txt
│   │   └── symbolize_v1.txt
│   │
│   ├── cli.py                # Command-line interface
│   ├── config.py             # Global config loader (e.g., env vars, adapter settings)
│   ├── types.py              # Shared dataclasses and schema bindings
│   ├── utils.py              # General-purpose utilities
│   └── test_runner.py        # Batch runner for examples and integration tests
│
├── schemas/                  # JSON schemas for inputs and outputs
│   ├── FormalizationResult.json
│   └── FormalizeOptions.json
│
├── examples/                 # Sample inputs and outputs
│   ├── input_statements.txt
│   └── formalized_outputs/
│
├── tests/                    # Unit and integration tests
│   ├── test_concision.py
│   ├── test_modality.py
│   ├── test_symbolizer.py
│   └── ...
│
├── .env                      # Environment variables (e.g., API keys)
├── README.md                 # Project overview and usage
└── LICENSE                   # License file
```
---

## Sprint 1 Quickstart (Deterministic Mock Mode)

### Installation

1. **Clone the repository**:
```powershell
git clone <repository-url>
cd witty-1
```

2. **Create and activate a virtual environment** (recommended):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. **Install dependencies**:
```powershell
pip install -r requirements.txt
```

### Basic Usage

The CLI currently operates in **deterministic mock mode** for Sprint 1, using pre-defined responses without requiring any API keys or network calls.

**Run a simple example**:
```powershell
python -m src.cli --input examples/simple_conditional.txt --output result.json --reproducible
```

**View the output**:
```powershell
cat result.json
```

### CLI Options

```
--input INPUT          Input text file (required)
--output OUTPUT        Output JSON file (required)
--config CONFIG        Optional YAML configuration file
--env ENV              Path to .env file (default: .env)
--verbosity LEVEL      Logging level: 'normal' or 'debug'
--reproducible         Enable reproducible mode (deterministic behavior)
```

### Example Workflow

```powershell
# Process a simple conditional statement
python -m src.cli `
  --input examples/simple_conditional.txt `
  --output outputs/simple.json `
  --reproducible `
  --verbosity debug

# Process a modal logic example
python -m src.cli `
  --input examples/modal_necessity.txt `
  --output outputs/modal.json `
  --reproducible
```

### What You Get

The output `FormalizationResult` JSON contains:
- **canonical_text**: Cleaned/normalized input
- **atomic_claims**: Extracted minimal claims with symbols (P1, P2, ...)
- **legend**: Mapping from symbols to natural language
- **logical_form_candidates**: Proposed logical representations
- **chosen_logical_form**: Selected logical form
- **cnf**: Conjunctive Normal Form representation
- **cnf_clauses**: CNF broken into clauses
- **provenance**: Complete tracking of all transformations
- **confidence**: Overall confidence score
- **warnings**: Any issues encountered

### Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/test_orchestrator.py -v
```

### Current Limitations (Sprint 1)

- **No live LLM integration**: All responses are deterministic mock data
- **Limited pipeline stages**: Core stages implemented, some advanced features pending
- **English only**: Multi-language support planned for future sprints

### Example Output Structure

```json
{
  "request_id": "req_abc123",
  "original_text": "If Alice owns a red car, then Alice prefers driving.",
  "canonical_text": "If Alice owns a red car, then Alice prefers driving.",
  "atomic_claims": [
    {
      "text": "Alice owns a red car",
      "symbol": "P1",
      "origin_spans": [[3, 24]]
    },
    {
      "text": "Alice prefers driving",
      "symbol": "P2",
      "origin_spans": [[31, 52]]
    }
  ],
  "legend": {
    "P1": "Alice owns a red car",
    "P2": "Alice prefers driving"
  },
  "cnf": "¬P1 ∨ P2",
  "confidence": 0.95
}
```

##  Status

**Sprint 1 Complete**: Core type system, mock adapter, and deterministic pipeline operational.

This is an early-stage prototype currently under active development. Contributions, feedback, and questions are welcome.

---