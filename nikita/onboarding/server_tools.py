"""Onboarding Server Tools (Spec 028).

Server tool handlers for Meta-Nikita onboarding calls.
These tools are called by ElevenLabs during the voice conversation
to collect and store user profile information.

Tools:
- collect_profile: Store individual profile fields
- configure_preferences: Set experience preferences
- complete_onboarding: Mark user as onboarded and trigger handoff

Implements:
- AC-T009.1-4: collect_profile server tool
- AC-T010.1-4: configure_preferences server tool
- AC-T011.1-4: complete_onboarding server tool
"""

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.database import get_session_maker
from nikita.db.repositories.user_repository import UserRepository
from nikita.onboarding.models import (
    ConversationStyle,
    PersonalityType,
    UserOnboardingProfile,
)

logger = logging.getLogger(__name__)

# Valid profile fields for collection
VALID_PROFILE_FIELDS = {
    "timezone",
    "occupation",
    "hobbies",
    "personality_type",
    "hangout_spots",
}


class OnboardingToolRequest(BaseModel):
    """Request model for onboarding server tools."""

    tool_name: str = Field(description="Name of the tool to execute")
    user_id: str = Field(description="User UUID")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class OnboardingToolResponse(BaseModel):
    """Response model for onboarding server tools."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str | None = Field(default=None, description="Success message")
    error: str | None = Field(default=None, description="Error message if failed")
    data: dict[str, Any] | None = Field(default=None, description="Additional data")


class OnboardingServerToolHandler:
    """Handler for onboarding-specific server tools.

    Processes server tool calls from ElevenLabs during Meta-Nikita
    onboarding voice calls. Uses database persistence via UserRepository.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize the handler.

        Args:
            session: Optional SQLAlchemy async session. If not provided,
                     a new session will be created for each request.
        """
        self._session = session
        # In-memory cache for profile during call (persisted to DB incrementally)
        self._profiles: dict[str, UserOnboardingProfile] = {}

    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        if self._session:
            return self._session
        session_maker = get_session_maker()
        return session_maker()

    async def handle_request(self, request: OnboardingToolRequest) -> OnboardingToolResponse:
        """
        Route and handle a server tool request.

        Args:
            request: The tool request from ElevenLabs

        Returns:
            Response with success/error status
        """
        user_id = UUID(request.user_id)

        if request.tool_name == "collect_profile":
            return await self.collect_profile(
                user_id=user_id,
                field_name=request.parameters.get("field_name", ""),
                value=request.parameters.get("value", ""),
            )
        elif request.tool_name == "configure_preferences":
            return await self.configure_preferences(
                user_id=user_id,
                darkness_level=request.parameters.get("darkness_level"),
                pacing_weeks=request.parameters.get("pacing_weeks"),
                conversation_style=request.parameters.get("conversation_style"),
            )
        elif request.tool_name == "complete_onboarding":
            return await self.complete_onboarding(
                user_id=user_id,
                call_id=request.parameters.get("call_id", "unknown"),
                notes=request.parameters.get("notes"),
            )
        elif request.tool_name == "end_call":
            return await self.end_call(
                user_id=user_id,
                reason=request.parameters.get("reason", "onboarding_complete"),
            )
        else:
            return OnboardingToolResponse(
                success=False,
                error=f"Unknown tool: {request.tool_name}",
            )

    async def collect_profile(
        self,
        user_id: UUID,
        field_name: str,
        value: str,
    ) -> OnboardingToolResponse:
        """
        Store a profile field collected during the conversation.

        AC-T009.1: collect_profile server tool
        AC-T009.2: Accepts field_name and value
        AC-T009.3: Validates and stores profile data

        Args:
            user_id: User's UUID
            field_name: Name of the field to update
            value: Value to store

        Returns:
            Response indicating success or failure
        """
        # Validate field name
        if field_name not in VALID_PROFILE_FIELDS:
            return OnboardingToolResponse(
                success=False,
                error=f"Invalid field_name: {field_name}. Valid fields: {VALID_PROFILE_FIELDS}",
            )

        try:
            # Get or create in-memory profile
            profile = self._get_or_create_profile(user_id)

            # Update the appropriate field
            if field_name == "timezone":
                profile.timezone = value
            elif field_name == "occupation":
                profile.occupation = value
            elif field_name == "hobbies":
                # Parse comma-separated hobbies
                hobbies = [h.strip() for h in value.split(",") if h.strip()]
                profile.hobbies = hobbies
            elif field_name == "personality_type":
                # Map to enum
                try:
                    profile.personality_type = PersonalityType(value.lower())
                except ValueError:
                    # Try to infer from common variations
                    value_lower = value.lower()
                    if "intro" in value_lower:
                        profile.personality_type = PersonalityType.INTROVERT
                    elif "extro" in value_lower:
                        profile.personality_type = PersonalityType.EXTROVERT
                    else:
                        profile.personality_type = PersonalityType.AMBIVERT
            elif field_name == "hangout_spots":
                # Parse comma-separated spots
                spots = [s.strip() for s in value.split(",") if s.strip()]
                profile.hangout_spots = spots

            # Save to database incrementally
            await self._persist_profile_to_db(user_id, profile)

            logger.info(f"Collected {field_name} for user {user_id}")

            return OnboardingToolResponse(
                success=True,
                message=f"Successfully stored {field_name}",
                data={field_name: value},
            )

        except Exception as e:
            logger.error(f"Error collecting profile field: {e}")
            return OnboardingToolResponse(
                success=False,
                error=str(e),
            )

    async def configure_preferences(
        self,
        user_id: UUID,
        darkness_level: int | None = None,
        pacing_weeks: int | None = None,
        conversation_style: str | None = None,
    ) -> OnboardingToolResponse:
        """
        Configure user's experience preferences.

        AC-T010.1: configure_preferences server tool
        AC-T010.2: Accepts darkness_level, pacing, conversation_style
        AC-T010.3: Validates ranges

        Args:
            user_id: User's UUID
            darkness_level: Experience intensity 1-5
            pacing_weeks: Game duration 4 or 8
            conversation_style: listener, balanced, or sharer

        Returns:
            Response indicating success or failure
        """
        try:
            profile = self._get_or_create_profile(user_id)
            updates = {}

            # Validate and set darkness_level
            if darkness_level is not None:
                if not 1 <= darkness_level <= 5:
                    return OnboardingToolResponse(
                        success=False,
                        error=f"darkness_level must be between 1 and 5, got {darkness_level}",
                    )
                profile.darkness_level = darkness_level
                updates["darkness_level"] = darkness_level

            # Validate and set pacing_weeks
            if pacing_weeks is not None:
                if pacing_weeks not in (4, 8):
                    return OnboardingToolResponse(
                        success=False,
                        error=f"pacing_weeks must be 4 or 8, got {pacing_weeks}",
                    )
                profile.pacing_weeks = pacing_weeks
                updates["pacing_weeks"] = pacing_weeks

            # Validate and set conversation_style
            if conversation_style is not None:
                try:
                    style = ConversationStyle(conversation_style.lower())
                    profile.conversation_style = style
                    updates["conversation_style"] = style.value
                except ValueError:
                    return OnboardingToolResponse(
                        success=False,
                        error=f"Invalid conversation_style: {conversation_style}",
                    )

            # Save if any updates were made
            if updates:
                await self._persist_profile_to_db(user_id, profile)
                logger.info(f"Configured preferences for user {user_id}: {updates}")

            return OnboardingToolResponse(
                success=True,
                message="Preferences configured successfully",
                data=updates,
            )

        except Exception as e:
            logger.error(f"Error configuring preferences: {e}")
            return OnboardingToolResponse(
                success=False,
                error=str(e),
            )

    async def complete_onboarding(
        self,
        user_id: UUID,
        call_id: str,
        notes: str | None = None,
    ) -> OnboardingToolResponse:
        """
        Mark onboarding as complete and trigger handoff.

        AC-T011.1: complete_onboarding server tool
        AC-T011.2: Marks user as onboarded
        AC-T011.3: Triggers handoff process

        Args:
            user_id: User's UUID
            call_id: ElevenLabs conversation ID
            notes: Optional notes about the call

        Returns:
            Response with profile summary
        """
        try:
            profile = self._get_or_create_profile(user_id)

            # Convert profile to dict for database storage
            profile_dict = profile.to_context_dict()
            if notes:
                profile_dict["onboarding_notes"] = notes

            # Complete onboarding in database (sets status, call_id, profile, timestamp)
            async with get_session_maker()() as session:
                user_repo = UserRepository(session)
                await user_repo.complete_onboarding(
                    user_id=user_id,
                    call_id=call_id,
                    profile=profile_dict,
                )

                # Spec 104 T1.3: Seed initial vice preferences from onboarding profile
                try:
                    from nikita.engine.vice.seeder import seed_vices_from_profile
                    from nikita.db.repositories.vice_repository import VicePreferenceRepository
                    vice_repo = VicePreferenceRepository(session)
                    await seed_vices_from_profile(
                        user_id=user_id,
                        profile=profile,
                        vice_repo=vice_repo,
                    )
                except Exception as e:
                    logger.warning("vice_seeding_failed error=%s", str(e))

                await session.commit()

            # Trigger the handoff to Nikita
            await self._trigger_handoff(user_id, profile)

            logger.info(f"Completed onboarding for user {user_id}")

            # Return summary
            return OnboardingToolResponse(
                success=True,
                message="Onboarding completed! Nikita will message you shortly.",
                data={
                    "profile": profile_dict,
                    "call_id": call_id,
                },
            )

        except Exception as e:
            logger.error(f"Error completing onboarding: {e}")
            return OnboardingToolResponse(
                success=False,
                error=str(e),
            )

    async def end_call(
        self,
        user_id: UUID,
        reason: str = "onboarding_complete",
    ) -> OnboardingToolResponse:
        """
        Signal that the call should end.

        This is called by the agent after complete_onboarding to cleanly
        terminate the conversation. The actual call termination is handled
        by ElevenLabs when the agent stops responding.

        Args:
            user_id: User's UUID
            reason: Why the call is ending

        Returns:
            Response confirming the call should end
        """
        logger.info(f"End call requested for user {user_id}: {reason}")

        return OnboardingToolResponse(
            success=True,
            message="Call ending. Say goodbye and stop talking.",
            data={"reason": reason, "action": "terminate"},
        )

    # Private helper methods

    def _get_or_create_profile(self, user_id: UUID) -> UserOnboardingProfile:
        """Get existing in-memory profile or create a new one."""
        user_key = str(user_id)
        if user_key not in self._profiles:
            self._profiles[user_key] = UserOnboardingProfile()
        return self._profiles[user_key]

    async def _persist_profile_to_db(
        self, user_id: UUID, profile: UserOnboardingProfile
    ) -> None:
        """Persist profile updates to database.

        Called incrementally during the call to ensure data isn't lost
        if the call is interrupted.
        """
        profile_dict = profile.to_context_dict()

        async with get_session_maker()() as session:
            user_repo = UserRepository(session)
            await user_repo.update_onboarding_profile(user_id, profile_dict)
            await session.commit()

        # Also update local cache
        self._profiles[str(user_id)] = profile

    async def _trigger_handoff(
        self, user_id: UUID, profile: UserOnboardingProfile
    ) -> None:
        """Trigger the handoff process to Nikita.

        Supports two modes (Spec 033 - Unified Phone Number):
        1. Voice callback: If user has phone_number, Nikita calls back
        2. Text message: Fallback via Telegram

        The voice callback flow:
        - Meta-Nikita hangs up
        - After 5s delay, Nikita calls the user
        - User continues relationship via voice

        Falls back to Telegram text if:
        - User has no phone number
        - Voice callback fails
        """
        try:
            from nikita.onboarding.handoff import HandoffManager

            # Get user data from database
            async with get_session_maker()() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get(user_id)

                if not user:
                    logger.error(f"User {user_id} not found for handoff")
                    return

                telegram_id = user.telegram_id
                phone_number = user.phone_number
                user_name = "friend"
                if user.onboarding_profile and isinstance(user.onboarding_profile, dict):
                    user_name = user.onboarding_profile.get("user_name", "friend")

            handoff = HandoffManager()

            # Prefer voice callback if user has phone number
            if phone_number:
                logger.info(
                    f"Initiating voice callback for user {user_id} to {phone_number}"
                )
                result = await handoff.execute_handoff_with_voice_callback(
                    user_id=user_id,
                    telegram_id=telegram_id or 0,
                    phone_number=phone_number,
                    profile=profile,
                    user_name=user_name,
                    callback_delay_seconds=5,  # Wait 5s after Meta-Nikita hangs up
                )

                if result.nikita_callback_initiated:
                    logger.info(
                        f"Voice handoff completed for user {user_id}: "
                        f"conversation_id={result.nikita_conversation_id}"
                    )
                    return

                # Voice failed but text succeeded
                if result.first_message_sent:
                    logger.info(
                        f"Voice callback failed, text handoff completed for user {user_id}"
                    )
                    return

            # Fallback: Text message via Telegram
            if not telegram_id:
                logger.warning(f"User {user_id} has no telegram_id for handoff")
                return

            result = await handoff.execute_handoff(
                user_id=user_id,
                telegram_id=telegram_id,
                profile=profile,
            )

            if result.success:
                logger.info(f"Text handoff completed for user {user_id}: {result.message}")
            else:
                logger.error(f"Handoff failed for user {user_id}: {result.error}")

        except Exception as e:
            logger.error(f"Error triggering handoff for user {user_id}: {e}")
