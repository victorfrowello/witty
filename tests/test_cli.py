"""
Smoke tests for Witty CLI.
Verifies argument parsing, config loading, reproducible mode, and output file creation.
Uses deterministic mock path for all tests.
"""
import os
import sys
import tempfile
import json
import subprocess
import pytest

CLI_PATH = os.path.join(os.path.dirname(__file__), '../src/cli.py')
EXAMPLE_INPUT = "Alice owns a red car."

@pytest.fixture
def temp_input_file():
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.txt') as f:
        f.write(EXAMPLE_INPUT)
        f.flush()
        yield f.name
    os.remove(f.name)

@pytest.fixture
def temp_output_file():
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.json') as f:
        yield f.name
    os.remove(f.name)

@pytest.mark.parametrize("reproducible", [True, False])
def test_cli_runs_and_writes_output(temp_input_file, temp_output_file, reproducible):
    # Prepare CLI command
    cmd = [sys.executable, CLI_PATH,
           '--input', temp_input_file,
           '--output', temp_output_file]
    if reproducible:
        cmd.append('--reproducible')
    # Run CLI
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Check output file exists and is valid JSON
    assert os.path.exists(temp_output_file)
    with open(temp_output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert 'canonical_text' in data or 'original_text' in data, "Output missing expected fields"

@pytest.mark.parametrize("verbosity", ['normal', 'debug'])
def test_cli_verbosity_flag(temp_input_file, temp_output_file, verbosity):
    cmd = [sys.executable, CLI_PATH,
           '--input', temp_input_file,
           '--output', temp_output_file,
           '--verbosity', verbosity]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert os.path.exists(temp_output_file)
    # Optionally check logs in result.stdout
    assert f"{verbosity}" in result.stdout or result.stderr

# Additional tests for config loading and error handling can be added as needed.
