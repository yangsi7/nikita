"""Message handler for Nikita text agent.

This module provides the main entry point for handling user messages.
It orchestrates:
1. Skip decision check
2. Agent response generation
3. Text pattern processing (Spec 026 - Remediation Plan T3.2)
4. Response timing calculation
5. Pending response storage for delayed delivery

Spec 030: Message history injection for conversation continuity.
The handler accepts optional conversation_messages and conversation_id
which are passed through to generate_response() for message_history.

Spec 026 / Remediation Plan T3.2: Text behavioral patterns.
Raw LLM responses are processed through TextPatternProcessor to apply:
- Emoji insertion based on context
- Punctuation quirks
- Length adjustments
- Natural texting patterns
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.text.facts import ExtractedFact, FactExtractor
from nikita.agents.text.skip import SkipDecision
from nikita.agents.text.timing import ResponseTimer

if TYPE_CHECKING:
    pass


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
        should_respond: Whether to actually send the response (False when skipped)
        skip_reason: Reason for skipping, if applicable
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
) -> None:
    """
    Store a pending response for later delivery.

    This is a placeholder that should be implemented with actual
    storage (database, Redis, etc.) for production use.

    Args:
        user_id: The user this response is for
        response: The response text to deliver
        scheduled_at: When to deliver the response
        response_id: Unique identifier for this response
    """
    # TODO: Implement actual storage
    # Options:
    # 1. Database table (pending_responses)
    # 2. Redis with TTL
    # 3. Celery delayed task
    pass


class MessageHandler:
    """
    Handles incoming user messages and generates delayed responses.

    Orchestrates the full message processing pipeline:
    1. Check skip decision (based on chapter probability)
    2. Load user and agent configuration
    3. Generate response using the Nikita agent
    4. Calculate response delay based on chapter
    5. Extract facts from the conversation
    6. Store pending response for delayed delivery
    7. Return decision with scheduling information

    Example usage:
        handler = MessageHandler()
        decision = await handler.handle(user_id, "Hello Nikita")
        if decision.should_respond:
            # decision.delay_seconds contains when to deliver
            # decision.response contains what to deliver
            # decision.facts_extracted contains learned facts
        else:
            # Message was skipped - decision.skip_reason explains why
    """

    def __init__(
        self,
        timer: Optional[ResponseTimer] = None,
        skip_decision: Optional[SkipDecision] = None,
        fact_extractor: Optional[FactExtractor] = None,
    ):
        """
        Initialize the MessageHandler.

        Args:
            timer: Optional ResponseTimer instance (creates default if not provided)
            skip_decision: Optional SkipDecision instance (creates default if not provided)
            fact_extractor: DEPRECATED - kept for backwards compatibility.
                           Fact extraction now happens in post-processing pipeline.
                           See nikita/context/post_processor.py
        """
        self.timer = timer or ResponseTimer()
        self.skip_decision = skip_decision or SkipDecision()
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
    ) -> ResponseDecision:
        """
        Process a user message and prepare a delayed response.

        Handles game state gating:
        - game_over: Returns game ended message, no further interaction
        - won: Returns post-game mode message, continues conversation
        - boss_fight: Processes with boss challenge context, no skipping
        - active: Normal message processing with skip decision

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

        Returns:
            ResponseDecision containing the response, delay, and scheduling info.
            If skipped, should_respond=False and skip_reason is set.

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

        # Skip decision based on chapter probability (AC-5.2.1)
        if self.skip_decision.should_skip(chapter):
            skip_reason = f"Random skip based on chapter {chapter} probability"
            logger.info(
                "Skipping message for user %s: %s",
                user_id,
                skip_reason,
            )
            # Return skip decision without generating response (AC-5.2.5)
            return ResponseDecision(
                response="",
                delay_seconds=0,
                scheduled_at=now,
                should_respond=False,
                skip_reason=skip_reason,
            )

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

        # Calculate delay based on user's chapter
        delay_seconds = self.timer.calculate_delay(chapter)

        # Calculate scheduled delivery time
        now = datetime.now(timezone.utc)
        scheduled_at = now + timedelta(seconds=delay_seconds)

        # Generate response ID for tracking
        response_id = uuid4()

        # Store pending response for later delivery
        await store_pending_response(
            user_id=user_id,
            response=response_text,
            scheduled_at=scheduled_at,
            response_id=response_id,
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
