"""Phase 1: OTP Registration Flow."""

from typing import Any, Dict, Optional
from dataclasses import dataclass

from ...helpers.telegram_helper import TelegramWebhookSimulator
from ...helpers.supabase_helper import SupabaseHelper
from ...helpers.otp_email_parser import OTPEmailParser
from ..evidence_collector import EvidenceCollector


@dataclass
class Phase1Result:
    """Result of Phase 1 execution."""
    success: bool
    user_id: Optional[str] = None
    otp_code: Optional[str] = None
    error: Optional[str] = None


class Phase1Registration:
    """
    Phase 1: OTP Registration

    Steps:
    1. /start command
    2. Email submission
    3. OTP retrieval (Gmail MCP)
    4. OTP submission
    5. User verification
    """

    def __init__(self, secret_token: Optional[str] = None):
        self.simulator = TelegramWebhookSimulator(secret_token=secret_token)
        self.db_helper = SupabaseHelper()
        self.parser = OTPEmailParser

    async def execute_step1_start(
        self,
        telegram_id: int,
        evidence: Optional[EvidenceCollector] = None
    ) -> bool:
        """Execute step 1: /start command."""
        response = await self.simulator.send_command("/start", telegram_id)

        if evidence:
            evidence.add_api_response(
                "start_command",
                "/telegram/webhook",
                response.status_code,
                response.text,
                "Step 1.1: /start"
            )

        return response.status_code == 200

    async def execute_step2_email(
        self,
        email: str,
        telegram_id: int,
        evidence: Optional[EvidenceCollector] = None
    ) -> bool:
        """Execute step 2: Email submission."""
        response = await self.simulator.send_message(email, telegram_id)

        if evidence:
            evidence.add_api_response(
                "email_submission",
                "/telegram/webhook",
                response.status_code,
                response.text,
                "Step 1.2: Email"
            )

        return response.status_code == 200

    def get_otp_search_query(self, email: str, since_timestamp: float) -> str:
        """Get Gmail search query for OTP email."""
        return self.parser.build_otp_search_query(email, since_timestamp)

    def extract_otp_from_email(self, email_body: str) -> Optional[str]:
        """Extract OTP code from email body."""
        return self.parser.extract_otp_code(email_body)

    async def execute_step5_submit_otp(
        self,
        otp_code: str,
        telegram_id: int,
        evidence: Optional[EvidenceCollector] = None
    ) -> bool:
        """Execute step 5: Submit OTP code."""
        response = await self.simulator.send_message(otp_code, telegram_id)

        if evidence:
            evidence.add_api_response(
                "otp_submission",
                "/telegram/webhook",
                response.status_code,
                response.text,
                "Step 1.5: OTP"
            )

        return response.status_code == 200

    def get_verification_query(self, telegram_id: int) -> str:
        """Get SQL query for registration verification."""
        return self.db_helper.sql_verify_registration_complete(telegram_id)

    def verify_registration(self, db_result: Any) -> Phase1Result:
        """Verify registration from DB result."""
        verification = self.db_helper.verify_registration_from_result(db_result)

        if verification.success:
            return Phase1Result(success=True)
        else:
            return Phase1Result(success=False, error=verification.message)
