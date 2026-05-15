"""Phase-2 regression tests — Walk #108 failures (GH #639, GH #640).

Walk #108 (2026-05-15, prod rev nikita-api-00321-dlj):
  - Phase-2 reached 8 turns (DB: phase_2_turn_count=7 at check point).
  - Turn 7 emitted verbatim "Is it awe, X, something Y?" pattern.
  - Turns 3+4+7 were near-verbatim repeats of turns 1+2.

Root causes fixed by PR #633 (GH #623):
  GH #639 — PHASE_2_MAX_TURNS lowered to 5. This file regression-guards
             that the constant stays at 5 and the gate fires correctly.
  GH #640 — Anti-repetition output validator. This file guards the trigram
             helper behaviour and the validator ModelRetry contract.

These tests are additive: they extend the existing triplet in
test_research_agent.py. They do NOT duplicate that file's tests.
"""

from __future__ import annotations

import pytest
from pydantic_ai.exceptions import ModelRetry
from unittest.mock import MagicMock

from nikita.agents.onboarding.v2.research_agent import (
    ANTI_REPETITION_TRIGRAM_THRESHOLD,
    MAX_ANTI_REPETITION_LOOK_BACK,
    V2ResearchDeps,
    _extract_prior_questions,
    _is_repetitive,
    _trigram_overlap,
    _trigrams,
    build_phase2_output_validator,
    phase_2_gate,
)
from nikita.agents.onboarding.v2.state import (
    MAX_PHASE2_TURNS,
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    Phase,
    WizardSlotsV2,
    WizardStateV2,
)
from nikita.agents.onboarding.v2.envelope import CompleteAsk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_slots() -> WizardSlotsV2:
    return WizardSlotsV2(
        display_name={"display_name": "Alex"},
        age={"age": 28},
        city={"city": "Berlin"},
        occupation={"occupation": "Architect"},
        primary_hobbies={"primary_hobbies": ["hiking", "photography"]},
        hangouts_personalized={"hangouts_personalized": ["galleries", "parks"]},
        voice_or_text={"voice_or_text": "text"},
        saturday_morning={"saturday_morning": "long coffee and sketching"},
        darkness_level={"darkness_level": 5},
        geek_out_on={"geek_out_on": "brutalist architecture"},
    )


def _state(count: int) -> WizardStateV2:
    return WizardStateV2(
        slots=_full_slots(),
        phase=Phase.phase2,
        phase_2_turn_count=count,
        phase_2_started_at="2026-05-15T00:00:00Z",
    )


def _mock_ctx(turn_count: int, phase_2_messages: list[dict] | None = None) -> MagicMock:
    """Return a mock RunContext with V2ResearchDeps wired."""
    ctx = MagicMock()
    ctx.deps = V2ResearchDeps(
        user_id="test-user-id",
        state=_state(turn_count),
        phase_2_messages=phase_2_messages or [],
    )
    return ctx


# ---------------------------------------------------------------------------
# GH #639 — Turn cap: PHASE_2_MAX_TURNS regression guard
# ---------------------------------------------------------------------------


class TestTurnCapConstant:
    """Regression guard: PHASE_2_MAX_TURNS must be 5 (GH #639).

    Walk #108 evidence: wizard ran 8 turns because PHASE_2_MAX_TURNS was 8.
    This test will fail if the constant is accidentally raised again.
    """

    def test_phase_2_max_turns_is_5(self) -> None:
        """PHASE_2_MAX_TURNS must equal 5 (GH #639, Walk #108 fix).

        Regression guard per .claude/rules/tuning-constants.md: every
        tuning constant needs a test asserting its exact current value.
        Intentional changes require updating this test AND its docstring.
        """
        assert PHASE_2_MAX_TURNS == 5, (  # noqa: PLR2004
            "PHASE_2_MAX_TURNS regressed — Walk #108 evidence requires max=5 "
            "(was 8 when wizard ran to 8 turns). Update this test + docstring if "
            "intentionally changing the constant."
        )

    def test_max_phase2_turns_alias_matches(self) -> None:
        """MAX_PHASE2_TURNS alias must equal PHASE_2_MAX_TURNS."""
        assert MAX_PHASE2_TURNS == PHASE_2_MAX_TURNS

    def test_min_turns_less_than_max_turns(self) -> None:
        """Sanity: MIN < MAX to avoid an always-forced-complete gate."""
        assert PHASE_2_MIN_TURNS < PHASE_2_MAX_TURNS, (
            f"MIN_TURNS ({PHASE_2_MIN_TURNS}) must be < MAX_TURNS ({PHASE_2_MAX_TURNS})"
        )

    def test_gate_forces_complete_at_turn_5(self) -> None:
        """phase_2_gate returns (True, True) exactly at turn 5 (GH #639)."""
        state = _state(5)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is True
        assert forced is True

    def test_gate_does_not_force_at_turn_4(self) -> None:
        """At turn 4 (== MIN_TURNS), agent decides freely — not forced."""
        state = _state(PHASE_2_MIN_TURNS)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is False
        assert forced is False

    def test_walk_108_scenario_turn_7_would_be_forced(self) -> None:
        """Walk #108 DB snapshot: phase_2_turn_count=7. With MAX=5, the
        pre-agent gate in portal_onboarding_v2.py fires and forces completion
        — agent is never called.

        With old MAX=8: count=7 < 8 → gate returns (False, False) → agent
        runs → outputs verbatim repeat → turn 8 is accepted.

        With new MAX=5: count=7 >= 5 → gate returns (True, True) → forced
        complete before agent runs.
        """
        state = _state(7)
        complete, forced = phase_2_gate(state, agent_signals_done=False)
        assert complete is True, "count=7 >= MAX=5 must force completion"
        assert forced is True


# ---------------------------------------------------------------------------
# GH #640 — Anti-repetition helpers: unit tests
# ---------------------------------------------------------------------------


class TestTrigramHelpers:
    """Unit tests for _trigrams, _trigram_overlap, _extract_prior_questions,
    _is_repetitive (GH #640)."""

    def test_trigrams_empty_string(self) -> None:
        result = _trigrams("")
        assert result == set()

    def test_trigrams_short_string_under_3_chars(self) -> None:
        """Strings < 3 chars — implementation-defined but should not raise."""
        result = _trigrams("ab")
        assert isinstance(result, set)

    def test_trigrams_known_word(self) -> None:
        result = _trigrams("abc")
        assert len(result) > 0

    def test_trigram_overlap_identical_strings(self) -> None:
        """Identical strings must have overlap == 1.0."""
        s = "Is it awe or unease or something else entirely?"
        assert _trigram_overlap(s, s) == pytest.approx(1.0)

    def test_trigram_overlap_completely_different_strings(self) -> None:
        """Completely different strings should have low overlap."""
        a = "Tell me about your childhood"
        b = "What music do you geek out on at 2am?"
        overlap = _trigram_overlap(a, b)
        assert overlap < 0.25, f"Expected low overlap, got {overlap:.3f}"

    def test_trigram_overlap_verbatim_repeat_is_high(self) -> None:
        """Walk #108 repeat pattern: same question emitted twice."""
        q = "Is it awe, unease, or something else entirely?"
        overlap = _trigram_overlap(q, q)
        assert overlap >= ANTI_REPETITION_TRIGRAM_THRESHOLD

    def test_trigram_overlap_near_verbatim_rephrase_detected(self) -> None:
        """Near-verbatim rephrase: word substitution with same structure."""
        q1 = "Is it awe, unease, or something else entirely?"
        q2 = "Is it awe, fear, or something quite different?"
        overlap = _trigram_overlap(q1, q2)
        assert overlap >= ANTI_REPETITION_TRIGRAM_THRESHOLD, (
            f"Expected near-verbatim rephrase to be flagged, got {overlap:.3f}"
        )

    def test_extract_prior_questions_filters_assistant_only(self) -> None:
        messages = [
            {"role": "user", "content": "I love hiking"},
            {"role": "assistant", "content": "What draws you to the mountains?"},
            {"role": "user", "content": "The silence mainly"},
            {"role": "assistant", "content": "Do you prefer solitude or company?"},
        ]
        prior = _extract_prior_questions(messages, look_back=10)
        assert prior == [
            "What draws you to the mountains?",
            "Do you prefer solitude or company?",
        ]

    def test_extract_prior_questions_look_back_truncates(self) -> None:
        messages = [
            {"role": "assistant", "content": f"Question {i}"}
            for i in range(10)
        ]
        prior = _extract_prior_questions(messages, look_back=3)
        assert len(prior) == 3
        assert prior[-1] == "Question 9"

    def test_extract_prior_questions_empty_messages(self) -> None:
        assert _extract_prior_questions([]) == []

    def test_is_repetitive_returns_true_for_verbatim_repeat(self) -> None:
        q = "Is it awe, unease, or something else entirely?"
        assert _is_repetitive(q, [q]) is True

    def test_is_repetitive_returns_false_for_diverse_question(self) -> None:
        prior = ["Is it awe, unease, or something else entirely?"]
        candidate = "What music do you listen to when you need to think?"
        assert _is_repetitive(candidate, prior) is False

    def test_is_repetitive_empty_prior_always_false(self) -> None:
        """No prior questions → nothing to be repetitive against."""
        assert _is_repetitive("Any question at all?", []) is False


# ---------------------------------------------------------------------------
# GH #640 — Anti-repetition validator: ModelRetry behaviour
# ---------------------------------------------------------------------------


class TestAntiRepetitionValidator:
    """build_phase2_output_validator raises ModelRetry on near-verbatim repeat.

    Tests call the validator directly (not through the agent factory) to
    isolate the logic from the LLM and output_retries budget.
    """

    @pytest.mark.asyncio
    async def test_validator_raises_modelretry_on_verbatim_repeat(self) -> None:
        """Walk #108 failure: same question emitted again in same session.

        Validator must raise ModelRetry so the agent produces a
        genuinely different question.
        """
        verbatim_q = "Is it awe, unease, or something else entirely?"
        ctx = _mock_ctx(
            turn_count=2,
            phase_2_messages=[
                {"role": "assistant", "content": verbatim_q},
            ],
        )
        validator = build_phase2_output_validator()
        with pytest.raises(ModelRetry):
            await validator(ctx, verbatim_q)

    @pytest.mark.asyncio
    async def test_validator_raises_modelretry_on_near_verbatim_rephrase(self) -> None:
        """Near-verbatim rephrase (same structure, some words swapped) must
        also be caught."""
        prior_q = "Is it awe, unease, or something else entirely?"
        rephrased_q = "Is it awe, fear, or something quite different?"
        ctx = _mock_ctx(
            turn_count=2,
            phase_2_messages=[
                {"role": "assistant", "content": prior_q},
            ],
        )
        validator = build_phase2_output_validator()
        with pytest.raises(ModelRetry):
            await validator(ctx, rephrased_q)

    @pytest.mark.asyncio
    async def test_validator_passes_on_diverse_question(self) -> None:
        """A genuinely different question must pass through without ModelRetry."""
        prior_q = "Is it awe, unease, or something else entirely?"
        diverse_q = "What kind of music do you geek out on at 2am?"
        ctx = _mock_ctx(
            turn_count=2,
            phase_2_messages=[
                {"role": "assistant", "content": prior_q},
            ],
        )
        validator = build_phase2_output_validator()
        # Must not raise
        result = await validator(ctx, diverse_q)
        assert result == diverse_q

    @pytest.mark.asyncio
    async def test_validator_passes_on_empty_prior_history(self) -> None:
        """First Phase-2 turn: no prior questions → validator must not block."""
        ctx = _mock_ctx(turn_count=0, phase_2_messages=[])
        validator = build_phase2_output_validator()
        q = "What draws you to brutalist architecture?"
        result = await validator(ctx, q)
        assert result == q

    @pytest.mark.asyncio
    async def test_validator_still_blocks_premature_complete_ask(self) -> None:
        """Existing gate: CompleteAsk before MIN_TURNS must still raise."""
        ctx = _mock_ctx(turn_count=PHASE_2_MIN_TURNS - 1)
        validator = build_phase2_output_validator()
        complete_ask = CompleteAsk(next_route="/dashboard")
        with pytest.raises(ModelRetry):
            await validator(ctx, complete_ask)

    @pytest.mark.asyncio
    async def test_validator_passes_complete_ask_at_min_turns(self) -> None:
        """CompleteAsk at or above MIN_TURNS must pass through."""
        ctx = _mock_ctx(turn_count=PHASE_2_MIN_TURNS)
        validator = build_phase2_output_validator()
        complete_ask = CompleteAsk(next_route="/dashboard")
        result = await validator(ctx, complete_ask)
        assert result is complete_ask

    @pytest.mark.asyncio
    async def test_validator_look_back_window_limits_comparison(self) -> None:
        """Validator only checks last MAX_ANTI_REPETITION_LOOK_BACK questions.

        If the verbatim repeat was > MAX_LOOK_BACK turns ago, it should
        NOT be caught (we only guard against recent repetition).
        """
        old_question = "Is it awe, unease, or something else entirely?"
        # Fill history with MAX_LOOK_BACK diverse questions after the old one
        filler_messages = [
            {"role": "assistant", "content": f"Tell me about topic {i}"}
            for i in range(MAX_ANTI_REPETITION_LOOK_BACK)
        ]
        # old_question is before the filler — beyond the look-back window
        all_messages = [
            {"role": "assistant", "content": old_question},
            *filler_messages,
        ]
        ctx = _mock_ctx(
            turn_count=len(filler_messages) + 1,
            phase_2_messages=all_messages,
        )
        validator = build_phase2_output_validator()
        # Should NOT raise — old_question is beyond the look-back window
        result = await validator(ctx, old_question)
        assert result == old_question
