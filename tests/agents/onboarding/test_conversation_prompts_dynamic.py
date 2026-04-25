"""Tests for T-F2c.7 — render_dynamic_instructions wires Question Registry.

Covers:
- Empty state → contains location hint substring + "STILL MISSING"
- All-required-filled → returns ""
- Partial state → "NEXT QUESTION (darkness)" + verbatim hint substring
- Verbatim hint match from ORDERED_QUESTIONS
- Does not raise when ctx.deps.state is None
- Opportunistic footer iff missing non-empty
"""
from __future__ import annotations

from unittest.mock import MagicMock


def _import_prompts():
    from nikita.agents.onboarding.conversation_prompts import (  # noqa: PLC0415
        render_dynamic_instructions,
    )
    return render_dynamic_instructions


def _import_slots():
    from nikita.agents.onboarding.state import SlotDelta, WizardSlots  # noqa: PLC0415
    return SlotDelta, WizardSlots


def _make_ctx(state):
    """Build a minimal mock RunContext[ConverseDeps] with deps.state set."""
    ctx = MagicMock()
    ctx.deps.state = state
    return ctx


def _full_slots():
    """Return WizardSlots with all 6 required slots filled."""
    SlotDelta, WizardSlots = _import_slots()
    slots = WizardSlots()
    for delta in [
        SlotDelta(kind="location", data={"city": "Berlin"}),
        SlotDelta(kind="scene", data={"scene": "techno"}),
        SlotDelta(kind="darkness", data={"drug_tolerance": 3}),
        SlotDelta(kind="identity", data={"name": "Sam", "age": 28, "occupation": "artist"}),
        SlotDelta(kind="backstory", data={"chosen_option_id": "abc", "cache_key": "berlin|techno|3"}),
        SlotDelta(kind="phone", data={"phone_preference": "text", "phone": None}),
    ]:
        slots = slots.apply(delta)
    return slots


class TestRenderDynamicInstructions:
    def test_empty_state_contains_still_missing(self):
        """Empty state output contains 'STILL MISSING' with all required slots."""
        render_dynamic_instructions = _import_prompts()
        _, WizardSlots = _import_slots()
        ctx = _make_ctx(WizardSlots())
        result = render_dynamic_instructions(ctx)
        assert "STILL MISSING" in result

    def test_empty_state_contains_location_hint(self):
        """Empty state → NEXT QUESTION hint for location is present."""
        render_dynamic_instructions = _import_prompts()
        _, WizardSlots = _import_slots()
        ctx = _make_ctx(WizardSlots())
        result = render_dynamic_instructions(ctx)
        # The hint for location from ORDERED_QUESTIONS
        assert "where are you" in result.lower() or "NEXT QUESTION (location)" in result

    def test_all_required_filled_returns_empty_string(self):
        """All-required-filled → render_dynamic_instructions returns ''."""
        render_dynamic_instructions = _import_prompts()
        ctx = _make_ctx(_full_slots())
        result = render_dynamic_instructions(ctx)
        assert result == ""

    def test_partial_state_location_scene_filled_next_question_darkness(self):
        """After location+scene filled, output contains 'NEXT QUESTION (darkness)'."""
        render_dynamic_instructions = _import_prompts()
        SlotDelta, WizardSlots = _import_slots()
        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Berlin"}))
        slots = slots.apply(SlotDelta(kind="scene", data={"scene": "techno"}))
        ctx = _make_ctx(slots)
        result = render_dynamic_instructions(ctx)
        assert "NEXT QUESTION (darkness)" in result

    def test_partial_state_contains_darkness_hint_substring(self):
        """After location+scene filled, output contains verbatim hint for darkness."""
        render_dynamic_instructions = _import_prompts()
        SlotDelta, WizardSlots = _import_slots()
        from nikita.agents.onboarding.question_registry import ORDERED_QUESTIONS  # noqa: PLC0415
        darkness_hint = next(q.hint for q in ORDERED_QUESTIONS if q.slot == "darkness")

        slots = WizardSlots()
        slots = slots.apply(SlotDelta(kind="location", data={"city": "Berlin"}))
        slots = slots.apply(SlotDelta(kind="scene", data={"scene": "techno"}))
        ctx = _make_ctx(slots)
        result = render_dynamic_instructions(ctx)
        assert darkness_hint in result

    def test_does_not_raise_when_state_is_none(self):
        """render_dynamic_instructions does not raise when ctx.deps.state is None."""
        render_dynamic_instructions = _import_prompts()
        ctx = _make_ctx(None)
        result = render_dynamic_instructions(ctx)  # must not raise
        assert isinstance(result, str)

    def test_opportunistic_footer_present_when_missing_nonempty(self):
        """Opportunistic footer appears when required slots are still missing."""
        render_dynamic_instructions = _import_prompts()
        _, WizardSlots = _import_slots()
        ctx = _make_ctx(WizardSlots())  # all missing
        result = render_dynamic_instructions(ctx)
        # Footer must contain vibe or personality_archetype guidance
        assert "vibe" in result or "personality_archetype" in result

    def test_opportunistic_footer_absent_when_all_required_filled(self):
        """No opportunistic footer when wizard is complete (missing is empty)."""
        render_dynamic_instructions = _import_prompts()
        ctx = _make_ctx(_full_slots())
        result = render_dynamic_instructions(ctx)
        assert result == ""
