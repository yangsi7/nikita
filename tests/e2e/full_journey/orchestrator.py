"""
Full Journey Orchestrator

State machine controller for complete user journey E2E tests.
Coordinates all phases: Registration → Conversation → Portal → Game State
"""

import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from ..helpers.telegram_helper import TelegramWebhookSimulator, generate_test_telegram_id
from ..helpers.supabase_helper import SupabaseHelper
from ..helpers.otp_email_parser import OTPEmailParser
from .evidence_collector import EvidenceCollector


class JourneyState(Enum):
    """States in the journey state machine."""
    INITIAL = auto()
    REGISTRATION_STARTED = auto()
    EMAIL_SUBMITTED = auto()
    OTP_RECEIVED = auto()
    USER_CREATED = auto()
    FIRST_MESSAGE_SENT = auto()
    CONVERSATION_ACTIVE = auto()
    PORTAL_LOGIN_STARTED = auto()
    MAGIC_LINK_RECEIVED = auto()
    PORTAL_LOGGED_IN = auto()
    DASHBOARD_VERIFIED = auto()
    GAME_STATE_VERIFIED = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class JourneyContext:
    """Context maintained throughout the journey."""
    # Test identifiers
    telegram_id: int = field(default_factory=generate_test_telegram_id)
    test_email: str = ""
    test_id: str = field(default_factory=lambda: f"journey_{int(time.time())}")

    # State tracking
    state: JourneyState = JourneyState.INITIAL
    states_history: List[JourneyState] = field(default_factory=list)

    # Phase 1: Registration
    otp_code: Optional[str] = None
    otp_email_id: Optional[str] = None
    user_id: Optional[str] = None
    registration_timestamp: Optional[float] = None

    # Phase 2: Conversation
    first_message: Optional[str] = None
    first_response: Optional[str] = None
    conversation_id: Optional[str] = None
    message_count: int = 0

    # Phase 3: Portal
    magic_link_url: Optional[str] = None
    portal_session_token: Optional[str] = None
    dashboard_score: Optional[float] = None
    dashboard_chapter: Optional[int] = None

    # Phase 4: Game State
    game_status: Optional[str] = None
    engagement_state: Optional[str] = None

    # Error tracking
    error: Optional[str] = None
    failed_phase: Optional[str] = None

    def __post_init__(self):
        if not self.test_email:
            self.test_email = SupabaseHelper.generate_test_email(
                "simon.yang.ch@gmail.com",
                self.telegram_id
            )

    def transition_to(self, new_state: JourneyState):
        """Transition to a new state."""
        self.states_history.append(self.state)
        self.state = new_state

    def fail(self, error: str, phase: str):
        """Mark journey as failed."""
        self.error = error
        self.failed_phase = phase
        self.transition_to(JourneyState.FAILED)


class FullJourneyOrchestrator:
    """
    Orchestrates the complete user journey E2E test.

    Phases:
    1. Registration (OTP via Gmail MCP)
    2. Conversation (Real Claude API calls)
    3. Portal Access (Playwright + Gmail MCP)
    4. Game State Verification (Optional)

    Usage (Claude Code):
        orchestrator = FullJourneyOrchestrator()
        ctx = orchestrator.create_context()

        # Phase 1
        instructions = orchestrator.get_phase1_instructions(ctx)
        # Execute via MCP tools, update ctx

        # Phase 2
        instructions = orchestrator.get_phase2_instructions(ctx)
        # Execute via webhook calls

        # Phase 3
        instructions = orchestrator.get_phase3_instructions(ctx)
        # Execute via Playwright + Gmail MCP

        # Cleanup
        cleanup_sql = orchestrator.get_cleanup_sql(ctx)
    """

    def __init__(self, secret_token: Optional[str] = None):
        """Initialize orchestrator.

        Args:
            secret_token: Telegram webhook secret token
        """
        self.simulator = TelegramWebhookSimulator(secret_token=secret_token)
        self.db_helper = SupabaseHelper()
        self.parser = OTPEmailParser

    def create_context(self) -> JourneyContext:
        """Create a new journey context with unique IDs."""
        return JourneyContext()

    def create_evidence_collector(self, ctx: JourneyContext) -> EvidenceCollector:
        """Create evidence collector for this journey."""
        return EvidenceCollector(test_id=ctx.test_id)

    # ==================== Phase 1: Registration ====================

    def get_phase1_instructions(self, ctx: JourneyContext) -> List[Dict[str, Any]]:
        """Get Phase 1 (Registration) instructions.

        Returns list of steps with MCP commands to execute.
        """
        ctx.registration_timestamp = time.time()

        return [
            {
                "step": "1.1",
                "name": "Send /start command",
                "type": "webhook",
                "action": "send_command",
                "params": {
                    "command": "/start",
                    "telegram_id": ctx.telegram_id,
                },
                "expected_status": 200,
            },
            {
                "step": "1.2",
                "name": "Send email",
                "type": "webhook",
                "action": "send_message",
                "params": {
                    "text": ctx.test_email,
                    "telegram_id": ctx.telegram_id,
                },
                "expected_status": 200,
            },
            {
                "step": "1.3",
                "name": "Wait for OTP email",
                "type": "gmail_mcp",
                "action": "search_emails",
                "params": {
                    "query": self.parser.build_otp_search_query(
                        ctx.test_email,
                        ctx.registration_timestamp
                    ),
                    "maxResults": 5,
                },
                "poll": True,
                "timeout_seconds": 90,
                "poll_interval": 3,
            },
            {
                "step": "1.4",
                "name": "Read OTP email",
                "type": "gmail_mcp",
                "action": "read_email",
                "params": {
                    "messageId": "<from_step_1.3>",
                },
                "extract": {
                    "otp_code": "OTPEmailParser.extract_otp_code(email_body)",
                },
            },
            {
                "step": "1.5",
                "name": "Submit OTP code",
                "type": "webhook",
                "action": "send_message",
                "params": {
                    "text": "<otp_code_from_1.4>",
                    "telegram_id": ctx.telegram_id,
                },
                "expected_status": 200,
            },
            {
                "step": "1.6",
                "name": "Verify user created",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.db_helper.sql_verify_registration_complete(ctx.telegram_id),
                },
                "expected": {
                    "user_count": 1,
                    "pending_count": 0,
                    "metrics_count": 1,
                },
            },
        ]

    # ==================== Phase 2: Conversation ====================

    def get_phase2_instructions(self, ctx: JourneyContext) -> List[Dict[str, Any]]:
        """Get Phase 2 (Conversation) instructions.

        Uses REAL Claude API - no mocking.
        """
        sample_messages = [
            "Hey Nikita, how are you today?",
            "I've been thinking about you",
            "What do you want to do this weekend?",
        ]

        return [
            {
                "step": "2.1",
                "name": "Send first message",
                "type": "webhook",
                "action": "send_message",
                "params": {
                    "text": sample_messages[0],
                    "telegram_id": ctx.telegram_id,
                },
                "expected_status": 200,
                "wait_after": 2,  # Wait for agent response
            },
            {
                "step": "2.2",
                "name": "Verify conversation created",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.db_helper.sql_verify_conversation_exists(ctx.telegram_id),
                },
                "expected": {
                    "conversation_count_gte": 1,
                    "message_count_gte": 2,  # User + Agent
                },
            },
            {
                "step": "2.3",
                "name": "Send follow-up message",
                "type": "webhook",
                "action": "send_message",
                "params": {
                    "text": sample_messages[1],
                    "telegram_id": ctx.telegram_id,
                },
                "expected_status": 200,
                "wait_after": 2,
            },
            {
                "step": "2.4",
                "name": "Verify message count increased",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.db_helper.sql_count_messages_by_telegram_id(ctx.telegram_id),
                },
                "expected": {
                    "count_gte": 4,  # 2 user + 2 agent
                },
            },
        ]

    # ==================== Phase 3: Portal ====================

    def get_phase3_instructions(self, ctx: JourneyContext) -> List[Dict[str, Any]]:
        """Get Phase 3 (Portal Access) instructions."""
        portal_url = os.getenv(
            "PORTAL_URL",
            "https://portal-yangsi7s-projects.vercel.app"
        )

        return [
            {
                "step": "3.1",
                "name": "Navigate to login page",
                "type": "playwright_mcp",
                "action": "navigate",
                "params": {
                    "url": portal_url,
                },
            },
            {
                "step": "3.2",
                "name": "Enter email and submit",
                "type": "playwright_mcp",
                "action": "evaluate",
                "params": {
                    "script": f"""
                        const input = document.querySelector('input[type="email"]');
                        const button = document.querySelector('button[type="submit"]');
                        if (input && button) {{
                            input.value = '{ctx.test_email}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            button.click();
                            true;
                        }} else {{
                            false;
                        }}
                    """,
                },
            },
            {
                "step": "3.3",
                "name": "Wait for magic link email",
                "type": "gmail_mcp",
                "action": "search_emails",
                "params": {
                    "query": self.parser.build_magic_link_search_query(
                        ctx.test_email,
                        time.time(),
                    ),
                    "maxResults": 5,
                },
                "poll": True,
                "timeout_seconds": 60,
                "poll_interval": 3,
            },
            {
                "step": "3.4",
                "name": "Read magic link email",
                "type": "gmail_mcp",
                "action": "read_email",
                "params": {
                    "messageId": "<from_step_3.3>",
                },
                "extract": {
                    "magic_link_url": "OTPEmailParser.extract_magic_link(email_body)",
                },
            },
            {
                "step": "3.5",
                "name": "Navigate to magic link",
                "type": "playwright_mcp",
                "action": "navigate",
                "params": {
                    "url": "<magic_link_url_from_3.4>",
                },
            },
            {
                "step": "3.6",
                "name": "Wait for dashboard",
                "type": "playwright_mcp",
                "action": "evaluate",
                "params": {
                    "script": """
                        new Promise((resolve, reject) => {
                            const check = () => {
                                if (document.body.textContent?.includes('Welcome Back')) {
                                    resolve(true);
                                } else if (document.body.textContent?.includes('error')) {
                                    reject(new Error('Dashboard error'));
                                } else {
                                    setTimeout(check, 500);
                                }
                            };
                            setTimeout(check, 1000);
                        });
                    """,
                },
            },
            {
                "step": "3.7",
                "name": "Extract dashboard data",
                "type": "playwright_mcp",
                "action": "evaluate",
                "params": {
                    "script": """
                        const data = {};
                        // Extract score
                        const scoreEl = document.querySelector('.text-5xl, .text-4xl');
                        if (scoreEl) data.score = parseFloat(scoreEl.textContent);
                        // Extract chapter
                        const chapterMatch = document.body.textContent?.match(/Chapter\\s*(\\d+)/i);
                        if (chapterMatch) data.chapter = parseInt(chapterMatch[1]);
                        data;
                    """,
                },
            },
            {
                "step": "3.8",
                "name": "Screenshot dashboard",
                "type": "playwright_mcp",
                "action": "screenshot",
                "params": {
                    "name": f"dashboard_{ctx.telegram_id}",
                },
            },
        ]

    # ==================== Phase 4: Game State ====================

    def get_phase4_instructions(self, ctx: JourneyContext) -> List[Dict[str, Any]]:
        """Get Phase 4 (Game State) instructions."""
        return [
            {
                "step": "4.1",
                "name": "Get user metrics",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.db_helper.sql_get_user_metrics(ctx.telegram_id),
                },
            },
            {
                "step": "4.2",
                "name": "Verify score in valid range",
                "type": "verification",
                "check": "0 <= score <= 100",
            },
            {
                "step": "4.3",
                "name": "Get score history",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.db_helper.sql_get_score_history(ctx.telegram_id, 5),
                },
            },
            {
                "step": "4.4",
                "name": "Verify chapter matches score",
                "type": "verification",
                "check": "chapter_for_score(score) == chapter",
            },
        ]

    # ==================== Cleanup ====================

    def get_cleanup_sql(self, ctx: JourneyContext) -> str:
        """Get SQL to cleanup all test data."""
        return self.db_helper.sql_full_cleanup_by_telegram_id(ctx.telegram_id)

    def get_cleanup_instructions(self, ctx: JourneyContext) -> List[Dict[str, Any]]:
        """Get cleanup instructions."""
        return [
            {
                "step": "cleanup",
                "name": "Delete all test data",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.get_cleanup_sql(ctx),
                },
            },
            {
                "step": "verify_cleanup",
                "name": "Verify cleanup complete",
                "type": "supabase_mcp",
                "action": "execute_sql",
                "params": {
                    "query": self.db_helper.sql_count_users_by_telegram_id(ctx.telegram_id),
                },
                "expected": {
                    "count": 0,
                },
            },
        ]

    # ==================== Complete Journey ====================

    def get_all_instructions(
        self,
        ctx: JourneyContext,
        include_phase4: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all instructions organized by phase."""
        instructions = {
            "phase1_registration": self.get_phase1_instructions(ctx),
            "phase2_conversation": self.get_phase2_instructions(ctx),
            "phase3_portal": self.get_phase3_instructions(ctx),
        }

        if include_phase4:
            instructions["phase4_game_state"] = self.get_phase4_instructions(ctx)

        instructions["cleanup"] = self.get_cleanup_instructions(ctx)

        return instructions

    def print_instructions(
        self,
        ctx: JourneyContext,
        include_phase4: bool = False
    ):
        """Print all instructions for manual execution."""
        all_instructions = self.get_all_instructions(ctx, include_phase4)

        print("\n" + "=" * 60)
        print("FULL JOURNEY E2E TEST INSTRUCTIONS")
        print("=" * 60)
        print(f"Test ID: {ctx.test_id}")
        print(f"Telegram ID: {ctx.telegram_id}")
        print(f"Test Email: {ctx.test_email}")
        print("=" * 60)

        for phase_name, instructions in all_instructions.items():
            print(f"\n### {phase_name.upper()} ###")
            for instr in instructions:
                print(f"\n[{instr['step']}] {instr['name']}")
                print(f"  Type: {instr['type']}")
                if 'params' in instr:
                    for k, v in instr['params'].items():
                        if isinstance(v, str) and len(v) > 50:
                            print(f"  {k}: {v[:50]}...")
                        else:
                            print(f"  {k}: {v}")

        print("\n" + "=" * 60)
