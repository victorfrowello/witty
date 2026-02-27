"""
Mock adapter implementation for deterministic testing and CI.

Provides a lightweight, deterministic LLM adapter that returns canned responses
without making any network calls. This enables reliable unit testing, CI/CD
pipelines, and reproducible demonstrations without requiring API keys or
network connectivity.

The mock adapter recognizes common prompt template IDs and returns appropriate
structured responses that match the expected format for each pipeline stage.

Enhanced in Sprint 4 to support:
- Realistic concision LLM responses with origin span tracking
- Configurable response behaviors via config dictionary
- Simulated latency and token counts
- Extended prompt template support for all pipeline stages

Author: Victor Rowello
Sprint: 4
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base import AdapterResponse


# Pre-defined mock responses for different prompt templates
# These simulate realistic LLM outputs for testing
MOCK_RESPONSES: Dict[str, Dict[str, Any]] = {
    "concise_v1": {
        "patterns": {
            # Pattern-based responses for common inputs
            "if.*then": {
                "canonical_text": "{antecedent} implies {consequent}",
                "atomic_candidates": [
                    {"text": "{antecedent}", "origin_spans": [[0, 20]], "role": "antecedent"},
                    {"text": "{consequent}", "origin_spans": [[25, 50]], "role": "consequent"},
                ],
                "confidence": 0.92,
                "structure_type": "conditional",
            },
            "and|both": {
                "canonical_text": "{claim1}; {claim2}",
                "atomic_candidates": [
                    {"text": "{claim1}", "origin_spans": [[0, 15]]},
                    {"text": "{claim2}", "origin_spans": [[20, 35]]},
                ],
                "confidence": 0.88,
                "structure_type": "conjunction",
            },
        },
        "default": {
            "canonical_text": "mock canonical statement",
            "atomic_candidates": [
                {"text": "mock atomic claim", "origin_spans": [[0, 17]]}
            ],
            "confidence": 0.95,
        },
    },
    "symbolize_v1": {
        "default": {
            "legend": {"P": "proposition P", "Q": "proposition Q"},
            "logical_form_candidates": [
                {"form": "P → Q", "confidence": 0.90}
            ],
        },
    },
    "modal_detect_v1": {
        "default": {
            "modal_operators": [],
            "world_references": [],
            "confidence": 0.85,
        },
    },
    "world_construct_v1": {
        "default": {
            "worlds": [{"id": "w0", "description": "actual world"}],
            "accessibility": [],
            "confidence": 0.80,
        },
    },
}


class MockLLMAdapter:
    """
    Deterministic mock adapter for testing and reproducible pipelines.
    
    Returns pre-defined responses based on prompt template IDs, enabling
    predictable testing without live model calls. All outputs are deterministic
    and suitable for CI environments.
    
    Behavior:
    - Recognizes known prompt template IDs (concise_v1, symbolize_v1, etc.)
      and returns appropriate parsed JSON responses
    - For unknown templates, returns simple text responses prefixed with 'MOCK:'
    - Generates deterministic request IDs based on SHA256 hash of inputs
    - Populates full adapter_provenance for testing provenance tracking
    - Supports pattern matching for more realistic responses based on input
    
    Configuration options (via config dict):
        simulate_latency: bool - Whether to include simulated latency in metadata
        token_multiplier: float - Multiplier for token count estimation
        fail_rate: float - Probability of simulated failure (0.0-1.0) for testing retries
        custom_responses: dict - Override default responses for specific templates
    
    Attributes:
        adapter_id: Identifier for this adapter (default: 'mock')
        version: Version string for this adapter implementation
        config: Configuration dictionary for behavior customization
    """

    def __init__(
        self,
        adapter_id: str = "mock",
        version: str = "0.1",
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the mock adapter.
        
        Args:
            adapter_id: Unique identifier for this adapter instance
            version: Semantic version of the adapter
            config: Configuration dictionary with optional settings:
                - simulate_latency: Include fake latency in metadata
                - token_multiplier: Scale token estimates
                - custom_responses: Dict of template_id -> response overrides
        """
        self.adapter_id = adapter_id
        self.version = version
        self.config = config or {}
        
        # Extract configuration options
        self._simulate_latency = self.config.get("simulate_latency", False)
        self._token_multiplier = self.config.get("token_multiplier", 1.0)
        self._custom_responses = self.config.get("custom_responses", {})

    def _make_request_id(self, prompt_template_id: str, prompt: str) -> str:
        """
        Generate a deterministic request ID based on inputs.
        
        Creates a reproducible hash-based ID that will be identical for the
        same inputs, enabling deterministic testing and comparison.
        
        Args:
            prompt_template_id: Template identifier used in the request
            prompt: The actual prompt text
            
        Returns:
            Truncated SHA256 hash as a 12-character hex string
        """
        # Combine all inputs to create a unique but deterministic key
        key = f"{self.adapter_id}:{self.version}:{prompt_template_id}:{prompt}"
        hash_digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return hash_digest[:12]  # Use first 12 characters for brevity

    def _extract_parts_from_prompt(self, prompt: str) -> Dict[str, str]:
        """
        Extract meaningful parts from the prompt for generating realistic responses.
        
        Parses the input prompt to identify key components like antecedents,
        consequents, and claims that can be used to generate more realistic
        mock responses.
        
        Args:
            prompt: The input prompt text
            
        Returns:
            Dictionary with extracted parts (antecedent, consequent, claims, etc.)
        """
        parts: Dict[str, str] = {}
        
        # Try to extract conditional parts (if-then)
        if_then_match = re.search(r'\bif\s+(.+?)\s+then\s+(.+?)(?:\.|$)', prompt, re.IGNORECASE)
        if if_then_match:
            parts["antecedent"] = if_then_match.group(1).strip()
            parts["consequent"] = if_then_match.group(2).strip()
            parts["structure"] = "conditional"
            return parts
        
        # Try to extract conjunction parts
        and_match = re.search(r'(.+?)\s+and\s+(.+?)(?:\.|$)', prompt, re.IGNORECASE)
        if and_match:
            parts["claim1"] = and_match.group(1).strip()
            parts["claim2"] = and_match.group(2).strip()
            parts["structure"] = "conjunction"
            return parts
        
        # Default: treat entire prompt as single claim
        parts["claim"] = prompt.strip().rstrip('.')
        parts["structure"] = "simple"
        return parts

    def _build_response_for_template(
        self,
        template_id: str,
        prompt: str,
        parts: Dict[str, str]
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Build an appropriate response based on template and extracted parts.
        
        Args:
            template_id: The prompt template identifier
            prompt: Original prompt text
            parts: Extracted parts from the prompt
            
        Returns:
            Tuple of (text response, parsed JSON dict or None)
        """
        # Check for custom responses first
        if template_id in self._custom_responses:
            custom = self._custom_responses[template_id]
            return json.dumps(custom), custom
        
        # Get template-specific mock response
        template_base = template_id.split("_v")[0] + "_v1" if "_v" in template_id else template_id
        template_config = MOCK_RESPONSES.get(template_base, {})
        
        # Concision template with intelligent response generation
        if template_id and template_id.startswith("concise"):
            if parts.get("structure") == "conditional":
                antecedent = parts.get("antecedent", "condition")
                consequent = parts.get("consequent", "result")
                # Calculate realistic origin spans based on actual text positions
                ante_start = prompt.lower().find(antecedent.lower()) if antecedent else 0
                ante_end = ante_start + len(antecedent) if ante_start >= 0 else len(antecedent)
                cons_start = prompt.lower().find(consequent.lower()) if consequent else ante_end + 5
                cons_end = cons_start + len(consequent) if cons_start >= 0 else cons_start + len(consequent)
                
                parsed_json = {
                    "canonical_text": f"{antecedent} implies {consequent}",
                    "atomic_candidates": [
                        {
                            "text": antecedent,
                            "origin_spans": [[max(0, ante_start), max(1, ante_end)]],
                            "role": "antecedent"
                        },
                        {
                            "text": consequent,
                            "origin_spans": [[max(0, cons_start), max(1, cons_end)]],
                            "role": "consequent"
                        }
                    ],
                    "confidence": 0.92,
                    "structure_type": "conditional",
                }
            elif parts.get("structure") == "conjunction":
                claim1 = parts.get("claim1", "first claim")
                claim2 = parts.get("claim2", "second claim")
                c1_start = prompt.lower().find(claim1.lower()) if claim1 else 0
                c1_end = c1_start + len(claim1) if c1_start >= 0 else len(claim1)
                c2_start = prompt.lower().find(claim2.lower()) if claim2 else c1_end + 5
                c2_end = c2_start + len(claim2) if c2_start >= 0 else c2_start + len(claim2)
                
                parsed_json = {
                    "canonical_text": f"{claim1}; {claim2}",
                    "atomic_candidates": [
                        {"text": claim1, "origin_spans": [[max(0, c1_start), max(1, c1_end)]]},
                        {"text": claim2, "origin_spans": [[max(0, c2_start), max(1, c2_end)]]},
                    ],
                    "confidence": 0.88,
                    "structure_type": "conjunction",
                }
            else:
                # Simple claim
                claim = parts.get("claim", prompt.strip())
                parsed_json = {
                    "canonical_text": claim,
                    "atomic_candidates": [
                        {"text": claim, "origin_spans": [[0, len(claim)]]}
                    ],
                    "confidence": 0.95,
                }
            return json.dumps(parsed_json), parsed_json
            
        elif template_id and template_id.startswith("symbolize"):
            # Symbolization response
            default = template_config.get("default", {})
            parsed_json = {
                "legend": default.get("legend", {"P": "proposition"}),
                "logical_form_candidates": default.get("logical_form_candidates", [])
            }
            return json.dumps(parsed_json), parsed_json
            
        elif template_id and template_id.startswith("modal"):
            # Modal detection response
            default = template_config.get("default", {})
            parsed_json = {
                "modal_operators": default.get("modal_operators", []),
                "world_references": default.get("world_references", []),
                "confidence": default.get("confidence", 0.85),
            }
            return json.dumps(parsed_json), parsed_json
            
        elif template_id and template_id.startswith("world"):
            # World construction response
            default = template_config.get("default", {})
            parsed_json = {
                "worlds": default.get("worlds", [{"id": "w0", "description": "actual world"}]),
                "accessibility": default.get("accessibility", []),
                "confidence": default.get("confidence", 0.80),
            }
            return json.dumps(parsed_json), parsed_json
        
        # Unknown template - return generic response
        return f"MOCK: {prompt}", None

    def generate(
        self,
        prompt_template_id: str,
        prompt: str,
        **kwargs: Any
    ) -> AdapterResponse:
        """
        Generate a mock response based on the prompt template ID.
        
        Returns deterministic, template-specific responses suitable for testing
        each stage of the pipeline. The responses are crafted to match the
        expected structure for each template type. For known templates, responses
        are intelligently generated based on the input prompt structure.
        
        Args:
            prompt_template_id: Identifier for the prompt template (e.g.,
                               'concise_v1', 'symbolize_v1')
            prompt: The prompt text (used for deterministic hashing and 
                   intelligent response generation)
            **kwargs: Additional parameters (ignored in mock implementation)
            
        Returns:
            AdapterResponse with appropriate parsed_json for known templates,
            or simple text response for unknown templates
        """
        # Generate deterministic request ID for provenance tracking
        request_id = self._make_request_id(prompt_template_id or "", prompt or "")
        start_time = datetime.now(timezone.utc)
        
        # Extract meaningful parts from the prompt
        parts = self._extract_parts_from_prompt(prompt or "")
        
        # Build template-specific response
        text, parsed_json = self._build_response_for_template(
            prompt_template_id or "", prompt or "", parts
        )

        # Calculate token count with multiplier
        base_tokens = len(text.split()) if text else 0
        tokens = int(base_tokens * self._token_multiplier)

        # Build comprehensive adapter provenance for testing
        end_time = datetime.now(timezone.utc)
        adapter_provenance = {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "prompt_template_id": prompt_template_id,
            "request_id": request_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "latency_ms": int((end_time - start_time).total_seconds() * 1000) if self._simulate_latency else 0,
            "raw_output_summary": (text[:200] + "...") if len(text) > 200 else text,
        }

        model_metadata = {
            "mock": True,
            "extracted_structure": parts.get("structure", "unknown"),
        }

        return AdapterResponse(
            text=text,
            parsed_json=parsed_json,
            tokens=tokens if tokens > 0 else None,
            model_metadata=model_metadata,
            adapter_provenance=adapter_provenance,
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return metadata about this mock adapter instance.
        
        Returns:
            Dictionary containing adapter ID, version, and configuration
        """
        return {
            "adapter_id": self.adapter_id,
            "version": self.version,
            "is_mock": True,
            "simulate_latency": self._simulate_latency,
            "token_multiplier": self._token_multiplier,
            "custom_response_templates": list(self._custom_responses.keys()),
        }
