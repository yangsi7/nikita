"""Vice Processing Stage - Detect and update user vice profile.

Spec 037 T2.8: Stage 7.5 of post-processing pipeline.
Analyzes conversation exchanges for vice signals.

Fixes H-4: Non-alternating messages handled correctly.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.base import PipelineStage, StageError
from nikita.db.models.conversation import Conversation


class ViceProcessingStage(PipelineStage[Conversation, int]):
    """Stage 7.5: Vice signal detection and profile update.

    Spec 037 T2.8:
    - AC-T2.8.1: is_critical = False
    - AC-T2.8.2: timeout_seconds = 30.0
    - AC-T2.8.3: _extract_exchanges() handles non-alternating messages
    - AC-T2.8.4: Both "assistant" and "nikita" roles recognized
    """

    name = "vice_processing"
    is_critical = False
    timeout_seconds = 30.0
    max_retries = 1

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session)

    async def _run(
        self,
        context: PipelineContext,
        conversation: Conversation,
    ) -> int:
        """Process conversation for vice signals.

        Uses context manager for ViceService to ensure cleanup.

        Args:
            context: Pipeline context
            conversation: Conversation to analyze

        Returns:
            Total number of signals detected
        """
        from nikita.engine.vice.service import ViceService

        self._logger.info(
            "starting_vice_processing",
            conversation_id=str(context.conversation_id),
            message_count=len(conversation.messages),
        )

        total_signals = 0

        # Use context manager for proper resource cleanup
        async with ViceService() as vice_service:
            # Fixed message pairing logic (H-4)
            exchanges = self._extract_exchanges(conversation.messages)

            self._logger.info(
                "extracted_exchanges",
                exchange_count=len(exchanges),
            )

            for user_msg, nikita_msg in exchanges:
                try:
                    result = await vice_service.process_conversation(
                        user_id=conversation.user_id,
                        user_message=user_msg,
                        nikita_message=nikita_msg,
                        conversation_id=conversation.id,
                    )
                    total_signals += result.get("signals_detected", 0)
                except Exception as e:
                    self._logger.warning(
                        "vice_exchange_failed",
                        error=str(e),
                    )
                    # Continue processing other exchanges

        self._logger.info(
            "vice_processing_complete",
            total_signals=total_signals,
        )

        return total_signals

    def _extract_exchanges(
        self,
        messages: list[dict],
    ) -> list[tuple[str, str]]:
        """Extract valid user→nikita exchanges.

        Handles non-alternating messages by finding nearest pairs.
        Fixes H-4: Message pairing assumption bug.

        Args:
            messages: List of message dicts with role and content

        Returns:
            List of (user_message, nikita_message) tuples
        """
        exchanges = []
        i = 0

        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Find next user message
            if role != "user":
                i += 1
                continue

            # Skip empty user messages
            if not content or not content.strip():
                i += 1
                continue

            user_msg = content

            # Find next assistant/nikita message after this user message
            j = i + 1
            while j < len(messages):
                next_msg = messages[j]
                next_role = next_msg.get("role", "")
                next_content = next_msg.get("content", "")

                # AC-T2.8.4: Both "assistant" and "nikita" roles recognized
                if next_role in ("nikita", "assistant"):
                    # Skip empty assistant messages
                    if next_content and next_content.strip():
                        exchanges.append((user_msg, next_content))
                        i = j + 1
                        break
                j += 1
            else:
                # No nikita response found, skip this user message
                i += 1

        return exchanges
