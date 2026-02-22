"""Integration tests for Group A feature flags (Spec 066 T1).

Verifies that skip_rates_enabled and life_sim_enhanced flags activate
their gated behavior paths when turned ON.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4


class TestSkipRatesFlagEnabled:
    """Tests for skip_rates_enabled=True flag behavior."""

    def test_skip_flag_off_always_returns_false(self):
        """With skip_rates_enabled=False, SkipDecision.should_skip always returns False."""
        from nikita.agents.text.skip import SkipDecision

        mock_settings = MagicMock()
        mock_settings.skip_rates_enabled = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            decision = SkipDecision()
            results = [decision.should_skip(chapter=1) for _ in range(100)]
            assert all(r is False for r in results), "With flag OFF, should never skip"

    def test_skip_flag_on_can_return_true(self):
        """With skip_rates_enabled=True, SkipDecision.should_skip can return True.

        Chapter 1 has 25-40% skip rate, so running 200 times statistically
        guarantees at least one skip.
        """
        from nikita.agents.text.skip import SkipDecision

        mock_settings = MagicMock()
        mock_settings.skip_rates_enabled = True

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            decision = SkipDecision()
            results = [decision.should_skip(chapter=1) for _ in range(200)]
            # With 25-40% skip rate, 200 samples should have many True values
            assert any(r is True for r in results), (
                "With flag ON (ch1 has 25-40% skip rate), at least one skip expected in 200 tries"
            )

    def test_skip_rates_not_zero_when_flag_on(self):
        """With skip_rates_enabled=True, the active rates table has non-zero values."""
        from nikita.agents.text.skip import SKIP_RATES

        # Verify the SKIP_RATES table (used when flag ON) has non-zero entries
        for chapter in [1, 2, 3]:
            min_rate, max_rate = SKIP_RATES[chapter]
            assert max_rate > 0, (
                f"Chapter {chapter} max skip rate should be >0 when flag is ON"
            )

    def test_skip_flag_on_chapter_5_low_rates(self):
        """With skip_rates_enabled=True, chapter 5 has very low skip rates (0-5%)."""
        from nikita.agents.text.skip import SKIP_RATES

        min_rate, max_rate = SKIP_RATES[5]
        assert min_rate == 0.0
        assert max_rate == 0.05


class TestLifeSimEnhancedFlagEnabled:
    """Tests for life_sim_enhanced=True flag behavior."""

    def test_is_enhanced_returns_true_when_flag_on(self):
        """_is_enhanced() returns True when life_sim_enhanced=True."""
        from nikita.life_simulation.simulator import LifeSimulator

        mock_store = MagicMock()
        mock_entity_manager = MagicMock()
        mock_event_generator = MagicMock()
        mock_narrative_manager = MagicMock()
        mock_mood_calculator = MagicMock()

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
            mood_calculator=mock_mood_calculator,
        )

        mock_settings = MagicMock()
        mock_settings.life_sim_enhanced = True

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert simulator._is_enhanced() is True

    def test_is_enhanced_returns_false_when_flag_off(self):
        """_is_enhanced() returns False when life_sim_enhanced=False."""
        from nikita.life_simulation.simulator import LifeSimulator

        mock_store = MagicMock()
        mock_entity_manager = MagicMock()
        mock_event_generator = MagicMock()
        mock_narrative_manager = MagicMock()
        mock_mood_calculator = MagicMock()

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
            mood_calculator=mock_mood_calculator,
        )

        mock_settings = MagicMock()
        mock_settings.life_sim_enhanced = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert simulator._is_enhanced() is False

    @pytest.mark.asyncio
    async def test_generate_events_calls_mood_when_enhanced(self):
        """With life_sim_enhanced=True, generate_next_day_events calls get_current_mood."""
        from nikita.life_simulation.simulator import LifeSimulator
        from datetime import date

        user_id = uuid4()

        mock_store = MagicMock()
        mock_store.get_events_for_date = AsyncMock(return_value=[])
        mock_store.get_entities = AsyncMock(return_value=[MagicMock()])
        mock_store.get_recent_events = AsyncMock(return_value=[])
        mock_store.save_events = AsyncMock()
        mock_store.update_npc_state = AsyncMock()

        mock_entity_manager = MagicMock()
        mock_entity_manager.seed_entities = AsyncMock(return_value=[])

        mock_event_generator = MagicMock()
        mock_event_generator.generate_events_for_day = AsyncMock(return_value=[])

        mock_narrative_manager = MagicMock()
        mock_narrative_manager.get_active_arcs = AsyncMock(return_value=[])
        mock_narrative_manager.maybe_resolve_arcs = AsyncMock(return_value=[])
        mock_narrative_manager.maybe_create_arc = AsyncMock(return_value=None)

        mock_mood_calculator = MagicMock()
        mock_mood = MagicMock()
        mock_mood.valence = 0.5

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
            mood_calculator=mock_mood_calculator,
        )

        mock_settings = MagicMock()
        mock_settings.life_sim_enhanced = True

        # Patch get_settings and also get_current_mood to track the call
        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            with patch.object(
                simulator,
                "get_current_mood",
                AsyncMock(return_value=mock_mood),
            ) as mock_get_mood:
                await simulator.generate_next_day_events(
                    user_id=user_id,
                    target_date=date.today(),
                )
                mock_get_mood.assert_called_once_with(user_id, lookback_days=3)

    @pytest.mark.asyncio
    async def test_generate_events_skips_mood_when_not_enhanced(self):
        """With life_sim_enhanced=False, generate_next_day_events skips get_current_mood."""
        from nikita.life_simulation.simulator import LifeSimulator
        from datetime import date

        user_id = uuid4()

        mock_store = MagicMock()
        mock_store.get_events_for_date = AsyncMock(return_value=[])
        mock_store.get_entities = AsyncMock(return_value=[MagicMock()])
        mock_store.get_recent_events = AsyncMock(return_value=[])
        mock_store.save_events = AsyncMock()

        mock_entity_manager = MagicMock()
        mock_entity_manager.seed_entities = AsyncMock(return_value=[])

        mock_event_generator = MagicMock()
        mock_event_generator.generate_events_for_day = AsyncMock(return_value=[])

        mock_narrative_manager = MagicMock()
        mock_narrative_manager.get_active_arcs = AsyncMock(return_value=[])
        mock_narrative_manager.maybe_resolve_arcs = AsyncMock(return_value=[])
        mock_narrative_manager.maybe_create_arc = AsyncMock(return_value=None)

        mock_mood_calculator = MagicMock()

        simulator = LifeSimulator(
            store=mock_store,
            entity_manager=mock_entity_manager,
            event_generator=mock_event_generator,
            narrative_manager=mock_narrative_manager,
            mood_calculator=mock_mood_calculator,
        )

        mock_settings = MagicMock()
        mock_settings.life_sim_enhanced = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            with patch.object(
                simulator,
                "get_current_mood",
                AsyncMock(return_value=MagicMock()),
            ) as mock_get_mood:
                await simulator.generate_next_day_events(
                    user_id=user_id,
                    target_date=date.today(),
                )
                mock_get_mood.assert_not_called()
