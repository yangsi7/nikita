"""Data access repositories for Nikita.

Provides repository pattern implementation for all database entities.
"""

from nikita.db.repositories.base import BaseRepository
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "UserMetricsRepository",
    "ConversationRepository",
    "ScoreHistoryRepository",
    "VicePreferenceRepository",
    "DailySummaryRepository",
]
