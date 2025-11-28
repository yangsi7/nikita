"""FastAPI dependencies for repository injection.

T7: Repository Dependencies

Provides FastAPI Depends functions for injecting repositories
into route handlers with proper session management.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.database import get_async_session
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository

# Type alias for session dependency
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_user_repo(
    session: AsyncSessionDep,
) -> AsyncGenerator[UserRepository, None]:
    """Get UserRepository instance.

    Args:
        session: Injected AsyncSession.

    Yields:
        UserRepository instance.
    """
    yield UserRepository(session)


async def get_metrics_repo(
    session: AsyncSessionDep,
) -> AsyncGenerator[UserMetricsRepository, None]:
    """Get UserMetricsRepository instance.

    Args:
        session: Injected AsyncSession.

    Yields:
        UserMetricsRepository instance.
    """
    yield UserMetricsRepository(session)


async def get_conversation_repo(
    session: AsyncSessionDep,
) -> AsyncGenerator[ConversationRepository, None]:
    """Get ConversationRepository instance.

    Args:
        session: Injected AsyncSession.

    Yields:
        ConversationRepository instance.
    """
    yield ConversationRepository(session)


async def get_score_history_repo(
    session: AsyncSessionDep,
) -> AsyncGenerator[ScoreHistoryRepository, None]:
    """Get ScoreHistoryRepository instance.

    Args:
        session: Injected AsyncSession.

    Yields:
        ScoreHistoryRepository instance.
    """
    yield ScoreHistoryRepository(session)


async def get_vice_repo(
    session: AsyncSessionDep,
) -> AsyncGenerator[VicePreferenceRepository, None]:
    """Get VicePreferenceRepository instance.

    Args:
        session: Injected AsyncSession.

    Yields:
        VicePreferenceRepository instance.
    """
    yield VicePreferenceRepository(session)


async def get_summary_repo(
    session: AsyncSessionDep,
) -> AsyncGenerator[DailySummaryRepository, None]:
    """Get DailySummaryRepository instance.

    Args:
        session: Injected AsyncSession.

    Yields:
        DailySummaryRepository instance.
    """
    yield DailySummaryRepository(session)


# Type aliases for use in route handlers
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
MetricsRepoDep = Annotated[UserMetricsRepository, Depends(get_metrics_repo)]
ConversationRepoDep = Annotated[ConversationRepository, Depends(get_conversation_repo)]
ScoreHistoryRepoDep = Annotated[ScoreHistoryRepository, Depends(get_score_history_repo)]
ViceRepoDep = Annotated[VicePreferenceRepository, Depends(get_vice_repo)]
SummaryRepoDep = Annotated[DailySummaryRepository, Depends(get_summary_repo)]
