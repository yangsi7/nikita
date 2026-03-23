#!/usr/bin/env python3
"""
Manual E2E Journey Test Script

Tests the complete user journey and documents all assets created at each stage:
1. Registration (OTP flow)
2. Onboarding (7 steps)
3. Conversation
4. Post-Processing
5. Neo4j Memory

Usage:
    TELEGRAM_WEBHOOK_SECRET="..." .venv/bin/python tests/e2e/manual_journey_test.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.helpers.telegram_helper import TelegramWebhookSimulator, generate_test_telegram_id

# Configuration
BACKEND_URL = os.getenv(
    "NIKITA_BACKEND_URL",
    "https://nikita-api-1040094048579.us-central1.run.app"
)
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

# Supabase config (for direct DB queries)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xnbtlxawcqzohitgkfol.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Service role key for admin access

# Test user data
TEST_TELEGRAM_ID = generate_test_telegram_id()
TEST_EMAIL = f"nikita.e2e.{TEST_TELEGRAM_ID}@test.example.com"


class JourneyReport:
    """Collects and formats the journey report."""

    def __init__(self):
        self.sections = []
        self.start_time = datetime.utcnow()

    def add_section(self, title: str, content: dict):
        self.sections.append({
            "title": title,
            "timestamp": datetime.utcnow().isoformat(),
            "content": content
        })

    def print_section(self, title: str, data: Any):
        """Print a section immediately for real-time visibility."""
        print(f"\n{'='*60}")
        print(f"📋 {title}")
        print(f"{'='*60}")
        if isinstance(data, dict):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(data)

    def generate_report(self) -> str:
        """Generate final markdown report."""
        report = [
            f"# E2E Journey Test Report",
            f"",
            f"**Generated**: {datetime.utcnow().isoformat()}Z",
            f"**Test User**: Telegram ID {TEST_TELEGRAM_ID}",
            f"**Backend**: {BACKEND_URL}",
            f"",
        ]

        for section in self.sections:
            report.append(f"## {section['title']}")
            report.append(f"*Timestamp: {section['timestamp']}*")
            report.append("")
            report.append("```json")
            report.append(json.dumps(section['content'], indent=2, default=str))
            report.append("```")
            report.append("")

        return "\n".join(report)


async def query_supabase(query: str, client: httpx.AsyncClient) -> dict:
    """Execute a raw SQL query via Supabase REST API."""
    # Note: This requires the service role key for raw SQL
    # For E2E tests, we'll use the backend's admin endpoints instead
    return {"error": "Use backend admin endpoints for queries"}


async def call_backend(
    path: str,
    method: str = "GET",
    json_data: dict = None,
    client: httpx.AsyncClient = None
) -> dict:
    """Call backend API endpoint."""
    url = f"{BACKEND_URL}{path}"
    headers = {
        "Authorization": f"Bearer {WEBHOOK_SECRET}",
        "Content-Type": "application/json",
    }

    try:
        if method == "GET":
            response = await client.get(url, headers=headers, timeout=30.0)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=json_data, timeout=60.0)
        else:
            return {"error": f"Unsupported method: {method}"}

        return {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
        }
    except Exception as e:
        return {"error": str(e)}


async def main():
    report = JourneyReport()
    simulator = TelegramWebhookSimulator(secret_token=WEBHOOK_SECRET)

    print(f"\n🚀 Starting E2E Journey Test")
    print(f"   Telegram ID: {TEST_TELEGRAM_ID}")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   Webhook Secret: {'✅ Set' if WEBHOOK_SECRET else '❌ Missing'}")

    if not WEBHOOK_SECRET:
        print("\n❌ ERROR: TELEGRAM_WEBHOOK_SECRET not set")
        sys.exit(1)

    async with httpx.AsyncClient() as client:
        # ============================================================
        # PHASE 1: REGISTRATION
        # ============================================================
        print("\n" + "="*60)
        print("📝 PHASE 1: REGISTRATION")
        print("="*60)

        # Step 1.1: Send /start command
        print("\n[1.1] Sending /start command...")
        response = await simulator.send_command("/start", TEST_TELEGRAM_ID)
        step_1_1 = {
            "action": "Send /start command",
            "telegram_id": TEST_TELEGRAM_ID,
            "response_status": response.status_code,
            "response_body": response.text[:500] if response.text else None,
        }
        report.add_section("1.1 - /start Command", step_1_1)
        report.print_section("Step 1.1: /start Command", step_1_1)

        await asyncio.sleep(2)  # Wait for processing

        # Step 1.2: Check pending_registrations
        print("\n[1.2] Checking pending_registrations table...")
        # Query via admin debug endpoint (if available) or note for manual check
        step_1_2 = {
            "check": "pending_registrations table",
            "expected": "Row with telegram_id={} and otp_state='pending'".format(TEST_TELEGRAM_ID),
            "note": "Query via Supabase MCP: SELECT * FROM pending_registrations WHERE telegram_id = {}".format(TEST_TELEGRAM_ID),
        }
        report.add_section("1.2 - Check Registration State", step_1_2)
        report.print_section("Step 1.2: Registration State", step_1_2)

        # Step 1.3: Send email (simulating user entering email for OTP)
        print("\n[1.3] Sending email for OTP...")
        response = await simulator.send_message(TEST_EMAIL, TEST_TELEGRAM_ID)
        step_1_3 = {
            "action": "Send email for OTP",
            "email": TEST_EMAIL,
            "response_status": response.status_code,
            "response_body": response.text[:500] if response.text else None,
        }
        report.add_section("1.3 - Email Input", step_1_3)
        report.print_section("Step 1.3: Email Input", step_1_3)

        await asyncio.sleep(2)

        # Step 1.4: Check OTP state
        print("\n[1.4] Checking OTP state...")
        step_1_4 = {
            "check": "pending_registrations.otp_state",
            "expected": "'code_sent' or user entry created",
            "note": "OTP sent to {} via Supabase Auth".format(TEST_EMAIL),
        }
        report.add_section("1.4 - OTP State Check", step_1_4)
        report.print_section("Step 1.4: OTP State", step_1_4)

        # Step 1.5: Send OTP code (we'll simulate with a known test code)
        # Note: In production, this requires the actual OTP from email
        print("\n[1.5] Sending OTP code (simulated)...")
        # For E2E testing, we might need to use a test bypass or mock
        # Let's send a dummy OTP to see the flow
        response = await simulator.send_message("123456", TEST_TELEGRAM_ID)
        step_1_5 = {
            "action": "Send OTP code",
            "otp": "123456 (test)",
            "response_status": response.status_code,
            "response_body": response.text[:500] if response.text else None,
            "note": "Real OTP verification requires email access or test bypass",
        }
        report.add_section("1.5 - OTP Verification", step_1_5)
        report.print_section("Step 1.5: OTP Verification", step_1_5)

        await asyncio.sleep(2)

        # ============================================================
        # PHASE 2: CHECK DATABASE STATE
        # ============================================================
        print("\n" + "="*60)
        print("🗄️ PHASE 2: DATABASE STATE CHECK")
        print("="*60)

        # Check if user was created
        print("\n[2.1] Database queries to verify state...")
        step_2_1 = {
            "queries": [
                f"SELECT * FROM pending_registrations WHERE telegram_id = {TEST_TELEGRAM_ID}",
                f"SELECT * FROM users WHERE telegram_id = {TEST_TELEGRAM_ID}",
                f"SELECT * FROM onboarding_states WHERE telegram_id = {TEST_TELEGRAM_ID}",
            ],
            "note": "Run these queries via Supabase MCP to verify state",
        }
        report.add_section("2.1 - Database Verification Queries", step_2_1)
        report.print_section("Step 2.1: Database Queries", step_2_1)

        # ============================================================
        # PHASE 3: CONVERSATION TEST (if user exists)
        # ============================================================
        print("\n" + "="*60)
        print("💬 PHASE 3: CONVERSATION TEST")
        print("="*60)

        # Try sending a conversation message
        print("\n[3.1] Sending conversation message...")
        response = await simulator.send_message("Hi Nikita! How are you doing today?", TEST_TELEGRAM_ID)
        step_3_1 = {
            "action": "Send conversation message",
            "message": "Hi Nikita! How are you doing today?",
            "response_status": response.status_code,
            "response_body": response.text[:1000] if response.text else None,
        }
        report.add_section("3.1 - Conversation Message", step_3_1)
        report.print_section("Step 3.1: Conversation Message", step_3_1)

        await asyncio.sleep(3)

        # ============================================================
        # PHASE 4: TRIGGER POST-PROCESSING
        # ============================================================
        print("\n" + "="*60)
        print("⚙️ PHASE 4: POST-PROCESSING")
        print("="*60)

        # Call the process-conversations endpoint
        print("\n[4.1] Triggering post-processing via /tasks/process-conversations...")
        result = await call_backend("/tasks/process-conversations", method="POST", client=client)
        step_4_1 = {
            "action": "Trigger post-processing",
            "endpoint": "/tasks/process-conversations",
            "result": result,
        }
        report.add_section("4.1 - Post-Processing Trigger", step_4_1)
        report.print_section("Step 4.1: Post-Processing", step_4_1)

        await asyncio.sleep(5)  # Wait for processing

        # ============================================================
        # PHASE 5: NEO4J MEMORY VERIFICATION
        # ============================================================
        print("\n" + "="*60)
        print("🧠 PHASE 5: NEO4J MEMORY VERIFICATION")
        print("="*60)

        # Try to get Neo4j debug info
        # First we need the user_id (UUID), not telegram_id
        print("\n[5.1] Neo4j memory check...")
        step_5_1 = {
            "action": "Check Neo4j memory",
            "note": "Need user UUID to query /admin/debug/neo4j/{user_id}",
            "query": f"SELECT id FROM users WHERE telegram_id = {TEST_TELEGRAM_ID}",
        }
        report.add_section("5.1 - Neo4j Memory Check", step_5_1)
        report.print_section("Step 5.1: Neo4j Memory", step_5_1)

        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)

        summary = {
            "test_telegram_id": TEST_TELEGRAM_ID,
            "test_email": TEST_EMAIL,
            "phases_executed": [
                "1. Registration (OTP flow)",
                "2. Database state check",
                "3. Conversation test",
                "4. Post-processing trigger",
                "5. Neo4j memory check",
            ],
            "verification_queries": [
                f"SELECT * FROM pending_registrations WHERE telegram_id = {TEST_TELEGRAM_ID}",
                f"SELECT * FROM users WHERE telegram_id = {TEST_TELEGRAM_ID}",
                f"SELECT * FROM user_metrics WHERE user_id = (SELECT id FROM users WHERE telegram_id = {TEST_TELEGRAM_ID})",
                f"SELECT * FROM conversations WHERE user_id = (SELECT id FROM users WHERE telegram_id = {TEST_TELEGRAM_ID})",
                f"SELECT * FROM onboarding_states WHERE telegram_id = {TEST_TELEGRAM_ID}",
            ],
            "cleanup_query": f"DELETE FROM pending_registrations WHERE telegram_id = {TEST_TELEGRAM_ID}",
        }
        report.add_section("Summary", summary)
        report.print_section("Test Summary", summary)

        # Save report
        report_path = f"docs-to-process/{datetime.utcnow().strftime('%Y%m%d')}-e2e-journey-report.md"
        print(f"\n📄 Saving report to: {report_path}")
        with open(report_path, "w") as f:
            f.write(report.generate_report())

        print("\n✅ E2E Journey Test Complete!")
        print(f"   Report saved to: {report_path}")
        print(f"   Use Supabase MCP to verify database state")

        return TEST_TELEGRAM_ID


if __name__ == "__main__":
    telegram_id = asyncio.run(main())
    print(f"\nTest Telegram ID for cleanup: {telegram_id}")
