"""
Agentic Orchestrator for Witty Pipeline (Sprint 6).

Implements a tool-calling agent using HuggingFace smolagents framework.
The agent coordinates pipeline execution by deciding which tools to call,
handling retries on validation failures, and falling back to deterministic
implementations when LLM-assisted modules fail.

Key features:
- Uses smolagents ToolCallingAgent for tool invocation
- Supports both live LLM models and MockToolCallingModel for testing
- Implements retry/fallback policy with human_review flagging
- Aggregates provenance across all tool invocations
- Never executes arbitrary code - only registered tools

Author: Victor Rowello
Sprint: 6
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from src.witty_types import (
    ModuleResult,
    ProvenanceRecord,
    FormalizationResult,
    FormalizeOptions,
    AtomicClaim,
)
from src.pipeline.orchestrator import AgentContext, make_provenance_id
from src.pipeline.tools import create_pipeline_tools

logger = logging.getLogger(__name__)


@dataclass
class AgentPolicy:
    """
    Configuration for agent retry/fallback behavior.
    
    Attributes:
        max_retries: Maximum retries per tool before fallback
        confidence_threshold: Minimum confidence to accept a result
        fallback_on_error: Whether to use deterministic fallback on errors
        human_review_on_fallback: Flag human_review when fallback is used
    """
    max_retries: int = 1
    confidence_threshold: float = 0.7
    fallback_on_error: bool = True
    human_review_on_fallback: bool = True


@dataclass
class ToolInvocationRecord:
    """
    Record of a single tool invocation for provenance tracking.
    
    Attributes:
        tool_name: Name of the invoked tool
        arguments: Arguments passed to the tool
        result: Result returned by the tool (JSON string)
        success: Whether the invocation succeeded
        retries: Number of retries attempted
        used_fallback: Whether deterministic fallback was used
        timestamp: When the invocation occurred
        duration_ms: Execution time in milliseconds
    """
    tool_name: str
    arguments: Dict[str, Any]
    result: str
    success: bool
    retries: int = 0
    used_fallback: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = 0


class WittyPipelineAgent:
    """
    Agentic orchestrator for the Witty formalization pipeline.
    
    Uses smolagents ToolCallingAgent to coordinate pipeline execution.
    The agent decides which tools to call based on the input and previous
    results, implements retry logic for failed validations, and falls back
    to deterministic implementations when needed.
    
    Features:
    - Tool-calling agent architecture (never executes arbitrary code)
    - Configurable retry/fallback policies
    - Comprehensive provenance tracking
    - Support for both live LLMs and mock models
    
    Example:
        >>> agent = WittyPipelineAgent()
        >>> result = agent.run("If it rains then the match is cancelled.")
        >>> print(result.legend)
        {'P1': 'it rains', 'P2': 'the match is cancelled'}
    """
    
    def __init__(
        self,
        model: Any = None,
        ctx: Optional[AgentContext] = None,
        policy: Optional[AgentPolicy] = None,
        llm_adapter: Any = None,
        retrieval_adapter: Any = None
    ):
        """
        Initialize the pipeline agent.
        
        Args:
            model: smolagents-compatible model for tool selection.
                   If None, uses MockToolCallingModel for testing.
            ctx: Optional pipeline context with configuration
            policy: Optional retry/fallback policy configuration
            llm_adapter: Optional LLM adapter for pipeline tools
            retrieval_adapter: Optional retrieval adapter for enrichment
        """
        self.ctx = ctx
        self.policy = policy or AgentPolicy()
        self.llm_adapter = llm_adapter
        self.retrieval_adapter = retrieval_adapter
        
        # Initialize model (use mock if not provided)
        if model is None:
            from src.adapters.mock_agent_model import MockToolCallingModel
            self.model = MockToolCallingModel()
        else:
            self.model = model
        
        # Create pipeline tools
        self.tools = create_pipeline_tools(
            ctx=ctx,
            llm_adapter=llm_adapter,
            retrieval_adapter=retrieval_adapter
        )
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # Invocation history for provenance
        self.invocation_history: List[ToolInvocationRecord] = []
        
        # Track overall human_review flag
        self.human_review_required = False
    
    def _create_context(self, options: Optional[FormalizeOptions] = None) -> AgentContext:
        """
        Create an AgentContext for this run.
        
        Args:
            options: Optional formalization options
            
        Returns:
            Configured AgentContext
        """
        if self.ctx:
            return self.ctx
        
        timestamp = datetime.now(timezone.utc)
        request_id = f"agent_{timestamp.strftime('%Y%m%d%H%M%S')}"
        
        return AgentContext(
            request_id=request_id,
            options=options or FormalizeOptions(),
            reproducible_mode=True,
            deterministic_salt="sprint6_agent"
        )
    
    def _invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        allow_retry: bool = True
    ) -> str:
        """
        Invoke a pipeline tool with retry/fallback handling.
        
        Args:
            tool_name: Name of the tool to invoke
            arguments: Arguments to pass to the tool
            allow_retry: Whether to allow retries on failure
            
        Returns:
            JSON string result from the tool
        """
        if tool_name not in self.tool_map:
            return json.dumps({
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "warnings": [f"Tool '{tool_name}' not found"]
            })
        
        tool = self.tool_map[tool_name]
        start_time = datetime.now(timezone.utc)
        retries = 0
        result = ""
        success = False
        used_fallback = False
        
        while retries <= self.policy.max_retries:
            try:
                # Invoke the tool
                result = tool.forward(**arguments)
                result_data = json.loads(result)
                
                # Check if successful
                if result_data.get("success", True):
                    # Check confidence threshold
                    confidence = result_data.get("confidence", 1.0)
                    if confidence >= self.policy.confidence_threshold:
                        success = True
                        break
                    else:
                        logger.warning(
                            f"Tool {tool_name} returned low confidence {confidence}, "
                            f"threshold is {self.policy.confidence_threshold}"
                        )
                
                # Retry if allowed
                if allow_retry and retries < self.policy.max_retries:
                    retries += 1
                    logger.info(f"Retrying {tool_name} (attempt {retries + 1})")
                    continue
                
                break
                
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                result = json.dumps({
                    "success": False,
                    "error": str(e),
                    "warnings": [f"Tool execution failed: {str(e)}"]
                })
                
                if allow_retry and retries < self.policy.max_retries:
                    retries += 1
                    continue
                break
        
        # If still not successful, try deterministic fallback
        if not success and self.policy.fallback_on_error:
            fallback_tool_name = f"{tool_name}_deterministic"
            if fallback_tool_name in self.tool_map:
                logger.info(f"Using deterministic fallback for {tool_name}")
                try:
                    result = self.tool_map[fallback_tool_name].forward(**arguments)
                    used_fallback = True
                    success = True
                    
                    if self.policy.human_review_on_fallback:
                        self.human_review_required = True
                except Exception as e:
                    logger.error(f"Fallback {fallback_tool_name} failed: {e}")
        
        # Record invocation
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        self.invocation_history.append(ToolInvocationRecord(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            success=success,
            retries=retries,
            used_fallback=used_fallback,
            timestamp=start_time,
            duration_ms=duration_ms
        ))
        
        return result
    
    def _run_sequential_pipeline(
        self,
        input_text: str,
        options: FormalizeOptions
    ) -> Dict[str, Any]:
        """
        Run the pipeline sequentially without agent decision-making.
        
        This is a fallback mode that executes the standard pipeline
        sequence without LLM-based tool selection.
        
        Args:
            input_text: Natural language text to formalize
            options: Formalization options
            
        Returns:
            Dictionary with all pipeline results
        """
        results: Dict[str, Any] = {}
        
        # Stage 1: Preprocess
        prep_result = self._invoke_tool("preprocess", {"text": input_text})
        results["preprocessing"] = json.loads(prep_result)
        
        if not results["preprocessing"].get("success"):
            return results
        
        # Stage 2: Concision
        conc_result = self._invoke_tool("concision", {
            "preprocessing_result": prep_result,
            "use_llm": not options.reproducible_mode
        })
        results["concision"] = json.loads(conc_result)
        
        if not results["concision"].get("success"):
            return results
        
        # Stage 3: Enrichment - agent decides unless user opts out
        # Priority: 1) User opted out with no_retrieval=True -> skip
        #           2) User forced with retrieval_enabled=True -> enrich
        #           3) Agent decides based on content analysis
        should_enrich = False
        enrichment_reason = None
        
        if getattr(options, 'no_retrieval', False):
            # User explicitly opted out
            should_enrich = False
            enrichment_reason = "disabled_by_user"
            logger.debug("Enrichment skipped: user set no_retrieval=True")
        elif getattr(options, 'retrieval_enabled', False):
            # User explicitly requested enrichment
            should_enrich = True
            enrichment_reason = "user_requested"
            logger.debug("Enrichment enabled: user set retrieval_enabled=True")
        else:
            # Agent decides based on content
            should_enrich = self._needs_enrichment(conc_result, results.get("preprocessing", {}).get("normalized_text", ""))
            enrichment_reason = "agent_decision" if should_enrich else "not_needed"
            if should_enrich:
                logger.info("Agent decided enrichment would improve results")
        
        if should_enrich:
            enrich_result = self._invoke_tool("enrich", {
                "concision_result": conc_result,
                "retrieval_enabled": True
            })
            results["enrichment"] = json.loads(enrich_result)
            results["enrichment"]["reason"] = enrichment_reason
            next_input = enrich_result
        else:
            results["enrichment"] = {"skipped": True, "reason": enrichment_reason}
            next_input = conc_result
        
        # Stage 4: Modal Detection
        modal_result = self._invoke_tool("detect_modal", {
            "input_result": next_input
        })
        results["modal"] = json.loads(modal_result)
        
        # Stage 5: World Construction (if modality detected or quantifiers present)
        has_modality = results["modal"].get("has_modality", False)
        has_quantifiers = self._check_for_quantifiers(next_input)
        
        if has_modality or has_quantifiers:
            world_result = self._invoke_tool("world_construct", {
                "input_result": next_input,
                "modal_result": modal_result
            })
            results["world"] = json.loads(world_result)
            sym_input = world_result
        else:
            sym_input = next_input
        
        # Stage 6: Symbolization
        sym_result = self._invoke_tool("symbolize", {
            "input_result": sym_input
        })
        results["symbolizer"] = json.loads(sym_result)
        
        if not results["symbolizer"].get("success"):
            return results
        
        # Stage 7: CNF Transform
        cnf_result = self._invoke_tool("cnf_transform", {
            "symbolizer_result": sym_result
        })
        results["cnf"] = json.loads(cnf_result)
        
        # Stage 8: Validation
        val_result = self._invoke_tool("validate", {
            "cnf_result": cnf_result,
            "symbolizer_result": sym_result
        })
        results["validation"] = json.loads(val_result)
        
        return results
    
    def _check_for_quantifiers(self, result_json: str) -> bool:
        """
        Check if the result contains quantified claims.
        
        Args:
            result_json: JSON string result from previous stage
            
        Returns:
            True if quantifiers are detected
        """
        try:
            data = json.loads(result_json)
            claims = data.get("atomic_candidates", data.get("expanded_claims", []))
            
            quantifier_words = ["all", "every", "each", "some", "any", "no", "none"]
            
            for claim in claims:
                text = claim.get("text", "").lower()
                if any(q in text for q in quantifier_words):
                    return True
            
            return False
        except Exception:
            return False
    
    def _needs_enrichment(self, result_json: str, original_text: str) -> bool:
        """
        Determine if the input would benefit from external retrieval/enrichment.
        
        The agent uses heuristics to decide when additional context would help:
        1. Quantifiers over domains (e.g., "all mammals", "every prime number")
        2. Proper nouns / named entities that may need grounding
        3. Technical terms or domain-specific vocabulary
        4. References to facts, dates, or verifiable claims
        5. Underspecified entities ("the president", "that country")
        
        Args:
            result_json: JSON string from concision stage
            original_text: The original input text
            
        Returns:
            True if enrichment would likely improve formalization quality
        """
        try:
            text_lower = original_text.lower()
            
            # 1. Quantifiers over concrete domains (not just logical quantifiers)
            domain_quantifiers = [
                r'\ball\s+\w+s\b',  # "all mammals", "all numbers"
                r'\bevery\s+\w+\b',  # "every person", "every element"
                r'\bsome\s+\w+s\b',  # "some animals", "some cases"
                r'\bno\s+\w+s?\b',   # "no exceptions", "no bird"
            ]
            import re
            for pattern in domain_quantifiers:
                if re.search(pattern, text_lower):
                    logger.debug(f"Enrichment triggered: domain quantifier pattern '{pattern}'")
                    return True
            
            # 2. Factual/verifiable claims (dates, statistics, comparisons)
            factual_indicators = [
                r'\b\d{4}\b',  # Years like 2024
                r'\b\d+\s*%',  # Percentages
                r'\baccording to\b',
                r'\bstudies show\b',
                r'\bresearch\b',
                r'\bstatistic\w*\b',
                r'\blargest\b|\bsmallest\b|\bfastest\b|\bmost\b',
                r'\bcapital of\b',
                r'\bpresident of\b',
                r'\bfounder of\b',
            ]
            for pattern in factual_indicators:
                if re.search(pattern, text_lower):
                    logger.debug(f"Enrichment triggered: factual indicator '{pattern}'")
                    return True
            
            # 3. Parse the concision result for entity-rich claims
            data = json.loads(result_json)
            claims = data.get("atomic_candidates", data.get("expanded_claims", []))
            
            # Check for proper nouns (capitalized words that aren't sentence starters)
            for claim in claims:
                claim_text = claim.get("text", "")
                words = claim_text.split()
                # Skip first word (might just be capitalized sentence start)
                for word in words[1:]:
                    if word and word[0].isupper() and word.isalpha() and len(word) > 2:
                        logger.debug(f"Enrichment triggered: proper noun '{word}'")
                        return True
            
            # 4. Underspecified references
            underspecified = [
                r'\bthe\s+(current|former|new|old)\s+\w+\b',
                r'\bthat\s+(country|person|company|organization)\b',
                r'\bthis\s+(year|month|week|day)\b',
            ]
            for pattern in underspecified:
                if re.search(pattern, text_lower):
                    logger.debug(f"Enrichment triggered: underspecified reference '{pattern}'")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error in _needs_enrichment: {e}")
            return False
    
    def _build_formalization_result(
        self,
        input_text: str,
        pipeline_results: Dict[str, Any],
        ctx: AgentContext
    ) -> FormalizationResult:
        """
        Build the final FormalizationResult from pipeline results.
        
        Args:
            input_text: Original input text
            pipeline_results: Results from all pipeline stages
            ctx: Pipeline context
            
        Returns:
            Complete FormalizationResult
        """
        # Extract results from pipeline
        sym_result = pipeline_results.get("symbolizer", {})
        cnf_result = pipeline_results.get("cnf", {})
        val_result = pipeline_results.get("validation", {})
        conc_result = pipeline_results.get("concision", {})
        
        # Build atomic claims
        atomic_claims = []
        for ac in sym_result.get("atomic_claims", []):
            claim = AtomicClaim(
                text=ac.get("text", ""),
                symbol=ac.get("symbol", ""),
                origin_spans=[tuple(s) for s in ac.get("origin_spans", [])]
            )
            atomic_claims.append(claim)
        
        # Build legend
        legend = sym_result.get("legend", {})
        
        # Build logical form candidates
        logical_form_candidates = []
        if legend:
            notation = " ∧ ".join([
                f"{sym}:{text[:30]}..." if len(text) > 30 else f"{sym}:{text}"
                for sym, text in legend.items()
            ])
            logical_form_candidates.append({
                "ast": {},
                "notation": notation,
                "confidence": sym_result.get("confidence", 1.0)
            })
        
        # Calculate overall confidence
        confidences = [
            conc_result.get("confidence", 1.0),
            sym_result.get("confidence", 1.0),
            cnf_result.get("confidence", 1.0)
        ]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 1.0
        
        # Collect warnings
        warnings = []
        for stage_name, stage_result in pipeline_results.items():
            warnings.extend(stage_result.get("warnings", []))
        
        if self.human_review_required:
            warnings.append("Human review recommended: deterministic fallback was used")
        
        # Build provenance from invocation history
        provenance = []
        for inv in self.invocation_history:
            prov = ProvenanceRecord(
                id=make_provenance_id(
                    input_text, inv.tool_name, "agent_v1", ctx.deterministic_salt
                ),
                created_at=inv.timestamp,
                module_id=inv.tool_name,
                module_version="agent_v1",
                adapter_id="agent",
                confidence=1.0 if inv.success else 0.5,
                event_log=[{
                    "ts": inv.timestamp.isoformat(),
                    "event_type": "tool_invocation",
                    "message": f"Tool {inv.tool_name} {'succeeded' if inv.success else 'failed'}",
                    "meta": {
                        "retries": inv.retries,
                        "used_fallback": inv.used_fallback,
                        "duration_ms": inv.duration_ms
                    }
                }]
            )
            provenance.append(prov)
        
        # Build result
        result = FormalizationResult.model_validate({
            "request_id": ctx.request_id,
            "original_text": input_text,
            "canonical_text": conc_result.get("canonical_text", input_text),
            "atomic_claims": [claim.model_dump() for claim in atomic_claims],
            "legend": legend,
            "logical_form_candidates": logical_form_candidates,
            "chosen_logical_form": logical_form_candidates[0] if logical_form_candidates else None,
            "cnf": cnf_result.get("cnf_string", ""),
            "cnf_clauses": cnf_result.get("cnf_clauses", []),
            "confidence": overall_confidence,
            "provenance": [prov.model_dump() for prov in provenance],
            "warnings": warnings,
            "config_metadata": ctx.options.model_dump()
        })
        
        return result
    
    def run(
        self,
        input_text: str,
        options: Optional[FormalizeOptions] = None
    ) -> FormalizationResult:
        """
        Run the agentic pipeline on input text.
        
        Coordinates pipeline execution using the tool-calling agent.
        The agent decides which tools to invoke based on the input
        and handles retries/fallbacks according to policy.
        
        Args:
            input_text: Natural language statement to formalize
            options: Optional formalization options
            
        Returns:
            FormalizationResult with symbols, legend, CNF, and provenance
            
        Example:
            >>> agent = WittyPipelineAgent()
            >>> result = agent.run("Every employee must attend the meeting.")
            >>> print(result.legend)
            >>> print(result.cnf)
        """
        # Reset state for new run
        self.invocation_history = []
        self.human_review_required = False
        
        # Create context
        options = options or FormalizeOptions()
        ctx = self._create_context(options)
        
        # Reset mock model if using one
        if hasattr(self.model, 'reset'):
            self.model.reset()
        
        # Run sequential pipeline (agent decision-making to be added)
        # In future, this will use self.model to decide tool order
        pipeline_results = self._run_sequential_pipeline(input_text, options)
        
        # Build final result
        result = self._build_formalization_result(input_text, pipeline_results, ctx)
        
        return result
    
    def run_with_agent_loop(
        self,
        input_text: str,
        options: Optional[FormalizeOptions] = None,
        max_steps: int = 20
    ) -> FormalizationResult:
        """
        Run the pipeline using the full agent loop with LLM decisions.
        
        This method uses the model to decide which tools to call at each
        step, rather than following a fixed sequence. Useful for testing
        the agent's decision-making capabilities.
        
        Args:
            input_text: Natural language statement to formalize
            options: Optional formalization options
            max_steps: Maximum number of agent steps
            
        Returns:
            FormalizationResult from agent execution
        """
        # Reset state
        self.invocation_history = []
        self.human_review_required = False
        
        options = options or FormalizeOptions()
        ctx = self._create_context(options)
        
        # Reset mock model
        if hasattr(self.model, 'reset'):
            self.model.reset()
        
        # Build conversation for agent
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt()
            },
            {
                "role": "user",
                "content": f"Formalize the following statement: {input_text}"
            }
        ]
        
        # Track results from each tool call
        pipeline_results: Dict[str, Any] = {}
        last_result = ""
        
        for step in range(max_steps):
            # Get model response
            response = self.model(
                messages=messages,
                tools=self.tools,
                stop_sequences=["Observation:"]
            )
            
            # Check if final answer
            if "Final Answer:" in response:
                break
            
            # Parse tool call
            from src.adapters.mock_agent_model import parse_tool_call_from_response
            tool_call = parse_tool_call_from_response(response)
            
            if not tool_call:
                logger.warning(f"Could not parse tool call from: {response[:100]}")
                break
            
            # Resolve placeholder arguments
            args = self._resolve_arguments(
                tool_call["arguments"],
                input_text,
                last_result
            )
            
            # Invoke tool
            result = self._invoke_tool(tool_call["tool_name"], args)
            last_result = result
            
            # Store result
            pipeline_results[tool_call["tool_name"]] = json.loads(result)
            
            # Add observation to messages
            messages.append({
                "role": "assistant",
                "content": response
            })
            messages.append({
                "role": "user",
                "content": f"Observation: {result[:500]}"  # Truncate for context
            })
        
        # Ensure we have minimum required results
        if "symbolizer" not in pipeline_results:
            # Run sequential fallback
            pipeline_results = self._run_sequential_pipeline(input_text, options)
        
        return self._build_formalization_result(input_text, pipeline_results, ctx)
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        return f"""You are a logical formalization agent. Your task is to convert natural 
language statements into formal logical representations.

Available tools:
{tool_descriptions}

Pipeline sequence:
1. preprocess - Always start here to segment and tokenize input
2. concision - Extract atomic claims from preprocessed text
3. enrich (optional) - Add external knowledge if entities are underspecified
4. detect_modal - Check for modal operators (must, should, possible)
5. world_construct - Build world model if modality or quantifiers detected
6. symbolize - Assign P1, P2, ... symbols to claims
7. cnf_transform - Convert to conjunctive normal form
8. validate - Check final result for completeness

Use the result of each tool as input to the next. When a tool fails validation,
retry once with corrected input. If retry fails, the system will use a 
deterministic fallback.

Always complete the full pipeline from preprocess to validate."""
    
    def _resolve_arguments(
        self,
        arguments: Dict[str, Any],
        input_text: str,
        last_result: str
    ) -> Dict[str, Any]:
        """
        Resolve placeholder values in arguments.
        
        Args:
            arguments: Raw arguments with potential placeholders
            input_text: Original input text
            last_result: Result from previous tool
            
        Returns:
            Arguments with placeholders resolved
        """
        resolved = {}
        
        for key, value in arguments.items():
            if isinstance(value, str):
                if value == "{input_text}":
                    resolved[key] = input_text
                elif value == "{prev_result}":
                    resolved[key] = last_result
                elif value.startswith("{") and value.endswith("}"):
                    # Other placeholders - use last_result
                    resolved[key] = last_result
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved
    
    def get_invocation_history(self) -> List[Dict[str, Any]]:
        """
        Get the history of all tool invocations.
        
        Returns:
            List of invocation records as dictionaries
        """
        return [
            {
                "tool_name": inv.tool_name,
                "success": inv.success,
                "retries": inv.retries,
                "used_fallback": inv.used_fallback,
                "duration_ms": inv.duration_ms,
                "timestamp": inv.timestamp.isoformat()
            }
            for inv in self.invocation_history
        ]


def formalize_with_agent(
    input_text: str,
    options: Optional[FormalizeOptions] = None,
    model: Any = None
) -> FormalizationResult:
    """
    Convenience function to formalize using the agent orchestrator.
    
    Creates a WittyPipelineAgent and runs formalization on the input.
    By default, creates an LLM adapter (Groq) for live formalization.
    Pass options with reproducible_mode=True for deterministic behavior.
    
    Args:
        input_text: Natural language statement to formalize
        options: Optional formalization options
        model: Optional smolagents-compatible model
        
    Returns:
        FormalizationResult with complete formalization
        
    Example:
        >>> result = formalize_with_agent("If it rains then the match is cancelled.")
        >>> print(result.legend)
    """
    if options is None:
        options = FormalizeOptions()
    
    # Create LLM adapter for live mode (not reproducible)
    llm_adapter = None
    if not getattr(options, 'reproducible_mode', False):
        try:
            from src.adapters.groq_adapter import GroqAdapter
            model_name = getattr(options, 'llm_model', None) or "llama-3.3-70b-versatile"
            llm_adapter = GroqAdapter(model=model_name)
            logger.info(f"Live mode: Created Groq adapter with {model_name}")
        except Exception as e:
            logger.warning(f"Failed to create Groq adapter, falling back to deterministic: {e}")
    
    agent = WittyPipelineAgent(model=model, llm_adapter=llm_adapter)
    return agent.run(input_text, options)
