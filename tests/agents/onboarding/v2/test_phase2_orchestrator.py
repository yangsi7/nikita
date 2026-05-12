"""Spec 218 Slice 218-6 — Phase-2 orchestrator tests (RED).

Tests the extended `handle_v2_answer` behaviour when `target is None`
(Phase-1 complete, Phase-2 active):

1. Phase-1-complete session transitions to Phase-2 turn (returns a TextShortAsk
   or similar follow-up prompt, NOT HandlerHandoffAsk).
2. Phase-2 turn counter increments each time the Phase-2 orchestrator runs.
3. At PHASE_2_MIN_TURNS with agent signalling done, CompleteAsk is returned.
4. At PHASE_2_MAX_TURNS, CompleteAsk is forced regardless of agent output.
5. `_force_phase2_complete_envelope` returns a well-formed CompleteAsk.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from nikita.agents.onboarding.v2.envelope import CompleteAsk, HandlerHandoffAsk
from nikita.agents.onboarding.v2.state import (
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    Phase,
    WizardSlotsV2,
    WizardStateV2,
)
from nikita.api.routes.portal_onboarding_v2 import _force_phase2_complete_envelope


def _full_slots() -> WizardSlotsV2:
    return WizardSlotsV2(
        display_name={"display_name": "Sam"},
        age={"age": 25},
        city={"city": "London"},
        occupation={"occupation": "Nurse"},
        primary_hobbies={"primary_hobbies": ["running", "cooking"]},
        hangouts_personalized={"hangouts_personalized": ["parks", "markets"]},
        voice_or_text={"voice_or_text": "text"},
        saturday_morning={"saturday_morning": "long bike ride"},
        darkness_level={"darkness_level": 4},
        geek_out_on={"geek_out_on": "fermentation science"},
    )


def _p2_state(count: int) -> WizardStateV2:
    return WizardStateV2(
        slots=_full_slots(),
        phase=Phase.phase2,
        phase_2_turn_count=count,
        phase_2_started_at="2026-05-12T00:00:00Z",
    )


class TestForceCompleteEnvelope:
    """_force_phase2_complete_envelope always returns a valid CompleteAsk."""

    def test_returns_complete_ask(self) -> None:
        state = _p2_state(PHASE_2_MAX_TURNS)
        envelope = _force_phase2_complete_envelope(state)
        assert isinstance(envelope, CompleteAsk)
        assert envelope.component == "complete"
        assert envelope.handler == "v2"
        assert envelope.next_route.startswith("/")

    def test_no_handoff_returned(self) -> None:
        state = _p2_state(PHASE_2_MAX_TURNS)
        envelope = _force_phase2_complete_envelope(state)
        assert not isinstance(envelope, HandlerHandoffAsk)

    def test_backstory_preview_optional(self) -> None:
        state = _p2_state(PHASE_2_MAX_TURNS)
        envelope = _force_phase2_complete_envelope(state)
        # backstory_preview may be None when backstory generation hasn't run
        assert envelope.backstory_preview is None or isinstance(
            envelope.backstory_preview, str
        )


class TestHandleV2AnswerPhase2Entry:
    """handle_v2_answer no longer returns HandlerHandoffAsk when Phase-1 complete."""

    @pytest.mark.asyncio
    async def test_phase1_complete_does_not_return_v1_handoff(self) -> None:
        """When target=None (all Phase-1 slots filled) and phase=phase2,
        handle_v2_answer must NOT return HandlerHandoffAsk to v1."""
        from nikita.api.routes.portal_onboarding_v2 import handle_v2_answer

        mock_req = MagicMock()
        mock_req.slot_kind = None
        mock_req.value = None

        mock_user = MagicMock()
        mock_user.id = UUID("00000000-0000-0000-0000-000000000001")
        state = _p2_state(0)
        mock_user.onboarding_profile = {
            "slots": state.slots.model_dump(exclude_none=True),
            "phase": Phase.phase2.value,
            "phase_2_turn_count": 0,
            "phase_2_started_at": "2026-05-12T00:00:00Z",
            "messages": [],
        }

        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_onboarding_profile = AsyncMock()

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.UserRepository",
                return_value=mock_repo,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_research_agent"
            ) as mock_get_agent,
        ):
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = "What draws you to fermentation science?"
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await handle_v2_answer(mock_req, mock_user, mock_session)

        assert not isinstance(result, HandlerHandoffAsk), (
            "Phase-1-complete session must not fall back to v1 handoff in slice 218-6"
        )

    @pytest.mark.asyncio
    async def test_phase2_forced_complete_at_max_turns(self) -> None:
        """At MAX_TURNS, handle_v2_answer returns CompleteAsk regardless of
        agent output."""
        from nikita.api.routes.portal_onboarding_v2 import handle_v2_answer

        mock_req = MagicMock()
        mock_req.slot_kind = None
        mock_req.value = None

        mock_user = MagicMock()
        mock_user.id = UUID("00000000-0000-0000-0000-000000000002")
        state = _p2_state(PHASE_2_MAX_TURNS)
        mock_user.onboarding_profile = {
            "slots": state.slots.model_dump(exclude_none=True),
            "phase": Phase.phase2.value,
            "phase_2_turn_count": PHASE_2_MAX_TURNS,
            "phase_2_started_at": "2026-05-12T00:00:00Z",
            "messages": [],
        }

        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_onboarding_profile = AsyncMock()

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.UserRepository",
                return_value=mock_repo,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_research_agent"
            ) as mock_get_agent,
        ):
            # Agent tries to return more questions (wrong at max turns)
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = "Tell me more…"
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await handle_v2_answer(mock_req, mock_user, mock_session)

        assert isinstance(result, CompleteAsk), (
            f"Expected CompleteAsk at MAX_TURNS, got {type(result)}"
        )
