# Witty CLI Usage Guide

This guide provides detailed instructions for using the Witty command-line interface during Sprint 1 development.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Basic Usage](#basic-usage)
- [CLI Arguments Reference](#cli-arguments-reference)
- [Configuration](#configuration)
- [Reproducible Mode](#reproducible-mode)
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

---

## CLI Arguments Reference

### Required Arguments

- `--input INPUT`
  - Path to the input text file containing natural language to formalize
  - Must be a readable text file (UTF-8 encoding recommended)
  - Example: `--input examples/simple_conditional.txt`

- `--output OUTPUT`
  - Path where the FormalizationResult JSON will be written
  - Will create/overwrite the file
  - Example: `--output results/output.json`

### Optional Arguments

- `--config CONFIG`
  - Path to a YAML configuration file
  - Allows setting multiple options in one file
  - Takes precedence over `.env` settings
  - Example: `--config config/production.yaml`

- `--env ENV`
  - Path to `.env` file for environment variables
  - Default: `.env` (in current directory)
  - Example: `--env .env.development`

- `--verbosity {normal|debug}`
  - Logging verbosity level
  - `normal`: Standard informational messages (default)
  - `debug`: Detailed debug output including module internals
  - Example: `--verbosity debug`

- `--reproducible`
  - Flag to enable reproducible/deterministic mode
  - Forces use of Mock adapters instead of live LLMs
  - Essential for CI/CD and testing
  - No value needed (presence = enabled)
  - Example: `--reproducible`

---

## Configuration

### Using .env Files

Create a `.env` file in your project root:

```env
REPRODUCIBLE_MODE=true
VERBOSITY=debug
LLM_PROVIDER=mock
```

Then run:

```powershell
python -m src.cli --input examples/simple_conditional.txt --output result.json --env .env
```

### Using YAML Configuration

Create a configuration file (e.g., `config.yaml`):

```yaml
retrieval_enabled: false
top_k_symbolizations: 3
llm_provider: mock
verbosity: debug
reproducible_mode: true
privacy_mode: default
```

Run with:

```powershell
python -m src.cli --input examples/simple_conditional.txt --output result.json --config config.yaml
```

### Configuration Priority

When multiple configuration sources are present, priority is:

1. Command-line arguments (highest)
2. YAML config file
3. .env file
4. Default values (lowest)

---

## Reproducible Mode

**Reproducible mode** ensures deterministic behavior across runs, critical for:
- Continuous Integration (CI)
- Automated testing
- Demos and presentations
- Debugging

When enabled (`--reproducible` flag or `reproducible_mode: true` in config):
- All LLM calls use Mock adapter with fixed responses
- No network calls are made
- Same input always produces identical output
- No API keys required

**Example**:

```powershell
python -m src.cli `
  --input examples/simple_conditional.txt `
  --output result.json `
  --reproducible `
  --verbosity debug
```

---

## Output Format

The CLI writes a JSON file conforming to the `FormalizationResult` schema.

### Key Fields

- **request_id**: Unique identifier for this formalization request
- **original_text**: Exact input text as provided
- **canonical_text**: Normalized/cleaned version of input
- **atomic_claims**: Array of extracted minimal claims
  - Each claim has: `text`, `symbol`, `origin_spans`, `modal_context`, `provenance`
- **legend**: Dictionary mapping symbols (P1, P2...) to claim text
- **logical_form_candidates**: Array of proposed logical forms (AST + notation)
- **chosen_logical_form**: The selected logical form from candidates
- **cnf**: Conjunctive Normal Form string representation
- **cnf_clauses**: CNF broken into individual clauses (array of arrays)
- **modal_metadata**: Information about modal operators detected
- **warnings**: Array of warning messages (non-fatal issues)
- **confidence**: Overall confidence score (0.0 to 1.0)
- **provenance**: Complete tracking of all transformations

### Example Output

```json
{
  "request_id": "req_20251104_001",
  "original_text": "If Alice owns a red car, then Alice prefers driving.",
  "canonical_text": "If Alice owns a red car, then Alice prefers driving.",
  "atomic_claims": [
    {
      "text": "Alice owns a red car",
      "symbol": "P1",
      "origin_spans": [[3, 24]],
      "modal_context": null
    },
    {
      "text": "Alice prefers driving",
      "symbol": "P2",
      "origin_spans": [[31, 52]],
      "modal_context": null
    }
  ],
  "legend": {
    "P1": "Alice owns a red car",
    "P2": "Alice prefers driving"
  },
  "chosen_logical_form": {
    "ast": {
      "type": "IMPLIES",
      "left": {"type": "ATOM", "symbol": "P1"},
      "right": {"type": "ATOM", "symbol": "P2"}
    },
    "notation": "P1 → P2",
    "confidence": 0.95
  },
  "cnf": "¬P1 ∨ P2",
  "cnf_clauses": [["¬P1", "P2"]],
  "confidence": 0.95,
  "warnings": []
}
```

---

## Examples

### Example 1: Simple Conditional

**Input** (`examples/simple_conditional.txt`):
```
If Alice owns a red car, then Alice prefers driving.
```

**Command**:
```powershell
python -m src.cli --input examples/simple_conditional.txt --output simple_out.json --reproducible
```

**Expected**: Two atomic claims with implication relationship, CNF: `¬P1 ∨ P2`

---

### Example 2: Modal Statement with Debug Logging

**Input** (`examples/modal_necessity.txt`):
```
It is necessary that all students attend the safety briefing before participating in the lab experiment.
```

**Command**:
```powershell
python -m src.cli `
  --input examples/modal_necessity.txt `
  --output modal_out.json `
  --reproducible `
  --verbosity debug
```

**Expected**: Claims with modal metadata, detailed logging in console

---

### Example 3: Batch Processing Multiple Files

Create a simple script (`process_all.ps1`):

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

Write-Host "All files processed!"
```

Run:
```powershell
.\process_all.ps1
```

---

### Example 4: Using Custom Configuration

**config.yaml**:
```yaml
reproducible_mode: true
verbosity: debug
top_k_symbolizations: 5
privacy_mode: strict
```

**Command**:
```powershell
python -m src.cli `
  --input examples/causal_chain.txt `
  --output causal_out.json `
  --config config.yaml
```

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Ensure you're running from the project root and using `python -m src.cli` (not `python src/cli.py`)

---

**Issue**: `FileNotFoundError: Input file not found`

**Solution**: Check the input file path. Use absolute paths or paths relative to the current directory:
```powershell
python -m src.cli --input .\examples\simple_conditional.txt --output result.json
```

---

**Issue**: Output file not created

**Solution**: 
- Check that you have write permissions in the output directory
- Create the output directory if it doesn't exist:
  ```powershell
  New-Item -ItemType Directory -Path outputs -Force
  python -m src.cli --input examples/simple_conditional.txt --output outputs/result.json
  ```

---

**Issue**: Want to see what's happening internally

**Solution**: Use `--verbosity debug` to see detailed pipeline execution:
```powershell
python -m src.cli --input examples/simple_conditional.txt --output result.json --verbosity debug
```

---

**Issue**: Output varies between runs

**Solution**: Use `--reproducible` flag to ensure deterministic behavior:
```powershell
python -m src.cli --input examples/simple_conditional.txt --output result.json --reproducible
```

---

### Getting Help

View all available options:
```powershell
python -m src.cli --help
```

Check Python and dependencies:
```powershell
python --version
pip list | Select-String "pydantic|pytest"
```

Run tests to verify installation:
```powershell
pytest tests/ -v
```

---

## Advanced Usage

### Programmatic API

While the CLI is the primary interface for Sprint 1, you can also call the pipeline directly from Python:

```python
from src.pipeline.orchestrator import formalize_statement
from src.witty.types import FormalizeOptions

# Configure options
options = FormalizeOptions(
    reproducible_mode=True,
    verbosity="debug"
)

# Run formalization
result = formalize_statement(
    input_text="If Alice owns a red car, then Alice prefers driving.",
    options=options
)

# Access results
print(f"Confidence: {result.confidence}")
print(f"CNF: {result.cnf}")
for claim in result.atomic_claims:
    print(f"{claim.symbol}: {claim.text}")
```

### Integration with Testing

Use the CLI in integration tests:

```python
import subprocess
import json

def test_cli_simple_conditional():
    result = subprocess.run([
        "python", "-m", "src.cli",
        "--input", "examples/simple_conditional.txt",
        "--output", "test_output.json",
        "--reproducible"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    
    with open("test_output.json") as f:
        output = json.load(f)
    
    assert output["confidence"] > 0.8
    assert len(output["atomic_claims"]) == 2
```

---

## Next Steps

- Review the [Design Specification](DesignSpec_forCopilot_v4.md) for detailed pipeline architecture
- Explore [Sprint 1 Plan](sprint1_plan.md) for development roadmap
- Check [examples/README.md](../examples/README.md) for more input examples
- See [tests/fixtures/README.json](../tests/fixtures/README.json) for expected output formats

---

*Last updated: November 4, 2025 - Sprint 1*
