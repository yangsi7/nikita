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


class TestAgentShape:
    def test_agent_has_six_tools_and_types(self):
        """AC-T2.3.2: six extraction tools + NoExtraction sentinel."""
        agent = get_conversation_agent()
        assert isinstance(agent, Agent)

        # Pydantic AI 1.x exposes registered tools via the internal
        # ``_function_toolset.tools`` dict; each ``@agent.tool_plain``
        # registration adds an entry keyed by function name.
        tools = list(agent._function_toolset.tools.keys())
        # 6 extraction tools + 1 no_extraction sentinel = 7.
        expected = {
            "extract_location",
            "extract_scene",
            "extract_darkness",
            "extract_identity",
            "extract_backstory",
            "extract_phone",
            "no_extraction",
        }
        assert expected.issubset(set(tools)), (
            f"missing tools — have {tools}, need {expected}"
        )

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
        surface as user-facing failures."""
        agent = get_conversation_agent()
        # Pydantic AI stores `retries` on the internal Agent config; exposed
        # via the `.retries` attribute or via the internal config object.
        retries = getattr(agent, "_default_retries", None)
        if retries is None:  # newer pydantic_ai exposes via ._config
            retries = getattr(getattr(agent, "_config", None), "retries", None)
        assert retries is not None, (
            "could not introspect agent.retries; update test if pydantic_ai "
            "renamed the attribute"
        )
        assert retries >= 4, (
            f"agent retries={retries}; GH #382 requires >=4 to absorb first-turn "
            f"tool-call schema guesses before surfacing a validation_reject"
        )


class TestNoExtractionToolSignature:
    """GH #382 regression guard — `no_extraction` tool signature must
    constrain `reason` to the Literal set defined in the schema.

    Root cause D4 (Walk Q deep trace): the tool signature declared
    `reason: str` with no Literal enforcement, so when the LLM emitted
    `no_extraction(reason="greeting")` (or any unknown value), the
    string flowed past the tool boundary into
    `NoExtraction.model_validate({"reason": reason})` which then raised
    ValidationError. The retry loop repeated the same error.
    """

    def test_no_extraction_tool_enforces_literal_reason(self):
        """Tool parameter schema must constrain `reason` to the 4
        Literal values; Pydantic AI will then reject at the tool-call
        boundary and the retry error message will self-explain.
        """
        import inspect
        from typing import Literal, get_args, get_origin

        from nikita.agents.onboarding.conversation_agent import (
            _create_conversation_agent,
        )

        agent = _create_conversation_agent()
        tool = agent._function_toolset.tools["no_extraction"]
        sig = inspect.signature(tool.function)
        reason_param = sig.parameters["reason"]
        ann = reason_param.annotation
        # Default may be wrapped in typing.Literal; accept either a bare
        # Literal[...] annotation or a Literal with a default value.
        assert get_origin(ann) is Literal, (
            f"no_extraction.reason annotation is {ann}; must be "
            f"Literal['off_topic','clarifying','backtracking','low_confidence']"
        )
        assert set(get_args(ann)) == {
            "off_topic",
            "clarifying",
            "backtracking",
            "low_confidence",
        }, f"Literal values drifted: got {get_args(ann)}"


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
