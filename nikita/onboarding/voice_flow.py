"""Voice Onboarding Flow (Spec 028).

Orchestrates the voice onboarding Telegram integration:
1. Check if user needs onboarding
2. Collect phone number
3. Confirm user is ready
4. Initiate voice call with Meta-Nikita

Implements:
- AC-T013.1-4: /start onboarding status check
- AC-T014.1-4: Phone collection flow
- AC-T015.1-4: Ready for call confirmation
- AC-T016.1-4: Voice call initiation
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from nikita.onboarding.meta_nikita import MetaNikitaConfig
from nikita.onboarding.models import OnboardingStatus

logger = logging.getLogger(__name__)

# Phone number validation regex (E.164-ish format)
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{6,14}$")

# Confirmation responses
CONFIRMATION_WORDS = {"yes", "yeah", "yep", "sure", "ok", "okay", "yea", "ready", "let's go", "go"}
DEFERRAL_WORDS = {"no", "nope", "not now", "later", "not yet", "maybe later", "not ready"}


@dataclass
class OnboardingState:
    """Tracks user's position in onboarding flow."""

    user_id: UUID
    state: str = "awaiting_phone"
    phone_number: str | None = None
    call_id: str | None = None

    # Valid state transitions
    VALID_TRANSITIONS = {
        "awaiting_phone": ["awaiting_confirmation", "deferred"],
        "awaiting_confirmation": ["call_initiated", "deferred"],
        "call_initiated": ["completed", "failed"],
        "deferred": ["awaiting_confirmation", "awaiting_phone"],
        "completed": [],
        "failed": ["awaiting_phone"],
    }

    def can_proceed_to(self, next_state: str) -> bool:
        """Check if transition to next_state is valid."""
        return next_state in self.VALID_TRANSITIONS.get(self.state, [])


class VoiceOnboardingFlow:
    """Orchestrates voice onboarding via Telegram.

    Manages the flow:
    1. /start triggers onboarding check
    2. Request phone number
    3. Confirm user is ready
    4. Initiate ElevenLabs call with Meta-Nikita
    """

    def __init__(self, session: Any = None) -> None:
        """Initialize the flow.

        Args:
            session: Optional AsyncSession for database operations.
                     When None, DB operations log but don't persist.
        """
        self._states: dict[str, OnboardingState] = {}
        self._meta_nikita = MetaNikitaConfig()
        self._session = session

    # ===== Onboarding Status Check (T013) =====

    async def is_already_onboarded(self, user_id: UUID) -> bool:
        """
        Check if user has completed voice onboarding.

        AC-T013.1: Check if user already onboarded
        AC-T013.2: Skip onboarding if already done

        Args:
            user_id: User's UUID

        Returns:
            True if user already completed onboarding
        """
        status = await self._get_user_onboarding_status(user_id)
        return status == OnboardingStatus.COMPLETED

    async def should_start_onboarding(self, user_id: UUID) -> bool:
        """
        Determine if user should start voice onboarding.

        AC-T013.3: Route to onboarding if new

        Args:
            user_id: User's UUID

        Returns:
            True if user should start onboarding
        """
        if await self.is_already_onboarded(user_id):
            return False

        status = await self._get_user_onboarding_status(user_id)
        return status in (OnboardingStatus.PENDING, OnboardingStatus.FAILED, None)

    # ===== Phone Collection (T014) =====

    def get_phone_request_message(self) -> str:
        """
        Get message requesting user's phone number.

        AC-T014.1: Request phone number

        Returns:
            Phone request message
        """
        return (
            "Great! Before we get started, I'll need your phone number for a quick onboarding call.\n\n"
            "Our game facilitator will call you to explain how everything works and personalize your experience.\n\n"
            "What's your phone number? (Include country code, e.g., +1 for US)"
        )

    def is_valid_phone(self, phone: str) -> bool:
        """
        Validate phone number format.

        AC-T014.2: Validate phone format

        Args:
            phone: Phone number to validate

        Returns:
            True if valid format
        """
        if not phone:
            return False

        # Remove spaces and dashes for validation
        cleaned = re.sub(r"[\s\-\(\)]", "", phone)
        return bool(PHONE_REGEX.match(cleaned))

    def normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164-ish format."""
        cleaned = re.sub(r"[\s\-\(\)]", "", phone)
        if not cleaned.startswith("+"):
            # Assume US if no country code
            if len(cleaned) == 10:
                cleaned = "+1" + cleaned
            elif len(cleaned) == 11 and cleaned.startswith("1"):
                cleaned = "+" + cleaned
        return cleaned

    async def process_phone_input(self, user_id: UUID, phone: str) -> dict[str, Any]:
        """
        Process phone number input from user.

        AC-T014.3: Store phone number
        AC-T014.4: Unit tests

        Args:
            user_id: User's UUID
            phone: Phone number input

        Returns:
            Result dict with success status
        """
        if not self.is_valid_phone(phone):
            return {
                "success": False,
                "error": "That doesn't look like a valid phone number. Please include your country code.",
                "next_message": "Try again with your full phone number including country code (e.g., +1 for US)",
            }

        normalized = self.normalize_phone(phone)

        try:
            await self._save_phone_number(user_id, normalized)
            await self._update_state(user_id, "awaiting_confirmation", phone_number=normalized)

            return {
                "success": True,
                "phone": normalized,
                "next_message": self.get_ready_confirmation_message(),
            }
        except Exception as e:
            logger.error(f"Error saving phone for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ===== Ready Confirmation (T015) =====

    def get_ready_confirmation_message(self) -> str:
        """
        Get message asking if user is ready for call.

        AC-T015.1: Ask user if ready

        Returns:
            Ready confirmation message
        """
        return (
            "Got it! 📞\n\n"
            "Ready for your onboarding call now?\n\n"
            "Our game facilitator will explain how Nikita works and ask you a few questions to personalize your experience. "
            "It only takes about 5 minutes.\n\n"
            "Reply 'yes' to start the call, or 'later' if now isn't a good time."
        )

    def is_confirmation(self, text: str) -> bool:
        """
        Check if text is a confirmation response.

        AC-T015.2: Handle 'yes' variants

        Args:
            text: User's response

        Returns:
            True if confirmation
        """
        return text.strip().lower() in CONFIRMATION_WORDS

    def is_deferral(self, text: str) -> bool:
        """
        Check if text is a deferral response.

        AC-T015.3: Handle 'not now' variants

        Args:
            text: User's response

        Returns:
            True if deferral
        """
        text_lower = text.strip().lower()
        return any(word in text_lower for word in DEFERRAL_WORDS)

    async def process_ready_response(self, user_id: UUID, response: str) -> dict[str, Any]:
        """
        Process user's ready/not ready response.

        AC-T015.2: Handle 'yes' → initiate call
        AC-T015.3: Handle 'not now' → defer
        AC-T015.4: Unit tests

        Args:
            user_id: User's UUID
            response: User's response text

        Returns:
            Action result dict
        """
        if self.is_confirmation(response):
            # Initiate call
            state = await self._get_onboarding_state(user_id)
            phone = state.phone_number if state else None

            if not phone:
                return {
                    "action": "error",
                    "error": "No phone number on file. Please provide your phone number first.",
                }

            result = await self._initiate_call(user_id, phone)

            if result.get("success"):
                return {
                    "action": "initiate_call",
                    "call_id": result.get("call_id"),
                    "message": "Great! You'll receive a call shortly. Please answer to get started!",
                }
            else:
                return {
                    "action": "error",
                    "error": result.get("error", "Failed to initiate call"),
                }

        elif self.is_deferral(response):
            # Defer onboarding
            await self._save_deferred_state(user_id)

            return {
                "action": "defer",
                "message": (
                    "No problem! When you're ready, just send /onboard and we'll pick up where we left off.\n\n"
                    "You can also skip voice onboarding entirely by sending /skip - "
                    "but you'll miss out on the personalized experience!"
                ),
            }

        else:
            # Unclear response
            return {
                "action": "unclear",
                "message": (
                    "I didn't quite get that. Reply 'yes' if you're ready for the call, "
                    "or 'later' if now isn't a good time."
                ),
            }

    # ===== Voice Call Initiation (T016) =====

    async def initiate_onboarding_call(
        self, user_id: UUID, phone: str, user_name: str = "friend"
    ) -> dict[str, Any]:
        """
        Initiate voice onboarding call via ElevenLabs.

        AC-T016.1: Call ElevenLabs to initiate call
        AC-T016.2: Use Meta-Nikita agent
        AC-T016.3: Handle call failures gracefully
        AC-T016.4: Unit tests

        Args:
            user_id: User's UUID
            phone: Phone number to call
            user_name: User's name for personalization

        Returns:
            Result dict with call_id or error
        """
        try:
            # Update status to IN_CALL
            await self._update_onboarding_status(user_id, OnboardingStatus.IN_CALL)

            # Get Meta-Nikita agent config
            agent_config = self._meta_nikita.get_agent_config(
                user_id=user_id,
                user_name=user_name,
            )

            # Call ElevenLabs
            result = await self._call_elevenlabs(phone, agent_config)

            if result.get("call_id"):
                # Update state with call ID
                await self._update_state(
                    user_id, "call_initiated", call_id=result["call_id"]
                )

                logger.info(
                    f"Initiated onboarding call for user {user_id}: call_id={result['call_id']}"
                )

                return {
                    "success": True,
                    "call_id": result["call_id"],
                }
            else:
                raise Exception("No call_id in response")

        except Exception as e:
            logger.error(f"Failed to initiate onboarding call for user {user_id}: {e}")

            # Revert status
            await self._update_onboarding_status(user_id, OnboardingStatus.PENDING)

            return {
                "success": False,
                "error": str(e),
            }

    # ===== Flow Orchestration =====

    async def handle_message(self, user_id: UUID, text: str) -> dict[str, Any]:
        """
        Handle incoming message based on onboarding state.

        Args:
            user_id: User's UUID
            text: Message text

        Returns:
            Result with appropriate action/message
        """
        state = await self._get_onboarding_state(user_id)

        if state is None or state.state == "awaiting_phone":
            # Expecting phone number
            return await self.process_phone_input(user_id, text)

        elif state.state == "awaiting_confirmation":
            # Expecting ready confirmation
            return await self.process_ready_response(user_id, text)

        elif state.state == "deferred":
            # User previously deferred - treat as resuming
            return await self.process_ready_response(user_id, text)

        else:
            # Call in progress or completed
            return {
                "action": "skip",
                "message": "Your onboarding is already in progress or complete!",
            }

    async def get_current_step_message(self, user_id: UUID) -> str:
        """
        Get message for user's current onboarding step.

        Args:
            user_id: User's UUID

        Returns:
            Appropriate message for current step
        """
        state = await self._get_onboarding_state(user_id)

        if state is None or state.state == "awaiting_phone":
            return self.get_phone_request_message()

        elif state.state == "awaiting_confirmation":
            return self.get_ready_confirmation_message()

        elif state.state == "deferred":
            return (
                "Ready to continue with your onboarding call?\n\n"
                "Reply 'yes' to start the call, or 'later' if you need more time."
            )

        elif state.state == "call_initiated":
            return "Your call is in progress! Please check your phone."

        else:
            return "You're all set! Start chatting with Nikita."

    # ===== Deferred Onboarding =====

    async def can_resume_onboarding(self, user_id: UUID) -> bool:
        """Check if user has deferred onboarding to resume."""
        state = await self._get_onboarding_state(user_id)
        return state is not None and state.state == "deferred" and state.phone_number is not None

    async def resume_onboarding(self, user_id: UUID) -> dict[str, Any]:
        """Resume deferred onboarding."""
        await self._update_state(user_id, "awaiting_confirmation")
        return {
            "action": "prompt_confirmation",
            "message": self.get_ready_confirmation_message(),
        }

    async def handle_onboard_command(self, user_id: UUID) -> dict[str, Any]:
        """Handle /onboard command to resume deferred onboarding."""
        if await self.is_already_onboarded(user_id):
            return {
                "action": "already_done",
                "message": "You've already completed onboarding! Just start chatting with Nikita.",
            }

        if await self.can_resume_onboarding(user_id):
            return await self.resume_onboarding(user_id)

        return {
            "action": "start_fresh",
            "message": self.get_phone_request_message(),
        }

    # ===== Private Helper Methods =====

    async def _get_user_onboarding_status(self, user_id: UUID) -> OnboardingStatus | None:
        """Get user's onboarding status from database."""
        if self._session is None:
            return None
        try:
            from nikita.db.repositories.user_repository import UserRepository

            repo = UserRepository(self._session)
            user = await repo.get(user_id)
            if user is None:
                return None
            try:
                return OnboardingStatus(user.onboarding_status)
            except ValueError:
                return None
        except Exception as e:
            logger.error(f"Error getting onboarding status for {user_id}: {e}")
            return None

    async def _get_onboarding_state(self, user_id: UUID) -> OnboardingState | None:
        """Get user's current onboarding state."""
        return self._states.get(str(user_id))

    async def _update_state(
        self,
        user_id: UUID,
        new_state: str,
        phone_number: str | None = None,
        call_id: str | None = None,
    ) -> None:
        """Update user's onboarding state."""
        user_key = str(user_id)
        current = self._states.get(user_key)

        if current is None:
            current = OnboardingState(user_id=user_id)

        current.state = new_state
        if phone_number:
            current.phone_number = phone_number
        if call_id:
            current.call_id = call_id

        self._states[user_key] = current

    async def _save_phone_number(self, user_id: UUID, phone: str) -> None:
        """Save phone number to database."""
        if self._session is None:
            logger.info(f"No session: would save phone {phone} for user {user_id}")
            return
        try:
            from nikita.db.repositories.user_repository import UserRepository

            repo = UserRepository(self._session)
            user = await repo.get(user_id)
            if user is not None:
                user.phone = phone
                await self._session.flush()
                logger.info(f"Saved phone {phone} for user {user_id}")
            else:
                logger.warning(f"User {user_id} not found for phone save")
        except Exception as e:
            logger.error(f"Error saving phone for {user_id}: {e}")

    async def _save_deferred_state(self, user_id: UUID) -> None:
        """Save deferred state to in-memory state + database.

        Note: 'deferred' is not a valid DB onboarding_status enum
        (valid: pending, in_progress, completed, skipped).
        We use 'skipped' as the closest match for deferred state.
        """
        await self._update_state(user_id, "deferred")
        if self._session is not None:
            try:
                from nikita.db.repositories.user_repository import UserRepository

                repo = UserRepository(self._session)
                # 'skipped' is the closest valid DB enum for deferred
                await repo.update_onboarding_status(user_id, "skipped")
            except Exception as e:
                logger.error(f"Error saving deferred state for {user_id}: {e}")

    async def _update_onboarding_status(
        self, user_id: UUID, status: OnboardingStatus
    ) -> None:
        """Update user's onboarding status in database."""
        if self._session is None:
            logger.info(f"No session: would update user {user_id} status to {status.value}")
            return
        try:
            from nikita.db.repositories.user_repository import UserRepository

            # Map OnboardingStatus enum to valid DB values
            status_map = {
                OnboardingStatus.PENDING: "pending",
                OnboardingStatus.IN_CALL: "in_progress",
                OnboardingStatus.COMPLETED: "completed",
                OnboardingStatus.SKIPPED: "skipped",
                OnboardingStatus.CALL_SCHEDULED: "in_progress",
                OnboardingStatus.FAILED: "pending",  # Reset to pending on failure
            }
            db_status = status_map.get(status, "pending")

            repo = UserRepository(self._session)
            await repo.update_onboarding_status(user_id, db_status)
            logger.info(f"Updated user {user_id} onboarding status to {db_status}")
        except Exception as e:
            logger.error(f"Error updating onboarding status for {user_id}: {e}")

    async def _initiate_call(self, user_id: UUID, phone: str) -> dict[str, Any]:
        """Internal call initiation wrapper."""
        return await self.initiate_onboarding_call(user_id, phone)

    async def _call_elevenlabs(
        self, phone: str, agent_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Call ElevenLabs API to initiate outbound onboarding call.

        Uses VoiceService.make_outbound_call() with Meta-Nikita config override.
        """
        try:
            from nikita.agents.voice.service import VoiceService
            from nikita.config.settings import get_settings

            settings = get_settings()
            service = VoiceService(settings=settings)

            # Build conversation config override from agent_config
            conversation_config_override = agent_config.get("conversation_config_override")
            dynamic_variables = agent_config.get("dynamic_variables", {})

            result = await service.make_outbound_call(
                to_number=phone,
                conversation_config_override=conversation_config_override,
                dynamic_variables=dynamic_variables,
                is_onboarding=True,
            )

            if result.get("success"):
                return {"call_id": result.get("conversation_id", "")}
            else:
                raise Exception(result.get("message", "Outbound call failed"))

        except Exception as e:
            logger.error(f"ElevenLabs call failed for {phone}: {e}")
            raise
