"""Integration tests for the life_sim_enhanced feature flag (Spec 066 T1).

Verifies that life_sim_enhanced activates its gated behavior paths when
turned ON. The skip_rates_enabled flag and its tests were removed in
PR #497 (kill skip rates) along with the underlying skip module.
"""

import pytest
from tests.integration import conftest as _conftest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _conftest._SUPABASE_REACHABLE, reason=_conftest._SKIP_REASON),
]

from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4


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
