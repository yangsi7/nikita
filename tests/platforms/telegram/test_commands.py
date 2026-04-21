"""Tests for CommandHandler - WRITTEN FIRST (TDD Red phase).

These tests verify command routing and handling for Telegram bot commands.
AC Coverage: AC-FR003-001, AC-T009.1-5, GH-#160
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nikita.platforms.telegram.commands import CommandHandler
from nikita.db.models.user import User
from decimal import Decimal
from uuid import uuid4


class TestCommandHandler:
    """Test suite for Telegram command handler."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock UserRepository for testing."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_telegram_auth(self):
        """Mock TelegramAuth for testing."""
        auth = AsyncMock()
        return auth

    @pytest.fixture
    def mock_bot(self):
        """Mock TelegramBot for testing."""
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def handler(self, mock_user_repository, mock_telegram_auth, mock_bot):
        """Create CommandHandler instance with mocked dependencies."""
        return CommandHandler(
            user_repository=mock_user_repository,
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.mark.asyncio
    async def test_ac_t009_1_routes_commands_by_name(self, handler):
        """
        AC-T009.1: Routes commands by name (start, help, status, call).

        Verifies that the handler correctly routes commands to their handlers.
        """
        # Arrange
        start_message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/start",
        }

        help_message = {**start_message, "text": "/help"}
        status_message = {**start_message, "text": "/status"}
        call_message = {**start_message, "text": "/call"}

        # Act & Assert - verify each command is routed
        with patch.object(handler, '_handle_start') as mock_start:
            await handler.handle(start_message)
            mock_start.assert_called_once()

        with patch.object(handler, '_handle_help') as mock_help:
            await handler.handle(help_message)
            mock_help.assert_called_once()

        with patch.object(handler, '_handle_status') as mock_status:
            await handler.handle(status_message)
            mock_status.assert_called_once()

        with patch.object(handler, '_handle_call') as mock_call:
            await handler.handle(call_message)
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_fr003_001_start_command_new_user_superseded_by_fr11c(
        self, handler, mock_user_repository, mock_bot
    ):
        """FR-11c supersedes AC-FR003-001.

        New users no longer get an email prompt; they get the bare portal
        URL button (AC-11c.1). Full coverage lives in
        `test_commands_fr11c.py::TestE1UnknownUser`. This regression guard
        just asserts the OLD email-prompt path is dead.
        """
        from unittest.mock import patch

        mock_bot.send_message_with_keyboard = AsyncMock()
        telegram_id = 123456789
        chat_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Alex"},
            "chat": {"id": chat_id, "type": "private"},
            "text": "/start",
        }
        mock_user_repository.get_by_telegram_id.return_value = None

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth"),
        ):
            await handler.handle(message)

        # send_message is NOT called (new user path uses keyboard button).
        mock_bot.send_message.assert_not_called()
        # send_message_with_keyboard IS called with a URL button.
        mock_bot.send_message_with_keyboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ac_t009_2_handle_start_existing_user(
        self, handler, mock_user_repository, mock_bot
    ):
        """AC-T009.2 + FR-11c AC-11c.2: onboarded + active = welcome-back text.

        Requires profile_repository DI (new in FR-11c) since known-user
        branches disambiguate limbo via profile presence.
        """
        telegram_id = 123456789
        chat_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Alex"},
            "chat": {"id": chat_id, "type": "private"},
            "text": "/start",
        }

        # User onboarded + active with a profile
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.telegram_id = telegram_id
        mock_user.chapter = 2
        mock_user.onboarding_status = "completed"
        mock_user.game_status = "active"
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # FR-11c requires profile_repository for known-user branching.
        profile_repo = AsyncMock()
        profile_repo.get.return_value = MagicMock()  # profile present
        handler.profile_repository = profile_repo

        await handler.handle(message)

        mock_user_repository.get_by_telegram_id.assert_called_once_with(telegram_id)
        mock_bot.send_message.assert_called_once()
        sent_message = mock_bot.send_message.call_args[1]["text"]
        assert "back" in sent_message.lower() or "again" in sent_message.lower()

    @pytest.mark.asyncio
    async def test_ac_t009_3_handle_help_returns_commands(self, handler, mock_bot):
        """
        AC-T009.3: _handle_help() returns available commands.

        Verifies that help command lists all available bot commands.
        """
        # Arrange
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/help",
        }

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        help_text = mock_bot.send_message.call_args[1]["text"]

        # Verify all commands are listed
        assert "/start" in help_text
        assert "/help" in help_text
        assert "/status" in help_text
        assert "/call" in help_text

    @pytest.mark.asyncio
    async def test_ac_t009_4_handle_status_returns_chapter_score(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        AC-T009.4: _handle_status() returns chapter/score hint.

        Verifies that status command shows current game state.
        """
        # Arrange
        telegram_id = 123456789
        chat_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Test"},
            "chat": {"id": chat_id, "type": "private"},
            "text": "/status",
        }

        # Mock: User exists with specific state
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.telegram_id = telegram_id
        mock_user.chapter = 3
        mock_user.relationship_score = Decimal("75.50")
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        status_text = mock_bot.send_message.call_args[1]["text"]

        # Verify chapter mentioned
        assert "3" in status_text or "chapter 3" in status_text.lower()

        # Should include score hint (not exact number, per game design)
        assert any(
            word in status_text.lower()
            for word in ["good", "great", "strong", "solid", "warm", "hot"]
        )

    @pytest.mark.asyncio
    async def test_ac_t009_5_unknown_commands_handled_gracefully(
        self, handler, mock_bot
    ):
        """
        AC-T009.5: Unknown commands handled gracefully.

        Verifies that unrecognized commands get helpful response.
        """
        # Arrange
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/unknown_command",
        }

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        response = mock_bot.send_message.call_args[1]["text"]

        # Should be helpful, not error message
        assert any(
            word in response.lower()
            for word in ["help", "try", "command", "don't", "what"]
        )

    @pytest.mark.asyncio
    async def test_command_with_bot_username(self, handler):
        """
        Verify commands work with @botname suffix (e.g., /start@NikitaBot).

        Telegram allows commands like /start@botname in group chats.
        """
        # Arrange
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/start@NikitaBot",
        }

        # Act
        with patch.object(handler, '_handle_start') as mock_start:
            await handler.handle(message)

            # Assert - should route to start handler despite @botname
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_command_unregistered_user(
        self, handler, mock_user_repository, mock_bot
    ):
        """
        Verify /status for unregistered user prompts registration.
        """
        # Arrange
        telegram_id = 123456789
        message = {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Test"},
            "chat": {"id": telegram_id, "type": "private"},
            "text": "/status",
        }

        # Mock: User doesn't exist
        mock_user_repository.get_by_telegram_id.return_value = None

        # Act
        await handler.handle(message)

        # Assert
        mock_bot.send_message.assert_called_once()
        response = mock_bot.send_message.call_args[1]["text"]

        # Should prompt to start registration
        assert "/start" in response or "register" in response.lower()


class TestOnboardCommand:
    """Tests for /onboard command (GH #160)."""

    @pytest.fixture
    def mock_user_repository(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_telegram_auth(self):
        auth = AsyncMock()
        return auth

    @pytest.fixture
    def mock_bot(self):
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        bot.send_message_with_keyboard = AsyncMock()
        return bot

    @pytest.fixture
    def handler(self, mock_user_repository, mock_telegram_auth, mock_bot):
        return CommandHandler(
            user_repository=mock_user_repository,
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
        )

    @pytest.fixture
    def onboard_message(self):
        return {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/onboard",
        }

    @pytest.mark.asyncio
    async def test_onboard_routes_to_handler(self, handler, onboard_message):
        """Verify /onboard is routed to _handle_onboard."""
        with patch.object(handler, "_handle_onboard") as mock_onboard:
            await handler.handle(onboard_message)
            mock_onboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_onboard_no_user_prompts_registration(
        self, handler, mock_user_repository, mock_bot, onboard_message
    ):
        """No user found -> tell them to /start."""
        mock_user_repository.get_by_telegram_id.return_value = None

        await handler.handle(onboard_message)

        mock_bot.send_message.assert_called_once()
        text = mock_bot.send_message.call_args[1]["text"]
        assert "/start" in text
        assert "register" in text.lower()

    @pytest.mark.asyncio
    async def test_onboard_already_completed(
        self, handler, mock_user_repository, mock_bot, onboard_message
    ):
        """User with onboarding_status=completed gets friendly message."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.onboarding_status = "completed"
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        await handler.handle(onboard_message)

        mock_bot.send_message.assert_called_once()
        text = mock_bot.send_message.call_args[1]["text"]
        assert "already set up" in text.lower()

    @pytest.mark.asyncio
    async def test_onboard_pending_sends_magic_link(
        self, handler, mock_user_repository, mock_bot, onboard_message
    ):
        """User with onboarding_status=pending gets magic link button."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.onboarding_status = "pending"
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # GH #233: commands.py now calls generate_portal_bridge_url directly
        # (source module patch per .claude/rules/testing.md).
        with patch(
            "nikita.platforms.telegram.utils.generate_portal_bridge_url",
            new=AsyncMock(
                return_value="https://nikita-mygirl.com/auth/bridge?token=abc"
            ),
        ):
            await handler.handle(onboard_message)

        # Should send keyboard with URL button
        mock_bot.send_message_with_keyboard.assert_called_once()
        call_kwargs = mock_bot.send_message_with_keyboard.call_args[1]
        assert call_kwargs["chat_id"] == 123456789
        keyboard = call_kwargs["keyboard"]
        assert len(keyboard) == 1
        assert "url" in keyboard[0][0]
        assert "abc" in keyboard[0][0]["url"]

    @pytest.mark.asyncio
    async def test_onboard_in_progress_sends_magic_link(
        self, handler, mock_user_repository, mock_bot, onboard_message
    ):
        """User with onboarding_status=in_progress also gets the link."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.onboarding_status = "in_progress"
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        with patch(
            "nikita.platforms.telegram.utils.generate_portal_bridge_url",
            new=AsyncMock(
                return_value="https://example.com/auth/bridge?token=xyz"
            ),
        ):
            await handler.handle(onboard_message)

        mock_bot.send_message_with_keyboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_onboard_magic_link_failure_falls_back(
        self, handler, mock_user_repository, mock_bot, onboard_message
    ):
        """When magic link generation fails, falls back to login URL."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.onboarding_status = "pending"
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        with patch(
            "nikita.platforms.telegram.utils.generate_portal_bridge_url",
            new=AsyncMock(return_value=None),
        ):
            await handler.handle(onboard_message)

        call_kwargs = mock_bot.send_message_with_keyboard.call_args[1]
        keyboard = call_kwargs["keyboard"]
        button_url = keyboard[0][0]["url"]
        assert "/login?next=/onboarding" in button_url

    @pytest.mark.asyncio
    async def test_onboard_skipped_status_treated_as_completed(
        self, handler, mock_user_repository, mock_bot, onboard_message
    ):
        """User with onboarding_status=skipped gets the 'already set up' message."""
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.onboarding_status = "skipped"
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        await handler.handle(onboard_message)

        mock_bot.send_message.assert_called_once()
        text = mock_bot.send_message.call_args[1]["text"]
        assert "already set up" in text.lower()

    @pytest.mark.asyncio
    async def test_help_includes_onboard_command(self, handler, mock_bot):
        """Verify /help output lists the /onboard command."""
        message = {
            "message_id": 1,
            "from": {"id": 123456789, "first_name": "Test"},
            "chat": {"id": 123456789, "type": "private"},
            "text": "/help",
        }

        await handler.handle(message)

        help_text = mock_bot.send_message.call_args[1]["text"]
        assert "/onboard" in help_text


class TestHandleStartWithPayload:
    """Test suite for GH #321 REQ-3: `/start <payload>` deep-link binding.

    When a portal user taps `https://t.me/Nikita_my_bot?start=<code>`, Telegram
    delivers a message text of `/start <payload>`. The bot MUST:

    1. Extract the payload from message["text"] split on whitespace.
    2. Validate against `^[A-Z0-9]{6}$` BEFORE any DB call (injection + typo guard).
    3. On valid format, call `TelegramLinkRepository.verify_code(payload)`.
    4. If verify_code returns a user_id, call
       `UserRepository.update_telegram_id(user_id, telegram_id)`.
    5. Send Nikita-voiced confirmation on success.
    6. On ANY reject (invalid format, expired code, conflict), short-circuit
       with a user-facing error. MUST NOT fall through to the email-OTP
       (branch-3) flow — that fallthrough reproduces the orphan-row bug
       GH #321 exists to fix.
    7. On vanilla `/start` with no payload, existing 3-branch behavior is
       preserved (unchanged).
    """

    @pytest.fixture
    def mock_user_repository(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_telegram_auth(self):
        auth = AsyncMock()
        return auth

    @pytest.fixture
    def mock_bot(self):
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_telegram_link_repository(self):
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def handler(
        self,
        mock_user_repository,
        mock_telegram_auth,
        mock_bot,
        mock_telegram_link_repository,
    ):
        """CommandHandler with telegram_link_repository injected."""
        return CommandHandler(
            user_repository=mock_user_repository,
            telegram_auth=mock_telegram_auth,
            bot=mock_bot,
            telegram_link_repository=mock_telegram_link_repository,
        )

    def _build_start_message(self, telegram_id: int, text: str) -> dict:
        return {
            "message_id": 1,
            "from": {"id": telegram_id, "first_name": "Alex"},
            "chat": {"id": telegram_id, "type": "private"},
            "text": text,
        }

    @pytest.mark.asyncio
    async def test_valid_payload_binds_and_confirms(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """Case 1: /start ABC123 with a valid unexpired code.

        MUST call verify_code, then update_telegram_id with the resolved
        user_id and the Telegram user's id. MUST send a confirmation.
        MUST NOT call get_by_telegram_id (that path is for the no-payload
        branches).
        """
        from nikita.db.repositories.user_repository import BindResult

        telegram_id = 123456789
        portal_user_id = uuid4()
        message = self._build_start_message(telegram_id, "/start ABC123")

        mock_telegram_link_repository.verify_code.return_value = portal_user_id
        mock_user_repository.update_telegram_id.return_value = BindResult.BOUND

        await handler.handle(message)

        mock_telegram_link_repository.verify_code.assert_awaited_once_with("ABC123")
        mock_user_repository.update_telegram_id.assert_awaited_once_with(
            portal_user_id, telegram_id
        )
        # Confirmation message was sent
        mock_bot.send_message.assert_awaited_once()
        sent_text = mock_bot.send_message.call_args[1]["text"]
        assert len(sent_text) > 0, "bind confirmation must have non-empty text"
        # MUST NOT have taken the vanilla-start path
        mock_user_repository.get_by_telegram_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_payload_short_circuits_no_email_otp_fallthrough(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_telegram_auth,
        mock_bot,
    ):
        """Case 2: /start ABC123 where verify_code returns None (expired / unknown).

        MUST short-circuit with an error message. MUST NOT fall through to
        the email-OTP branch-3 (the new-user prompt for email). MUST NOT
        call update_telegram_id. MUST NOT call get_by_telegram_id — a
        payload path is explicit; once verify_code fails, we don't
        silently re-interpret the message as a vanilla /start.
        """
        telegram_id = 123456789
        message = self._build_start_message(telegram_id, "/start ABC123")

        mock_telegram_link_repository.verify_code.return_value = None

        await handler.handle(message)

        mock_telegram_link_repository.verify_code.assert_awaited_once_with("ABC123")
        mock_user_repository.update_telegram_id.assert_not_called()
        # Critical: no email-OTP branch-3 fallthrough. TelegramAuth is what
        # initiates the email prompt + OTP issuance; it must not be invoked.
        mock_telegram_auth.assert_not_called()
        # And the no-payload branches (which call get_by_telegram_id) also
        # must not fire.
        mock_user_repository.get_by_telegram_id.assert_not_called()
        # Error message was sent
        mock_bot.send_message.assert_awaited_once()
        sent_text = mock_bot.send_message.call_args[1]["text"].lower()
        assert "expired" in sent_text or "invalid" in sent_text or "again" in sent_text, (
            f"expired-code path must produce a clear user-facing error. "
            f"Got: {sent_text[:120]}"
        )

    @pytest.mark.asyncio
    async def test_invalid_format_payload_rejects_without_db_call(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_telegram_auth,
        mock_bot,
    ):
        """Case 3: /start abc (lowercase, not 6 chars) — regex reject.

        MUST NOT call verify_code at all (regex gate fires first, DB is
        never consulted). MUST NOT fall through to email-OTP. MUST send
        a user-facing error.
        """
        telegram_id = 123456789
        # Lowercase + short — fails the `^[A-Z0-9]{6}$` regex.
        message = self._build_start_message(telegram_id, "/start abc")

        await handler.handle(message)

        # Regex gate stopped us before any DB call.
        mock_telegram_link_repository.verify_code.assert_not_called()
        mock_user_repository.update_telegram_id.assert_not_called()
        # No email-OTP fallthrough.
        mock_telegram_auth.assert_not_called()
        mock_user_repository.get_by_telegram_id.assert_not_called()
        # User-facing error was sent.
        mock_bot.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_conflict_different_user_sends_error_no_overwrite(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """Case 4: verify_code succeeds, but update_telegram_id raises
        TelegramIdAlreadyBoundByOtherUserError (telegram_id held by
        another user_id).

        MUST send a conflict error. MUST NOT silently overwrite (no
        re-try with different semantics). MUST NOT fall through to
        email-OTP.
        """
        from nikita.db.repositories.user_repository import (
            TelegramIdAlreadyBoundByOtherUserError,
        )

        telegram_id = 123456789
        portal_user_id = uuid4()
        message = self._build_start_message(telegram_id, "/start XYZ789")

        mock_telegram_link_repository.verify_code.return_value = portal_user_id
        mock_user_repository.update_telegram_id.side_effect = (
            TelegramIdAlreadyBoundByOtherUserError(telegram_id)
        )

        await handler.handle(message)

        mock_telegram_link_repository.verify_code.assert_awaited_once_with("XYZ789")
        # update_telegram_id WAS called (and raised)
        mock_user_repository.update_telegram_id.assert_awaited_once()
        # One send_message for the error; no silent-success.
        mock_bot.send_message.assert_awaited_once()
        sent_text = mock_bot.send_message.call_args[1]["text"].lower()
        assert "already" in sent_text or "another" in sent_text or "conflict" in sent_text or "linked" in sent_text, (
            f"conflict path must produce a clear error mentioning the existing binding. "
            f"Got: {sent_text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_same_user_rebind_is_idempotent_success(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """Case 5: verify_code succeeds, update_telegram_id returns
        ALREADY_BOUND_SAME_USER. User tapped the deep-link twice, or the
        code was reused. Treat as success (no error).
        """
        from nikita.db.repositories.user_repository import BindResult

        telegram_id = 123456789
        portal_user_id = uuid4()
        message = self._build_start_message(telegram_id, "/start DEF456")

        mock_telegram_link_repository.verify_code.return_value = portal_user_id
        mock_user_repository.update_telegram_id.return_value = (
            BindResult.ALREADY_BOUND_SAME_USER
        )

        await handler.handle(message)

        mock_user_repository.update_telegram_id.assert_awaited_once_with(
            portal_user_id, telegram_id
        )
        mock_bot.send_message.assert_awaited_once()
        # The message should be an ack (not an error). "already" is fine, but
        # must not read like a failure.
        sent_text = mock_bot.send_message.call_args[1]["text"].lower()
        assert "error" not in sent_text and "expired" not in sent_text, (
            f"same-user re-bind must be treated as success, not an error. "
            f"Got: {sent_text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_no_payload_routes_new_user_to_portal(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """Case 6 (FR-11c): vanilla `/start` with unknown user routes to
        portal instead of email-OTP.

        Before FR-11c this path sent an email prompt. After FR-11c it
        sends a single URL button to the bare portal `/onboarding/auth`
        (AC-11c.1). Payload branch MUST NOT fire.
        """
        from unittest.mock import patch

        mock_bot.send_message_with_keyboard = AsyncMock()
        telegram_id = 123456789
        message = self._build_start_message(telegram_id, "/start")
        mock_user_repository.get_by_telegram_id.return_value = None

        with patch(
            "nikita.platforms.telegram.commands.generate_portal_bridge_url",
            new=AsyncMock(return_value="https://p.example/onboarding/auth"),
        ):
            await handler.handle(message)

        # Payload branch did NOT fire.
        mock_telegram_link_repository.verify_code.assert_not_called()
        mock_user_repository.update_telegram_id.assert_not_called()
        # Vanilla branch DID fire.
        mock_user_repository.get_by_telegram_id.assert_awaited_once_with(
            telegram_id
        )
        # Keyboard button sent, NOT an email prompt.
        mock_bot.send_message_with_keyboard.assert_awaited_once()
        mock_bot.send_message.assert_not_called()

    # ──────────────────────────────────────────────────────────────────
    # Spec 214 T4.3 (FR-11e) extension: BackgroundTasks + claim + dispatch
    # ──────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_background_tasks_add_task_invoked_on_successful_bind(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """AC-T4.3.1: webhook plumbs `background_tasks` down; on a
        successful bind + successful claim, ``add_task`` MUST be called
        with the dispatcher target. The dispatcher itself is NOT awaited
        inline — the contract is "schedule, then return so the webhook
        can 200".
        """
        from nikita.db.repositories.user_repository import BindResult

        telegram_id = 123456789
        portal_user_id = uuid4()
        message = self._build_start_message(telegram_id, "/start ABC123")

        mock_telegram_link_repository.verify_code.return_value = portal_user_id
        mock_user_repository.update_telegram_id.return_value = BindResult.BOUND
        mock_user_repository.claim_handoff_intent = AsyncMock(return_value=True)

        bg = MagicMock()  # FastAPI BackgroundTasks shape: just .add_task

        await handler.handle(message, background_tasks=bg)

        # The claim was attempted (atomic gate before scheduling).
        mock_user_repository.claim_handoff_intent.assert_awaited_once_with(
            portal_user_id
        )
        # Dispatcher was scheduled, not invoked inline.
        bg.add_task.assert_called_once()
        scheduled_target = bg.add_task.call_args[0][0]
        assert scheduled_target.__name__ == "_dispatch_handoff_greeting", (
            "BackgroundTasks must schedule the FR-11e dispatcher; "
            f"got {scheduled_target.__name__}"
        )
        # Confirmation message still sent (the bind ack is independent
        # of the proactive greeting).
        mock_bot.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_second_concurrent_start_skips_dispatch(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """AC-T4.3.2 race-guard: when ``claim_handoff_intent`` returns
        False (second concurrent /start, or pg_cron already claimed),
        the dispatcher MUST NOT be scheduled. The bind confirmation is
        still sent (idempotent path).
        """
        from nikita.db.repositories.user_repository import BindResult

        telegram_id = 123456789
        portal_user_id = uuid4()
        message = self._build_start_message(telegram_id, "/start ABC123")

        mock_telegram_link_repository.verify_code.return_value = portal_user_id
        mock_user_repository.update_telegram_id.return_value = BindResult.BOUND
        # Second concurrent claim loses the race.
        mock_user_repository.claim_handoff_intent = AsyncMock(return_value=False)

        bg = MagicMock()

        await handler.handle(message, background_tasks=bg)

        # No greeting scheduling.
        bg.add_task.assert_not_called()
        # Confirmation still went out.
        mock_bot.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_sequence_and_retry_policy(self):
        """AC-T4.3.2: ``_dispatch_handoff_greeting`` retry policy.

        Sequence: 5xx, 5xx, 200 → ONE confirmed send + ``clear_pending_handoff``
        + commit. Verifies the retry chain doesn't dispatch twice on
        recovery and that on success the pending flag is cleared (NOT
        reset — that path is only for full retry-exhaust).
        """
        from unittest.mock import patch
        from nikita.platforms.telegram.commands import _dispatch_handoff_greeting

        bot = AsyncMock()
        # First two attempts: 5xx. Third: success.
        bot.send_message = AsyncMock(
            side_effect=[
                Exception("Telegram API error 502: Bad Gateway"),
                Exception("Telegram API error 503: Service Unavailable"),
                {"ok": True},
            ]
        )

        # Stub the session-maker context to a session shape that records
        # commit + the repo methods we expect.
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        async def _amock_aenter(*_a, **_k):
            return mock_session

        async def _amock_aexit(*_a, **_k):
            return None

        ctx = MagicMock()
        ctx.__aenter__ = _amock_aenter
        ctx.__aexit__ = _amock_aexit
        session_maker = MagicMock(return_value=ctx)

        # Stub the greeting generator to return a deterministic line so
        # we don't pull in the live agent.
        async def _gen(_user_id, _trigger, *, user_repo):
            return "hey alex. you made it."

        with patch(
            "nikita.db.database.get_session_maker", return_value=session_maker
        ), patch(
            "nikita.agents.onboarding.handoff_greeting.generate_handoff_greeting",
            new=_gen,
        ), patch("asyncio.sleep", new=AsyncMock()):
            # Patch UserRepository to return a stub repo that records
            # which terminal method was called.
            with patch(
                "nikita.platforms.telegram.commands.UserRepository"
            ) as repo_cls:
                repo_inst = AsyncMock()
                repo_inst.clear_pending_handoff = AsyncMock()
                repo_inst.reset_handoff_dispatch = AsyncMock()
                repo_cls.return_value = repo_inst

                await _dispatch_handoff_greeting(
                    user_id=uuid4(), chat_id=42, bot=bot
                )

        # Three send attempts: 2 fail with 5xx, 3rd succeeds.
        assert bot.send_message.await_count == 3
        # On confirmed delivery, the success path was taken.
        repo_inst.clear_pending_handoff.assert_awaited_once()
        repo_inst.reset_handoff_dispatch.assert_not_called()
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_retry_exhaust_resets_dispatch_for_backstop(self):
        """AC-T4.3.2: on full 5xx retry-exhaust, the dispatcher MUST
        ``reset_handoff_dispatch`` so the pg_cron backstop (T4.4) can
        re-claim the row on its next 60s tick.
        """
        from unittest.mock import patch
        from nikita.platforms.telegram.commands import _dispatch_handoff_greeting

        bot = AsyncMock()
        # Three 5xx in a row → exhaust.
        bot.send_message = AsyncMock(
            side_effect=[
                Exception("Telegram API error 502: Bad Gateway"),
                Exception("Telegram API error 502: Bad Gateway"),
                Exception("Telegram API error 502: Bad Gateway"),
            ]
        )

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def _amock_aenter(*_a, **_k):
            return mock_session

        async def _amock_aexit(*_a, **_k):
            return None

        ctx = MagicMock()
        ctx.__aenter__ = _amock_aenter
        ctx.__aexit__ = _amock_aexit
        session_maker = MagicMock(return_value=ctx)

        async def _gen(_user_id, _trigger, *, user_repo):
            return "hey. you made it."

        with patch(
            "nikita.db.database.get_session_maker", return_value=session_maker
        ), patch(
            "nikita.agents.onboarding.handoff_greeting.generate_handoff_greeting",
            new=_gen,
        ), patch("asyncio.sleep", new=AsyncMock()):
            with patch(
                "nikita.platforms.telegram.commands.UserRepository"
            ) as repo_cls:
                repo_inst = AsyncMock()
                repo_inst.clear_pending_handoff = AsyncMock()
                repo_inst.reset_handoff_dispatch = AsyncMock()
                repo_cls.return_value = repo_inst

                await _dispatch_handoff_greeting(
                    user_id=uuid4(), chat_id=42, bot=bot
                )

        # Three full attempts.
        assert bot.send_message.await_count == 3
        # Reset path taken (NOT clear).
        repo_inst.clear_pending_handoff.assert_not_called()
        repo_inst.reset_handoff_dispatch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_webhook_returns_before_dispatch_completes(
        self,
        handler,
        mock_user_repository,
        mock_telegram_link_repository,
        mock_bot,
    ):
        """AC-T4.3.3: scheduling is non-blocking. The greeting fires
        AFTER ``handle`` returns (FastAPI `BackgroundTasks` semantic).
        We model this by asserting that within the test boundary, the
        scheduled callable was registered but never invoked: the bot's
        ``send_message`` count is exactly 1 (the bind ack), with the
        greeting still pending in `bg.add_task`'s queue.
        """
        from nikita.db.repositories.user_repository import BindResult

        portal_user_id = uuid4()
        message = self._build_start_message(123, "/start ABC123")

        mock_telegram_link_repository.verify_code.return_value = portal_user_id
        mock_user_repository.update_telegram_id.return_value = BindResult.BOUND
        mock_user_repository.claim_handoff_intent = AsyncMock(return_value=True)

        bg = MagicMock()

        await handler.handle(message, background_tasks=bg)

        # Bind ack: yes. Greeting: still queued, not yet sent.
        assert mock_bot.send_message.await_count == 1
        bg.add_task.assert_called_once()
