"""Pydantic models used across the Witty pipeline.

These types are intentionally lightweight for Sprint 1. They provide the
schema contracts used by deterministic modules and by the Mock adapter.

Notes for debuggers:
- Keep models small and explicit; add validators when the behavior needs
  to be enforced (e.g., confidence ranges, id formats).
- Use `model_dump()` / `model_dump_json()` to produce serializable outputs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ModuleStage(str, Enum):
	"""Enumerates the named stages of the pipeline for provenance.

	Keep this enum compact; callers should use string values when storing
	provenance to avoid tight coupling to the Python enum object.
	"""

	PREPROCESSING = "preprocessing"
	CONCISION = "concision"
	ENRICHMENT = "enrichment"
	MODALITY = "modality"
	WORLD = "world"
	SYMBOLIZATION = "symbolization"
	CNF = "cnf"
	VALIDATION = "validation"


class ProvenanceRecord(BaseModel):
	"""Provenance details produced by each pipeline module invocation.

	Fields:
	- id: deterministic or unique id for this provenance record
	- created_at: timezone-aware UTC timestamp
	- module_id/module_version: identifies the producing module
	- adapter_*: optional adapter metadata when an external adapter is used
	- origin_spans: list of (start, end) tuples pointing into the source text
	- event_log: ordered list of events (invocation, parse attempts, fallbacks)
	"""

	id: str
	# Use timezone-aware UTC timestamps to avoid ambiguity in logs/serialization
	created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
	module_id: str
	module_version: str
	adapter_id: Optional[str] = None
	prompt_template_id: Optional[str] = None
	adapter_request_id: Optional[str] = None
	# origin_spans are (start, end) indices into the original input string
	origin_spans: List[Tuple[int, int]] = Field(default_factory=list)
	enrichment_sources: List[str] = Field(default_factory=list)
	# Confidence is constrained to [0.0, 1.0]
	confidence: float = Field(1.0, ge=0.0, le=1.0)
	ambiguity_flags: List[str] = Field(default_factory=list)
	reduction_rationale: Optional[str] = None
	# event_log should be human-readable structured records for debugging
	event_log: List[Dict[str, Any]] = Field(default_factory=list)


class ModuleResult(BaseModel):
	"""Standard return shape for pipeline modules.

	- payload: the module-specific data (structured dict)
	- provenance_record: provenance for this module call
	- confidence/warnings: summary metrics for orchestrator logic
	"""

	payload: Dict[str, Any]
	provenance_record: ProvenanceRecord
	confidence: float = Field(1.0, ge=0.0, le=1.0)
	warnings: List[str] = Field(default_factory=list)


class FormalizeOptions(BaseModel):
	"""Runtime options controlling pipeline behavior.

	Keep defaults conservative (no retrieval, minimal symbolizations).
	"""

	retrieval_enabled: bool = False
	top_k_symbolizations: int = 1
	llm_provider: Optional[str] = None
	verbosity: int = 0
	quantifier_reduction_detail: bool = False
	allow_modal_advanced_cnf: bool = False
	privacy_mode: str = "default"


class AtomicClaim(BaseModel):
	"""Represents a single atomic claim extracted from the input.

	- text: the claim text
	- symbol: optional assigned symbol (e.g. P1)
	- origin_spans: offsets in original text where the claim was sourced
	- provenance: optional provenance record specific to this claim
	"""

	text: str
	symbol: Optional[str] = None
	origin_spans: List[Tuple[int, int]] = Field(default_factory=list)
	modal_context: Optional[str] = None
	provenance: Optional[ProvenanceRecord] = None


class ConcisionResult(BaseModel):
	"""Result schema for the concision (canonicalization) stage.

	This is the preferred structured output for LLM-assisted or deterministic
	concision functions. It should be validated by the orchestrator.
	"""

	canonical_text: str
	atomic_candidates: List[AtomicClaim]
	confidence: float = Field(1.0, ge=0.0, le=1.0)
	explanations: Optional[str] = None
	error: Optional[str] = None


class FormalizationResult(BaseModel):
	"""Top-level formalization output returned by the pipeline.

	Consumers should validate this object against `schemas/FormalizationResult.json`.
	"""

	request_id: str
	original_text: str
	canonical_text: Optional[str] = None
	enrichment_sources: List[str] = Field(default_factory=list)
	atomic_claims: List[AtomicClaim] = Field(default_factory=list)
	legend: Dict[str, str] = Field(default_factory=dict)
	logical_form_candidates: List[Dict[str, Any]] = Field(default_factory=list)
	chosen_logical_form: Optional[Dict[str, Any]] = None
	cnf: Optional[str] = None
	cnf_clauses: List[List[str]] = Field(default_factory=list)
	modal_metadata: Dict[str, Any] = Field(default_factory=dict)
	warnings: List[str] = Field(default_factory=list)
	confidence: float = Field(1.0, ge=0.0, le=1.0)
	provenance: List[ProvenanceRecord] = Field(default_factory=list)


