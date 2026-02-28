"""
Smolagents Tool Wrappers for Witty Pipeline Modules.

Wraps each pipeline module as a typed smolagents Tool for use with
the agentic orchestrator. Each tool validates inputs/outputs and
records provenance.

Author: Victor Rowello
Sprint: 6
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import json

# Import smolagents base - will be available after pip install
try:
    from smolagents import Tool
except ImportError:
    # Provide stub for development without smolagents installed
    class Tool:
        """Stub Tool class for development without smolagents."""
        name: str = ""
        description: str = ""
        inputs: Dict[str, Any] = {}
        output_type: str = "string"
        
        def forward(self, **kwargs: Any) -> Any:
            raise NotImplementedError
        
        def __call__(self, **kwargs: Any) -> Any:
            return self.forward(**kwargs)

from src.witty_types import (
    ModuleResult,
    ConcisionResult,
    AtomicClaim,
    ProvenanceRecord,
    FormalizeOptions,
)
from src.pipeline.orchestrator import AgentContext, make_provenance_id


class PreprocessTool(Tool):
    """
    Tool wrapper for preprocessing pipeline stage.
    
    Segments and tokenizes input text, producing clause boundaries
    and token annotations for downstream processing.
    """
    
    name = "preprocess"
    description = """Preprocess natural language text by segmenting into clauses and 
    tokenizing. Returns a PreprocessingResult with clauses, tokens, and origin spans.
    Use this as the first step in any formalization pipeline."""
    
    inputs = {
        "text": {
            "type": "string",
            "description": "The natural language text to preprocess"
        }
    }
    output_type = "string"  # JSON string of PreprocessingResult
    
    def __init__(self, ctx: Optional[AgentContext] = None):
        """
        Initialize the preprocessing tool.
        
        Args:
            ctx: Optional pipeline context for configuration
        """
        super().__init__()
        self.ctx = ctx
    
    def forward(self, text: str) -> str:
        """
        Execute preprocessing on input text.
        
        Args:
            text: Natural language text to preprocess
            
        Returns:
            JSON string containing PreprocessingResult
        """
        from src.pipeline import preprocessing as prep_module
        
        try:
            result = prep_module.preprocess(text)
            # Convert to dict for JSON serialization
            return json.dumps({
                "normalized_text": result.normalized_text,
                "clauses": [
                    {"text": c.text, "start_char": c.start_char, "end_char": c.end_char}
                    for c in result.clauses
                ],
                "tokens": [
                    {"text": t.text, "char_offset": t.char_offset, "char_end": t.char_end, "annotations": list(t.annotations)}
                    for t in result.tokens
                ],
                "sentence_boundaries": result.sentence_boundaries,
                "origin_spans": result.origin_spans,
                "success": True
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "normalized_text": text.strip(),
                "clauses": [{"text": text.strip(), "start_char": 0, "end_char": len(text)}],
                "tokens": [],
                "sentence_boundaries": [],
                "origin_spans": {}
            })


class ConcisionTool(Tool):
    """
    Tool wrapper for concision pipeline stage.
    
    Extracts atomic claims from preprocessed text, decomposing logical
    structures like conditionals and conjunctions.
    """
    
    name = "concision"
    description = """Extract atomic claims from preprocessed text. Decomposes logical 
    structures (if-then, and, or) into minimal atomic propositions. Returns ConcisionResult 
    with canonical_text and atomic_candidates."""
    
    inputs = {
        "preprocessing_result": {
            "type": "string",
            "description": "JSON string from preprocessing stage"
        },
        "use_llm": {
            "type": "boolean",
            "description": "Whether to use LLM for concision (default: False for deterministic)",
            "nullable": True
        }
    }
    output_type = "string"  # JSON string of ConcisionResult
    
    def __init__(self, ctx: Optional[AgentContext] = None, llm_adapter: Any = None):
        """
        Initialize the concision tool.
        
        Args:
            ctx: Optional pipeline context
            llm_adapter: Optional LLM adapter for non-deterministic concision
        """
        super().__init__()
        self.ctx = ctx
        self.llm_adapter = llm_adapter
    
    def forward(self, preprocessing_result: str, use_llm: bool = False) -> str:
        """
        Execute concision on preprocessed text.
        
        Args:
            preprocessing_result: JSON string from preprocessing stage
            use_llm: Whether to use LLM (default False for deterministic)
            
        Returns:
            JSON string containing ConcisionResult
        """
        from src.pipeline import concision as conc_module
        from src.pipeline.preprocessing import PreprocessingResult, Clause, Token
        
        try:
            # Parse preprocessing result
            prep_data = json.loads(preprocessing_result)
            prep_result = PreprocessingResult(
                normalized_text=prep_data["normalized_text"],
                clauses=[
                    Clause(text=c["text"], start_char=c["start_char"], end_char=c["end_char"])
                    for c in prep_data.get("clauses", [])
                ],
                tokens=[
                    Token(
                        text=t["text"],
                        pos=t.get("pos", "UNKNOWN"),
                        lemma=t.get("lemma", t["text"]),
                        char_offset=t.get("char_offset", 0),
                        char_end=t.get("char_end", len(t["text"])),
                        annotations=t.get("annotations", [])
                    )
                    for t in prep_data.get("tokens", [])
                ],
                sentence_boundaries=prep_data.get("sentence_boundaries", []),
                origin_spans=prep_data.get("origin_spans", {})
            )
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Use deterministic concision (always, for now)
            module_result = conc_module.deterministic_concision(prep_result, ctx)
            
            # Convert atomic_candidates to JSON-safe format (remove provenance objects with datetimes)
            atomic_candidates = []
            for ac in module_result.payload.get("atomic_candidates", []):
                atomic_candidates.append({
                    "text": ac.get("text", ""),
                    "origin_spans": ac.get("origin_spans", []),
                    "symbol": ac.get("symbol"),
                    "modal_context": ac.get("modal_context")
                })
            
            return json.dumps({
                "success": True,
                "canonical_text": module_result.payload.get("canonical_text", ""),
                "atomic_candidates": atomic_candidates,
                "structural_metadata": module_result.payload.get("structural_metadata", {}),
                "confidence": module_result.confidence,
                "warnings": module_result.warnings
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "canonical_text": "",
                "atomic_candidates": [],
                "structural_metadata": {},
                "confidence": 0.0,
                "warnings": [f"Concision failed: {str(e)}"]
            })


class EnrichmentTool(Tool):
    """
    Tool wrapper for enrichment pipeline stage.
    
    Enriches claims with external knowledge through retrieval,
    expanding presuppositions and grounding underspecified entities.
    """
    
    name = "enrich"
    description = """Enrich atomic claims with external knowledge. Queries retrieval 
    sources to expand presuppositions and ground underspecified entities. Returns 
    EnrichmentResult with expanded_claims and enrichment_sources."""
    
    inputs = {
        "concision_result": {
            "type": "string",
            "description": "JSON string from concision stage"
        },
        "retrieval_enabled": {
            "type": "boolean",
            "description": "Whether to enable external retrieval (default: False)",
            "nullable": True
        }
    }
    output_type = "string"  # JSON string of EnrichmentResult
    
    def __init__(
        self, 
        ctx: Optional[AgentContext] = None,
        llm_adapter: Any = None,
        retrieval_adapter: Any = None
    ):
        """
        Initialize the enrichment tool.
        
        Args:
            ctx: Optional pipeline context
            llm_adapter: Optional LLM adapter for enrichment
            retrieval_adapter: Optional retrieval adapter
        """
        super().__init__()
        self.ctx = ctx
        self.llm_adapter = llm_adapter
        self.retrieval_adapter = retrieval_adapter
    
    def forward(self, concision_result: str, retrieval_enabled: bool = False) -> str:
        """
        Execute enrichment on concision result.
        
        Args:
            concision_result: JSON string from concision stage
            retrieval_enabled: Whether to enable retrieval
            
        Returns:
            JSON string containing EnrichmentResult
        """
        from src.pipeline import enrichment as enrich_module
        from src.witty_types import ConcisionResult, AtomicClaim
        
        try:
            # Parse concision result
            conc_data = json.loads(concision_result)
            
            # Build ConcisionResult
            atomic_candidates = [
                AtomicClaim(
                    text=ac.get("text", ""),
                    origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
                )
                for ac in conc_data.get("atomic_candidates", [])
            ]
            
            conc_result = ConcisionResult(
                canonical_text=conc_data.get("canonical_text", ""),
                atomic_candidates=atomic_candidates,
                structural_metadata=conc_data.get("structural_metadata", {}),
                confidence=conc_data.get("confidence", 1.0)
            )
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(retrieval_enabled=retrieval_enabled),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Get adapters (use mocks if not provided)
            from src.adapters.mock import MockLLMAdapter
            from src.adapters.retrieval import MockRetrievalAdapter
            
            llm = self.llm_adapter or MockLLMAdapter()
            retrieval = self.retrieval_adapter or MockRetrievalAdapter()
            
            # Call enrichment
            enrichment_result = enrich_module.llm_enrichment(
                conc_result, ctx, llm, retrieval
            )
            
            return json.dumps({
                "success": True,
                "expanded_claims": [
                    {
                        "claim_id": ec.claim_id,
                        "text": ec.text,
                        "origin": ec.origin,
                        "confidence": ec.confidence,
                        "source_ids": ec.source_ids
                    }
                    for ec in enrichment_result.expanded_claims
                ],
                "enrichment_sources": [
                    {
                        "source_id": es.source_id,
                        "url": es.url,
                        "content_summary": es.content_summary,
                        "relevance_score": es.relevance_score
                    }
                    for es in enrichment_result.enrichment_sources
                ],
                "coherence_flags": enrichment_result.coherence_flags,
                "confidence": enrichment_result.confidence,
                "warnings": enrichment_result.warnings
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "expanded_claims": [],
                "enrichment_sources": [],
                "coherence_flags": [],
                "confidence": 0.0,
                "warnings": [f"Enrichment failed: {str(e)}"]
            })


class ModalDetectionTool(Tool):
    """
    Tool wrapper for modal detection pipeline stage.
    
    Detects modal operators (must, should, possible, etc.) in claims
    and determines appropriate logical frame (default S5).
    """
    
    name = "detect_modal"
    description = """Detect modal operators in claims. Identifies necessity, possibility, 
    obligation, and permission modalities. Selects appropriate logical frame (default S5). 
    Returns ModalResult with modal_contexts and frame_selection."""
    
    inputs = {
        "input_result": {
            "type": "string",
            "description": "JSON string from concision or enrichment stage"
        }
    }
    output_type = "string"  # JSON string of ModalResult
    
    def __init__(self, ctx: Optional[AgentContext] = None):
        """
        Initialize the modal detection tool.
        
        Args:
            ctx: Optional pipeline context
        """
        super().__init__()
        self.ctx = ctx
    
    def forward(self, input_result: str) -> str:
        """
        Execute modal detection on input claims.
        
        Args:
            input_result: JSON string from concision or enrichment stage
            
        Returns:
            JSON string containing ModalResult
        """
        from src.pipeline import modality as modal_module
        from src.witty_types import ConcisionResult, AtomicClaim, EnrichmentResult
        
        try:
            # Parse input result
            data = json.loads(input_result)
            
            # Determine input type and build appropriate object
            if "expanded_claims" in data:
                # EnrichmentResult
                from src.witty_types import ExpandedClaim
                expanded_claims = [
                    ExpandedClaim(
                        claim_id=ec.get("claim_id", f"claim_{i}"),
                        text=ec.get("text", ""),
                        origin=ec.get("origin", "input"),
                        confidence=ec.get("confidence", 1.0),
                        source_ids=ec.get("source_ids", [])
                    )
                    for i, ec in enumerate(data.get("expanded_claims", []))
                ]
                input_obj = EnrichmentResult(
                    expanded_claims=expanded_claims,
                    enrichment_sources=[],
                    coherence_flags=data.get("coherence_flags", []),
                    confidence=data.get("confidence", 1.0),
                    warnings=[]
                )
            else:
                # ConcisionResult
                atomic_candidates = [
                    AtomicClaim(
                        text=ac.get("text", ""),
                        origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
                    )
                    for ac in data.get("atomic_candidates", [])
                ]
                input_obj = ConcisionResult(
                    canonical_text=data.get("canonical_text", ""),
                    atomic_candidates=atomic_candidates,
                    structural_metadata=data.get("structural_metadata", {}),
                    confidence=data.get("confidence", 1.0)
                )
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Call modal detection
            module_result = modal_module.detect_modal(input_obj, ctx)
            
            # Extract modal result from payload (it's a dict from model_dump())
            modal_payload = module_result.payload
            
            return json.dumps({
                "success": True,
                "modal_contexts": modal_payload.get("modal_contexts", []),
                "frame_selection": modal_payload.get("frame_selection", "S5"),
                "has_modality": modal_payload.get("has_modality", False),
                "confidence": modal_payload.get("confidence", 1.0),
                "warnings": modal_payload.get("warnings", [])
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "modal_contexts": [],
                "frame_selection": "S5",
                "has_modality": False,
                "confidence": 0.0,
                "warnings": [f"Modal detection failed: {str(e)}"]
            })


class WorldConstructionTool(Tool):
    """
    Tool wrapper for world construction pipeline stage.
    
    Builds a coherent world model by grounding entities, reducing
    quantifiers, and constructing possible worlds for modal claims.
    """
    
    name = "world_construct"
    description = """Construct a world model from enriched claims. Grounds entities, 
    reduces quantifiers to propositional placeholders, and builds possible worlds 
    for modal claims. Returns WorldResult with atomic_instances and entity_groundings."""
    
    inputs = {
        "input_result": {
            "type": "string", 
            "description": "JSON string from concision or enrichment stage"
        },
        "modal_result": {
            "type": "string",
            "description": "JSON string from modal detection stage",
            "nullable": True
        }
    }
    output_type = "string"  # JSON string of WorldResult
    
    def __init__(self, ctx: Optional[AgentContext] = None, llm_adapter: Any = None):
        """
        Initialize the world construction tool.
        
        Args:
            ctx: Optional pipeline context
            llm_adapter: Optional LLM adapter for LLM-assisted world construction
        """
        super().__init__()
        self.ctx = ctx
        self.llm_adapter = llm_adapter
    
    def forward(self, input_result: str, modal_result: Optional[str] = None) -> str:
        """
        Execute world construction on input claims.
        
        Args:
            input_result: JSON string from concision or enrichment stage
            modal_result: Optional JSON string from modal detection
            
        Returns:
            JSON string containing WorldResult
        """
        from src.pipeline import world as world_module
        from src.witty_types import ConcisionResult, AtomicClaim
        
        try:
            # Parse input result
            data = json.loads(input_result)
            
            # Build ConcisionResult (world_construct expects this)
            atomic_candidates = [
                AtomicClaim(
                    text=ac.get("text", ""),
                    origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
                )
                for ac in data.get("atomic_candidates", data.get("expanded_claims", []))
            ]
            
            # Handle case where expanded_claims use different structure
            if "expanded_claims" in data:
                atomic_candidates = [
                    AtomicClaim(
                        text=ec.get("text", ""),
                        origin_spans=[]
                    )
                    for ec in data.get("expanded_claims", [])
                ]
            
            conc_result = ConcisionResult(
                canonical_text=data.get("canonical_text", ""),
                atomic_candidates=atomic_candidates,
                structural_metadata=data.get("structural_metadata", {}),
                confidence=data.get("confidence", 1.0)
            )
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Call world construction
            module_result = world_module.world_construct(
                conc_result, ctx, salt=ctx.deterministic_salt
            )
            
            # Extract world result from payload
            world_payload = module_result.payload
            
            return json.dumps({
                "success": True,
                "atomic_instances": [
                    {
                        "text": ai.get("text", ai.get("claim_text", "")),
                        "symbol": ai.get("symbol", ""),
                        "origin_spans": ai.get("origin_spans", []),
                        "grounding_method": ai.get("grounding_method", "deterministic")
                    }
                    for ai in world_payload.get("atomic_instances", world_payload.get("atomic_claims", []))
                ],
                "entity_groundings": world_payload.get("entity_groundings", {}),
                "coherence_report": world_payload.get("coherence_report", {}),
                "confidence": module_result.confidence,
                "warnings": module_result.warnings
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "atomic_instances": [],
                "entity_groundings": {},
                "coherence_report": {},
                "confidence": 0.0,
                "warnings": [f"World construction failed: {str(e)}"]
            })


class SymbolizerTool(Tool):
    """
    Tool wrapper for symbolization pipeline stage.
    
    Assigns formal symbols (P1, P2, ...) to atomic claims and builds
    a legend mapping symbols to their natural language meanings.
    """
    
    name = "symbolize"
    description = """Assign formal symbols to atomic claims. Creates P1, P2, ... symbols 
    and builds a legend mapping each symbol to its natural language meaning. Returns 
    SymbolizerResult with legend and atomic_claims."""
    
    inputs = {
        "input_result": {
            "type": "string",
            "description": "JSON string from concision, enrichment, or world construction stage"
        }
    }
    output_type = "string"  # JSON string of SymbolizerResult
    
    def __init__(self, ctx: Optional[AgentContext] = None):
        """
        Initialize the symbolizer tool.
        
        Args:
            ctx: Optional pipeline context
        """
        super().__init__()
        self.ctx = ctx
    
    def forward(self, input_result: str) -> str:
        """
        Execute symbolization on input claims.
        
        Args:
            input_result: JSON string from previous pipeline stage
            
        Returns:
            JSON string containing SymbolizerResult
        """
        from src.pipeline import symbolizer as sym_module
        from src.witty_types import ConcisionResult, AtomicClaim, WorldResult
        
        try:
            # Parse input result
            data = json.loads(input_result)
            
            # Build appropriate input object
            if "atomic_instances" in data:
                # WorldResult
                from src.witty_types import WorldResult, EntityGrounding, CoherenceReport
                
                atomic_claims = [
                    AtomicClaim(
                        text=ai.get("text", ""),
                        symbol=ai.get("symbol", ""),
                        origin_spans=[tuple(s) for s in ai.get("origin_spans", [])]
                    )
                    for ai in data.get("atomic_instances", [])
                ]
                
                # Build entity_groundings dict from data
                raw_groundings = data.get("entity_groundings", {})
                entity_groundings_dict = {}
                if isinstance(raw_groundings, dict):
                    for key, eg in raw_groundings.items():
                        entity_groundings_dict[key] = EntityGrounding(
                            entity_text=eg.get("entity_text", key),
                            entity_type=eg.get("entity_type", "GENERIC"),
                            grounding_method=eg.get("grounding_method", "deterministic"),
                            related_claim_ids=eg.get("related_claim_ids", []),
                            confidence=eg.get("confidence", 0.8)
                        )
                
                input_obj = WorldResult(
                    atomic_claims=atomic_claims,
                    entity_groundings=entity_groundings_dict,
                    coherence_report=CoherenceReport(
                        is_coherent=True,
                        entity_completeness=1.0,
                        quantifier_coverage=1.0,
                        ungrounded_entities=[],
                        warnings=[]
                    ),
                    presuppositions=[],
                    reduction_log=[]
                )
            else:
                # ConcisionResult
                atomic_candidates = []
                for ac in data.get("atomic_candidates", data.get("expanded_claims", [])):
                    if isinstance(ac, dict):
                        atomic_candidates.append(AtomicClaim(
                            text=ac.get("text", ""),
                            origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
                        ))
                
                input_obj = ConcisionResult(
                    canonical_text=data.get("canonical_text", ""),
                    atomic_candidates=atomic_candidates,
                    structural_metadata=data.get("structural_metadata", {}),
                    confidence=data.get("confidence", 1.0)
                )
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Call symbolizer
            module_result = sym_module.symbolizer(input_obj, ctx)
            
            # Extract symbolizer result from payload
            sym_payload = module_result.payload
            
            # Build atomic_claims output - payload items may be dicts or objects
            atomic_claims_output = []
            for ac in sym_payload.get("atomic_claims", []):
                if isinstance(ac, dict):
                    atomic_claims_output.append({
                        "text": ac.get("text", ""),
                        "symbol": ac.get("symbol", ""),
                        "origin_spans": list(ac.get("origin_spans", []))
                    })
                else:
                    atomic_claims_output.append({
                        "text": ac.text,
                        "symbol": ac.symbol,
                        "origin_spans": list(ac.origin_spans)
                    })
            
            return json.dumps({
                "success": True,
                "legend": sym_payload.get("legend", {}),
                "atomic_claims": atomic_claims_output,
                "confidence": module_result.confidence,
                "warnings": module_result.warnings
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "legend": {},
                "atomic_claims": [],
                "confidence": 0.0,
                "warnings": [f"Symbolization failed: {str(e)}"]
            })


class CNFTransformTool(Tool):
    """
    Tool wrapper for CNF transformation pipeline stage.
    
    Converts logical forms to Conjunctive Normal Form (CNF) for
    use in downstream reasoning tools.
    """
    
    name = "cnf_transform"
    description = """Transform logical forms to Conjunctive Normal Form (CNF). Eliminates 
    implications and biconditionals, converts to NNF, and distributes OR over AND. Returns 
    CNFResult with cnf_string and cnf_clauses."""
    
    inputs = {
        "symbolizer_result": {
            "type": "string",
            "description": "JSON string from symbolization stage"
        }
    }
    output_type = "string"  # JSON string of CNFResult
    
    def __init__(self, ctx: Optional[AgentContext] = None):
        """
        Initialize the CNF transform tool.
        
        Args:
            ctx: Optional pipeline context
        """
        super().__init__()
        self.ctx = ctx
    
    def forward(self, symbolizer_result: str) -> str:
        """
        Execute CNF transformation on symbolizer result.
        
        Args:
            symbolizer_result: JSON string from symbolization stage
            
        Returns:
            JSON string containing CNFResult
        """
        from src.pipeline import cnf as cnf_module
        from src.witty_types import AtomicClaim
        
        try:
            # Parse symbolizer result
            data = json.loads(symbolizer_result)
            
            # Build atomic claims list
            atomic_claims = [
                AtomicClaim(
                    text=ac.get("text", ""),
                    symbol=ac.get("symbol", f"P{i+1}"),
                    origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
                )
                for i, ac in enumerate(data.get("atomic_claims", []))
            ]
            
            legend = data.get("legend", {})
            structural_metadata = data.get("structural_metadata", {})
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Call CNF transform
            module_result = cnf_module.cnf_transform(
                claims=atomic_claims,
                legend=legend,
                structural_metadata=structural_metadata,
                salt=ctx.deterministic_salt
            )
            
            # Extract CNF result from payload
            cnf_payload = module_result.payload
            
            return json.dumps({
                "success": True,
                "cnf_string": cnf_payload.get("cnf_string", ""),
                "cnf_clauses": cnf_payload.get("cnf_clauses", []),
                "ast": cnf_payload.get("ast", {}),
                "confidence": module_result.confidence,
                "warnings": module_result.warnings
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "cnf_string": "",
                "cnf_clauses": [],
                "ast": {},
                "confidence": 0.0,
                "warnings": [f"CNF transformation failed: {str(e)}"]
            })


class ValidationTool(Tool):
    """
    Tool wrapper for validation pipeline stage.
    
    Validates the final formalization result, checking symbol coverage,
    provenance completeness, and detecting contradictions/tautologies.
    """
    
    name = "validate"
    description = """Validate the final formalization result. Checks symbol coverage, 
    provenance completeness, entity grounding, and detects contradictions/tautologies. 
    Returns ValidationReport with is_valid flag and any issues."""
    
    inputs = {
        "cnf_result": {
            "type": "string",
            "description": "JSON string from CNF transformation stage"
        },
        "symbolizer_result": {
            "type": "string",
            "description": "JSON string from symbolization stage",
            "nullable": True
        }
    }
    output_type = "string"  # JSON string of ValidationReport
    
    def __init__(self, ctx: Optional[AgentContext] = None):
        """
        Initialize the validation tool.
        
        Args:
            ctx: Optional pipeline context
        """
        super().__init__()
        self.ctx = ctx
    
    def forward(self, cnf_result: str, symbolizer_result: Optional[str] = None) -> str:
        """
        Execute validation on CNF result.
        
        Args:
            cnf_result: JSON string from CNF transformation stage
            symbolizer_result: Optional JSON string from symbolization
            
        Returns:
            JSON string containing ValidationReport
        """
        from src.pipeline import validation as val_module
        from src.witty_types import AtomicClaim
        
        try:
            # Parse CNF result
            cnf_data = json.loads(cnf_result)
            
            # Parse symbolizer result if provided
            if symbolizer_result:
                sym_data = json.loads(symbolizer_result)
            else:
                sym_data = {}
            
            # Build atomic claims
            atomic_claims = [
                AtomicClaim(
                    text=ac.get("text", ""),
                    symbol=ac.get("symbol", f"P{i+1}"),
                    origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
                )
                for i, ac in enumerate(sym_data.get("atomic_claims", []))
            ]
            
            legend = sym_data.get("legend", {})
            cnf_clauses = cnf_data.get("cnf_clauses", [])
            
            # Create context if not provided
            ctx = self.ctx or AgentContext(
                request_id="tool_request",
                options=FormalizeOptions(),
                reproducible_mode=True,
                deterministic_salt="sprint6"
            )
            
            # Call validation
            module_result = val_module.validate_formalization(
                atomic_claims=atomic_claims,
                legend=legend,
                cnf_clauses=cnf_clauses,
                provenance_records=[],
                entity_groundings=None,
                salt=ctx.deterministic_salt
            )
            
            # Extract validation result from payload
            val_payload = module_result.payload
            
            return json.dumps({
                "success": True,
                "is_valid": val_payload.get("is_valid", True),
                "issues": val_payload.get("issues", []),
                "symbol_coverage": val_payload.get("symbol_coverage", 1.0),
                "provenance_coverage": val_payload.get("provenance_coverage", 1.0),
                "human_review_required": val_payload.get("human_review_required", False),
                "confidence": module_result.confidence,
                "warnings": module_result.warnings
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "is_valid": False,
                "issues": [f"Validation failed: {str(e)}"],
                "symbol_coverage": 0.0,
                "provenance_coverage": 0.0,
                "human_review_required": True,
                "confidence": 0.0,
                "warnings": [f"Validation error: {str(e)}"]
            })


def create_pipeline_tools(
    ctx: Optional[AgentContext] = None,
    llm_adapter: Any = None,
    retrieval_adapter: Any = None
) -> List[Tool]:
    """
    Factory function to create all pipeline tools.
    
    Creates instances of all pipeline tool wrappers with shared context
    and adapters for consistent behavior.
    
    Args:
        ctx: Optional shared pipeline context
        llm_adapter: Optional shared LLM adapter
        retrieval_adapter: Optional shared retrieval adapter
        
    Returns:
        List of Tool instances for use with smolagents ToolCallingAgent
    """
    return [
        PreprocessTool(ctx=ctx),
        ConcisionTool(ctx=ctx, llm_adapter=llm_adapter),
        EnrichmentTool(ctx=ctx, llm_adapter=llm_adapter, retrieval_adapter=retrieval_adapter),
        ModalDetectionTool(ctx=ctx),
        WorldConstructionTool(ctx=ctx, llm_adapter=llm_adapter),
        SymbolizerTool(ctx=ctx),
        CNFTransformTool(ctx=ctx),
        ValidationTool(ctx=ctx),
    ]
