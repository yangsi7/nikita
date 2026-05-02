"""Anti-pattern regression guards (B1+B2 ship-gate).

Per ``.claude/rules/agentic-design-patterns.md`` — 4 hard rules guarded
by static AST/grep checks:

- Rule #2: no `complete = True/False` boolean literal in handler code
- Rule #3: no `extract_*` per-slot @agent.tool registrations
- Rule #4: no `_compute_progress(latest_kind)` per-turn function
- Rule #6: no static-routing rules in conversation_prompts.py

These are FAST static checks; they do not exercise the live agent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(rel_path: str) -> str:
    return (_REPO_ROOT / rel_path).read_text()


class TestNoProgressPctComputeFunction:
    """Rule #4 guard: no per-turn `_compute_progress(latest_kind)` function."""

    def test_no_compute_progress_in_portal_onboarding(self):
        src = _read("nikita/api/routes/portal_onboarding.py")
        assert not re.search(
            r"\bdef\s+_compute_progress\s*\(", src
        ), "_compute_progress per-turn function resurrected (Rule #4 violation)"

    def test_no_compute_progress_in_agents_onboarding(self):
        # Check all .py files under nikita/agents/onboarding/
        agents_dir = _REPO_ROOT / "nikita" / "agents" / "onboarding"
        for path in agents_dir.glob("*.py"):
            src = path.read_text()
            assert not re.search(
                r"\bdef\s+_compute_progress\s*\(", src
            ), f"_compute_progress in {path}: Rule #4 violation"


class TestNoExtractStarTools:
    """Rule #3 guard: no `extract_*` @agent.tool registrations remain."""

    def test_no_extract_star_tool_decorators(self):
        src = _read("nikita/agents/onboarding/conversation_agent.py")
        # Look for `@agent.tool` followed by `def extract_*(`
        # Allow function with name `_validate_output` etc.
        forbidden_names = [
            "extract_location",
            "extract_scene",
            "extract_darkness",
            "extract_identity",
            "extract_backstory",
            "extract_phone",
            "extract_no_extraction",
        ]
        for name in forbidden_names:
            assert not re.search(
                rf"\bdef\s+{name}\s*\(", src
            ), f"{name} per-tool function still registered (Rule #3 violation)"


class TestNoCompletionBooleanLiteral:
    """Rule #2 guard: no `complete = True / False` literals in handler code."""

    def test_no_hardcoded_complete_in_portal_onboarding(self):
        """Check portal_onboarding.py route handler code."""
        src = _read("nikita/api/routes/portal_onboarding.py")
        # The pattern `\bconversation_complete\s*=\s*(True|False)\b` would
        # indicate a hardcoded gate. Allow `conversation_complete = slots.is_complete`
        # which delegates to FinalForm.
        assert not re.search(
            r"\bconversation_complete\s*=\s*(True|False)\b", src
        ), "hardcoded conversation_complete True/False literal (Rule #2 violation)"


class TestNoStaticRoutingInSystemPrompt:
    """Rule #6 guard: conversation_prompts.py has no _WIZARD_FRAMING /
    WIZARD_SYSTEM_PROMPT static-routing block.

    The regex matches actual code definitions / assignments rather than
    docstring or comment references — this lets the rewrite docstring
    legitimately mention the deleted symbols by name.
    """

    def test_no_wizard_framing_definition(self):
        src = _read("nikita/agents/onboarding/conversation_prompts.py")
        # Match assignment `_WIZARD_FRAMING = ...` not docstring/comment refs.
        assert not re.search(
            r"^_WIZARD_FRAMING\s*[:=]", src, flags=re.MULTILINE
        ), (
            "_WIZARD_FRAMING assignment resurrected — routing rules must live in "
            "inject_per_turn_context callable, not static prompt (Rule #6)"
        )

    def test_no_wizard_system_prompt_definition(self):
        src = _read("nikita/agents/onboarding/conversation_prompts.py")
        assert not re.search(
            r"^WIZARD_SYSTEM_PROMPT\s*[:=]", src, flags=re.MULTILINE
        ), (
            "WIZARD_SYSTEM_PROMPT assignment resurrected — routing rules must "
            "live in inject_per_turn_context callable, not static prompt (Rule #6)"
        )

    def test_no_render_dynamic_instructions_definition(self):
        src = _read("nikita/agents/onboarding/conversation_prompts.py")
        assert not re.search(
            r"^def\s+render_dynamic_instructions\s*\(", src, flags=re.MULTILINE
        ), (
            "render_dynamic_instructions def resurrected — should be inject_per_turn_context"
        )
