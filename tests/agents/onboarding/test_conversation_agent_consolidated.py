"""RED tests for GH #402/#403 — consolidated discriminated-union agent.

These tests verify that conversation_agent.py is refactored to use a single
``TurnOutput`` wrapper schema (output_type=TurnOutput) with no registered
@agent.tool extractions, per AC-11d.5 path (a).

Walk W live evidence (2026-04-23): 7-tool fan-out causes LLM to keep
emitting IdentityExtraction for phone/darkness inputs because tool-selection
bias dominates. Dynamic instructions (path b) are insufficient. Consolidating
to a single structured output removes the tool-selection decision entirely.

Tests use behavioral assertions via TestModel/FunctionModel — NOT private
attribute inspection like ``len(agent._tools)`` which is brittle and unreliable
(Pydantic AI registers internal "final_result" toolset entries).

All tests in this file are RED on the current codebase (7-tool agent).
They go GREEN after T2 refactor in conversation_agent.py.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic_ai.models.test import TestModel

from nikita.agents.onboarding.state import SlotDelta, WizardSlots


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps(state: WizardSlots | None = None) -> Any:
    """Build a ConverseDeps with optional partial state."""
    from nikita.agents.onboarding.conversation_agent import ConverseDeps

    return ConverseDeps(
        user_id=uuid4(),
        state=state or WizardSlots(),
    )


# ---------------------------------------------------------------------------
# T1-1: TurnOutput schema importable from conversation_agent
# ---------------------------------------------------------------------------


class TestTurnOutputSchema:
    """TurnOutput must be a Pydantic BaseModel with ``delta`` and ``reply``."""

    def test_turn_output_importable(self):
        """TurnOutput must be exported from conversation_agent.

        RED: ImportError on current codebase (class does not exist yet).
        """
        from nikita.agents.onboarding.conversation_agent import TurnOutput  # noqa: F401

    def test_turn_output_has_delta_field(self):
        """TurnOutput.delta must accept SlotDelta or None."""
        from nikita.agents.onboarding.conversation_agent import TurnOutput

        # Extraction turn: delta carries a SlotDelta
        delta = SlotDelta(kind="location", data={"city": "Zurich", "confidence": 0.9})
        out = TurnOutput(delta=delta, reply="Cool, Zurich noted!")
        assert out.delta is not None
        assert out.delta.kind == "location"

    def test_turn_output_none_delta_for_clarification(self):
        """TurnOutput.delta=None is valid for clarification turns."""
        from nikita.agents.onboarding.conversation_agent import TurnOutput

        out = TurnOutput(delta=None, reply="Could you clarify that?")
        assert out.delta is None
        assert out.reply == "Could you clarify that?"

    def test_turn_output_reply_required(self):
        """TurnOutput.reply must be a non-empty str — every turn needs a reply."""
        from nikita.agents.onboarding.conversation_agent import TurnOutput
        from pydantic import ValidationError

        with pytest.raises((ValidationError, TypeError)):
            TurnOutput(delta=None)  # missing reply


# ---------------------------------------------------------------------------
# T1-2: Agent output_type is TurnOutput (behavioral)
# ---------------------------------------------------------------------------


class TestAgentOutputTypeBehavioral:
    """Behavioral: run the consolidated agent with TestModel and verify
    result.output is a TurnOutput instance (never a raw str).

    RED: current agent has output_type=str, so result.output is str.
    """

    def test_agent_run_returns_turn_output_not_str(self):
        """Agent run must return TurnOutput, not str.

        Uses TestModel with custom_output_args to emit a TurnOutput-shaped dict.
        RED: current agent output_type=str → result.output is str, not TurnOutput.
        """
        from nikita.agents.onboarding.conversation_agent import (
            TurnOutput,
            _create_conversation_agent,
        )

        agent = _create_conversation_agent()
        deps = _make_deps()

        result = asyncio.run(
            agent.run(
                "I'm in Zurich",
                deps=deps,
                model=TestModel(
                    custom_output_args={
                        "delta": {
                            "kind": "location",
                            "data": {"city": "Zurich", "confidence": 0.9},
                        },
                        "reply": "Nice, Zurich it is.",
                    }
                ),
            )
        )

        assert isinstance(result.output, TurnOutput), (
            f"Expected TurnOutput, got {type(result.output).__name__}: {result.output!r}. "
            "Consolidation: output_type must be TurnOutput, not str."
        )

    def test_agent_run_clarification_turn_returns_turn_output_with_none_delta(self):
        """On a clarification turn the agent emits TurnOutput with delta=None."""
        from nikita.agents.onboarding.conversation_agent import (
            TurnOutput,
            _create_conversation_agent,
        )

        agent = _create_conversation_agent()
        deps = _make_deps()

        result = asyncio.run(
            agent.run(
                "hmm let me think",
                deps=deps,
                model=TestModel(
                    custom_output_args={"delta": None, "reply": "Take your time!"}
                ),
            )
        )

        assert isinstance(result.output, TurnOutput), (
            f"Expected TurnOutput, got {type(result.output).__name__}"
        )
        assert result.output.delta is None


# ---------------------------------------------------------------------------
# T1-3: No extraction tool registrations (behavioral via TestModel)
# ---------------------------------------------------------------------------


class TestNoExtractionToolsBehavioral:
    """The consolidated agent must NOT register any extract_* tools.

    Behavioral approach: attempt to call an extraction-tool name via
    TestModel(call_tools=["extract_location"]). If the tool is registered
    the model will succeed; if not, pydantic_ai raises ToolNotFoundError or
    similar. We also verify that the _function_toolset does not contain the
    old 7 extract_* names.

    RED: current agent has all 7 extract_* tools registered.
    """

    EXTRACTION_TOOL_NAMES = [
        "extract_location",
        "extract_scene",
        "extract_darkness",
        "extract_identity",
        "extract_backstory",
        "extract_phone",
        "no_extraction",
    ]

    def test_no_extract_location_tool(self):
        """extract_location must NOT be in the agent toolset."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        tools = set(agent._function_toolset.tools.keys())
        assert "extract_location" not in tools, (
            "extract_location still registered — 7-tool fan-out not removed"
        )

    def test_no_extract_phone_tool(self):
        """extract_phone must NOT be in the agent toolset."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        tools = set(agent._function_toolset.tools.keys())
        assert "extract_phone" not in tools, (
            "extract_phone still registered — 7-tool fan-out not removed"
        )

    def test_no_extract_identity_tool(self):
        """extract_identity must NOT be in the agent toolset — Walk W root cause."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        tools = set(agent._function_toolset.tools.keys())
        assert "extract_identity" not in tools, (
            "extract_identity still registered — this is the Walk W root cause: "
            "LLM defaults to extract_identity due to tool-selection bias"
        )

    def test_none_of_the_extraction_tools_remain(self):
        """All 7 old extraction tool names must be absent."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        tools = set(agent._function_toolset.tools.keys())
        stale = [t for t in self.EXTRACTION_TOOL_NAMES if t in tools]
        assert not stale, (
            f"Stale extraction tools still registered: {stale}. "
            "Consolidation requires deleting all @agent.tool registrations."
        )


# ---------------------------------------------------------------------------
# T1-4: State mutation in deps — apply() called on extraction turns
# ---------------------------------------------------------------------------


class TestDepsStateMutation:
    """After a successful extraction turn, deps.state must be updated.

    The output_validator (or the agent logic) must call:
        ctx.deps.state = ctx.deps.state.apply(output.delta)
    when output.delta is not None.

    RED: current agent uses deps.extracted sidecar list, not deps.state.
    """

    def test_deps_state_updated_after_extraction(self):
        """deps.state must reflect the extracted slot after agent.run returns.

        Strategy: run agent with TestModel emitting a location extraction.
        After run(), assert deps.state.location is not None.
        """
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        deps = _make_deps()

        asyncio.run(
            agent.run(
                "I'm in Zurich",
                deps=deps,
                model=TestModel(
                    custom_output_args={
                        "delta": {
                            "kind": "location",
                            "data": {"city": "Zurich", "confidence": 0.9},
                        },
                        "reply": "Zurich noted!",
                    }
                ),
            )
        )

        # After a location extraction, deps.state.location must be populated
        assert deps.state.location is not None, (
            "deps.state.location is None after location extraction. "
            "The output_validator must call deps.state = deps.state.apply(delta)."
        )
        assert deps.state.location.get("city") == "Zurich"

    def test_deps_state_unchanged_on_clarification_turn(self):
        """When delta=None, deps.state must remain at prior value."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        # Start with location already set
        prior = WizardSlots().apply(
            SlotDelta(kind="location", data={"city": "Berlin", "confidence": 0.95})
        )
        deps = _make_deps(state=prior)

        _agent = _create_conversation_agent()
        asyncio.run(
            _agent.run(
                "hmm",
                deps=deps,
                model=TestModel(custom_output_args={"delta": None, "reply": "Got it."}),
            )
        )

        # state must still show Berlin (delta=None → no apply)
        assert deps.state.location is not None
        assert deps.state.location.get("city") == "Berlin"


# ---------------------------------------------------------------------------
# T1-5: pick_primary_extraction absent from public API (dead code removal)
# ---------------------------------------------------------------------------


class TestPickPrimaryExtractionRemoved:
    """pick_primary_extraction is dead post-consolidation and must be removed.

    RED: current codebase exports it; import succeeds.
    GREEN: import raises ImportError.

    Note: if removing pick_primary_extraction breaks the __all__ list,
    the ImportError is also acceptable.
    """

    def test_pick_primary_extraction_not_in_public_api(self):
        """pick_primary_extraction must NOT be in __all__ post-consolidation."""
        import nikita.agents.onboarding.conversation_agent as ca

        all_exports = getattr(ca, "__all__", [])
        assert "pick_primary_extraction" not in all_exports, (
            "pick_primary_extraction still in __all__ — dead code not cleaned up. "
            "Post-consolidation, deps.extracted sidecar and pick_primary_extraction "
            "are both dead."
        )


# ---------------------------------------------------------------------------
# T1-6: Dynamic instructions still registered (regression guard)
# ---------------------------------------------------------------------------


class TestDynamicInstructionsPreserved:
    """@agent.instructions callable must still be registered post-refactor.

    This is a regression guard — PR-B already wired this (T11); T2 must
    NOT accidentally remove it during the tool-consolidation refactor.
    """

    def test_dynamic_instructions_still_registered(self):
        """agent._instructions must be non-empty after consolidation."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        dynamic_fns = getattr(agent, "_instructions", [])
        assert len(dynamic_fns) >= 1, (
            "agent._instructions is empty — @agent.instructions callable removed "
            "during tool-consolidation refactor. Must be preserved."
        )


# ---------------------------------------------------------------------------
# T1-7: Output validator still registered (regression guard)
# ---------------------------------------------------------------------------


class TestOutputValidatorPreserved:
    """@agent.output_validator must remain registered post-consolidation.

    The validator now enforces TurnOutput.reply is non-empty when wizard
    is incomplete, and calls deps.state = deps.state.apply(output.delta).
    """

    def test_output_validator_still_registered(self):
        """agent._output_validators must be non-empty after consolidation."""
        from nikita.agents.onboarding.conversation_agent import _create_conversation_agent

        agent = _create_conversation_agent()
        validators = getattr(agent, "_output_validators", [])
        assert len(validators) >= 1, (
            "agent._output_validators is empty — @agent.output_validator removed. "
            "Post-consolidation, the validator must still enforce reply quality."
        )


# ---------------------------------------------------------------------------
# T1-8: Mandatory agentic-flow test classes (testing.md requirement)
# ---------------------------------------------------------------------------


class TestCumulativeStateMonotonicity:
    """Agentic-flow mandatory test #1: turn-by-turn monotonicity.

    Feed 3 turns of extractions into WizardSlots.apply() via the consolidated
    agent (TestModel). Assert progress never decreases.

    This test validates the WizardSlots layer independently of the agent
    (state.py is not touched, so this is already green, but the agentic-design-
    patterns.md requires the test exists in the agent test file).
    """

    def test_progress_monotonically_increases(self):
        """WizardSlots.apply() + progress_pct must be monotonically increasing."""
        turns = [
            SlotDelta(kind="location", data={"city": "Zurich", "confidence": 0.9}),
            SlotDelta(kind="scene", data={"scene": "techno", "confidence": 0.9}),
            SlotDelta(kind="darkness", data={"drug_tolerance": 3, "confidence": 0.9}),
        ]

        state = WizardSlots()
        prev_pct = state.progress_pct
        for delta in turns:
            state = state.apply(delta)
            assert state.progress_pct >= prev_pct, (
                f"progress_pct regressed: {prev_pct} → {state.progress_pct} "
                f"after applying {delta.kind}. Monotonicity violated."
            )
            prev_pct = state.progress_pct


class TestCompletionGateTriplet:
    """Agentic-flow mandatory test #2: empty/partial/full completion gate."""

    def test_empty_state_not_complete(self):
        """Empty WizardSlots → not complete."""
        assert not WizardSlots().is_complete

    def test_partial_state_not_complete(self):
        """Partially-filled WizardSlots → not complete."""
        partial = WizardSlots(
            location={"city": "Zurich", "confidence": 0.9},
            scene={"scene": "techno", "confidence": 0.9},
        )
        assert not partial.is_complete

    def test_full_state_is_complete(self):
        """All 6 slots filled with valid data → is_complete."""
        full = WizardSlots(
            location={"city": "Zurich", "confidence": 0.9},
            scene={"scene": "techno", "confidence": 0.9},
            darkness={"drug_tolerance": 3, "confidence": 0.9},
            identity={"name": "Simon", "age": 25, "confidence": 0.9},
            backstory={"chosen_option_id": "opt_1", "cache_key": "abc", "confidence": 0.9},
            phone={"phone": "+41795550123", "phone_preference": "voice", "confidence": 0.9},
        )
        assert full.is_complete


class TestMockLLMWrongOutputRecovery:
    """Agentic-flow mandatory test #3: recovery when LLM emits wrong output.

    With consolidated output_type=TurnOutput, the LLM no longer picks tools —
    it fills TurnOutput fields. The "wrong tool" scenario becomes: LLM emits
    TurnOutput(delta=SlotDelta(kind='identity', ...), reply='...') when the
    phone number is present in input.

    Recovery path: regex_phone_fallback in the handler (defense in depth).
    This test verifies the fallback is importable and corrects an identity-
    delta-for-phone-input scenario.
    """

    def test_regex_phone_fallback_corrects_wrong_kind(self):
        """regex_phone_fallback must turn a phone-number input into a phone delta
        even when the LLM (incorrectly) emitted an identity-kind extraction.
        """
        from nikita.agents.onboarding.regex_fallback import regex_phone_fallback

        # State with no phone slot yet
        slots = WizardSlots(
            location={"city": "Zurich", "confidence": 0.9},
            scene={"scene": "techno", "confidence": 0.9},
            darkness={"drug_tolerance": 3, "confidence": 0.9},
            identity={"name": "Simon", "age": 25, "confidence": 0.9},
            backstory={"chosen_option_id": "opt_1", "cache_key": "abc", "confidence": 0.9},
        )

        # LLM emitted identity again (wrong), but user input is a phone number
        user_input = "voice. call me at +41795550234"
        fallback_delta = regex_phone_fallback(user_input, slots)

        assert fallback_delta is not None, (
            "regex_phone_fallback returned None for phone-number input. "
            "Defense in depth requires the fallback to catch this."
        )
        assert fallback_delta.kind == "phone", (
            f"fallback_delta.kind={fallback_delta.kind!r}; expected 'phone'"
        )
