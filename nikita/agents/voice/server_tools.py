"""Server tool handler for ElevenLabs Conversational AI.

This module implements the ServerToolHandler which processes
tool calls from ElevenLabs during voice conversations.

Server Tools (called by ElevenLabs agent):
- get_context: Load user context (chapter, vices, engagement)
- get_memory: Query Graphiti memory system
- score_turn: Analyze conversation exchange for scoring
- update_memory: Store new facts to Graphiti

Implements T012 acceptance criteria:
- AC-T012.1: handle(request) routes to appropriate tool handler
- AC-T012.2: Validates signed token for user_id
- AC-T012.3: Returns structured response for ElevenLabs
"""

import asyncio
import hashlib
import hmac
import logging
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

from nikita.agents.voice.models import (
    ServerToolName,
    ServerToolRequest,
    ServerToolResponse,
)


def with_timeout_fallback(
    timeout_seconds: float = 2.0,
    fallback_data: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator for server tool methods with timeout fallback (T072).

    Implements:
    - AC-T072.1: Decorator with configurable timeout
    - AC-T072.2: Returns fallback response on timeout
    - AC-T072.3: Logs all timeouts
    - AC-T072.4: Fallback includes cache_friendly=True

    Args:
        timeout_seconds: Maximum time to wait for response
        fallback_data: Default data to return on timeout

    Returns:
        Decorated function that handles timeouts gracefully
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> dict[str, Any]:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                # AC-T072.3: Log timeout
                logger.warning(
                    f"[SERVER TOOL] Timeout ({timeout_seconds}s) in {func.__name__}"
                )
                # AC-T072.2 & AC-T072.4: Return fallback with cache hint
                return {
                    **(fallback_data or {}),
                    "timeout": True,
                    "cache_friendly": True,
                    "error": f"Operation timed out after {timeout_seconds}s",
                }
        return wrapper
    return decorator

if TYPE_CHECKING:
    from nikita.config.settings import Settings

logger = logging.getLogger(__name__)

# Token validity window (5 minutes)
TOKEN_VALIDITY_SECONDS = 300


class ServerToolHandler:
    """Handler for ElevenLabs server tool calls.

    Routes incoming tool requests to the appropriate handler,
    validates authentication, and returns structured responses.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize ServerToolHandler.

        Args:
            settings: Application settings with secrets
        """
        self.settings = settings

    async def handle(self, request: ServerToolRequest) -> ServerToolResponse:
        """
        Handle a server tool request from ElevenLabs.

        AC-T012.1: Routes to appropriate tool handler
        AC-T012.2: Validates signed token (done by API endpoint before calling this)
        AC-T012.3: Returns structured response

        Args:
            request: Server tool request with tool_name, user_id, session_id, data

        Returns:
            ServerToolResponse with success status and data
        """
        logger.info(f"[SERVER TOOL] Handling {request.tool_name} request")

        # User ID and session ID are already validated by API endpoint
        user_id = request.user_id
        session_id = request.session_id

        # Route to appropriate handler (AC-T012.1)
        try:
            if request.tool_name == ServerToolName.GET_CONTEXT:
                data = await self._get_context(user_id, session_id, request.data)
            elif request.tool_name == ServerToolName.GET_MEMORY:
                data = await self._get_memory(user_id, session_id, request.data)
            elif request.tool_name == ServerToolName.SCORE_TURN:
                data = await self._score_turn(user_id, session_id, request.data)
            elif request.tool_name == ServerToolName.UPDATE_MEMORY:
                data = await self._update_memory(user_id, session_id, request.data)
            else:
                return ServerToolResponse(
                    success=False,
                    tool_name=None,  # Unknown tools don't have valid enum
                    error=f"Unknown tool: {request.tool_name}",
                    data={},
                )

            # Return structured response (AC-T012.3)
            return ServerToolResponse(
                success=True,
                tool_name=request.tool_name,
                data=data,
            )

        except Exception as e:
            logger.error(f"[SERVER TOOL] Handler error: {e}", exc_info=True)
            return ServerToolResponse(
                success=False,
                tool_name=request.tool_name,
                error=f"Tool execution failed: {type(e).__name__}",
                data={},
            )

    def _validate_token(self, token: str) -> tuple[str, str]:
        """
        Validate signed token and extract user_id and session_id.

        Token format: {user_id}:{session_id}:{timestamp}:{signature}

        Args:
            token: Signed token string

        Returns:
            Tuple of (user_id, session_id)

        Raises:
            ValueError: If token is invalid or expired
        """
        parts = token.split(":")
        if len(parts) != 4:
            raise ValueError("Invalid token format")

        user_id, session_id, timestamp_str, signature = parts

        # Validate timestamp
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            raise ValueError("Invalid timestamp in token")

        # Check if token is expired
        current_time = int(time.time())
        if current_time - timestamp > TOKEN_VALIDITY_SECONDS:
            raise ValueError("Token expired")

        # Verify signature
        secret = self.settings.elevenlabs_webhook_secret or "default_voice_secret"
        payload = f"{user_id}:{session_id}:{timestamp_str}"
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid signature")

        return user_id, session_id

    async def _get_context(
        self, user_id: str, session_id: str, data: dict
    ) -> dict[str, Any]:
        """
        Get user context for voice conversation.

        Enhanced implementation (T016) - loads comprehensive personality data:
        - AC-T016.1: Returns VoiceContext with all user data
        - AC-T016.2: Loads chapter, score, vices from database
        - AC-T016.3: Loads recent memory from Graphiti (optional)
        - AC-T016.4: Formats for LLM consumption

        Args:
            user_id: User UUID string
            session_id: Voice session ID
            data: Additional request data (include_behavior, include_persona)

        Returns:
            Context dictionary for LLM consumption
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.user_repository import UserRepository

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = UserRepository(session)
            user = await repo.get(UUID(user_id))

            if user is None:
                return {"error": "User not found"}

            # Build base context (AC-T016.1)
            context: dict[str, Any] = {
                "user_name": user.name or "friend",
                "chapter": user.chapter,
                "game_status": user.game_status,
                "engagement_state": user.engagement_state or "IN_ZONE",
            }

            # Add metrics if available (AC-T016.2)
            if user.metrics:
                context["relationship_score"] = float(user.metrics.relationship_score)
                context["intimacy"] = float(user.metrics.intimacy)
                context["passion"] = float(user.metrics.passion)
                context["trust"] = float(user.metrics.trust)

            # Add ALL vices with severity (T016 enhancement)
            if user.vice_preferences:
                # Primary vice for quick access
                primary = next(
                    (v for v in user.vice_preferences if v.is_primary), None
                )
                if primary:
                    context["primary_vice"] = primary.vice_category
                    context["vice_severity"] = primary.severity

                # All vices for comprehensive personality matching
                context["all_vices"] = [
                    {
                        "category": v.vice_category,
                        "severity": v.severity,
                        "is_primary": v.is_primary,
                    }
                    for v in user.vice_preferences
                ]

            # Compute Nikita's mood based on context (for voice persona)
            nikita_mood = self._compute_nikita_mood(
                chapter=user.chapter,
                engagement_state=context.get("engagement_state", "IN_ZONE"),
                relationship_score=context.get("relationship_score", 50.0),
            )
            context["nikita_mood"] = nikita_mood

            # Add voice persona additions if requested (AC-T016.4)
            include_persona = data.get("include_persona", False) if data else False
            if include_persona:
                try:
                    from nikita.prompts.voice_persona import get_voice_persona_additions

                    context["voice_persona"] = get_voice_persona_additions(
                        chapter=user.chapter,
                        mood=nikita_mood,
                    )
                except ImportError:
                    logger.warning("[SERVER TOOL] Voice persona module not available")

            # Add chapter behavior if requested
            include_behavior = data.get("include_behavior", False) if data else False
            if include_behavior:
                try:
                    from nikita.engine.constants import CHAPTER_BEHAVIORS

                    context["chapter_behavior"] = CHAPTER_BEHAVIORS.get(
                        user.chapter, ""
                    )
                except ImportError:
                    logger.warning("[SERVER TOOL] Chapter behaviors not available")

            return context

    def _compute_nikita_mood(
        self, chapter: int, engagement_state: str, relationship_score: float
    ) -> str:
        """Compute Nikita's mood based on context.

        Args:
            chapter: User's current chapter
            engagement_state: Current engagement state
            relationship_score: Current relationship score

        Returns:
            Mood string (flirty, vulnerable, annoyed, playful, distant, neutral)
        """
        # Early chapters tend toward distant/guarded
        if chapter == 1:
            return "distant"
        elif chapter == 2:
            return "neutral" if relationship_score > 55 else "distant"

        # Engagement state influences mood
        if engagement_state in ("CLINGY", "OBSESSED"):
            return "annoyed"
        elif engagement_state in ("DISTANT", "GHOSTING"):
            return "distant"
        elif engagement_state == "RECOVERING":
            return "neutral"

        # Later chapters with good score tend toward intimacy
        if chapter >= 4 and relationship_score > 70:
            return "vulnerable"
        elif chapter >= 3 and relationship_score > 60:
            return "flirty"
        elif relationship_score > 50:
            return "playful"

        return "neutral"

    async def _get_memory(
        self, user_id: str, session_id: str, data: dict
    ) -> dict[str, Any]:
        """
        Query user memory from Graphiti.

        Args:
            user_id: User UUID string
            session_id: Voice session ID
            data: Request data with 'query' field

        Returns:
            Memory search results
        """
        query = data.get("query", "recent conversations")
        limit = data.get("limit", 5)

        try:
            from nikita.memory.graphiti_client import get_memory_client

            memory = await get_memory_client(user_id)
            results = await memory.search(query, limit=limit)

            return {
                "facts": [r.get("content", "") for r in results[:3]] if results else [],
                "threads": [],  # TODO: Load open threads
            }
        except Exception as e:
            logger.warning(f"[SERVER TOOL] Memory query failed: {e}")
            return {"facts": [], "threads": [], "error": str(e)}

    async def _score_turn(
        self, user_id: str, session_id: str, data: dict
    ) -> dict[str, Any]:
        """
        Score a conversation turn.

        Analyzes user message and Nikita response for scoring.

        Args:
            user_id: User UUID string
            session_id: Voice session ID
            data: Request data with 'user_message' and 'nikita_response'

        Returns:
            Scoring deltas
        """
        user_message = data.get("user_message", "")
        nikita_response = data.get("nikita_response", "")

        if not user_message:
            return {"error": "No user_message provided"}

        try:
            from nikita.engine.scoring.analyzer import ResponseAnalyzer
            from nikita.db.database import get_session_maker
            from nikita.db.repositories.user_repository import UserRepository

            # Load user for context
            session_maker = get_session_maker()
            async with session_maker() as session:
                repo = UserRepository(session)
                user = await repo.get(UUID(user_id))

            if user is None:
                return {"error": "User not found"}

            # Analyze the exchange
            analyzer = ResponseAnalyzer()
            analysis = await analyzer.analyze(
                user_message=user_message,
                nikita_response=nikita_response,
                chapter=user.chapter,
            )

            # Return deltas
            return {
                "intimacy_delta": analysis.get("intimacy_delta", 0),
                "passion_delta": analysis.get("passion_delta", 0),
                "trust_delta": analysis.get("trust_delta", 0),
                "secureness_delta": analysis.get("secureness_delta", 0),
                "analysis_summary": analysis.get("summary", ""),
            }

        except Exception as e:
            logger.error(f"[SERVER TOOL] Scoring failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def _update_memory(
        self, user_id: str, session_id: str, data: dict
    ) -> dict[str, Any]:
        """
        Store new fact to Graphiti memory.

        Args:
            user_id: User UUID string
            session_id: Voice session ID
            data: Request data with 'fact' and optionally 'category'

        Returns:
            Storage confirmation
        """
        fact = data.get("fact", "")
        category = data.get("category", "general")

        if not fact:
            return {"error": "No fact provided"}

        try:
            from nikita.memory.graphiti_client import get_memory_client

            memory = await get_memory_client(user_id)
            await memory.add_user_fact(fact, category=category)

            return {"stored": True, "fact": fact, "category": category}

        except Exception as e:
            logger.warning(f"[SERVER TOOL] Memory update failed: {e}")
            return {"stored": False, "error": str(e)}


# Singleton instance
_handler: ServerToolHandler | None = None


def get_server_tool_handler() -> ServerToolHandler:
    """Get server tool handler singleton."""
    global _handler
    if _handler is None:
        from nikita.config.settings import get_settings
        _handler = ServerToolHandler(settings=get_settings())
    return _handler
