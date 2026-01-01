"""Inbound call handling for voice agent.

This module implements InboundCallHandler and VoiceSessionManager for:
- Processing incoming voice calls via Twilio
- Looking up users by phone number
- Checking chapter-based availability
- Managing voice sessions with disconnect recovery

Implements US-15 (Inbound Calls) acceptance criteria:
- AC-T076.1: handle_incoming_call(phone_number) processes inbound call
- AC-T076.2: Looks up user by phone number
- AC-T076.3: Checks call availability (chapter-based)
- AC-T076.4: Returns accept_call=False with message if unavailable
- AC-T077.1-4: VoiceSessionManager tracks sessions and recovery
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from nikita.db.models.user import User

logger = logging.getLogger(__name__)

# Session states
SESSION_STATE_ACTIVE = "ACTIVE"
SESSION_STATE_DISCONNECTED = "DISCONNECTED"
SESSION_STATE_FINALIZED = "FINALIZED"

# Recovery timeout in seconds
RECOVERY_TIMEOUT_SECONDS = 30


class VoiceSessionManager:
    """Manages voice call sessions with disconnect recovery.

    Tracks session state (ACTIVE, DISCONNECTED) and allows recovery
    within a 30-second window for connection drops.

    AC-T077.1: Tracks session state
    AC-T077.2: handle_disconnect marks session as disconnected
    AC-T077.3: attempt_recovery returns True if <30s disconnect
    AC-T077.4: Long disconnects trigger session finalization
    """

    def __init__(self):
        """Initialize session manager with empty session store."""
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, session_id: str, user_id: UUID) -> dict[str, Any]:
        """Create a new voice session.

        Args:
            session_id: Unique session identifier
            user_id: User UUID

        Returns:
            Session data dictionary
        """
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "state": SESSION_STATE_ACTIVE,
            "created_at": datetime.now(timezone.utc),
        }
        self._sessions[session_id] = session

        logger.info(f"[SESSION] Created session {session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        return self._sessions.get(session_id)

    def handle_disconnect(self, session_id: str) -> None:
        """Mark session as disconnected.

        AC-T077.2: handle_disconnect marks session as disconnected

        Args:
            session_id: Session identifier
        """
        session = self._sessions.get(session_id)
        if session:
            session["state"] = SESSION_STATE_DISCONNECTED
            session["disconnected_at"] = datetime.now(timezone.utc)

            logger.info(f"[SESSION] Session {session_id} marked as disconnected")

    def attempt_recovery(self, session_id: str) -> bool:
        """Attempt to recover a disconnected session.

        AC-T077.3: Returns True if disconnect was <30 seconds ago
        AC-T077.4: Long disconnects trigger session finalization

        Args:
            session_id: Session identifier

        Returns:
            True if recovery is possible, False otherwise
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session["state"] != SESSION_STATE_DISCONNECTED:
            return session["state"] == SESSION_STATE_ACTIVE

        disconnected_at = session.get("disconnected_at")
        if not disconnected_at:
            return False

        elapsed = (datetime.now(timezone.utc) - disconnected_at).total_seconds()

        if elapsed <= RECOVERY_TIMEOUT_SECONDS:
            # Recover session
            session["state"] = SESSION_STATE_ACTIVE
            session.pop("disconnected_at", None)
            logger.info(f"[SESSION] Session {session_id} recovered after {elapsed:.1f}s")
            return True
        else:
            # Too long, finalize
            self.finalize_session(session_id)
            logger.info(
                f"[SESSION] Session {session_id} cannot recover "
                f"({elapsed:.1f}s > {RECOVERY_TIMEOUT_SECONDS}s)"
            )
            return False

    def finalize_session(self, session_id: str) -> None:
        """Finalize a session (mark as done).

        Args:
            session_id: Session identifier
        """
        session = self._sessions.get(session_id)
        if session:
            session["state"] = SESSION_STATE_FINALIZED
            session["finalized_at"] = datetime.now(timezone.utc)

            logger.info(f"[SESSION] Session {session_id} finalized")


class InboundCallHandler:
    """Handles incoming voice calls via Twilio/ElevenLabs.

    AC-T076.1: handle_incoming_call(phone_number) processes inbound call
    AC-T076.2: Looks up user by phone number
    AC-T076.3: Checks call availability (chapter-based)
    AC-T076.4: Returns accept_call=False with message if unavailable
    """

    def __init__(self):
        """Initialize inbound call handler."""
        self._session_manager = VoiceSessionManager()

    async def handle_incoming_call(self, phone_number: str) -> dict[str, Any]:
        """Handle an incoming voice call.

        AC-T076.1: Processes inbound call
        AC-T076.2: Looks up user by phone number
        AC-T076.3: Checks availability
        AC-T076.4: Returns accept_call=False if unavailable

        Args:
            phone_number: Caller's phone number (E.164 format)

        Returns:
            Dict with accept_call, message, and optional context
        """
        logger.info(f"[INBOUND] Incoming call from {phone_number}")

        # Look up user by phone number
        user = await self._lookup_user_by_phone(phone_number)

        if not user:
            logger.warning(f"[INBOUND] Unknown caller: {phone_number}")
            return {
                "accept_call": False,
                "message": "Sorry, this number is not registered. "
                           "Please sign up via Telegram first.",
            }

        # Check availability
        is_available, reason = await self._check_availability(user)

        if not is_available:
            logger.info(
                f"[INBOUND] Call rejected for user {user.id}: {reason}"
            )
            return {
                "accept_call": False,
                "message": reason,
                "user_id": str(user.id),
            }

        # Build context for the call
        context = await self._build_context(user)

        # Create session
        session_id = f"voice_inbound_{user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self._session_manager.create_session(session_id, user.id)

        logger.info(f"[INBOUND] Call accepted for user {user.id}")

        return {
            "accept_call": True,
            "message": reason,
            "user_id": str(user.id),
            "session_id": session_id,
            "dynamic_variables": context,
            "conversation_config_override": self._get_tts_config(user),
        }

    async def _lookup_user_by_phone(self, phone_number: str) -> "User | None":
        """Look up user by phone number.

        AC-T076.2: Looks up user by phone number

        Args:
            phone_number: Phone number (E.164 format)

        Returns:
            User or None if not found
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.user_repository import UserRepository

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = UserRepository(session)
            return await repo.get_by_phone_number(phone_number)

    async def _check_availability(self, user: "User") -> tuple[bool, str]:
        """Check if Nikita is available for a call.

        AC-T076.3: Checks call availability (chapter-based)

        Args:
            user: User model

        Returns:
            Tuple of (is_available, reason_message)
        """
        from nikita.agents.voice.availability import get_availability_service

        availability = get_availability_service()
        return availability.is_available(user)

    async def _build_context(self, user: "User") -> dict[str, Any]:
        """Build context for the voice call.

        Args:
            user: User model

        Returns:
            Context dictionary with user info
        """
        from nikita.agents.voice.context import build_dynamic_variables

        return await build_dynamic_variables(user)

    def _get_tts_config(self, user: "User") -> dict[str, Any]:
        """Get TTS configuration based on user's chapter.

        Args:
            user: User model

        Returns:
            Conversation config override with TTS settings
        """
        from nikita.agents.voice.tts_config import get_tts_config

        tts = get_tts_config()
        settings = tts.get_chapter_settings(user.chapter)

        return {
            "tts": {
                "stability": settings.stability,
                "similarity_boost": settings.similarity_boost,
                "speed": settings.speed,
            }
        }


# Singleton instances
_inbound_handler: InboundCallHandler | None = None
_session_manager: VoiceSessionManager | None = None


def get_inbound_handler() -> InboundCallHandler:
    """Get inbound handler singleton."""
    global _inbound_handler
    if _inbound_handler is None:
        _inbound_handler = InboundCallHandler()
    return _inbound_handler


def get_session_manager() -> VoiceSessionManager:
    """Get session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = VoiceSessionManager()
    return _session_manager
