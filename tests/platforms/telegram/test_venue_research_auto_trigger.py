"""Tests for venue research auto-trigger after drug_tolerance step.

Bug fix: After answering drug_tolerance (step 5), the handler must immediately
call _handle_venue_research_step() instead of waiting for another user message.
Without this, the user sees "One moment while I set things up..." but the bot
is also waiting for a message — deadlock.

Also tests that _finalize_backstory_selection sets users.onboarding_status
to 'completed' (not just onboarding_states.current_step = COMPLETE).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.models.profile import OnboardingState, OnboardingStep
from nikita.platforms.telegram.onboarding.handler import OnboardingHandler


class TestVenueResearchAutoTrigger:
    """Venue research must be triggered automatically after drug_tolerance."""

    def _make_handler(self, **overrides) -> OnboardingHandler:
        """Create handler with default mocks."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        onboarding_repo = MagicMock()
        onboarding_repo.get = AsyncMock()
        onboarding_repo.update_step = AsyncMock()
        onboarding_repo.add_answer = AsyncMock()

        profile_repo = MagicMock()

        user_repo = MagicMock()
        user_repo.get_by_telegram_id = AsyncMock(return_value=None)
        user_repo.update_onboarding_status = AsyncMock()

        defaults = dict(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=profile_repo,
            user_repository=user_repo,
        )
        defaults.update(overrides)
        return OnboardingHandler(**defaults)

    @pytest.mark.asyncio
    async def test_drug_tolerance_triggers_venue_research_immediately(self):
        """After drug_tolerance answer, venue research runs without waiting for message."""
        handler = self._make_handler()

        # State at DRUG_TOLERANCE step
        state = MagicMock()
        state.current_step = OnboardingStep.DRUG_TOLERANCE.value
        state.collected_answers = {
            "location_city": "Zurich",
            "life_stage": "tech",
            "social_scene": "techno",
            "primary_interest": "music",
        }
        handler.onboarding_repo.get = AsyncMock(return_value=state)

        # Mock _handle_venue_research_step to track that it gets called
        handler._handle_venue_research_step = AsyncMock()

        # Send drug_tolerance answer "4"
        result = await handler.handle(
            telegram_id=123456789,
            chat_id=123456789,
            text="4",
        )

        assert result is True

        # The key assertion: venue research must be called immediately
        handler._handle_venue_research_step.assert_awaited_once_with(
            123456789, 123456789, ""
        )

    @pytest.mark.asyncio
    async def test_drug_tolerance_sends_response_before_venue_research(self):
        """User gets the tolerance response + 'One moment...' before venue research starts."""
        handler = self._make_handler()

        state = MagicMock()
        state.current_step = OnboardingStep.DRUG_TOLERANCE.value
        state.collected_answers = {
            "location_city": "Berlin",
            "social_scene": "art",
        }
        handler.onboarding_repo.get = AsyncMock(return_value=state)

        # Mock venue research to track call order
        call_order = []

        original_send = handler.bot.send_message

        async def track_send(**kwargs):
            call_order.append(("send_message", kwargs.get("text", "")[:30]))
            return await original_send(**kwargs)

        handler.bot.send_message = AsyncMock(side_effect=track_send)

        async def track_venue_research(*args, **kwargs):
            call_order.append(("venue_research", None))

        handler._handle_venue_research_step = AsyncMock(side_effect=track_venue_research)

        await handler.handle(
            telegram_id=111,
            chat_id=111,
            text="3",
        )

        # send_message must happen before venue_research
        send_indices = [i for i, (name, _) in enumerate(call_order) if name == "send_message"]
        venue_indices = [i for i, (name, _) in enumerate(call_order) if name == "venue_research"]

        assert len(send_indices) >= 1, "Should have sent at least one message"
        assert len(venue_indices) == 1, "Should have triggered venue research"
        assert send_indices[-1] < venue_indices[0], (
            "Last send_message should come before venue_research"
        )

    @pytest.mark.asyncio
    async def test_drug_tolerance_invalid_does_not_trigger_venue_research(self):
        """Invalid drug_tolerance (e.g. '7') should NOT trigger venue research."""
        handler = self._make_handler()

        state = MagicMock()
        state.current_step = OnboardingStep.DRUG_TOLERANCE.value
        state.collected_answers = {}
        handler.onboarding_repo.get = AsyncMock(return_value=state)

        handler._handle_venue_research_step = AsyncMock()

        await handler.handle(
            telegram_id=123,
            chat_id=123,
            text="7",  # Invalid — out of 1-5 range
        )

        handler._handle_venue_research_step.assert_not_awaited()


class TestOnboardingStatusCompletion:
    """After scenario selection, users.onboarding_status must be set to 'completed'."""

    @pytest.mark.asyncio
    async def test_finalize_sets_onboarding_status_completed(self):
        """_finalize_backstory_selection must call user_repo.update_onboarding_status('completed')."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        onboarding_repo = MagicMock()
        state = MagicMock()
        state.collected_answers = {
            "location_city": "Zurich",
            "life_stage": "tech",
            "social_scene": "techno",
            "drug_tolerance": 3,
        }
        onboarding_repo.get = AsyncMock(return_value=state)
        onboarding_repo.add_answer = AsyncMock()
        onboarding_repo.update_step = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()

        user_repo = MagicMock()
        user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
        user_repo.update_onboarding_status = AsyncMock()

        profile_repo = MagicMock()
        backstory_repo = MagicMock()
        vice_repo = MagicMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=profile_repo,
            user_repository=user_repo,
            backstory_repository=backstory_repo,
            vice_repository=vice_repo,
        )

        # Mock the persistence methods to avoid needing full DB setup
        handler._persist_profile_and_backstory = AsyncMock()
        handler._initialize_vices_from_profile = AsyncMock()
        handler._send_first_nikita_message = AsyncMock()

        selected = {
            "venue": "Hive Club",
            "context": "A techno night",
            "the_moment": "Eyes met across the dance floor",
            "unresolved_hook": "Left without a number",
            "tone": "chaotic",
        }

        await handler._finalize_backstory_selection(
            telegram_id=123456789,
            chat_id=123456789,
            selected=selected,
        )

        # Key assertion: onboarding_status must be updated to 'completed'
        user_repo.update_onboarding_status.assert_awaited_once_with(
            mock_user.id, "completed"
        )

    @pytest.mark.asyncio
    async def test_finalize_without_user_repo_does_not_crash(self):
        """If user_repo is None, finalize should still complete without error."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        onboarding_repo = MagicMock()
        state = MagicMock()
        state.collected_answers = {"drug_tolerance": 2}
        onboarding_repo.get = AsyncMock(return_value=state)
        onboarding_repo.add_answer = AsyncMock()
        onboarding_repo.update_step = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=MagicMock(),
            user_repository=None,  # No user_repo
        )
        handler._send_first_nikita_message = AsyncMock()

        selected = {
            "venue": "Bar",
            "the_moment": "Moment",
        }

        # Should not raise
        await handler._finalize_backstory_selection(
            telegram_id=999,
            chat_id=999,
            selected=selected,
        )

        # onboarding step should still be set to COMPLETE
        onboarding_repo.update_step.assert_awaited_once_with(
            999, OnboardingStep.COMPLETE
        )

    @pytest.mark.asyncio
    async def test_finalize_user_not_found_does_not_crash(self):
        """If user_repo.get_by_telegram_id returns None, should not crash."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        onboarding_repo = MagicMock()
        state = MagicMock()
        state.collected_answers = {"drug_tolerance": 3}
        onboarding_repo.get = AsyncMock(return_value=state)
        onboarding_repo.add_answer = AsyncMock()
        onboarding_repo.update_step = AsyncMock()

        user_repo = MagicMock()
        user_repo.get_by_telegram_id = AsyncMock(return_value=None)
        user_repo.update_onboarding_status = AsyncMock()

        handler = OnboardingHandler(
            bot=bot,
            onboarding_repository=onboarding_repo,
            profile_repository=MagicMock(),
            user_repository=user_repo,
        )
        handler._send_first_nikita_message = AsyncMock()

        selected = {"venue": "Cafe", "the_moment": "a glance"}

        await handler._finalize_backstory_selection(
            telegram_id=888,
            chat_id=888,
            selected=selected,
        )

        # Should NOT have tried to update onboarding_status (no user found)
        user_repo.update_onboarding_status.assert_not_awaited()

        # But onboarding step should still be COMPLETE
        onboarding_repo.update_step.assert_awaited_once_with(
            888, OnboardingStep.COMPLETE
        )
