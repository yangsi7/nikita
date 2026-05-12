"""Spec 218 Slice 218-6 — Phase-2 completion gate unit tests (RED).

Covers the Phase-2 gate contract: FR-008 (min 4, max 8 turns).
These tests focus on the gate boundary conditions; they do NOT re-test the
Phase-1 FinalForm gate (per R13 from plan: slot-extension slices re-test
only new surfaces).

Gate function: `phase_2_gate(state, agent_signals_done) -> (complete, forced)`
- complete: bool — whether Phase-2 should transition to `complete`
- forced: bool — True when min-floor retry or max-ceiling forced (FR-008)
"""

from __future__ import annotations

import pytest

from nikita.agents.onboarding.v2.research_agent import phase_2_gate
from nikita.agents.onboarding.v2.state import (
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    Phase,
    WizardSlotsV2,
    WizardStateV2,
)


def _phase2_state(
    turn_count: int, phase: Phase = Phase.phase2
) -> WizardStateV2:
    return WizardStateV2(
        slots=WizardSlotsV2(
            display_name={"display_name": "Alice"},
            age={"age": 22},
            city={"city": "Tokyo"},
            occupation={"occupation": "Designer"},
            primary_hobbies={"primary_hobbies": ["art", "yoga"]},
            hangouts_personalized={"hangouts_personalized": ["cafes", "parks"]},
            voice_or_text={"voice_or_text": "text"},
            saturday_morning={"saturday_morning": "slow morning walks"},
            darkness_level={"darkness_level": 2},
            geek_out_on={"geek_out_on": "typography"},
        ),
        phase=phase,
        phase_2_turn_count=turn_count,
        phase_2_started_at="2026-05-12T00:00:00Z",
    )


class TestMinFloorBoundary:
    """Turns 0..PHASE_2_MIN_TURNS-1 must never complete, even if agent wants to."""

    @pytest.mark.parametrize("count", list(range(PHASE_2_MIN_TURNS)))
    def test_not_complete_before_min(self, count: int) -> None:
        state = _phase2_state(count)
        complete, forced = phase_2_gate(state, agent_signals_done=True)
        assert complete is False
        assert forced is True, (
            f"expected forced=True at count={count} (min-floor retry)"
        )

    def test_complete_at_exactly_min_with_agent_done(self) -> None:
        state = _phase2_state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=True)
        assert complete is True
        assert forced is False

    def test_not_complete_at_exactly_min_without_agent_done(self) -> None:
        state = _phase2_state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is False
        assert forced is False


class TestMidRange:
    """Turns PHASE_2_MIN_TURNS+1 .. PHASE_2_MAX_TURNS-1: agent decides."""

    @pytest.mark.parametrize(
        "count", list(range(PHASE_2_MIN_TURNS + 1, PHASE_2_MAX_TURNS))
    )
    def test_complete_if_agent_signals(self, count: int) -> None:
        state = _phase2_state(count)
        complete, forced = phase_2_gate(state, agent_signals_done=True)
        assert complete is True
        assert forced is False

    @pytest.mark.parametrize(
        "count", list(range(PHASE_2_MIN_TURNS + 1, PHASE_2_MAX_TURNS))
    )
    def test_not_complete_if_agent_continues(self, count: int) -> None:
        state = _phase2_state(count)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is False
        assert forced is False


class TestMaxCeilingBoundary:
    """At PHASE_2_MAX_TURNS or beyond: always complete, always forced."""

    def test_forced_at_max(self) -> None:
        state = _phase2_state(PHASE_2_MAX_TURNS)
        for agent_done in (True, False):
            complete, forced = phase_2_gate(state, agent_signals_done=agent_done)
            assert complete is True
            assert forced is True, (
                f"expected forced=True at max turns with agent_signals_done={agent_done}"
            )

    @pytest.mark.parametrize("count", [PHASE_2_MAX_TURNS + 1, PHASE_2_MAX_TURNS + 5])
    def test_forced_beyond_max(self, count: int) -> None:
        state = _phase2_state(count)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is True
        assert forced is True
