"""
Full User Journey E2E Test

Complete test covering all 4 phases:
1. OTP Registration (Telegram + Gmail MCP)
2. Real Conversation (Telegram webhook + Claude API)
3. Portal Access (Playwright + Gmail MCP)
4. Game State Verification (Supabase MCP)

For Claude Code execution:
- MCP Tools: Gmail, Supabase, Playwright
- Telegram: TelegramWebhookSimulator (httpx)
- Evidence: Captured throughout

Test Account: simon.yang.ch@gmail.com
"""

import os
import time
from typing import Optional

import pytest

from .orchestrator import FullJourneyOrchestrator, JourneyContext, JourneyState
from .evidence_collector import EvidenceCollector
from .phases import (
    Phase1Registration,
    Phase2Conversation,
    Phase3Portal,
    Phase4GameState,
)
from ..helpers.supabase_helper import SupabaseHelper


# Configuration
TEST_EMAIL_BASE = "simon.yang.ch@gmail.com"


class TestFullJourneyE2E:
    """Full journey E2E test suite."""

    @pytest.fixture
    def orchestrator(self):
        """Create journey orchestrator."""
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        return FullJourneyOrchestrator(secret_token=secret)

    @pytest.fixture
    def context(self):
        """Create fresh journey context."""
        return JourneyContext()

    @pytest.fixture
    def evidence(self, context):
        """Create evidence collector."""
        return EvidenceCollector(test_id=context.test_id)

    # ==================== Orchestration Tests ====================

    def test_context_creation(self, orchestrator):
        """Test context is created with valid test IDs."""
        ctx = orchestrator.create_context()

        assert ctx.telegram_id >= 900000000
        assert ctx.telegram_id <= 999999999
        assert "@gmail.com" in ctx.test_email
        assert ctx.state == JourneyState.INITIAL

    def test_phase1_instructions_generated(self, orchestrator, context):
        """Test Phase 1 instructions are complete."""
        instructions = orchestrator.get_phase1_instructions(context)

        assert len(instructions) >= 5
        assert any("start" in i["name"].lower() for i in instructions)
        assert any("email" in i["name"].lower() for i in instructions)
        assert any("otp" in i["name"].lower() for i in instructions)

    def test_phase2_instructions_generated(self, orchestrator, context):
        """Test Phase 2 instructions include real messages."""
        instructions = orchestrator.get_phase2_instructions(context)

        assert len(instructions) >= 2
        assert any("message" in i["name"].lower() for i in instructions)

    def test_phase3_instructions_generated(self, orchestrator, context):
        """Test Phase 3 instructions include portal steps."""
        instructions = orchestrator.get_phase3_instructions(context)

        assert len(instructions) >= 5
        assert any("login" in i["name"].lower() or "navigate" in i["name"].lower()
                   for i in instructions)
        assert any("dashboard" in i["name"].lower() for i in instructions)

    def test_phase4_instructions_generated(self, orchestrator, context):
        """Test Phase 4 instructions include verification."""
        instructions = orchestrator.get_phase4_instructions(context)

        assert len(instructions) >= 2
        assert any("metrics" in i["name"].lower() for i in instructions)

    def test_cleanup_instructions_generated(self, orchestrator, context):
        """Test cleanup instructions generated."""
        instructions = orchestrator.get_cleanup_instructions(context)

        assert len(instructions) >= 1
        assert any("cleanup" in i["step"].lower() for i in instructions)

    def test_all_instructions_organized(self, orchestrator, context):
        """Test all instructions are organized by phase."""
        all_instr = orchestrator.get_all_instructions(context, include_phase4=True)

        assert "phase1_registration" in all_instr
        assert "phase2_conversation" in all_instr
        assert "phase3_portal" in all_instr
        assert "phase4_game_state" in all_instr
        assert "cleanup" in all_instr

    # ==================== Evidence Collection Tests ====================

    def test_evidence_phase_tracking(self, evidence):
        """Test evidence tracks phases correctly."""
        evidence.start_phase("registration")
        evidence.log("Test log entry")
        evidence.add_api_response("test", "/test", 200, "OK", "step1")
        evidence.end_phase(success=True)

        assert "registration" in evidence.phases
        assert evidence.phases["registration"].success
        assert len(evidence.phases["registration"].items) == 1

    def test_evidence_verification_recording(self, evidence):
        """Test evidence records verifications."""
        evidence.start_phase("test")
        evidence.add_verification("score_check", 50, 50, True, "verify_score")
        evidence.add_verification("chapter_check", 2, 3, False, "verify_chapter")
        evidence.end_phase()

        items = evidence.phases["test"].items
        verifications = [i for i in items if i.type == "verification"]

        assert len(verifications) == 2
        assert verifications[0].data["passed"]
        assert not verifications[1].data["passed"]

    def test_evidence_report_generation(self, evidence):
        """Test report generation."""
        evidence.start_phase("phase1")
        evidence.add_verification("test1", 1, 1, True)
        evidence.end_phase(success=True)

        evidence.start_phase("phase2")
        evidence.add_verification("test2", 2, 3, False)
        evidence.end_phase(success=False, error="Mismatch")

        report = evidence.generate_report()

        assert report["test_id"] == evidence.test_id
        assert not report["overall_success"]  # Phase 2 failed
        assert report["total_verifications"] == 2
        assert report["passed_verifications"] == 1

    # ==================== Phase Component Tests ====================

    def test_phase1_otp_extraction(self):
        """Test Phase 1 OTP extraction."""
        phase = Phase1Registration()

        # Test OTP extraction from various email formats
        test_cases = [
            ("Your verification code is 123456", "123456"),
            ("Code: 654321 for login", "654321"),
            ("Enter 999888 to verify", "999888"),
        ]

        for body, expected in test_cases:
            code = phase.extract_otp_from_email(body)
            assert code == expected, f"Failed for body: {body}"

    def test_phase2_sample_messages(self):
        """Test Phase 2 has sample messages."""
        phase = Phase2Conversation()

        assert len(phase.SAMPLE_MESSAGES) >= 3
        assert all(isinstance(m, str) for m in phase.SAMPLE_MESSAGES)

    def test_phase3_magic_link_extraction(self):
        """Test Phase 3 magic link extraction."""
        phase = Phase3Portal()

        test_body = """
        <a href="https://vlvlwmolfdpzdfmtipji.supabase.co/auth/v1/verify?token=abc123&amp;type=magiclink">
        Click here
        </a>
        """

        url = phase.extract_magic_link(test_body)
        assert url is not None
        assert "supabase.co/auth" in url

    def test_phase4_chapter_calculation(self):
        """Test Phase 4 chapter calculation."""
        phase = Phase4GameState()

        test_cases = [
            (10, 1),
            (30, 2),
            (50, 3),
            (70, 4),
            (90, 5),
        ]

        for score, expected_chapter in test_cases:
            chapter = phase.expected_chapter_for_score(score)
            assert chapter == expected_chapter, f"Score {score} should be chapter {expected_chapter}"


class TestJourneyManualExecution:
    """
    Tests for manual journey execution via Claude Code.

    These tests print instructions that can be executed step-by-step
    using MCP tools in Claude Code.
    """

    @pytest.fixture
    def orchestrator(self):
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        return FullJourneyOrchestrator(secret_token=secret)

    def test_print_all_instructions(self, orchestrator, capsys):
        """Print all instructions for manual execution."""
        ctx = orchestrator.create_context()
        orchestrator.print_instructions(ctx, include_phase4=True)

        captured = capsys.readouterr()
        assert "FULL JOURNEY E2E TEST INSTRUCTIONS" in captured.out
        assert "phase1_registration" in captured.out.lower()
        assert "phase2_conversation" in captured.out.lower()
        assert "phase3_portal" in captured.out.lower()
        assert "phase4_game_state" in captured.out.lower()

    def test_cleanup_sql_generated(self, orchestrator):
        """Test cleanup SQL is properly generated."""
        ctx = orchestrator.create_context()
        sql = orchestrator.get_cleanup_sql(ctx)

        assert "DELETE" in sql
        assert str(ctx.telegram_id) in sql
        assert "pending_registrations" in sql
        assert "users" in sql


# ==================== Integration Test Markers ====================

@pytest.mark.e2e
class TestJourneyIntegration:
    """
    Integration tests that require live services.

    Run with: pytest -m integration
    """

    @pytest.fixture
    def orchestrator(self):
        return FullJourneyOrchestrator(
            secret_token=os.getenv("TELEGRAM_WEBHOOK_SECRET")
        )

    @pytest.mark.asyncio
    async def test_phase1_webhook_connectivity(self, orchestrator):
        """Test webhook endpoint is reachable."""
        ctx = orchestrator.create_context()
        phase = Phase1Registration(
            secret_token=os.getenv("TELEGRAM_WEBHOOK_SECRET")
        )

        # Just test /start works
        result = await phase.execute_step1_start(ctx.telegram_id)
        assert result, "Webhook should be reachable"

        # Cleanup
        db = SupabaseHelper()
        cleanup_sql = db.sql_delete_pending(ctx.telegram_id)
        # Note: Actual cleanup needs MCP execution


# ==================== Manual Journey Runner ====================

def run_manual_journey():
    """
    Manual journey execution guide.

    Prints step-by-step instructions for executing the full journey
    using Claude Code's MCP tools.
    """
    orchestrator = FullJourneyOrchestrator()
    ctx = orchestrator.create_context()
    evidence = EvidenceCollector(test_id=ctx.test_id)

    print("\n" + "=" * 70)
    print("FULL USER JOURNEY E2E TEST - MANUAL EXECUTION GUIDE")
    print("=" * 70)
    print(f"\n📋 Test Context:")
    print(f"   Test ID: {ctx.test_id}")
    print(f"   Telegram ID: {ctx.telegram_id}")
    print(f"   Test Email: {ctx.test_email}")

    print("\n" + "-" * 70)
    print("PHASE 1: OTP REGISTRATION")
    print("-" * 70)
    for instr in orchestrator.get_phase1_instructions(ctx):
        print(f"\n[{instr['step']}] {instr['name']}")
        print(f"   Type: {instr['type']}")

    print("\n" + "-" * 70)
    print("PHASE 2: CONVERSATION (REAL CLAUDE)")
    print("-" * 70)
    for instr in orchestrator.get_phase2_instructions(ctx):
        print(f"\n[{instr['step']}] {instr['name']}")
        print(f"   Type: {instr['type']}")

    print("\n" + "-" * 70)
    print("PHASE 3: PORTAL ACCESS")
    print("-" * 70)
    for instr in orchestrator.get_phase3_instructions(ctx):
        print(f"\n[{instr['step']}] {instr['name']}")
        print(f"   Type: {instr['type']}")

    print("\n" + "-" * 70)
    print("PHASE 4: GAME STATE (Optional)")
    print("-" * 70)
    for instr in orchestrator.get_phase4_instructions(ctx):
        print(f"\n[{instr['step']}] {instr['name']}")
        print(f"   Type: {instr['type']}")

    print("\n" + "-" * 70)
    print("CLEANUP")
    print("-" * 70)
    cleanup_sql = orchestrator.get_cleanup_sql(ctx)
    print(f"\nExecute via mcp__supabase__execute_sql:")
    print(f"{cleanup_sql[:200]}...")

    print("\n" + "=" * 70)
    print("Ready for execution. Follow the steps above using MCP tools.")
    print("=" * 70)

    return ctx


if __name__ == "__main__":
    run_manual_journey()
