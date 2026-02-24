"""Tests for boss judgment prompt formatting — PR 76 Review R1.

Verifies player_context appears AFTER JSON examples, not concatenated inside them.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_player_context_not_inside_json_example():
    """R1: player_context must appear after the JSON example block, not inside it."""
    from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

    judgment = BossJudgment()

    with patch("pydantic_ai.Agent") as MockAgent:
        mock_result_obj = MagicMock()
        mock_result_obj.output = JudgmentResult(outcome="PASS", reasoning="Good", confidence=0.85)
        MockAgent.return_value.run = AsyncMock(return_value=mock_result_obj)

        await judgment.judge_boss_outcome(
            user_message="I care about you",
            conversation_history=[],
            chapter=3,
            boss_prompt={"success_criteria": "Show trust", "challenge_context": "Boss"},
            vice_profile={"dark_humor": 0.6},
            engagement_state="invested",
        )

        system_prompt = MockAgent.call_args.kwargs.get("system_prompt", "")

        # The FAIL JSON example line must NOT contain "PLAYER PERSONALITY CONTEXT"
        for line in system_prompt.split("\n"):
            if '"outcome": "FAIL"' in line:
                assert "PLAYER PERSONALITY CONTEXT" not in line, (
                    f"player_context is concatenated inside JSON example line: {line}"
                )

        # player_context section must still exist in the prompt
        assert "PLAYER PERSONALITY CONTEXT" in system_prompt
        assert "dark_humor" in system_prompt
        assert "invested" in system_prompt


@pytest.mark.asyncio
async def test_no_player_context_when_no_vices():
    """R1: Without vice_profile/engagement_state, no PLAYER PERSONALITY CONTEXT section."""
    from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

    judgment = BossJudgment()

    with patch("pydantic_ai.Agent") as MockAgent:
        mock_result_obj = MagicMock()
        mock_result_obj.output = JudgmentResult(outcome="PASS", reasoning="Good", confidence=0.9)
        MockAgent.return_value.run = AsyncMock(return_value=mock_result_obj)

        await judgment.judge_boss_outcome(
            user_message="Hello",
            conversation_history=[],
            chapter=1,
            boss_prompt={"success_criteria": "Show curiosity", "challenge_context": "Test"},
        )

        system_prompt = MockAgent.call_args.kwargs.get("system_prompt", "")
        assert "PLAYER PERSONALITY CONTEXT" not in system_prompt
