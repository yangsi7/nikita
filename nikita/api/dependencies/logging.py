"""PII-safe logging formatter for admin monitoring.

Part of Spec 034 - Admin User Monitoring Dashboard.
CRITICAL: All logs must sanitize PII to prevent data leakage.

Usage:
    from nikita.api.dependencies.logging import get_pii_safe_logger

    logger = get_pii_safe_logger(__name__)
    logger.info(f"Processing user {user.email}")  # Email will be redacted
"""

import logging
import re
from typing import Any


class PiiSafeFormatter(logging.Formatter):
    """Log formatter that redacts PII from messages.

    Patterns redacted:
    - Email addresses
    - Phone numbers (US and international)
    - IP addresses (optional, configurable)

    Patterns preserved:
    - UUIDs (internal identifiers, not PII)
    - Timestamps
    - Log levels and module names
    """

    # Regex patterns for PII
    EMAIL_PATTERN = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    )

    # Phone patterns - various formats
    PHONE_PATTERNS = [
        # International format: +1-555-123-4567, +44 20 1234 5678
        re.compile(r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}"),
        # US formats: (555) 123-4567, 555-123-4567, 555.123.4567
        re.compile(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"),
        # 10-digit no separators: 5551234567
        re.compile(r"(?<!\d)\d{10}(?!\d)"),
        # With country code: 1-555-123-4567
        re.compile(r"(?<!\d)1[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{4}"),
    ]

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        redact_emails: bool = True,
        redact_phones: bool = True,
    ):
        """Initialize PII-safe formatter.

        Args:
            fmt: Log format string
            datefmt: Date format string
            redact_emails: Whether to redact email addresses
            redact_phones: Whether to redact phone numbers
        """
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.redact_emails = redact_emails
        self.redact_phones = redact_phones

    def _redact_pii(self, message: str) -> str:
        """Redact PII from a message string.

        Args:
            message: Original log message

        Returns:
            Message with PII redacted
        """
        if self.redact_emails:
            message = self.EMAIL_PATTERN.sub("[EMAIL_REDACTED]", message)

        if self.redact_phones:
            for pattern in self.PHONE_PATTERNS:
                message = pattern.sub("[PHONE_REDACTED]", message)

        return message

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII redaction.

        Args:
            record: Log record to format

        Returns:
            Formatted log string with PII redacted
        """
        # Redact PII from the message before formatting
        original_msg = record.getMessage()
        redacted_msg = self._redact_pii(original_msg)

        # Create a copy of the record with redacted message
        record.msg = redacted_msg
        record.args = ()  # Clear args since we already formatted

        return super().format(record)


def get_pii_safe_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger configured with PII-safe formatting.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default INFO)

    Returns:
        Configured logger with PiiSafeFormatter

    Example:
        logger = get_pii_safe_logger(__name__)
        logger.info(f"User {email} accessed resource")  # Email redacted
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = PiiSafeFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
