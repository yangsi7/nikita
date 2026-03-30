"""Tests for OnboardingHandler vice seeding delegation to seeder.py.

GH #203: Telegram text onboarding was using an inline vice_mappings dict
that bypassed engine/vice/seeder.py. This test ensures the handler delegates
to seeder.py (single source of truth) with all intensities capped to 1.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.platforms.telegram.onboarding.handler import OnboardingHandler


@pytest.fixture
def mock_bot():
    """Minimal mock bot for OnboardingHandler construction."""
    return MagicMock()


@pytest.fixture
def mock_onboarding_repo():
    return AsyncMock()


@pytest.fixture
def mock_profile_repo():
    return AsyncMock()


@pytest.fixture
def mock_vice_repo():
    repo = AsyncMock()
    repo.discover = AsyncMock(return_value=MagicMock())
    return repo


@pytest.fixture
def handler_with_vice_repo(mock_bot, mock_onboarding_repo, mock_profile_repo, mock_vice_repo):
    """OnboardingHandler with a vice_repo injected."""
    return OnboardingHandler(
        bot=mock_bot,
        onboarding_repository=mock_onboarding_repo,
        profile_repository=mock_profile_repo,
        vice_repository=mock_vice_repo,
    )


@pytest.fixture
def handler_without_vice_repo(mock_bot, mock_onboarding_repo, mock_profile_repo):
    """OnboardingHandler with vice_repo=None."""
    return OnboardingHandler(
        bot=mock_bot,
        onboarding_repository=mock_onboarding_repo,
        profile_repository=mock_profile_repo,
        vice_repository=None,
    )


class TestHandlerViceSeeding:
    """AC-1 through AC-4 for GH #203."""

    @pytest.mark.asyncio
    async def test_handler_delegates_to_seeder(self, handler_with_vice_repo, mock_vice_repo):
        """AC-1: _initialize_vices_from_profile delegates to seed_vices_from_profile."""
        user_id = uuid4()
        with patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile"
        ) as mock_seed:
            mock_seed.return_value = []
            await handler_with_vice_repo._initialize_vices_from_profile(
                user_id=user_id,
                drug_tolerance=4,
            )
            mock_seed.assert_awaited_once_with(
                user_id=user_id,
                profile={"darkness_level": 4},
                vice_repo=mock_vice_repo,
            )

    @pytest.mark.asyncio
    async def test_all_intensities_capped_to_1(self, handler_with_vice_repo, mock_vice_repo):
        """AC-2: All vice_repo.discover() calls use initial_intensity=1."""
        await handler_with_vice_repo._initialize_vices_from_profile(
            user_id=uuid4(),
            drug_tolerance=5,  # Highest tolerance — should still seed at 1
        )
        assert mock_vice_repo.discover.await_count > 0, "No vices were seeded"
        for call in mock_vice_repo.discover.call_args_list:
            intensity = call.kwargs.get("initial_intensity")
            category = call.kwargs.get("category", "unknown")
            assert intensity == 1, (
                f"Category '{category}' seeded at intensity {intensity}, expected 1"
            )

    @pytest.mark.asyncio
    async def test_no_vice_repo_skips_gracefully(self, handler_without_vice_repo):
        """AC-3: When vice_repo is None, no error and no seeder call."""
        with patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile"
        ) as mock_seed:
            # Should not raise
            await handler_without_vice_repo._initialize_vices_from_profile(
                user_id=uuid4(),
                drug_tolerance=4,
            )
            mock_seed.assert_not_called()

    @pytest.mark.asyncio
    async def test_categories_match_seeder_tier(self, handler_with_vice_repo, mock_vice_repo):
        """AC-4: drug_tolerance=4 seeds TIER_HIGH categories (5), not all 8."""
        await handler_with_vice_repo._initialize_vices_from_profile(
            user_id=uuid4(),
            drug_tolerance=4,  # Maps to TIER_HIGH
        )
        seeded_categories = {
            call.kwargs["category"] for call in mock_vice_repo.discover.call_args_list
        }
        # TIER_HIGH has exactly these 5 categories
        expected = {
            "dark_humor",
            "emotional_intensity",
            "risk_taking",
            "sexuality",
            "vulnerability",
        }
        assert seeded_categories == expected, (
            f"Expected TIER_HIGH categories {expected}, got {seeded_categories}"
        )
        # substances and rule_breaking must NOT be seeded (discovered via ViceStage)
        assert "substances" not in seeded_categories
        assert "rule_breaking" not in seeded_categories

    @pytest.mark.asyncio
    async def test_out_of_range_drug_tolerance_seeds_nothing(
        self, handler_with_vice_repo, mock_vice_repo
    ):
        """Boundary: drug_tolerance outside 1-5 should seed zero vices."""
        for invalid_value in (0, 6, -1, 99):
            mock_vice_repo.discover.reset_mock()
            await handler_with_vice_repo._initialize_vices_from_profile(
                user_id=uuid4(),
                drug_tolerance=invalid_value,
            )
            assert mock_vice_repo.discover.await_count == 0, (
                f"drug_tolerance={invalid_value} should seed 0 vices, "
                f"got {mock_vice_repo.discover.await_count}"
            )
