"""Tests for Spec 060: Cache telemetry logging.

TDD-RED: Validates that _log_cache_telemetry extracts RunUsage cache fields
and logs them in the expected format.
"""

import logging

import pytest
from pydantic_ai.usage import RunUsage


class TestCacheTelemetryExtraction:
    """Verify _log_cache_telemetry extracts cache fields from RunUsage."""

    def test_cache_telemetry_extracts_read_tokens(self):
        """T3.1-1: Extracts cache_read_tokens from RunUsage."""
        from nikita.agents.text.agent import _log_cache_telemetry

        usage = RunUsage(
            requests=1,
            input_tokens=6200,
            output_tokens=150,
            cache_read_tokens=5400,
            cache_write_tokens=0,
        )
        # Function should not raise
        _log_cache_telemetry(usage)

    def test_cache_telemetry_extracts_write_tokens(self):
        """T3.1-2: Extracts cache_write_tokens from RunUsage."""
        from nikita.agents.text.agent import _log_cache_telemetry

        usage = RunUsage(
            requests=1,
            input_tokens=6200,
            output_tokens=150,
            cache_read_tokens=0,
            cache_write_tokens=5400,
        )
        _log_cache_telemetry(usage)


class TestCacheTelemetryLogFormat:
    """Verify log output matches expected format."""

    def test_cache_telemetry_log_format(self, caplog):
        """T3.1-3: Log format is [CACHE] read=N write=N input=N cache_ratio=N%."""
        from nikita.agents.text.agent import _log_cache_telemetry

        usage = RunUsage(
            requests=1,
            input_tokens=6200,
            output_tokens=150,
            cache_read_tokens=5400,
            cache_write_tokens=0,
        )

        with caplog.at_level(logging.INFO, logger="nikita.agents.text.agent"):
            _log_cache_telemetry(usage)

        # Find the CACHE log entry
        cache_logs = [r for r in caplog.records if "[CACHE]" in r.message]
        assert len(cache_logs) >= 1, f"Expected [CACHE] log entry, got: {[r.message for r in caplog.records]}"

        msg = cache_logs[0].message
        assert "read=5400" in msg
        assert "write=0" in msg
        assert "input=6200" in msg
        assert "cache_ratio=" in msg

    def test_cache_ratio_calculation(self, caplog):
        """T3.1-4: Cache ratio is correctly calculated as percentage."""
        from nikita.agents.text.agent import _log_cache_telemetry

        usage = RunUsage(
            requests=1,
            input_tokens=10000,
            output_tokens=200,
            cache_read_tokens=5000,
            cache_write_tokens=0,
        )

        with caplog.at_level(logging.INFO, logger="nikita.agents.text.agent"):
            _log_cache_telemetry(usage)

        cache_logs = [r for r in caplog.records if "[CACHE]" in r.message]
        msg = cache_logs[0].message
        # 5000/10000 = 50%
        assert "cache_ratio=50.0%" in msg


class TestCacheTelemetryGracefulDegradation:
    """Verify telemetry handles edge cases without crashing."""

    def test_handles_zero_cache_fields(self, caplog):
        """T3.1-5: Zero cache values logged without error."""
        from nikita.agents.text.agent import _log_cache_telemetry

        usage = RunUsage(
            requests=1,
            input_tokens=6200,
            output_tokens=150,
            cache_read_tokens=0,
            cache_write_tokens=0,
        )

        with caplog.at_level(logging.INFO, logger="nikita.agents.text.agent"):
            _log_cache_telemetry(usage)

        cache_logs = [r for r in caplog.records if "[CACHE]" in r.message]
        assert len(cache_logs) >= 1
        msg = cache_logs[0].message
        assert "read=0" in msg
        assert "write=0" in msg
        assert "cache_ratio=0.0%" in msg

    def test_handles_zero_input_tokens(self):
        """T3.1-6: Zero input_tokens doesn't cause division by zero."""
        from nikita.agents.text.agent import _log_cache_telemetry

        usage = RunUsage(
            requests=0,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_write_tokens=0,
        )
        # Should not raise ZeroDivisionError
        _log_cache_telemetry(usage)
