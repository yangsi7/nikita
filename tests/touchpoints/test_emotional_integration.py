"""Tests for Emotional State and Conflict Integration in TouchpointEngine.

Spec 041 T2.9: Emotional State Integration
Spec 041 T2.10: Conflict System Integration

Tests the integration between TouchpointEngine and:
- Emotional State Engine (Spec 023)
- Conflict System (Spec 027)
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.emotional_state.models import ConflictState, EmotionalStateModel
from nikita.touchpoints.engine import TouchpointEngine


class TestEmotionalStateIntegration:
    """Tests for T2.9: Emotional State Integration."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def engine(self, mock_session):
        """Create TouchpointEngine with mock session."""
        # Mock the MessageGenerator to avoid Pydantic AI API key requirement
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-for-test"}):
            with patch("nikita.touchpoints.engine.MessageGenerator"):
                return TouchpointEngine(mock_session)

    @pytest.mark.asyncio
    async def test_load_emotional_state_returns_state_from_store(self, engine):
        """_load_emotional_state should return state from StateStore."""
        user_id = uuid4()

        # Create a mock emotional state
        mock_state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.7,
            valence=0.8,
            dominance=0.6,
            intimacy=0.5,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            result = await engine._load_emotional_state(user_id)

        assert result is not None
        assert result["arousal"] == 0.7
        assert result["valence"] == 0.8
        assert result["dominance"] == 0.6
        assert result["intimacy"] == 0.5

    @pytest.mark.asyncio
    async def test_load_emotional_state_returns_defaults_when_no_state(self, engine):
        """_load_emotional_state should return neutral defaults when no state exists."""
        user_id = uuid4()

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=None)
            mock_get_store.return_value = mock_store

            result = await engine._load_emotional_state(user_id)

        assert result is not None
        assert result["valence"] == 0.5
        assert result["arousal"] == 0.5
        assert result["dominance"] == 0.5
        assert result["intimacy"] == 0.5

    @pytest.mark.asyncio
    async def test_load_emotional_state_handles_error_gracefully(self, engine):
        """_load_emotional_state should return defaults on error."""
        user_id = uuid4()

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(
                side_effect=Exception("Database error")
            )
            mock_get_store.return_value = mock_store

            result = await engine._load_emotional_state(user_id)

        # Should return neutral defaults on error
        assert result is not None
        assert result["valence"] == 0.5
        assert result["arousal"] == 0.5

    @pytest.mark.asyncio
    async def test_load_emotional_state_returns_all_four_dimensions(self, engine):
        """_load_emotional_state should return all 4D dimensions."""
        user_id = uuid4()

        mock_state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.3,
            valence=0.4,
            dominance=0.9,
            intimacy=0.2,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            result = await engine._load_emotional_state(user_id)

        # Verify all 4 dimensions are present
        assert "arousal" in result
        assert "valence" in result
        assert "dominance" in result
        assert "intimacy" in result


class TestConflictSystemIntegration:
    """Tests for T2.10: Conflict System Integration."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def engine(self, mock_session):
        """Create TouchpointEngine with mock session."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-for-test"}):
            with patch("nikita.touchpoints.engine.MessageGenerator"):
                return TouchpointEngine(mock_session)

    @pytest.mark.asyncio
    async def test_check_conflict_active_returns_true_when_conflict_exists(self, engine):
        """_check_conflict_active should return True for any non-NONE conflict state."""
        user_id = uuid4()

        # Test with PASSIVE_AGGRESSIVE conflict
        mock_state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.PASSIVE_AGGRESSIVE,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            result = await engine._check_conflict_active(user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_conflict_active_returns_false_when_no_conflict(self, engine):
        """_check_conflict_active should return False when conflict_state is NONE."""
        user_id = uuid4()

        mock_state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.NONE,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            result = await engine._check_conflict_active(user_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_conflict_active_returns_false_when_no_state(self, engine):
        """_check_conflict_active should return False when no state exists."""
        user_id = uuid4()

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=None)
            mock_get_store.return_value = mock_store

            result = await engine._check_conflict_active(user_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_conflict_active_handles_error_gracefully(self, engine):
        """_check_conflict_active should return False on error."""
        user_id = uuid4()

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(
                side_effect=Exception("Database error")
            )
            mock_get_store.return_value = mock_store

            result = await engine._check_conflict_active(user_id)

        # Should return False (no conflict) on error
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "conflict_state,expected",
        [
            (ConflictState.NONE, False),
            (ConflictState.PASSIVE_AGGRESSIVE, True),
            (ConflictState.COLD, True),
            (ConflictState.VULNERABLE, True),
            (ConflictState.EXPLOSIVE, True),
        ],
    )
    async def test_check_conflict_active_for_all_conflict_states(
        self, engine, conflict_state, expected
    ):
        """_check_conflict_active should correctly identify all conflict states."""
        user_id = uuid4()

        mock_state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=conflict_state,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            result = await engine._check_conflict_active(user_id)

        assert result is expected


class TestIntegrationWithSilenceEvaluation:
    """Tests for integration with strategic silence evaluation."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def engine(self, mock_session):
        """Create TouchpointEngine with mock session."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-for-test"}):
            with patch("nikita.touchpoints.engine.MessageGenerator"):
                return TouchpointEngine(mock_session)

    @pytest.mark.asyncio
    async def test_evaluate_silence_uses_emotional_state(self, engine):
        """_evaluate_silence should pass emotional state to StrategicSilence."""
        user_id = uuid4()

        mock_state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,  # High arousal
            valence=0.2,  # Low valence (negative mood)
            dominance=0.5,
            intimacy=0.5,
            conflict_state=ConflictState.NONE,
        )

        # Create a mock touchpoint with proper TriggerContext
        from nikita.touchpoints.models import ScheduledTouchpoint, TriggerType, TriggerContext

        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
            chapter=1,
        )
        touchpoint = ScheduledTouchpoint(
            id=uuid4(),
            user_id=user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=trigger_context,
            delivery_at=datetime.now(timezone.utc),
            chapter=1,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            # Spy on StrategicSilence.apply_strategic_silence
            with patch.object(
                engine.silence, "apply_strategic_silence"
            ) as mock_silence:
                mock_silence.return_value = MagicMock(should_skip=False)

                await engine._evaluate_silence(touchpoint)

                # Verify emotional state was passed
                mock_silence.assert_called_once()
                call_kwargs = mock_silence.call_args[1]
                assert call_kwargs["emotional_state"]["arousal"] == 0.9
                assert call_kwargs["emotional_state"]["valence"] == 0.2

    @pytest.mark.asyncio
    async def test_evaluate_silence_uses_conflict_state(self, engine):
        """_evaluate_silence should pass conflict state to StrategicSilence."""
        user_id = uuid4()

        mock_state = EmotionalStateModel(
            user_id=user_id,
            conflict_state=ConflictState.COLD,  # Active conflict
        )

        from nikita.touchpoints.models import ScheduledTouchpoint, TriggerType, TriggerContext

        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="evening",
            chapter=1,
        )
        touchpoint = ScheduledTouchpoint(
            id=uuid4(),
            user_id=user_id,
            trigger_type=TriggerType.TIME,
            trigger_context=trigger_context,
            delivery_at=datetime.now(timezone.utc),
            chapter=1,
        )

        with patch(
            "nikita.touchpoints.engine.get_state_store"
        ) as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_current_state = AsyncMock(return_value=mock_state)
            mock_get_store.return_value = mock_store

            with patch.object(
                engine.silence, "apply_strategic_silence"
            ) as mock_silence:
                mock_silence.return_value = MagicMock(should_skip=False)

                await engine._evaluate_silence(touchpoint)

                # Verify conflict_active was True
                call_kwargs = mock_silence.call_args[1]
                assert call_kwargs["conflict_active"] is True
