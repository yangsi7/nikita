"""Tests for OnboardingHandler.

Tests are organized by TDD approach for T2.1, T2.2, T2.3 acceptance criteria.

T2.1: OnboardingHandler Class
- AC-T2.1-001: OnboardingHandler class with handle() method routing by current_step
- AC-T2.1-002: Step handlers for each profile field with appropriate prompts
- AC-T2.1-003: Mysterious intro message: "Before we connect you... I need to know a bit about you."
- AC-T2.1-004: State saved after each step (resume capability)
- AC-T2.1-005: Validation for each field type

T2.2: Integration with OTP Handler
- AC-T2.2-001: After OTP verification success, check if user has profile
- AC-T2.2-002: If no profile, route to OnboardingHandler instead of welcome message
- AC-T2.2-003: If profile exists, send normal welcome message

T2.3: Resume Logic
- AC-T2.3-001: On new message, check OnboardingState for telegram_id
- AC-T2.3-002: If incomplete onboarding exists, prompt to continue from last step
- AC-T2.3-003: "skip" or "I don't want to" detection → apply generic backstory
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.db.models.profile import OnboardingStep


class TestOnboardingHandlerClass:
    """Tests for OnboardingHandler class structure (T2.1)."""

    def test_onboarding_handler_exists(self):
        """AC-T2.1-001: OnboardingHandler class exists."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert OnboardingHandler is not None

    def test_onboarding_handler_has_handle_method(self):
        """AC-T2.1-001: OnboardingHandler has handle() method."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "handle")
        assert callable(getattr(OnboardingHandler, "handle"))

    def test_onboarding_handler_has_start_method(self):
        """AC-T2.1-003: OnboardingHandler has start() method for intro message."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "start")
        assert callable(getattr(OnboardingHandler, "start"))


class TestOnboardingStepHandlers:
    """Tests for step handlers (AC-T2.1-002)."""

    def test_has_location_step_handler(self):
        """AC-T2.1-002: Has handler for LOCATION step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "_handle_location_step")

    def test_has_life_stage_step_handler(self):
        """AC-T2.1-002: Has handler for LIFE_STAGE step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "_handle_life_stage_step")

    def test_has_scene_step_handler(self):
        """AC-T2.1-002: Has handler for SCENE step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "_handle_scene_step")

    def test_has_interest_step_handler(self):
        """AC-T2.1-002: Has handler for INTEREST step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "_handle_interest_step")

    def test_has_drug_tolerance_step_handler(self):
        """AC-T2.1-002: Has handler for DRUG_TOLERANCE step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "_handle_drug_tolerance_step")


class TestOnboardingPrompts:
    """Tests for onboarding prompts and messages."""

    def test_intro_message_constant_exists(self):
        """AC-T2.1-003: Has mysterious intro message constant."""
        from nikita.platforms.telegram.onboarding.handler import INTRO_MESSAGE

        assert INTRO_MESSAGE is not None
        assert "Before we connect you" in INTRO_MESSAGE or "know a bit about you" in INTRO_MESSAGE

    def test_step_prompts_exist(self):
        """AC-T2.1-002: Has prompts for each step."""
        from nikita.platforms.telegram.onboarding.handler import STEP_PROMPTS

        assert STEP_PROMPTS is not None
        assert OnboardingStep.LOCATION.value in STEP_PROMPTS
        assert OnboardingStep.LIFE_STAGE.value in STEP_PROMPTS
        assert OnboardingStep.SCENE.value in STEP_PROMPTS
        assert OnboardingStep.INTEREST.value in STEP_PROMPTS
        assert OnboardingStep.DRUG_TOLERANCE.value in STEP_PROMPTS


class TestOnboardingValidation:
    """Tests for input validation (AC-T2.1-005)."""

    def test_validate_location_accepts_city_names(self):
        """AC-T2.1-005: Validates location input."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        handler = OnboardingHandler.__new__(OnboardingHandler)

        # Valid cities
        assert handler._validate_location("Berlin") is True
        assert handler._validate_location("New York") is True
        assert handler._validate_location("São Paulo") is True

        # Invalid (too short)
        assert handler._validate_location("") is False
        assert handler._validate_location("A") is False

    def test_validate_drug_tolerance_accepts_1_to_5(self):
        """AC-T2.1-005: Validates drug tolerance 1-5 scale."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        handler = OnboardingHandler.__new__(OnboardingHandler)

        # Valid range
        for i in range(1, 6):
            assert handler._validate_drug_tolerance(str(i)) is True

        # Invalid
        assert handler._validate_drug_tolerance("0") is False
        assert handler._validate_drug_tolerance("6") is False
        assert handler._validate_drug_tolerance("abc") is False
        assert handler._validate_drug_tolerance("") is False


class TestSkipDetection:
    """Tests for skip/abandon detection (AC-T2.3-003)."""

    def test_skip_detection_phrases(self):
        """AC-T2.3-003: Detects skip phrases."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        handler = OnboardingHandler.__new__(OnboardingHandler)

        # Skip phrases
        assert handler._is_skip_request("skip") is True
        assert handler._is_skip_request("Skip") is True
        assert handler._is_skip_request("SKIP") is True
        assert handler._is_skip_request("i don't want to") is True
        assert handler._is_skip_request("I don't want to do this") is True
        assert handler._is_skip_request("just skip it") is True
        assert handler._is_skip_request("no thanks") is True

        # Not skip phrases
        assert handler._is_skip_request("Berlin") is False
        assert handler._is_skip_request("techno") is False


@pytest.mark.asyncio
class TestOnboardingHandlerIntegration:
    """Integration tests for OnboardingHandler behavior."""

    async def test_start_sends_intro_and_first_prompt(self):
        """AC-T2.1-003, AC-T2.1-004: Start sends intro and creates state."""
        from nikita.platforms.telegram.onboarding.handler import (
            INTRO_MESSAGE,
            OnboardingHandler,
            STEP_PROMPTS,
        )

        # Setup mocks
        bot = MagicMock()
        bot.send_message = AsyncMock()

        onboarding_repo = MagicMock()
        onboarding_repo.get_or_create = AsyncMock(return_value=MagicMock(
            current_step=OnboardingStep.LOCATION.value,
            collected_answers={},
        ))

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=MagicMock(),
        )

        # Call start
        await handler.start(telegram_id=123456789, chat_id=123456789)

        # Verify intro message sent
        assert bot.send_message.call_count == 2  # Intro + first prompt
        calls = bot.send_message.call_args_list

        # First call should be intro
        assert INTRO_MESSAGE in calls[0].kwargs.get("text", calls[0].args[1] if len(calls[0].args) > 1 else "")

    async def test_handle_routes_by_current_step(self):
        """AC-T2.1-001: handle() routes by current_step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        # Setup mocks
        bot = MagicMock()
        bot.send_message = AsyncMock()

        state = MagicMock()
        state.current_step = OnboardingStep.LOCATION.value
        state.collected_answers = {}

        onboarding_repo = MagicMock()
        onboarding_repo.get = AsyncMock(return_value=state)
        onboarding_repo.update_step = AsyncMock(return_value=state)
        onboarding_repo.add_answer = AsyncMock(return_value=state)

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=MagicMock(),
        )

        # Handle location input
        result = await handler.handle(
            telegram_id=123456789,
            chat_id=123456789,
            text="Berlin",
        )

        # Should have processed and moved to next step
        assert result is True
        onboarding_repo.add_answer.assert_called()

    async def test_handle_saves_state_after_each_step(self):
        """AC-T2.1-004: State saved after each step."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        # Setup mocks
        bot = MagicMock()
        bot.send_message = AsyncMock()

        state = MagicMock()
        state.current_step = OnboardingStep.LIFE_STAGE.value
        state.collected_answers = {"location_city": "Berlin"}

        onboarding_repo = MagicMock()
        onboarding_repo.get = AsyncMock(return_value=state)
        onboarding_repo.update_step = AsyncMock(return_value=state)
        onboarding_repo.add_answer = AsyncMock(return_value=state)

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=MagicMock(),
        )

        # Handle life stage input
        await handler.handle(
            telegram_id=123456789,
            chat_id=123456789,
            text="tech",
        )

        # Verify state update called
        onboarding_repo.add_answer.assert_called_with(
            123456789,
            "life_stage",
            "tech",
        )

    async def test_skip_continues_onboarding_with_encouragement(self):
        """Phase 1: Skip now continues onboarding with encouraging message.

        Changed behavior: Skip no longer bypasses onboarding.
        Personalization is mandatory for the product to work.
        """
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        # Setup mocks
        bot = MagicMock()
        bot.send_message = AsyncMock()

        state = MagicMock()
        state.current_step = OnboardingStep.LOCATION.value
        state.collected_answers = {}

        onboarding_repo = MagicMock()
        onboarding_repo.get = AsyncMock(return_value=state)
        onboarding_repo.delete = AsyncMock(return_value=True)

        profile_repo = MagicMock()
        profile_repo.create_profile = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=profile_repo,
        )

        # Handle skip
        result = await handler.handle(
            telegram_id=123456789,
            chat_id=123456789,
            text="skip",
        )

        # Should continue onboarding (not delete state)
        assert result is True
        # Verify delete was NOT called - skip continues, doesn't bypass
        onboarding_repo.delete.assert_not_called()
        # Verify encouraging message was sent
        bot.send_message.assert_called()


class TestOnboardingStateCheck:
    """Tests for checking onboarding state (AC-T2.3-001)."""

    def test_has_check_onboarding_state_method(self):
        """AC-T2.3-001: Has method to check onboarding state."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        assert hasattr(OnboardingHandler, "has_incomplete_onboarding")

    @pytest.mark.asyncio
    async def test_has_incomplete_onboarding_returns_state(self):
        """AC-T2.3-001: Returns incomplete state if exists."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        state = MagicMock()
        state.current_step = OnboardingStep.SCENE.value
        state.is_complete = MagicMock(return_value=False)

        onboarding_repo = MagicMock()
        onboarding_repo.get = AsyncMock(return_value=state)

        handler = OnboardingHandler(
            bot=MagicMock(),
            onboarding_repository=onboarding_repo,
            profile_repository=MagicMock(),
        )

        result = await handler.has_incomplete_onboarding(123456789)

        assert result is not None
        assert result.current_step == OnboardingStep.SCENE.value


@pytest.mark.asyncio
class TestFirstNikitaMessage:
    """Tests for FR-008: First personalized Nikita message."""

    async def test_send_first_nikita_message_with_hook(self):
        """FR-008: Uses hook from backstory in first message."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        bot = MagicMock()
        bot.send_message = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=MagicMock(),
            profile_repository=MagicMock(),
        )

        # Call with backstory containing a hook
        await handler._send_first_nikita_message(
            chat_id=123456789,
            selected_backstory={
                "venue": "Berghain",
                "hook": "I still think about that look you gave me",
                "the_moment": "when our eyes met across the dancefloor",
            },
            answers={"primary_interest": "techno", "social_scene": "nightlife"},
        )

        # Verify message sent with hook
        bot.send_message.assert_called()
        call_args = bot.send_message.call_args
        message = call_args.kwargs.get("text", call_args.args[1] if len(call_args.args) > 1 else "")
        assert "I still think about that look you gave me" in message
        assert "😏" in message  # Nikita's signature emoji

    async def test_send_first_nikita_message_fallback_to_interest(self):
        """FR-008: Falls back to interest when no hook."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        bot = MagicMock()
        bot.send_message = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=MagicMock(),
            profile_repository=MagicMock(),
        )

        # Call without hook but with interest
        await handler._send_first_nikita_message(
            chat_id=123456789,
            selected_backstory={"venue": "Bar 25"},
            answers={"primary_interest": "photography", "social_scene": "art"},
        )

        # Verify message mentions their interest
        call_args = bot.send_message.call_args
        message = call_args.kwargs.get("text", "")
        assert "photography" in message
        assert "Bar 25" in message

    async def test_send_first_nikita_message_custom_backstory(self):
        """FR-008: Generates hook from the_moment for custom backstory."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        bot = MagicMock()
        bot.send_message = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=MagicMock(),
            profile_repository=MagicMock(),
        )

        # Call with custom backstory (no hook, but has the_moment)
        await handler._send_first_nikita_message(
            chat_id=123456789,
            selected_backstory={
                "venue": "Hive Club",
                "the_moment": "3am techno set",
            },
            answers={"primary_interest": "AI products", "social_scene": "techno"},
        )

        # Verify message uses the_moment to generate hook
        call_args = bot.send_message.call_args
        message = call_args.kwargs.get("text", "")
        assert "3am techno set" in message
        assert "Hive Club" in message
        assert "😏" in message

    async def test_send_first_nikita_message_generic_fallback(self):
        """FR-008: Uses generic message when no hook or interest."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        bot = MagicMock()
        bot.send_message = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=MagicMock(),
            profile_repository=MagicMock(),
        )

        # Call with minimal backstory
        await handler._send_first_nikita_message(
            chat_id=123456789,
            selected_backstory={"venue": "the club"},
            answers={},
        )

        # Verify generic but personal message
        call_args = bot.send_message.call_args
        message = call_args.kwargs.get("text", "")
        assert "the club" in message
        assert "😏" in message

    async def test_send_first_nikita_message_handles_error_gracefully(self):
        """FR-008: Logs warning but doesn't raise on send failure."""
        from nikita.platforms.telegram.onboarding.handler import OnboardingHandler

        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=Exception("Telegram API error"))

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=MagicMock(),
            profile_repository=MagicMock(),
        )

        # Should not raise
        await handler._send_first_nikita_message(
            chat_id=123456789,
            selected_backstory={"venue": "somewhere"},
            answers={},
        )
