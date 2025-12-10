# Witty — Public Design Specification

This public design spec describes the system goals, high-level architecture, module contracts, and public data schemas for Witty. It omits internal development workflows and tooling-specific guidance so external readers and integrators can focus on observable behaviors, inputs/outputs, and extension points.

## Goals
- Produce a `FormalizationResult` JSON for each input text containing: canonical text, atomic claims (with provenance), legend, logical form candidates (JSON AST + notation), chosen logical form, CNF, validation results, warnings, and confidence scores.
- Preserve provenance for traceability and auditability.
- Provide deterministic fallback behavior so the system is testable without external model access.

## High-level pipeline
Entry point signature (illustrative):
```python
def formalize_statement(input_text: str, options: FormalizeOptions) -> FormalizationResult
```

Pipeline stages (each stage returns a ModuleResult with payload, provenance_record, confidence, warnings):
1. Ingest — normalization and metadata extraction.
2. Preprocessing — tokenization, sentence/ clause segmentation, and token annotations (negation, modals, quantifiers). Output includes `origin_spans` mapping.
3. Concision — produce a canonicalized version of the input and candidate atomic claims. This stage may be LLM-assisted; deterministic fallback must exist.
4. Enrichment (optional) — controlled retrieval and summarization when explicitly enabled; must respect privacy settings.
5. Modal detection & framing — detect modal language and recommend framing.
6. World construction — reduce quantifiers to deterministic identifiers and expand presuppositions for downstream reasoning.
7. Symbolization — assign deterministic symbols (P1, P2, ...) and produce logical form candidates (JSON ASTs).
8. CNF transformation — convert chosen logical forms to CNF while preserving modal wrappers at the atom level.
9. Validation & sanity checks — well-formedness, provenance coverage, contradiction/tautology detection.
10. Output assembly — assemble `FormalizationResult` and emit provenance records.

Notes:
- Deterministic modules must be pure functions given the same configuration and salt.
- LLM-assisted modules must provide parsed structured output or trigger deterministic fallback behavior.

## Module contracts
- All modules accept typed inputs (JSON/Pydantic) and return `ModuleResult` objects with these fields: `payload`, `provenance_record`, `confidence`, `warnings`.
- ProvenanceRecord must include: id, created_at, module_id/module_version, adapter_id (when applicable), prompt_template_id (when applicable), origin_spans, enrichment_sources, confidence, ambiguity_flags, reduction_rationale, and an event_log.

## Adapters
- Model adapters (for external LLMs or local models) isolate network/auth behavior and return a structured `AdapterResponse` with: `text`, optional `parsed_json`, `tokens`, `model_metadata`, and `adapter_provenance` (adapter id, version, prompt id, request id, raw_output_summary).
- A Mock adapter implementation must exist to support deterministic CI and development without external credentials.

## Data models and schemas
- Keep authoritative JSON schemas under `schemas/`. Public API consumers should validate outputs against these schemas.
- Core schema elements:
  - `FormalizeOptions`: runtime flags and thresholds (retrieval_enabled, top_k_symbolizations, llm_provider, verbosity, quantifier_reduction_detail, allow_modal_advanced_cnf, privacy_mode).
  - `ProvenanceRecord`: structured per-module provenance metadata (id, created_at, module_id/module_version, adapter info, origin_spans, enrichment_sources, confidence, event_log).
  - `FormalizationResult`: final output contract (request_id, original_text, canonical_text, enrichment_sources, atomic_claims, legend, logical_form_candidates, chosen_logical_form, cnf, cnf_clauses, modal_metadata, warnings, confidence, provenance).

## Prompt/template management (public view)
- Prompts and templates are stored under `src/prompts/` with a companion `<template_id>.meta.json` for metadata. Public releases should include versioned templates and clear examples showing expected input/output shapes.

## Provenance, privacy, and determinism
- Provenance records must be generated for all non-deterministic operations and stored alongside outputs.
- `privacy_mode` ∈ {"default", "strict"}. In `strict` mode, provenance must redact text snippets and URLs while preserving structured identifiers.
- Deterministic id generation: an id should be derivable from a deterministic salt, normalized input, module id/version, and timestamp (SHA256-based) and suitable for auditing.

## Validation and configuration
- Default thresholds should be exposed in top-level metadata within the `FormalizationResult` (e.g., `llm_conf_threshold`, `origin_spans_coverage_threshold`).
- Pipeline stages must validate inputs/outputs against the schemas before proceeding.

## Testing and reproducibility
- CI must include a reproducible mode that uses the Mock adapter and disables external retrieval.
- Unit tests should cover deterministic modules and error/fallback behaviors for LLM-assisted stages (parse failures, low confidence, retries).

## Extension points for integrators
- Adapters: provide a new adapter implementing the adapter contract to integrate a new model provider.
- Retrieval: implement a RetrievalAdapter with `retrieve(query, k)` and `summarize(document, span)` methods for optional context enrichment.
- Prompt templates: add versioned prompt files under `src/prompts/` with examples and schema expectations.

## Public-facing operational guidance
- Default to reproducible/mock mode for CI and release artifacts.
- When using live models locally, ensure adapters return `parsed_json` where possible and that event logs capture adapter request ids and summaries.

## Schemas and references
- Schemas in `schemas/` are the authoritative contract for integration. Consumers should validate outputs with those schemas.

---

This public design spec intentionally omits internal development tooling other non-essential internal information. 
