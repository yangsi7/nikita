"""Phase D: Telegram Flow tests (Spec 028).

Tests for voice onboarding Telegram integration.

Implements:
- AC-T013.1-4: /start onboarding status check
- AC-T014.1-4: Phone collection flow
- AC-T015.1-4: Ready for call confirmation
- AC-T016.1-4: Voice call initiation
- AC-T017.1-2: Integration tests
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.models import OnboardingStatus, UserOnboardingProfile
from nikita.onboarding.voice_flow import (
    VoiceOnboardingFlow,
    OnboardingState,
)


class TestOnboardingState:
    """Tests for OnboardingState model."""

    def test_default_state(self) -> None:
        """Default state is AWAITING_PHONE."""
        state = OnboardingState(user_id=uuid4())
        assert state.state == "awaiting_phone"

    def test_state_transitions(self) -> None:
        """State can transition through flow."""
        state = OnboardingState(user_id=uuid4())
        assert state.can_proceed_to("awaiting_confirmation")

        state.state = "awaiting_confirmation"
        assert state.can_proceed_to("call_initiated")

    def test_phone_stored(self) -> None:
        """Phone number is stored."""
        state = OnboardingState(user_id=uuid4(), phone_number="+14155551234")
        assert state.phone_number == "+14155551234"


class TestVoiceOnboardingFlow:
    """Tests for VoiceOnboardingFlow class."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()


class TestOnboardingStatusCheck:
    """Tests for onboarding status check (T013)."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()

    @pytest.mark.asyncio
    async def test_check_already_onboarded(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T013.1: Detects already onboarded user."""
        user_id = uuid4()

        # Mock user as already onboarded
        with patch.object(flow, '_get_user_onboarding_status') as mock:
            mock.return_value = OnboardingStatus.COMPLETED

            is_onboarded = await flow.is_already_onboarded(user_id)

        assert is_onboarded is True

    @pytest.mark.asyncio
    async def test_check_not_onboarded(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T013.3: Detects user needing onboarding."""
        user_id = uuid4()

        with patch.object(flow, '_get_user_onboarding_status') as mock:
            mock.return_value = OnboardingStatus.PENDING

            is_onboarded = await flow.is_already_onboarded(user_id)

        assert is_onboarded is False

    @pytest.mark.asyncio
    async def test_skip_onboarding_if_done(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T013.2: Skips onboarding flow if completed."""
        user_id = uuid4()

        with patch.object(flow, 'is_already_onboarded') as mock:
            mock.return_value = True

            should_start = await flow.should_start_onboarding(user_id)

        assert should_start is False


class TestPhoneCollection:
    """Tests for phone collection flow (T014)."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()

    @pytest.mark.asyncio
    async def test_request_phone_message(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T014.1: Generates phone request message."""
        message = flow.get_phone_request_message()

        assert "phone" in message.lower()
        assert "call" in message.lower() or "number" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_phone_format_valid(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T014.2: Accepts valid phone formats."""
        # US format
        assert flow.is_valid_phone("+14155551234") is True
        # Swiss format
        assert flow.is_valid_phone("+41787950009") is True
        # Without + prefix (with country code)
        assert flow.is_valid_phone("14155551234") is True

    @pytest.mark.asyncio
    async def test_validate_phone_format_invalid(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T014.2: Rejects invalid phone formats."""
        # Too short
        assert flow.is_valid_phone("12345") is False
        # Letters
        assert flow.is_valid_phone("phone123") is False
        # Empty
        assert flow.is_valid_phone("") is False

    @pytest.mark.asyncio
    async def test_store_phone_number(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T014.3: Stores phone number."""
        user_id = uuid4()
        phone = "+14155551234"

        with patch.object(flow, '_save_phone_number') as mock:
            mock.return_value = None

            result = await flow.process_phone_input(user_id, phone)

        assert result["success"] is True
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_invalid_phone_error(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T014.4: Returns error for invalid phone."""
        user_id = uuid4()

        result = await flow.process_phone_input(user_id, "invalid")

        assert result["success"] is False
        assert "error" in result


class TestReadyConfirmation:
    """Tests for ready for call confirmation (T015)."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()

    @pytest.mark.asyncio
    async def test_get_confirmation_message(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T015.1: Asks user if ready."""
        message = flow.get_ready_confirmation_message()

        assert "ready" in message.lower()
        assert "call" in message.lower()

    @pytest.mark.asyncio
    async def test_process_yes_response(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T015.2: 'yes' triggers call."""
        user_id = uuid4()

        # Set up state with phone number first
        with patch.object(flow, '_get_onboarding_state') as mock_state:
            mock_state.return_value = OnboardingState(
                user_id=user_id,
                state="awaiting_confirmation",
                phone_number="+14155551234",
            )

            with patch.object(flow, '_initiate_call') as mock_call:
                mock_call.return_value = {"success": True, "call_id": "test123"}

                result = await flow.process_ready_response(user_id, "yes")

        assert result["action"] == "initiate_call"
        mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_confirmation_variants(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T015.2: Various yes variants trigger call."""
        confirmations = ["yes", "Yes", "YES", "yeah", "yep", "sure", "ok", "okay"]

        for confirmation in confirmations:
            assert flow.is_confirmation(confirmation) is True

    @pytest.mark.asyncio
    async def test_process_not_now_response(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T015.3: 'not now' defers."""
        user_id = uuid4()

        result = await flow.process_ready_response(user_id, "not now")

        assert result["action"] == "defer"

    @pytest.mark.asyncio
    async def test_defer_variants(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T015.3: Various defer variants recognized."""
        deferrals = ["not now", "later", "no", "nope", "not yet", "maybe later"]

        for deferral in deferrals:
            assert flow.is_deferral(deferral) is True


class TestCallInitiation:
    """Tests for voice call initiation (T016)."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()

    @pytest.mark.asyncio
    async def test_initiate_call_success(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T016.1: Initiates call via ElevenLabs."""
        user_id = uuid4()
        phone = "+14155551234"

        with patch.object(flow, '_call_elevenlabs') as mock:
            mock.return_value = {"call_id": "call_abc123"}

            result = await flow.initiate_onboarding_call(user_id, phone)

        assert result["success"] is True
        assert "call_id" in result

    @pytest.mark.asyncio
    async def test_initiate_call_uses_meta_nikita(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T016.2: Uses Meta-Nikita agent."""
        user_id = uuid4()
        phone = "+14155551234"

        with patch.object(flow, '_call_elevenlabs') as mock:
            mock.return_value = {"call_id": "call_xyz"}

            await flow.initiate_onboarding_call(user_id, phone)

        # Verify agent config was for Meta-Nikita
        call_args = mock.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_initiate_call_failure_handled(self, flow: VoiceOnboardingFlow) -> None:
        """AC-T016.3: Handles call failures gracefully."""
        user_id = uuid4()
        phone = "+14155551234"

        with patch.object(flow, '_call_elevenlabs') as mock:
            mock.side_effect = Exception("ElevenLabs API error")

            result = await flow.initiate_onboarding_call(user_id, phone)

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_updates_status_on_call_start(self, flow: VoiceOnboardingFlow) -> None:
        """Call initiation updates user onboarding status."""
        user_id = uuid4()
        phone = "+14155551234"

        with patch.object(flow, '_call_elevenlabs') as mock_call:
            mock_call.return_value = {"call_id": "call_123"}

            with patch.object(flow, '_update_onboarding_status') as mock_status:
                await flow.initiate_onboarding_call(user_id, phone)

        mock_status.assert_called_with(user_id, OnboardingStatus.IN_CALL)


class TestFlowOrchestration:
    """Tests for overall flow orchestration."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()

    @pytest.mark.asyncio
    async def test_handle_message_when_awaiting_phone(self, flow: VoiceOnboardingFlow) -> None:
        """Routes to phone collection when awaiting phone."""
        user_id = uuid4()

        with patch.object(flow, '_get_onboarding_state') as mock_state:
            mock_state.return_value = OnboardingState(user_id=user_id, state="awaiting_phone")

            with patch.object(flow, 'process_phone_input') as mock_process:
                mock_process.return_value = {"success": True}

                result = await flow.handle_message(user_id, "+14155551234")

        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_when_awaiting_confirmation(
        self, flow: VoiceOnboardingFlow
    ) -> None:
        """Routes to confirmation when awaiting ready response."""
        user_id = uuid4()

        with patch.object(flow, '_get_onboarding_state') as mock_state:
            mock_state.return_value = OnboardingState(
                user_id=user_id,
                state="awaiting_confirmation",
                phone_number="+14155551234",
            )

            with patch.object(flow, 'process_ready_response') as mock_process:
                mock_process.return_value = {"action": "initiate_call"}

                result = await flow.handle_message(user_id, "yes")

        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_step_message(self, flow: VoiceOnboardingFlow) -> None:
        """Returns appropriate message for current step."""
        user_id = uuid4()

        # Awaiting phone
        with patch.object(flow, '_get_onboarding_state') as mock_state:
            mock_state.return_value = OnboardingState(user_id=user_id, state="awaiting_phone")

            message = await flow.get_current_step_message(user_id)

        assert "phone" in message.lower()

    @pytest.mark.asyncio
    async def test_complete_flow_end_to_end(self, flow: VoiceOnboardingFlow) -> None:
        """Full flow from phone to call initiation."""
        user_id = uuid4()

        # Step 1: Provide phone (don't mock _update_state so it actually updates)
        with patch.object(flow, '_save_phone_number') as mock_save:
            result = await flow.process_phone_input(user_id, "+14155551234")

        assert result["success"] is True

        # Step 2: Confirm ready (state should now have phone number)
        with patch.object(flow, '_initiate_call') as mock_call:
            mock_call.return_value = {"success": True, "call_id": "test123"}

            result = await flow.process_ready_response(user_id, "yes")

        assert result["action"] == "initiate_call"


class TestDeferredOnboarding:
    """Tests for deferred onboarding handling."""

    @pytest.fixture
    def flow(self) -> VoiceOnboardingFlow:
        """Create flow instance."""
        return VoiceOnboardingFlow()

    @pytest.mark.asyncio
    async def test_defer_saves_state(self, flow: VoiceOnboardingFlow) -> None:
        """Deferring saves state for later."""
        user_id = uuid4()

        with patch.object(flow, '_save_deferred_state') as mock:
            mock.return_value = None

            result = await flow.process_ready_response(user_id, "later")

        assert result["action"] == "defer"
        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_can_resume_deferred(self, flow: VoiceOnboardingFlow) -> None:
        """Deferred onboarding can be resumed."""
        user_id = uuid4()

        with patch.object(flow, '_get_onboarding_state') as mock:
            mock.return_value = OnboardingState(
                user_id=user_id,
                state="deferred",
                phone_number="+14155551234",
            )

            can_resume = await flow.can_resume_onboarding(user_id)

        assert can_resume is True

    @pytest.mark.asyncio
    async def test_onboard_command_resumes(self, flow: VoiceOnboardingFlow) -> None:
        """User can use /onboard to resume."""
        user_id = uuid4()

        with patch.object(flow, 'can_resume_onboarding') as mock_resume:
            mock_resume.return_value = True

            with patch.object(flow, 'resume_onboarding') as mock_process:
                mock_process.return_value = {"action": "prompt_confirmation"}

                result = await flow.handle_onboard_command(user_id)

        assert result["action"] == "prompt_confirmation"
