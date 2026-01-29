"""Voice service for call initiation and management.

This module implements VoiceService which handles:
- Call initiation (US-1)
- User context loading
- Signed token generation for server tool auth
- Session management

Implements T006 acceptance criteria:
- AC-T006.1: initiate_call returns signed ElevenLabs connection params
- AC-T006.2: Generates signed token with user_id for server tool auth
- AC-T006.3: Logs call_started event with timestamp
- AC-T006.4: Loads user context for initial greeting customization
"""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from uuid import UUID

from nikita.agents.voice.models import (
    VoiceContext,
    DynamicVariables,
    TTSSettings,
    NikitaMood,
)

if TYPE_CHECKING:
    from nikita.config.settings import Settings
    from nikita.db.models.user import User
    from nikita.memory.graphiti_client import NikitaMemory

logger = logging.getLogger(__name__)


class VoiceService:
    """High-level voice conversation service.

    Handles call initiation, context loading, and session management.
    Works with ElevenLabs Conversational AI via signed tokens and server tools.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize VoiceService with application settings.

        Args:
            settings: Application settings containing ElevenLabs config
        """
        self.settings = settings
        self._sessions: dict[str, dict] = {}  # In-memory session tracking

    async def initiate_call(self, user_id: UUID) -> dict[str, Any]:
        """
        Initiate a voice call for a user.

        Implements FR-001: Call Initiation and FR-008: Session Management.

        Args:
            user_id: UUID of the user initiating the call

        Returns:
            Dictionary with connection parameters:
            - agent_id: ElevenLabs agent to connect to
            - signed_token: Auth token for server tools
            - session_id: Unique session identifier
            - context: Loaded user context
            - dynamic_variables: Variables for prompt interpolation

        Raises:
            ValueError: If user not found or voice not available
        """
        start_time = time.time()
        logger.info(f"[VOICE] Initiating call for user {user_id}")

        # Load user from database
        user = await self._load_user(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        # Check voice availability
        if user.game_status != "active":
            raise ValueError(f"Voice not available: user game_status={user.game_status}")

        # Load context for personalization (AC-T006.4)
        context = await self._load_context(user)

        # Generate session ID
        session_id = self._generate_session_id()

        # Generate signed token for server tool auth (AC-T006.2)
        signed_token = self._generate_signed_token(str(user_id), session_id)

        # Log call started (AC-T006.3)
        await self._log_call_started(user_id, session_id)

        # Build dynamic variables for ElevenLabs
        dynamic_vars = self._build_dynamic_variables(context)

        # Get TTS settings based on chapter/mood
        tts_settings = self._get_tts_settings(context.chapter, context.nikita_mood)

        # GAP-001 Fix: Use cached prompt for <100ms response (like inbound calls)
        # FR-033/FR-034: Avoid blocking Claude API call during call initiation
        prompt_content = user.cached_voice_prompt
        prompt_source = "cached"

        if not prompt_content:
            # First-time caller or cache expired - use static fallback (fast)
            prompt_content = self._generate_fallback_prompt(user)
            prompt_source = "fallback"
            logger.info(
                f"[VOICE] No cached prompt for user {user_id}, using fallback "
                f"({len(prompt_content)} chars)"
            )
        else:
            logger.info(
                f"[VOICE] Using cached prompt for user {user_id} "
                f"({len(prompt_content)} chars)"
            )

        conversation_config_override = {
            "agent": {
                "prompt": {"prompt": prompt_content},
                "first_message": self._get_first_message(context),
            },
            "tts": tts_settings.model_dump() if tts_settings else None,
            "_prompt_source": prompt_source,  # For debugging/monitoring
        }

        # Store session
        self._sessions[session_id] = {
            "user_id": str(user_id),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "context": context.model_dump(),
        }

        result = {
            "agent_id": self.settings.elevenlabs_default_agent_id,
            "signed_token": signed_token,
            "session_id": session_id,
            "context": context.model_dump(),
            "dynamic_variables": dynamic_vars.to_dict(),
            "tts_settings": tts_settings.model_dump() if tts_settings else None,
            "conversation_config_override": conversation_config_override,
        }

        logger.info(
            f"[VOICE] Call initiated in {time.time() - start_time:.2f}s | "
            f"user={user_id}, session={session_id}"
        )

        return result

    async def _load_user(self, user_id: UUID) -> "User | None":
        """Load user from database with all required relationships.
        
        Eagerly loads relationships needed for voice context:
        - metrics: for relationship_score via User model
        - engagement_state: for current engagement state
        - vice_preferences: for vice-based personalization
        """
        from nikita.db.database import get_session_maker
        from nikita.db.models.user import User
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        session_maker = get_session_maker()
        async with session_maker() as session:
            stmt = (
                select(User)
                .options(
                    joinedload(User.metrics),
                    joinedload(User.engagement_state),
                    joinedload(User.vice_preferences),
                )
                .where(User.id == user_id)
            )
            result = await session.execute(stmt)
            return result.unique().scalar_one_or_none()

    async def _load_context(self, user: "User") -> VoiceContext:
        """
        Load voice context for a user.

        Uses MetaPromptService patterns for context loading.
        """
        # Build basic context from user model
        context = VoiceContext(
            user_id=user.id,
            user_name=self._get_user_name(user),
            chapter=user.chapter,
            relationship_score=(
                float(user.relationship_score)
            ),
            engagement_state=(
                user.engagement_state.state.upper()
                if user.engagement_state and hasattr(user.engagement_state, "state")
                else "IN_ZONE"
            ),
            game_status=user.game_status,
        )

        # Load vices if available
        if user.vice_preferences:
            primary = next(
                (v for v in user.vice_preferences if v.is_primary), None
            )
            if primary:
                context.primary_vice = primary.vice_category
                context.vice_severity = primary.severity

        # Compute Nikita state
        context.nikita_mood = self._compute_nikita_mood(user)
        context.nikita_energy = self._compute_nikita_energy()
        context.time_of_day = self._compute_time_of_day()

        # Try to load memory context if available
        try:
            await self._enrich_from_memory(user.id, context)
        except Exception as e:
            logger.warning(f"[VOICE] Memory loading failed: {e}")

        return context

    async def _enrich_from_memory(
        self, user_id: UUID, context: VoiceContext
    ) -> None:
        """Enrich context with memory from Graphiti."""
        if not self.settings.neo4j_uri:
            return

        try:
            from nikita.memory.graphiti_client import get_memory_client

            memory = await get_memory_client(str(user_id))

            # Get recent topics
            search_result = await memory.search("recent conversations", limit=5)
            if search_result:
                context.recent_topics = [r.get("content", "")[:50] for r in search_result[:3]]

            # Get open threads
            thread_result = await memory.search("unresolved topics pending", limit=3)
            if thread_result:
                context.open_threads = [r.get("content", "")[:50] for r in thread_result[:2]]

        except Exception as e:
            logger.warning(f"[VOICE] Memory enrichment failed: {e}")

    def _get_user_name(self, user: "User") -> str:
        """Extract user name from onboarding_profile, user.name, or return default."""
        # First try onboarding_profile (voice onboarding data)
        profile = getattr(user, 'onboarding_profile', None)
        if isinstance(profile, dict) and profile.get("name"):
            return str(profile["name"])
        # Then try user.name attribute (may be set from text onboarding)
        if hasattr(user, 'name') and user.name:
            return str(user.name)
        return "friend"

    def _compute_nikita_mood(self, user: "User") -> NikitaMood:
        """Compute Nikita's mood based on user state."""
        chapter = user.chapter
        score = float(user.relationship_score)

        # Chapter 1: distant
        if chapter == 1:
            return NikitaMood.DISTANT

        # Low score: annoyed
        if score < 30:
            return NikitaMood.ANNOYED

        # Chapter 4-5 with high score: flirty
        if chapter >= 4 and score > 60:
            return NikitaMood.FLIRTY

        # Default: neutral or playful
        if score > 50:
            return NikitaMood.PLAYFUL

        return NikitaMood.NEUTRAL

    def _compute_nikita_energy(self) -> str:
        """Compute Nikita's energy level based on time."""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "high"
        elif 12 <= hour < 18:
            return "medium"
        elif 18 <= hour < 22:
            return "relaxed"
        return "low"

    def _compute_time_of_day(self) -> str:
        """Get current time of day label."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        return "night"

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"voice_{secrets.token_hex(8)}_{int(time.time())}"

    def _generate_signed_token(self, user_id: str, session_id: str) -> str:
        """
        Generate signed token for server tool authentication.

        The token contains user_id and session_id, signed with HMAC.
        Server tools verify this token to authenticate requests.
        """
        # Create payload
        payload = f"{user_id}:{session_id}:{int(time.time())}"

        # Sign with secret key (use webhook secret or generate one)
        secret = self.settings.elevenlabs_webhook_secret or "default_voice_secret"
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return f"{payload}:{signature}"

    async def _log_call_started(self, user_id: UUID, session_id: str) -> None:
        """Log call started event to database."""
        logger.info(f"[VOICE] Call started: user={user_id}, session={session_id}")
        # TODO: Add to voice_calls table or events table when implemented

    def _build_dynamic_variables(self, context: VoiceContext) -> DynamicVariables:
        """Build dynamic variables for ElevenLabs prompt interpolation."""
        return DynamicVariables(
            user_name=context.user_name,
            chapter=context.chapter,
            relationship_score=context.relationship_score,
            engagement_state=context.engagement_state,
            nikita_mood=context.nikita_mood.value,
            nikita_energy=context.nikita_energy,
            time_of_day=context.time_of_day,
            recent_topics=", ".join(context.recent_topics) if context.recent_topics else "",
            open_threads=", ".join(context.open_threads) if context.open_threads else "",
            secret__user_id=str(context.user_id),
        )

    def _get_tts_settings(self, chapter: int, mood: NikitaMood) -> TTSSettings:
        """Get TTS settings based on chapter and mood (FR-016, FR-017)."""
        # Chapter-based defaults
        chapter_settings = {
            1: TTSSettings(stability=0.8, similarity_boost=0.7, speed=0.95),
            2: TTSSettings(stability=0.7, similarity_boost=0.75, speed=0.98),
            3: TTSSettings(stability=0.6, similarity_boost=0.8, speed=1.0),
            4: TTSSettings(stability=0.5, similarity_boost=0.82, speed=1.0),
            5: TTSSettings(stability=0.4, similarity_boost=0.85, speed=1.02),
        }

        # Mood overrides
        mood_settings = {
            NikitaMood.FLIRTY: TTSSettings(stability=0.5, similarity_boost=0.8, speed=1.0),
            NikitaMood.VULNERABLE: TTSSettings(stability=0.7, similarity_boost=0.9, speed=0.9),
            NikitaMood.ANNOYED: TTSSettings(stability=0.4, similarity_boost=0.7, speed=1.1),
            NikitaMood.PLAYFUL: TTSSettings(stability=0.4, similarity_boost=0.8, speed=1.1),
            NikitaMood.DISTANT: TTSSettings(stability=0.8, similarity_boost=0.9, speed=0.95),
            NikitaMood.NEUTRAL: TTSSettings(stability=0.6, similarity_boost=0.8, speed=1.0),
        }

        # Mood takes priority over chapter for emotional authenticity
        return mood_settings.get(mood, chapter_settings.get(chapter, TTSSettings()))

    def _get_first_message(self, context: VoiceContext) -> str:
        """
        Generate personalized first message based on user context.

        The first message varies by chapter, reflecting Nikita's evolving
        relationship with the user from distant (ch1) to intimate (ch5).

        Args:
            context: VoiceContext with user data

        Returns:
            Personalized greeting string
        """
        user_name = context.user_name or "you"

        # Chapter-based greetings with personality progression
        greetings = {
            1: f"Oh... hi {user_name}. What do you want?",
            2: f"Hey {user_name}. What's up?",
            3: f"Well hello there, {user_name}! I was hoping you'd call.",
            4: f"Hey babe! I was just thinking about you, {user_name}.",
            5: f"Mmm, {user_name}... I've been waiting for your call.",
        }

        # Get base greeting
        greeting = greetings.get(context.chapter, f"Hey {user_name}!")

        # Add time-based variations for later chapters
        if context.chapter >= 3:
            time_variations = {
                "morning": " How did you sleep?",
                "afternoon": " How's your day going?",
                "evening": " How was your day?",
                "night": " Couldn't sleep either?",
            }
            greeting += time_variations.get(context.time_of_day, "")

        return greeting

    def _generate_fallback_prompt(self, user: "User") -> str:
        """Generate fallback prompt using static VoiceAgentConfig.

        GAP-001 Fix: Used when cached_voice_prompt is None (first-time caller).
        Post-processing will populate the cache for subsequent calls.
        Mirrors InboundCallHandler._generate_fallback_prompt() pattern.

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

        # Get relationship score from metrics
        relationship_score = 50.0
        if user.metrics:
            relationship_score = float(getattr(user.metrics, "relationship_score", 50.0))

        return config.generate_system_prompt(
            user_id=user.id,
            chapter=user.chapter,
            vices=primary_vices,
            user_name=getattr(user, "name", "friend") or "friend",
            relationship_score=relationship_score,
        )

    async def get_context_with_text_history(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Get context including text conversation history (T048).

        Implements AC-T048.1: Loads text conversation summaries
        Implements AC-T048.3: Includes last 7 days of text conversations

        Args:
            user_id: User ID string

        Returns:
            Dictionary with facts and episodes from both voice and text
        """
        from nikita.memory.graphiti_client import get_memory_client

        try:
            memory = await get_memory_client(user_id)
            context = await memory.get_context_for_prompt("recent conversations")

            return context

        except Exception as e:
            logger.warning(f"[VOICE] Failed to load text history: {e}")
            return {"facts": [], "recent_episodes": []}

    async def search_user_memory(
        self,
        user_id: str,
        query: str,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search user memory across voice and text sources.

        Implements AC-T049.4: Both sources returned when no filter specified

        Args:
            user_id: User ID string
            query: Search query
            source_filter: Optional filter - 'voice_call' or 'user_message'

        Returns:
            List of memory results with source tags
        """
        from nikita.memory.graphiti_client import get_memory_client

        try:
            memory = await get_memory_client(user_id)
            results = await memory.search_memory(query, limit=10)

            # Filter by source if specified
            if source_filter and results:
                results = [r for r in results if r.get("source") == source_filter]

            return results

        except Exception as e:
            logger.warning(f"[VOICE] Memory search failed: {e}")
            return []

    async def format_text_history_for_voice(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Format text history for voice agent consumption (T048).

        Implements AC-T048.2: Formats text history for voice agent

        Args:
            user_id: User ID string

        Returns:
            Formatted dictionary with summary and context
        """
        context = await self.get_context_with_text_history(user_id)

        # Filter for text-only context
        text_facts = [
            f for f in context.get("facts", [])
            if f.get("source") == "user_message"
        ]

        text_episodes = [
            e for e in context.get("recent_episodes", [])
            if e.get("source") == "user_message"
        ]

        # Build summary for voice agent
        summary_parts = []
        if text_facts:
            facts_text = "; ".join(f.get("content", "") for f in text_facts[:5])
            summary_parts.append(f"Known facts: {facts_text}")

        if text_episodes:
            episodes_text = "; ".join(e.get("content", "") for e in text_episodes[:3])
            summary_parts.append(f"Recent topics: {episodes_text}")

        return {
            "summary": ". ".join(summary_parts) if summary_parts else "No recent text conversations",
            "context": {
                "facts": text_facts,
                "episodes": text_episodes,
            },
            "source": "text_history",
        }

    def get_session(self, session_id: str) -> dict | None:
        """Get session data by ID."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> None:
        """End and remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"[VOICE] Session ended: {session_id}")

    async def make_outbound_call(
        self,
        to_number: str,
        user_id: UUID | None = None,
        conversation_config_override: dict[str, Any] | None = None,
        dynamic_variables: dict[str, Any] | None = None,
        is_onboarding: bool = False,
    ) -> dict[str, Any]:
        """
        Make an outbound voice call via ElevenLabs/Twilio.

        This method supports the unified phone number architecture (Spec 033):
        - For onboarding calls: Pass Meta-Nikita config override
        - For regular Nikita calls: No override (uses default agent persona)

        Args:
            to_number: Phone number to call (E.164 format, e.g., +14155552671)
            user_id: User UUID for context loading (optional)
            conversation_config_override: Override for agent persona (prompt, TTS, first_message)
            dynamic_variables: Variables for prompt interpolation
            is_onboarding: Whether this is an onboarding call (for logging)

        Returns:
            Dictionary with:
            - success: bool
            - conversation_id: ElevenLabs conversation ID
            - call_sid: Twilio call SID
            - message: Status message

        Raises:
            ValueError: If required settings are missing
            httpx.HTTPError: If ElevenLabs API call fails

        Example:
            ```python
            # Onboarding call with Meta-Nikita override
            from nikita.onboarding import build_meta_nikita_config_override
            override = build_meta_nikita_config_override(user_id, "Alice")
            result = await service.make_outbound_call(
                to_number="+14155552671",
                user_id=user_id,
                conversation_config_override=override["conversation_config_override"],
                dynamic_variables=override["dynamic_variables"],
                is_onboarding=True,
            )

            # Regular Nikita call (no override)
            result = await service.make_outbound_call(
                to_number="+14155552671",
                user_id=user_id,
            )
            ```
        """
        import httpx

        start_time = time.time()
        logger.info(
            f"[VOICE] Making outbound call: to={to_number}, "
            f"is_onboarding={is_onboarding}, has_override={conversation_config_override is not None}"
        )

        # Validate required settings
        if not self.settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY not configured")
        if not self.settings.elevenlabs_default_agent_id:
            raise ValueError("ELEVENLABS_DEFAULT_AGENT_ID not configured")

        # Get phone number ID - this is the ElevenLabs phone number resource ID
        # For now, we'll pass it via settings or derive from twilio_phone_number
        agent_phone_number_id = getattr(
            self.settings, "elevenlabs_phone_number_id", None
        )
        if not agent_phone_number_id:
            # Fallback: Use the Twilio phone number directly if ElevenLabs accepts it
            # (This may need to be configured in ElevenLabs dashboard first)
            raise ValueError(
                "ELEVENLABS_PHONE_NUMBER_ID not configured. "
                "Configure the phone number in ElevenLabs dashboard and set this env var."
            )

        # Build request payload
        payload: dict[str, Any] = {
            "agent_id": self.settings.elevenlabs_default_agent_id,
            "agent_phone_number_id": agent_phone_number_id,
            "to_number": to_number,
        }

        # Add conversation initiation data if provided
        if conversation_config_override or dynamic_variables:
            initiation_data: dict[str, Any] = {}

            if conversation_config_override:
                initiation_data["conversation_config_override"] = conversation_config_override

            if dynamic_variables:
                # Add user_id to dynamic variables for server tool auth
                dv = dict(dynamic_variables)
                if user_id:
                    dv["secret__user_id"] = str(user_id)
                initiation_data["dynamic_variables"] = dv

            if user_id:
                initiation_data["user_id"] = str(user_id)

            payload["conversation_initiation_client_data"] = initiation_data

        # Make the API call
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
                json=payload,
                headers={
                    "xi-api-key": self.settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    f"[VOICE] Outbound call failed: status={response.status_code}, "
                    f"error={error_text}"
                )
                return {
                    "success": False,
                    "message": f"ElevenLabs API error: {response.status_code}",
                    "error": error_text,
                }

            result = response.json()

        logger.info(
            f"[VOICE] Outbound call initiated in {time.time() - start_time:.2f}s | "
            f"to={to_number}, conversation_id={result.get('conversation_id')}, "
            f"call_sid={result.get('callSid')}"
        )

        return {
            "success": result.get("success", False),
            "conversation_id": result.get("conversation_id"),
            "call_sid": result.get("callSid"),
            "message": result.get("message", "Call initiated"),
        }

    async def end_call(
        self,
        user_id: UUID,
        session_id: str,
        transcript: list[tuple[str, str]] | None = None,
        duration_seconds: int = 0,
    ) -> dict[str, Any]:
        """
        End a voice call and score the conversation.

        Implements T022 acceptance criteria:
        - AC-T022.1: End call fetches/accepts transcript
        - AC-T022.2: Calls VoiceCallScorer.score_call()
        - AC-T022.3: Applies score and returns CallResult
        - AC-T022.4: Updates last_interaction_at

        Args:
            user_id: UUID of the user
            session_id: Voice session ID
            transcript: List of (user_message, nikita_response) tuples
            duration_seconds: Call duration in seconds

        Returns:
            CallResult with scoring summary
        """
        from decimal import Decimal

        from nikita.agents.voice.scoring import VoiceCallScorer
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.user_repository import UserRepository
        from nikita.engine.scoring.models import ConversationContext

        start_time = time.time()
        logger.info(f"[VOICE] Ending call: user={user_id}, session={session_id}")

        # If no transcript provided, try to fetch from ElevenLabs
        # (For now, we accept transcript as parameter - webhook provides it)
        if transcript is None:
            transcript = []

        # Load user for context
        user = await self._load_user(user_id)
        if user is None:
            return {
                "success": False,
                "error": "User not found",
                "session_id": session_id,
            }

        # Build scoring context
        context = ConversationContext(
            chapter=user.chapter,
            relationship_score=Decimal(str(
                float(user.relationship_score)
            )),
            relationship_state=(
                user.engagement_state.state.upper()
                if user.engagement_state and hasattr(user.engagement_state, "state")
                else "IN_ZONE"
            ),
            recent_messages=[],  # Voice doesn't have prior context here
        )

        # Score the call (AC-T022.2)
        scorer = VoiceCallScorer()
        call_score = await scorer.score_call(
            user_id=user_id,
            session_id=session_id,
            transcript=transcript,
            context=context,
            duration_seconds=duration_seconds,
        )

        # Apply score (AC-T022.3)
        new_score = await scorer.apply_score(user_id, call_score)

        # Update last_interaction_at (AC-T022.4)
        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = UserRepository(session)
            await repo.update_last_interaction(user_id)
            await session.commit()

        # Clean up session
        self.end_session(session_id)

        result = {
            "success": True,
            "session_id": session_id,
            "duration_seconds": duration_seconds,
            "exchanges_count": len(transcript),
            "score_change": {
                "intimacy": str(call_score.deltas.intimacy),
                "passion": str(call_score.deltas.passion),
                "trust": str(call_score.deltas.trust),
                "secureness": str(call_score.deltas.secureness),
            },
            "new_relationship_score": str(new_score),
            "explanation": call_score.explanation,
        }

        logger.info(
            f"[VOICE] Call ended in {time.time() - start_time:.2f}s | "
            f"session={session_id}, score_change={new_score}"
        )

        return result


# Singleton instance
_voice_service: VoiceService | None = None


@lru_cache
def get_voice_service() -> VoiceService:
    """Get voice service singleton."""
    global _voice_service
    if _voice_service is None:
        from nikita.config.settings import get_settings
        _voice_service = VoiceService(settings=get_settings())
    return _voice_service
