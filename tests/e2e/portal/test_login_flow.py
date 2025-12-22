"""
Portal Login Flow E2E Tests

Tests the magic link login flow:
1. Navigate to login page
2. Enter email
3. Submit form
4. Wait for magic link email via Gmail MCP
5. Extract magic link URL
6. Navigate to magic link
7. Verify redirect to dashboard

For Claude Code execution:
- Playwright MCP: mcp__playwright__playwright_navigate, mcp__playwright__playwright_evaluate
- Gmail MCP: mcp__gmail__search_emails, mcp__gmail__read_email
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import pytest

from .page_objects import LoginPage, DashboardPage
from ..helpers.otp_email_parser import OTPEmailParser


# Configuration
TEST_EMAIL_BASE = "simon.yang.ch@gmail.com"
PORTAL_URL = os.getenv(
    "PORTAL_URL",
    "https://portal-yangsi7s-projects.vercel.app"
)


@dataclass
class PortalLoginTestContext:
    """Context for portal login E2E test."""
    test_email: str
    timestamp_before_login: float = field(default_factory=time.time)

    # Collected during test
    magic_link_url: Optional[str] = None
    magic_link_email_id: Optional[str] = None
    pkce_code: Optional[str] = None

    # Page states
    login_page_loaded: bool = False
    magic_link_sent: bool = False
    dashboard_loaded: bool = False
    dashboard_data: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, email: str = TEST_EMAIL_BASE) -> "PortalLoginTestContext":
        """Create a new test context."""
        return cls(test_email=email)


class PortalLoginE2ETest:
    """
    Portal Login E2E Test orchestrator.

    This class provides structured steps for the login flow test.
    When run from Claude Code, Playwright MCP and Gmail MCP calls are made externally.

    Usage (Claude Code):
        1. Create context: ctx = PortalLoginTestContext.create()
        2. Step 1: Navigate to login page
           - mcp__playwright__playwright_navigate(url=login_page.url("/"))
        3. Step 2: Enter email and submit
           - mcp__playwright__playwright_evaluate(script=login_page.js_submit_form(email))
        4. Step 3: Wait for magic link email
           - query = OTPEmailParser.build_magic_link_search_query(email, timestamp)
           - mcp__gmail__search_emails(query=query)
           - Extract magic link URL from email
        5. Step 4: Navigate to magic link
           - mcp__playwright__playwright_navigate(url=magic_link_url)
        6. Step 5: Verify dashboard loaded
           - mcp__playwright__playwright_evaluate(script=dashboard_page.js_is_loaded())
        7. Step 6: Extract dashboard data
           - mcp__playwright__playwright_evaluate(script=dashboard_page.js_get_all_dashboard_data())
    """

    def __init__(self):
        """Initialize login test orchestrator."""
        self.login_page = LoginPage(base_url=PORTAL_URL)
        self.dashboard_page = DashboardPage(base_url=PORTAL_URL)
        self.parser = OTPEmailParser

    # ==================== Step 1: Navigate to Login ====================

    def step1_navigate_command(self) -> dict:
        """Get Playwright navigate command for login page.

        Returns:
            Dict for mcp__playwright__playwright_navigate
        """
        return self.login_page.navigate_to_login()

    def step1_verify_js(self) -> str:
        """Get JavaScript to verify login page loaded.

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.login_page.js_is_on_login_page()

    # ==================== Step 2: Submit Email ====================

    def step2_submit_js(self, email: str) -> str:
        """Get JavaScript to submit login form.

        Args:
            email: Email address to submit

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.login_page.js_submit_form(email)

    def step2_wait_for_success_js(self) -> str:
        """Get JavaScript to wait for magic link success message.

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.login_page.js_wait_for_magic_link_sent()

    # ==================== Step 3: Wait for Magic Link Email ====================

    def step3_build_gmail_query(self, ctx: PortalLoginTestContext) -> str:
        """Build Gmail search query for magic link email.

        Args:
            ctx: Test context with timestamp

        Returns:
            Gmail search query string
        """
        query = self.parser.build_magic_link_search_query(
            recipient_email=ctx.test_email,
            after_timestamp=ctx.timestamp_before_login,
        )
        print(f"[Step 3] Gmail query: {query}")
        return query

    def step3_extract_magic_link(self, ctx: PortalLoginTestContext, email_body: str) -> Optional[str]:
        """Extract magic link URL from email body.

        Args:
            ctx: Test context to update
            email_body: Raw email body content

        Returns:
            Magic link URL or None
        """
        url = self.parser.extract_magic_link(email_body)
        if url:
            ctx.magic_link_url = url
            ctx.pkce_code = self.parser.extract_pkce_code(url)
            print(f"[Step 3] Magic link found: {url[:80]}...")
            if ctx.pkce_code:
                print(f"[Step 3] PKCE code: {ctx.pkce_code[:20]}...")
        return url

    # ==================== Step 4: Navigate to Magic Link ====================

    def step4_navigate_command(self, ctx: PortalLoginTestContext) -> Optional[dict]:
        """Get Playwright navigate command for magic link.

        Args:
            ctx: Test context with magic link URL

        Returns:
            Dict for mcp__playwright__playwright_navigate or None if no URL
        """
        if not ctx.magic_link_url:
            print("[Step 4] ERROR: No magic link URL available")
            return None
        return {"url": ctx.magic_link_url}

    # ==================== Step 5: Verify Dashboard ====================

    def step5_wait_for_dashboard_js(self) -> str:
        """Get JavaScript to wait for dashboard to load.

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.dashboard_page.js_wait_for_dashboard_loaded()

    def step5_verify_dashboard_js(self) -> str:
        """Get JavaScript to verify dashboard is loaded.

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.dashboard_page.js_is_loaded()

    # ==================== Step 6: Extract Dashboard Data ====================

    def step6_extract_data_js(self) -> str:
        """Get JavaScript to extract dashboard data.

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.dashboard_page.js_get_all_dashboard_data()

    def step6_process_data(self, ctx: PortalLoginTestContext, data: Dict[str, Any]) -> bool:
        """Process extracted dashboard data.

        Args:
            ctx: Test context to update
            data: Dashboard data from JavaScript

        Returns:
            True if data looks valid
        """
        ctx.dashboard_data = data

        if data.get('error'):
            print(f"[Step 6] ERROR: {data['error']}")
            return False

        if data.get('loading'):
            print("[Step 6] Dashboard still loading")
            return False

        print(f"[Step 6] Dashboard data extracted:")
        print(f"  Score: {data.get('relationship_score')}")
        print(f"  Chapter: {data.get('chapter')}")
        print(f"  Engagement: {data.get('engagement_state')}")

        return data.get('relationship_score') is not None

    # ==================== Complete Flow ====================

    def get_complete_flow_instructions(self, ctx: PortalLoginTestContext) -> List[dict]:
        """Get complete flow instructions for Claude Code execution.

        Args:
            ctx: Test context

        Returns:
            List of step instructions with MCP commands
        """
        return [
            {
                "step": 1,
                "name": "Navigate to Login",
                "mcp": "mcp__playwright__playwright_navigate",
                "params": self.step1_navigate_command(),
            },
            {
                "step": 1.1,
                "name": "Verify Login Page",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step1_verify_js()},
                "expected": True,
            },
            {
                "step": 2,
                "name": "Submit Email",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step2_submit_js(ctx.test_email)},
            },
            {
                "step": 2.1,
                "name": "Wait for Magic Link Sent",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step2_wait_for_success_js()},
            },
            {
                "step": 3,
                "name": "Search for Magic Link Email",
                "mcp": "mcp__gmail__search_emails",
                "params": {"query": self.step3_build_gmail_query(ctx), "maxResults": 5},
                "note": "Poll until email found or timeout",
            },
            {
                "step": 3.1,
                "name": "Read Magic Link Email",
                "mcp": "mcp__gmail__read_email",
                "params": {"messageId": "<from step 3>"},
                "note": "Extract magic link URL from email body",
            },
            {
                "step": 4,
                "name": "Navigate to Magic Link",
                "mcp": "mcp__playwright__playwright_navigate",
                "params": {"url": "<magic_link_url from step 3.1>"},
            },
            {
                "step": 5,
                "name": "Wait for Dashboard",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step5_wait_for_dashboard_js()},
            },
            {
                "step": 6,
                "name": "Extract Dashboard Data",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step6_extract_data_js()},
            },
            {
                "step": 7,
                "name": "Screenshot",
                "mcp": "mcp__playwright__playwright_screenshot",
                "params": {"name": "portal_dashboard_after_login"},
            },
        ]


# ==================== Pytest Tests ====================

class TestPortalLoginPageObjects:
    """Test page object methods work correctly."""

    def test_login_page_url(self, login_page):
        """Test login page URL generation."""
        assert login_page.url("/") == f"{PORTAL_URL}/"
        assert login_page.url("/dashboard") == f"{PORTAL_URL}/dashboard"

    def test_login_js_generation(self, login_page):
        """Test JavaScript generation for login actions."""
        email = "test@example.com"

        enter_js = login_page.js_enter_email(email)
        assert email in enter_js
        assert "input" in enter_js.lower()

        submit_js = login_page.js_submit_form(email)
        assert email in submit_js
        assert "click" in submit_js.lower()

    def test_login_sequence_generation(self, login_page):
        """Test login sequence generation."""
        email = "test@example.com"
        sequence = login_page.build_login_sequence(email)

        assert len(sequence) >= 4
        assert sequence[0]["step"] == "navigate"
        assert sequence[-1]["step"] == "wait_for_result"


class TestPortalDashboardPageObjects:
    """Test dashboard page object methods."""

    def test_dashboard_url(self, dashboard_page):
        """Test dashboard page URL generation."""
        assert dashboard_page.url("/dashboard") == f"{PORTAL_URL}/dashboard"

    def test_dashboard_js_generation(self, dashboard_page):
        """Test JavaScript generation for dashboard."""
        score_js = dashboard_page.js_get_relationship_score()
        assert "score" in score_js.lower() or "text-5xl" in score_js

        chapter_js = dashboard_page.js_get_chapter()
        assert "chapter" in chapter_js.lower()

        data_js = dashboard_page.js_get_all_dashboard_data()
        assert "relationship_score" in data_js
        assert "chapter" in data_js


class TestPortalLoginFlow:
    """Test login flow orchestration."""

    def test_flow_instructions_generation(self, test_email):
        """Test complete flow instructions generation."""
        ctx = PortalLoginTestContext.create(email=test_email)
        test = PortalLoginE2ETest()

        instructions = test.get_complete_flow_instructions(ctx)

        assert len(instructions) >= 7
        assert instructions[0]["mcp"] == "mcp__playwright__playwright_navigate"

        # Verify Gmail step exists
        gmail_steps = [i for i in instructions if "gmail" in i["mcp"]]
        assert len(gmail_steps) >= 1

    def test_magic_link_extraction(self, test_email):
        """Test magic link extraction from email body."""
        ctx = PortalLoginTestContext.create(email=test_email)
        test = PortalLoginE2ETest()

        # Sample email body with magic link
        sample_body = """
        <html>
        <body>
        Click <a href="https://vlvlwmolfdpzdfmtipji.supabase.co/auth/v1/verify?token=abc123&amp;type=magiclink&amp;redirect_to=https://portal.example.com">here</a> to sign in.
        </body>
        </html>
        """

        url = test.step3_extract_magic_link(ctx, sample_body)
        assert url is not None
        assert "supabase.co/auth" in url
        assert ctx.magic_link_url == url
