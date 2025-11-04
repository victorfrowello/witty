# Contributing to Witty

Thank you for your interest in contributing! This project follows an LLM-first, Copilot-assisted development workflow and emphasizes a deterministic mock path for CI and testing.

Please read and follow these guidelines before opening pull requests.

1. Branching and commits
- Base work on the `main` branch. Create a feature branch: `feat/short-desc` or `fix/short-desc`.
- Write small, focused commits. Use conventional commit prefixes: `feat:`, `fix:`, `chore:`, `test:`.

2. Development environment
- Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- Use `REPRODUCIBLE_MODE=true` for deterministic behavior in tests and CI.

3. Tests and linting
- Add unit tests for all new behavior. Prefer the Mock adapter for tests that would otherwise call LLMs.
- Run linters and type checks before committing (project uses `pydantic`; future CI will include ruff/mypy/pytest).

4. Prompts and templates
- Store prompts in `src/prompts/` and include a `<template_id>.meta.json` file with keys: `template_id`, `version`, `released_at`.
- Prompts are immutable once released; bump the `version` for breaking changes.

5. Provenance and privacy
- Preserve provenance metadata for any module that performs non-deterministic operations.
- Respect `privacy_mode` settings when adding retrieval or enrichment tests (redact external snippets when `privacy_mode == "strict"`).

6. Pull requests
- Open a PR against `main` with a clear description, testing steps, and any relevant design notes.
- Reference related issues and include screenshots or sample outputs for user-facing changes.

If you are proposing a major design or API change, please open an issue first so we can discuss acceptance criteria and migration paths.

Thanks — Victor
