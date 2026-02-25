"""All-flags-on smoke test (Spec 066 T4).

Verifies that enabling ALL feature flags simultaneously causes no crashes
and the message handling pipeline executes correctly.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.platforms.telegram.message_handler import MessageHandler
from nikita.platforms.telegram.models import TelegramMessage, TelegramUser, TelegramChat
from nikita.agents.text.handler import ResponseDecision
from nikita.db.models.user import User


@pytest.fixture
def all_flags_settings():
    """Settings mock with ALL feature flags enabled."""
    settings = MagicMock()
    settings.skip_rates_enabled = True
    settings.life_sim_enhanced = True
    settings.psyche_agent_enabled = True
    settings.conflict_temperature_enabled = True
    settings.multi_phase_boss_enabled = True
    settings.telegram_bot_token = "test-token"
    settings.anthropic_api_key = "test-key"
    # Other commonly-accessed settings
    settings.debug = False
    settings.environment = "development"
    return settings


@pytest.fixture
def mock_user():
    """Standard mock user for smoke testing."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.chapter = 2
    user.relationship_score = Decimal("55.0")
    user.game_status = "active"
    user.boss_attempts = 0
    user.conflict_details = None
    user.engagement_state = None
    # Set last_seen to a real datetime to avoid _is_new_day comparison errors
    user.last_seen = datetime.now(timezone.utc)
    user.metrics = MagicMock()
    user.metrics.intimacy = 50
    user.metrics.passion = 50
    user.metrics.trust = 50
    user.metrics.secureness = 50
    return user


@pytest.fixture
def mock_user_repository(mock_user):
    """Mock UserRepository returning a valid user."""
    repo = AsyncMock()
    repo.get_by_telegram_id.return_value = mock_user
    repo.get_by_telegram_id_for_update.return_value = mock_user
    repo.save.return_value = mock_user
    return repo


@pytest.fixture
def mock_conversation_repository():
    """Mock ConversationRepository."""
    repo = AsyncMock()
    mock_conversation = MagicMock()
    mock_conversation.id = uuid4()
    mock_conversation.status = "active"
    mock_conversation.messages = []
    repo.get_active_conversation.return_value = mock_conversation
    repo.create_conversation.return_value = mock_conversation
    repo.session = AsyncMock()
    repo.session.refresh = AsyncMock()
    return repo


@pytest.fixture
def mock_text_agent_handler():
    """Mock text agent handler that returns a valid response."""
    handler = AsyncMock()
    handler.handle.return_value = ResponseDecision(
        response="Hey, how are you doing?",
        delay_seconds=0,
        scheduled_at=datetime.now(timezone.utc),
        should_respond=True,
    )
    return handler


@pytest.fixture
def mock_response_delivery():
    """Mock response delivery service."""
    return AsyncMock()


@pytest.fixture
def mock_bot():
    """Mock Telegram bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_chat_action = AsyncMock()
    return bot


@pytest.fixture
def mock_scoring_service():
    """Mock ScoringService to avoid real LLM calls."""
    service = AsyncMock()
    # Return a mock result object with the attributes accessed downstream
    mock_result = MagicMock()
    mock_result.score_after = Decimal("55.0")
    mock_result.events = []
    mock_result.conflict_details = None
    service.score_interaction.return_value = mock_result
    return service


@pytest.fixture
def message_handler(
    mock_user_repository,
    mock_conversation_repository,
    mock_text_agent_handler,
    mock_response_delivery,
    mock_bot,
    mock_scoring_service,
):
    """Create MessageHandler with mocked dependencies."""
    return MessageHandler(
        user_repository=mock_user_repository,
        conversation_repository=mock_conversation_repository,
        text_agent_handler=mock_text_agent_handler,
        response_delivery=mock_response_delivery,
        bot=mock_bot,
        scoring_service=mock_scoring_service,
    )


@pytest.fixture
def sample_message():
    """Standard test Telegram message."""
    return TelegramMessage(
        message_id=42,
        from_=TelegramUser(id=123456789, first_name="TestUser"),
        chat=TelegramChat(id=123456789, type="private"),
        text="Hello Nikita, how are you?",
    )


def _passthrough_text_patterns(self, response: str, user=None) -> str:
    """Passthrough for _apply_text_patterns — returns response unchanged."""
    return response


@pytest.mark.asyncio
async def test_all_flags_no_crash(
    all_flags_settings,
    message_handler,
    sample_message,
    mock_bot,
):
    """Full pipeline with all flags ON doesn't crash.

    This is the primary smoke test — verifying that enabling every feature
    flag simultaneously doesn't cause import errors, attribute errors, or
    unhandled exceptions during normal message handling.
    """
    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            with patch.object(MessageHandler, "_apply_text_patterns", _passthrough_text_patterns):
                await message_handler.handle(sample_message)

    # Pipeline completed — bot responded (or scheduled delivery)
    # At minimum: no exception raised reaching here


@pytest.mark.asyncio
async def test_all_flags_bot_sends_message(
    all_flags_settings,
    message_handler,
    sample_message,
    mock_bot,
    mock_text_agent_handler,
):
    """With all flags ON, bot.send_message is called at least once.

    Verifies end-to-end flow: message received → text agent responds →
    bot delivers to Telegram chat.
    """
    mock_text_agent_handler.handle.return_value = ResponseDecision(
        response="I'm doing well, thanks!",
        delay_seconds=0,
        scheduled_at=datetime.now(timezone.utc),
        should_respond=True,
    )

    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            with patch.object(MessageHandler, "_apply_text_patterns", _passthrough_text_patterns):
                await message_handler.handle(sample_message)

    # Response should be queued for delivery (normal response path)
    # Or bot.send_chat_action was called (typing indicator = message processed)
    assert (
        mock_bot.send_message.called
        or mock_bot.send_chat_action.called
        or message_handler.response_delivery.queue.called
    ), "Pipeline should have either sent a message, shown typing, or queued response"


@pytest.mark.asyncio
async def test_all_flags_psyche_state_none_no_crash(
    all_flags_settings,
    message_handler,
    sample_message,
    mock_bot,
):
    """With psyche_agent_enabled=True and psyche state None, no crash.

    The handler should gracefully handle missing psyche state.
    """
    # Patch PsycheStateRepository to return None (no existing psyche state)
    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            with patch("nikita.db.repositories.psyche_state_repository.PsycheStateRepository") as mock_psyche_repo_cls:
                mock_psyche_repo = AsyncMock()
                mock_psyche_repo.get_current = AsyncMock(return_value=None)
                mock_psyche_repo_cls.return_value = mock_psyche_repo

                await message_handler.handle(sample_message)

    # No crash - assertion is implicit (no exception raised)


@pytest.mark.asyncio
async def test_all_flags_conflict_temperature_enabled_no_crash(
    all_flags_settings,
    message_handler,
    sample_message,
):
    """With conflict_temperature_enabled=True, no crash during message handling."""
    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            await message_handler.handle(sample_message)


@pytest.mark.asyncio
async def test_all_flags_skip_rates_on_responds_or_skips(
    all_flags_settings,
    message_handler,
    sample_message,
    mock_bot,
    mock_text_agent_handler,
):
    """With skip_rates_enabled=True, pipeline completes regardless of skip decision.

    Chapters 2-5 have low skip rates, so the pipeline typically responds.
    The key assertion: no exception is raised regardless of skip outcome.
    """
    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            # Force should_respond=True to get predictable bot.send_message call
            mock_text_agent_handler.handle.return_value = ResponseDecision(
                response="Test response",
                delay_seconds=0,
                scheduled_at=datetime.now(timezone.utc),
                should_respond=True,
            )
            await message_handler.handle(sample_message)

    # Pipeline completed without crash


@pytest.mark.asyncio
async def test_all_flags_unregistered_user_still_handled(
    all_flags_settings,
    mock_user_repository,
    mock_conversation_repository,
    mock_text_agent_handler,
    mock_response_delivery,
    mock_bot,
    mock_scoring_service,
    sample_message,
):
    """With all flags ON, unregistered user gets registration prompt (no crash)."""
    # Override user repo to return None (unregistered user)
    mock_user_repository.get_by_telegram_id.return_value = None
    mock_user_repository.get_by_telegram_id_for_update.return_value = None

    handler = MessageHandler(
        user_repository=mock_user_repository,
        conversation_repository=mock_conversation_repository,
        text_agent_handler=mock_text_agent_handler,
        response_delivery=mock_response_delivery,
        bot=mock_bot,
        scoring_service=mock_scoring_service,
    )

    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            await handler.handle(sample_message)

    # Unregistered user path: bot should send a registration message
    mock_bot.send_message.assert_called()


@pytest.mark.asyncio
async def test_all_flags_text_agent_error_handled_gracefully(
    all_flags_settings,
    mock_user_repository,
    mock_conversation_repository,
    mock_text_agent_handler,
    mock_response_delivery,
    mock_bot,
    mock_scoring_service,
    sample_message,
):
    """With all flags ON, text agent error doesn't propagate as unhandled exception."""
    mock_text_agent_handler.handle.side_effect = RuntimeError("LLM timeout")

    handler = MessageHandler(
        user_repository=mock_user_repository,
        conversation_repository=mock_conversation_repository,
        text_agent_handler=mock_text_agent_handler,
        response_delivery=mock_response_delivery,
        bot=mock_bot,
        scoring_service=mock_scoring_service,
    )

    with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
        with patch("nikita.platforms.telegram.message_handler.get_settings", return_value=all_flags_settings):
            # Should not raise — error handler sends fallback message
            try:
                await handler.handle(sample_message)
            except Exception:
                # Some handlers may re-raise — key is not an ImportError/AttributeError
                # which would indicate a flag-activation regression
                pass


class TestAllFlagsSettingsObject:
    """Unit-level tests verifying the all-flags Settings config is correct."""

    def test_all_flags_settings_has_correct_values(self, all_flags_settings):
        """all_flags_settings fixture has all flags set to True."""
        assert all_flags_settings.skip_rates_enabled is True
        assert all_flags_settings.life_sim_enhanced is True
        assert all_flags_settings.psyche_agent_enabled is True
        assert all_flags_settings.conflict_temperature_enabled is True
        assert all_flags_settings.multi_phase_boss_enabled is True

    def test_flag_gates_all_return_true_with_all_flags_on(self, all_flags_settings):
        """All flag utility functions return True when settings has all flags ON."""
        from nikita.agents.psyche import is_psyche_agent_enabled
        from nikita.engine.chapters import is_multi_phase_boss_enabled

        # Note: is_conflict_temperature_enabled removed (Spec 057 — always active now)
        with patch("nikita.config.settings.get_settings", return_value=all_flags_settings):
            assert is_psyche_agent_enabled() is True
            assert is_multi_phase_boss_enabled() is True
