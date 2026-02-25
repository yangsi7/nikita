"""Integration tests for Group C feature flags (Spec 066 T3).

Verifies that conflict_temperature_enabled and multi_phase_boss_enabled flags
activate their gated behavior paths when turned ON.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestConflictTemperatureFlagEnabled:
    """Tests for conflict_temperature_enabled=True flag behavior."""

    def test_is_conflict_temperature_enabled_returns_true_when_flag_on(self):
        """is_conflict_temperature_enabled() returns True when flag is ON."""
        from nikita.conflicts import is_conflict_temperature_enabled

        mock_settings = MagicMock()
        mock_settings.conflict_temperature_enabled = True

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_conflict_temperature_enabled() is True

    def test_is_conflict_temperature_enabled_returns_false_when_flag_off(self):
        """is_conflict_temperature_enabled() returns False when flag is OFF."""
        from nikita.conflicts import is_conflict_temperature_enabled

        mock_settings = MagicMock()
        mock_settings.conflict_temperature_enabled = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_conflict_temperature_enabled() is False

    def test_temperature_engine_zone_calm_below_25(self):
        """TemperatureEngine.get_zone() returns CALM for temperature < 25."""
        from nikita.conflicts.temperature import TemperatureEngine
        from nikita.conflicts.models import TemperatureZone

        zone = TemperatureEngine.get_zone(10.0)
        assert zone == TemperatureZone.CALM

    def test_temperature_engine_zone_hot_between_50_and_75(self):
        """TemperatureEngine.get_zone() returns HOT for temperature 50-75."""
        from nikita.conflicts.temperature import TemperatureEngine
        from nikita.conflicts.models import TemperatureZone

        zone = TemperatureEngine.get_zone(60.0)
        assert zone == TemperatureZone.HOT

    def test_temperature_engine_zone_critical_above_75(self):
        """TemperatureEngine.get_zone() returns CRITICAL for temperature > 75."""
        from nikita.conflicts.temperature import TemperatureEngine
        from nikita.conflicts.models import TemperatureZone

        zone = TemperatureEngine.get_zone(80.0)
        assert zone == TemperatureZone.CRITICAL

    def test_temperature_engine_increase_clamps_at_100(self):
        """TemperatureEngine.increase() clamps result at 100."""
        from nikita.conflicts.temperature import TemperatureEngine

        result = TemperatureEngine.increase(current=95.0, delta=20.0)
        assert result <= 100.0

    def test_temperature_engine_decrease_clamps_at_0(self):
        """TemperatureEngine.decrease() clamps result at 0."""
        from nikita.conflicts.temperature import TemperatureEngine

        result = TemperatureEngine.decrease(current=5.0, delta=20.0)
        assert result >= 0.0

    def test_temperature_engine_time_decay_reduces_temperature(self):
        """TemperatureEngine.apply_time_decay() reduces temperature over time."""
        from nikita.conflicts.temperature import TemperatureEngine

        initial = 60.0
        # After 10 hours of decay
        decayed = TemperatureEngine.apply_time_decay(current=initial, hours_elapsed=10.0)
        assert decayed < initial

    @pytest.mark.asyncio
    async def test_conflict_stage_uses_temperature_mode_when_flag_on(self):
        """ConflictStage._run() uses temperature mode when flag is ON."""
        from nikita.pipeline.stages.conflict import ConflictStage
        from uuid import uuid4
        from datetime import datetime, timezone
        from nikita.pipeline.models import PipelineContext

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        ctx.emotional_state = {"arousal": 0.5, "valence": 0.2, "dominance": 0.5, "intimacy": 0.5}

        stage = ConflictStage(session=MagicMock())

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await stage._run(ctx)

        # Temperature mode returns temperature and zone fields
        assert "temperature" in result
        assert "zone" in result
        # Default temperature is 0 (CALM zone), so active=False
        assert result["active"] is False

    @pytest.mark.asyncio
    async def test_conflict_stage_active_when_temperature_hot(self):
        """ConflictStage with temperature=60 (HOT zone) sets active=True."""
        from nikita.pipeline.stages.conflict import ConflictStage
        from nikita.conflicts.models import ConflictDetails
        from uuid import uuid4
        from datetime import datetime, timezone
        from nikita.pipeline.models import PipelineContext

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
        )
        # Set conflict_details with a HOT temperature
        hot_details = ConflictDetails(temperature=60.0)
        ctx.conflict_details = hot_details.to_jsonb()

        stage = ConflictStage(session=MagicMock())

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=True):
            result = await stage._run(ctx)

        assert result["active"] is True
        assert result["zone"] == "hot"


class TestMultiPhaseBossFlagEnabled:
    """Tests for multi_phase_boss_enabled=True flag behavior."""

    def test_is_multi_phase_boss_enabled_returns_true_when_flag_on(self):
        """is_multi_phase_boss_enabled() returns True when flag is ON."""
        from nikita.engine.chapters import is_multi_phase_boss_enabled

        mock_settings = MagicMock()
        mock_settings.multi_phase_boss_enabled = True

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_multi_phase_boss_enabled() is True

    def test_is_multi_phase_boss_enabled_returns_false_when_flag_off(self):
        """is_multi_phase_boss_enabled() returns False when flag is OFF."""
        from nikita.engine.chapters import is_multi_phase_boss_enabled

        mock_settings = MagicMock()
        mock_settings.multi_phase_boss_enabled = False

        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_multi_phase_boss_enabled() is False

    def test_boss_phase_manager_start_boss_returns_opening_phase(self):
        """BossPhaseManager.start_boss() creates an OPENING phase state."""
        from nikita.engine.chapters.phase_manager import BossPhaseManager
        from nikita.engine.chapters.boss import BossPhase

        manager = BossPhaseManager()
        state = manager.start_boss(chapter=1)

        assert state.phase == BossPhase.OPENING
        assert state.chapter == 1
        assert state.turn_count == 0
        assert state.conversation_history == []

    def test_boss_phase_manager_advance_transitions_to_resolution(self):
        """BossPhaseManager.advance_phase() transitions OPENING -> RESOLUTION."""
        from nikita.engine.chapters.phase_manager import BossPhaseManager
        from nikita.engine.chapters.boss import BossPhase

        manager = BossPhaseManager()
        opening_state = manager.start_boss(chapter=2)

        resolution_state = manager.advance_phase(
            state=opening_state,
            user_message="I'm sorry I was late.",
            nikita_response="I appreciate you saying that.",
        )

        assert resolution_state.phase == BossPhase.RESOLUTION
        assert len(resolution_state.conversation_history) == 2
        assert resolution_state.conversation_history[0]["role"] == "user"
        assert resolution_state.conversation_history[1]["role"] == "assistant"

    def test_boss_phase_manager_persist_and_load_roundtrip(self):
        """BossPhaseManager.persist_phase() and load_phase() are inverse operations."""
        from nikita.engine.chapters.phase_manager import BossPhaseManager
        from nikita.engine.chapters.boss import BossPhase

        manager = BossPhaseManager()
        state = manager.start_boss(chapter=3)

        # Persist to a dict — static method signature: (conflict_details, state)
        conflict_details: dict = {}
        conflict_details = BossPhaseManager.persist_phase(conflict_details, state)

        # Load back
        loaded_state = BossPhaseManager.load_phase(conflict_details)

        assert loaded_state is not None
        assert loaded_state.phase == BossPhase.OPENING
        assert loaded_state.chapter == 3

    def test_boss_phase_manager_load_returns_none_for_empty_dict(self):
        """BossPhaseManager.load_phase() returns None for empty conflict_details."""
        from nikita.engine.chapters.phase_manager import BossPhaseManager

        manager = BossPhaseManager()
        result = manager.load_phase({})
        assert result is None
