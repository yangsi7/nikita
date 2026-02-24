"""Tests for narrative arc refs in summaries — Spec 104 Story 2.

SummaryStage includes active arcs in LLM prompt.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_active_arcs_returns_arc_strings():
    """ThoughtRepository.get_active_arcs returns list of arc strings."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    # Mock get_active_thoughts to return arc-typed thoughts
    arc1 = MagicMock(content="He's opening up about his past")
    arc2 = MagicMock(content="Trust rebuilding after argument")

    with patch.object(repo, "get_active_thoughts", return_value=[arc1, arc2]):
        arcs = await repo.get_active_arcs(uuid4())

    assert len(arcs) == 2
    assert arcs[0] == "He's opening up about his past"
    assert arcs[1] == "Trust rebuilding after argument"


@pytest.mark.asyncio
async def test_summary_includes_arcs_in_prompt():
    """SummaryStage._summarize_with_llm includes 'Active storylines' when arcs present."""
    from nikita.pipeline.stages.summary import SummaryStage

    stage = SummaryStage()

    messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    arcs = ["He's opening up about his past", "Trust rebuilding"]

    with patch("pydantic_ai.Agent") as MockAgent:
        mock_result = MagicMock()
        mock_result.output = "Summary text"
        mock_result.data = "Summary text"
        MockAgent.return_value.run = AsyncMock(return_value=mock_result)

        await stage._summarize_with_llm(messages, active_arcs=arcs)

        # Check that Agent was created with system_prompt containing arc content
        agent_init_kwargs = MockAgent.call_args
        system_prompt = agent_init_kwargs.kwargs.get("system_prompt", "")
        assert "Active storylines" in system_prompt


@pytest.mark.asyncio
async def test_summary_without_arcs_still_works():
    """SummaryStage works normally when no arcs present."""
    from nikita.pipeline.stages.summary import SummaryStage

    stage = SummaryStage()

    messages = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]

    with patch("pydantic_ai.Agent") as MockAgent:
        mock_result = MagicMock()
        mock_result.output = "Summary text"
        mock_result.data = "Summary text"
        MockAgent.return_value.run = AsyncMock(return_value=mock_result)

        result = await stage._summarize_with_llm(messages)

        assert result == "Summary text"
