"""Phase 2: Real Conversation Flow."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ...helpers.telegram_helper import TelegramWebhookSimulator
from ...helpers.supabase_helper import SupabaseHelper
from ..evidence_collector import EvidenceCollector


@dataclass
class Phase2Result:
    """Result of Phase 2 execution."""
    success: bool
    conversation_count: int = 0
    message_count: int = 0
    responses: List[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.responses is None:
            self.responses = []


class Phase2Conversation:
    """
    Phase 2: Real Conversation with Claude

    Uses REAL Claude API calls - no mocking.
    Verifies conversation and messages are stored.
    """

    SAMPLE_MESSAGES = [
        "Hey Nikita, how are you today?",
        "I've been thinking about you a lot",
        "What should we do this weekend?",
    ]

    def __init__(self, secret_token: Optional[str] = None):
        self.simulator = TelegramWebhookSimulator(secret_token=secret_token)
        self.db_helper = SupabaseHelper()

    async def execute_message(
        self,
        message: str,
        telegram_id: int,
        evidence: Optional[EvidenceCollector] = None,
        step_name: str = "message"
    ) -> bool:
        """Send a message and wait for response."""
        response = await self.simulator.send_message(message, telegram_id)

        if evidence:
            evidence.add_api_response(
                step_name,
                "/telegram/webhook",
                response.status_code,
                response.text,
                step_name
            )

        return response.status_code == 200

    async def execute_all_messages(
        self,
        telegram_id: int,
        evidence: Optional[EvidenceCollector] = None,
        wait_between: float = 2.0
    ) -> List[bool]:
        """Execute all sample messages."""
        import asyncio
        results = []

        for i, msg in enumerate(self.SAMPLE_MESSAGES):
            success = await self.execute_message(
                msg,
                telegram_id,
                evidence,
                f"message_{i+1}"
            )
            results.append(success)

            if wait_between > 0:
                await asyncio.sleep(wait_between)

        return results

    def get_conversation_verification_query(self, telegram_id: int) -> str:
        """Get SQL query to verify conversations exist."""
        return self.db_helper.sql_verify_conversation_exists(telegram_id)

    def get_message_count_query(self, telegram_id: int) -> str:
        """Get SQL query to count messages."""
        return self.db_helper.sql_count_messages_by_telegram_id(telegram_id)

    def verify_conversation(self, db_result: Any) -> Phase2Result:
        """Verify conversation from DB result."""
        rows = self.db_helper.parse_mcp_result(db_result)

        if not rows:
            return Phase2Result(success=False, error="No data returned")

        row = rows[0]
        conv_count = row.get('conversation_count', 0)
        msg_count = row.get('message_count', 0)

        if conv_count >= 1 and msg_count >= 2:
            return Phase2Result(
                success=True,
                conversation_count=conv_count,
                message_count=msg_count
            )
        else:
            return Phase2Result(
                success=False,
                conversation_count=conv_count,
                message_count=msg_count,
                error=f"Expected >=1 conversation and >=2 messages, got {conv_count} and {msg_count}"
            )
