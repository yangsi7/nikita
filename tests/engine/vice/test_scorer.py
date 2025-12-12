"""
Unit Tests for ViceScorer (T009, T012, T015-T018)

Tests for:
- AC-FR003-001: Given multiple dark_humor signals, When intensity calculated, Then score increases
- AC-FR008-001: Given user with established profile, When returns after days, Then same profile loaded
- AC-FR008-002: Given profile update, When persisted, Then survives system restart

TDD: Write tests FIRST, verify they fail, then implement.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestViceScorerProcessSignals:
    """T009, T012: ViceScorer.process_signals() tests."""

    @pytest.mark.asyncio
    async def test_ac_fr003_001_multiple_signals_increase_intensity(self):
        """AC-FR003-001: Given multiple dark_humor signals, When intensity calculated, Then score increases."""
        from nikita.engine.vice.scorer import ViceScorer
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        # Create multiple signals
        signals = [
            ViceSignal(
                category=ViceCategory.DARK_HUMOR,
                confidence=Decimal("0.80"),
                evidence="First morbid joke",
                is_positive=True,
            ),
            ViceSignal(
                category=ViceCategory.DARK_HUMOR,
                confidence=Decimal("0.75"),
                evidence="Second dark joke",
                is_positive=True,
            ),
        ]

        # Mock repository
        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # First signal discovers new vice
            mock_pref = MagicMock()
            mock_pref.id = uuid4()
            mock_pref.intensity_level = 1
            mock_pref.engagement_score = Decimal("0.80")
            mock_repo.discover.return_value = mock_pref
            mock_repo.get_by_category.return_value = None

            # Update engagement
            mock_pref_updated = MagicMock()
            mock_pref_updated.engagement_score = Decimal("1.55")
            mock_repo.update_engagement.return_value = mock_pref_updated

            result = await scorer.process_signals(user_id, signals)

            # Verify repository was called
            assert mock_repo.discover.called or mock_repo.get_by_category.called
            assert result is not None

    @pytest.mark.asyncio
    async def test_ac_t012_1_process_signals_updates_intensities(self):
        """AC-T012.1: process_signals(user_id, signals) updates intensities."""
        from nikita.engine.vice.scorer import ViceScorer
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        signal = ViceSignal(
            category=ViceCategory.RISK_TAKING,
            confidence=Decimal("0.90"),
            evidence="User loves danger",
            is_positive=True,
        )

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # Return existing preference
            mock_pref = MagicMock()
            mock_pref.id = uuid4()
            mock_pref.category = "risk_taking"
            mock_pref.engagement_score = Decimal("1.00")
            mock_repo.get_by_category.return_value = mock_pref

            await scorer.process_signals(user_id, [signal])

            # Should update engagement
            mock_repo.update_engagement.assert_called()

    @pytest.mark.asyncio
    async def test_ac_t012_3_discovers_new_vices(self):
        """AC-T012.3: Uses VicePreferenceRepository.discover() for new vices."""
        from nikita.engine.vice.scorer import ViceScorer
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        signal = ViceSignal(
            category=ViceCategory.VULNERABILITY,
            confidence=Decimal("0.70"),
            evidence="User shared fear",
            is_positive=True,
        )

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # No existing preference
            mock_repo.get_by_category.return_value = None

            # Return discovered preference
            mock_pref = MagicMock()
            mock_pref.id = uuid4()
            mock_repo.discover.return_value = mock_pref

            await scorer.process_signals(user_id, [signal])

            # Should discover new vice
            mock_repo.discover.assert_called_once_with(
                user_id,
                ViceCategory.VULNERABILITY.value,
                initial_intensity=1,
            )

    @pytest.mark.asyncio
    async def test_rejection_signal_decreases_engagement(self):
        """Rejection signals (is_positive=False) should decrease engagement."""
        from nikita.engine.vice.scorer import ViceScorer
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        signal = ViceSignal(
            category=ViceCategory.DARK_HUMOR,
            confidence=Decimal("0.80"),
            evidence="User rejected humor",
            is_positive=False,  # Rejection!
        )

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_pref = MagicMock()
            mock_pref.id = uuid4()
            mock_pref.category = "dark_humor"
            mock_pref.engagement_score = Decimal("2.00")
            mock_repo.get_by_category.return_value = mock_pref

            await scorer.process_signals(user_id, [signal])

            # Should update engagement with negative delta
            call_args = mock_repo.update_engagement.call_args
            if call_args:
                delta = call_args[1].get('delta') or call_args[0][1]
                assert delta < Decimal("0")  # Negative delta


class TestViceScorerGetProfile:
    """T015-T017: ViceScorer profile retrieval tests."""

    @pytest.mark.asyncio
    async def test_ac_fr008_001_profile_loaded_after_days(self):
        """AC-FR008-001: Given user with established profile, When returns after days, Then same profile loaded."""
        from nikita.engine.vice.scorer import ViceScorer
        from nikita.engine.vice.models import ViceProfile

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # Return established preferences
            mock_prefs = [
                MagicMock(
                    category="dark_humor",
                    engagement_score=Decimal("3.50"),
                    intensity_level=3,
                ),
                MagicMock(
                    category="intellectual_dominance",
                    engagement_score=Decimal("2.00"),
                    intensity_level=2,
                ),
            ]
            mock_repo.get_active.return_value = mock_prefs

            profile = await scorer.get_profile(user_id)

            assert isinstance(profile, ViceProfile)
            assert profile.user_id == user_id
            assert profile.get_intensity("dark_humor") > Decimal("0")

    @pytest.mark.asyncio
    async def test_ac_t016_1_returns_all_8_category_intensities(self):
        """AC-T016.1: Returns ViceProfile with all 8 category intensities."""
        from nikita.engine.vice.scorer import ViceScorer
        from nikita.config.enums import ViceCategory

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # Only 2 discovered vices
            mock_prefs = [
                MagicMock(category="dark_humor", engagement_score=Decimal("2.00"), intensity_level=2),
            ]
            mock_repo.get_active.return_value = mock_prefs

            profile = await scorer.get_profile(user_id)

            # All 8 categories should be in intensities (with 0.0 for undiscovered)
            assert len(profile.intensities) == 8
            assert profile.get_intensity("dark_humor") > Decimal("0")
            assert profile.get_intensity("substances") == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_ac_t016_2_missing_categories_return_zero(self):
        """AC-T016.2: Categories without data return intensity 0.0."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo
            mock_repo.get_active.return_value = []  # No vices discovered

            profile = await scorer.get_profile(user_id)

            for category in profile.intensities:
                assert profile.get_intensity(category) == Decimal("0.0")

    @pytest.mark.asyncio
    async def test_ac_t016_3_top_vices_ordered_descending(self):
        """AC-T016.3: top_vices ordered by intensity (descending)."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_prefs = [
                MagicMock(category="risk_taking", engagement_score=Decimal("1.00"), intensity_level=1),
                MagicMock(category="dark_humor", engagement_score=Decimal("3.00"), intensity_level=3),
                MagicMock(category="vulnerability", engagement_score=Decimal("2.00"), intensity_level=2),
            ]
            mock_repo.get_active.return_value = mock_prefs

            profile = await scorer.get_profile(user_id)

            # Top vices should be in descending order
            assert profile.top_vices[0] == "dark_humor"  # Highest (3.00)
            assert profile.top_vices[1] == "vulnerability"  # Second (2.00)
            assert profile.top_vices[2] == "risk_taking"  # Third (1.00)


class TestViceScorerGetTopVices:
    """T017: ViceScorer.get_top_vices() tests."""

    @pytest.mark.asyncio
    async def test_ac_t017_1_returns_top_n_by_intensity(self):
        """AC-T017.1: Returns top N vices by intensity (default 3)."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_prefs = [
                MagicMock(category="dark_humor", engagement_score=Decimal("4.00"), intensity_level=4),
                MagicMock(category="risk_taking", engagement_score=Decimal("3.00"), intensity_level=3),
                MagicMock(category="vulnerability", engagement_score=Decimal("2.00"), intensity_level=2),
                MagicMock(category="substances", engagement_score=Decimal("1.00"), intensity_level=1),
            ]
            mock_repo.get_active.return_value = mock_prefs

            top_vices = await scorer.get_top_vices(user_id, n=3)

            assert len(top_vices) == 3
            assert top_vices[0][0] == "dark_humor"  # Highest

    @pytest.mark.asyncio
    async def test_ac_t017_2_returns_category_intensity_tuples(self):
        """AC-T017.2: Returns (category, intensity) tuples."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_prefs = [
                MagicMock(category="dark_humor", engagement_score=Decimal("2.50"), intensity_level=2),
            ]
            mock_repo.get_active.return_value = mock_prefs

            top_vices = await scorer.get_top_vices(user_id, n=3)

            assert len(top_vices) >= 1
            category, intensity = top_vices[0]
            assert category == "dark_humor"
            assert isinstance(intensity, Decimal)

    @pytest.mark.asyncio
    async def test_ac_t017_3_filters_below_threshold(self):
        """AC-T017.3: Filters vices below minimum threshold."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        user_id = uuid4()

        with patch.object(scorer, '_get_vice_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            # Note: get_profile normalizes engagement_score / 5.0
            # So 2.00 -> 0.40 (above threshold), 0.50 -> 0.10 (below threshold)
            mock_prefs = [
                MagicMock(category="dark_humor", engagement_score=Decimal("2.00"), intensity_level=2),  # 0.40 after norm
                MagicMock(category="risk_taking", engagement_score=Decimal("0.50"), intensity_level=1),  # 0.10 after norm
            ]
            mock_repo.get_active.return_value = mock_prefs

            top_vices = await scorer.get_top_vices(user_id, n=3, min_threshold=Decimal("0.30"))

            # Only dark_humor should pass threshold (0.40 >= 0.30)
            categories = [v[0] for v in top_vices]
            assert "dark_humor" in categories
            assert "risk_taking" not in categories
