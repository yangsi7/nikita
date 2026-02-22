"""Tests for boss judgment context injection — Spec 104 Story 5.

Inject vice profile + engagement state into judge prompt.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_judge_accepts_context_params():
    """judge_boss_outcome accepts vice_profile and engagement_state kwargs."""
    from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

    judgment = BossJudgment()

    mock_result = JudgmentResult(outcome="PASS", reasoning="Good response", confidence=0.9)

    with patch.object(judgment, "_call_llm", return_value=mock_result) as mock_llm:
        result = await judgment.judge_boss_outcome(
            user_message="I really care about you",
            conversation_history=[],
            chapter=2,
            boss_prompt={"success_criteria": "Show vulnerability", "challenge_context": "Test"},
            vice_profile={"dark_humor": 0.6, "vulnerability": 0.8},
            engagement_state="invested",
        )

    assert result.outcome == "PASS"
    mock_llm.assert_called_once()
    # Verify context params were forwarded to _call_llm
    call_kwargs = mock_llm.call_args.kwargs
    assert call_kwargs.get("vice_profile") == {"dark_humor": 0.6, "vulnerability": 0.8}
    assert call_kwargs.get("engagement_state") == "invested"


@pytest.mark.asyncio
async def test_judge_prompt_includes_player_context():
    """When vices passed, prompt includes 'PLAYER PERSONALITY CONTEXT' section."""
    from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

    judgment = BossJudgment()

    # Patch Agent at source (imported inside _call_llm)
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

        # Check Agent was created with system_prompt containing player context
        agent_call = MockAgent.call_args
        system_prompt = agent_call.kwargs.get("system_prompt", "")
        assert "PLAYER PERSONALITY CONTEXT" in system_prompt
        assert "dark_humor" in system_prompt
        assert "invested" in system_prompt


@pytest.mark.asyncio
async def test_judge_backward_compatible_without_context():
    """Without context params (backward compat), judgment still works."""
    from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

    judgment = BossJudgment()

    mock_result = JudgmentResult(outcome="FAIL", reasoning="No engagement", confidence=0.9)

    with patch.object(judgment, "_call_llm", return_value=mock_result):
        result = await judgment.judge_boss_outcome(
            user_message="whatever",
            conversation_history=[],
            chapter=1,
            boss_prompt={"success_criteria": "Show curiosity", "challenge_context": "Test"},
        )

    assert result.outcome == "FAIL"
