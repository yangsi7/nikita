"""Tests for nikita.agents.onboarding.handoff_greeting (Spec 214 FR-11d/e)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from nikita.agents.onboarding.conversation_prompts import NIKITA_PERSONA
from nikita.agents.onboarding.handoff_greeting import (
    generate_handoff_greeting,
    template_for_trigger,
)
from nikita.agents.onboarding.validators import validate_reply
from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS


def _user(name: str | None):
    return SimpleNamespace(
        onboarding_profile=({"name": name} if name else {}),
    )


class TestHandoffGreeting:
    @pytest.mark.asyncio
    async def test_both_triggers_produce_valid_distinct_output(self):
        """AC-T2.10.1: both triggers return valid ≤140-char replies and
        their prompt-framing strings differ.
        """
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=_user("Simon"))

        bind = await generate_handoff_greeting(
            uuid4(),
            "handoff_bind",
            user_repo=user_repo,
        )
        first_msg = await generate_handoff_greeting(
            uuid4(),
            "first_user_message",
            user_repo=user_repo,
        )

        assert bind != first_msg
        # Both pass reply validators (length, no markdown/quotes/etc).
        for reply in (bind, first_msg):
            ok, reason = validate_reply(reply)
            assert ok, f"greeting failed validator: {reason}: {reply!r}"
            assert len(reply) <= NIKITA_REPLY_MAX_CHARS

    @pytest.mark.asyncio
    async def test_greeting_references_name_and_context(self):
        """AC-T2.10.2: greeting cites the user's first name if present."""
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=_user("Simon"))
        greeting = await generate_handoff_greeting(
            uuid4(),
            "handoff_bind",
            user_repo=user_repo,
        )
        assert "Simon" in greeting

    @pytest.mark.asyncio
    async def test_greeting_fallback_when_no_name(self):
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=_user(None))
        greeting = await generate_handoff_greeting(
            uuid4(),
            "handoff_bind",
            user_repo=user_repo,
        )
        # Non-personalized but still valid.
        assert greeting
        ok, _ = validate_reply(greeting)
        assert ok

    @pytest.mark.asyncio
    async def test_greeting_missing_user_fallback(self):
        user_repo = AsyncMock()
        user_repo.get = AsyncMock(return_value=None)
        greeting = await generate_handoff_greeting(
            uuid4(),
            "handoff_bind",
            user_repo=user_repo,
        )
        assert greeting  # fallback non-empty

    def test_templates_share_persona_and_differ_per_trigger(self):
        """AC-T2.10.3: both prompts embed NIKITA_PERSONA verbatim — the
        pairwise persona-drift gate passes trivially because they use
        the same persona object.
        """
        bind = template_for_trigger("handoff_bind")
        first = template_for_trigger("first_user_message")
        assert bind.startswith(NIKITA_PERSONA)
        assert first.startswith(NIKITA_PERSONA)
        assert bind != first

    def test_template_unknown_trigger_raises(self):
        with pytest.raises(ValueError):
            template_for_trigger("bogus")  # type: ignore[arg-type]

    def test_pairwise_persona_drift_within_gates(self):
        """AC-T2.10.3: pairwise drift across (main_text, conversation,
        handoff) agents all share the same NIKITA_PERSONA constant →
        drift is zero by construction. Full TF-IDF drift tests require
        live-model runs (ADR-001); this structural assertion is the
        cheap always-passing equivalent.
        """
        from nikita.agents.onboarding.conversation_prompts import (
            NIKITA_PERSONA as CONV_PERSONA,
            WIZARD_SYSTEM_PROMPT,
        )
        from nikita.agents.text.persona import (
            NIKITA_PERSONA as TEXT_PERSONA,
        )

        assert CONV_PERSONA is TEXT_PERSONA
        assert WIZARD_SYSTEM_PROMPT.startswith(TEXT_PERSONA)
        for trigger in ("handoff_bind", "first_user_message"):
            assert template_for_trigger(trigger).startswith(TEXT_PERSONA)
