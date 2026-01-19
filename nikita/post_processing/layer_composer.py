"""Layer Composer for Post-Processing Pipeline (Spec 021, T023 + Spec 022, T015 + Spec 023, T019).

Pre-composes Layers 2-4 (chapter, emotional state, situation) for storage
in the context package.

AC-T023.1: LayerComposer class pre-composes Layers 2-4
AC-T023.2: Fetches current chapter, emotional state, situation hints
AC-T023.3: Stores composed layers in context package
AC-T023.4: Unit tests for composer

AC-T015.1: life_events_today field populated (via LifeSimulator)
AC-T015.2: Events formatted as natural language
AC-T015.3: Top 3 events by importance selected

AC-T019.1: PostProcessingPipeline calls StateComputer
AC-T019.2: Emotional state stored in ContextPackage.nikita_mood
AC-T019.3: Conflict state available for Layer 3
"""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from nikita.context.layers import (
    get_layer2_composer,
    get_layer3_composer,
    get_layer4_computer,
    get_layer5_injector,
)
from nikita.context.package import (
    ActiveThread,
    ContextPackage,
    EmotionalState,
)
from nikita.db.database import get_async_session
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.thread_repository import ConversationThreadRepository
from nikita.db.repositories.thought_repository import NikitaThoughtRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.emotional_state import (
    StateComputer,
    get_state_computer,
    EmotionalStateModel,
    ConflictState,
)

logger = logging.getLogger(__name__)


class LayerComposer:
    """Pre-composes Layers 2-4 for context package.

    Fetches current game state and pre-computes:
    - Layer 2: Chapter-specific behaviors
    - Layer 3: Emotional state (using StateComputer from Spec 023)
    - Layer 4: Situation hints

    Also collects context data for Layer 5:
    - User facts (from memory)
    - Relationship events
    - Active threads
    - Summaries

    Attributes:
        session_factory: Factory function to create database sessions.
        layer2_composer: Layer 2 composer instance.
        layer3_composer: Layer 3 composer instance.
        layer4_computer: Layer 4 computer instance.
        layer5_injector: Layer 5 injector instance.
        state_computer: StateComputer for emotional state (Spec 023).
    """

    def __init__(
        self,
        session_factory: Callable | None = None,
        layer2_composer: Any | None = None,
        layer3_composer: Any | None = None,
        layer4_computer: Any | None = None,
        layer5_injector: Any | None = None,
        life_simulator: Any | None = None,
        state_computer: StateComputer | None = None,
    ) -> None:
        """Initialize LayerComposer.

        Args:
            session_factory: Optional factory to create sessions.
            layer2_composer: Optional Layer 2 composer.
            layer3_composer: Optional Layer 3 composer.
            layer4_computer: Optional Layer 4 computer.
            layer5_injector: Optional Layer 5 injector.
            life_simulator: Optional LifeSimulator instance.
            state_computer: Optional StateComputer instance (Spec 023).
        """
        self._session_factory = session_factory or get_async_session
        self._layer2_composer = layer2_composer
        self._layer3_composer = layer3_composer
        self._layer4_computer = layer4_computer
        self._layer5_injector = layer5_injector
        self._life_simulator = life_simulator
        self._state_computer = state_computer

    @property
    def layer2_composer(self) -> Any:
        """Get Layer 2 composer (lazy load)."""
        if self._layer2_composer is None:
            self._layer2_composer = get_layer2_composer()
        return self._layer2_composer

    @property
    def layer3_composer(self) -> Any:
        """Get Layer 3 composer (lazy load)."""
        if self._layer3_composer is None:
            self._layer3_composer = get_layer3_composer()
        return self._layer3_composer

    @property
    def layer4_computer(self) -> Any:
        """Get Layer 4 computer (lazy load)."""
        if self._layer4_computer is None:
            self._layer4_computer = get_layer4_computer()
        return self._layer4_computer

    @property
    def layer5_injector(self) -> Any:
        """Get Layer 5 injector (lazy load)."""
        if self._layer5_injector is None:
            self._layer5_injector = get_layer5_injector()
        return self._layer5_injector

    @property
    def life_simulator(self) -> Any:
        """Get LifeSimulator (lazy load)."""
        if self._life_simulator is None:
            from nikita.life_simulation.simulator import get_life_simulator

            self._life_simulator = get_life_simulator()
        return self._life_simulator

    @property
    def state_computer(self) -> StateComputer:
        """Get StateComputer (lazy load).

        AC-T019.1: PostProcessingPipeline calls StateComputer
        """
        if self._state_computer is None:
            self._state_computer = get_state_computer()
        return self._state_computer

    async def compose(
        self,
        user_id: UUID,
    ) -> ContextPackage:
        """Compose context package with pre-computed layers.

        Args:
            user_id: User ID to compose package for.

        Returns:
            ContextPackage with all pre-computed context.
        """
        async with self._session_factory() as session:
            # Get user data
            user_repo = UserRepository(session)
            thread_repo = ConversationThreadRepository(session)
            thought_repo = NikitaThoughtRepository(session)
            summary_repo = DailySummaryRepository(session)

            user = await user_repo.get(user_id)
            if not user:
                logger.warning(f"User {user_id} not found, creating minimal package")
                return self._create_minimal_package(user_id)

            # Get chapter
            chapter = user.chapter or 1

            # Compose Layer 2 (chapter behaviors)
            chapter_layer = self.layer2_composer.compose(chapter)

            # Compose Layer 3 (emotional state via StateComputer - Spec 023)
            # AC-T019.1: PostProcessingPipeline calls StateComputer
            emotional_state_model = await self._compute_emotional_state(user_id, user)
            emotional_state_layer = self.layer3_composer.compose(emotional_state_model)

            # Compute Layer 4 (situation hints)
            now = datetime.now(timezone.utc)
            last_interaction = user.updated_at or now - timedelta(hours=24)
            situation_result = self.layer4_computer.detect_and_compose(
                current_time=now,
                last_interaction=last_interaction,
                conversation_active=False,  # Post-processing means conversation ended
            )
            situation_hints = {
                "situation_type": situation_result.situation_type.value,
                "time_of_day": self._get_time_of_day(now),
                "hours_since_last": self._hours_since(last_interaction, now),
            }

            # Get context for Layer 5
            user_facts = await self._get_user_facts(user_id)
            relationship_events = await self._get_relationship_events(user_id)
            active_threads = await thread_repo.list_open(user_id, limit=5)
            active_threads_models = [
                ActiveThread(
                    topic=t.topic,
                    status=t.status,
                    last_mentioned=t.updated_at or t.created_at,
                )
                for t in active_threads
            ]

            # Get summaries
            today_summary = await self._get_today_summary(summary_repo, user_id, now)
            week_summaries = await self._get_week_summaries(summary_repo, user_id, now)

            # Get Nikita's simulated life events
            life_events_today = await self._get_life_events(thought_repo, user_id)

            # Convert EmotionalStateModel to EmotionalState for package storage
            # AC-T019.2: Emotional state stored in ContextPackage.nikita_mood
            nikita_mood = EmotionalState(
                arousal=emotional_state_model.arousal,
                valence=emotional_state_model.valence,
                dominance=emotional_state_model.dominance,
                intimacy=emotional_state_model.intimacy,
            )
            nikita_energy = emotional_state_model.arousal  # Energy derived from arousal

            # Build package
            # Note: situation_hints extended with conflict_state for Layer 3
            extended_situation_hints = {
                **situation_hints,
                "conflict_state": emotional_state_model.conflict_state.value,  # AC-T019.3
            }

            package = ContextPackage(
                user_id=user_id,
                created_at=now,
                expires_at=now + timedelta(hours=24),
                # Pre-computed layers
                chapter_layer=chapter_layer,
                emotional_state_layer=emotional_state_layer,
                situation_hints=extended_situation_hints,
                # Context for Layer 5
                user_facts=user_facts,
                relationship_events=relationship_events,
                active_threads=active_threads_models,
                today_summary=today_summary,
                week_summaries=week_summaries,
                # Nikita's state
                nikita_mood=nikita_mood,
                nikita_energy=nikita_energy,
                life_events_today=life_events_today,
            )

            logger.info(f"Context package composed for user {user_id}")
            return package

    def _create_minimal_package(self, user_id: UUID) -> ContextPackage:
        """Create minimal package when user data unavailable.

        Args:
            user_id: User ID.

        Returns:
            Minimal ContextPackage.
        """
        now = datetime.now(timezone.utc)
        return ContextPackage(
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )

    async def _compute_emotional_state(
        self,
        user_id: UUID,
        user: Any,
    ) -> EmotionalStateModel:
        """Compute emotional state using StateComputer (Spec 023).

        AC-T019.1: PostProcessingPipeline calls StateComputer

        Args:
            user_id: User ID.
            user: User entity with chapter, relationship_score.

        Returns:
            EmotionalStateModel with conflict state.
        """
        try:
            # Get life events from simulator for emotional impact
            life_events = None
            try:
                today_events = await self.life_simulator.get_today_events(
                    user_id=user_id,
                    max_events=5,
                )
                if today_events:
                    # Convert LifeEvents to LifeEventImpact format
                    # AC-T020.1: LifeSimulator events feed into StateComputer
                    # AC-T020.2: Events with emotional_impact processed
                    from nikita.emotional_state import LifeEventImpact

                    life_events = []
                    for e in today_events:
                        # Extract deltas from EmotionalImpact model
                        if hasattr(e, "emotional_impact") and e.emotional_impact:
                            impact = e.emotional_impact
                            life_events.append(
                                LifeEventImpact(
                                    arousal_delta=impact.arousal_delta if hasattr(impact, "arousal_delta") else 0.0,
                                    valence_delta=impact.valence_delta if hasattr(impact, "valence_delta") else 0.0,
                                    dominance_delta=impact.dominance_delta if hasattr(impact, "dominance_delta") else 0.0,
                                    intimacy_delta=impact.intimacy_delta if hasattr(impact, "intimacy_delta") else 0.0,
                                )
                            )
            except Exception as e:
                logger.debug(f"Failed to get life events for emotional state: {e}")

            # Compute state via StateComputer
            emotional_state = self.state_computer.compute(
                user_id=user_id,
                chapter=user.chapter or 1,
                relationship_score=float(user.relationship_score or 50),
                life_events=life_events,
            )

            return emotional_state

        except Exception as e:
            logger.warning(f"StateComputer failed, using fallback: {e}")
            # Fallback to simple computation (legacy behavior)
            score = float(user.relationship_score or 50) / 100
            return EmotionalStateModel(
                user_id=user_id,
                arousal=0.5,
                valence=score,
                dominance=0.5,
                intimacy=score * 0.8,
            )

    def _get_time_of_day(self, dt: datetime) -> str:
        """Get time of day category.

        Args:
            dt: Datetime to categorize.

        Returns:
            Time of day string (morning, afternoon, evening, night).
        """
        hour = dt.hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _hours_since(self, past: datetime, now: datetime) -> float:
        """Calculate hours between two datetimes.

        Args:
            past: Earlier datetime.
            now: Later datetime.

        Returns:
            Hours elapsed.
        """
        delta = now - past
        return delta.total_seconds() / 3600

    async def _get_user_facts(self, user_id: UUID) -> list[str]:
        """Get user facts from memory.

        Args:
            user_id: User ID.

        Returns:
            List of user fact strings.
        """
        # TODO: Integrate with Graphiti memory
        # For now, return empty list
        return []

    async def _get_relationship_events(self, user_id: UUID) -> list[str]:
        """Get relationship events from memory.

        Args:
            user_id: User ID.

        Returns:
            List of relationship event strings.
        """
        # TODO: Integrate with Graphiti memory
        # For now, return empty list
        return []

    async def _get_today_summary(
        self,
        summary_repo: DailySummaryRepository,
        user_id: UUID,
        now: datetime,
    ) -> str | None:
        """Get today's summary.

        Args:
            summary_repo: Summary repository.
            user_id: User ID.
            now: Current datetime.

        Returns:
            Today's summary text or None.
        """
        try:
            summary = await summary_repo.get_by_date(user_id, now.date())
            if summary:
                return summary.summary_text
        except Exception as e:
            logger.warning(f"Failed to get today's summary: {e}")
        return None

    async def _get_week_summaries(
        self,
        summary_repo: DailySummaryRepository,
        user_id: UUID,
        now: datetime,
    ) -> list[str]:
        """Get week's summaries.

        Args:
            summary_repo: Summary repository.
            user_id: User ID.
            now: Current datetime.

        Returns:
            List of weekly summary strings.
        """
        try:
            week_ago = now.date() - timedelta(days=7)
            summaries = await summary_repo.get_range(user_id, week_ago, now.date())
            return [
                s.summary_text
                for s in summaries
                if s.summary_text
            ]
        except Exception as e:
            logger.warning(f"Failed to get week summaries: {e}")
        return []

    async def _get_nikita_state(
        self,
        thought_repo: NikitaThoughtRepository,
        user_id: UUID,
    ) -> tuple[EmotionalState, float]:
        """Get Nikita's simulated state from life simulation.

        Uses LifeSimulator to compute current mood based on recent events.

        Args:
            thought_repo: Thought repository (unused, kept for API compatibility).
            user_id: User ID.

        Returns:
            Tuple of (mood as EmotionalState, energy as float).
        """
        try:
            # Get mood from life simulator (based on recent events)
            mood_state = await self.life_simulator.get_current_mood(
                user_id=user_id,
                lookback_days=3,
            )

            # Convert MoodState to EmotionalState
            emotional_state = EmotionalState(
                arousal=mood_state.arousal,
                valence=mood_state.valence,
                dominance=mood_state.dominance,
                intimacy=mood_state.intimacy,
            )

            # Energy derived from arousal
            energy = mood_state.arousal

            return emotional_state, energy

        except Exception as e:
            logger.warning(f"Failed to get Nikita state from simulator: {e}")
            # Return defaults
            return EmotionalState(), 0.5

    async def _get_life_events(
        self,
        thought_repo: NikitaThoughtRepository,
        user_id: UUID,
    ) -> list[str]:
        """Get Nikita's life events today (Spec 022, T015).

        Gets top 3 events by importance from LifeSimulator and formats
        them as natural language strings.

        AC-T015.1: life_events_today field populated
        AC-T015.2: Events formatted as natural language
        AC-T015.3: Top 3 events by importance selected

        Args:
            thought_repo: Thought repository (fallback).
            user_id: User ID.

        Returns:
            List of life event strings.
        """
        try:
            # Get top 3 events by importance from life simulator
            events = await self.life_simulator.get_today_events(
                user_id=user_id,
                max_events=3,
            )

            # Format events as natural language
            formatted_events = []
            for event in events:
                # Format: "Morning: Had a productive meeting with Alex about the Q2 roadmap"
                time_of_day = (
                    event.time_of_day.value
                    if hasattr(event.time_of_day, "value")
                    else str(event.time_of_day)
                )
                formatted = f"{time_of_day.capitalize()}: {event.description}"
                formatted_events.append(formatted)

            return formatted_events

        except Exception as e:
            logger.warning(f"Failed to get life events from simulator: {e}")
            # Fallback to thought-based events
            try:
                thoughts = await thought_repo.list_active(user_id, limit=3)
                return [t.thought_text for t in thoughts if t.thought_text]
            except Exception as inner_e:
                logger.warning(f"Fallback to thoughts also failed: {inner_e}")
        return []


# Module-level singleton
_default_composer: LayerComposer | None = None


def get_layer_composer() -> LayerComposer:
    """Get the singleton LayerComposer instance.

    Returns:
        Cached LayerComposer instance.
    """
    global _default_composer
    if _default_composer is None:
        _default_composer = LayerComposer()
    return _default_composer
