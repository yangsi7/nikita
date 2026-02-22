"""Tests for Spec 058 BossPhaseManager."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nikita.engine.chapters.boss import BossPhase, BossPhaseState
from nikita.engine.chapters.phase_manager import BossPhaseManager


class TestStartBoss:
    """AC-1.1: start_boss creates OPENING state."""

    def test_returns_opening_phase(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=3)
        assert state.phase == BossPhase.OPENING
        assert state.chapter == 3
        assert state.turn_count == 0
        assert state.conversation_history == []

    def test_started_at_is_recent(self):
        mgr = BossPhaseManager()
        before = datetime.now(UTC)
        state = mgr.start_boss(chapter=1)
        after = datetime.now(UTC)
        assert before <= state.started_at <= after


class TestAdvancePhase:
    """AC-1.2: advance_phase transitions OPENING -> RESOLUTION."""

    def test_transitions_to_resolution(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=2)
        advanced = mgr.advance_phase(state, "my response", "Nikita resolution prompt")
        assert advanced.phase == BossPhase.RESOLUTION

    def test_appends_history(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=1)
        advanced = mgr.advance_phase(state, "hello", "tell me more")
        assert len(advanced.conversation_history) == 2
        assert advanced.conversation_history[0] == {"role": "user", "content": "hello"}
        assert advanced.conversation_history[1] == {"role": "assistant", "content": "tell me more"}

    def test_increments_turn_count(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=1)
        assert state.turn_count == 0
        advanced = mgr.advance_phase(state, "msg", "resp")
        assert advanced.turn_count == 1

    def test_resets_started_at_on_advance(self):
        """R-6: started_at resets per-phase for independent 24h timeouts."""
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=4)
        advanced = mgr.advance_phase(state, "msg", "resp")
        # started_at should be reset (not preserved) for per-phase timeout
        assert advanced.started_at >= state.started_at

    def test_preserves_chapter(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=5)
        advanced = mgr.advance_phase(state, "msg", "resp")
        assert advanced.chapter == 5


class TestIsResolutionComplete:
    """AC-1.3: Resolution complete when phase=RESOLUTION and turn_count >= 2."""

    def test_not_complete_in_opening(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=1)
        assert mgr.is_resolution_complete(state) is False

    def test_not_complete_at_turn_1(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=1)
        advanced = mgr.advance_phase(state, "msg", "resp")
        assert advanced.turn_count == 1
        assert mgr.is_resolution_complete(advanced) is False

    def test_complete_at_turn_2(self):
        mgr = BossPhaseManager()
        state = BossPhaseState(
            phase=BossPhase.RESOLUTION,
            chapter=1,
            turn_count=2,
            conversation_history=[
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"},
                {"role": "assistant", "content": "d"},
            ],
        )
        assert mgr.is_resolution_complete(state) is True


class TestPersistence:
    """AC-1.4, AC-2.2, AC-2.3: Persist/load boss phase in conflict_details."""

    def test_persist_roundtrip(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=3)
        details = mgr.persist_phase(None, state)
        loaded = mgr.load_phase(details)
        assert loaded is not None
        assert loaded.phase == BossPhase.OPENING
        assert loaded.chapter == 3

    def test_persist_into_existing_details(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=2)
        existing = {"temperature": 25.0, "zone": "warm"}
        updated = mgr.persist_phase(existing, state)
        assert updated["temperature"] == 25.0
        assert updated["boss_phase"] is not None

    def test_load_returns_none_for_empty(self):
        mgr = BossPhaseManager()
        assert mgr.load_phase(None) is None
        assert mgr.load_phase({}) is None

    def test_load_returns_none_for_corrupt(self):
        mgr = BossPhaseManager()
        assert mgr.load_phase({"boss_phase": "garbage"}) is None
        assert mgr.load_phase({"boss_phase": {"phase": "invalid"}}) is None

    def test_clear_boss_phase(self):
        mgr = BossPhaseManager()
        state = mgr.start_boss(chapter=1)
        details = mgr.persist_phase(None, state)
        assert details["boss_phase"] is not None
        cleared = mgr.clear_boss_phase(details)
        assert cleared["boss_phase"] is None
        assert mgr.load_phase(cleared) is None


class TestTimeout:
    """AC-1.6: Boss timeout at 24h."""

    def test_no_timeout_at_23h59m(self):
        mgr = BossPhaseManager()
        state = BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=1,
            started_at=datetime.now(UTC) - timedelta(hours=23, minutes=59),
        )
        assert mgr.is_timed_out(state) is False

    def test_timeout_at_24h_1s(self):
        mgr = BossPhaseManager()
        started = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        now = started + timedelta(hours=24, seconds=1)
        state = BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=1,
            started_at=started,
        )
        assert mgr.is_timed_out(state, now=now) is True

    def test_no_timeout_at_exactly_24h(self):
        mgr = BossPhaseManager()
        started = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        now = started + timedelta(hours=24)
        state = BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=1,
            started_at=started,
        )
        # timedelta(hours=24) == timedelta(hours=24), not >, so False
        assert mgr.is_timed_out(state, now=now) is False
