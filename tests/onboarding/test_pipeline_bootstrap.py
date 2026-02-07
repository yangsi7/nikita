"""Tests for Spec 043 T2.2: Onboarding pipeline bootstrap.

Verifies that execute_handoff() triggers a pipeline run after
sending the first message, and that failures are non-blocking.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.handoff import HandoffManager


class TestPipelineBootstrap:
    """T3.4: Onboarding bootstrap tests."""

    @pytest.fixture
    def manager(self):
        manager = HandoffManager()
        manager._message_generator = MagicMock()
        manager._message_generator.generate = MagicMock(return_value="Hey there, babe!")
        return manager

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.mark.asyncio
    async def test_execute_handoff_triggers_pipeline_bootstrap(self, manager, user_id):
        """AC-3.4.1: execute_handoff() triggers pipeline bootstrap."""
        manager._send_first_message = AsyncMock(return_value={"success": True})
        manager._update_user_status = AsyncMock()
        manager._get_user_telegram_id = AsyncMock(return_value=12345)
        manager._bootstrap_pipeline = AsyncMock()

        result = await manager.execute_handoff(
            user_id=user_id,
            call_id="test-call",
            profile=MagicMock(),
            user_name="TestUser",
            telegram_id=12345,
        )

        assert result.success is True
        manager._bootstrap_pipeline.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_pipeline_failure_does_not_fail_handoff(self, manager, user_id):
        """AC-3.4.2: Pipeline failure does not fail handoff."""
        manager._send_first_message = AsyncMock(return_value={"success": True})
        manager._update_user_status = AsyncMock()
        manager._get_user_telegram_id = AsyncMock(return_value=12345)
        manager._bootstrap_pipeline = AsyncMock(
            side_effect=Exception("Pipeline exploded")
        )

        result = await manager.execute_handoff(
            user_id=user_id,
            call_id="test-call",
            profile=MagicMock(),
            user_name="TestUser",
            telegram_id=12345,
        )

        # Handoff should still succeed even though pipeline failed
        assert result.success is True
        assert result.first_message_sent is True

    @pytest.mark.asyncio
    async def test_bootstrap_pipeline_processes_conversation(self, user_id):
        """AC-3.4.3: Pipeline generates prompts for new user."""
        manager = HandoffManager()

        mock_conv = MagicMock()
        mock_conv.id = uuid4()

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_recent_for_user = AsyncMock(return_value=[mock_conv])

        mock_orchestrator = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_orchestrator.process = AsyncMock(return_value=mock_result)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch(
                 "nikita.config.settings.get_settings"
             ) as mock_settings_fn, \
             patch(
                 "nikita.db.database.get_session_maker"
             ) as mock_gsm, \
             patch(
                 "nikita.db.repositories.conversation_repository.ConversationRepository",
                 return_value=mock_conv_repo,
             ), \
             patch(
                 "nikita.pipeline.orchestrator.PipelineOrchestrator",
                 return_value=mock_orchestrator,
             ):
            mock_settings = MagicMock()
            mock_settings.unified_pipeline_enabled = True
            mock_settings_fn.return_value = mock_settings

            mock_gsm.return_value = MagicMock(return_value=mock_session)

            await manager._bootstrap_pipeline(user_id)

        mock_orchestrator.process.assert_called_once_with(
            conversation_id=mock_conv.id,
            user_id=user_id,
            platform="text",
        )
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bootstrap_skipped_if_flag_disabled(self, user_id):
        """AC-3.4.4: Bootstrap skipped if flag disabled."""
        manager = HandoffManager()

        with patch("nikita.config.settings.get_settings") as mock_settings_fn:
            mock_settings = MagicMock()
            mock_settings.unified_pipeline_enabled = False
            mock_settings_fn.return_value = mock_settings

            # Should return without error, no pipeline triggered
            await manager._bootstrap_pipeline(user_id)
