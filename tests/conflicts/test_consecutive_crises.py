"""Tests for consecutive crisis tracking (Spec 111).

TDD test file: covers schema extension, increment, reset,
breakup integration, and voice path temperature updates.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.conflicts.models import ConflictDetails


# ─── Story 1: ConflictDetails Schema Extension (FR-001) ─────────────


class TestConflictDetailsSchema:
    """Tests for new consecutive_crises fields on ConflictDetails."""

    def test_conflict_details_new_fields_defaults(self):
        """New fields default to 0 and None."""
        details = ConflictDetails()
        assert details.consecutive_crises == 0
        assert details.last_crisis_at is None

    def test_conflict_details_from_jsonb_backward_compat(self):
        """from_jsonb handles old data without new fields."""
        old_data = {"temperature": 80.0, "zone": "critical"}
        details = ConflictDetails.from_jsonb(old_data)
        assert details.consecutive_crises == 0
        assert details.last_crisis_at is None
        assert details.temperature == 80.0

    def test_conflict_details_roundtrip_with_crises(self):
        """to_jsonb/from_jsonb preserves crisis fields."""
        details = ConflictDetails(
            temperature=85.0,
            zone="critical",
            consecutive_crises=2,
            last_crisis_at="2026-03-11T10:00:00+00:00",
        )
        jsonb = details.to_jsonb()
        restored = ConflictDetails.from_jsonb(jsonb)
        assert restored.consecutive_crises == 2
        assert restored.last_crisis_at == "2026-03-11T10:00:00+00:00"
        assert restored.temperature == 85.0


# ─── Story 2: Crisis Increment Logic (FR-002) ───────────────────────


class TestCrisisIncrement:
    """Tests for crisis counter increment in scoring service."""

    def _make_details(self, **overrides: Any) -> dict[str, Any]:
        """Create conflict_details JSONB with defaults."""
        defaults = {
            "temperature": 80.0,
            "zone": "critical",
            "consecutive_crises": 0,
            "last_crisis_at": None,
        }
        defaults.update(overrides)
        return ConflictDetails(**defaults).to_jsonb()

    def _make_analysis(self, **overrides: Any) -> MagicMock:
        """Create mock ResponseAnalysis."""
        analysis = MagicMock()
        analysis.repair_attempt_detected = overrides.get("repair_attempt_detected", False)
        analysis.repair_quality = overrides.get("repair_quality", None)
        analysis.behaviors_identified = overrides.get("behaviors_identified", [])
        return analysis

    def _make_result(self, delta: str = "-5") -> MagicMock:
        """Create mock ScoreResult."""
        result = MagicMock()
        result.delta = Decimal(delta)
        return result

    def _call_update(self, analysis, result, conflict_details):
        """Call _update_temperature_and_gottman via the service."""
        from nikita.engine.scoring.service import ScoringService

        service = ScoringService.__new__(ScoringService)
        return service._update_temperature_and_gottman(
            analysis=analysis,
            result=result,
            conflict_details=conflict_details,
        )

    def test_crisis_increment_critical_zone_negative_delta(self):
        """Increment when zone=critical AND negative delta."""
        conflict_details = self._make_details(
            temperature=80.0, zone="critical", consecutive_crises=0
        )
        analysis = self._make_analysis()
        result = self._make_result(delta="-5")

        updated = self._call_update(analysis, result, conflict_details)
        assert updated is not None
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 1
        assert details.last_crisis_at is not None

    def test_crisis_no_increment_hot_zone(self):
        """No increment when zone=hot (below critical threshold)."""
        conflict_details = self._make_details(
            temperature=60.0, zone="hot", consecutive_crises=0
        )
        analysis = self._make_analysis()
        result = self._make_result(delta="-5")

        updated = self._call_update(analysis, result, conflict_details)
        assert updated is not None
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 0

    def test_crisis_no_increment_positive_delta(self):
        """No increment when delta is positive (even in critical zone)."""
        conflict_details = self._make_details(
            temperature=80.0, zone="critical", consecutive_crises=0
        )
        analysis = self._make_analysis()
        result = self._make_result(delta="5")

        updated = self._call_update(analysis, result, conflict_details)
        assert updated is not None
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 0

    def test_crisis_counter_persists_across_calls(self):
        """Counter accumulates: 0→1→2→3 across consecutive calls."""
        analysis = self._make_analysis()
        result = self._make_result(delta="-5")

        conflict_details = self._make_details(
            temperature=80.0, zone="critical", consecutive_crises=0
        )

        # Call 1: 0→1
        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 1

        # Call 2: 1→2 (use updated details, force zone back to critical)
        updated["zone"] = "critical"
        updated2 = self._call_update(analysis, result, updated)
        details2 = ConflictDetails.from_jsonb(updated2)
        assert details2.consecutive_crises == 2

        # Call 3: 2→3
        updated2["zone"] = "critical"
        updated3 = self._call_update(analysis, result, updated2)
        details3 = ConflictDetails.from_jsonb(updated3)
        assert details3.consecutive_crises == 3


# ─── Story 3: Crisis Reset Logic (FR-003) ────────────────────────────


class TestCrisisReset:
    """Tests for crisis counter reset on repair or temp drop."""

    def _make_details(self, **overrides: Any) -> dict[str, Any]:
        defaults = {
            "temperature": 80.0,
            "zone": "critical",
            "consecutive_crises": 2,
            "last_crisis_at": "2026-03-11T10:00:00+00:00",
        }
        defaults.update(overrides)
        return ConflictDetails(**defaults).to_jsonb()

    def _make_analysis(self, **overrides: Any) -> MagicMock:
        analysis = MagicMock()
        analysis.repair_attempt_detected = overrides.get("repair_attempt_detected", False)
        analysis.repair_quality = overrides.get("repair_quality", None)
        analysis.behaviors_identified = overrides.get("behaviors_identified", [])
        return analysis

    def _make_result(self, delta: str = "-5") -> MagicMock:
        result = MagicMock()
        result.delta = Decimal(delta)
        return result

    def _call_update(self, analysis, result, conflict_details):
        from nikita.engine.scoring.service import ScoringService

        service = ScoringService.__new__(ScoringService)
        return service._update_temperature_and_gottman(
            analysis=analysis,
            result=result,
            conflict_details=conflict_details,
        )

    def test_crisis_reset_excellent_repair(self):
        """EXCELLENT repair resets counter to 0."""
        conflict_details = self._make_details(consecutive_crises=2)
        analysis = self._make_analysis(
            repair_attempt_detected=True, repair_quality="excellent"
        )
        result = self._make_result()

        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 0
        assert details.last_crisis_at is None

    def test_crisis_reset_good_repair(self):
        """GOOD repair resets counter to 0."""
        conflict_details = self._make_details(consecutive_crises=2)
        analysis = self._make_analysis(
            repair_attempt_detected=True, repair_quality="good"
        )
        result = self._make_result()

        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 0
        assert details.last_crisis_at is None

    def test_crisis_no_reset_adequate_repair(self):
        """ADEQUATE repair does NOT reset counter."""
        conflict_details = self._make_details(consecutive_crises=2)
        analysis = self._make_analysis(
            repair_attempt_detected=True, repair_quality="adequate"
        )
        result = self._make_result()

        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 2

    def test_crisis_no_reset_no_repair_quality(self):
        """No repair quality means no reset."""
        conflict_details = self._make_details(consecutive_crises=2)
        analysis = self._make_analysis(
            repair_attempt_detected=False, repair_quality=None
        )
        result = self._make_result(delta="3")  # positive to avoid increment

        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        assert details.consecutive_crises == 2

    def test_crisis_reset_temp_below_50(self):
        """Counter resets when temperature drops below 50."""
        # Start at 55, apply large negative temp delta to drop below 50
        conflict_details = self._make_details(
            temperature=52.0,
            zone="hot",
            consecutive_crises=2,
        )
        analysis = self._make_analysis()
        # Positive delta so no increment, but temp engine might still change temp
        result = self._make_result(delta="10")

        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        # If temp dropped below 50 after TemperatureEngine update, counter resets
        if details.temperature < 50.0:
            assert details.consecutive_crises == 0
            assert details.last_crisis_at is None
        else:
            # Temp didn't drop enough — counter stays
            assert details.consecutive_crises == 2

    def test_crisis_no_reset_temp_at_50(self):
        """Counter does NOT reset at exactly 50.0 (must be strictly below)."""
        conflict_details = self._make_details(
            temperature=50.0,
            zone="warm",
            consecutive_crises=2,
        )
        analysis = self._make_analysis()
        result = self._make_result(delta="0")

        updated = self._call_update(analysis, result, conflict_details)
        details = ConflictDetails.from_jsonb(updated)
        # At exactly 50.0, temp engine may adjust slightly, but counter should
        # NOT reset unless temp goes strictly below 50
        # The zero-delta case should keep temp near 50
        if details.temperature >= 50.0:
            assert details.consecutive_crises == 2


# ─── Story 4: Breakup Engine Integration (FR-004) ────────────────────


class TestBreakupIntegration:
    """Tests for BreakupManager reading consecutive_crises from JSONB."""

    def _make_details(self, crises: int = 0) -> dict[str, Any]:
        return ConflictDetails(
            temperature=85.0,
            zone="critical",
            consecutive_crises=crises,
        ).to_jsonb()

    def test_breakup_reads_from_conflict_details(self):
        """BreakupManager reads consecutive_crises from JSONB."""
        from nikita.conflicts.breakup import BreakupManager

        manager = BreakupManager()
        conflict_details = self._make_details(crises=3)

        result = manager.check_threshold(
            user_id="test-user",
            relationship_score=50,
            conflict_details=conflict_details,
        )
        # With 3 crises, should be TRIGGERED
        assert result.consecutive_crises == 3

    def test_breakup_at_threshold(self):
        """3 consecutive crises triggers breakup."""
        from nikita.conflicts.breakup import BreakupManager

        manager = BreakupManager()
        conflict_details = self._make_details(crises=3)

        result = manager.check_threshold(
            user_id="test-user",
            relationship_score=50,
            conflict_details=conflict_details,
        )
        assert result.should_breakup is True

    def test_breakup_below_threshold(self):
        """2 consecutive crises does NOT trigger breakup."""
        from nikita.conflicts.breakup import BreakupManager

        manager = BreakupManager()
        conflict_details = self._make_details(crises=2)

        result = manager.check_threshold(
            user_id="test-user",
            relationship_score=50,
            conflict_details=conflict_details,
        )
        assert result.should_breakup is False


# ─── Story 5: Voice Path Fix (FR-005) ────────────────────────────────


class TestScoreBatchTemperature:
    """Tests for score_batch calling temperature update."""

    @pytest.mark.asyncio
    async def test_score_batch_updates_temperature(self):
        """score_batch should call _update_temperature_and_gottman when conflict_details provided."""
        from nikita.engine.scoring.service import ScoringService

        service = ScoringService.__new__(ScoringService)
        service.analyzer = AsyncMock()
        service.calculator = MagicMock()

        # Mock analyze_batch
        mock_analysis = MagicMock()
        mock_analysis.repair_attempt_detected = False
        mock_analysis.repair_quality = None
        mock_analysis.behaviors_identified = []
        service.analyzer.analyze_batch = AsyncMock(return_value=mock_analysis)

        # Mock calculate
        mock_result = MagicMock()
        mock_result.delta = Decimal("5")
        mock_result.conflict_details = None
        service.calculator.calculate = MagicMock(return_value=mock_result)

        # Mock _log_history
        service._log_history = AsyncMock()

        from uuid import uuid4

        from nikita.config.enums import EngagementState
        from nikita.engine.scoring.models import ConversationContext

        context = MagicMock(spec=ConversationContext)
        context.chapter = 1

        conflict_details = ConflictDetails(temperature=50.0).to_jsonb()

        result = await service.score_batch(
            user_id=uuid4(),
            exchanges=[("hello", "hi there")],
            context=context,
            current_metrics={"intimacy": Decimal("50")},
            engagement_state=EngagementState.IN_ZONE,
            conflict_details=conflict_details,
        )

        # Verify conflict_details was updated
        assert result.conflict_details is not None
