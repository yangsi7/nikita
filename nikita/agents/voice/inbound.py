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

CRITICAL: All paths MUST return dynamic_variables dict per ElevenLabs requirement:
"The dynamic_variables field must contain all dynamic variables defined for the agent."
See: https://elevenlabs.io/docs/agents-platform/customization/personalization/dynamic-variables
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

    def _generate_signed_token(self, user_id: str, session_id: str) -> str:
        """Generate HMAC-signed token for server tool authentication.

        Token format: {user_id}:{session_id}:{timestamp}:{signature}

        Args:
            user_id: User UUID string (or "unknown" for unknown callers)
            session_id: Voice session identifier

        Returns:
            Signed token string
        """
        import hashlib
        import hmac
        import time

        from nikita.config.settings import get_settings

        settings = get_settings()
        timestamp = int(time.time())
        payload = f"{user_id}:{session_id}:{timestamp}"
        secret = settings.elevenlabs_webhook_secret or "default_voice_secret"
        signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}:{signature}"

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
        logger.info(f"[INBOUND] Processing incoming call from {phone_number}")

        # Look up user by phone number
        user = await self._lookup_user_by_phone(phone_number)
        logger.info(f"[INBOUND] User lookup result: found={user is not None}")

        if not user:
            logger.warning(f"[INBOUND] Unknown caller: {phone_number} - returning default dynamic_variables")
            # CRITICAL: Must return dynamic_variables even for rejected calls
            # ElevenLabs requires ALL defined variables in webhook response
            # Generate session ID and signed token for unknown caller
            session_id = f"voice_unknown_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            signed_token = self._generate_signed_token("unknown", session_id)
            defaults = self._get_default_dynamic_variables(signed_token)
            logger.info(f"[INBOUND] Default dynamic_variables keys: {list(defaults.keys())}")
            return {
                "accept_call": False,
                "message": "Sorry, this number is not registered. "
                           "Please sign up via Telegram first.",
                "dynamic_variables": defaults,
                "conversation_config_override": {
                    "agent": {
                        "first_message": "Hmm, I don't recognize this number. "
                                         "You need to sign up through Telegram first, stranger.",
                    }
                },
            }

        # Generate session ID early (needed for signed token in ALL paths)
        session_id = f"voice_inbound_{user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Generate signed token for server tool authentication
        signed_token = self._generate_signed_token(str(user.id), session_id)

        # Build context WITH signed token (includes secrets for ElevenLabs)
        context = await self._build_context(user, signed_token=signed_token)
        logger.info(f"[INBOUND] Built context for user {user.id}: keys={list(context.keys())}")

        # Check availability
        is_available, reason = await self._check_availability(user)
        logger.info(f"[INBOUND] Availability check: is_available={is_available}, reason={reason}")

        if not is_available:
            logger.info(
                f"[INBOUND] Call rejected for user {user.id}: {reason} - returning context as dynamic_variables"
            )
            logger.info(f"[INBOUND] Unavailable user dynamic_variables keys: {list(context.keys())}")
            # CRITICAL: Must return dynamic_variables (with secrets) for unavailable users
            # ElevenLabs requires ALL defined variables in webhook response
            return {
                "accept_call": False,
                "message": reason,
                "user_id": str(user.id),
                "dynamic_variables": context,  # Includes secrets for server tools
                "conversation_config_override": {
                    "agent": {
                        "first_message": reason,  # Use the availability reason as first message
                    }
                },
            }

        # Register session with session manager
        self._session_manager.create_session(session_id, user.id)

        logger.info(f"[INBOUND] Call ACCEPTED for user {user.id}, session_id={session_id}")

        # Get conversation config override with TTS + generated prompt
        config_override = await self._get_conversation_config_override(user)
        logger.info(f"[INBOUND] Accepted call dynamic_variables keys: {list(context.keys())}")
        logger.info(f"[INBOUND] Accepted call config_override keys: {list(config_override.keys()) if config_override else None}")

        result = {
            "accept_call": True,
            "message": reason,
            "user_id": str(user.id),
            "session_id": session_id,
            "dynamic_variables": context,  # Includes secrets for server tools
            "conversation_config_override": config_override,
        }
        logger.info(f"[INBOUND] Returning result: accept_call={result['accept_call']}, has_dv={result['dynamic_variables'] is not None}")
        return result

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

    async def _build_context(
        self, user: "User", signed_token: str | None = None
    ) -> dict[str, Any]:
        """Build context for the voice call.

        Args:
            user: User model
            signed_token: HMAC-signed token for server tool authentication

        Returns:
            Context dictionary with user info INCLUDING secrets for ElevenLabs
        """
        from nikita.agents.voice.context import build_dynamic_variables

        return await build_dynamic_variables(user, signed_token=signed_token)

    def _get_default_dynamic_variables(self, signed_token: str) -> dict[str, str]:
        """Get default dynamic variables for unknown callers.

        ElevenLabs requires ALL defined dynamic variables in webhook response,
        INCLUDING secret variables for server tool parameter substitution.

        Args:
            signed_token: HMAC-signed token for server tool authentication

        Returns:
            Dict with all 11 required dynamic variables (9 visible + 2 secret)
        """
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            time_of_day = "morning"
        elif 12 <= current_hour < 18:
            time_of_day = "afternoon"
        elif 18 <= current_hour < 22:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        return {
            # Visible variables (sent to LLM)
            "user_name": "stranger",
            "chapter": "1",
            "relationship_score": "0",
            "engagement_state": "UNKNOWN",
            "nikita_mood": "neutral",
            "nikita_energy": "low",
            "time_of_day": time_of_day,
            "recent_topics": "",
            "open_threads": "",
            # Secret variables (NOT sent to LLM, used for server tool auth)
            "secret__user_id": "unknown",
            "secret__signed_token": signed_token,
        }

    async def _get_conversation_config_override(self, user: "User") -> dict[str, Any]:
        """Get conversation config override with TTS + cached system prompt.

        FR-033: Pre-call webhook MUST NOT call LLM or Neo4j.
        FR-034: Uses cached_voice_prompt from database for <100ms response.

        If cached prompt is None (first-time caller), uses static fallback prompt.

        Args:
            user: User model

        Returns:
            Conversation config override with TTS and agent prompt
        """
        from nikita.agents.voice.tts_config import get_tts_config_service

        tts = get_tts_config_service()
        settings = tts.get_chapter_settings(user.chapter)

        config: dict[str, Any] = {
            "tts": {
                "stability": settings.stability,
                "similarity_boost": settings.similarity_boost,
                "speed": settings.speed,
            }
        }

        # FR-033: Use cached prompt (NO LLM/Neo4j calls during pre-call)
        # FR-034: cached_voice_prompt is populated by post-processing after each call
        system_prompt = user.cached_voice_prompt
        if not system_prompt:
            # First-time caller or cache not yet populated - use static fallback
            logger.info(f"[INBOUND] No cached prompt for user {user.id}, using fallback")
            system_prompt = self._generate_fallback_prompt(user)

        config["agent"] = {
            "prompt": {"prompt": system_prompt},
            "first_message": self._get_first_message(user),
        }

        return config

    def _generate_fallback_prompt(self, user: "User") -> str:
        """Generate fallback prompt using static VoiceAgentConfig.

        FR-034: Used when cached_voice_prompt is None (first-time caller).
        Post-processing will populate the cache for subsequent calls.

        Args:
            user: User model

        Returns:
            Static system prompt
        """
        from nikita.agents.voice.config import VoiceAgentConfig
        from nikita.config.settings import get_settings

        config = VoiceAgentConfig(settings=get_settings())

        # Get vices
        vices = getattr(user, "vice_preferences", []) or []
        primary_vices = [v for v in vices if getattr(v, "is_primary", False)]

        return config.generate_system_prompt(
            user_id=user.id,
            chapter=user.chapter,
            vices=primary_vices,
            user_name=getattr(user, "name", "friend") or "friend",
            relationship_score=self._get_relationship_score(user),
        )

    def _get_relationship_score(self, user: "User") -> float:
        """Get relationship score from user metrics."""
        if user.metrics:
            return float(getattr(user.metrics, "relationship_score", 50.0))
        return 50.0

    def _get_first_message(self, user: "User") -> str:
        """Get chapter-appropriate first message.

        Args:
            user: User model

        Returns:
            Personalized first message
        """
        name = getattr(user, "name", None) or "you"
        chapter = user.chapter

        first_messages = {
            1: f"Oh, hey... {name}, right? What's going on?",
            2: f"Hey {name}! Good timing, I was just thinking about you.",
            3: f"There you are, {name}. I was hoping you'd call.",
            4: f"Mmm, hey {name}... I've been wanting to hear your voice.",
            5: f"Hi baby... I missed you. What's on your mind?",
        }
        return first_messages.get(chapter, f"Hey {name}, what's up?")

    def _get_tts_config(self, user: "User") -> dict[str, Any]:
        """Get TTS configuration based on user's chapter.

        DEPRECATED: Use _get_conversation_config_override instead.

        Args:
            user: User model

        Returns:
            Conversation config override with TTS settings
        """
        from nikita.agents.voice.tts_config import get_tts_config_service

        tts = get_tts_config_service()
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
