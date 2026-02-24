"""Tests for Spec 106 I13: Chapter-adaptive vice discovery sensitivity.

Higher chapters should be LESS sensitive (vices already established),
lower chapters MORE sensitive (discovery mode).
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.engine.vice.scorer import (
    CHAPTER_SENSITIVITY_MULTIPLIERS,
    ViceScorer,
)


class TestChapterSensitivityMultipliers:
    """Test CHAPTER_SENSITIVITY_MULTIPLIERS constants."""

    def test_ch1_higher_sensitivity(self):
        """Ch1 multiplier > Ch3 baseline (new relationship = heightened discovery)."""
        assert CHAPTER_SENSITIVITY_MULTIPLIERS[1] > CHAPTER_SENSITIVITY_MULTIPLIERS[3]
        assert CHAPTER_SENSITIVITY_MULTIPLIERS[1] == Decimal("1.5")

    def test_ch5_lower_sensitivity(self):
        """Ch5 multiplier < Ch3 baseline (mature = vices well-known)."""
        assert CHAPTER_SENSITIVITY_MULTIPLIERS[5] < CHAPTER_SENSITIVITY_MULTIPLIERS[3]
        assert CHAPTER_SENSITIVITY_MULTIPLIERS[5] == Decimal("0.5")

    def test_default_chapter_baseline(self):
        """Ch3 multiplier is exactly 1.0 (no change)."""
        assert CHAPTER_SENSITIVITY_MULTIPLIERS[3] == Decimal("1.0")

    def test_unknown_chapter_defaults_to_1(self):
        """Chapter 99 (not in dict) should default to 1.0 via .get()."""
        assert CHAPTER_SENSITIVITY_MULTIPLIERS.get(99, Decimal("1.0")) == Decimal("1.0")


class TestChapterSensitivityInProcessSignals:
    """Test that process_signals applies chapter multiplier to deltas."""

    @pytest.mark.asyncio
    async def test_ch1_produces_larger_delta(self):
        """Ch1 signal produces larger engagement delta than Ch3."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        signal = ViceSignal(
            category=ViceCategory.DARK_HUMOR,
            confidence=Decimal("0.8"),
            is_positive=True,
            evidence="test",
        )

        # Mock the repo
        mock_pref = MagicMock()
        mock_pref.id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.get_by_category.return_value = mock_pref
        mock_repo.update_engagement = AsyncMock()

        with patch.object(scorer, "_get_vice_repo", return_value=mock_repo):
            scorer._session = AsyncMock()

            # Ch1 — higher sensitivity
            await scorer.process_signals(user_id, [signal], chapter=1)
            ch1_call = mock_repo.update_engagement.call_args_list[-1]
            ch1_delta = ch1_call[0][1]

            mock_repo.update_engagement.reset_mock()

            # Ch3 — baseline
            await scorer.process_signals(user_id, [signal], chapter=3)
            ch3_call = mock_repo.update_engagement.call_args_list[-1]
            ch3_delta = ch3_call[0][1]

        assert ch1_delta > ch3_delta

    @pytest.mark.asyncio
    async def test_ch5_produces_smaller_delta(self):
        """Ch5 signal produces smaller engagement delta than Ch3."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        signal = ViceSignal(
            category=ViceCategory.DARK_HUMOR,
            confidence=Decimal("0.8"),
            is_positive=True,
            evidence="test",
        )

        mock_pref = MagicMock()
        mock_pref.id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.get_by_category.return_value = mock_pref
        mock_repo.update_engagement = AsyncMock()

        with patch.object(scorer, "_get_vice_repo", return_value=mock_repo):
            scorer._session = AsyncMock()

            # Ch5 — lower sensitivity
            await scorer.process_signals(user_id, [signal], chapter=5)
            ch5_call = mock_repo.update_engagement.call_args_list[-1]
            ch5_delta = ch5_call[0][1]

            mock_repo.update_engagement.reset_mock()

            # Ch3 — baseline
            await scorer.process_signals(user_id, [signal], chapter=3)
            ch3_call = mock_repo.update_engagement.call_args_list[-1]
            ch3_delta = ch3_call[0][1]

        assert ch5_delta < ch3_delta
