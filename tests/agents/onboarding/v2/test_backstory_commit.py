"""Spec 218 Slice 218-6 — backstory commit tests (RED).

Tests `nikita/agents/onboarding/v2/backstory_commit.py`:

1. `generate_v2_backstory(slots, phase2_messages)` returns a non-empty str
   (used as `CompleteAsk.backstory_preview`).
2. Generated string is ≤ 560 chars (CompleteAsk.backstory_preview max_length).
3. Function is idempotent under retry (same args → same result when mocked).
4. Function raises `BackstoryGenerationError` on LLM failure, not a
   raw Pydantic AI exception (isolates callers from agent internals).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from nikita.agents.onboarding.v2.backstory_commit import (
    BackstoryGenerationError,
    generate_v2_backstory,
)
from nikita.agents.onboarding.v2.state import WizardSlotsV2


def _slots() -> WizardSlotsV2:
    return WizardSlotsV2(
        display_name={"display_name": "Sam"},
        age={"age": 25},
        city={"city": "Austin"},
        occupation={"occupation": "Software Engineer"},
        primary_hobbies={"primary_hobbies": ["hiking", "cooking"]},
        hangouts_personalized={"hangouts_personalized": ["coffee shops", "trails"]},
        voice_or_text={"voice_or_text": "text"},
        saturday_morning={"saturday_morning": "long run then eggs"},
        darkness_level={"darkness_level": 3},
        geek_out_on={"geek_out_on": "distributed systems"},
    )


SAMPLE_PHASE2_MESSAGES = [
    {"role": "assistant", "content": "What's the most spontaneous thing you've done?"},
    {"role": "user", "content": "Booked a flight to Japan on a Friday night."},
    {
        "role": "assistant",
        "content": "Love that. What pulled you there specifically?",
    },
    {"role": "user", "content": "The food, the trains, the aesthetic."},
]


class TestGenerateV2Backstory:
    @pytest.mark.asyncio
    async def test_returns_non_empty_string(self) -> None:
        """generate_v2_backstory returns a non-empty backstory preview."""
        preview = "You live by impulse — booking flights, chasing flavors, always moving."

        with patch(
            "nikita.agents.onboarding.v2.backstory_commit._run_backstory_agent",
            new=AsyncMock(return_value=preview),
        ):
            result = await generate_v2_backstory(
                _slots(), SAMPLE_PHASE2_MESSAGES
            )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_result_within_max_length(self) -> None:
        """Preview must fit CompleteAsk.backstory_preview max_length=560."""
        # 520-char preview
        long_preview = "x" * 520

        with patch(
            "nikita.agents.onboarding.v2.backstory_commit._run_backstory_agent",
            new=AsyncMock(return_value=long_preview),
        ):
            result = await generate_v2_backstory(
                _slots(), SAMPLE_PHASE2_MESSAGES
            )

        assert len(result) <= 560

    @pytest.mark.asyncio
    async def test_raises_backstory_generation_error_on_llm_failure(
        self,
    ) -> None:
        """LLM failure is wrapped in BackstoryGenerationError, not re-raised raw."""
        with patch(
            "nikita.agents.onboarding.v2.backstory_commit._run_backstory_agent",
            side_effect=RuntimeError("model timeout"),
        ):
            with pytest.raises(BackstoryGenerationError):
                await generate_v2_backstory(_slots(), SAMPLE_PHASE2_MESSAGES)

    @pytest.mark.asyncio
    async def test_empty_phase2_messages_does_not_raise(self) -> None:
        """Phase-2 messages may be empty (e.g. forced complete at turn 0 in tests).
        generate_v2_backstory must handle this gracefully."""
        preview = "You're an engineer who loves the outdoors."

        with patch(
            "nikita.agents.onboarding.v2.backstory_commit._run_backstory_agent",
            new=AsyncMock(return_value=preview),
        ):
            result = await generate_v2_backstory(_slots(), [])

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_result_truncated_to_560_if_agent_returns_too_long(
        self,
    ) -> None:
        """If agent returns > 560 chars, generate_v2_backstory truncates at 560."""
        too_long = "x" * 600

        with patch(
            "nikita.agents.onboarding.v2.backstory_commit._run_backstory_agent",
            new=AsyncMock(return_value=too_long),
        ):
            result = await generate_v2_backstory(_slots(), SAMPLE_PHASE2_MESSAGES)

        assert len(result) <= 560
