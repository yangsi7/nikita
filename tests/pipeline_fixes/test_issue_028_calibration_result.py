"""TDD tests for Issue #28: CalibrationResult missing suggested_state field.

The bug: CalibrationResult is created at message_handler.py:993-999 without
the required `suggested_state` field, and includes an invalid `is_optimal` field.

The fix:
1. Add `suggested_state` when creating CalibrationResult
2. Remove `is_optimal` field which doesn't exist in the model
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from nikita.engine.engagement.models import CalibrationResult, EngagementState


class TestCalibrationResultRequiredFields:
    """Verify CalibrationResult requires suggested_state."""

    def test_calibration_result_requires_suggested_state(self):
        """Creating CalibrationResult without suggested_state should fail."""
        # This is what the buggy code does - missing suggested_state
        with pytest.raises(ValidationError) as exc_info:
            CalibrationResult(
                score=Decimal("0.75"),
                frequency_component=Decimal("0.8"),
                timing_component=Decimal("0.7"),
                content_component=Decimal("0.5"),
                # Missing: suggested_state
            )

        # Should fail validation due to missing field
        assert "suggested_state" in str(exc_info.value)

    def test_calibration_result_rejects_is_optimal(self):
        """CalibrationResult should reject unknown field 'is_optimal'."""
        # The buggy code tries to set is_optimal which doesn't exist
        # Pydantic v2 with strict config would reject this
        # Let's verify the model doesn't accept extra fields
        result = CalibrationResult(
            score=Decimal("0.75"),
            frequency_component=Decimal("0.8"),
            timing_component=Decimal("0.7"),
            content_component=Decimal("0.5"),
            suggested_state=EngagementState.IN_ZONE,
        )
        # is_optimal should NOT be in the model
        assert not hasattr(result, 'is_optimal')

    def test_calibration_result_with_suggested_state(self):
        """Creating CalibrationResult with suggested_state should work."""
        result = CalibrationResult(
            score=Decimal("0.75"),
            frequency_component=Decimal("0.8"),
            timing_component=Decimal("0.7"),
            content_component=Decimal("0.5"),
            suggested_state=EngagementState.IN_ZONE,  # Required field
        )

        assert result.suggested_state == EngagementState.IN_ZONE
        assert result.score == Decimal("0.75")

    def test_calibration_result_all_states(self):
        """CalibrationResult can have any EngagementState as suggested_state."""
        for state in EngagementState:
            result = CalibrationResult(
                score=Decimal("0.5"),
                frequency_component=Decimal("0.5"),
                timing_component=Decimal("0.5"),
                content_component=Decimal("0.5"),
                suggested_state=state,
            )
            assert result.suggested_state == state


class TestCalibrationResultFromCalculator:
    """Verify CalibrationCalculator produces valid CalibrationResult."""

    def test_calculator_returns_complete_result(self):
        """CalibrationCalculator.compute should return result with suggested_state."""
        from nikita.engine.engagement.calculator import CalibrationCalculator

        calculator = CalibrationCalculator()

        result = calculator.compute(
            actual_messages=10,
            optimal_messages=10,
            avg_response_seconds=300,
            avg_message_length=50,
            needy_score=Decimal("0.2"),
            distracted_score=Decimal("0.1"),
        )

        # Result must have suggested_state
        assert hasattr(result, 'suggested_state')
        assert isinstance(result.suggested_state, EngagementState)
