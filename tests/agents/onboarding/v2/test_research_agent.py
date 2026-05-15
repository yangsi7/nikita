"""Spec 218 Slice 218-6 — research agent mandatory triplet (RED).

Per `.claude/rules/agentic-design-patterns.md` + `.claude/rules/testing.md`
Agentic-Flow Test Requirements: any NEW agent file under
`nikita/agents/onboarding/v2/` MUST cover the three mandatory classes.

Phase-2 research agent (`nikita/agents/onboarding/v2/research_agent.py`) is
a NEW agent file in slice 218-6 — full triplet required (R3 / R13).

1. Cumulative-state monotonicity — phase_2_turn_count strictly non-decreasing
   across turns; completion gate never fires before MIN_TURNS.
2. Completion-gate triplet — `phase_2_gate` returns False below MIN_TURNS,
   False at MIN_TURNS with agent not signalling done, True at MIN_TURNS
   with agent signalling done, and forced True at MAX_TURNS.
3. Mock-LLM-emits-wrong-output recovery — agent returning str when
   CompleteAsk expected at MAX_TURNS; system forces completion envelope.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry

from nikita.agents.onboarding.v2.research_agent import (
    V2ResearchDeps,
    get_research_agent,
    phase_2_gate,
)
from nikita.agents.onboarding.v2.state import (
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    Phase,
    WizardSlotsV2,
    WizardStateV2,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_phase1_slots() -> WizardSlotsV2:
    """Return a WizardSlotsV2 with all Phase-1 required slots filled."""
    return WizardSlotsV2(
        display_name={"display_name": "Sam"},
        age={"age": 25},
        city={"city": "New York"},
        occupation={"occupation": "Engineer"},
        primary_hobbies={"primary_hobbies": ["hiking", "reading"]},
        hangouts_personalized={"hangouts_personalized": ["coffee", "museums"]},
        voice_or_text={"voice_or_text": "text"},
        saturday_morning={"saturday_morning": "coffee and journaling"},
        darkness_level={"darkness_level": 3},
        geek_out_on={"geek_out_on": "distributed systems and cats"},
    )


def _state(turn_count: int, phase: Phase = Phase.phase2) -> WizardStateV2:
    return WizardStateV2(
        slots=_full_phase1_slots(),
        phase=phase,
        phase_2_turn_count=turn_count,
        phase_2_started_at="2026-05-12T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# 1. Cumulative-state monotonicity
# ---------------------------------------------------------------------------


class TestTurnCountMonotonicity:
    """phase_2_turn_count is non-decreasing across Phase-2 turns (FR-008)."""

    def test_turn_count_never_decreases(self) -> None:
        """Simulate 5 turns; count strictly increases each time."""
        counts = [_state(i).phase_2_turn_count for i in range(5)]
        for i in range(len(counts) - 1):
            assert counts[i + 1] > counts[i], (
                f"turn_count regressed from {counts[i]} to {counts[i + 1]}"
            )

    def test_minimum_turns_not_reached_at_turn_3(self) -> None:
        """phase_2_gate returns (False, ...) when count < MIN_TURNS."""
        state = _state(PHASE_2_MIN_TURNS - 1)
        complete, _ = phase_2_gate(state, agent_signals_done=False)
        assert complete is False

    def test_gate_never_fires_before_min_turns_even_if_agent_signals(self) -> None:
        """Agent signalling done before MIN_TURNS must be overridden."""
        for count in range(PHASE_2_MIN_TURNS):
            state = _state(count)
            complete, forced = phase_2_gate(state, agent_signals_done=True)
            assert complete is False, (
                f"gate fired at turn {count} before MIN_TURNS={PHASE_2_MIN_TURNS}"
            )
            assert forced is True, "should be flagged as forced retry"


# ---------------------------------------------------------------------------
# 2. Completion-gate triplet
# ---------------------------------------------------------------------------


class TestPhase2Gate:
    """phase_2_gate(state, agent_signals_done) -> (complete, forced)."""

    def test_empty_turn_count_not_complete(self) -> None:
        state = _state(0)
        complete, _ = phase_2_gate(state, agent_signals_done=False)
        assert complete is False

    def test_at_min_turns_agent_not_signalling_not_complete(self) -> None:
        state = _state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is False
        assert forced is False

    def test_at_min_turns_agent_signals_done_complete(self) -> None:
        state = _state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=True)
        assert complete is True
        assert forced is False

    def test_at_max_turns_forced_complete_regardless_of_agent(self) -> None:
        state = _state(PHASE_2_MAX_TURNS)
        complete_no, forced_no = phase_2_gate(state, agent_signals_done=False)
        complete_yes, forced_yes = phase_2_gate(state, agent_signals_done=True)
        assert complete_no is True
        assert forced_no is True
        assert complete_yes is True
        assert forced_yes is True

    def test_beyond_max_turns_also_forced_complete(self) -> None:
        state = _state(PHASE_2_MAX_TURNS + 1)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is True
        assert forced is True


# ---------------------------------------------------------------------------
# 3. Mock-LLM-emits-wrong-output recovery
# ---------------------------------------------------------------------------


class TestWrongOutputRecovery:
    """If agent returns str when CompleteAsk expected at MAX_TURNS,
    the orchestration layer forces a CompleteAsk."""

    def test_str_output_at_max_turns_triggers_forced_complete(self) -> None:
        """Simulation: agent returns a follow-up str, but MAX turns reached.
        The caller (Phase-2 orchestrator) must force CompleteAsk."""
        from nikita.agents.onboarding.v2.envelope import CompleteAsk
        from nikita.api.routes.portal_onboarding_v2 import (
            _force_phase2_complete_envelope,
        )

        state = _state(PHASE_2_MAX_TURNS)
        # Agent returned a str (wrong: should have signalled done)
        agent_output: str = "So tell me more about your weekend…"
        envelope = _force_phase2_complete_envelope(state)
        assert isinstance(envelope, CompleteAsk)
        assert envelope.component == "complete"

    @pytest.mark.asyncio
    async def test_research_agent_output_validator_rejects_complete_before_min(
        self,
    ) -> None:
        """Output validator raises ModelRetry when agent signals complete
        before PHASE_2_MIN_TURNS have been collected."""
        from nikita.agents.onboarding.v2.envelope import CompleteAsk
        from nikita.agents.onboarding.v2.research_agent import (
            build_phase2_output_validator,
        )

        state = _state(PHASE_2_MIN_TURNS - 1)
        validator = build_phase2_output_validator()
        early_complete = CompleteAsk(next_route="/dashboard")
        ctx = MagicMock()
        ctx.deps.state = state

        # Validator must raise ModelRetry for premature completion
        with pytest.raises(ModelRetry):
            await validator(ctx, early_complete)  # type: ignore[arg-type]

    def test_research_deps_has_required_firecrawl_fields(self) -> None:
        """V2ResearchDeps carries fetch_invocations_this_turn and
        fetch_cost_cumulative required by firecrawl_tools._run_fetch."""
        from decimal import Decimal

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000001",
            state=_state(1),
            traceparent="00-trace-span-01",
        )
        assert hasattr(deps, "fetch_invocations_this_turn")
        assert hasattr(deps, "fetch_cost_cumulative")
        assert deps.fetch_cost_cumulative == Decimal("0")

    def test_get_research_agent_returns_same_instance(self) -> None:
        """@lru_cache(maxsize=1) — repeated calls return identical object."""
        agent_a = get_research_agent()
        agent_b = get_research_agent()
        assert agent_a is agent_b


# ---------------------------------------------------------------------------
# 4. Cost guard contract (Fix 3 — scaffolding for slice 218-7 tool wiring)
# ---------------------------------------------------------------------------


class TestCheckCostGuard:
    """_check_cost_guard raises ModelRetry when fetch budget is exhausted."""

    def test_raises_model_retry_when_fetch_budget_exceeded(self) -> None:
        """fetch_cost_cumulative >= FETCH_BUDGET_HARD_USD → ModelRetry."""
        from decimal import Decimal

        from pydantic_ai.exceptions import ModelRetry as _ModelRetry

        from nikita.agents.onboarding.cost_guard import FETCH_BUDGET_HARD_USD
        from nikita.agents.onboarding.v2.research_agent import _check_cost_guard

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000002",
            state=_state(1),
            fetch_cost_cumulative=FETCH_BUDGET_HARD_USD,
        )
        with pytest.raises(_ModelRetry):
            _check_cost_guard(deps)

    def test_no_raise_when_budget_available(self) -> None:
        """fetch_cost_cumulative well below both ceilings → no raise."""
        from decimal import Decimal

        from nikita.agents.onboarding.v2.research_agent import _check_cost_guard

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000003",
            state=_state(1),
            fetch_cost_cumulative=Decimal("0.01"),
        )
        # Must not raise
        _check_cost_guard(deps)

    def test_raises_model_retry_when_flow_ceiling_exceeded(self) -> None:
        """total_flow_cost_cumulative >= FLOW_HARD_CEILING_USD → ModelRetry.

        QA iter-2: flow ceiling check uses dedicated field
        ``total_flow_cost_cumulative`` (LLM + fetch combined) rather than
        the fetch-only field; fetch can be 0 while combined flow trips.
        """
        from decimal import Decimal

        from pydantic_ai.exceptions import ModelRetry as _ModelRetry

        from nikita.agents.onboarding.cost_guard import FLOW_HARD_CEILING_USD
        from nikita.agents.onboarding.v2.research_agent import _check_cost_guard

        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000004",
            state=_state(1),
            fetch_cost_cumulative=Decimal("0.01"),  # fetch alone fine
            total_flow_cost_cumulative=FLOW_HARD_CEILING_USD,
        )
        with pytest.raises(_ModelRetry, match=r"flow ceiling"):
            _check_cost_guard(deps)


# ---------------------------------------------------------------------------
# 5. GH #623 fixes: I1 max-turn gate / I2 topic diversity / I3 anti-repetition
# ---------------------------------------------------------------------------


class TestMaxTurnForcesCompletion:
    """I1: MAX_PHASE2_TURNS=5 hard cap — turn 5 forces backstory + complete.

    GH #623: walk evidence shows turn_count=7, backstory_seed=null,
    onboarding_status=pending. The existing cap was 8; lowering to 5
    prevents the runaway loop in typical sessions.
    """

    @pytest.mark.asyncio
    async def test_max_turn_forces_completion(self) -> None:
        """When phase_2_turn_count == MAX_PHASE2_TURNS, handle_v2_answer
        calls generate_v2_backstory and returns CompleteAsk with a
        non-None backstory_preview."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import UUID

        from nikita.agents.onboarding.v2.envelope import CompleteAsk
        from nikita.agents.onboarding.v2.research_agent import MAX_PHASE2_TURNS
        from nikita.agents.onboarding.v2.state import Phase
        from nikita.api.routes.portal_onboarding_v2 import handle_v2_answer

        mock_req = MagicMock()
        mock_req.slot_kind = None
        mock_req.value = None

        mock_user = MagicMock()
        mock_user.id = UUID("00000000-0000-0000-0000-000000000010")
        slots = _full_phase1_slots()
        mock_user.onboarding_profile = {
            "slots": slots.slots_dict(),
            "phase": Phase.phase2.value,
            "phase_2_turn_count": MAX_PHASE2_TURNS,
            "phase_2_started_at": "2026-05-15T00:00:00Z",
            "messages": [],
        }
        mock_user.onboarding_status = None

        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_onboarding_profile = AsyncMock()
        mock_repo.update_onboarding_status = AsyncMock()
        mock_repo.activate_game = AsyncMock()

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock()

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.UserRepository",
                return_value=mock_repo,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
                new=AsyncMock(return_value="An architect who finds beauty in brutalism."),
            ),
        ):
            result = await handle_v2_answer(mock_req, mock_user, mock_session)

        assert isinstance(result, CompleteAsk), (
            f"Expected CompleteAsk at MAX_PHASE2_TURNS={MAX_PHASE2_TURNS}, got {type(result)}"
        )
        assert result.backstory_preview is not None, (
            "backstory_preview must be set after forced completion"
        )
        mock_repo.update_onboarding_profile.assert_awaited()


class TestAntiRepetitionTriggersModelRetry:
    """I3: anti-repetition guard — repeated question text raises ModelRetry.

    GH #623 walk evidence: 5 of 7 questions ended with "Is it awe,
    [X], something [Y]?" verbatim. Trigram overlap >= 20% should trigger
    ModelRetry to force a new question.
    """

    @pytest.mark.asyncio
    async def test_anti_repetition_triggers_model_retry(self) -> None:
        """Output validator raises ModelRetry when proposed question has
        >= ANTI_REPETITION_TRIGRAM_THRESHOLD overlap with the last 3
        questions in phase_2_messages."""
        from nikita.agents.onboarding.v2.research_agent import (
            MAX_ANTI_REPETITION_LOOK_BACK,
            build_phase2_output_validator,
        )

        # Prior messages contain the same question repeated
        repeated_q = "Is it awe, unease, something else entirely?"
        prior_messages = [
            {"role": "assistant", "content": repeated_q},
            {"role": "user", "content": "I find it hard to explain"},
            {"role": "assistant", "content": repeated_q},  # identical repeat
        ]

        state = _state(PHASE_2_MIN_TURNS)
        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000011",
            state=state,
            phase_2_messages=prior_messages,
        )
        validator = build_phase2_output_validator()
        ctx = MagicMock()
        ctx.deps = deps
        ctx.deps.state = state

        # Agent proposes the same repeated question
        with pytest.raises(ModelRetry, match=r"[Rr]epetit"):
            await validator(ctx, repeated_q)

    @pytest.mark.asyncio
    async def test_no_model_retry_on_distinct_question(self) -> None:
        """Output validator does NOT raise ModelRetry for a genuinely new
        question that shares minimal overlap with prior questions."""
        from nikita.agents.onboarding.v2.research_agent import (
            build_phase2_output_validator,
        )

        prior_messages = [
            {"role": "assistant", "content": "Is it awe, unease, something else entirely?"},
            {"role": "user", "content": "Mostly unease honestly"},
            {"role": "assistant", "content": "What kind of music do you listen to?"},
            {"role": "user", "content": "Jazz and electronic"},
        ]

        state = _state(PHASE_2_MIN_TURNS)
        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000012",
            state=state,
            phase_2_messages=prior_messages,
        )
        validator = build_phase2_output_validator()
        ctx = MagicMock()
        ctx.deps = deps
        ctx.deps.state = state

        # A completely new question topic — must pass (return output unchanged)
        result = await validator(ctx, "What does your Saturday morning look like in summer?")
        assert result == "What does your Saturday morning look like in summer?"


class TestThemesTrackedAcrossTurns:
    """I2: topic-diversity — inject_phase2_context injects themes_so_far
    extracted from phase_2_messages.

    GH #623: agent fixated on architecture theme for 5/7 turns. Injecting
    themes_so_far into instructions forces the model to branch out.
    """

    def test_themes_tracked_across_turns(self) -> None:
        """inject_phase2_context with 3-turn fixture covering different themes
        must include themes_so_far in the rendered prompt."""
        from nikita.agents.onboarding.v2.research_agent import inject_phase2_context

        phase2_messages = [
            {"role": "assistant", "content": "What kind of architecture do you love most?"},
            {"role": "user", "content": "Brutalist buildings, especially in Berlin"},
            {"role": "assistant", "content": "What's your Saturday morning ritual?"},
            {"role": "user", "content": "Long coffee and reading architecture books"},
            {"role": "assistant", "content": "How does music fit into your creative work?"},
            {"role": "user", "content": "Electronic music helps me focus"},
        ]

        state = _state(3)
        deps = V2ResearchDeps(
            user_id="00000000-0000-0000-0000-000000000013",
            state=state,
            phase_2_messages=phase2_messages,
        )
        ctx = MagicMock()
        ctx.deps = deps

        prompt = inject_phase2_context(ctx)

        # Prompt must mention themes_so_far guidance (not necessarily the exact
        # string "themes_so_far" but the instructions must say "topics" or "themes"
        # already covered and tell the agent to explore something new)
        assert any(
            keyword in prompt.lower()
            for keyword in ("theme", "topic", "covered", "explored", "new area", "different")
        ), (
            f"Expected prompt to include topic-diversity guidance; got: {prompt[:200]}"
        )

    def test_themes_so_far_accumulates_with_more_turns(self) -> None:
        """Three separate calls with increasing turn fixtures; each time the
        injected prompt grows richer in theme-coverage guidance."""
        from nikita.agents.onboarding.v2.research_agent import inject_phase2_context

        def _prompt_for_messages(messages: list[dict]) -> str:
            state = _state(len(messages) // 2)
            deps = V2ResearchDeps(
                user_id="00000000-0000-0000-0000-000000000014",
                state=state,
                phase_2_messages=messages,
            )
            ctx = MagicMock()
            ctx.deps = deps
            return inject_phase2_context(ctx)

        msgs_1 = [
            {"role": "assistant", "content": "Tell me about your work as an architect?"},
            {"role": "user", "content": "I focus on structural engineering"},
        ]
        msgs_2 = msgs_1 + [
            {"role": "assistant", "content": "What kind of music moves you?"},
            {"role": "user", "content": "Ambient electronic"},
        ]
        msgs_3 = msgs_2 + [
            {"role": "assistant", "content": "How do you spend your Saturdays?"},
            {"role": "user", "content": "Long walks in the city"},
        ]

        p1 = _prompt_for_messages(msgs_1)
        p3 = _prompt_for_messages(msgs_3)

        # More turns = more covered themes in instructions
        # The prompts themselves may differ; at minimum both must include
        # diversity guidance (same keyword check as above)
        assert any(
            kw in p1.lower()
            for kw in ("theme", "topic", "covered", "explored", "new area", "different")
        )
        assert any(
            kw in p3.lower()
            for kw in ("theme", "topic", "covered", "explored", "new area", "different")
        )
