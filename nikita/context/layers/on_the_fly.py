"""Layer 6: On-the-Fly Modifications (Spec 021, T015).

Handles mid-conversation modifications to the prompt based on:
- Mood shifts (user shares positive/negative news)
- Memory retrieval (user references past conversations)

This layer is different from Layers 1-5 because it operates
DURING the conversation, not during pre-computation.

Token budget: ~200 tokens
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class ModificationType(str, Enum):
    """Types of on-the-fly modifications."""

    MOOD_SHIFT = "mood_shift"
    MEMORY_RETRIEVAL = "memory_retrieval"


@dataclass
class PromptModification:
    """A modification to apply to the prompt.

    Attributes:
        type: Type of modification (mood_shift or memory_retrieval).
        content: The content to inject into the prompt.
        reason: Why this modification is being applied.
        query: For memory_retrieval, the search query.
    """

    type: ModificationType
    content: str
    reason: str
    query: str = ""


# Trigger patterns for mood shifts
MOOD_SHIFT_POSITIVE_PATTERNS = [
    r"\b(promoted|promotion|got the job|accepted|engaged|married|pregnant)\b",
    r"\b(won|award|achievement|success|accomplished)\b",
    r"\b(love|amazing|wonderful|fantastic|incredible|best day)\b",
    r"\b(so happy|so excited|overjoyed|thrilled|ecstatic)\b",
]

MOOD_SHIFT_NEGATIVE_PATTERNS = [
    r"\b(fired|laid off|lost my job|rejected|failed)\b",
    r"\b(broke up|divorced|separated|left me)\b",
    r"\b(died|passed away|funeral|cancer|illness)\b",
    r"\b(so sad|depressed|devastated|heartbroken)\b",
    r"\b(stressed|anxious|worried|scared|terrified)\b",
]

# Trigger patterns for memory retrieval
MEMORY_RETRIEVAL_PATTERNS = [
    r"\bremember when\b",
    r"\byou know how i\b",
    r"\bi told you (about|that)\b",
    r"\bwe talked about\b",
    r"\byou mentioned\b",
    r"\blast time (you|i|we)\b",
    r"\bmy (sister|brother|mom|dad|friend|boss|colleague)\b",
]


class Layer6Handler:
    """Handler for Layer 6: On-the-Fly Modifications.

    Detects triggers in user messages that require prompt modifications
    and applies them during the conversation. Supports:
    - Mood shifts: When user shares emotional news
    - Memory retrieval: When user references past conversations

    Attributes:
        _memory_client: Optional memory client for Graphiti queries.
    """

    def __init__(self) -> None:
        """Initialize Layer6Handler."""
        self._memory_client: Any | None = None

    def detect_triggers(
        self,
        message: str,
        current_mood: str = "neutral",
    ) -> list[PromptModification]:
        """Detect modification triggers in user message.

        Args:
            message: User's message.
            current_mood: Current emotional state.

        Returns:
            List of modifications to apply.
        """
        modifications: list[PromptModification] = []
        message_lower = message.lower()

        # Check for positive mood shift
        for pattern in MOOD_SHIFT_POSITIVE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                modifications.append(
                    PromptModification(
                        type=ModificationType.MOOD_SHIFT,
                        content="Feeling genuinely happy and excited for them",
                        reason=f"User expressed positive news matching: {pattern}",
                    )
                )
                break  # Only one mood shift at a time

        # Check for negative mood shift
        if not any(m.type == ModificationType.MOOD_SHIFT for m in modifications):
            for pattern in MOOD_SHIFT_NEGATIVE_PATTERNS:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    modifications.append(
                        PromptModification(
                            type=ModificationType.MOOD_SHIFT,
                            content="Feeling empathetic and supportive, offering comfort",
                            reason=f"User expressed difficult news matching: {pattern}",
                        )
                    )
                    break

        # Check for memory retrieval triggers
        for pattern in MEMORY_RETRIEVAL_PATTERNS:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                # Extract query context (words around the match)
                start = max(0, match.start() - 20)
                end = min(len(message), match.end() + 50)
                query_context = message[start:end].strip()

                modifications.append(
                    PromptModification(
                        type=ModificationType.MEMORY_RETRIEVAL,
                        content="",  # Will be filled by retrieval
                        reason=f"User referenced memory: {match.group()}",
                        query=query_context,
                    )
                )
                break

        return modifications

    def apply_modification(
        self,
        current_prompt: str,
        modification: PromptModification,
    ) -> str:
        """Apply a modification to the prompt.

        Args:
            current_prompt: Current prompt text.
            modification: Modification to apply.

        Returns:
            Modified prompt.
        """
        if modification.type == ModificationType.MOOD_SHIFT:
            # Add mood context to the prompt
            mood_section = f"\n\n**Current emotional adjustment**: {modification.content}"
            return current_prompt + mood_section

        elif modification.type == ModificationType.MEMORY_RETRIEVAL:
            if modification.content:
                memory_section = f"\n\n**Retrieved memory**: {modification.content}"
                return current_prompt + memory_section

        return current_prompt

    async def retrieve_memory(
        self,
        user_id: UUID,
        query: str,
        num_results: int = 3,
    ) -> str | None:
        """Retrieve relevant memory via Graphiti.

        Args:
            user_id: User's UUID.
            query: Search query.
            num_results: Maximum results to return.

        Returns:
            Combined memory content, or None if not found.
        """
        try:
            client = await self._get_memory_client(user_id)
            results = await client.search(query=query, num_results=num_results)

            if not results:
                return None

            # Combine results into a single string
            contents = [r.content for r in results if hasattr(r, "content")]
            return "; ".join(contents) if contents else None

        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            return None

    async def _get_memory_client(self, user_id: UUID) -> Any:
        """Get or create memory client for user.

        Args:
            user_id: User's UUID.

        Returns:
            Memory client instance.
        """
        # This would typically use NikitaMemory from nikita.memory.graphiti_client
        # For now, we return a mock-able placeholder
        if self._memory_client is not None:
            return self._memory_client

        # Import here to avoid circular imports
        try:
            from nikita.memory.graphiti_client import get_memory_client
            return await get_memory_client(user_id)
        except ImportError:
            logger.warning("Memory client not available")
            raise

    async def process_modification(
        self,
        user_id: UUID,
        current_prompt: str,
        modification: PromptModification,
    ) -> str:
        """Process a modification fully, including memory retrieval if needed.

        Args:
            user_id: User's UUID.
            current_prompt: Current prompt text.
            modification: Modification to apply.

        Returns:
            Modified prompt.
        """
        if modification.type == ModificationType.MEMORY_RETRIEVAL and modification.query:
            # Retrieve memory first
            memory_content = await self.retrieve_memory(
                user_id=user_id,
                query=modification.query,
            )
            if memory_content:
                modification.content = memory_content

        return self.apply_modification(current_prompt, modification)

    def compose_static(self) -> str:
        """Compose the static Layer 6 section.

        This appears in every prompt as a placeholder for dynamic modifications.
        Actual modifications are applied during conversation via process_modification.

        Returns:
            Static Layer 6 prompt section.
        """
        return """## Real-time Adjustments

*This section may be updated during the conversation based on:*
- Mood shifts from the conversation
- Memory retrievals when relevant
- Topic changes requiring context refresh

**Current state**: Baseline emotional tone, ready to adapt."""

    @property
    def token_estimate(self) -> int:
        """Estimate token count for Layer 6.

        Returns:
            Target token budget (200).
        """
        return 200


# Module-level singleton for efficiency
_default_handler: Layer6Handler | None = None


def get_layer6_handler() -> Layer6Handler:
    """Get the singleton Layer6Handler instance.

    Returns:
        Cached Layer6Handler instance.
    """
    global _default_handler
    if _default_handler is None:
        _default_handler = Layer6Handler()
    return _default_handler
