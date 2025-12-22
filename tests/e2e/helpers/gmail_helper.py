"""
Gmail Helper for E2E Tests

Provides utilities for retrieving magic link and OTP emails from Gmail.
Uses Google Gmail API for automated email retrieval.

For local testing via Claude Code, the MCP tools can be used directly:
- mcp__gmail__search_emails
- mcp__gmail__read_email

For CI/CD, requires GOOGLE_APPLICATION_CREDENTIALS environment variable
pointing to a service account JSON file with Gmail API access.
"""

import asyncio
import base64
import os
import re
import time
from typing import Optional, Callable, Any

from .otp_email_parser import OTPEmailParser, OTPEmail, MagicLinkEmail


class GmailMCPClient:
    """Client for Gmail MCP operations.

    This class provides async waiting functions for OTP and magic link emails.
    Designed to be used with Claude Code's Gmail MCP tools.

    In Claude Code context, the actual MCP calls are made externally,
    and results are passed through callback functions.
    """

    def __init__(self, test_email: str):
        """Initialize Gmail MCP client.

        Args:
            test_email: Email address to monitor for emails.
        """
        self.test_email = test_email
        self.parser = OTPEmailParser

    async def wait_for_otp(
        self,
        timeout_seconds: int = 90,
        poll_interval: float = 3.0,
        since_timestamp: Optional[float] = None,
        search_fn: Optional[Callable] = None,
        read_fn: Optional[Callable] = None,
    ) -> OTPEmail:
        """Wait for OTP email and extract code.

        This method polls Gmail until an OTP email is found or timeout.

        Args:
            timeout_seconds: Maximum wait time (default 90s for email delivery).
            poll_interval: Seconds between poll attempts.
            since_timestamp: Only consider emails after this timestamp.
            search_fn: Async function to search emails (for testing).
            read_fn: Async function to read email content (for testing).

        Returns:
            OTPEmail with extracted 6-digit code.

        Raises:
            TimeoutError: If no OTP email found within timeout.
            ValueError: If email found but OTP code cannot be extracted.
        """
        if since_timestamp is None:
            since_timestamp = time.time() - 10  # 10 seconds buffer

        start_time = time.time()
        attempts = 0

        query = self.parser.build_otp_search_query(
            recipient_email=self.test_email,
            after_timestamp=since_timestamp,
        )

        while time.time() - start_time < timeout_seconds:
            attempts += 1
            print(f"[Gmail MCP] OTP poll attempt {attempts}...")

            try:
                # In Claude Code, these would be replaced with MCP calls:
                # mcp__gmail__search_emails({"query": query, "maxResults": 5})
                # mcp__gmail__read_email({"messageId": message_id})
                if search_fn:
                    search_results = await search_fn(query, max_results=5)

                    if search_results and len(search_results) > 0:
                        for msg_meta in search_results:
                            message_id = msg_meta.get("id")
                            if message_id and read_fn:
                                email_content = await read_fn(message_id)
                                otp_email = self.parser.parse_otp_email(
                                    message_id=message_id,
                                    email_content=email_content,
                                    recipient_email=self.test_email,
                                )
                                if otp_email:
                                    print(f"[Gmail MCP] OTP code found: {otp_email.code}")
                                    return otp_email

            except Exception as e:
                print(f"[Gmail MCP] Poll attempt {attempts} error: {e}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(
            f"No OTP email found for {self.test_email} within {timeout_seconds}s "
            f"after {attempts} attempts"
        )

    async def wait_for_magic_link(
        self,
        timeout_seconds: int = 60,
        poll_interval: float = 3.0,
        since_timestamp: Optional[float] = None,
        search_fn: Optional[Callable] = None,
        read_fn: Optional[Callable] = None,
    ) -> MagicLinkEmail:
        """Wait for magic link email and extract URL.

        Args:
            timeout_seconds: Maximum wait time.
            poll_interval: Seconds between poll attempts.
            since_timestamp: Only consider emails after this timestamp.
            search_fn: Async function to search emails (for testing).
            read_fn: Async function to read email content (for testing).

        Returns:
            MagicLinkEmail with extracted URL and PKCE code.

        Raises:
            TimeoutError: If no magic link email found within timeout.
        """
        if since_timestamp is None:
            since_timestamp = time.time() - 10

        start_time = time.time()
        attempts = 0

        query = self.parser.build_magic_link_search_query(
            recipient_email=self.test_email,
            after_timestamp=since_timestamp,
        )

        while time.time() - start_time < timeout_seconds:
            attempts += 1
            print(f"[Gmail MCP] Magic link poll attempt {attempts}...")

            try:
                if search_fn:
                    search_results = await search_fn(query, max_results=5)

                    if search_results and len(search_results) > 0:
                        for msg_meta in search_results:
                            message_id = msg_meta.get("id")
                            if message_id and read_fn:
                                email_content = await read_fn(message_id)
                                magic_link_email = self.parser.parse_magic_link_email(
                                    message_id=message_id,
                                    email_content=email_content,
                                    recipient_email=self.test_email,
                                )
                                if magic_link_email:
                                    print(f"[Gmail MCP] Magic link found: {magic_link_email.magic_link_url[:50]}...")
                                    return magic_link_email

            except Exception as e:
                print(f"[Gmail MCP] Poll attempt {attempts} error: {e}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(
            f"No magic link email found for {self.test_email} within {timeout_seconds}s "
            f"after {attempts} attempts"
        )


class GmailHelper:
    """Helper class for Gmail operations in E2E tests."""

    SUPABASE_VERIFY_URL_PATTERN = r'https://[^/]+\.supabase\.co/auth/v1/verify\?[^"\s<>]+'
    MAGIC_LINK_SENDER = "noreply@mail.app.supabase.io"

    def __init__(self, test_email: str):
        """Initialize Gmail helper.

        Args:
            test_email: The email address to monitor for magic links
        """
        self.test_email = test_email
        self._service = None

    async def wait_for_magic_link(
        self,
        timeout_seconds: int = 60,
        poll_interval: float = 2.0,
        since_timestamp: Optional[float] = None
    ) -> str:
        """
        Wait for a magic link email and return the verification URL.

        Args:
            timeout_seconds: Maximum time to wait for email
            poll_interval: Seconds between polling attempts
            since_timestamp: Only consider emails after this Unix timestamp

        Returns:
            The magic link URL

        Raises:
            TimeoutError: If no magic link email found within timeout
            ValueError: If magic link URL cannot be extracted from email
        """
        if since_timestamp is None:
            since_timestamp = time.time() - 5  # 5 seconds ago

        start_time = time.time()
        attempts = 0

        while time.time() - start_time < timeout_seconds:
            attempts += 1

            # Search for recent emails from Supabase
            try:
                email_content = await self._get_latest_magic_link_email(since_timestamp)
                if email_content:
                    magic_link = self._extract_magic_link(email_content)
                    if magic_link:
                        return magic_link
            except Exception as e:
                # Log but continue polling
                print(f"[GmailHelper] Attempt {attempts} failed: {e}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(
            f"No magic link email received within {timeout_seconds}s "
            f"for {self.test_email}"
        )

    async def _get_latest_magic_link_email(
        self,
        since_timestamp: float
    ) -> Optional[str]:
        """
        Get the most recent magic link email content.

        This is a placeholder that should be implemented based on
        the execution environment:
        - Claude Code: Uses Gmail MCP tools
        - CI/CD: Uses Gmail API with service account

        Returns:
            Email body HTML/text if found, None otherwise
        """
        # For Claude Code execution, this will be overridden
        # by direct MCP tool calls in the test file
        #
        # For standalone execution, implement Gmail API here:
        #
        # from google.oauth2 import service_account
        # from googleapiclient.discovery import build
        #
        # if self._service is None:
        #     creds = service_account.Credentials.from_service_account_file(
        #         os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
        #         scopes=['https://www.googleapis.com/auth/gmail.readonly']
        #     )
        #     self._service = build('gmail', 'v1', credentials=creds)
        #
        # ... query and return email content

        return None

    def _extract_magic_link(self, email_content: str) -> Optional[str]:
        """
        Extract magic link URL from email HTML content.

        Args:
            email_content: Raw email HTML or text content

        Returns:
            Magic link URL if found, None otherwise
        """
        # Look for Supabase verification URL
        match = re.search(self.SUPABASE_VERIFY_URL_PATTERN, email_content)
        if match:
            url = match.group(0)
            # Clean up any trailing quotes or HTML entities
            url = url.rstrip('"\'>')
            url = url.replace('&amp;', '&')
            return url

        # Also try looking for href with the URL
        href_pattern = r'href="(' + self.SUPABASE_VERIFY_URL_PATTERN + r')"'
        match = re.search(href_pattern, email_content)
        if match:
            return match.group(1).replace('&amp;', '&')

        return None


def extract_magic_link_from_html(html_content: str) -> Optional[str]:
    """
    Standalone function to extract magic link from email HTML.

    Args:
        html_content: Email HTML body

    Returns:
        Magic link URL or None
    """
    helper = GmailHelper("")
    return helper._extract_magic_link(html_content)


def extract_tokens_from_url(url: str) -> dict:
    """
    Extract authentication tokens from magic link URL.

    The URL may contain:
    - Query params: ?code=xxx (PKCE flow)
    - Hash fragment: #access_token=xxx (implicit flow)

    Args:
        url: Magic link URL

    Returns:
        Dict with 'code' and/or 'access_token' keys
    """
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(url)
    result = {}

    # Query params (PKCE flow)
    query_params = parse_qs(parsed.query)
    if 'code' in query_params:
        result['code'] = query_params['code'][0]
    if 'token' in query_params:
        result['token'] = query_params['token'][0]

    # Hash fragment (implicit flow)
    if parsed.fragment:
        fragment_params = parse_qs(parsed.fragment)
        if 'access_token' in fragment_params:
            result['access_token'] = fragment_params['access_token'][0]
        if 'token_type' in fragment_params:
            result['token_type'] = fragment_params['token_type'][0]

    return result
