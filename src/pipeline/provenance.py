"""
Provenance Utilities Module for Witty Pipeline.

This module provides utilities for deterministic ID generation, event logging,
and privacy redaction of provenance records. Ensures transparency, reproducibility,
and compliance with privacy requirements.

Key Features:
- Deterministic provenance ID generation using SHA256
- Event log formatting utilities
- Privacy mode redaction for sensitive data
- Standardized event types and structures

Author: Victor Rowello
Sprint: 2, Task: 5
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime, timezone

from src.witty_types import ProvenanceRecord


def make_provenance_id(
    normalized_input: str,
    module_id: str,
    module_version: str,
    salt: str
) -> str:
    """
    Generate a deterministic provenance ID using SHA256 hashing.
    
    Creates a stable, reproducible ID for provenance tracking. Same inputs
    always produce the same ID, ensuring reproducibility across runs.
    
    Args:
        normalized_input: Normalized input text for this processing step
        module_id: Identifier of the module creating this record
        module_version: Version of the module for reproducibility
        salt: Deterministic salt from AgentContext
        
    Returns:
        Provenance ID string in format "pr_{hash[:12]}"
        
    Examples:
        >>> make_provenance_id(
        ...     "if it rains then match cancelled",
        ...     "concision",
        ...     "1.0.0",
        ...     "test_salt"
        ... )
        'pr_a1b2c3d4e5f6'
        
    Algorithm:
        1. Combine: normalized_input + module_id + module_version + salt
        2. Hash with SHA256
        3. Return: "pr_{hash[:12]}"
        
    Note:
        The 12-character hash provides ~2^48 unique IDs (281 trillion),
        which is sufficient for provenance tracking while keeping IDs
        human-readable and manageable.
    """
    # Construct payload for hashing
    payload = f"{normalized_input}\n{module_id}\n{module_version}\n{salt}"
    
    # Hash with SHA256
    hash_obj = hashlib.sha256(payload.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    
    # Take first 12 characters of hash
    hash_prefix = hash_hex[:12]
    
    # Format: pr_{hash}
    provenance_id = f"pr_{hash_prefix}"
    
    return provenance_id


def log_adapter_call(
    event_log: List[Dict[str, Any]],
    adapter_id: str,
    request_id: str,
    additional_meta: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an adapter invocation event to the event log.
    
    Records when an LLM adapter or external service is called, capturing
    the adapter ID and request ID for debugging and reproducibility.
    
    Args:
        event_log: Event log list to append to (modified in place)
        adapter_id: Identifier of the adapter being called
        request_id: Unique request ID from the adapter
        additional_meta: Optional additional metadata to include
        
    Example:
        >>> event_log = []
        >>> log_adapter_call(event_log, "openai_gpt4", "req_abc123")
        >>> assert len(event_log) == 1
        >>> assert event_log[0]['event_type'] == 'invoke_adapter'
    
    Note:
        This function modifies event_log in place for efficiency.
    """
    meta = {"adapter_request_id": request_id}
    if additional_meta:
        meta.update(additional_meta)
    
    event_log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "invoke_adapter",
        "message": f"Called adapter {adapter_id}",
        "meta": meta
    })


def log_fallback(
    event_log: List[Dict[str, Any]],
    reason: str,
    additional_meta: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a fallback to deterministic implementation.
    
    Records when the pipeline falls back from LLM-based processing to
    deterministic rule-based processing, along with the reason.
    
    Args:
        event_log: Event log list to append to (modified in place)
        reason: Explanation for the fallback
        additional_meta: Optional additional metadata
        
    Example:
        >>> event_log = []
        >>> log_fallback(event_log, "LLM response invalid JSON")
        >>> assert event_log[0]['event_type'] == 'fallback'
        >>> assert 'invalid JSON' in event_log[0]['message']
    
    Note:
        Fallback events should trigger human review when appropriate.
    """
    meta = additional_meta if additional_meta else {}
    
    event_log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "fallback",
        "message": f"Used deterministic fallback: {reason}",
        "meta": meta
    })


def log_validation_failure(
    event_log: List[Dict[str, Any]],
    errors: List[str],
    additional_meta: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a validation failure event.
    
    Records when output validation fails, capturing the specific errors
    encountered for debugging.
    
    Args:
        event_log: Event log list to append to
        errors: List of validation error messages
        additional_meta: Optional additional metadata
        
    Example:
        >>> event_log = []
        >>> log_validation_failure(event_log, ["Missing required field 'canonical_text'"])
        >>> assert event_log[0]['event_type'] == 'validation_failed'
    """
    meta = {"errors": errors}
    if additional_meta:
        meta.update(additional_meta)
    
    event_log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "validation_failed",
        "message": f"Validation failed with {len(errors)} error(s)",
        "meta": meta
    })


def log_retry_attempt(
    event_log: List[Dict[str, Any]],
    attempt_number: int,
    reason: str,
    additional_meta: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a retry attempt.
    
    Records when the pipeline retries an operation (e.g., LLM call with
    modified prompt after initial failure).
    
    Args:
        event_log: Event log list to append to
        attempt_number: Which retry attempt this is (1, 2, ...)
        reason: Why the retry is happening
        additional_meta: Optional additional metadata
        
    Example:
        >>> event_log = []
        >>> log_retry_attempt(event_log, 1, "Parse failure, retrying with explicit schema")
        >>> assert 'retry' in event_log[0]['event_type']
    """
    meta = {"attempt": attempt_number}
    if additional_meta:
        meta.update(additional_meta)
    
    event_log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "retry_attempt",
        "message": f"Retry attempt {attempt_number}: {reason}",
        "meta": meta
    })


def redact_provenance(
    provenance: ProvenanceRecord,
    privacy_mode: str
) -> ProvenanceRecord:
    """
    Redact sensitive fields in a provenance record based on privacy mode.
    
    Applies privacy rules to redact sensitive information while preserving
    data needed for reproducibility and debugging.
    
    Args:
        provenance: The provenance record to redact
        privacy_mode: Privacy level ('default', 'strict', etc.)
        
    Returns:
        New ProvenanceRecord with sensitive fields redacted
        
    Privacy Rules:
        - 'default' mode: No redaction
        - 'strict' mode:
            * Redact enrichment_sources URLs
            * Redact raw_output_summary in event logs
            * Preserve source_id and metadata for reproducibility
            
    Examples:
        >>> prov = ProvenanceRecord(
        ...     id="pr_abc123",
        ...     module_id="test",
        ...     module_version="1.0",
        ...     enrichment_sources=["https://example.com/data"]
        ... )
        >>> redacted = redact_provenance(prov, "strict")
        >>> assert "REDACTED" in redacted.enrichment_sources[0]
    
    Note:
        This function creates a new ProvenanceRecord to avoid mutating
        the original. The original is preserved for internal use.
    """
    if privacy_mode == "default":
        # No redaction in default mode
        return provenance
    
    if privacy_mode == "strict":
        # Create a copy with redacted fields
        provenance_dict = provenance.model_dump()
        
        # Redact enrichment sources URLs
        # Keep source_id pattern but remove actual URLs
        redacted_sources = []
        for source in provenance_dict.get("enrichment_sources", []):
            if isinstance(source, str):
                # Simple string URL - redact it
                redacted_sources.append("REDACTED")
            elif isinstance(source, dict):
                # Structured source - redact URL but keep metadata
                redacted_source = source.copy()
                if "url" in redacted_source:
                    redacted_source["url"] = "REDACTED"
                redacted_sources.append(redacted_source)
            else:
                redacted_sources.append(source)
        
        provenance_dict["enrichment_sources"] = redacted_sources
        
        # Redact raw_output_summary in event logs
        redacted_events = []
        for event in provenance_dict.get("event_log", []):
            event_copy = event.copy()
            meta = event_copy.get("meta", {})
            if isinstance(meta, dict):
                if "raw_output_summary" in meta:
                    meta["raw_output_summary"] = "REDACTED"
                if "adapter_response" in meta:
                    meta["adapter_response"] = "REDACTED"
                event_copy["meta"] = meta
            redacted_events.append(event_copy)
        
        provenance_dict["event_log"] = redacted_events
        
        # Create new ProvenanceRecord with redacted data
        return ProvenanceRecord(**provenance_dict)
    
    # Unknown privacy mode - return original with warning
    # In production, this might raise an error
    return provenance


def create_event(
    event_type: str,
    message: str,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized event dictionary for event logs.
    
    Provides a consistent structure for all events, ensuring timestamps
    are properly formatted and all required fields are present.
    
    Args:
        event_type: Type of event (invoke_adapter, fallback, validation_failed, etc.)
        message: Human-readable message describing the event
        meta: Optional metadata dictionary
        
    Returns:
        Event dictionary with timestamp, type, message, and metadata
        
    Example:
        >>> event = create_event(
        ...     "custom_event",
        ...     "Something interesting happened",
        ...     {"detail": "more info"}
        ... )
        >>> assert "ts" in event
        >>> assert event["event_type"] == "custom_event"
    """
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "message": message,
        "meta": meta if meta else {}
    }
