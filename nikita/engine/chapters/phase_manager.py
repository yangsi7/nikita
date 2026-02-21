"""Boss Phase Manager for multi-phase boss encounters (Spec 058).

Manages the lifecycle of a 2-phase boss encounter:
  OPENING -> RESOLUTION -> judgment

Phase state is persisted in conflict_details.boss_phase JSONB.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from nikita.engine.chapters.boss import BossPhase, BossPhaseState

logger = logging.getLogger(__name__)

# Boss encounter timeout (24 hours)
BOSS_TIMEOUT_HOURS = 24


class BossPhaseManager:
    """Central class for boss phase lifecycle management (Spec 058).

    Methods:
        start_boss: Create OPENING phase state.
        advance_phase: Transition OPENING -> RESOLUTION, append history.
        is_resolution_complete: Check if RESOLUTION phase is done.
        is_timed_out: Check if boss has exceeded 24h timeout.
        persist_phase: Write phase state into conflict_details dict.
        load_phase: Read phase state from conflict_details dict.
    """

    # ── Phase lifecycle ──────────────────────────────────────────────

    def start_boss(self, chapter: int) -> BossPhaseState:
        """Create a new boss encounter in OPENING phase.

        Args:
            chapter: Current chapter (1-5).

        Returns:
            BossPhaseState in OPENING phase.
        """
        return BossPhaseState(
            phase=BossPhase.OPENING,
            chapter=chapter,
            started_at=datetime.now(UTC),
            turn_count=0,
            conversation_history=[],
        )

    def advance_phase(
        self,
        state: BossPhaseState,
        user_message: str,
        nikita_response: str,
    ) -> BossPhaseState:
        """Advance boss from OPENING -> RESOLUTION.

        Appends user message and Nikita response to conversation history,
        increments turn_count, and transitions phase.

        Args:
            state: Current boss phase state (must be OPENING).
            user_message: Player's response to OPENING challenge.
            nikita_response: Nikita's response/prompt for next phase.

        Returns:
            Updated BossPhaseState in RESOLUTION phase.
        """
        new_history = list(state.conversation_history)
        new_history.append({"role": "user", "content": user_message})
        new_history.append({"role": "assistant", "content": nikita_response})

        return BossPhaseState(
            phase=BossPhase.RESOLUTION,
            chapter=state.chapter,
            started_at=datetime.now(UTC),  # Reset timeout for per-phase 24h (R-6)
            turn_count=state.turn_count + 1,
            conversation_history=new_history,
        )

    def is_resolution_complete(self, state: BossPhaseState) -> bool:
        """Check if RESOLUTION phase has enough turns for judgment.

        Args:
            state: Current boss phase state.

        Returns:
            True when phase=RESOLUTION and turn_count >= 2.
        """
        return state.phase == BossPhase.RESOLUTION and state.turn_count >= 2

    # ── Timeout ──────────────────────────────────────────────────────

    def is_timed_out(
        self,
        state: BossPhaseState,
        now: datetime | None = None,
    ) -> bool:
        """Check if boss encounter has exceeded 24h timeout.

        Args:
            state: Current boss phase state.
            now: Current time (defaults to utcnow for testing).

        Returns:
            True if (now - started_at) > 24 hours.
        """
        if now is None:
            now = datetime.now(UTC)
        elapsed = now - state.started_at
        return elapsed > timedelta(hours=BOSS_TIMEOUT_HOURS)

    # ── Persistence ──────────────────────────────────────────────────

    @staticmethod
    def persist_phase(
        conflict_details: dict[str, Any] | None,
        state: BossPhaseState,
    ) -> dict[str, Any]:
        """Write boss phase state into conflict_details dict.

        Args:
            conflict_details: Existing conflict_details JSONB (may be None).
            state: Boss phase state to persist.

        Returns:
            Updated conflict_details dict with boss_phase set.
        """
        if conflict_details is None:
            conflict_details = {}
        conflict_details["boss_phase"] = state.model_dump(mode="json")
        return conflict_details

    @staticmethod
    def load_phase(
        conflict_details: dict[str, Any] | None,
    ) -> BossPhaseState | None:
        """Read boss phase state from conflict_details dict.

        Args:
            conflict_details: conflict_details JSONB from database.

        Returns:
            BossPhaseState if present and valid, None otherwise.
        """
        if not conflict_details:
            return None

        boss_phase_data = conflict_details.get("boss_phase")
        if not boss_phase_data:
            return None

        try:
            return BossPhaseState.model_validate(boss_phase_data)
        except Exception:
            logger.warning(
                "Failed to parse boss_phase from conflict_details, "
                "returning None for graceful degradation",
                exc_info=True,
            )
            return None

    @staticmethod
    def clear_boss_phase(
        conflict_details: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Clear boss phase from conflict_details (boss complete).

        Args:
            conflict_details: Existing conflict_details JSONB.

        Returns:
            Updated conflict_details dict with boss_phase set to None.
        """
        if conflict_details is None:
            conflict_details = {}
        conflict_details["boss_phase"] = None
        return conflict_details
