"""Message handler for Nikita text agent.

This module provides the main entry point for handling user messages.
It orchestrates:
1. Skip decision check
2. Agent response generation
3. Response timing calculation
4. Pending response storage for delayed delivery
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

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
            fact_extractor: Optional FactExtractor instance (creates default if not provided)
        """
        self.timer = timer or ResponseTimer()
        self.skip_decision = skip_decision or SkipDecision()
        self.fact_extractor = fact_extractor or FactExtractor()

    async def handle(self, user_id: UUID, message: str) -> ResponseDecision:
        """
        Process a user message and prepare a delayed response.

        First checks whether to skip this message based on chapter-specific
        probabilities. If skipped, returns immediately without generating
        a response.

        Args:
            user_id: UUID of the user sending the message
            message: The user's message text

        Returns:
            ResponseDecision containing the response, delay, and scheduling info.
            If skipped, should_respond=False and skip_reason is set.

        Raises:
            UserNotFoundError: If the user doesn't exist
        """
        # Load user and get configured agent
        agent, deps = await get_nikita_agent_for_user(user_id)

        # Check if we should skip this message (AC-5.2.1)
        chapter = deps.user.chapter
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
                scheduled_at=datetime.now(timezone.utc),
                should_respond=False,
                skip_reason=skip_reason,
            )

        # Generate response using the agent
        response_text = await generate_response(deps, message)

        # Extract facts from the conversation (AC-6.3.1)
        existing_facts = await deps.memory.get_user_facts()
        extracted_facts = await self.fact_extractor.extract_facts(
            user_message=message,
            nikita_response=response_text,
            existing_facts=existing_facts,
        )

        # Store extracted facts in memory (AC-6.3.2)
        for fact in extracted_facts:
            await deps.memory.add_user_fact(fact.fact, fact.confidence)

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

        # Return decision with extracted facts (AC-6.3.4)
        return ResponseDecision(
            response=response_text,
            delay_seconds=delay_seconds,
            scheduled_at=scheduled_at,
            response_id=response_id,
            should_respond=True,
            facts_extracted=extracted_facts,
        )
