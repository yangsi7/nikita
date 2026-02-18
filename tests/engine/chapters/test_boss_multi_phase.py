"""Tests for Spec 058 multi-phase boss integration (flag ON).

AC-8.5: Full integration tests with flag ON.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nikita.engine.chapters.boss import BossPhase, BossPhaseState, BossStateMachine
from nikita.engine.chapters.judgment import BossResult, JudgmentResult
from nikita.engine.chapters.phase_manager import BossPhaseManager


@pytest.fixture
def boss():
    return BossStateMachine()


@pytest.fixture
def phase_mgr():
    return BossPhaseManager()


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    user = SimpleNamespace(chapter=3, boss_attempts=0)
    repo.get.return_value = user
    repo.update_game_status.return_value = None
    repo.advance_chapter.return_value = SimpleNamespace(chapter=4, boss_attempts=0)
    repo.increment_boss_attempts.return_value = SimpleNamespace(
        chapter=3, boss_attempts=1,
    )
    return repo


class TestFullTwoPhaseFlowPass:
    """Full 2-phase flow: OPENING -> RESOLUTION -> PASS."""

    def test_opening_to_resolution(self, phase_mgr):
        state = phase_mgr.start_boss(chapter=3)
        assert state.phase == BossPhase.OPENING

        advanced = phase_mgr.advance_phase(state, "my response", "resolution prompt")
        assert advanced.phase == BossPhase.RESOLUTION
        assert advanced.turn_count == 1
        assert len(advanced.conversation_history) == 2

    @pytest.mark.asyncio
    async def test_resolution_pass_advances_chapter(self, boss, mock_user_repo):
        result = await boss.process_outcome(
            user_id="test-user",
            user_repository=mock_user_repo,
            outcome="PASS",
        )
        assert result["outcome"] == "PASS"
        assert result["passed"] is True
        mock_user_repo.advance_chapter.assert_called_once()


class TestFullTwoPhaseFlowPartial:
    """Full 2-phase flow: OPENING -> RESOLUTION -> PARTIAL."""

    @pytest.mark.asyncio
    async def test_partial_no_penalty_no_advance(self, boss, mock_user_repo):
        result = await boss.process_outcome(
            user_id="test-user",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        assert result["outcome"] == "PARTIAL"
        assert result["game_status"] == "active"
        mock_user_repo.advance_chapter.assert_not_called()
        mock_user_repo.increment_boss_attempts.assert_not_called()


class TestFullTwoPhaseFlowFail:
    """Full 2-phase flow: OPENING -> RESOLUTION -> FAIL."""

    @pytest.mark.asyncio
    async def test_fail_increments_attempts(self, boss, mock_user_repo):
        result = await boss.process_outcome(
            user_id="test-user",
            user_repository=mock_user_repo,
            outcome="FAIL",
        )
        assert result["outcome"] == "FAIL"
        assert result["passed"] is False
        mock_user_repo.increment_boss_attempts.assert_called_once()


class TestBossTimeoutIntegration:
    """24h timeout auto-FAIL integration."""

    def test_timeout_detected(self, phase_mgr):
        state = BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=2,
            started_at=datetime.now(UTC) - timedelta(hours=25),
        )
        assert phase_mgr.is_timed_out(state) is True

    def test_no_timeout_within_window(self, phase_mgr):
        state = phase_mgr.start_boss(chapter=2)
        assert phase_mgr.is_timed_out(state) is False


class TestInterruptedBoss:
    """Boss can be interrupted by non-boss messages (phase preserved)."""

    def test_phase_persists_through_serialization(self, phase_mgr):
        state = phase_mgr.start_boss(chapter=4)
        advanced = phase_mgr.advance_phase(state, "msg", "resp")

        # Persist and reload (simulates server restart)
        details = phase_mgr.persist_phase(None, advanced)
        loaded = phase_mgr.load_phase(details)

        assert loaded is not None
        assert loaded.phase == BossPhase.RESOLUTION
        assert loaded.chapter == 4
        assert loaded.turn_count == 1
        assert len(loaded.conversation_history) == 2


class TestPersistenceRoundTrip:
    """Server restart simulation."""

    def test_full_roundtrip_through_jsonb(self, phase_mgr):
        # Create state
        state = phase_mgr.start_boss(chapter=5)
        advanced = phase_mgr.advance_phase(state, "opening reply", "resolution prompt")

        # Serialize to JSONB
        details = phase_mgr.persist_phase({"temperature": 30.0}, advanced)

        # Simulate DB read
        import json
        jsonb_str = json.dumps(details)
        restored_details = json.loads(jsonb_str)

        # Load state
        loaded = phase_mgr.load_phase(restored_details)
        assert loaded is not None
        assert loaded.phase == BossPhase.RESOLUTION
        assert loaded.chapter == 5
        assert loaded.turn_count == 1

    def test_clear_after_completion(self, phase_mgr):
        state = phase_mgr.start_boss(chapter=1)
        details = phase_mgr.persist_phase(None, state)
        assert phase_mgr.load_phase(details) is not None

        cleared = phase_mgr.clear_boss_phase(details)
        assert phase_mgr.load_phase(cleared) is None
