"""Tests for Spec 043 T2.2: Onboarding pipeline bootstrap.

Verifies that execute_handoff() triggers a pipeline run after
sending the first message, and that failures are non-blocking.

Note: Pipeline bootstrap runs as a background task via asyncio.create_task()
to avoid Cloud Run timeouts (ONBOARD-TIMEOUT fix).
Tests use asyncio.sleep(0) to yield control and let tasks complete.
"""

import asyncio
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
        # GH onboarding-pipeline-bootstrap: mock the conversation seed
        seed_conv_id = uuid4()
        manager._seed_conversation = AsyncMock(return_value=seed_conv_id)

        result = await manager.execute_handoff(
            user_id=user_id,
            call_id="test-call",
            profile=MagicMock(),
            user_name="TestUser",
            telegram_id=12345,
        )

        # Let background task complete
        await asyncio.sleep(0)

        assert result.success is True
        manager._seed_conversation.assert_called_once()
        manager._bootstrap_pipeline.assert_called_once_with(
            user_id, conversation_id=seed_conv_id
        )

    @pytest.mark.asyncio
    async def test_pipeline_failure_does_not_fail_handoff(self, manager, user_id):
        """AC-3.4.2: Pipeline failure does not fail handoff."""
        manager._send_first_message = AsyncMock(return_value={"success": True})
        manager._update_user_status = AsyncMock()
        manager._get_user_telegram_id = AsyncMock(return_value=12345)
        manager._bootstrap_pipeline = AsyncMock(
            side_effect=Exception("Pipeline exploded")
        )
        manager._seed_conversation = AsyncMock(return_value=uuid4())

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
        mock_conv_repo.get_recent = AsyncMock(return_value=[mock_conv])

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user_repo = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

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
                 "nikita.db.repositories.user_repository.UserRepository",
                 return_value=mock_user_repo,
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
            conversation=mock_conv,
            user=mock_user,
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

    @pytest.mark.asyncio
    async def test_bootstrap_pipeline_with_conversation_id_skips_get_recent(
        self, user_id
    ):
        """GH onboarding-pipeline-bootstrap: When conversation_id is provided,
        fetch by ID directly — skip get_recent."""
        manager = HandoffManager()

        mock_conv = MagicMock()
        mock_conv.id = uuid4()

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get = AsyncMock(return_value=mock_conv)
        mock_conv_repo.get_recent = AsyncMock()  # Should NOT be called

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user_repo = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

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
                 "nikita.db.repositories.user_repository.UserRepository",
                 return_value=mock_user_repo,
             ), \
             patch(
                 "nikita.pipeline.orchestrator.PipelineOrchestrator",
                 return_value=mock_orchestrator,
             ):
            mock_settings = MagicMock()
            mock_settings.unified_pipeline_enabled = True
            mock_settings_fn.return_value = mock_settings

            mock_gsm.return_value = MagicMock(return_value=mock_session)

            await manager._bootstrap_pipeline(
                user_id, conversation_id=mock_conv.id
            )

        # get() called with the conversation_id, NOT get_recent()
        mock_conv_repo.get.assert_called_once_with(mock_conv.id)
        mock_conv_repo.get_recent.assert_not_called()
        mock_orchestrator.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_bootstrap_pipeline_without_conversation_id_uses_get_recent(
        self, user_id
    ):
        """GH onboarding-pipeline-bootstrap: Backward compat — when no
        conversation_id, fall back to get_recent."""
        manager = HandoffManager()

        mock_conv = MagicMock()
        mock_conv.id = uuid4()

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_recent = AsyncMock(return_value=[mock_conv])

        mock_user = MagicMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

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
                 "nikita.db.repositories.user_repository.UserRepository",
                 return_value=mock_user_repo,
             ), \
             patch(
                 "nikita.pipeline.orchestrator.PipelineOrchestrator",
                 return_value=mock_orchestrator,
             ):
            mock_settings = MagicMock()
            mock_settings.unified_pipeline_enabled = True
            mock_settings_fn.return_value = mock_settings

            mock_gsm.return_value = MagicMock(return_value=mock_session)

            # No conversation_id — uses get_recent
            await manager._bootstrap_pipeline(user_id)

        mock_conv_repo.get_recent.assert_called_once_with(user_id, limit=1)
        mock_orchestrator.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handoff_seeds_conversation_before_bootstrap(
        self, manager, user_id
    ):
        """GH onboarding-pipeline-bootstrap: execute_handoff calls
        _seed_conversation before _bootstrap_pipeline."""
        call_order = []

        async def mock_seed(*args, **kwargs):
            call_order.append("seed")
            return uuid4()

        async def mock_bootstrap(*args, **kwargs):
            call_order.append("bootstrap")

        manager._send_first_message = AsyncMock(return_value={"success": True})
        manager._seed_conversation = mock_seed
        manager._bootstrap_pipeline = mock_bootstrap

        result = await manager.execute_handoff(
            user_id=user_id,
            telegram_id=12345,
            profile=MagicMock(),
            user_name="TestUser",
        )

        await asyncio.sleep(0)  # Let background task complete

        assert result.success is True
        assert call_order[0] == "seed"  # Seed runs before bootstrap

    @pytest.mark.asyncio
    async def test_voice_handoff_triggers_pipeline_bootstrap(self, manager, user_id):
        """GH onboarding-pipeline-bootstrap Bug 4 fix: voice callback
        path now triggers _bootstrap_pipeline."""
        manager._seed_conversation = AsyncMock(return_value=uuid4())
        manager._bootstrap_pipeline = AsyncMock()

        with patch.object(
            manager,
            "initiate_nikita_callback",
            return_value={"success": True, "conversation_id": "conv_voice"},
        ):
            result = await manager.execute_handoff_with_voice_callback(
                user_id=user_id,
                telegram_id=12345,
                phone_number="+14155551234",
                profile=MagicMock(),
                callback_delay_seconds=0,
            )

        await asyncio.sleep(0)

        assert result.success is True
        assert result.nikita_callback_initiated is True
        manager._seed_conversation.assert_called_once()
        manager._bootstrap_pipeline.assert_called_once()
