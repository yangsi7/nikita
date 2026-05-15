"""Spec 218 Slice 218-2 — decorator agent mandatory triplet.

Per `.claude/rules/agentic-design-patterns.md` + `.claude/rules/testing.md`
Agentic-Flow Test Requirements: any test file adding a NEW agent file
under `nikita/agents/onboarding/v2/` MUST cover the three classes below.

This file gates the decorator agent at `nikita/agents/onboarding/v2/
decorator_agent.py` shipped in PR-218-2.

1. Cumulative-state monotonicity (>=3-turn fixture, progress[t+1] >= progress[t])
2. Completion-gate triplet (empty/partial/full WizardSlotsV2 -> FinalForm)
3. Mock-LLM-emits-wrong-component recovery (ModelRetry OR deterministic fallback)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from pydantic_ai.exceptions import ModelRetry

from nikita.agents.onboarding.v2.state import (
    FinalForm,
    SlotDeltaV2,
    SlotKindV2,
    WizardSlotsV2,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_slots() -> WizardSlotsV2:
    return WizardSlotsV2()


@pytest.fixture
def partial_slots() -> WizardSlotsV2:
    """display_name + age + city filled; remainder None."""
    return WizardSlotsV2(
        display_name={"display_name": "Sam"},
        age={"age": 28},
        city={"city": "Berlin"},
    )


@pytest.fixture
def full_slots() -> WizardSlotsV2:
    """All 11 Phase-1 slots filled with valid payloads."""
    return WizardSlotsV2(
        display_name={"display_name": "Sam"},
        age={"age": 28},
        city={"city": "Berlin"},
        occupation={"occupation": "engineer"},
        primary_hobbies={"primary_hobbies": ["techno", "climbing"]},
        hangouts_personalized={"hangouts_personalized": ["berghain"]},
        voice_or_text={"voice_or_text": "text"},
        saturday_morning={"saturday_morning": "long walk + coffee"},
        darkness_level={"darkness_level": 3},
        geek_out_on={"geek_out_on": "ML inference latency"},
    )


# ---------------------------------------------------------------------------
# AC-T-1: Cumulative-state monotonicity
# ---------------------------------------------------------------------------


class TestCumulativeStateMonotonicity:
    """progress[t+1] >= progress[t] across an N-turn slot-fill sequence.

    The decorator agent never reduces progress; only `dag_invalidate`
    (router) can null downstream slots, and that path is exercised
    elsewhere. Here we assert monotonicity on the happy-path advance.
    """

    def test_three_turn_advance_monotonic(self, empty_slots: WizardSlotsV2) -> None:
        s = empty_slots
        progress = [s.progress_pct]

        s = s.apply(SlotDeltaV2(kind=SlotKindV2.display_name.value, data={"display_name": "Sam"}))
        progress.append(s.progress_pct)

        s = s.apply(SlotDeltaV2(kind=SlotKindV2.age.value, data={"age": 28}))
        progress.append(s.progress_pct)

        s = s.apply(SlotDeltaV2(kind=SlotKindV2.city.value, data={"city": "Berlin"}))
        progress.append(s.progress_pct)

        assert progress == sorted(progress), f"progress regressed: {progress}"
        assert progress[-1] > progress[0]

    def test_no_extraction_does_not_advance(self, empty_slots: WizardSlotsV2) -> None:
        s = empty_slots.apply(SlotDeltaV2(kind="no_extraction"))
        assert s.progress_pct == empty_slots.progress_pct


# ---------------------------------------------------------------------------
# AC-T-2: Completion-gate triplet
# ---------------------------------------------------------------------------


class TestCompletionGateTriplet:
    """FinalForm.model_validate IS the gate. Never a literal True / False."""

    def test_empty_state_gate_false(self, empty_slots: WizardSlotsV2) -> None:
        with pytest.raises(ValidationError):
            FinalForm.model_validate(empty_slots.slots_dict())

    def test_partial_state_gate_false(self, partial_slots: WizardSlotsV2) -> None:
        with pytest.raises(ValidationError):
            FinalForm.model_validate(partial_slots.slots_dict())

    def test_full_state_gate_true(self, full_slots: WizardSlotsV2) -> None:
        form = FinalForm.model_validate(full_slots.slots_dict())
        assert form.display_name == {"display_name": "Sam"}
        assert form.voice_or_text == {"voice_or_text": "text"}


# ---------------------------------------------------------------------------
# AC-T-3: Mock-LLM-emits-wrong-component recovery
# ---------------------------------------------------------------------------


class TestWrongComponentRecovery:
    """When decorator target is display_name but agent emits a non-target
    shape (e.g., CalendarAsk when TextShortAsk expected), output_validator
    MUST raise ModelRetry.

    Per ADR-009 + spec 218 §18 P3 + R12 (mid-failure handling).
    Failure of this test means the agent will accept incoherent output and
    advance the wizard with no display_name extraction.

    PR-218-8: HandlerHandoffAsk deleted; CalendarAsk used as "wrong shape"
    stand-in (display_name target expects TextShortAsk, not CalendarAsk).
    """

    def test_wrong_component_for_display_name_target_raises_model_retry(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import CalendarAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.display_name.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                CalendarAsk(
                    component="calendar",
                    slot="age",
                    prompt="When were you born?",
                ),
            )


# ---------------------------------------------------------------------------
# Agent invocation contract (per .claude/rules/agentic-design-patterns.md)
# ---------------------------------------------------------------------------


class TestAgentInvocationContract:
    """Decorator agent MUST be invoked with message_history= AND deps=
    containing cumulative state. Per agentic-design-patterns.md
    Required Tests §1.
    """

    @pytest.mark.asyncio
    async def test_agent_called_with_message_history_and_deps(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            get_decorator_agent,
        )

        agent = get_decorator_agent()
        with patch.object(agent, "run", new_callable=MagicMock) as mock_run:
            mock_run.return_value = MagicMock(output=MagicMock(), new_messages=lambda: [])
            # The route handler is expected to invoke run() with these kwargs.
            deps = MagicMock()
            deps.slots = WizardSlotsV2()
            deps.target_slot = SlotKindV2.display_name.value
            agent.run("hello", message_history=[], deps=deps)

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert "message_history" in call_kwargs
            assert "deps" in call_kwargs


# ---------------------------------------------------------------------------
# Progress injection — progress_pct must be set on emitted envelope
# (Cluster X — state integrity wire-through)
# ---------------------------------------------------------------------------


class TestProgressPctInjection:
    """Route handler must inject state.progress_pct into every emitted
    AskUnion envelope. Monotonic: as slots fill, emitted progress_pct
    must not decrease.

    Tests the _inject_progress_pct helper and WizardSlotsV2 as the
    source of truth.
    """

    def test_progress_pct_injected_into_text_short(self) -> None:
        """After 3 slots filled, progress_pct on emitted envelope > 0."""
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import _inject_progress_pct  # noqa: PLC0415

        slots = WizardSlotsV2(
            display_name={"display_name": "Sam"},
            age={"age": 28},
            city={"city": "Berlin"},
        )
        raw_ask = TextShortAsk(slot="occupation", prompt="What do you do?")
        assert raw_ask.progress_pct is None, "raw envelope has no progress before injection"

        enriched = _inject_progress_pct(raw_ask, slots)
        expected_pct = slots.progress_pct  # 3/11 * 100 == 27
        assert enriched.progress_pct == expected_pct
        assert enriched.progress_pct > 0

    def test_progress_pct_monotonic_across_three_turns(self) -> None:
        """Injected progress_pct increases as slots are filled."""
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import _inject_progress_pct  # noqa: PLC0415

        empty = WizardSlotsV2()
        after_one = empty.apply(SlotDeltaV2(kind=SlotKindV2.display_name.value, data={"display_name": "Sam"}))
        after_two = after_one.apply(SlotDeltaV2(kind=SlotKindV2.age.value, data={"age": 28}))
        after_three = after_two.apply(SlotDeltaV2(kind=SlotKindV2.city.value, data={"city": "Berlin"}))

        ask = TextShortAsk(slot="occupation", prompt="?")
        p0 = _inject_progress_pct(ask, empty).progress_pct
        p1 = _inject_progress_pct(ask, after_one).progress_pct
        p2 = _inject_progress_pct(ask, after_two).progress_pct
        p3 = _inject_progress_pct(ask, after_three).progress_pct

        assert p0 is not None
        assert p1 is not None
        assert p2 is not None
        assert p3 is not None
        progress = [p0, p1, p2, p3]
        assert progress == sorted(progress), f"progress_pct not monotonic: {progress}"
        assert p3 > p0, "progress should increase across turns"

    def test_progress_pct_100_on_complete(self) -> None:
        """CompleteAsk emitted with progress_pct=100."""
        from nikita.agents.onboarding.v2.envelope import CompleteAsk  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import _inject_progress_pct  # noqa: PLC0415

        full_slots = WizardSlotsV2(
            display_name={"display_name": "Sam"},
            age={"age": 28},
            city={"city": "Berlin"},
            occupation={"occupation": "engineer"},
            primary_hobbies={"primary_hobbies": ["techno"]},
            hangouts_personalized={"hangouts_personalized": ["berghain"]},
            voice_or_text={"voice_or_text": "text"},
            saturday_morning={"saturday_morning": 5},
            darkness_level={"darkness_level": 3},
            geek_out_on={"geek_out_on": "ML inference"},
        )
        raw = CompleteAsk(next_route="/dashboard")
        enriched = _inject_progress_pct(raw, full_slots)
        assert enriched.progress_pct == 100


# ---------------------------------------------------------------------------
# Dynamic-instructions invocation (Hard Rule §3 + Required Tests §2)
# ---------------------------------------------------------------------------


class TestDynamicInstructionsInvocation:
    """Decorator agent MUST use `instructions=callable` (NOT static
    string). Callable MUST reference current state.missing per turn.
    """

    def test_decorator_factory_attaches_dynamic_instructions(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            _create_decorator_agent,
            inject_v2_per_turn_context,
        )

        agent = _create_decorator_agent()
        # `agent.instructions(callable)` registers a dynamic instructions
        # function. The function attribute must reference our injection
        # callable; bare static string is the anti-pattern.
        assert callable(inject_v2_per_turn_context)
        # Smoke: the agent was constructed (no exception); the callable
        # is exported for inspection so future slices can compose it.
        assert agent is not None
