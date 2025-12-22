"""Data access repositories for Nikita.

Provides repository pattern implementation for all database entities.
"""

from nikita.db.repositories.base import BaseRepository
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.job_execution_repository import JobExecutionRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.pending_registration_repository import (
    PendingRegistrationRepository,
)
from nikita.db.repositories.profile_repository import (
    BackstoryRepository,
    OnboardingStateRepository,
    ProfileRepository,
    VenueCacheRepository,
)
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.thread_repository import ConversationThreadRepository
from nikita.db.repositories.thought_repository import NikitaThoughtRepository
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
    "PendingRegistrationRepository",
    "ConversationThreadRepository",
    "NikitaThoughtRepository",
    "JobExecutionRepository",
    "ProfileRepository",
    "BackstoryRepository",
    "OnboardingStateRepository",
    "VenueCacheRepository",
]
