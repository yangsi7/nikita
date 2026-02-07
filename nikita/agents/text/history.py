"""Message history loader for text agent conversation continuity.

This module implements the HistoryLoader class that retrieves and formats
conversation history for PydanticAI's message_history parameter.

Spec 030: Text Agent Message History and Continuity
Spec 041 T2.8: Two-tier token estimation (fast for loading, accurate for budget)

Key Features:
- Loads messages from conversations.messages JSONB
- Converts to PydanticAI ModelMessage types via ModelMessagesTypeAdapter
- Implements token budgeting (1500-3000 tokens)
- Ensures tool call/return pairing (PydanticAI requirement)
- Uses fast token estimation for message loading loops
- Uses accurate token estimation for final budget validation

Critical Notes (from research):
- When message_history is non-empty, PydanticAI does NOT regenerate the system prompt
- Our @agent.instructions decorators only run when message_history is empty
- Solution: Return None for new sessions to trigger fresh prompt generation
"""

import logging
from typing import Any
from uuid import UUID

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from nikita.context.utils.token_counter import get_token_estimator

logger = logging.getLogger(__name__)

# Token budget for message history tier (1500-3000 tokens)
DEFAULT_TOKEN_BUDGET = 3000
MIN_TURNS_PRESERVED = 10


class HistoryLoader:
    """Loads and formats conversation history for PydanticAI message_history.

    This class is responsible for:
    1. Loading raw messages from conversation.messages JSONB
    2. Converting to PydanticAI-compatible ModelMessage types
    3. Token budget enforcement (truncating oldest messages first)
    4. Ensuring tool call/return pairing (PydanticAI requirement)

    Example usage:
        loader = HistoryLoader(conversation_id, session)
        history = await loader.load(limit=80, token_budget=3000)
        result = await agent.run(prompt, message_history=history)
    """

    def __init__(
        self,
        conversation_id: UUID | None = None,
        raw_messages: list[dict[str, Any]] | None = None,
    ):
        """Initialize HistoryLoader.

        Args:
            conversation_id: The conversation's UUID (for logging/debugging).
            raw_messages: Raw messages from conversation.messages JSONB.
                         If None, load() will return None (new session).
        """
        self.conversation_id = conversation_id
        self.raw_messages = raw_messages or []

    def _convert_to_model_messages(
        self,
        raw_messages: list[dict[str, Any]],
    ) -> list[ModelMessage]:
        """Convert raw JSONB messages to PydanticAI ModelMessage types.

        Handles conversion of Nikita's message format to PydanticAI's format:
        - "user" role → ModelRequest with UserPromptPart
        - "nikita" role → ModelResponse with TextPart
        - Tool calls are preserved if properly formatted

        Args:
            raw_messages: List of message dicts from JSONB.

        Returns:
            List of ModelMessage objects.
        """
        converted: list[ModelMessage] = []

        for msg in raw_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                # User messages become ModelRequest with UserPromptPart
                request = ModelRequest(parts=[UserPromptPart(content=content)])
                converted.append(request)
            elif role == "nikita" or role == "assistant":
                # Nikita/assistant messages become ModelResponse with TextPart
                response = ModelResponse(parts=[TextPart(content=content)])
                converted.append(response)
            elif role == "tool_call":
                # Handle tool calls if present in raw format
                # These would need special handling if stored separately
                pass
            else:
                logger.warning(
                    f"Unknown message role '{role}' in conversation {self.conversation_id}"
                )

        return converted

    def _ensure_tool_call_pairing(
        self,
        messages: list[ModelMessage],
    ) -> list[ModelMessage]:
        """Ensure tool calls and returns are properly paired.

        From PydanticAI docs: "When slicing the message history, you need to
        make sure that tool calls and returns are paired, otherwise the LLM
        may return an error."

        This method removes any unpaired tool calls at the truncation boundary.

        Args:
            messages: List of ModelMessage objects.

        Returns:
            List with unpaired tool calls removed.
        """
        if not messages:
            return messages

        # Track tool call IDs and their return status
        tool_call_ids: set[str] = set()
        tool_return_ids: set[str] = set()

        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_return_ids.add(part.tool_call_id)
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        tool_call_ids.add(part.tool_call_id)

        # Find unpaired tool calls (no matching return)
        unpaired_call_ids = tool_call_ids - tool_return_ids

        if unpaired_call_ids:
            logger.warning(
                f"Excluding {len(unpaired_call_ids)} unpaired tool calls from history "
                f"for conversation {self.conversation_id}"
            )

            # Filter out messages containing unpaired tool calls
            filtered: list[ModelMessage] = []
            for msg in messages:
                if isinstance(msg, ModelResponse):
                    # Check if this response has unpaired tool calls
                    has_unpaired = any(
                        isinstance(part, ToolCallPart)
                        and part.tool_call_id in unpaired_call_ids
                        for part in msg.parts
                    )
                    if not has_unpaired:
                        filtered.append(msg)
                else:
                    filtered.append(msg)
            return filtered

        return messages

    def _estimate_tokens(
        self, messages: list[ModelMessage], accurate: bool = False
    ) -> int:
        """Estimate token count for a list of messages.

        Spec 041 T2.8: Uses two-tier estimation:
        - Fast (default): Character ratio for quick estimates (~100x faster)
        - Accurate: tiktoken encoding for precise budget validation

        Args:
            messages: List of ModelMessage objects.
            accurate: If True, use tiktoken for precise count.

        Returns:
            Estimated token count.
        """
        estimator = get_token_estimator()
        total_tokens = 0

        for msg in messages:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        content = part.content if isinstance(part.content, str) else ""
                        total_tokens += estimator.estimate(content, accurate=accurate)
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        content = part.content if isinstance(part.content, str) else ""
                        total_tokens += estimator.estimate(content, accurate=accurate)

        return total_tokens

    def _truncate_to_budget(
        self,
        messages: list[ModelMessage],
        token_budget: int,
        min_turns: int = MIN_TURNS_PRESERVED,
    ) -> list[ModelMessage]:
        """Truncate messages to fit within token budget.

        Truncates from the oldest messages first, but preserves at least
        min_turns messages regardless of budget.

        Spec 041 T2.8: Uses fast estimation during truncation loop,
        accurate estimation for final budget validation.

        Args:
            messages: List of ModelMessage objects.
            token_budget: Maximum token budget.
            min_turns: Minimum messages to preserve regardless of budget.

        Returns:
            Truncated list of messages.
        """
        if not messages:
            return messages

        # Always preserve at least min_turns
        if len(messages) <= min_turns:
            return messages

        # Start with all messages and remove oldest until within budget
        # Use fast estimation in the loop for performance
        current_messages = messages.copy()

        while len(current_messages) > min_turns:
            tokens = self._estimate_tokens(current_messages, accurate=False)
            if tokens <= token_budget:
                break
            # Remove oldest message
            current_messages = current_messages[1:]

        # Use accurate estimation for final count logging
        final_tokens = self._estimate_tokens(current_messages, accurate=True)
        if len(current_messages) < len(messages):
            logger.info(
                f"Truncated history from {len(messages)} to {len(current_messages)} "
                f"messages (~{final_tokens} tokens) for conversation {self.conversation_id}"
            )

        return current_messages

    def load(
        self,
        limit: int = 80,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ) -> list[ModelMessage] | None:
        """Load and format message history for agent.run().

        IMPORTANT: Returns None (not empty list) when:
        - No messages in conversation (new session)
        - Raw messages list is empty

        This is critical because PydanticAI does NOT regenerate the system
        prompt when message_history is non-empty (even if it's an empty list).
        Returning None ensures our @agent.instructions decorators are called.

        Args:
            limit: Maximum messages to load before truncation.
            token_budget: Token budget for history tier.

        Returns:
            list[ModelMessage] for continuation, or None for new sessions.
        """
        # Return None for new sessions to trigger fresh prompt generation
        if not self.raw_messages:
            logger.debug(
                f"No messages in conversation {self.conversation_id}, "
                "returning None for fresh prompt generation"
            )
            return None

        # Take last N messages
        raw_subset = self.raw_messages[-limit:] if limit else self.raw_messages

        # Convert to ModelMessage types
        messages = self._convert_to_model_messages(raw_subset)

        if not messages:
            return None

        # Truncate to token budget
        messages = self._truncate_to_budget(messages, token_budget)

        # Ensure tool call pairing
        messages = self._ensure_tool_call_pairing(messages)

        # Use accurate estimation for final count logging
        logger.info(
            f"Loaded {len(messages)} messages (~{self._estimate_tokens(messages, accurate=True)} tokens) "
            f"for conversation {self.conversation_id}"
        )

        return messages if messages else None


async def load_message_history(
    conversation_messages: list[dict[str, Any]] | None,
    conversation_id: UUID | None = None,
    limit: int = 80,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> list[ModelMessage] | None:
    """Convenience function to load message history.

    Args:
        conversation_messages: Raw messages from conversation.messages JSONB.
        conversation_id: The conversation's UUID (for logging).
        limit: Maximum messages to load.
        token_budget: Token budget for history tier.

    Returns:
        list[ModelMessage] for continuation, or None for new sessions.
    """
    loader = HistoryLoader(
        conversation_id=conversation_id,
        raw_messages=conversation_messages,
    )
    return loader.load(limit=limit, token_budget=token_budget)
