# Witty CLI Usage Guide

Complete reference for the Witty command-line interface.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Basic Usage](#basic-usage)
- [CLI Arguments Reference](#cli-arguments-reference)
- [Operating Modes](#operating-modes)
- [Enrichment Control](#enrichment-control)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before using the Witty CLI, ensure you have:

1. **Python 3.9 or higher** installed
2. **Virtual environment** created and activated (recommended)
3. **Dependencies installed** via `pip install -r requirements.txt`

To verify your setup:

```powershell
python --version
python -m src.cli --help
```

---

## Basic Usage

The general command structure is:

```powershell
python -m src.cli --input <INPUT_FILE> --output <OUTPUT_FILE> [OPTIONS]
```

**Minimal example**:

```powershell
python -m src.cli --input examples/simple_conditional.txt --output result.json
```

By default, Witty uses the **agent orchestrator** which intelligently routes through pipeline stages and auto-decides on enrichment.

---

## CLI Arguments Reference

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--input INPUT` | Path to input text file (UTF-8) |
| `--output OUTPUT` | Path for output JSON file |

### Optional Arguments

| Argument | Description |
|----------|-------------|
| `--config CONFIG` | Path to YAML configuration file |
| `--env ENV` | Path to `.env` file (default: `.env`) |
| `--verbosity {normal,debug}` | Logging level (default: `normal`) |
| `--reproducible` | Enable deterministic mode (no external calls) |
| `--live` | Enable live LLM mode (requires API key) |
| `--model MODEL` | LLM model override (e.g., `llama-3.3-70b-versatile`) |
| `--retrieval` | Force external context retrieval |
| `--no-retrieval` | Disable auto-enrichment completely |

---

## Operating Modes

### Default Mode (Agent Orchestrator)

```powershell
python -m src.cli --input input.txt --output result.json
```

- Uses intelligent agent orchestrator
- Agent auto-decides on enrichment based on content
- Falls back to deterministic processing if agent fails

### Reproducible Mode

```powershell
python -m src.cli --input input.txt --output result.json --reproducible
```

- Fully deterministic processing
- No external API calls
- Same input always produces identical output
- Ideal for CI/CD and testing

### Live Mode (LLM-Assisted)

```powershell
python -m src.cli --input input.txt --output result.json --live
```

- Uses real LLM (Groq Llama 3.3 70B by default)
- Requires `GROQ_API_KEY` in `.env`
- Higher quality claim extraction
- Agent still decides on enrichment

```powershell
# With custom model
python -m src.cli --input input.txt --output result.json --live --model llama-3.3-70b-versatile
```

---

## Enrichment Control

The agent automatically decides when to fetch external context (Wikipedia, DuckDuckGo) based on content analysis.

### Auto-Enrichment (Default)

```powershell
python -m src.cli --input input.txt --output result.json
```

**Triggers enrichment when detecting:**
- Domain quantifiers: "all mammals", "every country"
- Factual claims: dates, statistics, proper nouns
- Underspecified references: "the current president"

### Force Enrichment

```powershell
python -m src.cli --input input.txt --output result.json --retrieval
```

Always fetches external context, regardless of content.

### Disable Enrichment

```powershell
python -m src.cli --input input.txt --output result.json --no-retrieval
```

Agent will **never** fetch external context, even if it thinks it would help.

---

## Configuration

### Using .env Files

Create a `.env` file in your project root:

```env
# LLM Configuration (for --live mode)
GROQ_API_KEY=your_api_key_here
LLM_MODEL=llama-3.3-70b-versatile

# Pipeline defaults
REPRODUCIBLE_MODE=false
PRIVACY_MODE=default
```

### Using YAML Configuration

Create a configuration file (e.g., `config.yaml`):

```yaml
reproducible_mode: true
verbosity: debug
privacy_mode: default
no_retrieval: false
```

Run with:

```powershell
python -m src.cli --input input.txt --output result.json --config config.yaml
```

### Configuration Priority

1. Command-line arguments (highest)
2. YAML config file
3. .env file
4. Default values (lowest)

---

## Output Format

The CLI writes a JSON file conforming to the `FormalizationResult` schema.

### Key Fields

| Field | Description |
|-------|-------------|
| `request_id` | Unique identifier for this request |
| `original_text` | Exact input text as provided |
| `canonical_text` | Normalized/cleaned version |
| `atomic_claims` | Extracted minimal claims with symbols |
| `legend` | Symbol → claim text mapping |
| `cnf` | CNF formula string (e.g., `¬P1 ∨ P2`) |
| `cnf_clauses` | CNF as nested lists |
| `modal_metadata` | Modal operators by symbol |
| `confidence` | Overall confidence (0.0 to 1.0) |
| `warnings` | Non-fatal issues encountered |
| `provenance` | Complete transformation history |

### Example Output

```json
{
  "request_id": "req_20260228120000",
  "original_text": "If it rains, the match is cancelled.",
  "canonical_text": "If it rains, the match is cancelled.",
  "atomic_claims": [
    {
      "text": "it rains",
      "symbol": "P1",
      "origin_spans": [[3, 11]],
      "modal_context": null
    },
    {
      "text": "the match is cancelled",
      "symbol": "P2",
      "origin_spans": [[13, 35]],
      "modal_context": null
    }
  ],
  "legend": {
    "P1": "it rains",
    "P2": "the match is cancelled"
  },
  "cnf": "¬P1 ∨ P2",
  "cnf_clauses": [["¬P1", "P2"]],
  "modal_metadata": {},
  "confidence": 0.95,
  "warnings": []
}
```

### Modal Logic Output

For statements with modal operators:

```json
{
  "legend": {"P1": "squares are rectangles"},
  "cnf": "□P1",
  "modal_metadata": {"P1": "NECESSARY"}
}
```

Supported modal operators:
- `□` (NECESSARY) - "necessarily", "must be"
- `◇` (POSSIBLE) - "possibly", "might be"
- `¬□` (NOT_NECESSARY) - "not necessarily"
- `¬◇` (NOT_POSSIBLE) - "impossible", "cannot"

---

## Examples

### Example 1: Simple Conditional

```powershell
echo "If it rains, the match is cancelled." > input.txt
python -m src.cli --input input.txt --output result.json --reproducible
```

**Result**: CNF `¬P1 ∨ P2`

---

### Example 2: Modal Statement

```powershell
echo "Squares are necessarily rectangles." > input.txt
python -m src.cli --input input.txt --output result.json --reproducible
```

**Result**: CNF `□P1`, modal_metadata `{"P1": "NECESSARY"}`

---

### Example 3: Live Mode with Debug

```powershell
python -m src.cli `
  --input examples/causal_chain.txt `
  --output result.json `
  --live `
  --verbosity debug
```

---

### Example 4: Force Enrichment

```powershell
echo "All mammals are warm-blooded." > input.txt
python -m src.cli --input input.txt --output result.json --live --retrieval
```

Fetches context from Wikipedia/DuckDuckGo to enrich the formalization.

---

### Example 5: Batch Processing

```powershell
$examples = Get-ChildItem -Path examples -Filter *.txt

foreach ($file in $examples) {
    $outputName = "outputs/$($file.BaseName).json"
    Write-Host "Processing $($file.Name)..."
    
    python -m src.cli `
      --input $file.FullName `
      --output $outputName `
      --reproducible
}
```

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Run from the project root using `python -m src.cli`

---

**Issue**: `FileNotFoundError: Input file not found`

**Solution**: Check the input file path. Use absolute paths if needed:
```powershell
python -m src.cli --input C:\full\path\to\input.txt --output result.json
```

---

**Issue**: Rate limit errors in live mode

**Solution**: Groq free tier has 100k tokens/day. Use `--reproducible` for unlimited deterministic processing, or wait for rate limit reset.

---

**Issue**: Want to see what's happening internally

**Solution**: Use `--verbosity debug`:
```powershell
python -m src.cli --input input.txt --output result.json --verbosity debug
```

---

**Issue**: Output varies between runs

**Solution**: Use `--reproducible` for deterministic behavior:
```powershell
python -m src.cli --input input.txt --output result.json --reproducible
```

---

**Issue**: Agent using enrichment when I don't want it

**Solution**: Use `--no-retrieval` to disable auto-enrichment:
```powershell
python -m src.cli --input input.txt --output result.json --no-retrieval
```

---

### Getting Help

```powershell
# View all options
python -m src.cli --help

# Check installation
python --version
pip list | Select-String "pydantic|spacy"

# Run tests
python -m pytest tests/ -q
```

---

## Programmatic Usage

For library usage instead of CLI, see [API Reference](../../API.md):

```python
from src.pipeline.orchestrator import formalize
from src.witty_types import FormalizeOptions

result = formalize("If it rains, the match is cancelled.")
print(result.cnf)  # ¬P1 ∨ P2
```

---

## See Also

- [Quickstart Guide](../../QUICKSTART.md) - Get started in 5 minutes
- [API Reference](../../API.md) - Complete library documentation
- [Examples](../../../examples/) - Sample input files

---

*Last updated: February 28, 2026 - v1.0*
