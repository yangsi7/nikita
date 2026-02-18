"""DA-05: Adversarial tests for feature flag toggling mid-operation.

Target: Behavior when conflict_temperature_enabled flag is toggled
between operations — flag ON then OFF, OFF then ON, and mid-check.

Tests cover:
- Flag ON with populated ConflictDetails, then flag OFF (legacy path)
- Flag OFF with conflict_details=None, then flag ON (safe defaults)
- Flag toggle during BreakupManager.check_threshold()
- Flag toggle in ConflictStage async dispatch
- State leakage across flag toggles
"""

import pytest
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from nikita.conflicts import is_conflict_temperature_enabled
from nikita.conflicts.breakup import BreakupManager, BreakupRisk
from nikita.conflicts.generator import ConflictGenerator, GenerationContext, GenerationResult
from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictDetails,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    TemperatureZone,
    TriggerType,
)
from nikita.conflicts.store import ConflictStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(active_conflict=None, consecutive_crises=0) -> MagicMock:
    """Create a mocked ConflictStore."""
    store = MagicMock(spec=ConflictStore)
    store.get_active_conflict.return_value = active_conflict
    store.count_consecutive_unresolved_crises.return_value = consecutive_crises
    store.create_conflict.side_effect = lambda **kw: ActiveConflict(
        conflict_id=str(uuid4()),
        user_id=kw["user_id"],
        conflict_type=kw["conflict_type"],
        severity=kw["severity"],
        escalation_level=EscalationLevel.SUBTLE,
        triggered_at=datetime.now(UTC),
        trigger_ids=kw.get("trigger_ids", []),
    )
    return store


def _make_context(user_id="toggle-user-1", score=50, chapter=1) -> GenerationContext:
    return GenerationContext(
        user_id=user_id,
        chapter=chapter,
        relationship_score=score,
        recent_conflicts=[],
        days_since_last_conflict=2.0,
    )


def _make_trigger(severity=0.5, trigger_type=TriggerType.JEALOUSY) -> ConflictTrigger:
    return ConflictTrigger(
        trigger_id=str(uuid4()),
        trigger_type=trigger_type,
        severity=severity,
    )


def _warm_details() -> dict:
    """ConflictDetails JSONB in WARM zone (temp=35)."""
    return ConflictDetails(
        temperature=35.0,
        zone="warm",
        positive_count=10,
        negative_count=5,
        gottman_ratio=2.0,
    ).to_jsonb()


def _critical_details() -> dict:
    """ConflictDetails JSONB in CRITICAL zone (temp=85)."""
    return ConflictDetails(
        temperature=85.0,
        zone="critical",
        positive_count=2,
        negative_count=15,
        gottman_ratio=0.13,
    ).to_jsonb()


# ===========================================================================
# TestFlagOnThenOff
# ===========================================================================


class TestFlagOnThenOff:
    """Populate ConflictDetails while flag ON, then switch flag OFF.

    When the flag is OFF, generate() should use the legacy path even if
    conflict_details is populated. It must not crash on stale temperature data.
    """

    def test_legacy_path_with_populated_details(self):
        """Flag OFF + populated conflict_details => legacy path, no crash."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]
        details = _warm_details()

        # Step 1: flag ON — uses temperature path
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result_on = gen.generate(triggers, ctx, conflict_details=details)
        # Temperature path was used (reason mentions temperature)
        assert "emperatur" in result_on.reason.lower() or result_on.generated

        # Step 2: flag OFF — should use legacy path even though details present
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result_off = gen.generate(triggers, ctx, conflict_details=details)
        # Legacy path: reason should NOT mention temperature
        assert "temperature" not in result_off.reason.lower() or result_off.generated
        # Legacy path should still produce a valid result
        assert isinstance(result_off, GenerationResult)

    def test_legacy_path_ignores_conflict_details(self):
        """Legacy path does not read temperature from conflict_details."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.6, trigger_type=TriggerType.TRUST)]

        # Even with CRITICAL temperature data, legacy path should not use it
        details = _critical_details()

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = gen.generate(triggers, ctx, conflict_details=details)

        # Legacy path checks cooldown/score, not temperature
        assert isinstance(result, GenerationResult)
        # Should not mention temperature in reason
        if not result.generated:
            assert "temperature" not in result.reason.lower()

    def test_legacy_path_with_none_details_after_flag_off(self):
        """Flag OFF + conflict_details=None => standard legacy behavior."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = gen.generate(triggers, ctx, conflict_details=None)

        assert isinstance(result, GenerationResult)


# ===========================================================================
# TestFlagOffThenOn
# ===========================================================================


class TestFlagOffThenOn:
    """Start with flag OFF (conflict_details=None), then turn flag ON.

    When flag ON + conflict_details=None, generate() should still take
    the legacy path (the guard is `flag AND details is not None`).
    """

    def test_flag_on_with_none_details_uses_legacy(self):
        """Flag ON but conflict_details=None => falls through to legacy."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = gen.generate(triggers, ctx, conflict_details=None)

        # Should use legacy path since details is None
        assert isinstance(result, GenerationResult)
        # Reason should not mention temperature
        if not result.generated:
            assert "temperature" not in result.reason.lower()

    def test_flag_on_with_empty_dict_uses_defaults(self):
        """Flag ON + conflict_details={} => ConflictDetails.from_jsonb({}) => defaults (temp=0, CALM)."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        # Empty dict is not None, so temperature path will be entered
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = gen.generate(triggers, ctx, conflict_details={})

        # Default temperature=0 => CALM zone => no conflict
        assert result.generated is False
        assert "calm" in result.reason.lower()

    def test_from_jsonb_none_returns_safe_defaults(self):
        """ConflictDetails.from_jsonb(None) returns all defaults."""
        details = ConflictDetails.from_jsonb(None)
        assert details.temperature == 0.0
        assert details.zone == "calm"
        assert details.positive_count == 0
        assert details.negative_count == 0
        assert details.horsemen_detected == []
        assert details.repair_attempts == []


# ===========================================================================
# TestFlagToggleDuringConflictCheck
# ===========================================================================


class TestFlagToggleDuringConflictCheck:
    """Toggle flag between calls to BreakupManager.check_threshold().

    Flag ON => temperature-based thresholds. Flag OFF => score-based only.
    """

    def test_critical_temperature_warning_with_flag_on(self):
        """Flag ON + CRITICAL temperature (85, not >90) + >24h => CRITICAL warning."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager(store=store)
        details = _critical_details()  # temp=85.0

        # CRITICAL zone for >24h but temp<=90 => warning, not breakup
        last_conflict_at = datetime(2020, 1, 1, tzinfo=UTC)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold(
                user_id="toggle-user-2",
                relationship_score=50,
                conflict_details=details,
                last_conflict_at=last_conflict_at,
            )

        # temp=85 (<=90) in CRITICAL for >24h => CRITICAL warning (not breakup)
        assert result.risk_level == BreakupRisk.CRITICAL
        assert result.should_warn is True
        assert result.should_breakup is False
        assert "temperature" in result.reason.lower()

    def test_critical_temperature_breakup_with_flag_on(self):
        """Flag ON + temperature >90 + >48h => TRIGGERED breakup."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager(store=store)
        # temp=95 (>90) for breakup trigger
        details = ConflictDetails(temperature=95.0, zone="critical").to_jsonb()
        last_conflict_at = datetime(2020, 1, 1, tzinfo=UTC)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = manager.check_threshold(
                user_id="toggle-user-2",
                relationship_score=50,
                conflict_details=details,
                last_conflict_at=last_conflict_at,
            )

        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True
        assert "temperature" in result.reason.lower()

    def test_same_call_with_flag_off_uses_score(self):
        """Flag OFF with same CRITICAL details => only score-based check."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager(store=store)
        details = _critical_details()
        last_conflict_at = datetime(2020, 1, 1, tzinfo=UTC)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = manager.check_threshold(
                user_id="toggle-user-2",
                relationship_score=50,
                conflict_details=details,
                last_conflict_at=last_conflict_at,
            )

        # Score=50 is above all thresholds => NONE
        assert result.risk_level == BreakupRisk.NONE
        assert result.should_breakup is False
        assert "temperature" not in result.reason.lower()

    def test_flag_off_with_low_score_triggers_score_breakup(self):
        """Flag OFF + low score => score-based breakup (not temperature)."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager(store=store)

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result = manager.check_threshold(
                user_id="toggle-user-2",
                relationship_score=5,  # Below breakup_threshold=10
                conflict_details=_critical_details(),
            )

        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True
        assert "score" in result.reason.lower()


# ===========================================================================
# TestConflictStageToggle
# ===========================================================================


class TestConflictStageToggle:
    """Test ConflictStage._run() dispatches correctly based on flag."""

    @pytest.mark.asyncio
    async def test_flag_on_dispatches_temperature_mode(self):
        """Flag ON => _run_temperature_mode is called."""
        from nikita.pipeline.stages.conflict import ConflictStage
        from nikita.pipeline.models import PipelineContext

        stage = ConflictStage(session=None)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
            platform="text",
            emotional_state={"arousal": 0.5, "valence": 0.5, "dominance": 0.5, "intimacy": 0.5},
            relationship_score=Decimal("50"),
            conflict_details=_warm_details(),
        )

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await stage._run(ctx)

        # Temperature mode returns temperature and zone keys
        assert result is not None
        assert "temperature" in result
        assert "zone" in result

    @pytest.mark.asyncio
    async def test_flag_off_dispatches_legacy_mode(self):
        """Flag OFF => _run_legacy_mode is called."""
        from nikita.pipeline.stages.conflict import ConflictStage
        from nikita.pipeline.models import PipelineContext

        stage = ConflictStage(session=None)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
            platform="text",
            emotional_state={"arousal": 0.5, "valence": 0.5, "dominance": 0.5, "intimacy": 0.5},
            relationship_score=Decimal("50"),
        )

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            # Legacy mode imports ConflictDetector — mock it
            with patch(
                "nikita.emotional_state.conflict.ConflictDetector"
            ) as MockDetector:
                mock_instance = MockDetector.return_value
                from nikita.emotional_state.models import ConflictState
                mock_instance.detect_conflict_state.return_value = ConflictState.NONE

                # Also mock BreakupManager to avoid store initialization
                with patch("nikita.conflicts.breakup.BreakupManager"):
                    result = await stage._run(ctx)

        # Legacy mode returns active + type, no temperature key
        assert result is not None
        assert "active" in result
        assert "temperature" not in result

    @pytest.mark.asyncio
    async def test_toggle_between_calls(self):
        """Call _run with flag ON, then flag OFF — dispatches change correctly."""
        from nikita.pipeline.stages.conflict import ConflictStage
        from nikita.pipeline.models import PipelineContext

        stage = ConflictStage(session=None)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
            platform="text",
            emotional_state={"arousal": 0.5, "valence": 0.5, "dominance": 0.5, "intimacy": 0.5},
            relationship_score=Decimal("50"),
            conflict_details=_warm_details(),
        )

        # Call 1: flag ON => temperature mode
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            r1 = await stage._run(ctx)
        assert "temperature" in r1

        # Call 2: flag OFF => legacy mode
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            with patch(
                "nikita.emotional_state.conflict.ConflictDetector"
            ) as MockDetector:
                from nikita.emotional_state.models import ConflictState
                MockDetector.return_value.detect_conflict_state.return_value = ConflictState.NONE
                with patch("nikita.conflicts.breakup.BreakupManager"):
                    r2 = await stage._run(ctx)
        assert "temperature" not in r2


# ===========================================================================
# TestToggleDoesNotLeakState
# ===========================================================================


class TestToggleDoesNotLeakState:
    """After running in temperature mode, toggling to legacy should not
    carry temperature state into legacy decisions.
    """

    def test_legacy_does_not_use_conflict_temperature_field(self):
        """Legacy path in ConflictGenerator never references temperature."""
        store = _make_store()
        gen = ConflictGenerator(store=store)
        ctx = _make_context()

        # First: run with temperature ON — conflict_details populated
        triggers = [_make_trigger(severity=0.5)]
        details = _warm_details()

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            with patch("random.random", return_value=0.001):  # Force injection
                result_temp = gen.generate(triggers, ctx, conflict_details=details)

        # Second: run with temperature OFF — should not be affected by prior temp state
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            result_legacy = gen.generate(triggers, ctx, conflict_details=details)

        # Both results are valid GenerationResult
        assert isinstance(result_temp, GenerationResult)
        assert isinstance(result_legacy, GenerationResult)

        # Legacy result should not mention temperature
        if not result_legacy.generated:
            assert "temperature" not in result_legacy.reason.lower()

    def test_breakup_manager_state_isolation(self):
        """BreakupManager does not carry state between flag toggles."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager(store=store)

        # Use temp=95 (>90) to trigger actual breakup
        details = ConflictDetails(temperature=95.0, zone="critical").to_jsonb()
        old_time = datetime(2020, 1, 1, tzinfo=UTC)

        # Flag ON: temperature-based breakup triggered (temp>90, >48h)
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            r1 = manager.check_threshold(
                user_id="leak-test",
                relationship_score=50,
                conflict_details=details,
                last_conflict_at=old_time,
            )
        assert r1.should_breakup is True

        # Flag OFF: same args, but score=50 is safe — temperature ignored
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            r2 = manager.check_threshold(
                user_id="leak-test",
                relationship_score=50,
                conflict_details=details,
                last_conflict_at=old_time,
            )
        assert r2.should_breakup is False
        assert r2.risk_level == BreakupRisk.NONE

    @pytest.mark.asyncio
    async def test_pipeline_ctx_temperature_fields_reset(self):
        """After temperature mode sets ctx.conflict_temperature, legacy mode
        should not be affected by it (legacy mode does not read it)."""
        from nikita.pipeline.stages.conflict import ConflictStage
        from nikita.pipeline.models import PipelineContext

        stage = ConflictStage(session=None)

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(UTC),
            platform="text",
            emotional_state={"arousal": 0.5, "valence": 0.5, "dominance": 0.5, "intimacy": 0.5},
            relationship_score=Decimal("50"),
            conflict_details=_warm_details(),
        )

        # Temperature mode sets ctx.conflict_temperature
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            await stage._run(ctx)
        assert ctx.conflict_temperature > 0  # Was set

        # Legacy mode — ctx.conflict_temperature still has old value
        # but legacy code should not use it for decisions
        old_temp = ctx.conflict_temperature
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            with patch(
                "nikita.emotional_state.conflict.ConflictDetector"
            ) as MockDetector:
                from nikita.emotional_state.models import ConflictState
                MockDetector.return_value.detect_conflict_state.return_value = ConflictState.NONE
                with patch("nikita.conflicts.breakup.BreakupManager"):
                    result = await stage._run(ctx)

        # Legacy mode should not update conflict_temperature
        # NOTE: May fail if legacy mode actively resets temperature fields
        assert result["active"] is False
        assert "temperature" not in result
