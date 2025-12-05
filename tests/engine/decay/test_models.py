"""Tests for decay system models (spec 005).

TDD: These tests define the expected behavior for DecayResult model.
Tests written FIRST before implementation.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from nikita.engine.decay.models import DecayResult


class TestDecayResult:
    """Test DecayResult model with audit trail fields."""

    def test_valid_decay_result(self):
        """Test creating a valid DecayResult with all required fields."""
        user_id = uuid4()
        result = DecayResult(
            user_id=user_id,
            decay_amount=Decimal("2.4"),
            score_before=Decimal("65.0"),
            score_after=Decimal("62.6"),
            hours_overdue=3.0,
            chapter=1,
            timestamp=datetime.now(UTC),
        )
        assert result.user_id == user_id
        assert result.decay_amount == Decimal("2.4")
        assert result.score_before == Decimal("65.0")
        assert result.score_after == Decimal("62.6")
        assert result.hours_overdue == 3.0
        assert result.chapter == 1
        assert result.game_over_triggered is False  # default

    def test_decay_result_with_game_over(self):
        """Test DecayResult when game_over is triggered."""
        result = DecayResult(
            user_id=uuid4(),
            decay_amount=Decimal("5.0"),
            score_before=Decimal("3.0"),
            score_after=Decimal("0.0"),
            hours_overdue=10.0,
            chapter=2,
            timestamp=datetime.now(UTC),
            game_over_triggered=True,
        )
        assert result.game_over_triggered is True
        assert result.score_after == Decimal("0.0")

    def test_decay_result_with_decay_reason(self):
        """Test DecayResult with optional decay_reason field."""
        result = DecayResult(
            user_id=uuid4(),
            decay_amount=Decimal("1.6"),
            score_before=Decimal("50.0"),
            score_after=Decimal("48.4"),
            hours_overdue=2.0,
            chapter=1,
            timestamp=datetime.now(UTC),
            decay_reason="inactivity",
        )
        assert result.decay_reason == "inactivity"

    def test_decay_amount_must_be_positive(self):
        """Test that decay_amount must be positive (or zero)."""
        # Zero is valid (no decay)
        result = DecayResult(
            user_id=uuid4(),
            decay_amount=Decimal("0"),
            score_before=Decimal("50.0"),
            score_after=Decimal("50.0"),
            hours_overdue=0.0,
            chapter=1,
            timestamp=datetime.now(UTC),
        )
        assert result.decay_amount == Decimal("0")

        # Negative should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("-5.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("55.0"),
                hours_overdue=2.0,
                chapter=1,
                timestamp=datetime.now(UTC),
            )
        assert "decay_amount" in str(exc_info.value)

    def test_score_after_cannot_exceed_score_before(self):
        """Test score_after should not be greater than score_before."""
        # This is a logical constraint for decay results
        with pytest.raises(ValidationError):
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("5.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("55.0"),  # Invalid: increased after decay
                hours_overdue=2.0,
                chapter=1,
                timestamp=datetime.now(UTC),
            )

    def test_score_after_cannot_be_negative(self):
        """Test score_after must be >= 0 (floor at 0)."""
        with pytest.raises(ValidationError):
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("10.0"),
                score_before=Decimal("5.0"),
                score_after=Decimal("-5.0"),  # Invalid: negative
                hours_overdue=10.0,
                chapter=1,
                timestamp=datetime.now(UTC),
            )

    def test_chapter_bounds(self):
        """Test chapter must be 1-5."""
        # Valid chapters
        for chapter in range(1, 6):
            result = DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("1.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("49.0"),
                hours_overdue=2.0,
                chapter=chapter,
                timestamp=datetime.now(UTC),
            )
            assert result.chapter == chapter

        # Invalid chapter 0
        with pytest.raises(ValidationError):
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("1.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("49.0"),
                hours_overdue=2.0,
                chapter=0,
                timestamp=datetime.now(UTC),
            )

        # Invalid chapter 6
        with pytest.raises(ValidationError):
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("1.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("49.0"),
                hours_overdue=2.0,
                chapter=6,
                timestamp=datetime.now(UTC),
            )

    def test_hours_overdue_non_negative(self):
        """Test hours_overdue must be >= 0."""
        with pytest.raises(ValidationError):
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("1.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("49.0"),
                hours_overdue=-1.0,  # Invalid
                chapter=1,
                timestamp=datetime.now(UTC),
            )

    def test_timestamp_required(self):
        """Test timestamp is a required field."""
        # Missing timestamp should fail
        with pytest.raises(ValidationError):
            DecayResult(
                user_id=uuid4(),
                decay_amount=Decimal("1.0"),
                score_before=Decimal("50.0"),
                score_after=Decimal("49.0"),
                hours_overdue=2.0,
                chapter=1,
                # timestamp missing
            )

    def test_decimal_precision(self):
        """Test that decimal fields support precision."""
        result = DecayResult(
            user_id=uuid4(),
            decay_amount=Decimal("2.4567"),
            score_before=Decimal("65.1234"),
            score_after=Decimal("62.6667"),
            hours_overdue=3.5,
            chapter=1,
            timestamp=datetime.now(UTC),
        )
        assert result.decay_amount == Decimal("2.4567")
        assert result.score_before == Decimal("65.1234")
