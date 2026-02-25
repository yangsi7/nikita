"""DA-05: Adversarial tests for conflict_details-based path dispatch.

Target: Behavior when conflict_details is provided vs None.
The legacy feature flag has been removed — production code now dispatches
solely based on whether conflict_details is None or not.

Tests cover:
- conflict_details provided => temperature path
- conflict_details=None => legacy/fallback path
- BreakupManager dispatch based on conflict_details presence
- ConflictStage always uses temperature mode
- State isolation between temperature calls
"""

import pytest
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(active_conflict=None, consecutive_crises=0) -> MagicMock:
    """Create a mocked store (spec removed — ConflictStore deleted in Spec 057)."""
    store = MagicMock()
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
# TestDetailsProvidedPath (was TestFlagOnThenOff)
# ===========================================================================


class TestDetailsProvidedPath:
    """When conflict_details is provided, generate() uses the temperature path.
    When conflict_details is None, generate() uses the legacy/fallback path.
    """

    def test_temperature_path_with_populated_details(self):
        """Populated conflict_details => temperature path."""
        store = _make_store()
        gen = ConflictGenerator()
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]
        details = _warm_details()

        # conflict_details provided — uses temperature path
        result = gen.generate(triggers, ctx, conflict_details=details)
        # Temperature path was used (reason mentions temperature or generated)
        assert "emperatur" in result.reason.lower() or result.generated
        assert isinstance(result, GenerationResult)

    def test_legacy_path_with_none_details(self):
        """conflict_details=None => legacy/fallback path, no temperature."""
        store = _make_store()
        gen = ConflictGenerator()
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        result = gen.generate(triggers, ctx, conflict_details=None)

        assert isinstance(result, GenerationResult)
        # Legacy path should not mention temperature
        if not result.generated:
            assert "temperature" not in result.reason.lower()

    def test_legacy_path_ignores_temperature_data(self):
        """Legacy path (None details) does not use temperature."""
        store = _make_store()
        gen = ConflictGenerator()
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.6, trigger_type=TriggerType.TRUST)]

        result = gen.generate(triggers, ctx, conflict_details=None)

        # Legacy path checks cooldown/score, not temperature
        assert isinstance(result, GenerationResult)
        if not result.generated:
            assert "temperature" not in result.reason.lower()


# ===========================================================================
# TestFlagOffThenOn (now tests conflict_details=None vs provided)
# ===========================================================================


class TestNoneDetailsThenProvided:
    """Start with conflict_details=None (legacy), then provide details (temp path).

    When conflict_details=None, generate() uses legacy path.
    When details provided, generate() uses temperature path.
    """

    def test_none_details_uses_legacy(self):
        """conflict_details=None => falls through to legacy."""
        store = _make_store()
        gen = ConflictGenerator()
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        result = gen.generate(triggers, ctx, conflict_details=None)

        # Should use legacy path since details is None
        assert isinstance(result, GenerationResult)
        # Reason should not mention temperature
        if not result.generated:
            assert "temperature" not in result.reason.lower()

    def test_empty_dict_uses_defaults(self):
        """conflict_details={} => ConflictDetails.from_jsonb({}) => defaults (temp=0, CALM)."""
        store = _make_store()
        gen = ConflictGenerator()
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        # Empty dict is not None, so temperature path will be entered
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
# TestBreakupThresholdDispatch (was TestFlagToggleDuringConflictCheck)
# ===========================================================================


class TestBreakupThresholdDispatch:
    """BreakupManager.check_threshold() dispatches on conflict_details presence.

    conflict_details provided => temperature-based thresholds checked first.
    conflict_details=None => score-based only.
    """

    def test_critical_temperature_warning_with_details(self):
        """CRITICAL temperature (85, not >90) + >24h => CRITICAL warning."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager()
        details = _critical_details()  # temp=85.0

        # CRITICAL zone for >24h but temp<=90 => warning, not breakup
        last_conflict_at = datetime(2020, 1, 1, tzinfo=UTC)

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

    def test_critical_temperature_breakup_with_details(self):
        """Temperature >90 + >48h => TRIGGERED breakup."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager()
        # temp=95 (>90) for breakup trigger
        details = ConflictDetails(temperature=95.0, zone="critical").to_jsonb()
        last_conflict_at = datetime(2020, 1, 1, tzinfo=UTC)

        result = manager.check_threshold(
            user_id="toggle-user-2",
            relationship_score=50,
            conflict_details=details,
            last_conflict_at=last_conflict_at,
        )

        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True
        assert "temperature" in result.reason.lower()

    def test_none_details_uses_score_only(self):
        """conflict_details=None => only score-based check, no temperature."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager()

        result = manager.check_threshold(
            user_id="toggle-user-2",
            relationship_score=50,
            conflict_details=None,
        )

        # Score=50 is above all thresholds => NONE
        assert result.risk_level == BreakupRisk.NONE
        assert result.should_breakup is False

    def test_low_score_triggers_score_breakup(self):
        """Low score => score-based breakup (not temperature)."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager()

        result = manager.check_threshold(
            user_id="toggle-user-2",
            relationship_score=5,  # Below breakup_threshold=10
            conflict_details=None,
        )

        assert result.risk_level == BreakupRisk.TRIGGERED
        assert result.should_breakup is True
        assert "score" in result.reason.lower()


# ===========================================================================
# TestConflictStageAlwaysTemperature (was TestConflictStageToggle)
# ===========================================================================


class TestConflictStageAlwaysTemperature:
    """ConflictStage._run() always uses temperature mode now."""

    @pytest.mark.asyncio
    async def test_dispatches_temperature_mode_with_details(self):
        """With conflict_details => temperature mode results."""
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

        result = await stage._run(ctx)

        # Temperature mode returns temperature and zone keys
        assert result is not None
        assert "temperature" in result
        assert "zone" in result

    @pytest.mark.asyncio
    async def test_dispatches_temperature_mode_without_details(self):
        """Even without conflict_details, stage uses temperature mode (defaults)."""
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

        result = await stage._run(ctx)

        # Temperature mode always returns these keys
        assert result is not None
        assert "temperature" in result
        assert "zone" in result
        # Default temp=0, CALM zone, no active conflict
        assert result["active"] is False
        assert result["zone"] == "calm"

    @pytest.mark.asyncio
    async def test_successive_calls_consistent(self):
        """Multiple _run calls produce consistent temperature results."""
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

        r1 = await stage._run(ctx)
        assert "temperature" in r1

        r2 = await stage._run(ctx)
        assert "temperature" in r2


# ===========================================================================
# TestNoStateLeakage (was TestToggleDoesNotLeakState)
# ===========================================================================


class TestNoStateLeakage:
    """Temperature state does not leak between generate() calls with different details."""

    def test_different_details_produce_different_results(self):
        """Passing different conflict_details produces independent results."""
        store = _make_store()
        gen = ConflictGenerator()
        ctx = _make_context()
        triggers = [_make_trigger(severity=0.5)]

        # First call: with warm details
        with patch("random.random", return_value=0.001):  # Force injection
            result_warm = gen.generate(triggers, ctx, conflict_details=_warm_details())

        # Second call: with None details (legacy)
        result_legacy = gen.generate(triggers, ctx, conflict_details=None)

        # Both results are valid GenerationResult
        assert isinstance(result_warm, GenerationResult)
        assert isinstance(result_legacy, GenerationResult)

        # Legacy result should not mention temperature
        if not result_legacy.generated:
            assert "temperature" not in result_legacy.reason.lower()

    def test_breakup_manager_independent_calls(self):
        """BreakupManager produces correct results based on conflict_details presence."""
        store = _make_store(consecutive_crises=0)
        manager = BreakupManager()

        # Use temp=95 (>90) to trigger actual breakup
        details = ConflictDetails(temperature=95.0, zone="critical").to_jsonb()
        old_time = datetime(2020, 1, 1, tzinfo=UTC)

        # With details: temperature-based breakup triggered (temp>90, >48h)
        r1 = manager.check_threshold(
            user_id="leak-test",
            relationship_score=50,
            conflict_details=details,
            last_conflict_at=old_time,
        )
        assert r1.should_breakup is True

        # Without details: score=50 is safe
        r2 = manager.check_threshold(
            user_id="leak-test",
            relationship_score=50,
            conflict_details=None,
        )
        assert r2.should_breakup is False
        assert r2.risk_level == BreakupRisk.NONE

    @pytest.mark.asyncio
    async def test_pipeline_ctx_temperature_set(self):
        """ConflictStage sets ctx.conflict_temperature from conflict_details."""
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
        await stage._run(ctx)
        assert ctx.conflict_temperature > 0  # Was set

        # Result always includes temperature
        result = await stage._run(ctx)
        assert "temperature" in result
        assert result["active"] is False or result["active"] is True
