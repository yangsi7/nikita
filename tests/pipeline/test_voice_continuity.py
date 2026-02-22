"""Tests for Spec 106 I14: Cross-platform conversation continuity.

Voice conversation summaries should appear in text agent context,
enabling Nikita to reference voice interactions during text chats.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.db.repositories.conversation_repository import ConversationRepository


class TestGetRecentVoiceSummaries:
    """Test ConversationRepository.get_recent_voice_summaries()."""

    @pytest.mark.asyncio
    async def test_voice_summaries_loaded(self):
        """Mock repository returns voice summaries."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.all.return_value = [
            ("You talked about your day at work",),
            ("Late night call about fears and dreams",),
        ]
        session.execute.return_value = result_mock

        repo = ConversationRepository(session)
        summaries = await repo.get_recent_voice_summaries(user_id=uuid4(), limit=3)

        assert len(summaries) == 2
        assert "day at work" in summaries[0]
        assert "fears and dreams" in summaries[1]

    @pytest.mark.asyncio
    async def test_no_voice_summaries_graceful(self):
        """No voice conversations returns empty list."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.all.return_value = []
        session.execute.return_value = result_mock

        repo = ConversationRepository(session)
        summaries = await repo.get_recent_voice_summaries(user_id=uuid4())

        assert summaries == []

    @pytest.mark.asyncio
    async def test_voice_summaries_in_template_vars(self):
        """Verify voice_summaries key appears in prompt builder template vars."""
        from datetime import datetime, timezone
        from nikita.pipeline.stages.prompt_builder import PromptBuilderStage
        from nikita.pipeline.models import PipelineContext

        ctx = PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            platform="text",
            started_at=datetime.now(timezone.utc),
        )
        # Simulate enrichment having set voice_summaries
        ctx.voice_summaries = ["Voice call about work", "Late night chat"]

        stage = PromptBuilderStage(session=None)
        template_vars = stage._build_template_vars(ctx, "text")

        assert "voice_summaries" in template_vars
        assert len(template_vars["voice_summaries"]) == 2
