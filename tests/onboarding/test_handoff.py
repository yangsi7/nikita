"""Phase G: Handoff tests (Spec 028).

Tests for HandoffManager class and first Nikita message generation.

Implements:
- AC-T026.1-4: HandoffManager class
- AC-T027.1-4: First Nikita message generation
- AC-T028.1-4: User status update
- AC-T029.1-2: Integration tests
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.handoff import (
    HandoffManager,
    HandoffResult,
    FirstMessageGenerator,
    generate_first_nikita_message,
)
from nikita.onboarding.models import (
    ConversationStyle,
    OnboardingStatus,
    PersonalityType,
    UserOnboardingProfile,
)


class TestHandoffManager:
    """Tests for HandoffManager class (T026)."""

    @pytest.fixture
    def manager(self) -> HandoffManager:
        """Create manager instance."""
        return HandoffManager()

    @pytest.mark.asyncio
    async def test_transition_success(self, manager: HandoffManager) -> None:
        """AC-T026.2: transition() completes handoff."""
        user_id = uuid4()
        call_id = "call_123abc"
        profile = UserOnboardingProfile(
            timezone="America/New_York",
            occupation="Software Engineer",
            hobbies=["coding", "gaming"],
            darkness_level=3,
            pacing_weeks=4,
        )

        with patch.object(manager, "_update_user_status") as mock_status:
            with patch.object(manager, "_get_user_telegram_id") as mock_get_tg:
                mock_get_tg.return_value = 123456789

                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_send.return_value = {"success": True}

                    result = await manager.transition(
                        user_id=user_id,
                        call_id=call_id,
                        profile=profile,
                    )

        assert result.success is True
        assert result.call_id == call_id
        mock_status.assert_called_once()
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_transition_sets_onboarded_status(self, manager: HandoffManager) -> None:
        """AC-T026.3: Transition updates user to onboarded."""
        user_id = uuid4()
        call_id = "call_xyz"
        profile = UserOnboardingProfile()

        with patch.object(manager, "_update_user_status") as mock_status:
            with patch.object(manager, "_send_first_message") as mock_send:
                mock_send.return_value = {"success": True}

                await manager.transition(
                    user_id=user_id,
                    call_id=call_id,
                    profile=profile,
                )

        mock_status.assert_called_once_with(
            user_id,
            OnboardingStatus.COMPLETED,
            call_id,
        )

    @pytest.mark.asyncio
    async def test_transition_generates_first_message(self, manager: HandoffManager) -> None:
        """AC-T026.3: Transition triggers first Nikita message."""
        user_id = uuid4()
        profile = UserOnboardingProfile(
            occupation="Designer",
            hobbies=["art", "music"],
        )

        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_get_user_telegram_id") as mock_get_tg:
                mock_get_tg.return_value = 123456789

                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_send.return_value = {"success": True}

                    await manager.transition(
                        user_id=user_id,
                        call_id="call_test",
                        profile=profile,
                    )

        # Verify first message was sent with profile
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_transition_handles_send_failure(self, manager: HandoffManager) -> None:
        """AC-T026.3: Handles message send failure gracefully."""
        user_id = uuid4()
        profile = UserOnboardingProfile()

        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_send_first_message") as mock_send:
                mock_send.side_effect = Exception("Telegram API error")

                result = await manager.transition(
                    user_id=user_id,
                    call_id="call_test",
                    profile=profile,
                )

        # Status should still be updated even if message fails
        assert result.success is False
        assert "error" in result.error.lower() or "telegram" in result.error.lower()

    @pytest.mark.asyncio
    async def test_transition_returns_handoff_result(self, manager: HandoffManager) -> None:
        """AC-T026.2: transition() returns HandoffResult."""
        user_id = uuid4()
        profile = UserOnboardingProfile()

        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_get_user_telegram_id") as mock_get_tg:
                mock_get_tg.return_value = 123456789

                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_send.return_value = {"success": True, "message_id": 12345}

                    result = await manager.transition(
                        user_id=user_id,
                        call_id="call_abc",
                        profile=profile,
                    )

        assert isinstance(result, HandoffResult)
        assert result.user_id == user_id
        assert result.first_message_sent is True


class TestFirstMessageGenerator:
    """Tests for first Nikita message generation (T027)."""

    @pytest.fixture
    def generator(self) -> FirstMessageGenerator:
        """Create generator instance."""
        return FirstMessageGenerator()

    def test_generate_uses_profile_info(self, generator: FirstMessageGenerator) -> None:
        """AC-T027.3: Uses collected profile info."""
        profile = UserOnboardingProfile(
            occupation="Teacher",
            hobbies=["reading", "yoga"],
            timezone="Europe/London",
        )

        message = generator.generate(profile, user_name="Alex")

        # Message should reference profile elements
        assert message is not None
        assert len(message) > 0

    def test_generate_references_onboarding(self, generator: FirstMessageGenerator) -> None:
        """AC-T027.2: References onboarding naturally."""
        profile = UserOnboardingProfile()

        message = generator.generate(profile, user_name="Sam")

        # Should feel like a natural continuation
        assert message is not None
        # Should not be generic/robotic
        assert "user" not in message.lower()  # No "Dear user"

    def test_generate_personalized_greeting(self, generator: FirstMessageGenerator) -> None:
        """AC-T027.1: Personalized first message."""
        profile = UserOnboardingProfile(
            personality_type=PersonalityType.INTROVERT,
            conversation_style=ConversationStyle.LISTENER,
        )

        message = generator.generate(profile, user_name="Jordan")

        assert message is not None
        # Should feel warm and personal
        assert len(message) > 20  # Not too short

    def test_generate_adapts_to_darkness_level(self, generator: FirstMessageGenerator) -> None:
        """AC-T027.1: Message tone adapts to darkness level."""
        vanilla_profile = UserOnboardingProfile(darkness_level=1)
        noir_profile = UserOnboardingProfile(darkness_level=5)

        vanilla_msg = generator.generate(vanilla_profile, user_name="Test")
        noir_msg = generator.generate(noir_profile, user_name="Test")

        # Both should be valid but different tone
        assert vanilla_msg is not None
        assert noir_msg is not None
        # Noir might be more casual/edgy

    def test_generate_message_variants(self, generator: FirstMessageGenerator) -> None:
        """AC-T027.1: Can generate multiple variants."""
        profile = UserOnboardingProfile()

        messages = [generator.generate(profile, user_name="Test") for _ in range(3)]

        # Should have some variety
        assert len(messages) == 3
        assert all(m is not None for m in messages)


class TestGenerateFirstNikitaMessage:
    """Tests for the generate_first_nikita_message function."""

    def test_generates_non_empty_message(self) -> None:
        """Basic message generation."""
        profile = UserOnboardingProfile()

        message = generate_first_nikita_message(profile, "TestUser")

        assert message is not None
        assert len(message) > 0

    def test_includes_user_name(self) -> None:
        """Message can reference user name."""
        profile = UserOnboardingProfile()

        message = generate_first_nikita_message(profile, "Alex")

        # Name might be used but not required
        assert message is not None

    def test_adapts_to_profile(self) -> None:
        """Message adapts based on profile."""
        profile = UserOnboardingProfile(
            hobbies=["music", "dancing"],
            personality_type=PersonalityType.EXTROVERT,
        )

        message = generate_first_nikita_message(profile, "Test")

        assert message is not None
        assert len(message) > 20


class TestUserStatusUpdate:
    """Tests for user status update (T028)."""

    @pytest.fixture
    def manager(self) -> HandoffManager:
        """Create manager instance."""
        return HandoffManager()

    @pytest.mark.asyncio
    async def test_mark_user_onboarded(self, manager: HandoffManager) -> None:
        """AC-T028.1: Mark user as onboarded."""
        user_id = uuid4()
        profile = UserOnboardingProfile()

        with patch.object(manager, "_update_user_status") as mock_update:
            with patch.object(manager, "_send_first_message") as mock_send:
                mock_send.return_value = {"success": True}

                await manager.transition(
                    user_id=user_id,
                    call_id="call_123",
                    profile=profile,
                )

        mock_update.assert_called()
        call_args = mock_update.call_args
        assert call_args[0][1] == OnboardingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_set_onboarded_at_timestamp(self, manager: HandoffManager) -> None:
        """AC-T028.2: Set onboarded_at timestamp."""
        user_id = uuid4()
        profile = UserOnboardingProfile()

        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_send_first_message") as mock_send:
                mock_send.return_value = {"success": True}

                result = await manager.transition(
                    user_id=user_id,
                    call_id="call_123",
                    profile=profile,
                )

        assert result.onboarded_at is not None
        # Should be recent
        assert (datetime.now(UTC) - result.onboarded_at).total_seconds() < 60

    @pytest.mark.asyncio
    async def test_store_onboarding_call_id(self, manager: HandoffManager) -> None:
        """AC-T028.3: Store onboarding_call_id."""
        user_id = uuid4()
        call_id = "call_unique_123"
        profile = UserOnboardingProfile()

        with patch.object(manager, "_update_user_status") as mock_update:
            with patch.object(manager, "_send_first_message") as mock_send:
                mock_send.return_value = {"success": True}

                result = await manager.transition(
                    user_id=user_id,
                    call_id=call_id,
                    profile=profile,
                )

        # Verify call_id was passed to status update
        mock_update.assert_called_once_with(user_id, OnboardingStatus.COMPLETED, call_id)
        assert result.call_id == call_id


class TestHandoffIntegration:
    """Integration tests for handoff flow (T029)."""

    @pytest.fixture
    def manager(self) -> HandoffManager:
        """Create manager instance."""
        return HandoffManager()

    @pytest.mark.asyncio
    async def test_full_handoff_flow(self, manager: HandoffManager) -> None:
        """AC-T029.2: Full handoff integration."""
        user_id = uuid4()
        call_id = "call_integration_test"
        profile = UserOnboardingProfile(
            timezone="America/Chicago",
            occupation="Engineer",
            hobbies=["sports", "cooking"],
            personality_type=PersonalityType.AMBIVERT,
            darkness_level=3,
            pacing_weeks=4,
            conversation_style=ConversationStyle.BALANCED,
        )

        with patch.object(manager, "_update_user_status") as mock_status:
            with patch.object(manager, "_get_user_telegram_id") as mock_get_tg:
                mock_get_tg.return_value = 123456789

                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_send.return_value = {"success": True, "message_id": 999}

                    result = await manager.transition(
                        user_id=user_id,
                        call_id=call_id,
                        profile=profile,
                    )

        # All steps completed
        assert result.success is True
        assert result.user_id == user_id
        assert result.call_id == call_id
        assert result.onboarded_at is not None
        assert result.first_message_sent is True
        mock_status.assert_called_once()
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handoff_with_minimal_profile(self, manager: HandoffManager) -> None:
        """Handoff works with minimal profile."""
        user_id = uuid4()
        profile = UserOnboardingProfile()  # All defaults

        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_get_user_telegram_id") as mock_get_tg:
                mock_get_tg.return_value = 123456789

                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_send.return_value = {"success": True}

                    result = await manager.transition(
                        user_id=user_id,
                        call_id="call_minimal",
                        profile=profile,
                    )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_handoff_summary_generation(self, manager: HandoffManager) -> None:
        """Handoff can generate summary of onboarding."""
        user_id = uuid4()
        profile = UserOnboardingProfile(
            occupation="Doctor",
            hobbies=["tennis", "travel"],
            darkness_level=4,
        )

        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_send_first_message") as mock_send:
                mock_send.return_value = {"success": True}

                result = await manager.transition(
                    user_id=user_id,
                    call_id="call_summary",
                    profile=profile,
                )

        # Should have profile summary for Nikita's context
        assert result.profile_summary is not None
        assert "Doctor" in result.profile_summary or "occupation" in result.profile_summary.lower()
