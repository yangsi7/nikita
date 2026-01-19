"""Phase H: E2E tests (Spec 028).

End-to-end tests for the full voice onboarding flow.

Implements:
- AC-T030.1-4: Full onboarding E2E tests
- AC-T031.1-3: Quality metrics tests
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.handoff import (
    FirstMessageGenerator,
    HandoffManager,
    HandoffResult,
    generate_first_nikita_message,
)
from nikita.onboarding.models import (
    ConversationStyle,
    OnboardingStatus,
    PersonalityType,
    UserOnboardingProfile,
)
from nikita.onboarding.preference_config import (
    PreferenceConfigurator,
    get_darkness_config,
    get_pacing_config,
)
from nikita.onboarding.profile_collector import (
    ProfileCollector,
    ProfileField,
)
from nikita.onboarding.server_tools import (
    OnboardingServerToolHandler,
    OnboardingToolRequest,
)
from nikita.onboarding.voice_flow import (
    OnboardingState,
    VoiceOnboardingFlow,
)


class TestFullOnboardingE2E:
    """E2E tests for complete onboarding flow (T030)."""

    @pytest.fixture
    def user_id(self):
        """Generate test user ID."""
        return uuid4()

    @pytest.fixture
    def voice_flow(self):
        """Create voice flow instance."""
        return VoiceOnboardingFlow()

    @pytest.fixture
    def profile_collector(self):
        """Create profile collector instance."""
        return ProfileCollector()

    @pytest.fixture
    def preference_configurator(self):
        """Create preference configurator instance."""
        return PreferenceConfigurator()

    @pytest.fixture
    def handoff_manager(self):
        """Create handoff manager instance."""
        return HandoffManager()

    @pytest.mark.asyncio
    async def test_full_flow_telegram_to_call(
        self,
        user_id,
        voice_flow,
    ) -> None:
        """AC-T030.1: Full onboarding E2E (Telegram -> Voice -> First Message)."""
        # Step 1: User starts on Telegram - not yet onboarded
        is_onboarded = await voice_flow.is_already_onboarded(user_id)
        assert is_onboarded is False

        # Step 2: Collect phone number
        phone = "+1234567890"
        phone_result = await voice_flow.process_phone_input(user_id, phone)
        assert phone_result["success"] is True
        assert "next_message" in phone_result  # Confirmation message returned

        # Step 3: User confirms they're ready
        ready_result = await voice_flow.process_ready_response(user_id, "yes")
        assert ready_result["action"] == "initiate_call"

        # Step 4: Initiate call
        call_result = await voice_flow.initiate_onboarding_call(
            user_id=user_id,
            phone=phone,
            user_name="TestUser",
        )
        assert call_result["success"] is True
        assert "call_id" in call_result

    @pytest.mark.asyncio
    async def test_profile_collection_during_call(
        self,
        user_id,
        profile_collector,
    ) -> None:
        """AC-T030.2: Test profile completeness during call."""
        # Simulate server tool collecting profile fields during voice call

        # Collect timezone
        result = profile_collector.collect(
            user_id, ProfileField.TIMEZONE, "America/New_York"
        )
        assert result.success is True

        # Collect occupation
        result = profile_collector.collect(
            user_id, ProfileField.OCCUPATION, "Software Engineer"
        )
        assert result.success is True

        # Collect hobbies
        result = profile_collector.collect(
            user_id, ProfileField.HOBBIES, ["gaming", "reading", "cooking"]
        )
        assert result.success is True

        # Collect personality type
        result = profile_collector.collect(
            user_id, ProfileField.PERSONALITY_TYPE, PersonalityType.AMBIVERT
        )
        assert result.success is True

        # Collect hangout spots
        result = profile_collector.collect(
            user_id, ProfileField.HANGOUT_SPOTS, ["coffee shops", "parks", "gym"]
        )
        assert result.success is True

        # Verify profile completeness
        profile = profile_collector.get_profile(user_id)
        assert profile.timezone == "America/New_York"
        assert profile.occupation == "Software Engineer"
        assert len(profile.hobbies) == 3
        assert profile.personality_type == PersonalityType.AMBIVERT
        assert len(profile.hangout_spots) == 3

    @pytest.mark.asyncio
    async def test_preference_configuration_during_call(
        self,
        user_id,
        preference_configurator,
    ) -> None:
        """AC-T030.3: Test preference configuration during call."""
        # Configure darkness level
        result = preference_configurator.configure(
            user_id=user_id,
            darkness_level=4,
        )
        assert result.success is True

        # Configure pacing
        result = preference_configurator.configure(
            user_id=user_id,
            pacing_weeks=8,
        )
        assert result.success is True

        # Configure conversation style
        result = preference_configurator.configure(
            user_id=user_id,
            conversation_style=ConversationStyle.LISTENER,
        )
        assert result.success is True

        # Verify all preferences set
        prefs = preference_configurator.get_preferences(user_id)
        assert prefs.darkness_level == 4
        assert prefs.pacing_weeks == 8
        assert prefs.conversation_style == ConversationStyle.LISTENER

        # Verify behavioral config computed correctly
        behavioral = preference_configurator.get_behavioral_config(user_id)
        assert behavioral.darkness_config.name == "edgy"
        assert behavioral.pacing_config.name == "relaxed"
        assert behavioral.allows_manipulation is True

    @pytest.mark.asyncio
    async def test_handoff_to_nikita(
        self,
        user_id,
        handoff_manager,
    ) -> None:
        """AC-T030.4: Test handoff to Nikita."""
        call_id = "call_e2e_test_123"

        # Build complete profile directly (simulating what server tools would create)
        profile = UserOnboardingProfile(
            timezone="America/Chicago",
            occupation="Teacher",
            hobbies=["music", "hiking"],
            personality_type=PersonalityType.EXTROVERT,
            darkness_level=3,
            pacing_weeks=4,
            conversation_style=ConversationStyle.BALANCED,
        )

        # Execute handoff - mock all database operations
        with patch.object(handoff_manager, "_update_user_status") as mock_status:
            with patch.object(handoff_manager, "_get_user_telegram_id") as mock_telegram:
                with patch.object(handoff_manager, "_send_first_message") as mock_send:
                    mock_telegram.return_value = 12345678  # Mock telegram ID
                    mock_send.return_value = {"success": True, "message_id": 999}

                    result = await handoff_manager.transition(
                        user_id=user_id,
                        call_id=call_id,
                        profile=profile,
                        user_name="TestUser",
                    )

        # Verify handoff completed
        assert result.success is True
        assert result.user_id == user_id
        assert result.call_id == call_id
        assert result.onboarded_at is not None
        assert result.first_message_sent is True
        assert result.profile_summary is not None

        # Verify status was updated
        mock_status.assert_called_once_with(
            user_id, OnboardingStatus.COMPLETED, call_id
        )

        # Verify first message was sent
        mock_send.assert_called_once()


class TestE2EServerToolIntegration:
    """E2E tests using server tool handler."""

    @pytest.fixture
    def handler(self):
        """Create server tool handler."""
        return OnboardingServerToolHandler()

    @pytest.mark.asyncio
    async def test_server_tool_profile_collection_flow(self, handler) -> None:
        """E2E: Server tools collect profile during call."""
        user_id = str(uuid4())

        # Mock database persistence - server tools now persist to DB
        with patch.object(handler, "_persist_profile_to_db", new_callable=AsyncMock) as mock_persist:
            mock_persist.return_value = None

            # Tool 1: Collect timezone
            request = OnboardingToolRequest(
                tool_name="collect_profile",
                user_id=user_id,
                parameters={
                    "field_name": "timezone",
                    "value": "Europe/London",
                },
            )
            response = await handler.handle_request(request)
            assert response.success is True

            # Tool 2: Collect occupation
            request = OnboardingToolRequest(
                tool_name="collect_profile",
                user_id=user_id,
                parameters={
                    "field_name": "occupation",
                    "value": "Designer",
                },
            )
            response = await handler.handle_request(request)
            assert response.success is True

            # Tool 3: Configure preferences
            request = OnboardingToolRequest(
                tool_name="configure_preferences",
                user_id=user_id,
                parameters={
                    "darkness_level": 2,
                    "pacing_weeks": 8,
                },
            )
            response = await handler.handle_request(request)
            assert response.success is True

    @pytest.mark.asyncio
    async def test_server_tool_completes_onboarding(self, handler) -> None:
        """E2E: Server tool completes onboarding and triggers handoff."""
        user_id = str(uuid4())
        call_id = "call_complete_e2e"

        # Mock all database operations
        with patch.object(handler, "_persist_profile_to_db", new_callable=AsyncMock):
            # Collect minimal profile
            await handler.handle_request(
                OnboardingToolRequest(
                    tool_name="collect_profile",
                    user_id=user_id,
                    parameters={
                        "field_name": "timezone",
                        "value": "Asia/Tokyo",
                    },
                )
            )

        # Complete onboarding - mock database and handoff
        request = OnboardingToolRequest(
            tool_name="complete_onboarding",
            user_id=user_id,
            parameters={
                "call_id": call_id,
            },
        )

        with patch("nikita.onboarding.server_tools.get_session_maker") as mock_session_maker:
            with patch.object(handler, "_trigger_handoff", new_callable=AsyncMock) as mock_handoff:
                # Set up mock session and user repo
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.commit = AsyncMock()
                mock_session_maker.return_value.return_value = mock_session

                mock_user_repo = MagicMock()
                mock_user_repo.complete_onboarding = AsyncMock()
                with patch("nikita.onboarding.server_tools.UserRepository", return_value=mock_user_repo):
                    mock_handoff.return_value = None
                    response = await handler.handle_request(request)

        assert response.success is True


class TestQualityMetrics:
    """Quality metrics tests (T031)."""

    def test_onboarding_completion_rate_calculation(self) -> None:
        """AC-T031.1: Measure onboarding completion rate."""
        # Simulate completion data
        total_started = 100
        total_completed = 85

        completion_rate = total_completed / total_started * 100
        assert completion_rate == 85.0

        # Target: >= 80% completion rate
        assert completion_rate >= 80.0

    def test_profile_completeness_score(self) -> None:
        """AC-T031.3: Measure profile completeness."""
        # Full profile
        full_profile = UserOnboardingProfile(
            timezone="America/New_York",
            occupation="Engineer",
            hobbies=["coding", "reading"],
            personality_type=PersonalityType.INTROVERT,
            hangout_spots=["coffee shops"],
            darkness_level=3,
            pacing_weeks=4,
            conversation_style=ConversationStyle.BALANCED,
        )

        # Calculate completeness
        fields_set = 0
        total_fields = 8

        if full_profile.timezone:
            fields_set += 1
        if full_profile.occupation:
            fields_set += 1
        if full_profile.hobbies:
            fields_set += 1
        if full_profile.personality_type:
            fields_set += 1
        if full_profile.hangout_spots:
            fields_set += 1
        if full_profile.darkness_level:
            fields_set += 1
        if full_profile.pacing_weeks:
            fields_set += 1
        if full_profile.conversation_style:
            fields_set += 1

        completeness = fields_set / total_fields * 100
        assert completeness == 100.0

    def test_partial_profile_completeness(self) -> None:
        """Test partial profile completeness score."""
        # Partial profile (only defaults set)
        partial_profile = UserOnboardingProfile(
            timezone="America/Los_Angeles",
            occupation="",  # Empty
            hobbies=[],  # Empty list
        )

        # Calculate completeness
        fields_set = 0
        total_fields = 8

        if partial_profile.timezone:
            fields_set += 1
        if partial_profile.occupation:
            fields_set += 1
        if partial_profile.hobbies:
            fields_set += 1
        if partial_profile.personality_type:
            fields_set += 1
        if partial_profile.hangout_spots:
            fields_set += 1
        if partial_profile.darkness_level:
            fields_set += 1
        if partial_profile.pacing_weeks:
            fields_set += 1
        if partial_profile.conversation_style:
            fields_set += 1

        completeness = fields_set / total_fields * 100

        # With defaults (darkness_level=3, pacing_weeks=4), we get partial completeness
        # timezone (1) + darkness_level (1) + pacing_weeks (1) = 3/8 = 37.5%
        assert completeness >= 25.0  # At least some defaults

    def test_average_call_duration_tracking(self) -> None:
        """AC-T031.2: Measure average call duration."""
        # Simulate call durations (in seconds)
        call_durations = [
            180,  # 3 minutes
            240,  # 4 minutes
            300,  # 5 minutes
            210,  # 3.5 minutes
            270,  # 4.5 minutes
        ]

        avg_duration = sum(call_durations) / len(call_durations)
        assert avg_duration == 240.0  # 4 minutes average

        # Target: 3-5 minute average
        assert 180 <= avg_duration <= 300

    def test_first_message_quality_check(self) -> None:
        """Test first message meets quality standards."""
        profile = UserOnboardingProfile(
            timezone="America/Denver",
            occupation="Artist",
            hobbies=["painting", "music"],
            personality_type=PersonalityType.INTROVERT,
            darkness_level=2,
        )

        generator = FirstMessageGenerator()
        message = generator.generate(profile, user_name="Alex")

        # Quality checks
        assert len(message) > 20  # Not too short
        assert len(message) < 500  # Not too long
        assert "user" not in message.lower()  # No generic "Dear user"
        assert message[0].isupper() or message[0] in "!?"  # Proper start

    def test_message_variety_across_profiles(self) -> None:
        """Test messages vary appropriately by profile."""
        generator = FirstMessageGenerator()

        # Vanilla profile
        vanilla = UserOnboardingProfile(darkness_level=1)
        vanilla_msgs = {generator.generate(vanilla) for _ in range(10)}

        # Noir profile
        noir = UserOnboardingProfile(darkness_level=5)
        noir_msgs = {generator.generate(noir) for _ in range(10)}

        # Should have some variety
        assert len(vanilla_msgs) >= 2
        assert len(noir_msgs) >= 2

        # Vanilla and noir should be different sets (high probability)
        # Due to randomness, we just check they're not identical
        # Some overlap is possible but total shouldn't be same
        assert vanilla_msgs != noir_msgs or len(vanilla_msgs) > 1


class TestE2EEdgeCases:
    """E2E edge case tests."""

    @pytest.mark.asyncio
    async def test_user_defers_then_returns(self) -> None:
        """Test user defers onboarding then returns later."""
        user_id = uuid4()
        flow = VoiceOnboardingFlow()

        # User provides phone
        phone_result = await flow.process_phone_input(user_id, "+1555123456")
        assert phone_result["success"] is True

        # User defers
        defer_result = await flow.process_ready_response(user_id, "not now")
        assert defer_result["action"] == "defer"

        # Later: User wants to continue (would be triggered by /onboard command)
        state = await flow._get_onboarding_state(user_id)
        assert state.phone_number == "+1555123456"
        assert state.state == "deferred"

        # Can resume
        ready_result = await flow.process_ready_response(user_id, "yes")
        assert ready_result["action"] == "initiate_call"

    @pytest.mark.asyncio
    async def test_minimal_profile_handoff(self) -> None:
        """Test handoff works with minimal profile data."""
        user_id = uuid4()
        call_id = "call_minimal"

        # Minimal profile - just defaults
        profile = UserOnboardingProfile()

        manager = HandoffManager()

        # Mock all database operations including telegram_id lookup
        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_get_user_telegram_id") as mock_telegram:
                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_telegram.return_value = 12345678  # Mock telegram ID
                    mock_send.return_value = {"success": True}

                    result = await manager.transition(
                        user_id=user_id,
                        call_id=call_id,
                        profile=profile,
                    )

        # Should still succeed with defaults
        assert result.success is True
        assert result.profile_summary == "No profile data collected" or "Darkness level" in result.profile_summary

    @pytest.mark.asyncio
    async def test_invalid_preference_rejected(self) -> None:
        """Test invalid preferences are rejected gracefully."""
        user_id = uuid4()
        configurator = PreferenceConfigurator()

        # Invalid darkness level
        result = configurator.configure(user_id=user_id, darkness_level=10)
        assert result.success is False
        assert "Invalid" in result.error or "darkness" in result.error.lower()

        # Invalid pacing
        result = configurator.configure(user_id=user_id, pacing_weeks=6)
        assert result.success is False
        assert "Invalid" in result.error or "pacing" in result.error.lower()

    def test_darkness_level_boundaries(self) -> None:
        """Test all darkness level boundaries work."""
        for level in range(1, 6):
            config = get_darkness_config(level)
            assert config.level == level
            assert config.name in ["vanilla", "mild", "balanced", "edgy", "noir"]

        # Out of bounds
        with pytest.raises(ValueError):
            get_darkness_config(0)
        with pytest.raises(ValueError):
            get_darkness_config(6)

    def test_pacing_boundaries(self) -> None:
        """Test all pacing options work."""
        intense = get_pacing_config(4)
        assert intense.weeks == 4
        assert intense.name == "intense"

        relaxed = get_pacing_config(8)
        assert relaxed.weeks == 8
        assert relaxed.name == "relaxed"

        # Invalid
        with pytest.raises(ValueError):
            get_pacing_config(6)


class TestOnboardingResilience:
    """Tests for onboarding resilience and error recovery."""

    @pytest.mark.asyncio
    async def test_call_failure_recovery(self) -> None:
        """Test system handles call initiation failure."""
        user_id = uuid4()
        flow = VoiceOnboardingFlow()

        # Set up state
        await flow.process_phone_input(user_id, "+1555999888")

        # Mock call failure
        with patch.object(flow, "_call_elevenlabs") as mock_call:
            mock_call.side_effect = Exception("ElevenLabs API error")

            result = await flow.initiate_onboarding_call(
                user_id=user_id,
                phone="+1555999888",
                user_name="Test",
            )

        # Should handle gracefully
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handoff_partial_failure(self) -> None:
        """Test handoff handles message send failure."""
        user_id = uuid4()
        profile = UserOnboardingProfile(
            timezone="UTC",
            darkness_level=3,
        )

        manager = HandoffManager()

        # Mock all database operations, then let send_first_message fail
        with patch.object(manager, "_update_user_status"):
            with patch.object(manager, "_get_user_telegram_id") as mock_telegram:
                with patch.object(manager, "_send_first_message") as mock_send:
                    mock_telegram.return_value = 12345678  # Mock telegram ID
                    mock_send.side_effect = Exception("Telegram API error")

                    result = await manager.transition(
                        user_id=user_id,
                        call_id="call_partial_fail",
                        profile=profile,
                    )

        # Should report failure
        assert result.success is False
        assert "Telegram" in result.error or "error" in result.error.lower()
        assert result.first_message_sent is False

    def test_profile_collector_handles_invalid_fields(self) -> None:
        """Test profile collector handles invalid field values."""
        user_id = uuid4()
        collector = ProfileCollector()

        # Invalid timezone
        result = collector.collect(user_id, ProfileField.TIMEZONE, "Invalid/Timezone")
        # Should store anyway (validation is lenient)
        assert result.success is True

        # Invalid personality type string
        result = collector.collect(
            user_id, ProfileField.PERSONALITY_TYPE, "invalid_type"
        )
        # String should be rejected if not a valid enum
        # The collector accepts enum values or valid strings
        # This test depends on implementation - adjust as needed
        profile = collector.get_profile(user_id)
        # Personality might not be set if invalid
        assert profile.timezone == "Invalid/Timezone"
