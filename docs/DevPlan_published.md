# Witty — Public Development Plan

Witty converts natural-language statements and arguments into structured, machine-readable formalizations that expose atomic claims, inference structure, and provenance metadata for each claim. This public development plan summarizes the project's vision, high-level roadmap, release milestones, contribution model, and a short quickstart for users and contributors.

## Vision
- Transparent, auditable formalizations that preserve provenance for every atomic claim.
- Reproducible pipelines: deterministic mock path for CI and testing; live model adapters optional and local.
- Interoperable outputs with stable JSON schemas so downstream tooling can consume results reliably.

## Who this is for
- Researchers and engineers working on formal reasoning, argument analysis, and explainability.
- Developers integrating LLM-assisted formalizers into workflows who need auditability and schema stability.

## Public Roadmap (high-level)
1. Sprint 0 — Project scaffold (completed): repository layout, JSON schemas, prompt templates, reproducible-mode infra.
2. Sprint 1 — Types & deterministic mock path: pydantic models, Mock adapter, CLI, minimal orchestrator.
3. Sprint 2 — Deterministic core pipeline: preprocessing, quantifier reduction, symbolizer, provenance utilities.
4. Sprint 3 — Logical transformations & validation: CNF transformer, validation rules, output assembly.
5. Sprint 4 — Optional local LLM wiring: adapters for local use only, with strict validation and fallback rules.
6. Sprint 5 — Agent orchestration & enrichment: policy-driven orchestrator and optional retrieval/summarization.
7. Sprint 6 — Tests, docs, and release packaging: integration test suite, CI hardening, documentation and examples.

Releases will be incremental and documented; schema changes will include migration notes.

## Release milestones
- v0.1.0: Deterministic pipeline and mock adapters; usable locally without external API keys.
- v0.2.0: CNF/validation and stable output assembly (schema-stable artifacts).
- v1.0.0: Public API stability, comprehensive docs, and example artifacts.

## Contribution
- Contributions welcome via pull requests. For significant design changes, open an issue first to discuss scope and acceptance criteria.
- Use feature branches; write focused commit messages and tests for new behavior.
- Prefer the Mock adapter in tests to keep CI reproducible.
- Store prompts under `src/prompts/` with a companion `<template_id>.meta.json` containing `{ template_id, version, released_at }`. When releasing a prompt, publish a new version rather than editing the released file.

For full contributor guidance, see `CONTRIBUTING.md`.

## Privacy & provenance
- Provenance records are created for every non-deterministic module call (module id/version, adapter id, origin spans, event log).
- `privacy_mode` supports redaction of sensitive text in provenance when set to `strict`.
- `REPRODUCIBLE_MODE=true` forces mock adapters and disables external retrieval to ensure deterministic CI runs.

## Quickstart (developer)
1. Clone the repository and create a virtual environment
```powershell
git clone <your-repo-url>
cd witty
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Run in reproducible mode (deterministic mock path)
```powershell
$env:REPRODUCIBLE_MODE = "true"
python -m src.test_runner --input examples/sample1.txt
```

Replace the command above with the real CLI entrypoint once implemented.

## Documentation & examples
- JSON schemas are authoritative and live in `schemas/`.
- Prompt templates live in `src/prompts/` and include metadata `.meta.json` files.
- Implementation and design notes are in `docs/DesignSpec_public.md` (public design spec).

## Community & support
- File issues for bugs or feature requests; open issues for major design proposals.

---

