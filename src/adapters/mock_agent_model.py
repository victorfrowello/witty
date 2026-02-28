"""
Mock Tool-Calling Model for smolagents Framework.

Provides a deterministic mock model that returns predetermined tool calls
in the exact format expected by smolagents ToolCallingAgent. This enables
comprehensive testing of the agentic orchestrator without requiring a real LLM.

The mock model returns responses in smolagents' native format:
- Thought: <reasoning about next step>
- Action: <tool_name>
- Action Input: <JSON args>

This approach tests the actual smolagents framework plumbing while only mocking
the LLM's decision-making, ensuring Sprint 7's live LLM swap is minimal.

Author: Victor Rowello
Sprint: 6
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Union
from dataclasses import dataclass, field


@dataclass
class MockToolCall:
    """
    Represents a single tool call to be returned by the mock model.
    
    Attributes:
        tool_name: Name of the tool to invoke
        arguments: Dictionary of arguments to pass to the tool
        thought: Optional reasoning text for this step
    """
    tool_name: str
    arguments: Dict[str, Any]
    thought: str = "Executing next pipeline step"


@dataclass
class MockScenario:
    """
    Defines a complete scenario of tool calls for the mock model.
    
    A scenario represents a full pipeline execution path with ordered tool calls.
    The mock model will return these tool calls in sequence when invoked.
    
    Attributes:
        name: Human-readable name for this scenario
        tool_calls: Ordered list of tool calls to return
        final_answer: The final answer to return after all tools complete
    """
    name: str
    tool_calls: List[MockToolCall]
    final_answer: str = "Pipeline execution complete"


# Predefined scenarios for common pipeline paths
PIPELINE_SCENARIOS: Dict[str, MockScenario] = {
    "simple_statement": MockScenario(
        name="simple_statement",
        tool_calls=[
            MockToolCall(
                tool_name="preprocess",
                arguments={"text": "{input_text}"},
                thought="First, I need to preprocess the input text to segment and tokenize it."
            ),
            MockToolCall(
                tool_name="concision",
                arguments={"preprocessing_result": "{prev_result}"},
                thought="Now I'll extract atomic claims from the preprocessed text."
            ),
            MockToolCall(
                tool_name="symbolize",
                arguments={"concision_result": "{prev_result}"},
                thought="Assigning symbols to the atomic claims."
            ),
            MockToolCall(
                tool_name="cnf_transform",
                arguments={"symbolizer_result": "{prev_result}"},
                thought="Converting to conjunctive normal form."
            ),
            MockToolCall(
                tool_name="validate",
                arguments={"cnf_result": "{prev_result}"},
                thought="Validating the final formalization result."
            ),
        ],
        final_answer="Successfully formalized the statement."
    ),
    
    "with_enrichment": MockScenario(
        name="with_enrichment",
        tool_calls=[
            MockToolCall(
                tool_name="preprocess",
                arguments={"text": "{input_text}"},
                thought="Starting with preprocessing the input."
            ),
            MockToolCall(
                tool_name="concision",
                arguments={"preprocessing_result": "{prev_result}"},
                thought="Extracting atomic claims from preprocessed text."
            ),
            MockToolCall(
                tool_name="enrich",
                arguments={"concision_result": "{prev_result}"},
                thought="The statement mentions underspecified entities. I need to enrich with context."
            ),
            MockToolCall(
                tool_name="detect_modal",
                arguments={"enrichment_result": "{prev_result}"},
                thought="Checking for modal operators in the claims."
            ),
            MockToolCall(
                tool_name="world_construct",
                arguments={"enrichment_result": "{prev_result}", "modal_result": "{modal_result}"},
                thought="Constructing the world model with grounded entities."
            ),
            MockToolCall(
                tool_name="symbolize",
                arguments={"world_result": "{prev_result}"},
                thought="Assigning symbols to the world-constructed claims."
            ),
            MockToolCall(
                tool_name="cnf_transform",
                arguments={"symbolizer_result": "{prev_result}"},
                thought="Converting to CNF."
            ),
            MockToolCall(
                tool_name="validate",
                arguments={"cnf_result": "{prev_result}"},
                thought="Final validation."
            ),
        ],
        final_answer="Successfully formalized with enrichment."
    ),
    
    "with_modal": MockScenario(
        name="with_modal",
        tool_calls=[
            MockToolCall(
                tool_name="preprocess",
                arguments={"text": "{input_text}"},
                thought="Preprocessing the modal statement."
            ),
            MockToolCall(
                tool_name="concision",
                arguments={"preprocessing_result": "{prev_result}"},
                thought="Extracting atomic claims."
            ),
            MockToolCall(
                tool_name="detect_modal",
                arguments={"concision_result": "{prev_result}"},
                thought="The statement contains modal language. Detecting modal operators."
            ),
            MockToolCall(
                tool_name="world_construct",
                arguments={"concision_result": "{prev_result}", "modal_result": "{modal_result}"},
                thought="Building world model with modal context."
            ),
            MockToolCall(
                tool_name="symbolize",
                arguments={"world_result": "{prev_result}"},
                thought="Symbolizing the claims."
            ),
            MockToolCall(
                tool_name="cnf_transform",
                arguments={"symbolizer_result": "{prev_result}"},
                thought="CNF transformation with modal wrappers."
            ),
            MockToolCall(
                tool_name="validate",
                arguments={"cnf_result": "{prev_result}"},
                thought="Validating modal formalization."
            ),
        ],
        final_answer="Successfully formalized modal statement."
    ),
    
    "retry_fallback": MockScenario(
        name="retry_fallback",
        tool_calls=[
            MockToolCall(
                tool_name="preprocess",
                arguments={"text": "{input_text}"},
                thought="Preprocessing input."
            ),
            MockToolCall(
                tool_name="concision",
                arguments={"preprocessing_result": "{prev_result}"},
                thought="Attempting LLM concision."
            ),
            # This scenario simulates the agent detecting a failure and retrying
            MockToolCall(
                tool_name="concision",
                arguments={"preprocessing_result": "{prev_result}", "retry": True},
                thought="Concision failed validation. Retrying with augmented prompt."
            ),
            # After retry fails, agent falls back to deterministic
            MockToolCall(
                tool_name="concision_deterministic",
                arguments={"preprocessing_result": "{prev_result}"},
                thought="Retry also failed. Using deterministic fallback."
            ),
            MockToolCall(
                tool_name="symbolize",
                arguments={"concision_result": "{prev_result}"},
                thought="Continuing with symbolization."
            ),
            MockToolCall(
                tool_name="cnf_transform",
                arguments={"symbolizer_result": "{prev_result}"},
                thought="CNF transformation."
            ),
            MockToolCall(
                tool_name="validate",
                arguments={"cnf_result": "{prev_result}"},
                thought="Final validation (flagging human review due to fallback)."
            ),
        ],
        final_answer="Formalized with deterministic fallback. Human review recommended."
    ),
}


class MockToolCallingModel:
    """
    Mock model that returns predetermined tool calls in smolagents format.
    
    This model simulates LLM behavior for testing the agentic orchestrator.
    It returns tool calls in the exact format smolagents expects, allowing
    comprehensive testing of the framework without a real LLM.
    
    Format returned:
        Thought: <reasoning>
        Action: <tool_name>
        Action Input: <JSON arguments>
    
    Or for final answer:
        Thought: <reasoning>
        Final Answer: <result>
    
    Attributes:
        scenario: The MockScenario defining tool call sequence
        call_index: Current position in the tool call sequence
        model_id: Identifier for this mock model
        history: Log of all calls made to this model
    """
    
    def __init__(
        self,
        scenario: Optional[Union[str, MockScenario]] = None,
        model_id: str = "mock_tool_calling_model"
    ) -> None:
        """
        Initialize the mock model.
        
        Args:
            scenario: Either a scenario name (string) or MockScenario instance.
                     Defaults to "simple_statement" if not provided.
            model_id: Identifier for provenance tracking
        """
        if scenario is None:
            self.scenario = PIPELINE_SCENARIOS["simple_statement"]
        elif isinstance(scenario, str):
            if scenario not in PIPELINE_SCENARIOS:
                raise ValueError(f"Unknown scenario: {scenario}. "
                               f"Available: {list(PIPELINE_SCENARIOS.keys())}")
            self.scenario = PIPELINE_SCENARIOS[scenario]
        else:
            self.scenario = scenario
        
        self.model_id = model_id
        self.call_index = 0
        self.history: List[Dict[str, Any]] = []
    
    def reset(self) -> None:
        """Reset the model to the beginning of the scenario."""
        self.call_index = 0
        self.history = []
    
    def __call__(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Any]] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate the next tool call or final answer.
        
        This method is called by smolagents ToolCallingAgent to get the model's
        response. It returns either a tool call in the expected format or the
        final answer when all tools have been called.
        
        Args:
            messages: List of message dicts (system, user, assistant roles)
            tools: List of available tools (used for validation)
            stop_sequences: Stop sequences (ignored in mock)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            String in smolagents format:
            - Tool call: "Thought: ... Action: ... Action Input: ..."
            - Final: "Thought: ... Final Answer: ..."
        """
        # Log this call
        self.history.append({
            "call_index": self.call_index,
            "messages_count": len(messages),
            "tools_provided": [t.name for t in tools] if tools else []
        })
        
        # Check if we've completed all tool calls
        if self.call_index >= len(self.scenario.tool_calls):
            return self._format_final_answer()
        
        # Get the next tool call
        tool_call = self.scenario.tool_calls[self.call_index]
        self.call_index += 1
        
        return self._format_tool_call(tool_call)
    
    def _format_tool_call(self, tool_call: MockToolCall) -> str:
        """
        Format a tool call in smolagents' expected format.
        
        Args:
            tool_call: The MockToolCall to format
            
        Returns:
            Formatted string with Thought, Action, and Action Input
        """
        # Format arguments as JSON
        args_json = json.dumps(tool_call.arguments, indent=2)
        
        return f"""Thought: {tool_call.thought}
Action: {tool_call.tool_name}
Action Input: {args_json}"""
    
    def _format_final_answer(self) -> str:
        """
        Format the final answer in smolagents' expected format.
        
        Returns:
            Formatted string with Thought and Final Answer
        """
        return f"""Thought: All pipeline steps completed successfully.
Final Answer: {self.scenario.final_answer}"""
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """
        Get the history of all calls made to this model.
        
        Returns:
            List of call records with index, message count, and tools
        """
        return self.history.copy()
    
    def get_current_step(self) -> int:
        """
        Get the current step index in the scenario.
        
        Returns:
            Current call index (0-based)
        """
        return self.call_index
    
    def is_complete(self) -> bool:
        """
        Check if the scenario has completed all tool calls.
        
        Returns:
            True if all tool calls have been made
        """
        return self.call_index >= len(self.scenario.tool_calls)


def create_mock_model_for_input(input_text: str) -> MockToolCallingModel:
    """
    Factory function to create an appropriate mock model based on input.
    
    Analyzes the input text and selects the most appropriate scenario.
    This enables more realistic testing by simulating the agent's decision
    to use different pipeline paths.
    
    Args:
        input_text: The input text to analyze
        
    Returns:
        MockToolCallingModel configured with the appropriate scenario
    """
    text_lower = input_text.lower()
    
    # Check for modal indicators
    modal_keywords = ["must", "should", "ought", "possible", "necessary", "might", "may"]
    has_modal = any(kw in text_lower for kw in modal_keywords)
    
    # Check for enrichment indicators (underspecified entities)
    enrichment_keywords = ["the prototype", "the system", "it", "they", "this"]
    needs_enrichment = any(kw in text_lower for kw in enrichment_keywords)
    
    # Select scenario
    if needs_enrichment:
        return MockToolCallingModel(scenario="with_enrichment")
    elif has_modal:
        return MockToolCallingModel(scenario="with_modal")
    else:
        return MockToolCallingModel(scenario="simple_statement")


def create_custom_scenario(tool_sequence: List[Dict[str, Any]], name: str = "custom") -> MockScenario:
    """
    Create a custom scenario from a list of tool call definitions.
    
    Allows tests to define specific tool call sequences for edge cases.
    
    Args:
        tool_sequence: List of dicts with 'tool_name', 'arguments', and optional 'thought'
        name: Name for the scenario
        
    Returns:
        MockScenario with the specified tool calls
        
    Example:
        >>> scenario = create_custom_scenario([
        ...     {"tool_name": "preprocess", "arguments": {"text": "test"}},
        ...     {"tool_name": "concision", "arguments": {"result": "..."}}
        ... ])
        >>> model = MockToolCallingModel(scenario=scenario)
    """
    tool_calls = [
        MockToolCall(
            tool_name=tc["tool_name"],
            arguments=tc.get("arguments", {}),
            thought=tc.get("thought", f"Executing {tc['tool_name']}")
        )
        for tc in tool_sequence
    ]
    
    return MockScenario(
        name=name,
        tool_calls=tool_calls,
        final_answer="Custom scenario complete"
    )


class MockMessageContent:
    """
    Mock message content class for smolagents compatibility.
    
    smolagents expects message content to have specific attributes.
    This class provides the minimal interface needed for testing.
    """
    
    def __init__(self, content: str):
        self.content = content
    
    def __str__(self) -> str:
        return self.content


def validate_smolagents_format(response: str) -> bool:
    """
    Validate that a response is in correct smolagents format.
    
    Checks for either:
    - Tool call format: Thought + Action + Action Input
    - Final answer format: Thought + Final Answer
    
    Args:
        response: The response string to validate
        
    Returns:
        True if the response is valid smolagents format
    """
    # Check for final answer format
    if "Final Answer:" in response:
        return "Thought:" in response
    
    # Check for tool call format
    has_thought = "Thought:" in response
    has_action = "Action:" in response
    has_action_input = "Action Input:" in response
    
    return has_thought and has_action and has_action_input


def parse_tool_call_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse a tool call from a smolagents format response.
    
    Extracts the tool name and arguments from a response string.
    
    Args:
        response: Response in smolagents format
        
    Returns:
        Dict with 'tool_name' and 'arguments', or None if not a tool call
    """
    if "Final Answer:" in response:
        return None
    
    # Extract tool name
    action_match = re.search(r'Action:\s*(\w+)', response)
    if not action_match:
        return None
    tool_name = action_match.group(1)
    
    # Extract arguments
    input_match = re.search(r'Action Input:\s*(.+)', response, re.DOTALL)
    if not input_match:
        return {"tool_name": tool_name, "arguments": {}}
    
    args_str = input_match.group(1).strip()
    try:
        arguments = json.loads(args_str)
    except json.JSONDecodeError:
        arguments = {"raw": args_str}
    
    return {"tool_name": tool_name, "arguments": arguments}
