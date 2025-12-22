"""
Dashboard Page Object for Portal E2E Tests

Handles dashboard data verification.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from .base_page import BasePage, PORTAL_URL


@dataclass
class DashboardData:
    """Dashboard data snapshot."""
    relationship_score: Optional[float] = None
    chapter: Optional[int] = None
    engagement_state: Optional[str] = None
    game_status: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    loading: bool = False
    error: Optional[str] = None


class DashboardPage(BasePage):
    """
    Page object for the portal dashboard page.

    Key elements:
    - Relationship score (in ScoreCard)
    - Chapter number (in ChapterCard)
    - Engagement state (in EngagementCard)
    - Metrics grid (intimacy, passion, trust, secureness)
    - Sign out button
    """

    # ==================== Selectors ====================

    # Header elements
    HEADER = "header"
    SITE_TITLE = "h1"  # "Nikita"
    SIGN_OUT_BUTTON = "text=Sign Out"

    # Loading states
    LOADING_INDICATOR = "text=Loading your relationship"
    ERROR_INDICATOR = "text=Failed to load dashboard"

    # Card selectors (based on component structure)
    SCORE_CARD = "[class*='ScoreCard']"  # May need adjustment based on actual output
    CHAPTER_CARD = "[class*='ChapterCard']"
    ENGAGEMENT_CARD = "[class*='EngagementCard']"

    # Score display (large number in ScoreCard)
    SCORE_VALUE = ".text-5xl.font-bold"  # The main score display

    def __init__(self, base_url: str = PORTAL_URL):
        """Initialize dashboard page."""
        super().__init__(base_url)

    # ==================== Navigation ====================

    def navigate_to_dashboard(self) -> dict:
        """Get navigation command for dashboard.

        Returns:
            Dict for mcp__playwright__playwright_navigate
        """
        return self.navigate_command("/dashboard")

    # ==================== Page State ====================

    def js_is_loading(self) -> str:
        """JavaScript to check if dashboard is in loading state.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            document.body.textContent?.includes('Loading your relationship') ||
            document.querySelector('.animate-pulse') !== null
        """

    def js_has_error(self) -> str:
        """JavaScript to check if dashboard has error.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            document.body.textContent?.includes('Failed to load dashboard')
        """

    def js_is_loaded(self) -> str:
        """JavaScript to check if dashboard is fully loaded.

        Returns:
            JavaScript code that returns boolean
        """
        return """
            !document.body.textContent?.includes('Loading your relationship') &&
            !document.body.textContent?.includes('Failed to load dashboard') &&
            document.querySelector('header') !== null &&
            document.body.textContent?.includes('Welcome Back')
        """

    # ==================== Data Extraction ====================

    def js_get_relationship_score(self) -> str:
        """JavaScript to extract relationship score.

        Looks for the large score number in the score card.

        Returns:
            JavaScript code that returns number or null
        """
        return """
            // Look for large bold number (the score)
            const scoreElements = document.querySelectorAll('.text-5xl, .text-4xl, .text-3xl');
            for (const el of scoreElements) {
                const text = el.textContent?.trim();
                const num = parseFloat(text);
                if (!isNaN(num) && num >= 0 && num <= 100) {
                    return num;
                }
            }
            // Fallback: look for any number near "Score" or "Relationship"
            const cards = document.querySelectorAll('[class*="Card"]');
            for (const card of cards) {
                if (card.textContent?.toLowerCase().includes('score')) {
                    const match = card.textContent.match(/(\d+(\.\d+)?)/);
                    if (match) {
                        return parseFloat(match[1]);
                    }
                }
            }
            return null;
        """

    def js_get_chapter(self) -> str:
        """JavaScript to extract current chapter.

        Returns:
            JavaScript code that returns number or null
        """
        return """
            // Look for "Chapter X" text
            const text = document.body.textContent;
            const match = text?.match(/Chapter\\s*(\\d+)/i);
            if (match) {
                return parseInt(match[1]);
            }
            return null;
        """

    def js_get_engagement_state(self) -> str:
        """JavaScript to extract engagement state.

        Returns:
            JavaScript code that returns string or null
        """
        return """
            // Engagement states: optimal, healthy, engaged, clingy, distant, unavailable
            const states = ['optimal', 'healthy', 'engaged', 'clingy', 'distant', 'unavailable'];
            const text = document.body.textContent?.toLowerCase() || '';
            for (const state of states) {
                if (text.includes(state)) {
                    return state;
                }
            }
            return null;
        """

    def js_get_metrics(self) -> str:
        """JavaScript to extract all metrics.

        Returns:
            JavaScript code that returns object or null
        """
        return """
            const metrics = {};
            const metricNames = ['intimacy', 'passion', 'trust', 'secureness'];

            for (const name of metricNames) {
                // Find element containing metric name and nearby number
                const regex = new RegExp(name + '.*?(\\d+(\\.\\d+)?)', 'i');
                const match = document.body.textContent?.match(regex);
                if (match) {
                    metrics[name] = parseFloat(match[1]);
                }
            }

            return Object.keys(metrics).length > 0 ? metrics : null;
        """

    def js_get_all_dashboard_data(self) -> str:
        """JavaScript to extract all dashboard data at once.

        Returns:
            JavaScript code that returns object
        """
        return """
            const data = {
                loading: false,
                error: null,
                relationship_score: null,
                chapter: null,
                engagement_state: null,
                game_status: null,
                metrics: null
            };

            // Check loading/error states
            if (document.body.textContent?.includes('Loading your relationship')) {
                data.loading = true;
                return data;
            }
            if (document.body.textContent?.includes('Failed to load dashboard')) {
                data.error = 'Failed to load dashboard';
                return data;
            }

            // Extract relationship score
            const scoreElements = document.querySelectorAll('.text-5xl, .text-4xl, .text-3xl');
            for (const el of scoreElements) {
                const num = parseFloat(el.textContent?.trim());
                if (!isNaN(num) && num >= 0 && num <= 100) {
                    data.relationship_score = num;
                    break;
                }
            }

            // Extract chapter
            const chapterMatch = document.body.textContent?.match(/Chapter\\s*(\\d+)/i);
            if (chapterMatch) {
                data.chapter = parseInt(chapterMatch[1]);
            }

            // Extract engagement state
            const states = ['optimal', 'healthy', 'engaged', 'clingy', 'distant', 'unavailable'];
            const text = document.body.textContent?.toLowerCase() || '';
            for (const state of states) {
                if (text.includes(state)) {
                    data.engagement_state = state;
                    break;
                }
            }

            // Extract game status
            const statuses = ['active', 'boss_fight', 'dumped', 'complete'];
            for (const status of statuses) {
                if (text.includes(status.replace('_', ' '))) {
                    data.game_status = status;
                    break;
                }
            }

            // Extract metrics
            const metrics = {};
            const metricNames = ['intimacy', 'passion', 'trust', 'secureness'];
            for (const name of metricNames) {
                const regex = new RegExp(name + '.*?(\\d+(\\.\\d+)?)', 'i');
                const match = document.body.textContent?.match(regex);
                if (match) {
                    metrics[name] = parseFloat(match[1]);
                }
            }
            if (Object.keys(metrics).length > 0) {
                data.metrics = metrics;
            }

            return data;
        """

    # ==================== Actions ====================

    def js_click_sign_out(self) -> str:
        """JavaScript to click sign out button.

        Returns:
            JavaScript code string
        """
        return """
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent?.includes('Sign Out')) {
                    btn.click();
                    return true;
                }
            }
            return false;
        """

    def js_navigate_to_conversations(self) -> str:
        """JavaScript to click conversations link.

        Returns:
            JavaScript code string
        """
        return """
            const links = document.querySelectorAll('a, button');
            for (const link of links) {
                if (link.textContent?.toLowerCase().includes('conversation') ||
                    link.href?.includes('/conversation')) {
                    link.click();
                    return true;
                }
            }
            return false;
        """

    def js_navigate_to_history(self) -> str:
        """JavaScript to click history link.

        Returns:
            JavaScript code string
        """
        return """
            const links = document.querySelectorAll('a, button');
            for (const link of links) {
                if (link.textContent?.toLowerCase().includes('history') ||
                    link.href?.includes('/history')) {
                    link.click();
                    return true;
                }
            }
            return false;
        """

    # ==================== Verification ====================

    def js_wait_for_dashboard_loaded(self, timeout_ms: int = 30000) -> str:
        """JavaScript to wait for dashboard to fully load.

        Args:
            timeout_ms: Maximum wait time in milliseconds

        Returns:
            JavaScript code that returns a promise
        """
        return f"""
            new Promise((resolve, reject) => {{
                const startTime = Date.now();
                const check = () => {{
                    // Check for error
                    if (document.body.textContent?.includes('Failed to load dashboard')) {{
                        reject(new Error('Dashboard failed to load'));
                        return;
                    }}
                    // Check for loaded state
                    if (document.body.textContent?.includes('Welcome Back') &&
                        document.querySelector('header') !== null &&
                        !document.body.textContent?.includes('Loading your relationship')) {{
                        resolve(true);
                        return;
                    }}
                    // Timeout check
                    if (Date.now() - startTime > {timeout_ms}) {{
                        reject(new Error('Timeout waiting for dashboard to load'));
                        return;
                    }}
                    setTimeout(check, 200);
                }};
                check();
            }});
        """

    # ==================== Composite Operations ====================

    def build_verification_sequence(self) -> list:
        """Build sequence of operations to verify dashboard data.

        Returns:
            List of steps with JS code for each operation
        """
        return [
            {
                "step": "navigate",
                "command": self.navigate_command("/dashboard"),
                "description": "Navigate to dashboard",
            },
            {
                "step": "wait_for_load",
                "js": self.js_wait_for_dashboard_loaded(),
                "description": "Wait for dashboard to load",
            },
            {
                "step": "extract_data",
                "js": self.js_get_all_dashboard_data(),
                "description": "Extract all dashboard data",
            },
            {
                "step": "screenshot",
                "command": self.screenshot_command("dashboard"),
                "description": "Take screenshot of dashboard",
            },
        ]
