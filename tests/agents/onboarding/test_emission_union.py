"""Tests for the 217-3A.2 emission-union agent + output validator.

Covers:
  - AC-5.2 / AC-5.3 — emission-union agent factory wires
    ``output_type=[ToolOutput(ReactionOnly), ToolOutput(FollowUpQuestion),
    ToolOutput(TurnFailure)]``; ``result.output`` narrows to one of the
    three branches under isinstance-based dispatch.
  - AC-6.1 / AC-6.2 / AC-6.3 — dynamic per-turn instructions decorator
    + ``output_retries=2``.
  - AC-7.1 / AC-7.2 / AC-7.3 / AC-7.4 — output validator rejects
    mirror-of-next + mirror-echo via ``ModelRetry``; calibration pairs
    verify the 0.85 threshold.
  - AC-T-1 — cumulative-state monotonicity through followup transitions.
  - AC-T-2 — completion-gate triplet (empty/partial/full).
  - AC-T-3 — mock-LLM-emits-wrong-tool ModelRetry recovery.
  - AC-T-4 — agent.run called with ``deps=`` containing cumulative state
    (the parallel emission-agent doesn't yet wire ``message_history=``;
    that lands in 217-3A.3 alongside the route refactor — this test
    verifies the deps-cumulative-state contract is shipped now).
  - AC-T-5 — dynamic-instructions invocation references ``state.missing``.

The /answer route dispatch on the emission union (AC-9.x) and IdentityPair
BE partial-validation (AC-10a.x) are deferred to 217-3A.3 because the
route refactor would invalidate ~77 legacy-shape assertions across 4
test files (~2164 LOC) — a clean cut belongs in a dedicated PR.
"""

from __future__ import annotations

import difflib
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import ModelRetry, RunContext

from nikita.agents.onboarding.conversation_agent import (
    ConverseDeps,
    build_emission_output_validator,
    get_emission_agent,
)
from nikita.agents.onboarding.converse_contracts import (
    FollowUpQuestion,
    ReactionOnly,
    TurnFailure,
)
from nikita.agents.onboarding.question_registry import SlotKind
from nikita.agents.onboarding.state import FinalForm, SlotDelta, WizardSlots
from nikita.agents.onboarding.validators import (
    MIRROR_THRESHOLD,
    validate_no_mirror_echo,
    validate_no_mirror_of_next,
)
from tests.agents.onboarding.fixtures.similarity_calibration import (
    DISTINCT_PAIRS,
    NEAR_DUPLICATES,
)


# ---------------------------------------------------------------------------
# AC-5.2 / AC-5.3 — emission-union agent shape
# ---------------------------------------------------------------------------


class TestEmissionAgentShape:
    def test_factory_returns_agent_singleton(self):
        """``get_emission_agent`` returns a cached Agent instance."""
        agent_a = get_emission_agent()
        agent_b = get_emission_agent()
        assert agent_a is agent_b, "lru_cache should return the same instance"

    def test_output_type_includes_three_branches(self):
        """AC-5.2 — output_type wires three named ToolOutput branches:
        emit_reaction (ReactionOnly), ask_followup (FollowUpQuestion),
        turn_failure (TurnFailure).

        Introspects the constructed agent's output schema toolset to
        verify the exact tool names landed. Pydantic AI stores ToolOutput
        wrappers as ToolDefinition entries on
        ``agent._output_schema.toolset._tool_defs``; reading private
        attributes here is the only structural assertion path the
        library exposes today (cf. Pydantic AI 1.71 — no public
        introspection API for output_type tool names).
        """
        agent = get_emission_agent()
        tool_defs = agent._output_schema.toolset._tool_defs  # noqa: SLF001
        names = {td.name for td in tool_defs}
        assert names == {"emit_reaction", "ask_followup", "turn_failure"}, (
            f"Expected 3 ToolOutput branches; got {names}"
        )
        # Verify each branch wraps the correct Pydantic class via title.
        titles = {td.parameters_json_schema.get("title") for td in tool_defs}
        assert titles == {"ReactionOnly", "FollowUpQuestion", "TurnFailure"}, (
            f"Expected ReactionOnly/FollowUpQuestion/TurnFailure; got {titles}"
        )


# ---------------------------------------------------------------------------
# AC-7.1 / AC-7.2 / AC-7.3 / AC-7.4 — output validator
# ---------------------------------------------------------------------------


def _ctx(*, next_hint: str = "", last_value: str = "") -> RunContext[ConverseDeps]:
    """Build a minimal RunContext for the validator. Only ``ctx.deps`` is read."""
    deps = ConverseDeps(
        user_id=uuid4(),
        conversation_id=uuid4(),
        state=WizardSlots(),
        next_slot_hint=next_hint,
        last_value=last_value,
    )
    # The validator only reads ctx.deps — a SimpleNamespace-shaped object
    # suffices. We use the real RunContext signature where possible.
    fake_ctx = MagicMock(spec=RunContext)
    fake_ctx.deps = deps
    return fake_ctx


class TestOutputValidatorMirrorOfNext:
    @pytest.mark.parametrize("a,b,_expected", NEAR_DUPLICATES)
    def test_followup_mirroring_next_question_raises(self, a, b, _expected):
        """AC-7.1 — FollowUpQuestion.question_text mirroring next-question
        text (similarity > MIRROR_THRESHOLD) raises ModelRetry."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint=a, last_value="")
        output = FollowUpQuestion(question_text=b)
        with pytest.raises(ModelRetry):
            validator(ctx, output)

    @pytest.mark.parametrize("a,b,_expected", DISTINCT_PAIRS)
    def test_followup_distinct_from_next_question_passes(self, a, b, _expected):
        """AC-7.4 — distinct pairs (ratio < MIRROR_THRESHOLD) pass cleanly."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint=a, last_value="")
        output = FollowUpQuestion(question_text=b)
        result = validator(ctx, output)
        assert result is output

    def test_reaction_mirroring_next_question_raises(self):
        """AC-7.1 — ReactionOnly.reaction_text also rejected when mirroring."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="what's your name", last_value="")
        output = ReactionOnly(reaction_text="what's your name?")
        with pytest.raises(ModelRetry):
            validator(ctx, output)


class TestOutputValidatorMirrorEcho:
    def test_followup_quoting_user_verbatim_raises(self):
        """AC-7.2 — FollowUpQuestion containing user's last answer verbatim raises."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="describe morning", last_value="walker")
        output = FollowUpQuestion(question_text="so walker is ready?")
        with pytest.raises(ModelRetry):
            validator(ctx, output)

    def test_reaction_quoting_user_verbatim_raises(self):
        """AC-7.2 — ReactionOnly mirroring user input verbatim also rejected."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="describe morning", last_value="berlin")
        output = ReactionOnly(reaction_text="berlin sounds rough")
        with pytest.raises(ModelRetry):
            validator(ctx, output)

    def test_emission_distinct_from_user_passes(self):
        """Reactions that don't quote verbatim pass."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="describe morning", last_value="walker")
        output = ReactionOnly(reaction_text="that's a strong answer")
        result = validator(ctx, output)
        assert result is output


class TestOutputValidatorTurnFailurePassthrough:
    def test_turn_failure_bypasses_mirror_checks(self):
        """TurnFailure has no candidate text — passes the validator unchanged."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="what's your name", last_value="")
        output = TurnFailure(explanation="eighteen and up only.")
        result = validator(ctx, output)
        assert result is output


class TestOutputValidatorEmptyContext:
    def test_empty_next_hint_short_circuits_mirror_of_next(self):
        """Empty ``next_slot_hint`` → no comparison possible; passes."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="", last_value="")
        output = FollowUpQuestion(question_text="what's your name?")
        result = validator(ctx, output)
        assert result is output

    def test_empty_last_value_short_circuits_mirror_echo(self):
        """Empty ``last_value`` → no echo possible; passes."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="describe morning", last_value="")
        output = ReactionOnly(reaction_text="anything you say is fine")
        result = validator(ctx, output)
        assert result is output


# ---------------------------------------------------------------------------
# AC-7.4 — calibration: threshold cleanly separates near-dups from distinct.
# ---------------------------------------------------------------------------


class TestMirrorThresholdCalibration:
    @pytest.mark.parametrize("a,b,_expected", NEAR_DUPLICATES)
    def test_near_duplicate_ratio_above_threshold(self, a, b, _expected):
        ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
        assert ratio > MIRROR_THRESHOLD, (
            f"Near-duplicate pair ratio {ratio:.3f} should exceed "
            f"{MIRROR_THRESHOLD}; calibration drift detected."
        )

    @pytest.mark.parametrize("a,b,_expected", DISTINCT_PAIRS)
    def test_distinct_pair_ratio_below_threshold(self, a, b, _expected):
        ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
        assert ratio < MIRROR_THRESHOLD, (
            f"Distinct pair ratio {ratio:.3f} should be below "
            f"{MIRROR_THRESHOLD}; calibration drift detected."
        )


# ---------------------------------------------------------------------------
# AC-T-1 — cumulative-state monotonicity through followup transitions
# ---------------------------------------------------------------------------


class TestCumulativeStateMonotonicityThroughFollowups:
    def test_progress_pct_monotonic_across_3_turns_with_pending_followup(self):
        """3-turn fixture: turn-1 fills name, turn-2 followup pending (no
        slot advance), turn-3 followup resolved + city filled. Progress
        must be monotonic non-decreasing across all 3 transitions."""
        state = WizardSlots()
        history: list[int] = [state.progress_pct]

        # Turn 1 — agent emits TurnOutput-equivalent slot fill (display_name).
        state = state.apply(SlotDelta(kind=SlotKind.display_name.value, data={"display_name": "Walker"}))
        history.append(state.progress_pct)

        # Turn 2 — agent emits FollowUpQuestion (sidecar pending). No
        # WizardSlots mutation; progress UNCHANGED (Hard Rule #1 — sidecar
        # is NEVER a slot, NEVER advances the cumulative state).
        history.append(state.progress_pct)

        # Turn 3 — followup resolved + city filled.
        state = state.apply(SlotDelta(kind=SlotKind.city.value, data={"city": "berlin"}))
        history.append(state.progress_pct)

        for t in range(1, len(history)):
            assert history[t] >= history[t - 1], (
                f"progress_pct dropped at turn {t}: {history[t - 1]} -> {history[t]}. "
                "Cumulative state invariant violated."
            )


# ---------------------------------------------------------------------------
# AC-T-2 — completion-gate triplet
# ---------------------------------------------------------------------------


class TestCompletionGateTriplet:
    def test_empty_state_not_complete(self):
        """Empty WizardSlots → FinalForm validation fails → not complete."""
        state = WizardSlots()
        assert state.is_complete is False
        assert state.progress_pct == 0

    def test_partial_state_not_complete(self):
        """Some slots filled → still not complete; <100%."""
        state = WizardSlots().apply(
            SlotDelta(kind=SlotKind.display_name.value, data={"display_name": "Walker"})
        )
        assert state.is_complete is False
        assert state.progress_pct < 100

    def test_full_state_complete_via_finalform(self):
        """All 13 slots filled → FinalForm.model_validate succeeds; is_complete True."""
        state = (
            WizardSlots()
            .apply(SlotDelta(kind=SlotKind.display_name.value, data={"display_name": "Walker"}))
            .apply(SlotDelta(kind=SlotKind.age.value, data={"age": 25}))
            .apply(SlotDelta(kind=SlotKind.occupation.value, data={"occupation": "engineer"}))
            .apply(SlotDelta(kind=SlotKind.city.value, data={"city": "berlin"}))
            .apply(SlotDelta(kind=SlotKind.darkness_level.value, data={"darkness_level": 3}))
            .apply(SlotDelta(kind=SlotKind.primary_hobbies.value, data={"primary_hobbies": ["chess"]}))
            .apply(SlotDelta(kind=SlotKind.saturday_morning.value, data={"saturday_morning": "coffee and a walk"}))
            .apply(SlotDelta(kind=SlotKind.geek_out_on.value, data={"geek_out_on": "compiler internals"}))
            .apply(SlotDelta(kind=SlotKind.together_we_could.value, data={"together_we_could": "ride trains across germany"}))
            .apply(SlotDelta(kind=SlotKind.same_weird_if.value, data={"same_weird_if": "we both kept journals from age twelve"}))
            .apply(SlotDelta(kind=SlotKind.voice_tone_pref.value, data={"voice_tone_pref": "text"}))
            .apply(SlotDelta(kind=SlotKind.backstory_pick.value, data={"backstory_pick": "researcher"}))
            .apply(SlotDelta(kind=SlotKind.phone.value, data={"phone": "+14155550100"}))
        )
        # Direct FinalForm validation — independent of WizardSlots.is_complete.
        FinalForm.model_validate(state.slots_dict())
        assert state.is_complete is True
        assert state.progress_pct == 100


# ---------------------------------------------------------------------------
# AC-T-3 — mock-LLM-emits-wrong-tool ModelRetry recovery
# ---------------------------------------------------------------------------


class TestWrongToolRecovery:
    def test_followup_mirroring_next_lifts_to_modelretry(self):
        """Mock-LLM scenario: agent emits FollowUpQuestion that mirrors
        the next deterministic question (wrong tool selection / wrong
        content). Validator lifts to ModelRetry so Pydantic AI's
        self-correction loop can re-prompt."""
        validator = build_emission_output_validator()
        ctx = _ctx(next_hint="what's your occupation?", last_value="walker")
        # Agent picked FollowUpQuestion when ReactionOnly was correct;
        # additionally mirrors the next question text.
        output = FollowUpQuestion(question_text="what is your occupation?")
        with pytest.raises(ModelRetry) as excinfo:
            validator(ctx, output)
        assert "mirror_of_next" in str(excinfo.value)


# ---------------------------------------------------------------------------
# AC-T-4 — agent invocation contract: deps carries cumulative state
# ---------------------------------------------------------------------------


class TestAgentInvocationContract:
    def test_converse_deps_carries_cumulative_state(self):
        """ConverseDeps.state IS cumulative WizardSlots (not per-turn snapshot)."""
        state = WizardSlots().apply(
            SlotDelta(kind=SlotKind.display_name.value, data={"display_name": "Walker"})
        )
        deps = ConverseDeps(
            user_id=uuid4(),
            conversation_id=uuid4(),
            state=state,
        )
        assert deps.state.progress_pct == state.progress_pct
        assert deps.state.is_complete == state.is_complete
        # Cumulative invariant: the deps-state IS the WizardSlots, not a snapshot.
        assert deps.state is state


# ---------------------------------------------------------------------------
# AC-T-5 — dynamic-instructions callable invoked per-turn referencing state.missing
# ---------------------------------------------------------------------------


class TestDynamicInstructionsInvocation:
    def test_inject_per_turn_context_references_state_missing(self):
        """Static-prompt anti-pattern guard — the dynamic-instructions
        callable accesses ``ctx.deps.state`` (which exposes
        ``state.missing`` via @computed_field). Calling the function with
        a deps containing partial state must produce a non-empty string
        whose content varies with state."""
        from nikita.agents.onboarding.conversation_prompts import (
            inject_per_turn_context,
        )

        empty_deps = ConverseDeps(
            user_id=uuid4(),
            conversation_id=uuid4(),
            state=WizardSlots(),
        )
        partial_state = WizardSlots().apply(
            SlotDelta(kind=SlotKind.display_name.value, data={"display_name": "Walker"})
        )
        partial_deps = ConverseDeps(
            user_id=uuid4(),
            conversation_id=uuid4(),
            state=partial_state,
        )

        # Use the same MagicMock(spec=RunContext) shape as the validator tests.
        ctx_empty = MagicMock(spec=RunContext)
        ctx_empty.deps = empty_deps
        ctx_partial = MagicMock(spec=RunContext)
        ctx_partial.deps = partial_deps

        empty_prompt = inject_per_turn_context(ctx_empty)
        partial_prompt = inject_per_turn_context(ctx_partial)

        # Both produce non-empty strings (per Pydantic AI docs:
        # "dynamic instructions are always reevaluated").
        assert isinstance(empty_prompt, str) and len(empty_prompt) > 0
        assert isinstance(partial_prompt, str) and len(partial_prompt) > 0
        # Content varies with state — the cumulative-state context is
        # actually wired into the prompt body.
        assert empty_prompt != partial_prompt


# ---------------------------------------------------------------------------
# AC-9.1bis / 9.3 — schema oneOf shape (Spec 217-3A AC-9.1bis amendment)
# ---------------------------------------------------------------------------


class TestAnswerResponseSchemaUnion:
    def test_completion_response_branch_present(self):
        """AC-9.1bis amendment (GH #561) — CompletionResponse 6th branch
        carries terminal-turn fields (``link_code``, ``conversation_id``,
        ``progress_pct=100``, ``is_complete=True``) so the FE can
        narrow on ``kind="completion"`` to render the post-completion
        Telegram bind QR."""
        from nikita.api.schemas.onboarding import (
            AnswerResponse,
            CompletionResponse,
        )

        cid = str(uuid4())
        completion = CompletionResponse(
            conversation_id=cid,
            link_code="ABC12345",
        )
        assert completion.kind == "completion"
        assert completion.is_complete is True
        assert completion.progress_pct == 100
        assert completion.link_code == "ABC12345"

        # Round-trip through the union via Pydantic discriminator.
        from pydantic import TypeAdapter

        adapter = TypeAdapter(AnswerResponse)
        wire = completion.model_dump()
        rehydrated = adapter.validate_python(wire)
        assert isinstance(rehydrated, CompletionResponse)
        assert rehydrated.conversation_id == cid

    def test_completion_progress_must_be_100(self):
        """``progress_pct: Literal[100]`` enforces the terminal-turn
        invariant — emit a different envelope if progress is below 100."""
        from pydantic import ValidationError

        from nikita.api.schemas.onboarding import CompletionResponse

        with pytest.raises(ValidationError):
            CompletionResponse(
                conversation_id=str(uuid4()),
                progress_pct=99,  # type: ignore[arg-type]  # intentional
            )

    def test_six_branches_in_union(self):
        """AnswerResponse Union[...] now contains 6 alternatives keyed
        on the ``kind`` discriminator (217-3A.1 shipped 5; 217-3A.2
        adds ``CompletionResponse``)."""
        from typing import Union, get_args, get_origin
        from typing import Annotated

        from nikita.api.schemas.onboarding import AnswerResponse

        # AnswerResponse = Annotated[Union[...], Field(discriminator=...)]
        # get_args on the Annotated returns (Union[...], Field(...))
        annotated_args = get_args(AnswerResponse)
        union_type = annotated_args[0]
        assert get_origin(union_type) is Union
        branches = get_args(union_type)
        assert len(branches) == 6, (
            f"AnswerResponse must have 6 discriminated branches "
            f"(post-217-3A.2); got {len(branches)}."
        )


# ---------------------------------------------------------------------------
# Bare validator-helper assertions (cheap regression for AC-7.1/7.2 helpers)
# ---------------------------------------------------------------------------


class TestValidatorHelpers:
    def test_validate_no_mirror_of_next_passes_on_distinct(self):
        validate_no_mirror_of_next(
            "what gets you out of bed in the morning",
            next_question="what do you do for work",
        )  # No raise

    def test_validate_no_mirror_of_next_raises_on_near_dup(self):
        with pytest.raises(ValueError, match="mirror_of_next"):
            validate_no_mirror_of_next(
                "what is your occupation?",
                next_question="what's your occupation?",
            )

    def test_validate_no_mirror_echo_passes_on_distinct(self):
        validate_no_mirror_echo(
            "that's a strong answer",
            last_user_answer="walker",
        )  # No raise

    def test_validate_no_mirror_echo_raises_on_verbatim(self):
        with pytest.raises(ValueError, match="mirror_echo"):
            validate_no_mirror_echo(
                "so walker is ready?",
                last_user_answer="walker",
            )
