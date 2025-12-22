"""
Portal Conversations E2E Tests

Tests conversation history page:
1. Navigate to conversations page
2. Verify page loads
3. Check conversation list exists
4. Extract conversation data
5. Verify against database

For Claude Code execution:
- Playwright MCP: navigation, evaluation, screenshots
- Supabase MCP: conversation verification
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import pytest

from .page_objects import ConversationsPage, DashboardPage
from ..helpers.supabase_helper import SupabaseHelper


PORTAL_URL = os.getenv(
    "PORTAL_URL",
    "https://portal-yangsi7s-projects.vercel.app"
)


@dataclass
class ConversationsTestContext:
    """Context for conversations E2E test."""
    telegram_id: Optional[int] = None

    # UI data
    ui_conversation_count: int = 0
    ui_conversations: List[Dict[str, Any]] = None

    # DB data
    db_conversation_count: int = 0

    # Test states
    page_loaded: bool = False
    conversations_found: bool = False
    error: Optional[str] = None

    def __post_init__(self):
        if self.ui_conversations is None:
            self.ui_conversations = []


class ConversationsE2ETest:
    """Conversations E2E Test orchestrator."""

    def __init__(self):
        """Initialize conversations test."""
        self.conversations_page = ConversationsPage(base_url=PORTAL_URL)
        self.db_helper = SupabaseHelper()

    # ==================== Navigation ====================

    def step1_navigate_command(self) -> dict:
        """Get navigate command for conversations page."""
        return self.conversations_page.navigate_to_conversations()

    def step1_from_dashboard_js(self) -> str:
        """Get JavaScript to navigate from dashboard."""
        return DashboardPage(base_url=PORTAL_URL).js_navigate_to_conversations()

    # ==================== Wait and Verify ====================

    def step2_wait_js(self) -> str:
        """Get JavaScript to wait for page load."""
        return self.conversations_page.js_wait_for_conversations_loaded()

    def step2_verify_loaded_js(self) -> str:
        """Get JavaScript to verify page loaded."""
        return self.conversations_page.js_is_loaded()

    # ==================== Data Extraction ====================

    def step3_extract_all_js(self) -> str:
        """Get JavaScript to extract all data."""
        return self.conversations_page.js_get_all_conversations_data()

    def step3_process_data(self, ctx: ConversationsTestContext, data: Dict[str, Any]) -> bool:
        """Process extracted data into context."""
        if data.get('error'):
            ctx.error = data['error']
            return False

        if data.get('loading'):
            ctx.error = "Page still loading"
            return False

        ctx.ui_conversations = data.get('conversations', [])
        ctx.ui_conversation_count = data.get('total_count', 0)
        ctx.page_loaded = True
        ctx.conversations_found = ctx.ui_conversation_count > 0

        print(f"[Step 3] Extracted {ctx.ui_conversation_count} conversations")
        return True

    # ==================== Database Verification ====================

    def step4_db_query(self, telegram_id: int) -> str:
        """Get SQL query for conversation verification."""
        return self.db_helper.sql_verify_conversation_exists(telegram_id)

    def step4_verify(self, ctx: ConversationsTestContext, db_result: Any) -> bool:
        """Verify UI matches database."""
        rows = self.db_helper.parse_mcp_result(db_result)
        if not rows:
            return False

        row = rows[0]
        ctx.db_conversation_count = row.get('conversation_count', 0)

        print(f"[Step 4] DB: {ctx.db_conversation_count} conversations")

        # UI should show at least the conversations in DB
        return ctx.ui_conversation_count >= ctx.db_conversation_count

    # ==================== Complete Flow ====================

    def get_verification_instructions(self, telegram_id: Optional[int] = None) -> List[dict]:
        """Get verification instructions for Claude Code."""
        steps = [
            {
                "step": 1,
                "name": "Navigate to Conversations",
                "mcp": "mcp__playwright__playwright_navigate",
                "params": self.step1_navigate_command(),
            },
            {
                "step": 2,
                "name": "Wait for Load",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step2_wait_js()},
            },
            {
                "step": 3,
                "name": "Extract Data",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step3_extract_all_js()},
            },
        ]

        if telegram_id:
            steps.append({
                "step": 4,
                "name": "Verify with Database",
                "mcp": "mcp__supabase__execute_sql",
                "params": {"query": self.step4_db_query(telegram_id)},
            })

        steps.append({
            "step": 5,
            "name": "Screenshot",
            "mcp": "mcp__playwright__playwright_screenshot",
            "params": {"name": "conversations_page"},
        })

        return steps


# ==================== Pytest Tests ====================

class TestConversationsPageObject:
    """Test conversations page object."""

    def test_navigate_command(self, conversations_page):
        """Test navigation command."""
        cmd = conversations_page.navigate_to_conversations()
        assert "url" in cmd
        assert "/conversations" in cmd["url"]

    def test_extraction_js(self, conversations_page):
        """Test data extraction JavaScript."""
        js = conversations_page.js_get_all_conversations_data()
        assert "conversations" in js
        assert "loading" in js

    def test_verification_sequence(self, conversations_page):
        """Test verification sequence."""
        sequence = conversations_page.build_verification_sequence()
        assert len(sequence) >= 4


class TestConversationsE2E:
    """Test conversations E2E orchestration."""

    def test_verification_instructions(self):
        """Test verification instructions generation."""
        test = ConversationsE2ETest()
        instructions = test.get_verification_instructions()

        assert len(instructions) >= 4
        assert instructions[0]["mcp"] == "mcp__playwright__playwright_navigate"

    def test_data_processing(self):
        """Test data processing logic."""
        test = ConversationsE2ETest()
        ctx = ConversationsTestContext()

        # Test with conversations
        data = {
            "loading": False,
            "error": None,
            "conversations": [
                {"date": "12/20/2024", "message_count": 5},
                {"date": "12/19/2024", "message_count": 3},
            ],
            "total_count": 2,
        }

        assert test.step3_process_data(ctx, data)
        assert ctx.ui_conversation_count == 2
        assert ctx.conversations_found

    def test_empty_conversations(self):
        """Test handling of no conversations."""
        test = ConversationsE2ETest()
        ctx = ConversationsTestContext()

        data = {
            "loading": False,
            "error": None,
            "conversations": [],
            "total_count": 0,
        }

        assert test.step3_process_data(ctx, data)
        assert ctx.ui_conversation_count == 0
        assert not ctx.conversations_found
