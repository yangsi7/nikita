"""Phase 3: Portal Access Flow."""

from typing import Any, Dict, Optional
from dataclasses import dataclass

from ...helpers.otp_email_parser import OTPEmailParser
from ..evidence_collector import EvidenceCollector
from ...portal.page_objects import LoginPage, DashboardPage


@dataclass
class Phase3Result:
    """Result of Phase 3 execution."""
    success: bool
    dashboard_score: Optional[float] = None
    dashboard_chapter: Optional[int] = None
    engagement_state: Optional[str] = None
    error: Optional[str] = None


class Phase3Portal:
    """
    Phase 3: Portal Access via Magic Link

    Steps:
    1. Navigate to portal login
    2. Submit email
    3. Wait for magic link (Gmail MCP)
    4. Navigate to magic link
    5. Verify dashboard loads
    6. Extract dashboard data
    """

    def __init__(self, portal_url: str = "https://portal-yangsi7s-projects.vercel.app"):
        self.login_page = LoginPage(base_url=portal_url)
        self.dashboard_page = DashboardPage(base_url=portal_url)
        self.parser = OTPEmailParser

    # ==================== Step 1: Navigate to Login ====================

    def get_login_navigate_command(self) -> dict:
        """Get Playwright navigate command for login."""
        return self.login_page.navigate_to_login()

    # ==================== Step 2: Submit Email ====================

    def get_submit_email_js(self, email: str) -> str:
        """Get JavaScript to submit email."""
        return self.login_page.js_submit_form(email)

    def get_wait_for_magic_link_sent_js(self) -> str:
        """Get JavaScript to wait for success message."""
        return self.login_page.js_wait_for_magic_link_sent()

    # ==================== Step 3: Magic Link Email ====================

    def get_magic_link_search_query(self, email: str, since_timestamp: float) -> str:
        """Get Gmail search query for magic link."""
        return self.parser.build_magic_link_search_query(email, since_timestamp)

    def extract_magic_link(self, email_body: str) -> Optional[str]:
        """Extract magic link URL from email body."""
        return self.parser.extract_magic_link(email_body)

    # ==================== Step 4: Navigate to Magic Link ====================

    def get_magic_link_navigate_command(self, magic_link_url: str) -> dict:
        """Get Playwright navigate command for magic link."""
        return {"url": magic_link_url}

    # ==================== Step 5: Wait for Dashboard ====================

    def get_wait_for_dashboard_js(self) -> str:
        """Get JavaScript to wait for dashboard."""
        return self.dashboard_page.js_wait_for_dashboard_loaded()

    # ==================== Step 6: Extract Dashboard Data ====================

    def get_extract_data_js(self) -> str:
        """Get JavaScript to extract dashboard data."""
        return self.dashboard_page.js_get_all_dashboard_data()

    def process_dashboard_data(self, data: Dict[str, Any]) -> Phase3Result:
        """Process extracted dashboard data."""
        if data.get('error'):
            return Phase3Result(success=False, error=data['error'])

        if data.get('loading'):
            return Phase3Result(success=False, error="Dashboard still loading")

        return Phase3Result(
            success=True,
            dashboard_score=data.get('relationship_score'),
            dashboard_chapter=data.get('chapter'),
            engagement_state=data.get('engagement_state'),
        )

    # ==================== Screenshot ====================

    def get_screenshot_command(self, name: str = "portal_dashboard") -> dict:
        """Get Playwright screenshot command."""
        return self.dashboard_page.screenshot_command(name)
