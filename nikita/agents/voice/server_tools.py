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
from datetime import date, timedelta
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

        Enhanced implementation (T016 + Phase 1 Context Enhancement):
        - AC-T016.1: Returns VoiceContext with all user data
        - AC-T016.2: Loads chapter, score, vices from database
        - AC-T016.3: Loads recent memory from Graphiti (optional)
        - AC-T016.4: Formats for LLM consumption

        Phase 1 Enhancements (2026-01-11):
        - active_thoughts: Nikita's simulated inner thoughts by type
        - today_summary: What happened today in Nikita's words
        - week_summaries: Last 7 days of narrative context
        - backstory: How Nikita and user met (venue, scenario, hooks)

        Args:
            user_id: User UUID string
            session_id: Voice session ID
            data: Additional request data (include_behavior, include_persona)

        Returns:
            Context dictionary for LLM consumption with:
            - user_name, chapter, game_status, engagement_state
            - relationship_score, intimacy, passion, trust (metrics)
            - primary_vice, vice_severity, all_vices
            - active_thoughts, today_summary, week_summaries, backstory
            - nikita_mood
            - voice_persona (optional), chapter_behavior (optional)
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
                "engagement_state": (
                    user.engagement_state.state.upper()
                    if user.engagement_state and hasattr(user.engagement_state, "state")
                    else "IN_ZONE"
                ),
            }

            # Add metrics if available (AC-T016.2)
            # Spec 029: Voice-text parity - include all 4 metrics
            if user.metrics:
                context["relationship_score"] = float(user.metrics.relationship_score)
                context["intimacy"] = float(user.metrics.intimacy)
                context["passion"] = float(user.metrics.passion)
                context["trust"] = float(user.metrics.trust)
                context["secureness"] = float(user.metrics.secureness)  # Added for parity

            # Spec 029: Voice-text parity - add hours_since_last
            from datetime import datetime

            now = datetime.utcnow()
            if user.last_interaction_at:
                delta = now - user.last_interaction_at
                context["hours_since_last"] = round(delta.total_seconds() / 3600, 1)
            else:
                context["hours_since_last"] = 0.0

            # Spec 029: Voice-text parity - add temporal context
            hour = now.hour
            if 5 <= hour < 12:
                context["time_of_day"] = "morning"
            elif 12 <= hour < 17:
                context["time_of_day"] = "afternoon"
            elif 17 <= hour < 21:
                context["time_of_day"] = "evening"
            elif 21 <= hour < 24:
                context["time_of_day"] = "night"
            else:
                context["time_of_day"] = "late_night"

            # Spec 029: Voice-text parity - add nikita_activity
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            context["day_of_week"] = day_names[now.weekday()]
            context["nikita_activity"] = self._compute_nikita_activity(
                context["time_of_day"], context["day_of_week"]
            )
            context["nikita_energy"] = self._compute_nikita_energy(context["time_of_day"])

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

            # Spec 029: Voice-text parity - load user_facts, relationship_episodes, nikita_events from Graphiti
            try:
                from nikita.memory.graphiti_client import get_memory_client

                memory = await get_memory_client(user_id)

                async def _query_graph(graph_type: str, limit: int = 50) -> list[str]:
                    """Query a specific graph type and extract fact strings."""
                    try:
                        results = await memory.search_memory(
                            query="relevant context about user and relationship",
                            graph_types=[graph_type],
                            limit=limit,
                        )
                        return [r.get("fact", str(r)) for r in results if r]
                    except Exception as e:
                        logger.warning(f"[SERVER TOOL] Failed to query {graph_type} graph: {e}")
                        return []

                # Query all 3 graphs concurrently (standard tier limits)
                user_facts, relationship_episodes, nikita_events = await asyncio.gather(
                    _query_graph("user", limit=50),
                    _query_graph("relationship", limit=30),
                    _query_graph("nikita", limit=20),
                )

                context["user_facts"] = user_facts
                context["relationship_episodes"] = relationship_episodes
                context["nikita_events"] = nikita_events

                logger.debug(
                    f"[SERVER TOOL] Loaded {len(user_facts)} user_facts, "
                    f"{len(relationship_episodes)} relationship_episodes, "
                    f"{len(nikita_events)} nikita_events for {user_id}"
                )
            except Exception as e:
                logger.warning(f"[SERVER TOOL] Failed to load Graphiti memories: {e}")
                context["user_facts"] = []
                context["relationship_episodes"] = []
                context["nikita_events"] = []

            # Load open threads for voice-text parity
            try:
                from nikita.db.repositories.thread_repository import ConversationThreadRepository

                thread_repo = ConversationThreadRepository(session)
                threads_by_type = await thread_repo.get_threads_for_prompt(UUID(user_id), max_per_type=10)
                context["open_threads"] = {
                    thread_type: [{"content": t.content} for t in threads]
                    for thread_type, threads in threads_by_type.items()
                }
            except Exception as e:
                logger.warning(f"[SERVER TOOL] Failed to load threads: {e}")
                context["open_threads"] = {}

            # Load active thoughts (Phase 1 Enhancement)
            try:
                from nikita.db.repositories.thought_repository import NikitaThoughtRepository

                thought_repo = NikitaThoughtRepository(session)
                thoughts = await thought_repo.get_thoughts_for_prompt(UUID(user_id), max_per_type=10)
                context["active_thoughts"] = {
                    t_type: [{"content": t.content} for t in t_list]
                    for t_type, t_list in thoughts.items()
                }
            except Exception as e:
                logger.warning(f"[SERVER TOOL] Failed to load thoughts: {e}")
                context["active_thoughts"] = {}

            # Load today's summary and week summaries (Phase 1 Enhancement)
            try:
                from nikita.db.repositories.summary_repository import DailySummaryRepository

                summary_repo = DailySummaryRepository(session)
                today = date.today()

                # Today's summary
                today_summary = await summary_repo.get_by_date(UUID(user_id), today)
                context["today_summary"] = (
                    today_summary.nikita_summary_text if today_summary else None
                )

                # Week summaries (last 7 days)
                week_start = today - timedelta(days=7)
                week_summaries = await summary_repo.get_range(
                    UUID(user_id), week_start, today
                )
                context["week_summaries"] = {
                    str(s.date): s.nikita_summary_text
                    for s in week_summaries
                    if s.nikita_summary_text
                }
            except Exception as e:
                logger.warning(f"[SERVER TOOL] Failed to load summaries: {e}")
                context["today_summary"] = None
                context["week_summaries"] = {}

            # Load backstory if exists (Phase 1 Enhancement)
            try:
                from nikita.db.repositories.profile_repository import BackstoryRepository

                backstory_repo = BackstoryRepository(session)
                backstory = await backstory_repo.get_by_user_id(UUID(user_id))
                if backstory:
                    context["backstory"] = {
                        "venue_name": backstory.venue_name,
                        "venue_city": backstory.venue_city,
                        "scenario_type": backstory.scenario_type,
                        "how_we_met": backstory.how_we_met,
                        "the_moment": backstory.the_moment,
                        "unresolved_hook": backstory.unresolved_hook,
                    }
                else:
                    context["backstory"] = None
            except Exception as e:
                logger.warning(f"[SERVER TOOL] Failed to load backstory: {e}")
                context["backstory"] = None

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

    def _compute_nikita_activity(self, time_of_day: str, day_of_week: str) -> str:
        """Compute what Nikita is likely doing based on time.

        Spec 029: Voice-text parity - matches meta_prompts/service.py implementation.

        Args:
            time_of_day: Time of day (morning, afternoon, evening, night, late_night)
            day_of_week: Day name (Monday, Tuesday, etc.)

        Returns:
            Activity description string
        """
        weekend = day_of_week in ("Saturday", "Sunday")

        activities = {
            ("morning", False): "just finished her morning coffee, checking emails",
            ("morning", True): "sleeping in after a late night",
            ("afternoon", False): "deep in a security audit, headphones on",
            ("afternoon", True): "at the gym, checking her phone between sets",
            ("evening", False): "wrapping up work, cat on her lap",
            ("evening", True): "getting ready to go out with friends",
            ("night", False): "on the couch with wine, watching trash TV",
            ("night", True): "at a bar with friends, slightly buzzed",
            ("late_night", False): "in bed scrolling, can't sleep",
            ("late_night", True): "stumbling home from a night out",
        }

        return activities.get((time_of_day, weekend), "doing her thing")

    def _compute_nikita_energy(self, time_of_day: str) -> str:
        """Compute energy level based on time of day.

        Spec 029: Voice-text parity - matches meta_prompts/service.py implementation.

        Args:
            time_of_day: Time of day (morning, afternoon, evening, night, late_night)

        Returns:
            Energy level (low, moderate, high)
        """
        energy_map = {
            "morning": "moderate",
            "afternoon": "high",
            "evening": "moderate",
            "night": "low",
            "late_night": "low",
        }
        return energy_map.get(time_of_day, "moderate")

    async def _get_memory(
        self, user_id: str, session_id: str, data: dict
    ) -> dict[str, Any]:
        """
        Query user memory from Graphiti and load open threads.

        Args:
            user_id: User UUID string
            session_id: Voice session ID
            data: Request data with 'query' field

        Returns:
            Memory search results with facts and threads
        """
        query = data.get("query", "recent conversations")
        limit = data.get("limit", 5)

        facts: list[str] = []
        threads: list[dict[str, str]] = []
        errors: list[str] = []

        # Load facts from Graphiti
        try:
            from nikita.memory.graphiti_client import get_memory_client

            memory = await get_memory_client(user_id)
            results = await memory.search(query, limit=limit)
            facts = [r.get("content", "") for r in results[:3]] if results else []
        except Exception as e:
            logger.warning(f"[SERVER TOOL] Memory query failed: {e}")
            errors.append(f"Memory: {e}")

        # Load open threads from database
        try:
            from nikita.db.database import get_session_maker
            from nikita.db.repositories.thread_repository import ConversationThreadRepository

            session_maker = get_session_maker()
            async with session_maker() as session:
                thread_repo = ConversationThreadRepository(session)
                open_threads = await thread_repo.get_open_threads(
                    UUID(user_id), limit=5
                )
                threads = [
                    {"type": t.thread_type, "content": t.content}
                    for t in open_threads
                ]
        except Exception as e:
            logger.warning(f"[SERVER TOOL] Thread loading failed: {e}")
            errors.append(f"Threads: {e}")

        result: dict[str, Any] = {"facts": facts, "threads": threads}
        if errors:
            result["error"] = "; ".join(errors)
        return result

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
            from nikita.engine.scoring.analyzer import ScoreAnalyzer
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
            analyzer = ScoreAnalyzer()
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
