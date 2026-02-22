"""Tests for Spec 058 ConflictDetails.boss_phase field."""

from __future__ import annotations

from datetime import UTC, datetime

from nikita.conflicts.models import ConflictDetails
from nikita.engine.chapters.boss import BossPhase, BossPhaseState


class TestConflictDetailsBossPhase:
    """AC-2.2, AC-2.5: boss_phase field in ConflictDetails."""

    def test_boss_phase_none_by_default(self):
        details = ConflictDetails()
        assert details.boss_phase is None

    def test_stores_boss_phase_state_roundtrip(self):
        state = BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=2,
            started_at=datetime.now(UTC),
        )
        details = ConflictDetails(boss_phase=state.model_dump(mode="json"))
        # Round-trip through JSONB
        jsonb = details.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert restored.boss_phase is not None
        parsed = BossPhaseState.model_validate(restored.boss_phase)
        assert parsed.phase == BossPhase.OPENING
        assert parsed.chapter == 2

    def test_from_jsonb_with_no_boss_phase(self):
        details = ConflictDetails.from_jsonb({"temperature": 25.0})
        assert details.boss_phase is None

    def test_from_jsonb_with_empty_dict(self):
        details = ConflictDetails.from_jsonb({})
        assert details.boss_phase is None
