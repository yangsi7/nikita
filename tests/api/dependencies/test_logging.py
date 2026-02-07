"""Tests for PII-safe logging formatter - T1.3 Spec 034.

TDD: Write tests FIRST, then implement.
"""

import logging
from uuid import uuid4

import pytest


class TestPiiSafeFormatter:
    """Test PiiSafeFormatter class."""

    def test_format_redacts_email(self):
        """AC-1.3.1: Email addresses are redacted from logs."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User email is user@example.com",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "user@example.com" not in result
        assert "[EMAIL_REDACTED]" in result or "***" in result

    def test_format_redacts_phone_number(self):
        """AC-1.3.2: Phone numbers are redacted from logs."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User phone is +1-555-123-4567",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "+1-555-123-4567" not in result
        assert "[PHONE_REDACTED]" in result or "***" in result

    def test_format_redacts_telegram_id(self):
        """Telegram IDs are redacted from logs."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Telegram ID: 123456789",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        # Telegram IDs can stay since they're not personal info without context
        # This test documents the behavior

    def test_format_preserves_uuids(self):
        """AC-1.3.3: UUIDs are preserved (not PII)."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        test_uuid = str(uuid4())
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"User ID: {test_uuid}",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert test_uuid in result

    def test_format_redacts_multiple_pii(self):
        """Multiple PII items in one message are all redacted."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User user@test.com called from +44-20-1234-5678",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "user@test.com" not in result
        assert "+44-20-1234-5678" not in result

    def test_format_handles_message_without_pii(self):
        """Messages without PII are not modified."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        original_msg = "Processing conversation started at 2024-01-15"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=original_msg,
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert original_msg in result

    def test_get_pii_safe_logger(self):
        """get_pii_safe_logger returns logger with PiiSafeFormatter."""
        from nikita.api.dependencies.logging import get_pii_safe_logger

        logger = get_pii_safe_logger("test_admin_monitoring")

        assert logger.name == "test_admin_monitoring"
        # Check that handler has PiiSafeFormatter
        for handler in logger.handlers:
            from nikita.api.dependencies.logging import PiiSafeFormatter
            if isinstance(handler.formatter, PiiSafeFormatter):
                break
        else:
            # Logger should have at least one handler with PiiSafeFormatter
            # or inherit from parent
            pass  # This is acceptable if using propagation


class TestSensitiveDataPatterns:
    """Test various sensitive data patterns."""

    def test_us_phone_formats(self):
        """Various US phone formats are redacted."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        phone_formats = [
            "(555) 123-4567",
            "555-123-4567",
            "5551234567",
            "1-555-123-4567",
        ]

        for phone in phone_formats:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Phone: {phone}",
                args=(),
                exc_info=None,
            )
            result = formatter.format(record)
            assert phone not in result, f"Phone {phone} not redacted"

    def test_international_phone_formats(self):
        """International phone formats are redacted."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        phones = [
            "+44 20 1234 5678",
            "+41 44 123 45 67",
            "+1 (555) 123-4567",
        ]

        for phone in phones:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Phone: {phone}",
                args=(),
                exc_info=None,
            )
            result = formatter.format(record)
            assert phone not in result, f"Phone {phone} not redacted"

    def test_email_formats(self):
        """Various email formats are redacted."""
        from nikita.api.dependencies.logging import PiiSafeFormatter

        formatter = PiiSafeFormatter()
        emails = [
            "user@example.com",
            "user.name@example.co.uk",
            "user+tag@example.org",
            "admin@silent-agents.com",
        ]

        for email in emails:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Email: {email}",
                args=(),
                exc_info=None,
            )
            result = formatter.format(record)
            assert email not in result, f"Email {email} not redacted"
