"""
Unit tests for the provenance module.

This test suite validates provenance utilities including:
- Deterministic provenance ID generation
- Event logging utilities
- Privacy redaction
- Standardized event creation

Author: Victor Rowello
Sprint: 2, Task: 5
"""
import pytest
from src.pipeline.provenance import (
    make_provenance_id,
    log_adapter_call,
    log_fallback,
    log_validation_failure,
    log_retry_attempt,
    redact_provenance,
    create_event,
)
from src.witty_types import ProvenanceRecord


class TestProvenanceIDGeneration:
    """Test deterministic provenance ID generation."""
    
    def test_id_format(self):
        """Test that provenance IDs have correct format."""
        prov_id = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        assert prov_id.startswith("pr_")
        assert len(prov_id) == 15  # "pr_" + 12 hex chars
    
    def test_determinism(self):
        """Test that same inputs produce same ID."""
        id1 = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        id2 = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        assert id1 == id2
    
    def test_different_inputs_different_id(self):
        """Test that different inputs produce different IDs."""
        id1 = make_provenance_id(
            normalized_input="test input 1",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        id2 = make_provenance_id(
            normalized_input="test input 2",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        assert id1 != id2
    
    def test_different_salts_different_id(self):
        """Test that different salts produce different IDs."""
        id1 = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="salt1"
        )
        
        id2 = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="salt2"
        )
        
        assert id1 != id2
    
    def test_different_module_versions_different_id(self):
        """Test that different module versions produce different IDs."""
        id1 = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        id2 = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.1",
            salt="test_salt"
        )
        
        assert id1 != id2
    
    def test_unicode_input(self):
        """Test that unicode inputs are handled correctly."""
        # Test with various unicode characters
        unicode_inputs = [
            "测试输入",  # Chinese
            "テスト入力",  # Japanese
            "Тестовый ввод",  # Russian
            "test café résumé",  # Accented characters
            "emoji 🔥 🎉",  # Emojis
        ]
        
        ids = []
        for input_text in unicode_inputs:
            prov_id = make_provenance_id(
                normalized_input=input_text,
                module_id="test_module",
                module_version="1.0.0",
                salt="test_salt"
            )
            assert prov_id.startswith("pr_")
            assert len(prov_id) == 15
            ids.append(prov_id)
        
        # All IDs should be unique
        assert len(ids) == len(set(ids))
    
    def test_empty_input(self):
        """Test that empty input produces valid ID."""
        prov_id = make_provenance_id(
            normalized_input="",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        assert prov_id.startswith("pr_")
        assert len(prov_id) == 15
    
    def test_very_long_input(self):
        """Test that very long inputs are handled correctly."""
        # 10,000 character input
        long_input = "a" * 10000
        
        prov_id = make_provenance_id(
            normalized_input=long_input,
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        assert prov_id.startswith("pr_")
        assert len(prov_id) == 15
    
    def test_special_characters_in_input(self):
        """Test that special characters don't break ID generation."""
        special_inputs = [
            "input\nwith\nnewlines",
            "input\twith\ttabs",
            'input "with" quotes',
            "input 'with' apostrophes",
            "input\\with\\backslashes",
            "input/with/slashes",
        ]
        
        for input_text in special_inputs:
            prov_id = make_provenance_id(
                normalized_input=input_text,
                module_id="test_module",
                module_version="1.0.0",
                salt="test_salt"
            )
            assert prov_id.startswith("pr_")
            assert len(prov_id) == 15
    
    def test_id_contains_only_hex_characters(self):
        """Test that ID hash portion contains only hexadecimal characters."""
        prov_id = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        # Extract hash portion (after "pr_")
        hash_portion = prov_id[3:]
        
        # Should be valid hexadecimal
        try:
            int(hash_portion, 16)
            valid_hex = True
        except ValueError:
            valid_hex = False
        
        assert valid_hex
    
    def test_reproducibility_across_calls(self):
        """Test that multiple calls with same inputs produce same ID."""
        inputs = [
            ("input1", "module1", "1.0", "salt1"),
            ("input2", "module2", "2.0", "salt2"),
            ("", "module3", "3.0", "salt3"),
        ]
        
        for normalized_input, module_id, version, salt in inputs:
            ids = [
                make_provenance_id(normalized_input, module_id, version, salt)
                for _ in range(10)
            ]
            # All should be identical
            assert len(set(ids)) == 1


class TestEventLogging:
    """Test event logging utility functions."""
    
    def test_log_adapter_call(self):
        """Test logging adapter calls."""
        event_log = []
        log_adapter_call(event_log, "openai_gpt4", "req_123")
        
        assert len(event_log) == 1
        assert event_log[0]["event_type"] == "invoke_adapter"
        assert event_log[0]["meta"]["adapter_request_id"] == "req_123"
        assert "ts" in event_log[0]
    
    def test_log_adapter_call_with_metadata(self):
        """Test logging adapter calls with additional metadata."""
        event_log = []
        log_adapter_call(
            event_log, 
            "openai_gpt4", 
            "req_123",
            additional_meta={"model": "gpt-4", "tokens": 150}
        )
        
        assert len(event_log) == 1
        assert event_log[0]["meta"]["adapter_request_id"] == "req_123"
        assert event_log[0]["meta"]["model"] == "gpt-4"
        assert event_log[0]["meta"]["tokens"] == 150
    
    def test_log_fallback(self):
        """Test logging fallback events."""
        event_log = []
        log_fallback(event_log, "LLM response invalid")
        
        assert len(event_log) == 1
        assert event_log[0]["event_type"] == "fallback"
        assert "invalid" in event_log[0]["message"]
    
    def test_log_fallback_with_metadata(self):
        """Test logging fallback with additional metadata."""
        event_log = []
        log_fallback(
            event_log, 
            "LLM response invalid",
            additional_meta={"error_code": "PARSE_ERROR"}
        )
        
        assert len(event_log) == 1
        assert event_log[0]["meta"]["error_code"] == "PARSE_ERROR"
    
    def test_log_validation_failure(self):
        """Test logging validation failures."""
        event_log = []
        log_validation_failure(event_log, ["Error 1", "Error 2"])
        
        assert len(event_log) == 1
        assert event_log[0]["event_type"] == "validation_failed"
        assert len(event_log[0]["meta"]["errors"]) == 2
    
    def test_log_validation_failure_empty_errors(self):
        """Test logging validation failure with empty error list."""
        event_log = []
        log_validation_failure(event_log, [])
        
        assert len(event_log) == 1
        assert event_log[0]["meta"]["errors"] == []
    
    def test_log_retry_attempt(self):
        """Test logging retry attempts."""
        event_log = []
        log_retry_attempt(event_log, 1, "Parse failure")
        
        assert len(event_log) == 1
        assert event_log[0]["event_type"] == "retry_attempt"
        assert event_log[0]["meta"]["attempt"] == 1
    
    def test_multiple_events_in_sequence(self):
        """Test logging multiple events to the same log."""
        event_log = []
        
        log_adapter_call(event_log, "adapter1", "req_1")
        log_retry_attempt(event_log, 1, "First retry")
        log_fallback(event_log, "Giving up")
        
        assert len(event_log) == 3
        assert event_log[0]["event_type"] == "invoke_adapter"
        assert event_log[1]["event_type"] == "retry_attempt"
        assert event_log[2]["event_type"] == "fallback"
    
    def test_event_log_timestamp_format(self):
        """Test that event timestamps are properly formatted ISO strings."""
        event_log = []
        log_adapter_call(event_log, "test_adapter", "req_1")
        
        # Should be ISO format timestamp
        timestamp = event_log[0]["ts"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format includes T separator
        # Should be parseable as datetime
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            valid_timestamp = True
        except ValueError:
            valid_timestamp = False
        assert valid_timestamp


class TestPrivacyRedaction:
    """Test privacy redaction of provenance records."""
    
    def test_no_redaction_default_mode(self):
        """Test that default mode doesn't redact."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            enrichment_sources=["https://example.com/data"]
        )
        
        redacted = redact_provenance(prov, "default")
        
        assert redacted.enrichment_sources == ["https://example.com/data"]
    
    def test_redaction_strict_mode(self):
        """Test that strict mode redacts URLs."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            enrichment_sources=["https://example.com/data"]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        assert "REDACTED" in redacted.enrichment_sources[0]
    
    def test_redaction_structured_sources(self):
        """Test that redaction handles string sources correctly in strict mode."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            enrichment_sources=[
                "https://example.com/data1",
                "https://example.com/data2"
            ]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        # All sources should be redacted
        assert len(redacted.enrichment_sources) == 2
        assert all("REDACTED" in source for source in redacted.enrichment_sources)
    
    def test_redaction_event_log(self):
        """Test that event log entries are redacted in strict mode."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            event_log=[
                {
                    "ts": "2025-01-01T00:00:00Z",
                    "event_type": "test",
                    "message": "test",
                    "meta": {"raw_output_summary": "sensitive data"}
                }
            ]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        assert redacted.event_log[0]["meta"]["raw_output_summary"] == "REDACTED"
    
    def test_redaction_adapter_response_in_event_log(self):
        """Test that adapter responses are redacted in strict mode."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            event_log=[
                {
                    "ts": "2025-01-01T00:00:00Z",
                    "event_type": "test",
                    "message": "test",
                    "meta": {"adapter_response": "full response text"}
                }
            ]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        assert redacted.event_log[0]["meta"]["adapter_response"] == "REDACTED"
    
    def test_redaction_preserves_other_fields(self):
        """Test that redaction preserves non-sensitive fields."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test_module",
            module_version="1.0.0",
            adapter_id="openai",
            confidence=0.95,
            ambiguity_flags=["flag1"],
            reduction_rationale="test rationale",
            enrichment_sources=["https://example.com/data"],
            event_log=[
                {
                    "ts": "2025-01-01T00:00:00Z",
                    "event_type": "test",
                    "message": "test",
                    "meta": {"raw_output_summary": "sensitive"}
                }
            ]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        # Non-sensitive fields should be preserved
        assert redacted.id == "pr_abc123"
        assert redacted.module_id == "test_module"
        assert redacted.module_version == "1.0.0"
        assert redacted.adapter_id == "openai"
        assert redacted.confidence == 0.95
        assert redacted.ambiguity_flags == ["flag1"]
        assert redacted.reduction_rationale == "test rationale"
    
    def test_redaction_empty_sources_and_logs(self):
        """Test redaction with empty enrichment sources and event logs."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            enrichment_sources=[],
            event_log=[]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        assert redacted.enrichment_sources == []
        assert redacted.event_log == []
    
    def test_redaction_unknown_privacy_mode(self):
        """Test that unknown privacy modes return original data."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            enrichment_sources=["https://example.com/data"]
        )
        
        redacted = redact_provenance(prov, "unknown_mode")
        
        # Should return original unmodified
        assert redacted.enrichment_sources == ["https://example.com/data"]
    
    def test_redaction_multiple_event_log_entries(self):
        """Test redaction of multiple event log entries."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            event_log=[
                {
                    "ts": "2025-01-01T00:00:00Z",
                    "event_type": "adapter_call",
                    "message": "test1",
                    "meta": {"raw_output_summary": "sensitive1"}
                },
                {
                    "ts": "2025-01-01T00:00:01Z",
                    "event_type": "retry",
                    "message": "test2",
                    "meta": {"adapter_response": "sensitive2"}
                },
                {
                    "ts": "2025-01-01T00:00:02Z",
                    "event_type": "success",
                    "message": "test3",
                    "meta": {"other_field": "not sensitive"}
                }
            ]
        )
        
        redacted = redact_provenance(prov, "strict")
        
        assert len(redacted.event_log) == 3
        assert redacted.event_log[0]["meta"]["raw_output_summary"] == "REDACTED"
        assert redacted.event_log[1]["meta"]["adapter_response"] == "REDACTED"
        assert redacted.event_log[2]["meta"]["other_field"] == "not sensitive"


class TestCreateEvent:
    """Test standardized event creation."""
    
    def test_basic_event(self):
        """Test creating a basic event."""
        event = create_event("test_event", "Test message")
        
        assert event["event_type"] == "test_event"
        assert event["message"] == "Test message"
        assert "ts" in event
        assert "meta" in event
    
    def test_event_with_metadata(self):
        """Test creating event with metadata."""
        event = create_event(
            "test_event",
            "Test message",
            {"key": "value"}
        )
        
        assert event["meta"]["key"] == "value"
    
    def test_event_with_none_metadata(self):
        """Test creating event with None metadata creates empty dict."""
        event = create_event("test_event", "Test message", None)
        
        assert event["meta"] == {}
    
    def test_event_with_complex_metadata(self):
        """Test creating event with complex nested metadata."""
        meta = {
            "nested": {
                "level1": {
                    "level2": "value"
                }
            },
            "list": [1, 2, 3],
            "string": "test"
        }
        event = create_event("test_event", "Test message", meta)
        
        assert event["meta"]["nested"]["level1"]["level2"] == "value"
        assert event["meta"]["list"] == [1, 2, 3]
        assert event["meta"]["string"] == "test"
    
    def test_event_timestamp_is_recent(self):
        """Test that event timestamp is recent (within last few seconds)."""
        from datetime import datetime, timezone
        
        before = datetime.now(timezone.utc)
        event = create_event("test_event", "Test message")
        after = datetime.now(timezone.utc)
        
        # Parse event timestamp
        event_time = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
        
        # Should be between before and after
        assert before <= event_time <= after


class TestProvenanceIntegration:
    """Integration tests combining multiple provenance utilities."""
    
    def test_complete_provenance_workflow(self):
        """Test a complete workflow of creating and managing provenance."""
        # Create provenance ID
        prov_id = make_provenance_id(
            normalized_input="test input",
            module_id="test_module",
            module_version="1.0.0",
            salt="test_salt"
        )
        
        # Create event log
        event_log = []
        log_adapter_call(event_log, "openai_gpt4", "req_123")
        log_retry_attempt(event_log, 1, "Parse error")
        log_fallback(event_log, "LLM failed")
        
        # Create provenance record
        prov = ProvenanceRecord(
            id=prov_id,
            module_id="test_module",
            module_version="1.0.0",
            adapter_id="openai_gpt4",
            confidence=0.85,
            event_log=event_log,
            enrichment_sources=["https://example.com/source"]
        )
        
        # Apply redaction
        redacted = redact_provenance(prov, "strict")
        
        # Verify workflow results
        assert redacted.id == prov_id
        assert len(redacted.event_log) == 3
        assert "REDACTED" in redacted.enrichment_sources[0]
        assert redacted.confidence == 0.85
    
    def test_provenance_reproducibility_with_redaction(self):
        """Test that redaction doesn't affect ID reproducibility."""
        prov_id1 = make_provenance_id(
            "input", "module", "1.0", "salt"
        )
        
        prov1 = ProvenanceRecord(
            id=prov_id1,
            module_id="module",
            module_version="1.0",
            enrichment_sources=["https://example.com"]
        )
        
        redacted1 = redact_provenance(prov1, "strict")
        
        # Create another with same inputs
        prov_id2 = make_provenance_id(
            "input", "module", "1.0", "salt"
        )
        
        prov2 = ProvenanceRecord(
            id=prov_id2,
            module_id="module",
            module_version="1.0",
            enrichment_sources=["https://example.com"]
        )
        
        redacted2 = redact_provenance(prov2, "strict")
        
        # IDs should be identical
        assert redacted1.id == redacted2.id
        assert prov_id1 == prov_id2


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""
    
    def test_log_functions_handle_concurrent_modifications(self):
        """Test that log functions work correctly with concurrent-like access."""
        event_log = []
        
        # Simulate rapid additions
        for i in range(100):
            if i % 3 == 0:
                log_adapter_call(event_log, f"adapter_{i}", f"req_{i}")
            elif i % 3 == 1:
                log_retry_attempt(event_log, i, f"Retry {i}")
            else:
                log_fallback(event_log, f"Fallback {i}")
        
        assert len(event_log) == 100
        # Verify all events are properly formed
        for event in event_log:
            assert "ts" in event
            assert "event_type" in event
            assert "message" in event
    
    def test_redaction_with_malformed_event_log(self):
        """Test redaction handles malformed event log entries gracefully."""
        prov = ProvenanceRecord(
            id="pr_abc123",
            module_id="test",
            module_version="1.0",
            event_log=[
                {
                    "ts": "2025-01-01T00:00:00Z",
                    "event_type": "test",
                    "message": "test",
                    # meta is missing - should not crash
                },
                {
                    "ts": "2025-01-01T00:00:01Z",
                    "event_type": "test",
                    "message": "test",
                    "meta": "not a dict"  # meta is not a dict
                }
            ]
        )
        
        # Should not crash
        redacted = redact_provenance(prov, "strict")
        
        assert len(redacted.event_log) == 2
    
    def test_provenance_id_with_null_bytes(self):
        """Test that null bytes in input don't break ID generation."""
        # Python strings can contain null bytes
        input_with_null = "test\x00input"
        
        prov_id = make_provenance_id(
            normalized_input=input_with_null,
            module_id="test",
            module_version="1.0",
            salt="salt"
        )
        
        assert prov_id.startswith("pr_")
        assert len(prov_id) == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
