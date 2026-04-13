"""Message handler for Nikita text agent.

This module provides the main entry point for handling user messages.
It orchestrates:
1. Agent response generation
2. Text pattern processing (Spec 026 - Remediation Plan T3.2)
3. Response timing calculation (Spec 210 v2: log-normal × chapter × momentum)
4. Pending response storage for delayed delivery

Spec 030: Message history injection for conversation continuity.
The handler accepts optional conversation_messages and conversation_id
which are passed through to generate_response() for message_history.

Spec 026 / Remediation Plan T3.2: Text behavioral patterns.
Raw LLM responses are processed through TextPatternProcessor to apply:
- Emoji insertion based on context
- Punctuation quirks
- Length adjustments
- Natural texting patterns

Spec 210 v2: Skip-decision has been removed (no random drops). Response
delay is now driven by new-conversation gate + chapter coefficients +
momentum (EWMA of user-turn inter-message gaps). Ongoing conversations
return 0 delay.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.text.conversation_rhythm import (
    SESSION_BREAK_SECONDS,
    compute_momentum,
    compute_user_gaps,
)
from nikita.agents.text.facts import ExtractedFact, FactExtractor
from nikita.agents.text.timing import ResponseTimer
from nikita.config.settings import get_settings


# Lazy imports to avoid circular dependencies and pydantic_ai import during testing
def _get_nikita_agent_for_user():
    """Lazy import to avoid triggering pydantic_ai import at module load."""
    from nikita.agents.text import get_nikita_agent_for_user
    return get_nikita_agent_for_user


def _generate_response():
    """Lazy import to avoid triggering pydantic_ai import at module load."""
    from nikita.agents.text.agent import generate_response
    return generate_response


def _get_text_pattern_processor():
    """Lazy import for TextPatternProcessor (Remediation Plan T3.2)."""
    from nikita.text_patterns.processor import TextPatternProcessor
    return TextPatternProcessor


# Singleton processor instance (initialized on first use)
_text_processor_instance = None


def _get_processor_instance():
    """Get or create singleton TextPatternProcessor instance."""
    global _text_processor_instance
    if _text_processor_instance is None:
        TextPatternProcessor = _get_text_pattern_processor()
        _text_processor_instance = TextPatternProcessor()
    return _text_processor_instance


# Re-export for patching in tests
async def get_nikita_agent_for_user(user_id: UUID):
    """Wrapper for lazy import."""
    fn = _get_nikita_agent_for_user()
    return await fn(user_id)


async def generate_response(deps, message: str):
    """Wrapper for lazy import."""
    fn = _generate_response()
    return await fn(deps, message)

logger = logging.getLogger(__name__)


@dataclass
class ResponseDecision:
    """
    Result of processing a user message.

    Contains the generated response, calculated delay,
    and scheduling information for delivery.

    Attributes:
        response: The generated response text from Nikita
        delay_seconds: How long to wait before delivering (in seconds)
        scheduled_at: The datetime when the response should be delivered
        response_id: Unique identifier for tracking this pending response
        should_respond: Always True (skip-decision removed in Spec 210 v2)
        skip_reason: Always None (skip-decision removed in Spec 210 v2)
        facts_extracted: List of facts extracted from this conversation turn
    """

    response: str
    delay_seconds: int
    scheduled_at: datetime
    response_id: UUID = field(default_factory=uuid4)
    should_respond: bool = True
    skip_reason: Optional[str] = None
    facts_extracted: list[ExtractedFact] = field(default_factory=list)


async def store_pending_response(
    user_id: UUID,
    response: str,
    scheduled_at: datetime,
    response_id: UUID,
    chat_id: int,
    session: "AsyncSession | None" = None,
) -> None:
    """
    Store a pending response in scheduled_events for later delivery.

    Writes a MESSAGE_DELIVERY event to the scheduled_events table so that
    the pg_cron delivery task can pick it up and send the message at the
    right time. If no session is provided, the write is skipped and a
    warning is logged (tests typically omit the session).

    Args:
        user_id: The user this response is for
        response: The response text to deliver
        scheduled_at: When to deliver the response
        response_id: Unique identifier for this response (used as idempotency key)
        chat_id: Telegram chat id for delivery. Must match the schema
            expected by the /tasks/deliver worker
            (`nikita/api/routes/tasks.py`). GH #248 — missing chat_id
            caused every scheduled response to fail silently.
        session: Optional async database session. Required for actual DB write.
    """
    if session is None:
        logger.debug(
            "[HANDLER] store_pending_response called without session — skipping DB write"
        )
        return

    from nikita.db.repositories.scheduled_event_repository import ScheduledEventRepository
    from nikita.db.models.scheduled_event import EventPlatform, EventType

    repo = ScheduledEventRepository(session)
    await repo.create_event(
        user_id=user_id,
        platform=EventPlatform.TELEGRAM,
        event_type=EventType.MESSAGE_DELIVERY,
        content={
            "chat_id": chat_id,
            "text": response,
            "response_id": str(response_id),
        },
        scheduled_at=scheduled_at,
    )
    logger.info(
        f"[HANDLER] Stored pending response in scheduled_events: "
        f"user_id={user_id}, scheduled_at={scheduled_at}, response_id={response_id}"
    )


def _is_new_conversation_from_messages(
    conversation_messages: list[dict[str, Any]] | None,
    _now: datetime | None = None,  # vestigial; kept for call-site compat
    session_break_seconds: int = SESSION_BREAK_SECONDS,
) -> bool:
    """Decide whether the current turn starts a new conversation.

    A turn is a "new conversation" if at least ``session_break_seconds``
    seconds have elapsed between the two most recent user messages
    (default 15 min, matching ``TEXT_SESSION_TIMEOUT_MINUTES``).

    ``conversation_messages`` typically includes the CURRENT user message
    (appended by ``message_handler.py`` before calling ``handler.handle``).
    We compare the last two user-message timestamps rather than comparing
    the latest to ``now`` — using ``now`` would always yield a gap of ~0
    and the delay would never fire.

    Args:
        conversation_messages: Optional list of message dicts with
            ``role`` and ``timestamp`` fields. Only ``role=="user"`` entries
            are considered. Expected to include the current message.
        _now: Unused; kept for call-site back-compat.
        session_break_seconds: Gap threshold in seconds (default from
            :data:`conversation_rhythm.SESSION_BREAK_SECONDS`).

    Returns:
        True if < 2 user messages (first contact / cold start) or if
        the gap between the two most recent user messages >= threshold.
    """
    if not conversation_messages:
        return True

    user_timestamps: list[datetime] = []
    for msg in conversation_messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        raw = msg.get("timestamp")
        if not isinstance(raw, str):
            continue
        try:
            ts = datetime.fromisoformat(raw)
        except ValueError:
            continue
        # Normalise to naive UTC — prevents TypeError on mixed aware/naive
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        user_timestamps.append(ts)

    if len(user_timestamps) < 2:
        return True

    user_timestamps.sort()
    gap = (user_timestamps[-1] - user_timestamps[-2]).total_seconds()
    return gap >= session_break_seconds


class MessageHandler:
    """
    Handles incoming user messages and generates delayed responses.

    Orchestrates the full message processing pipeline:
    1. Load user and agent configuration
    2. Generate response using the Nikita agent
    3. Calculate response delay (Spec 210 v2: log-normal × chapter × momentum)
    4. Store pending response for delayed delivery
    5. Return decision with scheduling information

    Spec 210 v2 removed random skip-decisions: every message produces a
    response. Delay fires only on new-conversation starts; ongoing
    ping-pong returns 0 delay.

    Example usage:
        handler = MessageHandler()
        decision = await handler.handle(user_id, "Hello Nikita")
        # decision.delay_seconds contains when to deliver
        # decision.response contains what to deliver
    """

    def __init__(
        self,
        timer: Optional[ResponseTimer] = None,
        skip_decision: Optional[Any] = None,  # DEPRECATED Spec 210 v2 — ignored
        fact_extractor: Optional[FactExtractor] = None,
    ):
        """
        Initialize the MessageHandler.

        Args:
            timer: Optional ResponseTimer instance (creates default if not provided)
            skip_decision: DEPRECATED (Spec 210 v2). Skip-decision behavior
                           has been removed — every message gets a response.
                           The kwarg is accepted for backwards-compat with
                           tests and callers but is ignored. Will be removed
                           in a future spec.
            fact_extractor: DEPRECATED - kept for backwards compatibility.
                           Fact extraction now happens in post-processing pipeline.
                           See nikita/context/post_processor.py
        """
        self.timer = timer or ResponseTimer()
        # DEPRECATED Spec 210 v2: skip_decision kwarg is accepted but ignored.
        # Retained as an instance attribute for any external caller that peeks
        # at it; its ``should_skip`` method is NEVER called from this handler.
        self.skip_decision = skip_decision
        # DEPRECATED: fact_extractor kept for backwards compatibility
        # Fact extraction moved to post-processing pipeline (spec 012)
        self.fact_extractor = fact_extractor or FactExtractor()

    def _apply_text_patterns(self, response_text: str) -> str:
        """Apply text behavioral patterns to response (Remediation Plan T3.2).

        Processes response through TextPatternProcessor for natural texting feel:
        - Emoji insertion based on context
        - Punctuation quirks
        - Length adjustments

        Args:
            response_text: Raw LLM response.

        Returns:
            Processed response with text patterns applied.
            Returns original text if processing fails (non-blocking).
        """
        try:
            processor = _get_processor_instance()
            pattern_result = processor.process(response_text)
            # Join split messages for single delivery
            if pattern_result.messages:
                processed_text = " ".join(
                    msg.content for msg in pattern_result.messages
                )
                logger.debug(
                    f"[TEXT-PATTERNS] Applied patterns: context={pattern_result.context}, "
                    f"emoji_count={pattern_result.emoji_count}"
                )
                return processed_text
            return response_text
        except Exception as e:
            # Non-blocking: log warning but continue with original response
            logger.warning(f"[TEXT-PATTERNS] Failed to apply patterns: {e}")
            return response_text

    async def handle(
        self,
        user_id: UUID,
        message: str,
        conversation_messages: list[dict[str, Any]] | None = None,
        conversation_id: UUID | None = None,
        session: "AsyncSession | None" = None,  # Spec 038: Session propagation
        psyche_state: dict | None = None,  # Spec 056: Psyche state for L3 injection
    ) -> ResponseDecision:
        """
        Process a user message and prepare a delayed response.

        Handles game state gating:
        - game_over: Returns game ended message, no further interaction
        - won: Returns post-game mode message, immediate delivery
        - boss_fight: Processes with boss challenge context, immediate delivery
        - active: Normal message processing with Spec 210 v2 timing model

        Spec 030: Conversation continuity via message_history.
        When conversation_messages is provided, they are injected into
        NikitaDeps and used to build PydanticAI message_history for
        context continuity. This enables Nikita to understand references
        like "yes", "why", "lol" without losing context.

        Args:
            user_id: UUID of the user sending the message
            message: The user's message text
            conversation_messages: Optional list of previous messages for context
            conversation_id: Optional conversation UUID for logging
            session: Optional SQLAlchemy AsyncSession for DB operations
            psyche_state: Optional psyche state dict for L3 prompt injection

        Returns:
            ResponseDecision containing the response, delay, and scheduling info.

        Raises:
            UserNotFoundError: If the user doesn't exist
        """
        logger.info(
            f"[LLM-DEBUG] TextAgentHandler.handle called: "
            f"user_id={user_id}, message_len={len(message)}, "
            f"conversation_id={conversation_id}, "
            f"history_messages={len(conversation_messages) if conversation_messages else 0}"
        )

        # Load user and get configured agent
        logger.info(f"[LLM-DEBUG] Loading agent for user_id={user_id}")
        agent, deps = await get_nikita_agent_for_user(user_id)

        # Spec 030: Inject conversation context into deps for message_history
        if conversation_messages is not None:
            deps.conversation_messages = conversation_messages
        if conversation_id is not None:
            deps.conversation_id = conversation_id
        # Spec 038: Inject session for session propagation
        if session is not None:
            deps.session = session
        # Spec 056: Inject psyche state for L3 prompt injection
        if psyche_state is not None:
            deps.psyche_state = psyche_state
        logger.info(
            f"[LLM-DEBUG] Agent loaded: game_status={deps.user.game_status}, "
            f"chapter={deps.user.chapter}"
        )

        # Check game_status gating (T12: AC-T12-003, AC-T12-004)
        game_status = deps.user.game_status
        chapter = deps.user.chapter
        now = datetime.now(timezone.utc)

        # Handle game_over state - no further interaction (AC-T12-004)
        if game_status == 'game_over':
            logger.info(
                "Game over for user %s - returning ended message",
                user_id,
            )
            return ResponseDecision(
                response="Our story has ended. The game is over.",
                delay_seconds=0,
                scheduled_at=now,
                should_respond=True,
            )

        # Handle won state - post-game mode (relaxed conversation)
        if game_status == 'won':
            logger.info(
                "User %s has won - post-game mode",
                user_id,
            )
            # In won state, continue conversation but no stakes
            response_text = await generate_response(deps, message)
            # Apply text patterns (T3.2)
            response_text = self._apply_text_patterns(response_text)
            return ResponseDecision(
                response=response_text,
                delay_seconds=0,  # Immediate in post-game
                scheduled_at=now,
                should_respond=True,
            )

        # Handle boss_fight state - no skipping, process with challenge context
        if game_status == 'boss_fight':
            logger.info(
                "User %s in boss_fight - processing challenge response",
                user_id,
            )
            # Boss fight never skips, always responds
            response_text = await generate_response(deps, message)
            # Apply text patterns (T3.2)
            response_text = self._apply_text_patterns(response_text)
            return ResponseDecision(
                response=response_text,
                delay_seconds=0,  # Immediate during boss
                scheduled_at=now,
                should_respond=True,
            )

        # Spec 210 v2: Skip-decision removed. Every message gets a response;
        # pacing is now driven by new-conversation gate + chapter + momentum.

        # Generate response using the agent
        logger.info(f"[LLM-DEBUG] Calling generate_response for user_id={user_id}")
        response_text = await generate_response(deps, message)
        logger.info(
            f"[LLM-DEBUG] generate_response returned: response_len={len(response_text)}"
        )

        # Remediation Plan T3.2: Apply text behavioral patterns (Spec 026)
        response_text = self._apply_text_patterns(response_text)

        # NOTE: Fact extraction REMOVED per spec 012 context engineering redesign
        # Facts are now extracted in the POST-PROCESSING pipeline, not during conversation
        # This reduces latency and moves memory writes to async background processing
        # See: nikita/context/post_processor.py

        # Spec 210 v2: compute delay using log-normal × chapter × momentum.
        # Momentum reads the user's recent user-turn gap history and
        # multiplies the base log-normal sample. Feature-flagged via
        # settings.momentum_enabled (default True). When the current turn
        # is NOT a new conversation (ongoing ping-pong), the timer returns 0.
        settings = get_settings()
        gaps = compute_user_gaps(conversation_messages or [])
        momentum = (
            compute_momentum(gaps, chapter) if settings.momentum_enabled else 1.0
        )
        is_new = _is_new_conversation_from_messages(conversation_messages, now)
        logger.info(
            "[TIMING-HANDLER] ch=%s is_new=%s gaps=%s momentum=%.2f",
            chapter,
            is_new,
            [round(g, 1) for g in gaps],
            momentum,
        )
        delay_seconds = self.timer.calculate_delay(
            chapter,
            is_new_conversation=is_new,
            momentum=momentum,
        )

        # Calculate scheduled delivery time (fresh timestamp after LLM call)
        delivery_now = datetime.now(timezone.utc)
        scheduled_at = delivery_now + timedelta(seconds=delay_seconds)

        # Generate response ID for tracking
        response_id = uuid4()

        # Store pending response for later delivery via scheduled_events table.
        # deps.user.telegram_id must be set — handler is invoked from the
        # Telegram webhook path. Guard explicitly against inconsistent data.
        chat_id = deps.user.telegram_id
        if chat_id is None:
            logger.error(
                "[HANDLER] user %s has no telegram_id; cannot schedule delivery",
                user_id,
            )
            return ResponseDecision(
                response=response_text,
                delay_seconds=delay_seconds,
                scheduled_at=scheduled_at,
                response_id=response_id,
                should_respond=False,
                skip_reason="missing_telegram_id",
            )

        await store_pending_response(
            user_id=user_id,
            response=response_text,
            scheduled_at=scheduled_at,
            response_id=response_id,
            chat_id=chat_id,
            session=session,
        )

        # Return decision (facts extracted post-conversation per spec 012)
        return ResponseDecision(
            response=response_text,
            delay_seconds=delay_seconds,
            scheduled_at=scheduled_at,
            response_id=response_id,
            should_respond=True,
            # facts_extracted is empty - extraction now happens in post-processing
        )
