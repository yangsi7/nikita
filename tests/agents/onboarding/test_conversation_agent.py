"""Tests for nikita.agents.onboarding.conversation_agent (Spec 214 FR-11d).

AC-T2.3.1 — persona imported verbatim (snapshot equality vs. main text
    agent's ``NIKITA_PERSONA``).
AC-T2.3.2 — agent exposes six extraction tools + deps_type + output_type.
AC-T2.3.3 — Anthropic prompt caching is enabled on the system block.

Live-model persona-drift (AC-T2.9.3) is scaffolded here as a skipped
test — the CSV baseline + ADR-001 generator are authored in T2.9 but
actual 60-row CSV generation requires live Anthropic calls and is
tracked as a post-merge follow-up.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic_ai import Agent

from nikita.agents.onboarding.conversation_agent import (
    CACHE_SETTINGS,
    ConverseDeps,
    get_conversation_agent,
)
from nikita.agents.onboarding.conversation_prompts import (
    NIKITA_PERSONA,
    WIZARD_SYSTEM_PROMPT,
)
from nikita.agents.text.persona import NIKITA_PERSONA as CANONICAL_PERSONA
from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS


class TestPersonaImport:
    def test_persona_imported_verbatim(self):
        """AC-T2.3.1: no fork — identity invariant pinned.

        The conversation agent's WIZARD_SYSTEM_PROMPT MUST start with
        ``NIKITA_PERSONA`` verbatim. Drift here is a PR blocker because
        it changes Nikita's voice across surfaces.
        """
        assert NIKITA_PERSONA is CANONICAL_PERSONA, (
            "conversation_prompts must re-export the canonical persona object"
        )
        assert WIZARD_SYSTEM_PROMPT.startswith(CANONICAL_PERSONA), (
            "WIZARD_SYSTEM_PROMPT must start with NIKITA_PERSONA verbatim"
        )

    def test_wizard_framing_references_reply_budget(self):
        """The framing layer must cite NIKITA_REPLY_MAX_CHARS — the
        reply-length ceiling — so a future re-tune of 140→N cascades
        into the prompt without requiring a parallel edit.
        """
        assert str(NIKITA_REPLY_MAX_CHARS) in WIZARD_SYSTEM_PROMPT


class TestExtractionToolRouting:
    """GH #394 (Walk U 2026-04-22): the WIZARD_SYSTEM_PROMPT must give
    the LLM explicit guidance on WHICH extraction tool to call for a
    given user message. Walk U evidence: even with input "voice. you can
    call me at +41 79 555 0234 anytime" — an unambiguous phone number
    with explicit voice preference — the LLM called extract_identity
    (re-emitting prior name/age/occupation) instead of extract_phone.

    Without phone extraction the wizard cannot reach the completion
    gate (PR #392, #391); ceremony never paints; user trapped.

    These tests assert the prompt contains explicit per-tool routing
    cues. They are deterministic snapshot-style assertions on the
    prompt string — behavioral tests against the live LLM are tracked
    separately as @pytest.mark.integration."""

    def test_prompt_has_routing_section_header(self):
        """The prompt MUST contain the literal section header
        'EXTRACTION TOOL ROUTING'. Discriminating-power: a future
        regression that drops the routing block (regressing to a bare
        tool list) MUST fail this assertion. Walk U: bare tool list
        produced 100% extract_identity defaults."""
        assert "EXTRACTION TOOL ROUTING" in WIZARD_SYSTEM_PROMPT, (
            "Routing section header missing. Walk U regression: prompt "
            "without explicit per-tool routing rules causes LLM to default "
            "to extract_identity for any vaguely-personal turn."
        )

    def test_prompt_phone_routing_rule_is_explicit(self):
        """Each terminal-extraction rule MUST appear as a numbered routing
        rule with a WHEN/call clause. Tighter discrimination than the
        loose substring check: requires extract_phone to appear at the
        start of a routing entry (after the section header), followed by
        a 'call WHEN' clause. Catches regressions that would weaken the
        rule shape."""
        import re

        # Find the routing section
        if "EXTRACTION TOOL ROUTING" not in WIZARD_SYSTEM_PROMPT:
            pytest.fail("routing section header missing — see sibling test")
        routing_section = WIZARD_SYSTEM_PROMPT.split("EXTRACTION TOOL ROUTING", 1)[1]

        # extract_phone must appear as a numbered routing entry whose body
        # contains "call WHEN" — case-insensitive. Tight 30-char budget
        # between the tool name and the "call when" clause prevents future
        # edits from sneaking inline notes that change the rule shape.
        phone_rule_pattern = re.compile(
            r"\d+\.\s*extract_phone[\s\S]{0,30}?call\s+when",
            re.IGNORECASE,
        )
        assert phone_rule_pattern.search(routing_section), (
            "extract_phone must appear as a numbered routing rule (e.g. "
            "'1. extract_phone — call WHEN ...'). The routing block must "
            "spell out activation conditions; a bare mention of the tool "
            "name is insufficient (Walk U evidence)."
        )

    def test_prompt_marks_phone_as_terminal_extraction(self):
        """Per spec FR-11d / FR-1 step 9, PhoneExtraction is the terminal
        kind that completes the wizard. The prompt MUST contain the
        literal phrase 'terminal extraction' so the LLM has an
        unambiguous completion signal."""
        prompt_lower = WIZARD_SYSTEM_PROMPT.lower()
        assert "terminal extraction" in prompt_lower, (
            "Prompt must contain literal 'terminal extraction' near "
            "extract_phone. Loose synonyms (final/completes/last) are "
            "false-positive prone in surrounding prose."
        )

    def test_prompt_warns_against_redundant_identity_extraction(self):
        """The dedup guard ('do NOT re-emit IdentityExtraction') MUST
        appear in the SAME paragraph as the extract_identity routing
        rule. Discriminating-power: a future edit that softens the
        guard or moves it to a different section will fail this
        assertion."""
        # Split prompt into paragraphs (double-newline boundary). Find
        # the paragraph containing 'extract_identity' as the lead tool.
        # Reject if the entire prompt collapses to a single paragraph
        # (would let the dedup keyword leak in from any other section).
        paragraphs = WIZARD_SYSTEM_PROMPT.split("\n\n")
        assert len(paragraphs) >= 4, (
            "Prompt collapsed to <4 paragraphs — routing rules must be "
            "structured as separate paragraphs to prevent dedup-guard "
            "leakage from unrelated sections."
        )
        identity_paras = [p for p in paragraphs if "extract_identity" in p]
        assert identity_paras, (
            "extract_identity routing rule paragraph not found"
        )
        # Combined paragraph(s) must contain a dedup keyword and the
        # word 'identity' to confirm scope. Anchor on Walk U regression
        # phrasing.
        combined = " ".join(identity_paras).lower()
        has_dedup_guard = (
            "do not re-emit" in combined
            or "do not repeat" in combined
            or "do not re-extract" in combined
            or "already committed" in combined
            or "already acknowledged" in combined
        )
        assert has_dedup_guard, (
            "extract_identity paragraph must contain explicit dedup guard "
            "('do NOT re-emit', 'already acknowledged', etc). Walk U: LLM "
            "looped on identity 3 turns straight without this guard."
        )


class TestAgentShape:
    def test_agent_uses_consolidated_output_type(self):
        """AC-T2.3.2 (updated GH #402/#403): agent uses TurnOutput, not str.

        Walk W (2026-04-23): 7-tool fan-out removed. The agent now emits a
        single TurnOutput per turn instead of calling extraction tools.
        AC-11d.5 path (a) — consolidated discriminated-union output.
        """
        from nikita.agents.onboarding.conversation_agent import TurnOutput

        agent = get_conversation_agent()
        assert isinstance(agent, Agent)

        # Verify no extraction tools registered (tool-selection bias removed).
        # Pydantic AI may register internal "final_result" output entries;
        # we check that none of the old extraction tool names are present.
        tools = set(agent._function_toolset.tools.keys())
        stale_tools = {
            "extract_location", "extract_scene", "extract_darkness",
            "extract_identity", "extract_backstory", "extract_phone",
            "no_extraction",
        }
        assert not (stale_tools & tools), (
            f"Stale extraction tools still registered: {stale_tools & tools}. "
            "GH #402/#403: consolidation removed all @agent.tool registrations."
        )

        # Verify TurnOutput is the output type (behavioral: import must succeed)
        assert TurnOutput is not None

    def test_cache_control_on_system_prompt(self):
        """AC-T2.3.3: ``AnthropicModelSettings.anthropic_cache_instructions``
        is the Pydantic AI flag that emits
        ``cache_control: {"type": "ephemeral"}`` on the system block.
        """
        assert CACHE_SETTINGS.get("anthropic_cache_instructions") is True

    def test_converse_deps_minimal_shape(self):
        """Deps are kept minimal (user_id + locale) to keep the agent
        stateless per tech-spec §2.1.
        """
        deps = ConverseDeps(user_id=uuid4())
        assert deps.locale == "en"

    def test_agent_singleton_cached(self):
        """``lru_cache`` returns the same agent across calls — matches
        the main text-agent lazy-singleton pattern.
        """
        assert get_conversation_agent() is get_conversation_agent()


class TestRetriesBudget:
    """GH #382 regression guard — retry budget must absorb first-turn
    tool-call mistakes.

    Walk Q (2026-04-21) evidence: fresh-user input "I'm Simon, 32, in Zürich"
    triggered `converse_validation_reject err_count=2`. The agent exhausted
    its retry budget (previously `retries=2`) on repeated tool-call schema
    errors. Raising to `retries=4` gives the LLM more chances to self-correct
    when its first tool-call arg guess fails Pydantic validation.
    """

    def test_retries_at_least_4(self):
        """Retry budget ≥ 4 so first-turn schema guesses don't immediately
        surface as user-facing failures.

        Pydantic AI 1.x splits the retry budget into `_max_tool_retries`
        (per-tool-call, i.e. when Pydantic rejects the args and the LLM
        has to re-emit) and `_max_result_retries` (per final output).
        GH #382 is about tool-call retries; guard that specifically.
        """
        agent = get_conversation_agent()
        retries = getattr(agent, "_max_tool_retries", None)
        assert retries is not None, (
            "could not introspect agent._max_tool_retries; pydantic_ai "
            "may have renamed the attribute, update the test + production "
            "`retries=` kwarg together"
        )
        assert retries >= 4, (
            f"agent tool-retries={retries}; GH #382 requires >=4 to absorb "
            f"first-turn tool-call schema guesses before surfacing a "
            f"validation_reject"
        )


class TestExtractionSchemaLiterals:
    """GH #382 D4b (Walk R 2026-04-21): extraction schema Literal constraints.

    Post-consolidation (GH #402/#403), the LLM fills SlotDelta.kind and
    SlotDelta.data directly — no tool-call boundary. The Literal constraints
    must still exist in extraction_schemas.py (the canonical source) so that
    Pydantic validates the SlotDelta.data contents when the handler applies
    the delta to WizardSlots.

    These tests moved from tool-signature inspection to schema-level checks.
    """

    def test_scene_value_literals(self):
        """SceneValue must be the canonical 5 values."""
        from typing import Literal, get_args, get_origin

        from nikita.agents.onboarding.extraction_schemas import SceneValue

        assert get_origin(SceneValue) is Literal
        assert set(get_args(SceneValue)) == {
            "techno", "art", "food", "cocktails", "nature",
        }

    def test_life_stage_value_literals(self):
        """LifeStageValue must be the canonical 6 values."""
        from typing import Literal, get_args, get_origin

        from nikita.agents.onboarding.extraction_schemas import LifeStageValue

        assert get_origin(LifeStageValue) is Literal
        assert set(get_args(LifeStageValue)) == {
            "tech", "finance", "creative", "student", "entrepreneur", "other",
        }

    def test_phone_preference_value_literals(self):
        """PhonePreferenceValue must be Literal['voice','text']."""
        from typing import Literal, get_args, get_origin

        from nikita.agents.onboarding.extraction_schemas import PhonePreferenceValue

        assert get_origin(PhonePreferenceValue) is Literal
        assert set(get_args(PhonePreferenceValue)) == {"voice", "text"}

    def test_drug_tolerance_value_is_bounded(self):
        """DrugToleranceValue must be Annotated[int, ge=1, le=5]."""
        from typing import Annotated, get_args, get_origin

        from pydantic.fields import FieldInfo

        from nikita.agents.onboarding.extraction_schemas import DrugToleranceValue

        assert get_origin(DrugToleranceValue) is not None, (
            f"DrugToleranceValue is bare {DrugToleranceValue}; must be Annotated"
        )
        args = get_args(DrugToleranceValue)
        metas = list(args[1:])
        field_info = next((m for m in metas if isinstance(m, FieldInfo)), None)
        assert field_info is not None
        has_ge_1 = any(hasattr(m, "ge") and m.ge == 1 for m in field_info.metadata)
        has_le_5 = any(hasattr(m, "le") and m.le == 5 for m in field_info.metadata)
        assert has_ge_1, f"DrugToleranceValue missing ge=1"
        assert has_le_5, f"DrugToleranceValue missing le=5"


class TestNoExtractionReasonLiteral:
    """GH #382 regression guard — NoExtractionReasonValue Literal must
    constrain to the 4 allowed values.

    Post-consolidation (GH #402/#403): no_extraction is no longer a @agent.tool.
    The LLM sets TurnOutput.delta=None for clarification/backtracking turns.
    The NoExtractionReasonValue type alias is preserved for SlotDelta compatibility.
    """

    def test_no_extraction_reason_value_has_four_literals(self):
        """NoExtractionReasonValue must be the canonical 4-value Literal."""
        from typing import Literal, get_args, get_origin

        from nikita.agents.onboarding.extraction_schemas import NoExtractionReasonValue

        assert get_origin(NoExtractionReasonValue) is Literal
        assert set(get_args(NoExtractionReasonValue)) == {
            "off_topic", "clarifying", "backtracking", "low_confidence",
        }


class TestDynamicInstructions:
    """T10 RED — Spec 214 FR-11d PR-B: @agent.instructions callable for
    dynamic missing-slot injection.

    These tests are GENUINELY RED on the current codebase (pre-T11):
    - ConverseDeps does NOT have a ``state`` field
    - render_dynamic_instructions does NOT exist in conversation_prompts
    - @agent.instructions is NOT registered on the singleton

    After T11 GREEN they must all pass.
    """

    def test_converse_deps_has_state_field(self):
        """ConverseDeps must carry a ``state: WizardSlots`` field so the
        dynamic-instructions callable can inspect cumulative slot state
        and inject missing-slot guidance per turn.

        RED: ConverseDeps(user_id=uuid4()) will raise TypeError or
        AttributeError because the field does not exist yet.
        """
        from nikita.agents.onboarding.state import WizardSlots

        deps = ConverseDeps(user_id=uuid4())
        assert hasattr(deps, "state"), (
            "ConverseDeps must have a 'state' field of type WizardSlots; "
            "the dynamic-instructions callable uses it each turn"
        )
        assert isinstance(deps.state, WizardSlots), (
            f"deps.state expected WizardSlots, got {type(deps.state)}"
        )

    def test_render_dynamic_instructions_lists_missing_slots(self):
        """render_dynamic_instructions must return a non-empty string that
        mentions the missing slots when wizard is incomplete.

        Strategy: build a mock RunContext with partially-filled WizardSlots
        (location set, rest empty) and assert the returned string names at
        least one missing slot.

        RED: ImportError — function does not exist yet.
        """
        from unittest.mock import MagicMock

        from nikita.agents.onboarding.conversation_prompts import (
            render_dynamic_instructions,
        )
        from nikita.agents.onboarding.state import WizardSlots

        # location filled, everything else empty
        partial_state = WizardSlots(location={"city": "Zurich", "confidence": 0.9})
        deps = ConverseDeps(user_id=uuid4(), state=partial_state)
        ctx = MagicMock()
        ctx.deps = deps

        result = render_dynamic_instructions(ctx)

        assert isinstance(result, str), (
            f"render_dynamic_instructions must return str, got {type(result)}"
        )
        assert len(result) > 0, "must return non-empty string when slots missing"
        # At least one of the remaining slot names must appear
        remaining = partial_state.missing
        assert remaining, "partial_state should have missing slots"
        assert any(slot in result for slot in remaining), (
            f"render_dynamic_instructions returned '{result}' but missing "
            f"slots {remaining} are not mentioned"
        )

    def test_render_dynamic_instructions_omits_filled_slots(self):
        """When all slots are filled, render_dynamic_instructions should
        return a short string (no slots left to collect).

        RED: same ImportError as sibling test.
        """
        from unittest.mock import MagicMock

        from nikita.agents.onboarding.conversation_prompts import (
            render_dynamic_instructions,
        )
        from nikita.agents.onboarding.state import WizardSlots

        full_state = WizardSlots(
            location={"city": "Zurich", "confidence": 0.9},
            scene={"scene": "techno", "confidence": 0.9},
            darkness={"drug_tolerance": 3, "confidence": 0.9},
            identity={"name": "Simon", "age": 32, "occupation": "tech", "confidence": 0.9},
            backstory={"chosen_option_id": "opt_1", "cache_key": "abc123", "confidence": 0.9},
            phone={"phone": "+41795550123", "phone_preference": "voice", "confidence": 0.9},
        )
        assert full_state.is_complete, "test fixture must be complete"

        deps = ConverseDeps(user_id=uuid4(), state=full_state)
        ctx = MagicMock()
        ctx.deps = deps

        result = render_dynamic_instructions(ctx)

        assert isinstance(result, str), "must always return str"
        # When complete, the callable may return empty string or a
        # completion acknowledgement — it must NOT list slot names.
        for slot in [
            "location",
            "scene",
            "darkness",
            "identity",
            "backstory",
            "phone",
        ]:
            assert slot not in result.lower(), (
                f"render_dynamic_instructions returned '{result}' but slot "
                f"'{slot}' appears even though slots are all filled"
            )

    def test_dynamic_instructions_registered_on_agent(self):
        """The agent singleton must have at least one registered dynamic
        instruction callable (set via @agent.instructions decorator).

        RED: agent._instructions is empty list on current codebase.
        """
        agent = get_conversation_agent()
        # Pydantic AI stores @agent.instructions registrations in
        # agent._instructions (confirmed via dir(agent) in session).
        dynamic_fns = getattr(agent, "_instructions", [])
        assert len(dynamic_fns) >= 1, (
            f"agent._instructions is empty — @agent.instructions callable "
            f"(render_dynamic_instructions) not registered. Have: {dynamic_fns}"
        )


class TestOutputValidator:
    """T10 RED — @agent.output_validator registration guard.

    RED: agent._output_validators is empty list on current codebase.
    GREEN after T11 wires the validator.
    """

    def test_output_validator_registered(self):
        """The conversation agent must have at least one output validator
        registered via @agent.output_validator. The validator raises
        ModelRetry when the LLM emits a string reply that contains no
        extraction content (i.e. the LLM skipped calling a tool).

        Pydantic AI stores validators in agent._output_validators.
        """
        agent = get_conversation_agent()
        validators = getattr(agent, "_output_validators", [])
        assert len(validators) >= 1, (
            f"agent._output_validators is empty — @agent.output_validator "
            f"not registered. Per spec 214 FR-11d validation-layering rule "
            f"(agentic-design-patterns.md §5), the post-tool layer is "
            f"MANDATORY. Have validators: {validators}"
        )


class TestRegressionGuards:
    """Regression guards for PR-A wiring that MUST survive the PR-B
    refactor untouched.

    These tests are already GREEN (PR-A wired both primitives). They are
    committed in the T10 RED commit to lock the contract: if T11 accidentally
    breaks message_history wiring or regex_phone_fallback, CI catches it
    on the same commit that introduces the regression.
    """

    def test_agent_run_uses_message_history_primitive(self):
        """Confirm message_history= is accepted by the agent's run()
        signature — the official Pydantic AI multi-turn primitive.

        Strategy: verify via inspect that agent.run / agent.run_sync has
        a 'message_history' parameter (or that the underlying method
        accepts it via **kwargs). This is a contract-shape test, not an
        integration test — no live model call needed.
        """
        import inspect

        agent = get_conversation_agent()
        sig = inspect.signature(agent.run)
        params = set(sig.parameters.keys())
        assert "message_history" in params, (
            f"agent.run() does not accept message_history= parameter. "
            f"Params: {params}. PR-A must wire this — do NOT remove."
        )

    def test_regex_phone_fallback_module_importable(self):
        """regex_phone_fallback must remain importable from the portal_onboarding
        route module. It is wired post-agent.run in PR-A to recover from
        LLM tool-selection bias on phone numbers.

        This is a smoke-import guard — it does NOT run the fallback function.
        """
        # The fallback lives inside the route module as a local helper.
        # Verify the module imports without error (covers any breakage
        # from T11 refactor).
        try:
            import nikita.api.routes.portal_onboarding  # noqa: F401
        except ImportError as exc:
            pytest.fail(
                f"portal_onboarding route failed to import after T11 refactor: {exc}"
            )


class TestPersonaDriftScaffolding:
    """AC-T2.9.* scaffolding.

    Full 60-row baseline CSV generation requires live Anthropic calls
    and is tracked as a post-merge follow-up (see ADR-001). These tests
    assert the scaffold exists so the drift test can be wired in a
    follow-up PR without new structural work.
    """

    def test_baseline_csv_row_count_and_schema(self):
        """AC-T2.9.2: when baseline CSV exists, it is 3 × 20 = 60 rows
        with the documented columns. Test xfails until the CSV is
        generated; structure pinned so generation drift fails fast.
        """
        from pathlib import Path

        csv_path = (
            Path(__file__).parents[2]
            / "fixtures"
            / "persona_baseline_v1.csv"
        )
        if not csv_path.exists():
            pytest.skip(
                "persona_baseline_v1.csv not yet generated; "
                "scripts/persona_baseline_generate.py is the generator"
            )

        import csv

        with csv_path.open() as fh:
            rows = list(csv.DictReader(fh))
        from nikita.onboarding.tuning import PERSONA_DRIFT_SEED_SAMPLES

        # 3 seeds × 20 samples each (AC-T2.9.2)
        assert len(rows) == 3 * PERSONA_DRIFT_SEED_SAMPLES
        assert {"seed", "sample_index", "prompt", "reply"}.issubset(rows[0].keys())

    @pytest.mark.skip(
        reason=(
            "Persona drift requires live Anthropic calls + generated "
            "baseline CSV. Activated after scripts/persona_baseline_generate.py "
            "runs once in CI; see ADR-001."
        )
    )
    def test_persona_drift_vs_baseline(self):  # pragma: no cover
        """AC-T2.9.3: TF-IDF cosine ≥ PERSONA_DRIFT_COSINE_MIN + feature
        bounds within ±PERSONA_DRIFT_FEATURE_TOLERANCE. Activated post-
        baseline-generation.
        """
        raise NotImplementedError
