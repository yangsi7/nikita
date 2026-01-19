"""Handoff Manager (Spec 028 Phase G).

Implements HandoffManager for transitioning from Meta-Nikita onboarding
to the main Nikita experience.

Implements:
- AC-T026.1-4: HandoffManager class
- AC-T027.1-4: First Nikita message generation
- AC-T028.1-4: User status update
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
    profile_summary: str | None = None
    message: str | None = None
    error: str | None = None


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
