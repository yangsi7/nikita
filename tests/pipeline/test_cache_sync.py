"""Tests for Spec 043 T1.2: Voice prompt cache sync in PromptBuilder.

Verifies that _store_prompt() syncs voice prompts to both
ready_prompts table AND user.cached_voice_prompt.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.pipeline.models import PipelineContext


class TestVoicePromptCacheSync:
    """T3.2: Voice prompt cache sync tests."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def builder(self, mock_session):
        from nikita.pipeline.stages.prompt_builder import PromptBuilderStage

        stage = PromptBuilderStage(session=mock_session)
        return stage

    @pytest.fixture
    def ctx(self):
        return PipelineContext(
            conversation_id=uuid4(),
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
            platform="text",
            chapter=2,
            relationship_score=Decimal("55"),
            game_status="active",
            vices=["dark_humor"],
            engagement_state="engaged",
            metrics={"intimacy": Decimal("55"), "passion": Decimal("60"),
                     "trust": Decimal("50"), "secureness": Decimal("45")},
        )

    @pytest.mark.asyncio
    async def test_voice_prompt_stored_in_ready_prompts(self, builder, ctx, mock_session):
        """AC-3.2.1: Voice prompt stored in ready_prompts table."""
        mock_repo = AsyncMock()
        mock_repo.set_current = AsyncMock()

        # Mock the sync method to avoid needing UserRepository
        builder._sync_cached_voice_prompt = AsyncMock()

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            await builder._store_prompt(ctx, "voice", "test voice prompt", 100, 50.0)

        mock_repo.set_current.assert_called_once()
        call_kwargs = mock_repo.set_current.call_args.kwargs
        assert call_kwargs["platform"] == "voice"
        assert call_kwargs["prompt_text"] == "test voice prompt"

    @pytest.mark.asyncio
    async def test_voice_prompt_synced_to_cached_voice_prompt(self, builder, ctx, mock_session):
        """AC-3.2.2: Voice prompt synced to user.cached_voice_prompt."""
        mock_user = MagicMock()
        mock_user.cached_voice_prompt = None
        mock_user.cached_voice_prompt_at = None

        mock_user_repo = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        with patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ):
            await builder._sync_cached_voice_prompt(ctx.user_id, "synced voice prompt")

        assert mock_user.cached_voice_prompt == "synced voice prompt"
        assert mock_user.cached_voice_prompt_at is not None

    @pytest.mark.asyncio
    async def test_text_prompt_not_synced_to_cached_voice_prompt(self, builder, ctx, mock_session):
        """AC-3.2.3: Text prompt NOT synced to cached_voice_prompt (voice only)."""
        mock_repo = AsyncMock()
        mock_repo.set_current = AsyncMock()

        builder._sync_cached_voice_prompt = AsyncMock()

        with patch(
            "nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository",
            return_value=mock_repo,
        ):
            await builder._store_prompt(ctx, "text", "text prompt", 100, 50.0)

        builder._sync_cached_voice_prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_failure_does_not_fail_pipeline(self, builder, ctx, mock_session):
        """AC-3.2.4: Sync failure does not fail the pipeline stage."""
        # Test that _sync_cached_voice_prompt catches its own exceptions
        with patch(
            "nikita.db.repositories.user_repository.UserRepository",
            side_effect=Exception("DB connection failed"),
        ):
            # Should NOT raise
            await builder._sync_cached_voice_prompt(ctx.user_id, "test prompt")
