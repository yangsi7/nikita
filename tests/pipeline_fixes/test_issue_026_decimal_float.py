"""TDD tests for Issue #26: Decimal/float division error.

The bug: relationship_score from DB is Decimal(5,2), but arithmetic uses float literals.
When computing: `(relationship_score - 0.5) * 0.2`, if relationship_score is Decimal,
this causes type errors.

The fix: Convert relationship_score to float at the start of _apply_relationship_modifier.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from nikita.emotional_state.computer import StateComputer


class TestDecimalFloatConversion:
    """Verify StateComputer handles Decimal relationship_score."""

    def test_compute_with_decimal_relationship_score(self):
        """StateComputer.compute should handle Decimal relationship_score."""
        computer = StateComputer()
        user_id = uuid4()

        # This is how relationship_score comes from the DB (Decimal)
        relationship_score = Decimal("75.50")

        # Should NOT raise TypeError on arithmetic with float literals
        result = computer.compute(
            user_id=user_id,
            chapter=3,
            relationship_score=relationship_score,  # Decimal input
            life_events=None,
        )

        # Should return valid emotional state
        assert result is not None
        assert 0.0 <= result.arousal <= 1.0
        assert 0.0 <= result.valence <= 1.0
        assert 0.0 <= result.dominance <= 1.0
        assert 0.0 <= result.intimacy <= 1.0

    def test_compute_with_float_relationship_score(self):
        """StateComputer.compute should still work with float relationship_score."""
        computer = StateComputer()
        user_id = uuid4()

        # Float input should still work
        relationship_score = 75.50

        result = computer.compute(
            user_id=user_id,
            chapter=3,
            relationship_score=relationship_score,
            life_events=None,
        )

        assert result is not None
        assert 0.0 <= result.arousal <= 1.0

    def test_apply_relationship_modifier_with_decimal(self):
        """_apply_relationship_modifier should handle Decimal input."""
        computer = StateComputer()

        # This would fail before the fix with:
        # TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and 'float'
        result = computer._apply_relationship_modifier(
            chapter=3,
            relationship_score=Decimal("0.75"),  # Decimal (0-1 scale)
        )

        # Should return dict with float deltas
        assert isinstance(result, dict)
        assert "valence_delta" in result
        assert isinstance(result["valence_delta"], float)

    def test_apply_relationship_modifier_edge_cases(self):
        """Test edge cases for relationship score conversion."""
        computer = StateComputer()

        # Test boundary values
        for score in [Decimal("0.0"), Decimal("0.5"), Decimal("1.0")]:
            result = computer._apply_relationship_modifier(
                chapter=1,
                relationship_score=score,
            )
            assert isinstance(result, dict)
            # No exception raised

    def test_compute_preserves_computation_accuracy(self):
        """Ensure Decimal to float conversion doesn't change results."""
        computer = StateComputer()
        user_id = uuid4()

        # Same value as Decimal and float
        result_decimal = computer.compute(
            user_id=user_id,
            chapter=3,
            relationship_score=Decimal("75.00"),
            life_events=None,
        )

        result_float = computer.compute(
            user_id=user_id,
            chapter=3,
            relationship_score=75.0,
            life_events=None,
        )

        # Results should be the same (or very close due to floating point)
        assert abs(result_decimal.valence - result_float.valence) < 0.001
        assert abs(result_decimal.arousal - result_float.arousal) < 0.001
