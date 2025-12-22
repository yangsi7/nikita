"""OTP Email Parser for E2E Tests using Gmail MCP.

Extracts OTP codes (6-8 digits) from Supabase authentication emails.
Designed to work with Gmail MCP tools in Claude Code environment.
"""

import re
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OTPEmail:
    """Parsed OTP email data."""
    message_id: str
    code: str
    email_to: str
    received_at: datetime
    raw_body: str


@dataclass
class MagicLinkEmail:
    """Parsed magic link email data."""
    message_id: str
    magic_link_url: str
    email_to: str
    received_at: datetime
    pkce_code: Optional[str] = None


class OTPEmailParser:
    """Parse OTP codes and magic links from Supabase authentication emails."""

    # Supabase OTP sender
    SUPABASE_SENDER = "noreply@mail.app.supabase.io"

    # OTP code pattern - 6-8 consecutive digits (Supabase may send either)
    OTP_PATTERNS = [
        re.compile(r'Your verification code is[:\s]*(\d{6,8})'),
        re.compile(r'verification code[:\s]*(\d{6,8})'),
        re.compile(r'code[:\s]*(\d{6,8})'),
        re.compile(r'\b(\d{6,8})\b'),  # Fallback: any 6-8 digit sequence
    ]

    # Magic link patterns
    MAGIC_LINK_PATTERN = re.compile(
        r'https://[^\s<>"]+\.supabase\.co/auth/v1/verify\?[^\s<>"]+',
        re.IGNORECASE
    )
    PKCE_CODE_PATTERN = re.compile(r'[?&]code=([^&\s"]+)')

    @classmethod
    def extract_otp_code(cls, email_body: str) -> Optional[str]:
        """Extract OTP code (6-8 digits) from email body.

        Args:
            email_body: Raw email body text (HTML or plain text).

        Returns:
            OTP code string (6-8 digits), or None if not found.
        """
        # Try each pattern in order of specificity
        for pattern in cls.OTP_PATTERNS:
            match = pattern.search(email_body)
            if match:
                return match.group(1)
        return None

    @classmethod
    def extract_magic_link(cls, email_body: str) -> Optional[str]:
        """Extract magic link URL from email body.

        Args:
            email_body: Raw email body text (HTML or plain text).

        Returns:
            Magic link URL string, or None if not found.
        """
        # Also check href attributes
        href_pattern = re.compile(r'href="([^"]*supabase\.co/auth[^"]*)"')
        match = href_pattern.search(email_body)
        if match:
            url = match.group(1).replace('&amp;', '&')
            return url

        # Fallback to direct pattern
        match = cls.MAGIC_LINK_PATTERN.search(email_body)
        if match:
            url = match.group(0).rstrip('"\'>')
            url = url.replace('&amp;', '&')
            return url

        return None

    @classmethod
    def extract_pkce_code(cls, url: str) -> Optional[str]:
        """Extract PKCE code from magic link URL.

        Args:
            url: Magic link URL containing PKCE code.

        Returns:
            PKCE authorization code, or None if not found.
        """
        match = cls.PKCE_CODE_PATTERN.search(url)
        return match.group(1) if match else None

    @classmethod
    def build_otp_search_query(
        cls,
        recipient_email: str,
        after_timestamp: Optional[float] = None,
    ) -> str:
        """Build Gmail search query for OTP emails.

        Args:
            recipient_email: Email address that received OTP.
            after_timestamp: Unix timestamp to filter emails after.

        Returns:
            Gmail search query string.
        """
        query_parts = [
            f"from:{cls.SUPABASE_SENDER}",
            f"to:{recipient_email}",
        ]

        if after_timestamp:
            # Gmail uses seconds, not milliseconds
            query_parts.append(f"after:{int(after_timestamp)}")

        return " ".join(query_parts)

    @classmethod
    def build_magic_link_search_query(
        cls,
        recipient_email: str,
        after_timestamp: Optional[float] = None,
    ) -> str:
        """Build Gmail search query for magic link emails.

        Args:
            recipient_email: Email address that received magic link.
            after_timestamp: Unix timestamp to filter emails after.

        Returns:
            Gmail search query string.
        """
        query_parts = [
            f"from:{cls.SUPABASE_SENDER}",
            f"to:{recipient_email}",
            "(subject:magic OR subject:login OR subject:sign)",
        ]

        if after_timestamp:
            query_parts.append(f"after:{int(after_timestamp)}")

        return " ".join(query_parts)

    @classmethod
    def parse_otp_email(
        cls,
        message_id: str,
        email_content: dict,
        recipient_email: str = "",
    ) -> Optional[OTPEmail]:
        """Parse Gmail MCP read_email response into OTPEmail.

        Args:
            message_id: Gmail message ID.
            email_content: Response from mcp__gmail__read_email.
            recipient_email: Expected recipient email.

        Returns:
            OTPEmail dataclass or None if parsing fails.
        """
        body = cls._extract_body(email_content)

        code = cls.extract_otp_code(body)
        if not code:
            return None

        return OTPEmail(
            message_id=message_id,
            code=code,
            email_to=recipient_email,
            received_at=datetime.utcnow(),
            raw_body=body,
        )

    @classmethod
    def parse_magic_link_email(
        cls,
        message_id: str,
        email_content: dict,
        recipient_email: str = "",
    ) -> Optional[MagicLinkEmail]:
        """Parse Gmail MCP read_email response into MagicLinkEmail.

        Args:
            message_id: Gmail message ID.
            email_content: Response from mcp__gmail__read_email.
            recipient_email: Expected recipient email.

        Returns:
            MagicLinkEmail dataclass or None if parsing fails.
        """
        body = cls._extract_body(email_content)

        magic_link = cls.extract_magic_link(body)
        if not magic_link:
            return None

        pkce_code = cls.extract_pkce_code(magic_link)

        return MagicLinkEmail(
            message_id=message_id,
            magic_link_url=magic_link,
            email_to=recipient_email,
            received_at=datetime.utcnow(),
            pkce_code=pkce_code,
        )

    @classmethod
    def _extract_body(cls, email_content: dict | str) -> str:
        """Extract body text from email content.

        Handles different response formats from Gmail MCP.
        """
        if isinstance(email_content, str):
            return email_content

        if not isinstance(email_content, dict):
            return ""

        # Try common fields
        body = email_content.get("body", "")
        if body:
            return body

        body = email_content.get("snippet", "")
        if body:
            return body

        # Try payload structure (for raw MIME)
        payload = email_content.get("payload", {})
        parts = payload.get("parts", [])

        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type.startswith("text/"):
                body_data = part.get("body", {}).get("data", "")
                if body_data:
                    import base64
                    try:
                        return base64.urlsafe_b64decode(body_data).decode("utf-8")
                    except Exception:
                        continue

        # Fallback to raw body data
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            import base64
            try:
                return base64.urlsafe_b64decode(body_data).decode("utf-8")
            except Exception:
                pass

        return ""
