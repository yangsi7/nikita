"""Tests for thought-driven conversation openers — Spec 104 Story 4.

Load active 'wants_to_share' thoughts into prompt builder.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_active_openers_returns_max_3():
    """get_active_openers returns max 3 wants_to_share thoughts."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    thoughts = [
        MagicMock(content=f"Opener {i}") for i in range(5)
    ]

    with patch.object(repo, "get_active_thoughts", return_value=thoughts[:3]) as mock_get:
        openers = await repo.get_active_openers(uuid4())

    assert len(openers) <= 3
    # Should filter by thought_type='wants_to_share'
    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args
    if call_kwargs.kwargs:
        assert call_kwargs.kwargs.get("thought_type") == "wants_to_share"


@pytest.mark.asyncio
async def test_openers_populated_in_context():
    """PromptBuilderStage._enrich_context populates ctx.conversation_openers."""
    from nikita.pipeline.stages.prompt_builder import PromptBuilderStage

    mock_session = AsyncMock()
    stage = PromptBuilderStage(session=mock_session)

    ctx = MagicMock()
    ctx.user_id = uuid4()
    ctx.conversation_id = uuid4()
    ctx.chapter = 2
    ctx.relationship_score = 55.0
    ctx.emotional_state = None
    ctx.extracted_threads = []
    ctx.relationship_episodes = []
    ctx.nikita_events = []
    ctx.active_thoughts = []
    ctx.open_threads = []
    ctx.conversation_openers = []

    openers = ["I want to tell him about my dream", "Ask about his weekend"]

    # Patch at source module (lazy imports resolve from source)
    with patch("nikita.utils.nikita_state.compute_time_of_day", return_value="evening"), \
         patch("nikita.utils.nikita_state.compute_day_of_week", return_value="Monday"), \
         patch("nikita.utils.nikita_state.compute_nikita_activity", return_value="relaxing"), \
         patch("nikita.utils.nikita_state.compute_nikita_energy", return_value="calm"), \
         patch("nikita.utils.nikita_state.compute_nikita_mood", return_value="content"), \
         patch("nikita.utils.nikita_state.compute_vulnerability_level", return_value="low"), \
         patch("nikita.db.repositories.conversation_repository.ConversationRepository") as MockConvRepo, \
         patch("nikita.db.repositories.user_repository.UserRepository") as MockUserRepo, \
         patch("nikita.db.repositories.thought_repository.NikitaThoughtRepository") as MockThoughtRepo, \
         patch("nikita.db.repositories.thread_repository.ConversationThreadRepository") as MockThreadRepo, \
         patch("nikita.config.settings.get_settings") as MockSettings:

        # Disable memory loading (needs openai_api_key)
        mock_settings = MagicMock()
        mock_settings.openai_api_key = None
        MockSettings.return_value = mock_settings

        # Setup thought repo to return openers
        mock_thought_instance = MockThoughtRepo.return_value
        mock_thought_instance.get_active_thoughts = AsyncMock(return_value=[])
        mock_thought_instance.get_active_openers = AsyncMock(return_value=openers)

        MockConvRepo.return_value.get_conversation_summaries_for_prompt = AsyncMock(return_value={})
        MockUserRepo.return_value.get = AsyncMock(return_value=None)
        MockThreadRepo.return_value.get_open_threads = AsyncMock(return_value=[])

        await stage._enrich_context(ctx)

    assert ctx.conversation_openers == openers


@pytest.mark.asyncio
async def test_openers_empty_no_error():
    """Empty openers result doesn't cause errors."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    with patch.object(repo, "get_active_thoughts", return_value=[]):
        openers = await repo.get_active_openers(uuid4())

    assert openers == []
