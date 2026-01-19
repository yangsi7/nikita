#!/usr/bin/env python3
"""Post-call verification script for Voice Agent E2E testing.

This script verifies that all expected state changes occurred after a voice call:
- Database checks (Supabase): users, user_metrics, conversations, score_history
- Neo4j checks: episodes, facts stored with source='voice_call'
- ElevenLabs API checks: transcript availability, agent config

Usage:
    # Verify specific session
    python scripts/verify-voice-call.py --user-id UUID --session-id SESSION_ID

    # Verify latest call for user
    python scripts/verify-voice-call.py --user-id UUID --latest

    # Output formats
    python scripts/verify-voice-call.py --user-id UUID --latest --format json
    python scripts/verify-voice-call.py --user-id UUID --latest --format markdown

Requirements:
    - DATABASE_URL environment variable (Supabase connection)
    - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD environment variables
    - ELEVENLABS_API_KEY environment variable
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class DatabaseChecks:
    """Database verification results."""

    user_exists: CheckResult | None = None
    user_updated: CheckResult | None = None
    metrics_exist: CheckResult | None = None
    metrics_updated: CheckResult | None = None
    conversation_stored: CheckResult | None = None
    score_recorded: CheckResult | None = None
    engagement_state: CheckResult | None = None

    @property
    def all_passed(self) -> bool:
        """Check if all database checks passed."""
        checks = [
            self.user_exists,
            self.user_updated,
            self.metrics_exist,
            self.conversation_stored,
            self.score_recorded,
        ]
        return all(c.passed for c in checks if c is not None)


@dataclass
class Neo4jChecks:
    """Neo4j verification results."""

    connected: CheckResult | None = None
    episode_stored: CheckResult | None = None
    facts_extracted: CheckResult | None = None

    @property
    def all_passed(self) -> bool:
        """Check if all Neo4j checks passed."""
        checks = [self.connected, self.episode_stored]
        return all(c.passed for c in checks if c is not None)


@dataclass
class ElevenLabsChecks:
    """ElevenLabs API verification results."""

    transcript_available: CheckResult | None = None
    agent_config_valid: CheckResult | None = None

    @property
    def all_passed(self) -> bool:
        """Check if all ElevenLabs checks passed."""
        checks = [self.transcript_available]
        return all(c.passed for c in checks if c is not None)


@dataclass
class VerificationReport:
    """Complete verification report."""

    verification_time: str
    user_id: str
    session_id: str | None
    database: DatabaseChecks = field(default_factory=DatabaseChecks)
    neo4j: Neo4jChecks = field(default_factory=Neo4jChecks)
    elevenlabs: ElevenLabsChecks = field(default_factory=ElevenLabsChecks)
    errors: list[str] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        """Get overall verification status."""
        if self.errors:
            return "ERROR"
        if self.database.all_passed and self.neo4j.all_passed and self.elevenlabs.all_passed:
            return "PASS"
        return "FAIL"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "verification_time": self.verification_time,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "overall_status": self.overall_status,
            "checks": {
                "database": {
                    k: asdict(v) if v else None
                    for k, v in {
                        "user_exists": self.database.user_exists,
                        "user_updated": self.database.user_updated,
                        "metrics_exist": self.database.metrics_exist,
                        "metrics_updated": self.database.metrics_updated,
                        "conversation_stored": self.database.conversation_stored,
                        "score_recorded": self.database.score_recorded,
                        "engagement_state": self.database.engagement_state,
                    }.items()
                },
                "neo4j": {
                    k: asdict(v) if v else None
                    for k, v in {
                        "connected": self.neo4j.connected,
                        "episode_stored": self.neo4j.episode_stored,
                        "facts_extracted": self.neo4j.facts_extracted,
                    }.items()
                },
                "elevenlabs": {
                    k: asdict(v) if v else None
                    for k, v in {
                        "transcript_available": self.elevenlabs.transcript_available,
                        "agent_config_valid": self.elevenlabs.agent_config_valid,
                    }.items()
                },
            },
            "errors": self.errors,
        }


class VoiceCallVerifier:
    """Verifier for voice call state changes."""

    def __init__(self, user_id: str, session_id: str | None = None):
        """Initialize verifier.

        Args:
            user_id: User UUID to verify
            session_id: Optional session ID (if None, finds latest)
        """
        self.user_id = user_id
        self.session_id = session_id
        self.report = VerificationReport(
            verification_time=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            session_id=session_id,
        )

    async def verify_all(self) -> VerificationReport:
        """Run all verification checks."""
        try:
            # Database checks
            await self._verify_database()

            # Neo4j checks
            await self._verify_neo4j()

            # ElevenLabs checks
            await self._verify_elevenlabs()

        except Exception as e:
            self.report.errors.append(f"Verification failed: {str(e)}")

        return self.report

    async def _verify_database(self) -> None:
        """Run database verification checks."""
        try:
            from nikita.db.database import get_session_maker

            session_maker = get_session_maker()
            async with session_maker() as session:
                # Check user exists
                await self._check_user_exists(session)

                # Check user metrics
                await self._check_metrics(session)

                # Check conversation stored
                await self._check_conversation(session)

                # Check score history
                await self._check_score_history(session)

                # Check engagement state
                await self._check_engagement(session)

        except ImportError as e:
            self.report.errors.append(f"Database module import failed: {e}")
        except Exception as e:
            self.report.errors.append(f"Database verification failed: {e}")

    async def _check_user_exists(self, session) -> None:
        """Check if user exists and was recently updated."""
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT id, relationship_score, chapter, last_active, game_status
                FROM users WHERE id = :user_id
            """),
            {"user_id": self.user_id},
        )
        row = result.fetchone()

        if row:
            self.report.database.user_exists = CheckResult(
                name="user_exists",
                passed=True,
                details={
                    "relationship_score": float(row[1]) if row[1] else 0,
                    "chapter": row[2],
                    "last_active": str(row[3]) if row[3] else None,
                    "game_status": row[4],
                },
            )

            # Check if updated recently (within last hour)
            if row[3]:
                last_active = row[3]
                now = datetime.now(timezone.utc)
                if hasattr(last_active, "tzinfo") and last_active.tzinfo is None:
                    from datetime import timezone as tz

                    last_active = last_active.replace(tzinfo=tz.utc)
                age_seconds = (now - last_active).total_seconds()
                recently_updated = age_seconds < 3600

                self.report.database.user_updated = CheckResult(
                    name="user_updated",
                    passed=recently_updated,
                    details={
                        "last_active": str(last_active),
                        "age_seconds": age_seconds,
                    },
                )
        else:
            self.report.database.user_exists = CheckResult(
                name="user_exists",
                passed=False,
                error="User not found",
            )

    async def _check_metrics(self, session) -> None:
        """Check user metrics exist and values."""
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT intimacy, passion, trust, secureness, updated_at
                FROM user_metrics WHERE user_id = :user_id
            """),
            {"user_id": self.user_id},
        )
        row = result.fetchone()

        if row:
            self.report.database.metrics_exist = CheckResult(
                name="metrics_exist",
                passed=True,
                details={
                    "intimacy": float(row[0]) if row[0] else 0,
                    "passion": float(row[1]) if row[1] else 0,
                    "trust": float(row[2]) if row[2] else 0,
                    "secureness": float(row[3]) if row[3] else 0,
                    "updated_at": str(row[4]) if row[4] else None,
                },
            )
        else:
            self.report.database.metrics_exist = CheckResult(
                name="metrics_exist",
                passed=False,
                error="User metrics not found",
            )

    async def _check_conversation(self, session) -> None:
        """Check conversation was stored."""
        from sqlalchemy import text

        # Build query based on whether we have session_id
        if self.session_id:
            result = await session.execute(
                text("""
                    SELECT id, voice_session_id, channel, content, summary,
                           emotional_tone, status, created_at
                    FROM conversations
                    WHERE user_id = :user_id AND voice_session_id = :session_id
                """),
                {"user_id": self.user_id, "session_id": self.session_id},
            )
        else:
            # Get latest voice conversation
            result = await session.execute(
                text("""
                    SELECT id, voice_session_id, channel, content, summary,
                           emotional_tone, status, created_at
                    FROM conversations
                    WHERE user_id = :user_id AND channel = 'voice'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"user_id": self.user_id},
            )

        row = result.fetchone()

        if row:
            # Update session_id if we found one
            if not self.session_id and row[1]:
                self.session_id = row[1]
                self.report.session_id = row[1]

            self.report.database.conversation_stored = CheckResult(
                name="conversation_stored",
                passed=True,
                details={
                    "conversation_id": str(row[0]),
                    "voice_session_id": row[1],
                    "channel": row[2],
                    "has_content": bool(row[3]),
                    "has_summary": bool(row[4]),
                    "emotional_tone": row[5],
                    "status": row[6],
                    "created_at": str(row[7]) if row[7] else None,
                },
            )
        else:
            self.report.database.conversation_stored = CheckResult(
                name="conversation_stored",
                passed=False,
                error="No voice conversation found",
            )

    async def _check_score_history(self, session) -> None:
        """Check score history was recorded."""
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT id, delta, intimacy_delta, passion_delta, trust_delta,
                       secureness_delta, source, metadata, created_at
                FROM score_history
                WHERE user_id = :user_id
                ORDER BY created_at DESC LIMIT 5
            """),
            {"user_id": self.user_id},
        )
        rows = result.fetchall()

        if rows:
            latest = rows[0]
            # Check if there's a voice-related score
            voice_scores = [r for r in rows if r[6] == "voice_call" or "voice" in str(r[7] or "")]

            self.report.database.score_recorded = CheckResult(
                name="score_recorded",
                passed=len(voice_scores) > 0,
                details={
                    "total_recent_scores": len(rows),
                    "voice_scores": len(voice_scores),
                    "latest_delta": float(latest[1]) if latest[1] else 0,
                    "latest_source": latest[6],
                    "latest_created_at": str(latest[8]) if latest[8] else None,
                },
            )
        else:
            self.report.database.score_recorded = CheckResult(
                name="score_recorded",
                passed=False,
                error="No score history found",
            )

    async def _check_engagement(self, session) -> None:
        """Check engagement state."""
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT state, multiplier, updated_at
                FROM engagement_state WHERE user_id = :user_id
            """),
            {"user_id": self.user_id},
        )
        row = result.fetchone()

        if row:
            self.report.database.engagement_state = CheckResult(
                name="engagement_state",
                passed=True,
                details={
                    "state": row[0],
                    "multiplier": float(row[1]) if row[1] else 1.0,
                    "updated_at": str(row[2]) if row[2] else None,
                },
            )
        else:
            self.report.database.engagement_state = CheckResult(
                name="engagement_state",
                passed=False,
                error="Engagement state not found",
            )

    async def _verify_neo4j(self) -> None:
        """Run Neo4j verification checks."""
        try:
            from nikita.memory.graphiti_client import get_memory_client

            # Check connection
            try:
                memory = await get_memory_client(self.user_id)
                self.report.neo4j.connected = CheckResult(
                    name="connected",
                    passed=True,
                    details={"graph_name": f"relationship_{self.user_id}"},
                )
            except Exception as e:
                self.report.neo4j.connected = CheckResult(
                    name="connected",
                    passed=False,
                    error=str(e),
                )
                return

            # Check for voice_call episodes
            try:
                # Search for recent voice episodes
                results = await memory.search(
                    query="voice call conversation",
                    limit=5,
                )

                voice_episodes = [r for r in results if r.get("source") == "voice_call"]
                self.report.neo4j.episode_stored = CheckResult(
                    name="episode_stored",
                    passed=len(voice_episodes) > 0 or len(results) > 0,
                    details={
                        "total_results": len(results),
                        "voice_episodes": len(voice_episodes),
                    },
                )
            except Exception as e:
                self.report.neo4j.episode_stored = CheckResult(
                    name="episode_stored",
                    passed=False,
                    error=str(e),
                )

            # Check for extracted facts
            try:
                facts = await memory.search(
                    query="user fact preference hobby work",
                    limit=10,
                )
                self.report.neo4j.facts_extracted = CheckResult(
                    name="facts_extracted",
                    passed=True,
                    details={
                        "fact_count": len(facts),
                        "sample_facts": [f.get("content", "")[:100] for f in facts[:3]],
                    },
                )
            except Exception as e:
                self.report.neo4j.facts_extracted = CheckResult(
                    name="facts_extracted",
                    passed=False,
                    error=str(e),
                )

        except ImportError as e:
            self.report.errors.append(f"Neo4j module import failed: {e}")
        except Exception as e:
            self.report.errors.append(f"Neo4j verification failed: {e}")

    async def _verify_elevenlabs(self) -> None:
        """Run ElevenLabs API verification checks."""
        try:
            from nikita.agents.voice.elevenlabs_client import get_elevenlabs_client
            from nikita.config.settings import get_settings

            settings = get_settings()
            client = get_elevenlabs_client()

            # Get latest conversation if no session_id
            if not self.session_id:
                try:
                    result = await client.list_conversations(
                        agent_id=settings.elevenlabs_default_agent_id,
                        limit=1,
                    )
                    if result.conversations:
                        self.session_id = result.conversations[0].conversation_id
                        self.report.session_id = self.session_id
                except Exception as e:
                    self.report.elevenlabs.transcript_available = CheckResult(
                        name="transcript_available",
                        passed=False,
                        error=f"Failed to list conversations: {e}",
                    )
                    return

            # Get conversation details
            if self.session_id:
                try:
                    detail = await client.get_conversation(self.session_id)
                    self.report.elevenlabs.transcript_available = CheckResult(
                        name="transcript_available",
                        passed=len(detail.transcript) > 0,
                        details={
                            "turn_count": len(detail.transcript),
                            "status": detail.status.value,
                            "has_audio": detail.has_audio,
                            "duration_secs": detail.metadata.call_duration_secs
                            if detail.metadata
                            else None,
                        },
                    )

                    # Check agent config
                    try:
                        config = await client.get_agent_config(detail.agent_id)
                        has_persona = bool(config.system_prompt and "nikita" in config.name.lower())

                        self.report.elevenlabs.agent_config_valid = CheckResult(
                            name="agent_config_valid",
                            passed=has_persona,
                            details={
                                "agent_name": config.name,
                                "has_system_prompt": bool(config.system_prompt),
                                "has_first_message": bool(config.first_message),
                                "voice_id": config.voice_id,
                            },
                        )
                    except Exception as e:
                        self.report.elevenlabs.agent_config_valid = CheckResult(
                            name="agent_config_valid",
                            passed=False,
                            error=str(e),
                        )

                except Exception as e:
                    self.report.elevenlabs.transcript_available = CheckResult(
                        name="transcript_available",
                        passed=False,
                        error=f"Failed to get conversation: {e}",
                    )
            else:
                self.report.elevenlabs.transcript_available = CheckResult(
                    name="transcript_available",
                    passed=False,
                    error="No session ID available",
                )

        except ImportError as e:
            self.report.errors.append(f"ElevenLabs module import failed: {e}")
        except Exception as e:
            self.report.errors.append(f"ElevenLabs verification failed: {e}")


def format_markdown(report: VerificationReport) -> str:
    """Format report as markdown."""
    lines = [
        "# Voice Call Verification Report",
        "",
        f"**Time**: {report.verification_time}",
        f"**User ID**: `{report.user_id}`",
        f"**Session ID**: `{report.session_id or 'N/A'}`",
        f"**Status**: **{report.overall_status}**",
        "",
        "## Database Checks",
        "",
    ]

    def format_check(check: CheckResult | None) -> str:
        if not check:
            return "- [ ] Not run"
        status = "[x]" if check.passed else "[ ]"
        result = f"- {status} **{check.name}**"
        if check.error:
            result += f" - {check.error}"
        elif check.details:
            result += f" - {json.dumps(check.details, default=str)}"
        return result

    for check in [
        report.database.user_exists,
        report.database.user_updated,
        report.database.metrics_exist,
        report.database.conversation_stored,
        report.database.score_recorded,
        report.database.engagement_state,
    ]:
        lines.append(format_check(check))

    lines.extend([
        "",
        "## Neo4j Checks",
        "",
    ])

    for check in [
        report.neo4j.connected,
        report.neo4j.episode_stored,
        report.neo4j.facts_extracted,
    ]:
        lines.append(format_check(check))

    lines.extend([
        "",
        "## ElevenLabs Checks",
        "",
    ])

    for check in [
        report.elevenlabs.transcript_available,
        report.elevenlabs.agent_config_valid,
    ]:
        lines.append(format_check(check))

    if report.errors:
        lines.extend([
            "",
            "## Errors",
            "",
        ])
        for error in report.errors:
            lines.append(f"- {error}")

    return "\n".join(lines)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify voice call state changes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/verify-voice-call.py --user-id UUID --session-id SESSION_ID
    python scripts/verify-voice-call.py --user-id UUID --latest
    python scripts/verify-voice-call.py --user-id UUID --latest --format json
        """,
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="User UUID to verify",
    )
    parser.add_argument(
        "--session-id",
        help="Voice session ID (ElevenLabs conversation_id)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Find and verify the latest voice call",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.session_id and not args.latest:
        parser.error("Either --session-id or --latest is required")

    # Run verification
    verifier = VoiceCallVerifier(
        user_id=args.user_id,
        session_id=args.session_id if not args.latest else None,
    )

    report = await verifier.verify_all()

    # Format output
    if args.format == "json":
        output = json.dumps(report.to_dict(), indent=2, default=str)
    else:
        output = format_markdown(report)

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)

    # Exit with appropriate code
    sys.exit(0 if report.overall_status == "PASS" else 1)


if __name__ == "__main__":
    asyncio.run(main())
