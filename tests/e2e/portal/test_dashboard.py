"""
Portal Dashboard E2E Tests

Tests dashboard data verification:
1. Navigate to dashboard (requires authenticated session)
2. Verify dashboard loads successfully
3. Extract and validate relationship score
4. Extract and validate chapter info
5. Extract engagement state
6. Verify metrics display

For Claude Code execution:
- Playwright MCP: mcp__playwright__playwright_navigate, mcp__playwright__playwright_evaluate, mcp__playwright__playwright_screenshot
- Supabase MCP: mcp__supabase__execute_sql (for data verification)
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import pytest

from .page_objects import DashboardPage
from ..helpers.supabase_helper import SupabaseHelper


# Configuration
PORTAL_URL = os.getenv(
    "PORTAL_URL",
    "https://portal-yangsi7s-projects.vercel.app"
)


@dataclass
class DashboardTestContext:
    """Context for dashboard E2E test."""
    telegram_id: Optional[int] = None  # If testing for specific user

    # UI extracted data
    ui_score: Optional[float] = None
    ui_chapter: Optional[int] = None
    ui_engagement: Optional[str] = None
    ui_metrics: Optional[Dict[str, float]] = None

    # DB verified data
    db_score: Optional[float] = None
    db_chapter: Optional[int] = None

    # Test states
    dashboard_loaded: bool = False
    data_matches: bool = False
    error: Optional[str] = None


class DashboardE2ETest:
    """
    Dashboard E2E Test orchestrator.

    Provides structured steps for dashboard verification.
    Compares UI data with database values for accuracy.
    """

    def __init__(self):
        """Initialize dashboard test orchestrator."""
        self.dashboard_page = DashboardPage(base_url=PORTAL_URL)
        self.db_helper = SupabaseHelper()

    # ==================== Step 1: Navigate to Dashboard ====================

    def step1_navigate_command(self) -> dict:
        """Get Playwright navigate command for dashboard.

        Returns:
            Dict for mcp__playwright__playwright_navigate
        """
        return self.dashboard_page.navigate_to_dashboard()

    # ==================== Step 2: Wait for Load ====================

    def step2_wait_js(self) -> str:
        """Get JavaScript to wait for dashboard load.

        Returns:
            JavaScript code for mcp__playwright__playwright_evaluate
        """
        return self.dashboard_page.js_wait_for_dashboard_loaded()

    def step2_verify_loaded_js(self) -> str:
        """Get JavaScript to verify dashboard loaded.

        Returns:
            JavaScript code
        """
        return self.dashboard_page.js_is_loaded()

    # ==================== Step 3: Extract UI Data ====================

    def step3_extract_all_js(self) -> str:
        """Get JavaScript to extract all dashboard data.

        Returns:
            JavaScript code
        """
        return self.dashboard_page.js_get_all_dashboard_data()

    def step3_process_ui_data(self, ctx: DashboardTestContext, data: Dict[str, Any]) -> bool:
        """Process extracted UI data into context.

        Args:
            ctx: Test context to update
            data: Dashboard data from JavaScript

        Returns:
            True if extraction successful
        """
        if data.get('error'):
            ctx.error = data['error']
            return False

        if data.get('loading'):
            ctx.error = "Dashboard still loading"
            return False

        ctx.ui_score = data.get('relationship_score')
        ctx.ui_chapter = data.get('chapter')
        ctx.ui_engagement = data.get('engagement_state')
        ctx.ui_metrics = data.get('metrics')
        ctx.dashboard_loaded = True

        print(f"[Step 3] UI Data Extracted:")
        print(f"  Score: {ctx.ui_score}")
        print(f"  Chapter: {ctx.ui_chapter}")
        print(f"  Engagement: {ctx.ui_engagement}")
        print(f"  Metrics: {ctx.ui_metrics}")

        return ctx.ui_score is not None

    # ==================== Step 4: Verify with Database ====================

    def step4_db_query(self, telegram_id: int) -> str:
        """Get SQL query to fetch user data for verification.

        Args:
            telegram_id: Telegram ID of user

        Returns:
            SQL query string
        """
        return self.db_helper.sql_get_user_metrics(telegram_id)

    def step4_verify_data(
        self,
        ctx: DashboardTestContext,
        db_result: Any,
        tolerance: float = 0.1
    ) -> bool:
        """Verify UI data matches database.

        Args:
            ctx: Test context with UI data
            db_result: Result from Supabase query
            tolerance: Acceptable difference for score comparison

        Returns:
            True if data matches within tolerance
        """
        rows = self.db_helper.parse_mcp_result(db_result)
        if not rows:
            print("[Step 4] No database data found")
            return False

        row = rows[0]
        ctx.db_score = row.get('relationship_score')
        ctx.db_chapter = row.get('chapter')

        print(f"[Step 4] DB Data:")
        print(f"  Score: {ctx.db_score}")
        print(f"  Chapter: {ctx.db_chapter}")

        # Compare with tolerance
        score_match = (
            ctx.ui_score is not None and
            ctx.db_score is not None and
            abs(ctx.ui_score - ctx.db_score) <= tolerance
        )

        chapter_match = ctx.ui_chapter == ctx.db_chapter

        ctx.data_matches = score_match and chapter_match

        if not score_match:
            print(f"[Step 4] Score mismatch: UI={ctx.ui_score}, DB={ctx.db_score}")
        if not chapter_match:
            print(f"[Step 4] Chapter mismatch: UI={ctx.ui_chapter}, DB={ctx.db_chapter}")

        return ctx.data_matches

    # ==================== Step 5: Screenshot ====================

    def step5_screenshot_command(self, name: str = "dashboard") -> dict:
        """Get Playwright screenshot command.

        Args:
            name: Screenshot name

        Returns:
            Dict for mcp__playwright__playwright_screenshot
        """
        return self.dashboard_page.screenshot_command(name)

    # ==================== Complete Verification ====================

    def get_verification_instructions(self, telegram_id: Optional[int] = None) -> List[dict]:
        """Get complete verification instructions for Claude Code.

        Args:
            telegram_id: Optional Telegram ID for DB verification

        Returns:
            List of step instructions
        """
        steps = [
            {
                "step": 1,
                "name": "Navigate to Dashboard",
                "mcp": "mcp__playwright__playwright_navigate",
                "params": self.step1_navigate_command(),
            },
            {
                "step": 2,
                "name": "Wait for Dashboard Load",
                "mcp": "mcp__playwright__playwright_evaluate",
                "params": {"script": self.step2_wait_js()},
            },
            {
                "step": 3,
                "name": "Extract Dashboard Data",
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
            "name": "Take Screenshot",
            "mcp": "mcp__playwright__playwright_screenshot",
            "params": {"name": "dashboard_verification"},
        })

        return steps


# ==================== Pytest Tests ====================

class TestDashboardPageObject:
    """Test dashboard page object methods."""

    def test_navigate_command(self, dashboard_page):
        """Test navigation command generation."""
        cmd = dashboard_page.navigate_to_dashboard()
        assert "url" in cmd
        assert "/dashboard" in cmd["url"]

    def test_js_extraction_methods(self, dashboard_page):
        """Test JavaScript extraction methods."""
        score_js = dashboard_page.js_get_relationship_score()
        assert "score" in score_js.lower() or "text" in score_js

        chapter_js = dashboard_page.js_get_chapter()
        assert "Chapter" in chapter_js

        all_js = dashboard_page.js_get_all_dashboard_data()
        assert "relationship_score" in all_js
        assert "chapter" in all_js
        assert "engagement_state" in all_js

    def test_wait_for_load_js(self, dashboard_page):
        """Test wait for load JavaScript."""
        wait_js = dashboard_page.js_wait_for_dashboard_loaded()
        assert "Promise" in wait_js
        assert "Welcome Back" in wait_js

    def test_verification_sequence(self, dashboard_page):
        """Test verification sequence generation."""
        sequence = dashboard_page.build_verification_sequence()
        assert len(sequence) >= 4
        assert sequence[0]["step"] == "navigate"
        assert any(s["step"] == "extract_data" for s in sequence)


class TestDashboardE2E:
    """Test dashboard E2E orchestration."""

    def test_verification_instructions(self):
        """Test verification instructions generation."""
        test = DashboardE2ETest()
        instructions = test.get_verification_instructions()

        assert len(instructions) >= 4
        assert instructions[0]["mcp"] == "mcp__playwright__playwright_navigate"
        assert any("screenshot" in i["mcp"] for i in instructions)

    def test_verification_with_telegram_id(self):
        """Test verification includes DB step when telegram_id provided."""
        test = DashboardE2ETest()
        instructions = test.get_verification_instructions(telegram_id=912345678)

        assert any("supabase" in i["mcp"] for i in instructions)

    def test_data_verification_logic(self):
        """Test data verification logic."""
        test = DashboardE2ETest()
        ctx = DashboardTestContext()

        # Set UI data
        ctx.ui_score = 50.0
        ctx.ui_chapter = 2

        # Matching DB data
        matching_result = [{"relationship_score": 50.0, "chapter": 2}]
        assert test.step4_verify_data(ctx, matching_result)
        assert ctx.data_matches

        # Mismatching DB data
        ctx2 = DashboardTestContext()
        ctx2.ui_score = 50.0
        ctx2.ui_chapter = 2
        mismatch_result = [{"relationship_score": 75.0, "chapter": 3}]
        assert not test.step4_verify_data(ctx2, mismatch_result)
        assert not ctx2.data_matches


class TestDashboardDataExtraction:
    """Test dashboard data extraction patterns."""

    def test_score_extraction_js(self, dashboard_page):
        """Test score extraction JavaScript handles various formats."""
        js = dashboard_page.js_get_relationship_score()

        # Should handle large text classes
        assert "text-5xl" in js or "text-4xl" in js

    def test_chapter_extraction_js(self, dashboard_page):
        """Test chapter extraction JavaScript."""
        js = dashboard_page.js_get_chapter()

        # Should match "Chapter X" pattern
        assert "Chapter" in js
        assert "match" in js

    def test_engagement_extraction_js(self, dashboard_page):
        """Test engagement state extraction JavaScript."""
        js = dashboard_page.js_get_engagement_state()

        # Should check for all engagement states
        for state in ["optimal", "healthy", "engaged", "clingy", "distant"]:
            assert state in js
