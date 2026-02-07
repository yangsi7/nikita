"""
OTP Registration E2E Tests with Gmail MCP

Tests the complete OTP registration flow:
1. /start command via webhook
2. Email submission via webhook
3. OTP code retrieval via Gmail MCP
4. OTP submission via webhook
5. User verification via Supabase MCP
6. Cleanup

For Claude Code execution:
- Gmail MCP tools: mcp__gmail__search_emails, mcp__gmail__read_email
- Supabase MCP: mcp__supabase__execute_sql
- Webhook calls: TelegramWebhookSimulator (httpx)

Test Account: simon.yang.ch@gmail.com
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any, Dict

import pytest

from .helpers.telegram_helper import TelegramWebhookSimulator, generate_test_telegram_id
from .helpers.supabase_helper import SupabaseHelper, VerificationResult
from .helpers.otp_email_parser import OTPEmailParser, OTPEmail

# Mark all tests as integration tests (require Gmail MCP + external services)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("RUN_E2E_TESTS"),
        reason="E2E tests require live services (set RUN_E2E_TESTS=1 to run)"
    ),
]


# ==================== Test Configuration ====================

TEST_EMAIL_BASE = "simon.yang.ch@gmail.com"
BACKEND_URL = os.getenv(
    "NIKITA_BACKEND_URL",
    "https://nikita-api-1040094048579.us-central1.run.app"
)

# Timing configuration
OTP_POLL_TIMEOUT = 90  # seconds
OTP_POLL_INTERVAL = 3.0  # seconds
WEBHOOK_TIMEOUT = 30.0  # seconds


# ==================== Test Context Dataclass ====================

@dataclass
class OTPTestContext:
    """Context for OTP flow E2E test."""
    telegram_id: int
    test_email: str
    timestamp_before_email: float = field(default_factory=time.time)

    # Collected during test
    otp_code: Optional[str] = None
    otp_email_id: Optional[str] = None
    user_id: Optional[str] = None

    # Webhook responses
    start_response: Optional[Dict[str, Any]] = None
    email_response: Optional[Dict[str, Any]] = None
    otp_response: Optional[Dict[str, Any]] = None

    # Verification results
    verification_result: Optional[VerificationResult] = None

    @classmethod
    def create(cls, base_email: str = TEST_EMAIL_BASE) -> "OTPTestContext":
        """Create a new test context with unique IDs."""
        telegram_id = generate_test_telegram_id()
        test_email = SupabaseHelper.generate_test_email(base_email, telegram_id)
        return cls(
            telegram_id=telegram_id,
            test_email=test_email,
        )


# ==================== E2E Test Steps ====================

class OTPFlowE2ETest:
    """
    OTP Registration E2E Test orchestrator.

    This class provides structured steps for the OTP flow test.
    When run from Claude Code, the MCP calls are made externally.

    Usage (Claude Code):
        1. Create context: ctx = OTPTestContext.create()
        2. Step 1: Send /start → simulator.send_command("/start", ctx.telegram_id)
        3. Step 2: Send email → simulator.send_message(ctx.test_email, ctx.telegram_id)
        4. Step 3: Wait for OTP email via Gmail MCP
           - query = OTPEmailParser.build_otp_search_query(ctx.test_email, ctx.timestamp_before_email)
           - results = mcp__gmail__search_emails(query=query, maxResults=5)
           - for msg in results: content = mcp__gmail__read_email(messageId=msg['id'])
           - ctx.otp_code = OTPEmailParser.extract_otp_code(content)
        5. Step 4: Submit OTP → simulator.send_message(ctx.otp_code, ctx.telegram_id)
        6. Step 5: Verify in Supabase via MCP
           - sql = SupabaseHelper.sql_verify_registration_complete(ctx.telegram_id)
           - result = mcp__supabase__execute_sql(query=sql)
           - ctx.verification_result = SupabaseHelper.verify_registration_from_result(result)
        7. Cleanup: sql = SupabaseHelper.sql_full_cleanup_by_telegram_id(ctx.telegram_id)
    """

    def __init__(self, secret_token: Optional[str] = None):
        """Initialize E2E test orchestrator."""
        self.simulator = TelegramWebhookSimulator(secret_token=secret_token)
        self.helper = SupabaseHelper()
        self.parser = OTPEmailParser

    async def step1_send_start(self, ctx: OTPTestContext) -> bool:
        """Step 1: Send /start command to initiate registration."""
        print(f"\n[Step 1] Sending /start to telegram_id={ctx.telegram_id}")

        response = await self.simulator.send_command(
            "/start",
            telegram_id=ctx.telegram_id,
            timeout=WEBHOOK_TIMEOUT,
        )

        ctx.start_response = {
            "status_code": response.status_code,
            "body": response.text[:500] if response.text else None,
        }

        print(f"[Step 1] Response: {response.status_code}")
        return response.status_code == 200

    async def step2_send_email(self, ctx: OTPTestContext) -> bool:
        """Step 2: Send email to trigger OTP."""
        print(f"\n[Step 2] Sending email: {ctx.test_email}")

        # Record timestamp before sending (for email search)
        ctx.timestamp_before_email = time.time()

        # Small delay to ensure timestamp is before email
        await asyncio.sleep(0.5)

        response = await self.simulator.send_message(
            ctx.test_email,
            telegram_id=ctx.telegram_id,
            timeout=WEBHOOK_TIMEOUT,
        )

        ctx.email_response = {
            "status_code": response.status_code,
            "body": response.text[:500] if response.text else None,
        }

        print(f"[Step 2] Response: {response.status_code}")
        return response.status_code == 200

    def step3_build_otp_search_query(self, ctx: OTPTestContext) -> str:
        """Step 3a: Build Gmail search query for OTP email.

        Returns query string for mcp__gmail__search_emails.
        """
        query = self.parser.build_otp_search_query(
            recipient_email=ctx.test_email,
            after_timestamp=ctx.timestamp_before_email,
        )
        print(f"\n[Step 3] Gmail search query: {query}")
        return query

    def step3_parse_otp_from_email(self, ctx: OTPTestContext, email_body: str) -> Optional[str]:
        """Step 3b: Extract OTP code from email content.

        Args:
            email_body: Raw email body from mcp__gmail__read_email

        Returns:
            6-digit OTP code or None
        """
        code = self.parser.extract_otp_code(email_body)
        if code:
            ctx.otp_code = code
            print(f"[Step 3] OTP code extracted: {code}")
        else:
            print(f"[Step 3] No OTP code found in email")
        return code

    async def step4_submit_otp(self, ctx: OTPTestContext) -> bool:
        """Step 4: Submit OTP code to complete registration."""
        if not ctx.otp_code:
            print("[Step 4] ERROR: No OTP code available")
            return False

        print(f"\n[Step 4] Submitting OTP: {ctx.otp_code}")

        response = await self.simulator.send_message(
            ctx.otp_code,
            telegram_id=ctx.telegram_id,
            timeout=WEBHOOK_TIMEOUT,
        )

        ctx.otp_response = {
            "status_code": response.status_code,
            "body": response.text[:500] if response.text else None,
        }

        print(f"[Step 4] Response: {response.status_code}")
        return response.status_code == 200

    def step5_build_verification_query(self, ctx: OTPTestContext) -> str:
        """Step 5a: Build Supabase verification query.

        Returns SQL for mcp__supabase__execute_sql.
        """
        sql = self.helper.sql_verify_registration_complete(ctx.telegram_id)
        print(f"\n[Step 5] Verification SQL ready for telegram_id={ctx.telegram_id}")
        return sql

    def step5_verify_result(self, ctx: OTPTestContext, result: Any) -> VerificationResult:
        """Step 5b: Verify registration completion from SQL result.

        Args:
            result: Response from mcp__supabase__execute_sql

        Returns:
            VerificationResult with success status
        """
        verification = self.helper.verify_registration_from_result(result)
        ctx.verification_result = verification

        if verification.success:
            print(f"[Step 5] ✅ {verification.message}")
        else:
            print(f"[Step 5] ❌ {verification.message}")

        return verification

    def build_cleanup_query(self, ctx: OTPTestContext) -> str:
        """Build cleanup SQL for test data.

        Returns SQL for mcp__supabase__execute_sql.
        """
        sql = self.helper.sql_full_cleanup_by_telegram_id(ctx.telegram_id)
        print(f"\n[Cleanup] SQL ready for telegram_id={ctx.telegram_id}")
        return sql


# ==================== Pytest Test Cases ====================

@pytest.fixture
def otp_test():
    """Create OTP flow test instance."""
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    return OTPFlowE2ETest(secret_token=secret)


@pytest.fixture
def test_context():
    """Create fresh test context."""
    return OTPTestContext.create()


class TestOTPFlowSteps:
    """Test individual steps of OTP flow (for development/debugging)."""

    @pytest.mark.asyncio
    async def test_step1_start_command(self, otp_test, test_context):
        """Test /start command sends successfully."""
        result = await otp_test.step1_send_start(test_context)
        assert result, f"Failed: {test_context.start_response}"

    @pytest.mark.asyncio
    async def test_step2_email_submission(self, otp_test, test_context):
        """Test email submission sends successfully."""
        # Must do step 1 first
        await otp_test.step1_send_start(test_context)

        result = await otp_test.step2_send_email(test_context)
        assert result, f"Failed: {test_context.email_response}"

    def test_step3_otp_parsing(self, otp_test, test_context):
        """Test OTP code extraction from email body."""
        # Test with sample email body formats
        test_bodies = [
            "Your verification code is 123456",
            "Code: 654321",
            "Enter 987654 to verify",
            "<html>Your code is 111222</html>",
        ]

        expected_codes = ["123456", "654321", "987654", "111222"]

        for body, expected in zip(test_bodies, expected_codes):
            code = otp_test.step3_parse_otp_from_email(test_context, body)
            assert code == expected, f"Expected {expected}, got {code}"

    def test_step5_verification_parsing(self, otp_test, test_context):
        """Test verification result parsing."""
        # Successful registration
        success_result = [{"user_count": 1, "pending_count": 0, "metrics_count": 1}]
        verification = otp_test.step5_verify_result(test_context, success_result)
        assert verification.success

        # Failed registration (pending not deleted)
        fail_result = [{"user_count": 1, "pending_count": 1, "metrics_count": 1}]
        test_context2 = OTPTestContext.create()
        verification2 = otp_test.step5_verify_result(test_context2, fail_result)
        assert not verification2.success
        assert "pending" in verification2.message.lower()


class TestOTPFlowIntegration:
    """
    Full OTP flow integration tests.

    These tests require:
    - TELEGRAM_WEBHOOK_SECRET environment variable
    - Backend running and accessible
    - For Gmail MCP steps: Manual execution via Claude Code
    """

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("TELEGRAM_WEBHOOK_SECRET"),
        reason="Requires TELEGRAM_WEBHOOK_SECRET"
    )
    async def test_otp_flow_steps_1_and_2(self, otp_test, test_context):
        """Test steps 1-2: /start and email submission."""
        # Step 1: /start
        result1 = await otp_test.step1_send_start(test_context)
        assert result1, f"Step 1 failed: {test_context.start_response}"

        # Step 2: Email
        result2 = await otp_test.step2_send_email(test_context)
        assert result2, f"Step 2 failed: {test_context.email_response}"

        # At this point, OTP email should be sent
        # Query for Gmail MCP:
        query = otp_test.step3_build_otp_search_query(test_context)
        print(f"\n📧 Gmail MCP query: {query}")
        print(f"🔑 Telegram ID: {test_context.telegram_id}")
        print(f"📬 Test email: {test_context.test_email}")

        # Cleanup query for later
        cleanup_sql = otp_test.build_cleanup_query(test_context)
        print(f"\n🧹 Cleanup SQL ready")


# ==================== Manual Test Script ====================

async def run_manual_otp_test():
    """
    Manual OTP flow test for Claude Code execution.

    Run this function and follow the printed instructions
    to complete the test with MCP tool calls.
    """
    print("=" * 60)
    print("OTP Registration E2E Test - Manual Execution")
    print("=" * 60)

    # Create context
    ctx = OTPTestContext.create()
    test = OTPFlowE2ETest()

    print(f"\n📋 Test Context Created:")
    print(f"   Telegram ID: {ctx.telegram_id}")
    print(f"   Test Email: {ctx.test_email}")

    # Step 1: /start
    print("\n" + "=" * 40)
    result1 = await test.step1_send_start(ctx)
    if not result1:
        print("❌ Step 1 failed. Aborting.")
        return ctx

    # Wait for webhook to process
    await asyncio.sleep(2)

    # Step 2: Email
    print("\n" + "=" * 40)
    result2 = await test.step2_send_email(ctx)
    if not result2:
        print("❌ Step 2 failed. Aborting.")
        return ctx

    # Step 3: Instructions for Gmail MCP
    print("\n" + "=" * 40)
    print("[Step 3] OTP Email Retrieval")
    print("-" * 40)

    query = test.step3_build_otp_search_query(ctx)
    print(f"\n🔍 Execute this Gmail MCP search:")
    print(f"   mcp__gmail__search_emails(query=\"{query}\", maxResults=5)")
    print(f"\n📧 Then read each email:")
    print(f"   mcp__gmail__read_email(messageId=\"<id from search>\")")
    print(f"\n🔑 Extract OTP code from email body")

    # Placeholder for manual OTP entry
    print("\n⏳ Waiting for OTP code...")
    print("   (In Claude Code, use Gmail MCP to retrieve the code)")

    # For automated testing, we'd poll here
    # For manual testing, the OTP is entered via next step

    return ctx


def print_test_summary(ctx: OTPTestContext):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Telegram ID: {ctx.telegram_id}")
    print(f"Test Email: {ctx.test_email}")
    print(f"OTP Code: {ctx.otp_code or 'Not retrieved'}")

    if ctx.verification_result:
        status = "✅ PASS" if ctx.verification_result.success else "❌ FAIL"
        print(f"Verification: {status}")
        print(f"Message: {ctx.verification_result.message}")
    else:
        print("Verification: Not performed")


if __name__ == "__main__":
    # Run manual test
    ctx = asyncio.run(run_manual_otp_test())
    print_test_summary(ctx)
