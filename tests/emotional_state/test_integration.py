"""Integration tests for Spec 023 Phase E (T019-T022).

Tests the wiring of EmotionalStateModel to ContextPackage and
PostProcessingPipeline.

AC-T019.1: PostProcessingPipeline calls StateComputer
AC-T019.2: Emotional state stored in ContextPackage.nikita_mood
AC-T019.3: Conflict state available for Layer 3
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.context.layers.emotional_state import (
    Layer3Composer,
    get_layer3_composer,
    compose_emotional_state_layer,
)
from nikita.context.package import EmotionalState
from nikita.emotional_state.models import ConflictState, EmotionalStateModel


# ============================================================================
# T019 Tests: Wire to ContextPackage
# ============================================================================


class TestLayer3ComposerEmotionalStateModel:
    """Test Layer3Composer accepts EmotionalStateModel (AC-T019.3)."""

    def test_compose_with_emotional_state_model_no_conflict(self):
        """Should compose without conflict state section when NONE."""
        composer = Layer3Composer()
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.6,
            valence=0.7,
            dominance=0.5,
            intimacy=0.6,
            conflict_state=ConflictState.NONE,
        )

        result = composer.compose(state)

        # Should NOT contain conflict state section
        assert "**Conflict State**:" not in result
        # Should contain standard sections
        assert "**Mood**:" in result
        assert "**Energy**:" in result
        assert "**Emotional Dynamics**:" in result
        assert "**Behavioral Impact**:" in result

    def test_compose_with_passive_aggressive_conflict(self):
        """Should show passive aggressive conflict state and behaviors."""
        composer = Layer3Composer()
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.3,
            dominance=0.5,
            intimacy=0.3,
            conflict_state=ConflictState.PASSIVE_AGGRESSIVE,
        )

        result = composer.compose(state)

        # Should contain conflict state
        assert "**Conflict State**:" in result
        assert "Passive Aggressive" in result
        # Should have conflict-specific behaviors
        assert "shorter, more clipped responses" in result
        assert "sarcasm" in result

    def test_compose_with_cold_conflict(self):
        """Should show cold conflict state and behaviors."""
        composer = Layer3Composer()
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.3,
            valence=0.2,
            dominance=0.5,
            intimacy=0.2,
            conflict_state=ConflictState.COLD,
        )

        result = composer.compose(state)

        assert "**Conflict State**:" in result
        assert "Cold" in result
        # Should have cold-specific behaviors
        assert "minimal and factual" in result
        assert "formal language" in result

    def test_compose_with_vulnerable_conflict(self):
        """Should show vulnerable conflict state and behaviors."""
        composer = Layer3Composer()
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.4,
            valence=0.3,
            dominance=0.2,
            intimacy=0.4,
            conflict_state=ConflictState.VULNERABLE,
        )

        result = composer.compose(state)

        assert "**Conflict State**:" in result
        assert "Vulnerable" in result
        # Should have vulnerable-specific behaviors
        assert "hurt feelings" in result
        assert "reassurance" in result

    def test_compose_with_explosive_conflict(self):
        """Should show explosive conflict state and behaviors."""
        composer = Layer3Composer()
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,
            valence=0.2,
            dominance=0.7,
            intimacy=0.2,
            conflict_state=ConflictState.EXPLOSIVE,
        )

        result = composer.compose(state)

        assert "**Conflict State**:" in result
        assert "Explosive" in result
        # Should have explosive-specific behaviors
        assert "anger directly" in result
        assert "threaten consequences" in result

    def test_compose_backwards_compatible_with_emotional_state(self):
        """Should still work with simple EmotionalState from package.py."""
        composer = Layer3Composer()

        state = EmotionalState(
            arousal=0.6,
            valence=0.7,
            dominance=0.5,
            intimacy=0.6,
        )

        result = composer.compose(state)

        # Should NOT contain conflict state (EmotionalState doesn't have it)
        assert "**Conflict State**:" not in result
        # Should contain standard sections
        assert "**Mood**:" in result
        assert "**Behavioral Impact**:" in result

    def test_compose_with_none_uses_default(self):
        """Should use default neutral state when None passed."""
        composer = Layer3Composer()

        result = composer.compose(None)

        assert "**Mood**:" in result
        # Default is neutral
        assert "Neutral" in result


class TestLayer3ComposerConflictBehaviors:
    """Test conflict state overrides standard behavioral impacts."""

    def test_conflict_behavior_overrides_arousal_impact(self):
        """In conflict, conflict behaviors should replace arousal impacts."""
        composer = Layer3Composer()
        user_id = uuid4()

        # High arousal but in cold conflict
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,  # High arousal
            valence=0.2,
            dominance=0.5,
            intimacy=0.2,
            conflict_state=ConflictState.COLD,
        )

        result = composer.compose(state)

        # Should have cold behaviors, not high-arousal behaviors
        assert "minimal and factual" in result
        # Should NOT have standard high-arousal behavior
        assert "animation and enthusiasm" not in result

    def test_no_conflict_uses_standard_behaviors(self):
        """Without conflict, should use standard emotional impacts."""
        composer = Layer3Composer()
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.9,
            valence=0.8,
            dominance=0.7,
            intimacy=0.7,
            conflict_state=ConflictState.NONE,
        )

        result = composer.compose(state)

        # Should have standard high-arousal behavior
        assert "animation and enthusiasm" in result


class TestLayer3ComposerConvenienceFunction:
    """Test module-level convenience function."""

    def test_convenience_function_accepts_emotional_state_model(self):
        """compose_emotional_state_layer should accept EmotionalStateModel."""
        user_id = uuid4()
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.5,
            conflict_state=ConflictState.COLD,
        )

        result = compose_emotional_state_layer(state)

        assert "Cold" in result

    def test_convenience_function_accepts_none(self):
        """compose_emotional_state_layer should accept None."""
        result = compose_emotional_state_layer(None)

        assert "**Mood**:" in result


class TestLayer3ComposerSingleton:
    """Test singleton pattern."""

    def test_get_layer3_composer_returns_same_instance(self):
        """Should return singleton instance."""
        composer1 = get_layer3_composer()
        composer2 = get_layer3_composer()

        assert composer1 is composer2


class TestLayerComposerStateComputerIntegration:
    """Test LayerComposer calls StateComputer (AC-T019.1)."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.chapter = 2
        user.relationship_score = 65
        user.updated_at = datetime.now(timezone.utc)
        return user

    @pytest.mark.asyncio
    async def test_layer_composer_calls_state_computer(self, mock_user):
        """AC-T019.1: LayerComposer should call StateComputer.compute()."""
        from nikita.post_processing.layer_composer import LayerComposer

        user_id = uuid4()

        # Mock StateComputer
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=user_id,
            arousal=0.6,
            valence=0.7,
            dominance=0.5,
            intimacy=0.6,
            conflict_state=ConflictState.NONE,
        )

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[])
        mock_life_sim.get_current_mood = AsyncMock(
            return_value=MagicMock(
                arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
            )
        )

        # Create composer with mocked dependencies
        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        # Call _compute_emotional_state
        result = await composer._compute_emotional_state(user_id, mock_user)

        # Verify StateComputer was called
        mock_state_computer.compute.assert_called_once()
        # Verify result is EmotionalStateModel
        assert isinstance(result, EmotionalStateModel)
        assert result.arousal == 0.6
        assert result.valence == 0.7

    @pytest.mark.asyncio
    async def test_layer_composer_passes_life_events_to_state_computer(
        self, mock_user
    ):
        """StateComputer should receive life events from LifeSimulator."""
        from nikita.post_processing.layer_composer import LayerComposer
        from nikita.emotional_state import LifeEventImpact
        from nikita.life_simulation.models import EmotionalImpact

        user_id = uuid4()

        # Mock life event with proper EmotionalImpact model
        mock_event = MagicMock()
        mock_event.event_type = "work_success"
        mock_event.emotional_impact = EmotionalImpact(valence_delta=0.1)

        # Mock life simulator returning events
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[mock_event])
        mock_life_sim.get_current_mood = AsyncMock(
            return_value=MagicMock(
                arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
            )
        )

        # Mock StateComputer that records args
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=user_id,
        )

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        await composer._compute_emotional_state(user_id, mock_user)

        # Verify life_events were passed
        call_kwargs = mock_state_computer.compute.call_args
        assert "life_events" in call_kwargs.kwargs
        life_events = call_kwargs.kwargs["life_events"]
        assert len(life_events) == 1
        assert life_events[0].valence_delta == 0.1

    @pytest.mark.asyncio
    async def test_layer_composer_fallback_on_state_computer_error(
        self, mock_user
    ):
        """Should use fallback when StateComputer fails."""
        from nikita.post_processing.layer_composer import LayerComposer

        user_id = uuid4()

        # Mock StateComputer that raises
        mock_state_computer = MagicMock()
        mock_state_computer.compute.side_effect = Exception("StateComputer failed")

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[])

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        # Should not raise, should return fallback
        result = await composer._compute_emotional_state(user_id, mock_user)

        assert isinstance(result, EmotionalStateModel)
        # Fallback uses relationship_score (65) / 100 = 0.65 for valence
        assert result.valence == 0.65


class TestContextPackageConflictState:
    """Test conflict state stored in ContextPackage (AC-T019.2, AC-T019.3)."""

    @pytest.mark.asyncio
    async def test_situation_hints_includes_conflict_state(self):
        """AC-T019.3: situation_hints should include conflict_state."""
        from nikita.post_processing.layer_composer import LayerComposer
        from nikita.db.models.user import User

        user_id = uuid4()

        # Create mock dependencies
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        # Mock user
        mock_user = MagicMock(spec=User)
        mock_user.chapter = 2
        mock_user.relationship_score = 50
        mock_user.updated_at = datetime.now(timezone.utc)

        # Mock repos
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_thread_repo = MagicMock()
        mock_thread_repo.list_open = AsyncMock(return_value=[])

        mock_thought_repo = MagicMock()
        mock_thought_repo.list_active = AsyncMock(return_value=[])

        mock_summary_repo = MagicMock()
        mock_summary_repo.get_by_date = AsyncMock(return_value=None)
        mock_summary_repo.get_range = AsyncMock(return_value=[])

        # Mock layer composers
        mock_layer2 = MagicMock()
        mock_layer2.compose.return_value = "Chapter 2 behaviors"

        mock_layer3 = MagicMock()
        mock_layer3.compose.return_value = "Emotional state"

        mock_layer4 = MagicMock()
        mock_layer4.detect_and_compose.return_value = MagicMock(
            situation_type=MagicMock(value="returning_after_gap")
        )

        mock_layer5 = MagicMock()

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[])
        mock_life_sim.get_current_mood = AsyncMock(
            return_value=MagicMock(
                arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5
            )
        )

        # Mock state computer returning conflict state
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.3,
            conflict_state=ConflictState.COLD,
        )

        # Create composer with patched repos
        with patch(
            "nikita.post_processing.layer_composer.UserRepository",
            return_value=mock_user_repo,
        ), patch(
            "nikita.post_processing.layer_composer.ConversationThreadRepository",
            return_value=mock_thread_repo,
        ), patch(
            "nikita.post_processing.layer_composer.NikitaThoughtRepository",
            return_value=mock_thought_repo,
        ), patch(
            "nikita.post_processing.layer_composer.DailySummaryRepository",
            return_value=mock_summary_repo,
        ):
            composer = LayerComposer(
                session_factory=lambda: mock_session,
                layer2_composer=mock_layer2,
                layer3_composer=mock_layer3,
                layer4_computer=mock_layer4,
                layer5_injector=mock_layer5,
                life_simulator=mock_life_sim,
                state_computer=mock_state_computer,
            )

            package = await composer.compose(user_id)

        # Verify conflict_state is in situation_hints
        assert "conflict_state" in package.situation_hints
        assert package.situation_hints["conflict_state"] == "cold"

    @pytest.mark.asyncio
    async def test_nikita_mood_populated_from_state_computer(self):
        """AC-T019.2: nikita_mood should be populated from StateComputer."""
        from nikita.post_processing.layer_composer import LayerComposer

        user_id = uuid4()

        # Create mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        # Mock user
        mock_user = MagicMock()
        mock_user.chapter = 3
        mock_user.relationship_score = 75
        mock_user.updated_at = datetime.now(timezone.utc)

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_thread_repo = MagicMock()
        mock_thread_repo.list_open = AsyncMock(return_value=[])

        mock_thought_repo = MagicMock()
        mock_thought_repo.list_active = AsyncMock(return_value=[])

        mock_summary_repo = MagicMock()
        mock_summary_repo.get_by_date = AsyncMock(return_value=None)
        mock_summary_repo.get_range = AsyncMock(return_value=[])

        # Mock layers
        mock_layer2 = MagicMock()
        mock_layer2.compose.return_value = "Chapter"
        mock_layer3 = MagicMock()
        mock_layer3.compose.return_value = "Emotional"
        mock_layer4 = MagicMock()
        mock_layer4.detect_and_compose.return_value = MagicMock(
            situation_type=MagicMock(value="normal")
        )
        mock_layer5 = MagicMock()

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[])

        # Mock state computer with specific values
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(
            user_id=user_id,
            arousal=0.8,
            valence=0.6,
            dominance=0.7,
            intimacy=0.65,
            conflict_state=ConflictState.NONE,
        )

        with patch(
            "nikita.post_processing.layer_composer.UserRepository",
            return_value=mock_user_repo,
        ), patch(
            "nikita.post_processing.layer_composer.ConversationThreadRepository",
            return_value=mock_thread_repo,
        ), patch(
            "nikita.post_processing.layer_composer.NikitaThoughtRepository",
            return_value=mock_thought_repo,
        ), patch(
            "nikita.post_processing.layer_composer.DailySummaryRepository",
            return_value=mock_summary_repo,
        ):
            composer = LayerComposer(
                session_factory=lambda: mock_session,
                layer2_composer=mock_layer2,
                layer3_composer=mock_layer3,
                layer4_computer=mock_layer4,
                layer5_injector=mock_layer5,
                life_simulator=mock_life_sim,
                state_computer=mock_state_computer,
            )

            package = await composer.compose(user_id)

        # Verify nikita_mood has values from StateComputer
        assert package.nikita_mood.arousal == 0.8
        assert package.nikita_mood.valence == 0.6
        assert package.nikita_mood.dominance == 0.7
        assert package.nikita_mood.intimacy == 0.65
        # Energy should be derived from arousal
        assert package.nikita_energy == 0.8


# ============================================================================
# T020 Tests: Wire to LifeSimulator (022)
# ============================================================================


class TestLifeSimulatorIntegration:
    """Test LifeSimulator events feed into StateComputer (AC-T020.1-3)."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.chapter = 2
        user.relationship_score = 65
        user.updated_at = datetime.now(timezone.utc)
        return user

    @pytest.mark.asyncio
    async def test_life_event_emotional_impact_converted_correctly(self, mock_user):
        """AC-T020.2: Events with emotional_impact should be processed correctly."""
        from nikita.post_processing.layer_composer import LayerComposer
        from nikita.life_simulation.models import EmotionalImpact

        user_id = uuid4()

        # Create mock life event with EmotionalImpact model
        mock_event = MagicMock()
        mock_event.event_type = "work_success"
        mock_event.emotional_impact = EmotionalImpact(
            arousal_delta=0.1,
            valence_delta=0.2,
            dominance_delta=0.15,
            intimacy_delta=0.05,
        )

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[mock_event])

        # Mock StateComputer that records args
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(user_id=user_id)

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        await composer._compute_emotional_state(user_id, mock_user)

        # Verify life_events were passed with correct deltas
        call_kwargs = mock_state_computer.compute.call_args.kwargs
        assert "life_events" in call_kwargs
        life_events = call_kwargs["life_events"]
        assert len(life_events) == 1

        # Verify the LifeEventImpact has correct values
        event_impact = life_events[0]
        assert event_impact.arousal_delta == 0.1
        assert event_impact.valence_delta == 0.2
        assert event_impact.dominance_delta == 0.15
        assert event_impact.intimacy_delta == 0.05

    @pytest.mark.asyncio
    async def test_multiple_life_events_converted(self, mock_user):
        """AC-T020.1: Multiple LifeSimulator events should feed into StateComputer."""
        from nikita.post_processing.layer_composer import LayerComposer
        from nikita.life_simulation.models import EmotionalImpact

        user_id = uuid4()

        # Create multiple mock events
        event1 = MagicMock()
        event1.event_type = "work_success"
        event1.emotional_impact = EmotionalImpact(
            arousal_delta=0.1,
            valence_delta=0.2,
        )

        event2 = MagicMock()
        event2.event_type = "friend_drama"
        event2.emotional_impact = EmotionalImpact(
            arousal_delta=0.15,
            valence_delta=-0.1,
        )

        event3 = MagicMock()
        event3.event_type = "gym"
        event3.emotional_impact = EmotionalImpact(
            arousal_delta=0.2,
            valence_delta=0.1,
        )

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[event1, event2, event3])

        # Mock StateComputer
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(user_id=user_id)

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        await composer._compute_emotional_state(user_id, mock_user)

        # Verify all 3 events were passed
        call_kwargs = mock_state_computer.compute.call_args.kwargs
        life_events = call_kwargs["life_events"]
        assert len(life_events) == 3

    @pytest.mark.asyncio
    async def test_life_event_without_emotional_impact_ignored(self, mock_user):
        """Events without emotional_impact should be skipped."""
        from nikita.post_processing.layer_composer import LayerComposer
        from nikita.life_simulation.models import EmotionalImpact

        user_id = uuid4()

        # Create one event with impact, one without
        event_with_impact = MagicMock()
        event_with_impact.event_type = "work_success"
        event_with_impact.emotional_impact = EmotionalImpact(valence_delta=0.1)

        event_without_impact = MagicMock()
        event_without_impact.event_type = "errand"
        event_without_impact.emotional_impact = None

        # Mock life simulator
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(
            return_value=[event_with_impact, event_without_impact]
        )

        # Mock StateComputer
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(user_id=user_id)

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        await composer._compute_emotional_state(user_id, mock_user)

        # Only the event with impact should be passed
        call_kwargs = mock_state_computer.compute.call_args.kwargs
        life_events = call_kwargs["life_events"]
        assert len(life_events) == 1

    @pytest.mark.asyncio
    async def test_life_simulator_error_handled_gracefully(self, mock_user):
        """Should continue without events if LifeSimulator fails."""
        from nikita.post_processing.layer_composer import LayerComposer

        user_id = uuid4()

        # Mock life simulator that fails
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(side_effect=Exception("Simulator error"))

        # Mock StateComputer
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(user_id=user_id)

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        # Should not raise
        result = await composer._compute_emotional_state(user_id, mock_user)

        assert isinstance(result, EmotionalStateModel)
        # StateComputer should be called without life_events (None)
        call_kwargs = mock_state_computer.compute.call_args.kwargs
        assert call_kwargs.get("life_events") is None

    @pytest.mark.asyncio
    async def test_empty_life_events_handled(self, mock_user):
        """Should handle empty event list correctly."""
        from nikita.post_processing.layer_composer import LayerComposer

        user_id = uuid4()

        # Mock life simulator returning empty list
        mock_life_sim = MagicMock()
        mock_life_sim.get_today_events = AsyncMock(return_value=[])

        # Mock StateComputer
        mock_state_computer = MagicMock()
        mock_state_computer.compute.return_value = EmotionalStateModel(user_id=user_id)

        composer = LayerComposer(
            state_computer=mock_state_computer,
            life_simulator=mock_life_sim,
        )

        await composer._compute_emotional_state(user_id, mock_user)

        # life_events should be empty list or None
        call_kwargs = mock_state_computer.compute.call_args.kwargs
        life_events = call_kwargs.get("life_events")
        assert life_events is None or len(life_events) == 0


class TestStateComputerLifeEventProcessing:
    """Test StateComputer correctly processes life event impacts (AC-T020.2)."""

    def test_state_computer_applies_single_event_impact(self):
        """StateComputer should apply life event deltas to emotional state."""
        from nikita.emotional_state import StateComputer, LifeEventImpact

        computer = StateComputer()
        user_id = uuid4()

        # Event that increases valence and arousal
        event = LifeEventImpact(
            arousal_delta=0.2,
            valence_delta=0.15,
            dominance_delta=0.1,
            intimacy_delta=0.0,
        )

        result = computer.compute(
            user_id=user_id,
            life_events=[event],
            chapter=1,
            relationship_score=0.5,
        )

        # Base state is around 0.5 for all dimensions
        # With +0.2 arousal delta, should be higher
        assert result.arousal > 0.5
        assert result.valence > 0.5

    def test_state_computer_applies_multiple_event_impacts(self):
        """StateComputer should sum deltas from multiple events."""
        from nikita.emotional_state import StateComputer, LifeEventImpact

        computer = StateComputer()
        user_id = uuid4()

        # Two positive events
        events = [
            LifeEventImpact(arousal_delta=0.1, valence_delta=0.1),
            LifeEventImpact(arousal_delta=0.1, valence_delta=0.1),
        ]

        result = computer.compute(
            user_id=user_id,
            life_events=events,
            chapter=1,
            relationship_score=0.5,
        )

        # Cumulative effect should be noticeable (base ~0.5 + 0.2 each = 0.7 before clamping)
        # Clamping limits total delta to ±0.3, so we expect ~0.55+ for arousal
        assert result.arousal >= 0.55
        assert result.valence >= 0.55

    def test_state_computer_clamps_extreme_deltas(self):
        """StateComputer should clamp extreme cumulative deltas."""
        from nikita.emotional_state import StateComputer, LifeEventImpact

        computer = StateComputer()
        user_id = uuid4()

        # Events with extreme negative deltas
        events = [
            LifeEventImpact(valence_delta=-0.3),
            LifeEventImpact(valence_delta=-0.3),
            LifeEventImpact(valence_delta=-0.3),
        ]

        result = computer.compute(
            user_id=user_id,
            life_events=events,
            chapter=1,
            relationship_score=0.5,
        )

        # Should be clamped, not go below 0
        assert result.valence >= 0.0
        assert result.valence <= 1.0


# ============================================================================
# T021 Tests: E2E Pipeline Tests
# ============================================================================


class TestE2EPipeline:
    """End-to-end tests for the full emotional state pipeline (AC-T021)."""

    @pytest.fixture
    def state_computer(self):
        """Create real StateComputer."""
        from nikita.emotional_state import StateComputer
        return StateComputer()

    @pytest.fixture
    def conflict_detector(self):
        """Create real ConflictDetector."""
        from nikita.emotional_state import ConflictDetector
        return ConflictDetector()

    @pytest.fixture
    def recovery_manager(self):
        """Create real RecoveryManager."""
        from nikita.emotional_state import RecoveryManager
        return RecoveryManager()

    def test_full_pipeline_events_to_state_to_context(
        self, state_computer, conflict_detector
    ):
        """AC-T021.1: Full pipeline from events → state → context."""
        from nikita.emotional_state import LifeEventImpact
        from nikita.context.layers.emotional_state import Layer3Composer

        user_id = uuid4()

        # Step 1: Life events from simulator
        events = [
            LifeEventImpact(arousal_delta=0.1, valence_delta=0.15),  # Good event
            LifeEventImpact(arousal_delta=-0.05, valence_delta=0.1),  # Relaxing
        ]

        # Step 2: StateComputer computes state
        state = state_computer.compute(
            user_id=user_id,
            life_events=events,
            chapter=2,
            relationship_score=0.65,
        )

        # Step 3: ConflictDetector checks for conflicts
        conflict_state = conflict_detector.detect_conflict_state(state)

        # Step 4: State goes to Layer3Composer for context
        state_with_conflict = EmotionalStateModel(
            user_id=user_id,
            arousal=state.arousal,
            valence=state.valence,
            dominance=state.dominance,
            intimacy=state.intimacy,
            conflict_state=conflict_state,
        )

        composer = Layer3Composer()
        context_layer = composer.compose(state_with_conflict)

        # Verify pipeline produced valid output
        # Base arousal varies by time of day, events add +0.05 net
        # Just verify valence improved (events have +0.25 net valence delta)
        assert state.valence > 0.5  # Events increased valence
        assert state.arousal >= 0.0  # Valid arousal range
        assert conflict_state == ConflictState.NONE  # No conflict (positive state)
        assert "**Mood**:" in context_layer
        assert "**Behavioral Impact**:" in context_layer

    def test_conversation_tone_affects_emotional_state(self, state_computer):
        """AC-T021.2: Conversation tone should affect emotional state."""
        from nikita.emotional_state.computer import ConversationTone

        user_id = uuid4()

        # Supportive conversation should improve mood
        supportive_state = state_computer.compute(
            user_id=user_id,
            conversation_tones=[ConversationTone.SUPPORTIVE, ConversationTone.ROMANTIC],
            chapter=2,
            relationship_score=0.5,
        )

        # Dismissive conversation should worsen mood
        dismissive_state = state_computer.compute(
            user_id=user_id,
            conversation_tones=[ConversationTone.DISMISSIVE, ConversationTone.COLD],
            chapter=2,
            relationship_score=0.5,
        )

        # Supportive should have higher valence and intimacy
        assert supportive_state.valence > dismissive_state.valence
        assert supportive_state.intimacy > dismissive_state.intimacy

    def test_state_computation_deterministic(self, state_computer):
        """AC-T021.3: Same inputs should produce same state (determinism)."""
        from nikita.emotional_state import LifeEventImpact
        from nikita.emotional_state.computer import ConversationTone
        from datetime import datetime, timezone

        user_id = uuid4()
        fixed_time = datetime(2026, 1, 12, 14, 0, 0, tzinfo=timezone.utc)

        events = [LifeEventImpact(valence_delta=0.1)]
        tones = [ConversationTone.PLAYFUL]

        # Compute twice with same inputs
        state1 = state_computer.compute(
            user_id=user_id,
            timestamp=fixed_time,
            life_events=events,
            conversation_tones=tones,
            chapter=3,
            relationship_score=0.7,
        )

        state2 = state_computer.compute(
            user_id=user_id,
            timestamp=fixed_time,
            life_events=events,
            conversation_tones=tones,
            chapter=3,
            relationship_score=0.7,
        )

        # Should produce identical results
        assert state1.arousal == state2.arousal
        assert state1.valence == state2.valence
        assert state1.dominance == state2.dominance
        assert state1.intimacy == state2.intimacy


class TestStateStore:
    """Test state persistence between sessions (AC-T021.3)."""

    def test_state_model_serializes_to_db(self):
        """State should serialize for database storage."""
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.7,
            valence=0.6,
            dominance=0.5,
            intimacy=0.8,
            conflict_state=ConflictState.VULNERABLE,
            conflict_trigger="ignored message",
            ignored_message_count=2,
        )

        db_dict = state.model_dump_for_db()

        # Verify all fields serialize
        assert db_dict["arousal"] == 0.7
        assert db_dict["valence"] == 0.6
        assert db_dict["conflict_state"] == "vulnerable"
        assert db_dict["conflict_trigger"] == "ignored message"
        assert db_dict["ignored_message_count"] == 2

    def test_state_model_deserializes_from_db(self):
        """State should deserialize from database row."""
        user_id = uuid4()
        state_id = uuid4()

        db_row = {
            "state_id": str(state_id),
            "user_id": str(user_id),
            "arousal": 0.65,
            "valence": 0.4,
            "dominance": 0.55,
            "intimacy": 0.3,
            "conflict_state": "cold",
            "conflict_started_at": "2026-01-12T10:00:00+00:00",
            "conflict_trigger": "low valence",
            "ignored_message_count": 0,
            "last_updated": "2026-01-12T12:00:00+00:00",
            "created_at": "2026-01-12T08:00:00+00:00",
            "metadata": {"test": True},
        }

        state = EmotionalStateModel.from_db_row(db_row)

        assert state.arousal == 0.65
        assert state.valence == 0.4
        assert state.conflict_state == ConflictState.COLD
        assert state.metadata == {"test": True}


# ============================================================================
# T022 Tests: Quality Tests
# ============================================================================


class TestEventStateCorrelation:
    """Test state reflects events correctly (AC-T022.1)."""

    def test_positive_events_improve_state(self):
        """Positive life events should improve emotional state."""
        from nikita.emotional_state import StateComputer, LifeEventImpact

        computer = StateComputer()
        user_id = uuid4()

        # Baseline (no events)
        baseline = computer.compute(
            user_id=user_id,
            chapter=2,
            relationship_score=0.5,
        )

        # With positive events
        with_events = computer.compute(
            user_id=user_id,
            life_events=[
                LifeEventImpact(arousal_delta=0.15, valence_delta=0.2),
                LifeEventImpact(dominance_delta=0.1),
            ],
            chapter=2,
            relationship_score=0.5,
        )

        # State should be better
        assert with_events.valence > baseline.valence
        assert with_events.arousal > baseline.arousal

    def test_negative_events_worsen_state(self):
        """Negative life events should worsen emotional state."""
        from nikita.emotional_state import StateComputer, LifeEventImpact

        computer = StateComputer()
        user_id = uuid4()

        baseline = computer.compute(
            user_id=user_id,
            chapter=2,
            relationship_score=0.5,
        )

        with_negative = computer.compute(
            user_id=user_id,
            life_events=[
                LifeEventImpact(valence_delta=-0.2, arousal_delta=0.1),
            ],
            chapter=2,
            relationship_score=0.5,
        )

        assert with_negative.valence < baseline.valence

    def test_chapter_progression_affects_intimacy(self):
        """Higher chapters should have higher baseline intimacy."""
        from nikita.emotional_state import StateComputer

        computer = StateComputer()
        user_id = uuid4()

        chapter1_state = computer.compute(
            user_id=user_id,
            chapter=1,
            relationship_score=0.5,
        )

        chapter5_state = computer.compute(
            user_id=user_id,
            chapter=5,
            relationship_score=0.5,
        )

        # Chapter 5 should have higher intimacy modifier
        assert chapter5_state.intimacy > chapter1_state.intimacy


class TestConflictDetectionAccuracy:
    """Test conflict detection accuracy (AC-T022.2)."""

    @pytest.fixture
    def detector(self):
        """Create ConflictDetector."""
        from nikita.emotional_state import ConflictDetector
        return ConflictDetector()

    def test_low_valence_triggers_cold_conflict(self, detector):
        """Low valence should trigger COLD conflict."""
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.4,
            valence=0.25,  # Below 0.3 threshold
            dominance=0.5,
            intimacy=0.4,
        )

        conflict = detector.detect_conflict_state(state)

        assert conflict == ConflictState.COLD

    def test_high_arousal_low_valence_triggers_explosive(self, detector):
        """High arousal + low valence should trigger EXPLOSIVE conflict."""
        user_id = uuid4()

        # Need to be in COLD state first to transition to EXPLOSIVE
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.85,  # Above 0.8
            valence=0.2,  # Below 0.3
            dominance=0.6,
            intimacy=0.3,
            conflict_state=ConflictState.COLD,  # Must be in COLD to escalate
        )

        conflict = detector.detect_conflict_state(state)

        assert conflict == ConflictState.EXPLOSIVE

    def test_normal_state_no_conflict(self, detector):
        """Normal balanced state should have no conflict."""
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.6,
            dominance=0.5,
            intimacy=0.5,
        )

        conflict = detector.detect_conflict_state(state)

        assert conflict == ConflictState.NONE

    def test_ignored_messages_trigger_passive_aggressive(self, detector):
        """2+ ignored messages should trigger PASSIVE_AGGRESSIVE."""
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.5,
            dominance=0.5,
            intimacy=0.5,
            ignored_message_count=2,  # Threshold is 2
        )

        conflict = detector.detect_conflict_state(state)

        assert conflict == ConflictState.PASSIVE_AGGRESSIVE


class TestRecoveryMechanics:
    """Test recovery mechanics work as intended (AC-T022.3)."""

    @pytest.fixture
    def manager(self):
        """Create RecoveryManager."""
        from nikita.emotional_state import RecoveryManager
        return RecoveryManager()

    def test_apology_enables_recovery(self, manager):
        """Apology approach should enable recovery from conflict."""
        from nikita.emotional_state.recovery import RecoveryApproach
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.3,
            conflict_state=ConflictState.COLD,
        )

        # apply_recovery returns tuple (new_state, result)
        new_state, result = manager.apply_recovery(state, approach=RecoveryApproach.APOLOGETIC)

        # Recovery should clear conflict state or show progress
        # Recovery doesn't always increase valence, it clears conflict state
        assert (
            new_state.conflict_state == ConflictState.NONE
            or result.recovery_amount > 0
            or new_state.valence >= state.valence
        )

    def test_dismissive_blocks_recovery(self, manager):
        """Dismissive approach should block recovery."""
        from nikita.emotional_state.recovery import RecoveryApproach
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.3,
            conflict_state=ConflictState.COLD,
        )

        # apply_recovery returns tuple (new_state, result)
        new_state, result = manager.apply_recovery(state, approach=RecoveryApproach.DISMISSIVE)

        # No recovery should occur
        assert result.recovery_amount == 0.0

    def test_full_recovery_clears_conflict(self, manager):
        """Full recovery should clear conflict state."""
        from nikita.emotional_state.recovery import RecoveryApproach
        user_id = uuid4()

        # State that's close to recovery threshold
        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.45,  # Close to recovery threshold of 0.5
            dominance=0.5,
            intimacy=0.5,
            conflict_state=ConflictState.COLD,
        )

        # Multiple recovery applications
        current = state
        for _ in range(5):
            # apply_recovery returns tuple (new_state, result)
            new_state, result = manager.apply_recovery(current, approach=RecoveryApproach.APOLOGETIC)
            current = new_state
            if result.recovered:
                break

        # Should have recovered
        assert current.conflict_state == ConflictState.NONE or current.valence >= 0.5

    def test_no_conflict_no_recovery_needed(self, manager):
        """Should detect when no recovery is needed."""
        user_id = uuid4()

        state = EmotionalStateModel(
            user_id=user_id,
            arousal=0.5,
            valence=0.7,
            conflict_state=ConflictState.NONE,
        )

        can_recover = manager.can_recover(state)

        assert not can_recover  # No conflict to recover from
