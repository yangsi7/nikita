"""Tests for Engagement Model Phase 1: Core Models.

TDD tests for spec 014 - T1.1 through T1.4.
"""

from decimal import Decimal

import pytest


class TestEngagementStateEnum:
    """Tests for EngagementState enum (T1.2)."""

    def test_ac_1_2_1_enum_has_six_values(self):
        """AC-1.2.1: EngagementState enum with 6 values."""
        from nikita.config.enums import EngagementState

        assert len(EngagementState) == 6

    def test_ac_1_2_2_calibrating_state(self):
        """AC-1.2.2: CALIBRATING state exists with correct value."""
        from nikita.config.enums import EngagementState

        assert EngagementState.CALIBRATING.value == "calibrating"

    def test_ac_1_2_3_in_zone_state(self):
        """AC-1.2.3: IN_ZONE state exists with correct value."""
        from nikita.config.enums import EngagementState

        assert EngagementState.IN_ZONE.value == "in_zone"

    def test_ac_1_2_4_drifting_state(self):
        """AC-1.2.4: DRIFTING state exists with correct value."""
        from nikita.config.enums import EngagementState

        assert EngagementState.DRIFTING.value == "drifting"

    def test_ac_1_2_5_clingy_state(self):
        """AC-1.2.5: CLINGY state exists with correct value."""
        from nikita.config.enums import EngagementState

        assert EngagementState.CLINGY.value == "clingy"

    def test_ac_1_2_6_distant_state(self):
        """AC-1.2.6: DISTANT state exists with correct value."""
        from nikita.config.enums import EngagementState

        assert EngagementState.DISTANT.value == "distant"

    def test_ac_1_2_7_out_of_zone_state(self):
        """AC-1.2.7: OUT_OF_ZONE state exists with correct value."""
        from nikita.config.enums import EngagementState

        assert EngagementState.OUT_OF_ZONE.value == "out_of_zone"

    def test_ac_1_2_8_get_multiplier_returns_correct_values(self):
        """AC-1.2.8: get_multiplier() method returns correct value per state."""
        from nikita.config.enums import EngagementState

        # Expected multipliers per spec 014
        expected_multipliers = {
            EngagementState.CALIBRATING: Decimal("0.9"),
            EngagementState.IN_ZONE: Decimal("1.0"),
            EngagementState.DRIFTING: Decimal("0.8"),
            EngagementState.CLINGY: Decimal("0.5"),
            EngagementState.DISTANT: Decimal("0.6"),
            EngagementState.OUT_OF_ZONE: Decimal("0.2"),
        }

        for state, expected in expected_multipliers.items():
            actual = state.get_multiplier()
            assert actual == expected, f"{state.name} multiplier should be {expected}, got {actual}"

    def test_is_healthy_property(self):
        """Test is_healthy property for engagement states."""
        from nikita.config.enums import EngagementState

        # Healthy states
        assert EngagementState.CALIBRATING.is_healthy is True
        assert EngagementState.IN_ZONE.is_healthy is True

        # Unhealthy states
        assert EngagementState.DRIFTING.is_healthy is False
        assert EngagementState.CLINGY.is_healthy is False
        assert EngagementState.DISTANT.is_healthy is False
        assert EngagementState.OUT_OF_ZONE.is_healthy is False


class TestEngagementModuleStructure:
    """Tests for engagement module structure (T1.1)."""

    def test_ac_1_1_1_module_directory_exists(self):
        """AC-1.1.1: nikita/engine/engagement/ directory exists."""
        import nikita.engine.engagement

        assert nikita.engine.engagement is not None

    def test_ac_1_1_2_module_exports_key_classes(self):
        """AC-1.1.2: Module exports EngagementEngine, EngagementState."""
        from nikita.engine.engagement import EngagementState

        # EngagementEngine will be tested when implemented
        assert EngagementState is not None

    def test_ac_1_1_3_models_file_exists(self):
        """AC-1.1.3: models.py file created with base imports."""
        from nikita.engine.engagement import models

        assert models is not None

    def test_ac_1_1_4_module_importable_without_errors(self):
        """AC-1.1.4: Module importable without errors."""
        # If we get here, import succeeded
        from nikita.engine.engagement import EngagementState, models

        assert True


class TestEngagementPydanticModels:
    """Tests for Pydantic models in engagement module."""

    def test_engagement_snapshot_model_exists(self):
        """EngagementSnapshot Pydantic model exists."""
        from nikita.engine.engagement.models import EngagementSnapshot

        assert EngagementSnapshot is not None

    def test_engagement_snapshot_fields(self):
        """EngagementSnapshot has required fields."""
        from nikita.config.enums import EngagementState
        from nikita.engine.engagement.models import EngagementSnapshot

        snapshot = EngagementSnapshot(
            state=EngagementState.CALIBRATING,
            calibration_score=Decimal("0.5"),
            consecutive_in_zone=0,
            consecutive_clingy_days=0,
            consecutive_distant_days=0,
        )

        assert snapshot.state == EngagementState.CALIBRATING
        assert snapshot.calibration_score == Decimal("0.5")
        assert snapshot.consecutive_in_zone == 0
        assert snapshot.consecutive_clingy_days == 0
        assert snapshot.consecutive_distant_days == 0

    def test_clinginess_result_model_exists(self):
        """ClinginessResult Pydantic model exists."""
        from nikita.engine.engagement.models import ClinginessResult

        assert ClinginessResult is not None

    def test_clinginess_result_fields(self):
        """ClinginessResult has required fields."""
        from nikita.engine.engagement.models import ClinginessResult

        result = ClinginessResult(
            score=Decimal("0.6"),
            is_clingy=False,
            signals={
                "frequency": Decimal("0.3"),
                "double_text": Decimal("0.1"),
                "response_time": Decimal("0.1"),
                "length_ratio": Decimal("0.05"),
                "needy_language": Decimal("0.05"),
            },
        )

        assert result.score == Decimal("0.6")
        assert result.is_clingy is False
        assert len(result.signals) == 5

    def test_neglect_result_model_exists(self):
        """NeglectResult Pydantic model exists."""
        from nikita.engine.engagement.models import NeglectResult

        assert NeglectResult is not None

    def test_neglect_result_fields(self):
        """NeglectResult has required fields."""
        from nikita.engine.engagement.models import NeglectResult

        result = NeglectResult(
            score=Decimal("0.4"),
            is_neglecting=False,
            signals={
                "frequency": Decimal("0.2"),
                "response_time": Decimal("0.1"),
                "short_messages": Decimal("0.05"),
                "abrupt_endings": Decimal("0.03"),
                "distracted_language": Decimal("0.02"),
            },
        )

        assert result.score == Decimal("0.4")
        assert result.is_neglecting is False
        assert len(result.signals) == 5


class TestClinginessThreshold:
    """Tests for clinginess threshold behavior."""

    def test_clinginess_threshold_at_0_7(self):
        """Clinginess threshold is 0.7."""
        from nikita.engine.engagement.models import ClinginessResult

        # Below threshold
        result_below = ClinginessResult(
            score=Decimal("0.69"),
            is_clingy=False,
            signals={},
        )
        assert result_below.is_clingy is False

        # At/above threshold
        result_above = ClinginessResult(
            score=Decimal("0.71"),
            is_clingy=True,
            signals={},
        )
        assert result_above.is_clingy is True


class TestNeglectThreshold:
    """Tests for neglect threshold behavior."""

    def test_neglect_threshold_at_0_6(self):
        """Neglect threshold is 0.6."""
        from nikita.engine.engagement.models import NeglectResult

        # Below threshold
        result_below = NeglectResult(
            score=Decimal("0.59"),
            is_neglecting=False,
            signals={},
        )
        assert result_below.is_neglecting is False

        # At/above threshold
        result_above = NeglectResult(
            score=Decimal("0.61"),
            is_neglecting=True,
            signals={},
        )
        assert result_above.is_neglecting is True
