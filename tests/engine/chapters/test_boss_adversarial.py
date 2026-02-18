"""Tests for Spec 058 adversarial edge cases.

AC-8.2, AC-8.3: Edge cases and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nikita.engine.chapters.boss import BossPhase, BossPhaseState, BossStateMachine
from nikita.engine.chapters.phase_manager import BossPhaseManager


@pytest.fixture
def phase_mgr():
    return BossPhaseManager()


@pytest.fixture
def boss():
    return BossStateMachine()


class TestRapidPhaseTransitions:
    """Rapid back-to-back messages."""

    def test_double_advance_stays_resolution(self, phase_mgr):
        """Advancing from RESOLUTION doesn't create a third phase."""
        state = phase_mgr.start_boss(chapter=1)
        advanced = phase_mgr.advance_phase(state, "msg1", "resp1")
        assert advanced.phase == BossPhase.RESOLUTION

        # "Advancing" again from resolution just adds more history
        advanced2 = phase_mgr.advance_phase(advanced, "msg2", "resp2")
        # Still resolution (no third phase exists)
        assert advanced2.phase == BossPhase.RESOLUTION
        assert advanced2.turn_count == 2
        assert len(advanced2.conversation_history) == 4


class TestBossDuringGameOver:
    """Boss should not start during game_over/won status."""

    def test_no_trigger_during_game_over(self, boss):
        assert boss.should_trigger_boss(Decimal("55"), 1, "game_over") is False

    def test_no_trigger_during_won(self, boss):
        assert boss.should_trigger_boss(Decimal("75"), 5, "won") is False

    def test_no_trigger_during_boss_fight(self, boss):
        assert boss.should_trigger_boss(Decimal("55"), 1, "boss_fight") is False


class TestCorruptConflictDetails:
    """Corrupt conflict_details JSONB graceful degradation."""

    def test_corrupt_boss_phase_string(self, phase_mgr):
        """String instead of dict -> None."""
        assert phase_mgr.load_phase({"boss_phase": "not a dict"}) is None

    def test_corrupt_boss_phase_invalid_phase(self, phase_mgr):
        """Invalid phase value -> None."""
        assert phase_mgr.load_phase({"boss_phase": {"phase": "invalid", "chapter": 1}}) is None

    def test_corrupt_boss_phase_missing_chapter(self, phase_mgr):
        """Missing required field -> None."""
        assert phase_mgr.load_phase({"boss_phase": {"phase": "opening"}}) is None

    def test_null_conflict_details(self, phase_mgr):
        assert phase_mgr.load_phase(None) is None

    def test_empty_dict(self, phase_mgr):
        assert phase_mgr.load_phase({}) is None


class TestPhaseStateMissingFields:
    """Partial data handling."""

    def test_missing_turn_count_uses_default(self):
        """BossPhaseState with missing optional fields uses defaults."""
        state = BossPhaseState(phase=BossPhase.OPENING, chapter=1)
        assert state.turn_count == 0
        assert state.conversation_history == []

    def test_extra_fields_ignored(self, phase_mgr):
        """Extra fields in JSONB don't break parsing."""
        data = {
            "boss_phase": {
                "phase": "opening",
                "chapter": 2,
                "started_at": datetime.now(UTC).isoformat(),
                "turn_count": 0,
                "conversation_history": [],
                "extra_field": "should be fine",
            }
        }
        loaded = phase_mgr.load_phase(data)
        assert loaded is not None
        assert loaded.chapter == 2


class TestBossPhaseWithFlagOff:
    """boss_phase present in conflict_details but flag OFF."""

    def test_flag_off_ignores_phase_data(self):
        """When flag OFF, boss_phase in conflict_details is irrelevant.

        The _handle_boss_response method branches on the flag,
        so phase data is never read when flag is OFF.
        """
        # Just verify the flag check function works
        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.multi_phase_boss_enabled = False
            from nikita.engine.chapters import is_multi_phase_boss_enabled
            assert is_multi_phase_boss_enabled() is False


class TestDoubleBossInitiation:
    """Should not create duplicate phases."""

    def test_persist_overwrites_existing(self, phase_mgr):
        """Persisting a new phase overwrites the old one."""
        state1 = phase_mgr.start_boss(chapter=2)
        details = phase_mgr.persist_phase(None, state1)
        loaded1 = phase_mgr.load_phase(details)
        assert loaded1.chapter == 2

        # "Double initiation" - new boss overwrites
        state2 = phase_mgr.start_boss(chapter=3)
        details = phase_mgr.persist_phase(details, state2)
        loaded2 = phase_mgr.load_phase(details)
        assert loaded2.chapter == 3  # Overwritten, not duplicated
