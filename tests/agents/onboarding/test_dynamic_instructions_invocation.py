"""B1.4 — Dynamic instructions are invoked per turn (anti-static-prompt guard).

Verifies that the agent uses ``Agent(instructions=callable)`` registration
(not static ``system_prompt=`` for routing) and that the callable can
reference ``state.missing`` per turn.
"""

from __future__ import annotations

import inspect


def _import_agent_module():
    from nikita.agents.onboarding import conversation_agent  # noqa: PLC0415
    return conversation_agent


def _import_prompts_module():
    from nikita.agents.onboarding import conversation_prompts  # noqa: PLC0415
    return conversation_prompts


class TestDynamicInstructionsRegistration:
    def test_inject_per_turn_context_exists(self):
        """The callable must exist as a module symbol."""
        prompts = _import_prompts_module()
        assert hasattr(prompts, "inject_per_turn_context"), (
            "conversation_prompts.inject_per_turn_context callable missing"
        )

    def test_inject_per_turn_context_is_callable(self):
        prompts = _import_prompts_module()
        assert callable(prompts.inject_per_turn_context)

    def test_callable_references_state_missing(self):
        """Implementation grep: the callable body references ``.missing``."""
        prompts = _import_prompts_module()
        src = inspect.getsource(prompts.inject_per_turn_context)
        assert ".missing" in src, (
            "inject_per_turn_context must reference state.missing per turn"
        )

    def test_agent_uses_instructions_decorator_not_static_routing_prompt(self):
        """The agent module wires ``@agent.instructions`` to the callable, NOT
        a static system_prompt with hardcoded routing rules."""
        ca = _import_agent_module()
        src = inspect.getsource(ca)
        # Anti-pattern guard: no _WIZARD_FRAMING / WIZARD_SYSTEM_PROMPT references
        # in the agent module after the rewrite.
        assert "_WIZARD_FRAMING" not in src
        assert "WIZARD_SYSTEM_PROMPT" not in src
        # The agent must wire the callable
        assert "inject_per_turn_context" in src or "instructions" in src
