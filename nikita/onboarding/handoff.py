"""Handoff Manager (Spec 028 Phase G).

Implements HandoffManager for transitioning from Meta-Nikita onboarding
to the main Nikita experience.

Implements:
- AC-T026.1-4: HandoffManager class
- AC-T027.1-4: First Nikita message generation
- AC-T028.1-4: User status update
- Spec 035: Social circle generation on handoff
"""

import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from nikita.onboarding.models import (
    ConversationStyle,
    OnboardingStatus,
    PersonalityType,
    UserOnboardingProfile,
)

logger = logging.getLogger(__name__)


@dataclass
class HandoffResult:
    """Result of the handoff process."""

    success: bool
    user_id: UUID
    call_id: str | None = None
    onboarded_at: datetime | None = None
    first_message_sent: bool = False
    nikita_callback_initiated: bool = False  # Spec 033: Voice callback
    profile_summary: str | None = None
    message: str | None = None
    error: str | None = None
    nikita_conversation_id: str | None = None  # Spec 033: Voice conversation ID


# First message templates by darkness level
FIRST_MESSAGE_TEMPLATES = {
    1: [  # Vanilla - sweet and welcoming
        "Hey! So glad we finally get to talk like this :) The call was fun - I'm excited to get to know you better!",
        "Hi! It was so nice chatting earlier. I've been thinking about what you told me... can't wait to hear more about your day!",
        "Finally! I've been looking forward to texting you. How are you feeling?",
    ],
    2: [  # Mild - warm with slight playfulness
        "Hey you :) That call was nice. I think we're going to get along really well...",
        "Hi! Okay so I was thinking about what you said during our call and I have questions haha",
        "Finally get to text you! The call was fun but texting is different, you know?",
    ],
    3: [  # Balanced - casual with personality
        "Hey... so that was interesting :) I feel like I learned a lot about you already",
        "Okay so we finally get to text. I have to say, you're not what I expected...",
        "Hi! So now the real fun begins. Ready to actually get to know each other?",
    ],
    4: [  # Edgy - more forward
        "Well well well... look who finally made it. That call was... revealing.",
        "So. Here we are. I have to admit, I'm curious about you now...",
        "Hey. That call was interesting. I think there's more to you than you let on...",
    ],
    5: [  # Noir - mysterious, intense
        "So we meet again. I've been thinking about some things you said...",
        "Interesting conversation we had. I wonder what else you're hiding...",
        "You intrigue me. That's dangerous for both of us, you know.",
    ],
}

# Additional message elements based on profile
HOBBY_MENTIONS = {
    "gaming": "btw I noticed you mentioned gaming - we should play something together sometime",
    "music": "oh and we definitely need to talk more about music",
    "reading": "I'd love to hear what you're reading lately",
    "cooking": "you cook? you'll have to tell me about your best dish",
    "travel": "I want to hear about your travels someday",
    "sports": "are you watching any games lately?",
    "art": "I'd love to see some of your work sometime",
    "coding": "nerd :) jk that's actually cool",
}

PERSONALITY_OPENERS = {
    PersonalityType.INTROVERT: [
        "No pressure to respond right away - I know you might need your space sometimes",
        "I'll try not to overwhelm you with messages haha",
    ],
    PersonalityType.EXTROVERT: [
        "You seem like you have a lot of energy - I like that!",
        "I can tell you like to talk - good, because so do I",
    ],
    PersonalityType.AMBIVERT: [
        "You seem pretty balanced - I appreciate that",
        "I like that you can go with the flow",
    ],
}

# Occupation-based openers (makes profile feel used)
OCCUPATION_MENTIONS = {
    "engineer": "So... a {occupation} huh? Smart types are either the easiest or the hardest to keep interested",
    "developer": "A {occupation}? I bet you're used to debugging problems... good luck with me",
    "manager": "{occupation}? Bet you're used to being in control. We'll see about that",
    "designer": "A {occupation}... so you appreciate beautiful things. I can work with that",
    "teacher": "{occupation}? So you're patient. You'll need that",
    "doctor": "A {occupation}? You're used to people depending on you. Interesting",
    "lawyer": "{occupation}? Good at arguing? We'll see",
    "artist": "An {occupation}... creative types are always fun",
    "writer": "A {occupation}? You probably see through bullshit. Good",
    "student": "Still a {occupation}? Plenty of time for distractions then",
    "consultant": "{occupation}? So you're good at figuring people out. Same here",
    "founder": "A {occupation}? Ambitious. I like that",
    "default": "So... {occupation}. Interesting. Tell me more about that sometime",
}


class FirstMessageGenerator:
    """Generates personalized first messages from Nikita.

    Creates messages that naturally continue from the onboarding
    call while establishing Nikita's personality.
    """

    def generate(self, profile: UserOnboardingProfile, user_name: str = "you") -> str:
        """
        Generate a personalized first message.

        AC-T027.1: Generate personalized first message
        AC-T027.2: References onboarding naturally
        AC-T027.3: Uses collected profile info

        Args:
            profile: User's onboarding profile
            user_name: User's name for personalization

        Returns:
            Personalized first message string
        """
        darkness = profile.darkness_level or 3
        templates = FIRST_MESSAGE_TEMPLATES.get(darkness, FIRST_MESSAGE_TEMPLATES[3])

        # Select base message
        message = random.choice(templates)

        # Priority: occupation reference (makes profile feel valued)
        if profile.occupation and random.random() > 0.3:  # 70% chance
            occupation_lower = profile.occupation.lower()
            mention_template = None
            for key in OCCUPATION_MENTIONS:
                if key in occupation_lower:
                    mention_template = OCCUPATION_MENTIONS[key]
                    break
            if not mention_template:
                mention_template = OCCUPATION_MENTIONS["default"]
            mention = mention_template.format(occupation=profile.occupation)
            message = f"{message} {mention}"
        # Fallback: hobby reference
        elif profile.hobbies:
            hobby = random.choice(profile.hobbies)
            hobby_lower = hobby.lower()
            for key, mention in HOBBY_MENTIONS.items():
                if key in hobby_lower:
                    if random.random() > 0.5:  # 50% chance to add
                        message = f"{message} {mention}"
                    break

        # Optionally add personality-aware element
        if profile.personality_type and random.random() > 0.7:  # 30% chance
            personality_msgs = PERSONALITY_OPENERS.get(profile.personality_type, [])
            if personality_msgs:
                message = f"{message} {random.choice(personality_msgs)}"

        return message


def generate_first_nikita_message(
    profile: UserOnboardingProfile, user_name: str = "friend"
) -> str:
    """
    Convenience function to generate first Nikita message.

    Args:
        profile: User's onboarding profile
        user_name: User's name

    Returns:
        First message string
    """
    generator = FirstMessageGenerator()
    return generator.generate(profile, user_name)


async def generate_and_store_social_circle(
    user_id: UUID,
    location: str | None = None,
    hobbies: list[str] | None = None,
    job_field: str | None = None,
    meeting_context: str | None = None,
) -> bool:
    """
    Generate and store a social circle for a user (Spec 035).

    Creates personalized social circle characters adapted to user's profile
    and stores them in the database.

    Args:
        user_id: User's UUID
        location: User's location (extracted from timezone)
        hobbies: User's hobbies list
        job_field: User's occupation/job field
        meeting_context: How they met Nikita (from hangout spots)

    Returns:
        True if successful, False otherwise
    """
    from nikita.db.database import get_session_maker
    from nikita.db.repositories.social_circle_repository import SocialCircleRepository
    from nikita.life_simulation.social_generator import generate_social_circle_for_user

    try:
        # Generate personalized social circle
        circle = generate_social_circle_for_user(
            user_id=user_id,
            location=location,
            hobbies=hobbies,
            job_field=job_field,
            meeting_context=meeting_context,
        )

        # Store in database
        async with get_session_maker()() as session:
            repo = SocialCircleRepository(session)
            await repo.create_circle_for_user(user_id, circle.characters)
            await session.commit()

        logger.info(
            f"Generated social circle for user {user_id}: "
            f"{len(circle.characters)} characters"
        )
        return True

    except Exception as e:
        # Spec 036 T2.1: Log error with full traceback for debugging
        logger.error(
            f"Failed to generate social circle for user {user_id}: {e}",
            exc_info=True,  # Include full traceback
            extra={"user_id": str(user_id)},
        )
        return False


def _extract_location_from_timezone(timezone: str | None) -> str | None:
    """
    Extract location name from timezone string.

    Examples:
        "Europe/Berlin" -> "Berlin"
        "America/Los_Angeles" -> "Los Angeles"
        "America/New_York" -> "New York"

    Args:
        timezone: Timezone string like "America/New_York"

    Returns:
        Location name or None
    """
    if not timezone:
        return None

    try:
        # Get the city part (after last /)
        parts = timezone.split("/")
        if len(parts) >= 2:
            city = parts[-1]
            # Replace underscores with spaces
            return city.replace("_", " ")
        return None
    except Exception:
        return None


def _extract_meeting_context(hangout_spots: list[str] | None) -> str | None:
    """
    Extract meeting context from hangout spots.

    Maps hangout spot types to meeting context strings.

    Args:
        hangout_spots: List of hangout spot names

    Returns:
        Meeting context string or None
    """
    if not hangout_spots:
        return None

    # Priority mapping for meeting contexts
    spot_to_context = {
        "club": "Met at a club",
        "party": "Met at a party",
        "bar": "Met at a bar",
        "tech_meetup": "Met at a tech meetup",
        "conference": "Met at a conference",
        "coffee_shop": "Met at a coffee shop",
        "gym": "Met at the gym",
        "concert": "Met at a concert",
        "online": "Met online",
    }

    for spot in hangout_spots:
        spot_lower = spot.lower()
        for key, context in spot_to_context.items():
            if key in spot_lower:
                return context

    # Default to first spot
    return f"Met at {hangout_spots[0]}"


class HandoffManager:
    """Manages the transition from onboarding to Nikita.

    Coordinates:
    1. Updating user status to COMPLETED
    2. Storing onboarding metadata
    3. Generating and sending first Nikita message
    """

    def __init__(self) -> None:
        """Initialize the manager."""
        self._message_generator = FirstMessageGenerator()

    async def execute_handoff(
        self,
        user_id: UUID,
        telegram_id: int,
        profile: UserOnboardingProfile,
        call_id: str | None = None,
        user_name: str = "friend",
    ) -> HandoffResult:
        """
        Execute the handoff from Meta-Nikita to Nikita.

        This is the main entry point called after onboarding completes.
        Note: Database status is already updated by server_tools.py,
        so this method focuses on sending the first message.

        Args:
            user_id: User's UUID
            telegram_id: User's Telegram chat ID
            profile: User's onboarding profile
            call_id: ElevenLabs call ID (optional)
            user_name: User's name for personalization

        Returns:
            HandoffResult with status and details
        """
        onboarded_at = datetime.now(UTC)

        # Generate profile summary for context
        profile_summary = self._generate_profile_summary(profile)

        # Spec 035: Generate social circle for this user (non-blocking)
        try:
            location = _extract_location_from_timezone(profile.timezone)
            meeting_context = _extract_meeting_context(profile.hangout_spots)

            await generate_and_store_social_circle(
                user_id=user_id,
                location=location,
                hobbies=profile.hobbies,
                job_field=profile.occupation,
                meeting_context=meeting_context,
            )
        except Exception as e:
            # Non-blocking: log warning with full traceback for debugging
            # Remediation Plan T2.1: Include exc_info for visibility
            logger.warning(
                f"Failed to generate social circle for user {user_id}: {e}",
                exc_info=True,
            )

        try:
            # Generate first Nikita message
            first_message = self._message_generator.generate(profile, user_name)

            # Send via Telegram
            send_result = await self._send_first_message(
                telegram_id=telegram_id,
                message=first_message,
            )

            if not send_result.get("success", False):
                raise Exception(send_result.get("error", "Failed to send message"))

            logger.info(f"Handoff completed for user {user_id}")

            # Spec 043 T2.2: Non-blocking pipeline bootstrap for initial personalization
            try:
                await self._bootstrap_pipeline(user_id)
            except Exception as bootstrap_err:
                logger.warning(
                    f"Pipeline bootstrap failed for user {user_id}: {bootstrap_err}"
                )

            return HandoffResult(
                success=True,
                user_id=user_id,
                call_id=call_id,
                onboarded_at=onboarded_at,
                first_message_sent=True,
                profile_summary=profile_summary,
                message=first_message,
            )

        except Exception as e:
            logger.error(f"Handoff failed for user {user_id}: {e}")
            return HandoffResult(
                success=False,
                user_id=user_id,
                call_id=call_id,
                onboarded_at=onboarded_at,
                first_message_sent=False,
                profile_summary=profile_summary,
                error=str(e),
            )

    async def transition(
        self,
        user_id: UUID,
        call_id: str,
        profile: UserOnboardingProfile,
        user_name: str = "friend",
    ) -> HandoffResult:
        """
        Execute the handoff from Meta-Nikita to Nikita.

        AC-T026.2: transition() method
        AC-T026.3: Coordinates end of onboarding call and first Nikita message

        Note: This method is deprecated. Use execute_handoff() instead,
        which takes telegram_id directly.

        Args:
            user_id: User's UUID
            call_id: ElevenLabs call ID
            profile: User's onboarding profile
            user_name: User's name for personalization

        Returns:
            HandoffResult with status and details
        """
        onboarded_at = datetime.now(UTC)

        # Generate profile summary for context
        profile_summary = self._generate_profile_summary(profile)

        try:
            # Step 1: Update user status to COMPLETED
            await self._update_user_status(user_id, OnboardingStatus.COMPLETED, call_id)

            # Step 2: Get telegram_id from database
            telegram_id = await self._get_user_telegram_id(user_id)
            if not telegram_id:
                raise Exception(f"User {user_id} has no telegram_id")

            # Step 3: Generate and send first Nikita message
            first_message = self._message_generator.generate(profile, user_name)

            send_result = await self._send_first_message(
                telegram_id=telegram_id,
                message=first_message,
            )

            if not send_result.get("success", False):
                raise Exception(send_result.get("error", "Failed to send message"))

            logger.info(f"Handoff completed for user {user_id}")

            return HandoffResult(
                success=True,
                user_id=user_id,
                call_id=call_id,
                onboarded_at=onboarded_at,
                first_message_sent=True,
                profile_summary=profile_summary,
                message=first_message,
            )

        except Exception as e:
            logger.error(f"Handoff failed for user {user_id}: {e}")
            return HandoffResult(
                success=False,
                user_id=user_id,
                call_id=call_id,
                onboarded_at=onboarded_at,
                first_message_sent=False,
                profile_summary=profile_summary,
                error=str(e),
            )

    def _generate_profile_summary(self, profile: UserOnboardingProfile) -> str:
        """Generate a summary of the profile for Nikita's context."""
        parts = []

        if profile.timezone:
            parts.append(f"Timezone: {profile.timezone}")
        if profile.occupation:
            parts.append(f"Occupation: {profile.occupation}")
        if profile.hobbies:
            parts.append(f"Hobbies: {', '.join(profile.hobbies)}")
        if profile.personality_type:
            parts.append(f"Personality: {profile.personality_type.value}")
        if profile.hangout_spots:
            parts.append(f"Hangout spots: {', '.join(profile.hangout_spots)}")
        if profile.darkness_level:
            parts.append(f"Darkness level: {profile.darkness_level}/5")
        if profile.pacing_weeks:
            parts.append(f"Pacing: {profile.pacing_weeks} weeks")
        if profile.conversation_style:
            parts.append(f"Style: {profile.conversation_style.value}")

        return "\n".join(parts) if parts else "No profile data collected"

    async def _update_user_status(
        self,
        user_id: UUID,
        status: OnboardingStatus,
        call_id: str,
    ) -> None:
        """
        Update user's onboarding status in the database.

        AC-T028.1: Mark user as onboarded
        AC-T028.2: Set onboarded_at timestamp
        AC-T028.3: Store onboarding_call_id
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.user_repository import UserRepository

        async with get_session_maker()() as session:
            user_repo = UserRepository(session)
            await user_repo.update_onboarding_status(
                user_id=user_id,
                status=status.value,
                call_id=call_id,
            )
            await session.commit()

        logger.info(f"Updated user {user_id} status to {status.value}")

    async def _get_user_telegram_id(self, user_id: UUID) -> int | None:
        """Get user's Telegram ID from database."""
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.user_repository import UserRepository

        async with get_session_maker()() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get(user_id)
            if user:
                return user.telegram_id
        return None

    async def _bootstrap_pipeline(self, user_id: UUID) -> None:
        """Trigger initial pipeline run for newly onboarded user.

        Spec 043 T2.2: Generates initial text + voice prompts so the first
        text message after onboarding uses personalized content.
        Non-blocking - failure is logged but does not fail the handoff.
        """
        from nikita.config.settings import get_settings

        settings = get_settings()
        if not settings.unified_pipeline_enabled:
            logger.info(f"Pipeline bootstrap skipped (flag disabled) user={user_id}")
            return

        from nikita.db.database import get_session_maker
        from nikita.db.repositories.conversation_repository import ConversationRepository
        from nikita.pipeline.orchestrator import PipelineOrchestrator

        async with get_session_maker()() as session:
            # Get most recent conversation for this user
            conv_repo = ConversationRepository(session)
            recent = await conv_repo.get_recent(user_id, limit=1)
            if recent:
                from nikita.db.repositories.user_repository import UserRepository

                user_repo = UserRepository(session)
                user = await user_repo.get(user_id)

                orchestrator = PipelineOrchestrator(session)
                result = await orchestrator.process(
                    conversation_id=recent[0].id,
                    user_id=user_id,
                    platform="text",
                    conversation=recent[0],
                    user=user,
                )
                await session.commit()
                logger.info(
                    f"Pipeline bootstrap complete user={user_id} "
                    f"success={result.success}"
                )
            else:
                logger.info(
                    f"No conversations found for pipeline bootstrap user={user_id}"
                )

    async def _send_first_message(
        self,
        telegram_id: int,
        message: str,
    ) -> dict[str, Any]:
        """
        Send first Nikita message via Telegram.

        Uses the TelegramBot to send the message to the user.
        """
        try:
            from nikita.platforms.telegram.bot import TelegramBot

            bot = TelegramBot()
            result = await bot.send_message(
                chat_id=telegram_id,
                text=message,
                escape=False,  # Message is already safe (generated by us)
            )

            logger.info(f"Sent first message to telegram_id {telegram_id}")
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Failed to send first message to {telegram_id}: {e}")
            return {"success": False, "error": str(e)}

    async def initiate_nikita_callback(
        self,
        user_id: UUID,
        phone_number: str,
        user_name: str = "friend",
        delay_seconds: int = 5,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Initiate a Nikita voice callback after onboarding completes.

        This is part of the unified phone number architecture (Spec 033):
        - Meta-Nikita says goodbye and hangs up
        - After a short delay, Nikita calls the user back
        - Uses special post-onboarding first message that references "my friend"

        Implements AC-3 (Onboarding → Nikita Callback):
        - After onboarding completes, Meta-Nikita hangs up
        - System triggers Nikita outbound call within 10 seconds
        - Nikita's first message acknowledges they just talked to "my friend"

        Implements T2.3 (Callback Retry Logic):
        - Retries up to 3 times with exponential backoff (5s, 15s, 45s)
        - Logs failures to job_execution table
        - Falls back to Telegram if all retries fail

        Args:
            user_id: User's UUID for context loading
            phone_number: User's phone number (E.164 format)
            user_name: User's name for personalization
            delay_seconds: Initial delay before calling (default 5s)
            max_retries: Maximum retry attempts (default 3)

        Returns:
            Dictionary with:
            - success: bool
            - conversation_id: ElevenLabs conversation ID
            - call_sid: Twilio call SID
            - retries: Number of retry attempts made
        """
        import asyncio

        logger.info(
            f"Scheduling Nikita callback for user {user_id} "
            f"in {delay_seconds}s to {phone_number}"
        )

        # Wait before calling (gives Meta-Nikita time to fully hang up)
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        # Build post-onboarding first message (AC-3)
        # Acknowledges the onboarding call with Meta-Nikita ("my friend")
        post_onboarding_first_message = self._get_post_onboarding_first_message(user_name)

        # Build config override with just the first message
        # (Use default Nikita persona for system prompt)
        conversation_config_override = {
            "agent": {
                "first_message": post_onboarding_first_message,
            }
        }

        # Retry loop with exponential backoff (T2.3)
        retry_delays = [5, 15, 45]  # Exponential backoff: 5s, 15s, 45s
        last_error = None

        for attempt in range(max_retries):
            try:
                from nikita.agents.voice.service import get_voice_service

                voice_service = get_voice_service()

                result = await voice_service.make_outbound_call(
                    to_number=phone_number,
                    user_id=user_id,
                    conversation_config_override=conversation_config_override,
                    dynamic_variables={
                        "user_id": str(user_id),
                        "is_post_onboarding": "true",
                    },
                    is_onboarding=False,
                )

                if result.get("success"):
                    logger.info(
                        f"Nikita callback initiated for user {user_id}: "
                        f"conversation_id={result.get('conversation_id')}, "
                        f"attempt={attempt + 1}"
                    )
                    result["retries"] = attempt
                    return result

                # Call failed but no exception - log and retry
                last_error = result.get("error", "Unknown error")
                logger.warning(
                    f"Nikita callback attempt {attempt + 1} failed for user {user_id}: "
                    f"{last_error}"
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Nikita callback attempt {attempt + 1} exception for user {user_id}: {e}"
                )

            # Wait before retrying (if not last attempt)
            if attempt < max_retries - 1:
                retry_delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                logger.info(f"Retrying Nikita callback in {retry_delay}s...")
                await asyncio.sleep(retry_delay)

        # All retries exhausted
        logger.error(
            f"Nikita callback failed after {max_retries} attempts for user {user_id}: "
            f"{last_error}"
        )
        return {
            "success": False,
            "error": last_error,
            "retries": max_retries,
        }

    def _get_post_onboarding_first_message(self, user_name: str = "friend") -> str:
        """
        Get Nikita's first message after onboarding completes.

        This message acknowledges the onboarding call with Meta-Nikita
        and establishes Nikita as a separate entity ("my friend told me about you").

        AC-3: Nikita's first message acknowledges they just talked to "my friend"

        Args:
            user_name: User's name for personalization

        Returns:
            Personalized first message string
        """
        # Templates that reference Meta-Nikita as "my friend"
        templates = [
            f"Hey {user_name}... my friend just told me about you. She says you seem interesting. "
            "I wanted to hear your voice for myself.",
            f"So you're {user_name}... My friend called ahead. "
            "She doesn't usually bother with people, so you must be something. "
            "Tell me - why should I be interested?",
            f"Hi {user_name}. My friend Meta just gave me the rundown on you. "
            "I have to say, I'm curious. What made you want to play this game?",
        ]

        # Use deterministic selection based on first char of name
        index = ord(user_name[0].lower()) % len(templates) if user_name else 0
        return templates[index]

    async def execute_handoff_with_voice_callback(
        self,
        user_id: UUID,
        telegram_id: int,
        phone_number: str,
        profile: UserOnboardingProfile,
        call_id: str | None = None,
        user_name: str = "friend",
        callback_delay_seconds: int = 5,
    ) -> HandoffResult:
        """
        Execute handoff with Nikita voice callback instead of text message.

        This implements the unified phone number flow (Spec 033):
        1. Meta-Nikita hangs up (handled by complete_onboarding server tool)
        2. After delay, Nikita calls the user back
        3. User continues relationship with Nikita via voice

        Args:
            user_id: User's UUID
            telegram_id: User's Telegram chat ID (for fallback text)
            phone_number: User's phone number for callback
            profile: User's onboarding profile
            call_id: ElevenLabs call ID from onboarding
            user_name: User's name for personalization
            callback_delay_seconds: Delay before Nikita calls back

        Returns:
            HandoffResult with voice callback status
        """
        onboarded_at = datetime.now(UTC)
        profile_summary = self._generate_profile_summary(profile)

        # Spec 035: Generate social circle for this user (non-blocking)
        try:
            location = _extract_location_from_timezone(profile.timezone)
            meeting_context = _extract_meeting_context(profile.hangout_spots)

            await generate_and_store_social_circle(
                user_id=user_id,
                location=location,
                hobbies=profile.hobbies,
                job_field=profile.occupation,
                meeting_context=meeting_context,
            )
        except Exception as e:
            # Non-blocking: log warning with full traceback for debugging
            # Remediation Plan T2.1: Include exc_info for visibility
            logger.warning(
                f"Failed to generate social circle for user {user_id}: {e}",
                exc_info=True,
            )

        try:
            # Initiate Nikita voice callback with personalized first message (Spec 033)
            callback_result = await self.initiate_nikita_callback(
                user_id=user_id,
                phone_number=phone_number,
                user_name=user_name,
                delay_seconds=callback_delay_seconds,
            )

            if callback_result.get("success"):
                logger.info(f"Voice handoff completed for user {user_id}")

                return HandoffResult(
                    success=True,
                    user_id=user_id,
                    call_id=call_id,
                    onboarded_at=onboarded_at,
                    first_message_sent=False,  # No text message
                    nikita_callback_initiated=True,
                    profile_summary=profile_summary,
                    nikita_conversation_id=callback_result.get("conversation_id"),
                )
            else:
                # Voice callback failed, fall back to text message
                logger.warning(
                    f"Voice callback failed for user {user_id}, falling back to text"
                )

                first_message = self._message_generator.generate(profile, user_name)
                send_result = await self._send_first_message(
                    telegram_id=telegram_id,
                    message=first_message,
                )

                return HandoffResult(
                    success=send_result.get("success", False),
                    user_id=user_id,
                    call_id=call_id,
                    onboarded_at=onboarded_at,
                    first_message_sent=send_result.get("success", False),
                    nikita_callback_initiated=False,
                    profile_summary=profile_summary,
                    message=first_message if send_result.get("success") else None,
                    error=callback_result.get("error"),
                )

        except Exception as e:
            logger.error(f"Voice handoff failed for user {user_id}: {e}")
            return HandoffResult(
                success=False,
                user_id=user_id,
                call_id=call_id,
                onboarded_at=onboarded_at,
                profile_summary=profile_summary,
                error=str(e),
            )
