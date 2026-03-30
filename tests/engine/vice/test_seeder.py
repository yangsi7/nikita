"""Tests for vice seeder — Spec 104 Story 1.

Maps onboarding darkness_level to initial vice weights.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_seed_vices_low_darkness():
    """Level 1-2: vulnerability + intellectual_dominance at weight 0.4."""
    from nikita.engine.vice.seeder import seed_vices_from_profile

    user_id = uuid4()
    profile = {"darkness_level": 2}

    mock_repo = AsyncMock()
    mock_repo.discover = AsyncMock(return_value=MagicMock())

    result = await seed_vices_from_profile(user_id, profile, mock_repo)

    # Should discover vulnerability and intellectual_dominance
    categories = [call.kwargs.get("category") or call.args[1] for call in mock_repo.discover.call_args_list]
    assert "vulnerability" in categories
    assert "intellectual_dominance" in categories


@pytest.mark.asyncio
async def test_seed_vices_mid_darkness():
    """Level 3: moderate spread across multiple categories."""
    from nikita.engine.vice.seeder import seed_vices_from_profile

    user_id = uuid4()
    profile = {"darkness_level": 3}

    mock_repo = AsyncMock()
    mock_repo.discover = AsyncMock(return_value=MagicMock())

    result = await seed_vices_from_profile(user_id, profile, mock_repo)

    # Should discover at least 3 categories for moderate spread
    assert mock_repo.discover.call_count >= 3


@pytest.mark.asyncio
async def test_seed_vices_high_darkness():
    """Level 4-5: dark_humor + emotional_intensity at weight 0.6."""
    from nikita.engine.vice.seeder import seed_vices_from_profile

    user_id = uuid4()
    profile = {"darkness_level": 4}

    mock_repo = AsyncMock()
    mock_repo.discover = AsyncMock(return_value=MagicMock())

    result = await seed_vices_from_profile(user_id, profile, mock_repo)

    categories = [call.kwargs.get("category") or call.args[1] for call in mock_repo.discover.call_args_list]
    assert "dark_humor" in categories
    assert "emotional_intensity" in categories


@pytest.mark.asyncio
async def test_seed_vices_missing_profile_graceful():
    """Missing or empty profile returns empty list without error."""
    from nikita.engine.vice.seeder import seed_vices_from_profile

    user_id = uuid4()
    mock_repo = AsyncMock()

    # None profile
    result = await seed_vices_from_profile(user_id, None, mock_repo)
    assert result == []

    # Empty dict
    result = await seed_vices_from_profile(user_id, {}, mock_repo)
    assert result == []

    # No discover calls
    mock_repo.discover.assert_not_called()


# ---------------------------------------------------------------------------
# Intensity cap tests (GH #193) — all tiers must seed at intensity 1
# ---------------------------------------------------------------------------

class TestSeederIntensityCap:
    """All vice tiers must seed at initial_intensity=1 (discovery level)."""

    @pytest.mark.asyncio
    async def test_high_tier_seeds_at_intensity_1(self):
        """Level 4-5 (TIER_HIGH): every discover() call uses initial_intensity=1."""
        from nikita.engine.vice.seeder import seed_vices_from_profile

        user_id = uuid4()
        profile = {"darkness_level": 4}

        mock_repo = AsyncMock()
        mock_repo.discover = AsyncMock(return_value=MagicMock())

        await seed_vices_from_profile(user_id, profile, mock_repo)

        for call in mock_repo.discover.call_args_list:
            assert call.kwargs.get("initial_intensity") == 1, (
                f"Expected initial_intensity=1, got {call.kwargs.get('initial_intensity')} "
                f"for category={call.kwargs.get('category')}"
            )

    @pytest.mark.asyncio
    async def test_mid_tier_seeds_at_intensity_1(self):
        """Level 3 (TIER_MID): every discover() call uses initial_intensity=1."""
        from nikita.engine.vice.seeder import seed_vices_from_profile

        user_id = uuid4()
        profile = {"darkness_level": 3}

        mock_repo = AsyncMock()
        mock_repo.discover = AsyncMock(return_value=MagicMock())

        await seed_vices_from_profile(user_id, profile, mock_repo)

        for call in mock_repo.discover.call_args_list:
            assert call.kwargs.get("initial_intensity") == 1, (
                f"Expected initial_intensity=1, got {call.kwargs.get('initial_intensity')} "
                f"for category={call.kwargs.get('category')}"
            )

    @pytest.mark.asyncio
    async def test_low_tier_seeds_at_intensity_1(self):
        """Level 1-2 (TIER_LOW): every discover() call uses initial_intensity=1."""
        from nikita.engine.vice.seeder import seed_vices_from_profile

        user_id = uuid4()
        profile = {"darkness_level": 2}

        mock_repo = AsyncMock()
        mock_repo.discover = AsyncMock(return_value=MagicMock())

        await seed_vices_from_profile(user_id, profile, mock_repo)

        for call in mock_repo.discover.call_args_list:
            assert call.kwargs.get("initial_intensity") == 1, (
                f"Expected initial_intensity=1, got {call.kwargs.get('initial_intensity')} "
                f"for category={call.kwargs.get('category')}"
            )
