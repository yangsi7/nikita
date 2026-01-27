"""Ingestion Stage - Load conversation from database.

Spec 037 T2.5: Stage 1 of post-processing pipeline.
Loads the conversation record and validates it has messages.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.context.pipeline_context import PipelineContext
from nikita.context.stages.base import PipelineStage, StageError, StageResult
from nikita.db.models.conversation import Conversation
from nikita.db.repositories.conversation_repository import ConversationRepository


class IngestionStage(PipelineStage[UUID, Conversation]):
    """Stage 1: Load and validate conversation.

    Spec 037 T2.5:
    - AC-T2.5.1: is_critical = True
    - AC-T2.5.2: timeout_seconds = 10.0
    - AC-T2.5.3: Raises StageError if conversation not found
    - AC-T2.5.4: Raises StageError if messages empty
    """

    name = "ingestion"
    is_critical = True
    timeout_seconds = 10.0
    max_retries = 2

    def __init__(self, session: AsyncSession):
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session
        """
        super().__init__(session)
        self._repo = ConversationRepository(session)

    async def _run(
        self,
        context: PipelineContext,
        conversation_id: UUID,
    ) -> Conversation:
        """Load conversation from database.

        Args:
            context: Pipeline context
            conversation_id: ID of conversation to load

        Returns:
            Loaded Conversation model

        Raises:
            StageError: If conversation not found or has no messages
        """
        self._logger.info(
            "loading_conversation",
            conversation_id=str(conversation_id),
        )

        # Load conversation
        conversation = await self._repo.get(conversation_id)

        if conversation is None:
            raise StageError(
                stage_name=self.name,
                message=f"Conversation {conversation_id} not found",
                recoverable=False,
            )

        # Validate messages exist
        if not conversation.messages:
            raise StageError(
                stage_name=self.name,
                message=f"Conversation {conversation_id} has no messages",
                recoverable=False,
            )

        self._logger.info(
            "conversation_loaded",
            conversation_id=str(conversation_id),
            message_count=len(conversation.messages),
            user_id=str(conversation.user_id),
        )

        # Store conversation in context for other stages
        context.conversation = conversation

        return conversation
