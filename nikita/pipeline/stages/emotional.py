"""Emotional state stage - computes 4D mood (T2.6).

Non-critical: logs error on failure, continues.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog

from nikita.pipeline.stages.base import BaseStage
from nikita.pipeline.models import PipelineContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class EmotionalStage(BaseStage):
    """Compute emotional state from conversation and life events.

    Non-critical: failure does not stop the pipeline.
    Converts LifeEvent objects to LifeEventImpact for StateComputer,
    and maps emotional_tone string to ConversationTone enum.
    """

    name = "emotional"
    is_critical = False
    timeout_seconds = 30.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    def _wrap_session_factory(self):
        """Wrap pipeline session as a session factory for StateStore."""
        session = self._session

        @asynccontextmanager
        async def _factory():
            yield session

        return _factory

    # Default emotional state when computation fails or no data exists (Spec 045 WP-5b)
    DEFAULT_EMOTIONAL_STATE = {
        "arousal": 0.5,
        "valence": 0.5,
        "dominance": 0.5,
        "intimacy": 0.5,
    }

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Compute 4D emotional state.

        Converts ctx.life_events (LifeEvent objects from life_simulation)
        to LifeEventImpact objects expected by StateComputer. Also maps
        ctx.emotional_tone string to ConversationTone enum.

        Returns sensible defaults (0.5 for all dimensions) on failure.
        """
        try:
            from nikita.emotional_state.computer import (
                ConversationTone,
                EmotionalStateModel,
                LifeEventImpact,
                StateComputer,
            )

            computer = StateComputer()

            # Build base state from defaults
            base = EmotionalStateModel(user_id=ctx.user_id)

            # Convert LifeEvent objects to LifeEventImpact for StateComputer
            life_impacts = None
            if ctx.life_events:
                life_impacts = []
                for e in ctx.life_events:
                    ei = getattr(e, "emotional_impact", None)
                    if ei is not None:
                        life_impacts.append(
                            LifeEventImpact(
                                arousal_delta=getattr(ei, "arousal_delta", 0.0),
                                valence_delta=getattr(ei, "valence_delta", 0.0),
                                dominance_delta=getattr(ei, "dominance_delta", 0.0),
                                intimacy_delta=getattr(ei, "intimacy_delta", 0.0),
                            )
                        )
                if not life_impacts:
                    life_impacts = None

            # Map emotional_tone string to ConversationTone enum
            conversation_tones = None
            tone_str = getattr(ctx, "emotional_tone", None) or ""
            if tone_str and tone_str != "neutral":
                try:
                    conversation_tones = [ConversationTone(tone_str)]
                except ValueError:
                    logger.debug("unknown_conversation_tone", tone=tone_str)

            state = computer.compute(
                user_id=ctx.user_id,
                current_state=base,
                life_events=life_impacts,
                conversation_tones=conversation_tones,
                chapter=ctx.chapter,
                relationship_score=float(ctx.relationship_score),
            )

            ctx.emotional_state = {
                "arousal": state.arousal,
                "valence": state.valence,
                "dominance": state.dominance,
                "intimacy": state.intimacy,
            }

            # Persist computed emotional state to DB (wires nikita_emotional_states table)
            if self._session is not None:
                try:
                    from nikita.emotional_state.store import StateStore

                    store = StateStore(session_factory=self._wrap_session_factory())
                    await store.save_state(state)
                    logger.info(
                        "emotional_state_persisted",
                        user_id=str(ctx.user_id),
                        arousal=state.arousal,
                        valence=state.valence,
                    )
                except Exception as persist_err:
                    logger.warning("emotional_state_persist_failed", error=str(persist_err))

        except Exception as e:
            logger.error("emotional_computation_failed", exc_info=True)
            ctx.emotional_state = dict(self.DEFAULT_EMOTIONAL_STATE)

        # Ensure we always have a valid emotional state (Spec 045 WP-5b)
        if not ctx.emotional_state:
            ctx.emotional_state = dict(self.DEFAULT_EMOTIONAL_STATE)

        # Spec 057: Load conflict_details from DB for ConflictStage
        if self._session is not None:
            try:
                from nikita.conflicts.persistence import load_conflict_details

                details = await load_conflict_details(ctx.user_id, self._session)
                if details:
                    ctx.conflict_details = details
                    logger.info(
                        "conflict_details_loaded",
                        temperature=details.get("temperature", 0),
                        zone=details.get("zone", "calm"),
                    )
            except Exception as e:
                logger.warning("conflict_details_load_failed", error=str(e))

        return ctx.emotional_state
