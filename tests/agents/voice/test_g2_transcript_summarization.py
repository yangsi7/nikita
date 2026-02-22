"""Tests for G2: LLM Transcript Summarization (Spec 072).

Verifies _summarize_via_llm() calls the LLM and returns a non-empty
summary capturing: what was discussed, emotional tone, commitments/plans.

TDD: Tests written before implementation.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.models import TranscriptData, TranscriptEntry
from datetime import datetime, timezone


@pytest.fixture
def positive_transcript_text():
    return (
        "nikita: Hey! I was just thinking about you. How's your day going?\n"
        "user: Pretty great! I finally finished that big project.\n"
        "nikita: That's amazing! I knew you could do it.\n"
        "user: Thanks, want to celebrate this weekend?\n"
        "nikita: Absolutely! Let's plan something special."
    )


@pytest.fixture
def short_transcript_text():
    return (
        "nikita: Hey!\n"
        "user: Sorry, bad time."
    )


@pytest.fixture
def empty_transcript_text():
    return ""


class TestSummarizeViaLLM:
    """Test TranscriptManager._summarize_via_llm()."""

    @pytest.mark.asyncio
    async def test_returns_nonempty_string_on_success(self, positive_transcript_text):
        """LLM call returns a non-empty summary string."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        mock_result = MagicMock()
        mock_output = MagicMock()
        mock_output.summary = (
            "The user completed a major project. Nikita was supportive and celebratory. "
            "They plan to celebrate together this weekend."
        )
        mock_result.output = mock_output

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        # Agent is imported inside the function, so patch pydantic_ai.Agent
        with patch("pydantic_ai.Agent", return_value=mock_agent):
            result = await manager._summarize_via_llm(positive_transcript_text)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_returns_empty_string_on_empty_input(self, empty_transcript_text):
        """Empty transcript text returns empty string without calling LLM."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock()

        # For empty input, LLM is never called — no patch needed
        result = await manager._summarize_via_llm(empty_transcript_text)

        assert result == ""

    @pytest.mark.asyncio
    async def test_summary_captures_content(self, positive_transcript_text):
        """Summary captures the discussion content."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        expected_summary = "User finished a project. Positive, celebratory tone. Plans to celebrate weekend."

        mock_result = MagicMock()
        mock_output = MagicMock()
        mock_output.summary = expected_summary
        mock_result.output = mock_output

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        with patch("pydantic_ai.Agent", return_value=mock_agent):
            result = await manager._summarize_via_llm(positive_transcript_text)

        assert result == expected_summary

    @pytest.mark.asyncio
    async def test_handles_llm_exception_gracefully(self, positive_transcript_text):
        """When LLM call fails, returns empty string without raising."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        with patch("pydantic_ai.Agent", return_value=mock_agent):
            result = await manager._summarize_via_llm(positive_transcript_text)

        assert result == ""

    @pytest.mark.asyncio
    async def test_llm_agent_is_called_once(self, positive_transcript_text):
        """LLM agent run() is called exactly once per invocation."""
        from nikita.agents.voice.transcript import TranscriptManager

        manager = TranscriptManager(session=None)

        mock_result = MagicMock()
        mock_output = MagicMock()
        mock_output.summary = "Summary here."
        mock_result.output = mock_output

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        with patch("pydantic_ai.Agent", return_value=mock_agent):
            await manager._summarize_via_llm(positive_transcript_text)

        mock_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_end_to_end(self):
        """generate_summary() orchestrates correctly: builds text and calls _summarize_via_llm."""
        from nikita.agents.voice.transcript import TranscriptManager
        from nikita.agents.voice.models import TranscriptData, TranscriptEntry
        from datetime import datetime, timezone

        base_time = datetime.now(timezone.utc)
        transcript = TranscriptData(
            session_id="voice_test_001",
            entries=[
                TranscriptEntry(speaker="nikita", text="How are you?", timestamp=base_time),
                TranscriptEntry(speaker="user", text="Doing well, thanks!", timestamp=base_time),
            ],
            user_turns=1,
            nikita_turns=1,
        )

        manager = TranscriptManager(session=None)
        expected_summary = "Brief positive check-in call."

        with patch.object(manager, "_summarize_via_llm", new_callable=AsyncMock, return_value=expected_summary) as mock_summarize:
            result = await manager.generate_summary(transcript)

        assert result == expected_summary
        mock_summarize.assert_called_once()
        # Verify the text passed contains both turns
        call_text = mock_summarize.call_args[0][0]
        assert "nikita" in call_text
        assert "user" in call_text

    @pytest.mark.asyncio
    async def test_generate_summary_returns_none_on_empty(self):
        """generate_summary() returns None for empty transcripts."""
        from nikita.agents.voice.transcript import TranscriptManager
        from nikita.agents.voice.models import TranscriptData

        transcript = TranscriptData(
            session_id="voice_empty",
            entries=[],
            user_turns=0,
            nikita_turns=0,
        )

        manager = TranscriptManager(session=None)

        with patch.object(manager, "_summarize_via_llm", new_callable=AsyncMock, return_value="") as mock_summarize:
            result = await manager.generate_summary(transcript)

        assert result is None
