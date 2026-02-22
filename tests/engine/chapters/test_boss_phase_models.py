"""Tests for Spec 058 BossPhase enum and BossPhaseState model."""

from __future__ import annotations

from datetime import UTC, datetime

from nikita.engine.chapters.boss import BossPhase, BossPhaseState


class TestBossPhaseEnum:
    """AC-2.1: BossPhase enum values."""

    def test_opening_value(self):
        assert BossPhase.OPENING == "opening"
        assert BossPhase.OPENING.value == "opening"

    def test_resolution_value(self):
        assert BossPhase.RESOLUTION == "resolution"
        assert BossPhase.RESOLUTION.value == "resolution"

    def test_is_str_enum(self):
        assert isinstance(BossPhase.OPENING, str)


class TestBossPhaseState:
    """AC-2.1: BossPhaseState model defaults and serialization."""

    def test_defaults(self):
        state = BossPhaseState(phase=BossPhase.OPENING, chapter=1)
        assert state.phase == BossPhase.OPENING
        assert state.chapter == 1
        assert state.turn_count == 0
        assert state.conversation_history == []
        assert isinstance(state.started_at, datetime)

    def test_serialization_roundtrip(self):
        now = datetime.now(UTC)
        state = BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=3,
            started_at=now,
            turn_count=1,
            conversation_history=[{"role": "user", "content": "test"}],
        )
        dumped = state.model_dump(mode="json")
        restored = BossPhaseState.model_validate(dumped)
        assert restored.phase == BossPhase.OPENING
        assert restored.chapter == 3
        assert restored.turn_count == 1
        assert len(restored.conversation_history) == 1
        assert restored.conversation_history[0]["role"] == "user"

    def test_datetime_handling(self):
        state = BossPhaseState(phase=BossPhase.RESOLUTION, chapter=5)
        dumped = state.model_dump(mode="json")
        assert isinstance(dumped["started_at"], str)
        restored = BossPhaseState.model_validate(dumped)
        assert isinstance(restored.started_at, datetime)
