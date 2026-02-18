"""Database models for Nikita."""

from nikita.db.models.audit_log import AuditLog
from nikita.db.models.base import Base
from nikita.db.models.error_log import ErrorLevel, ErrorLog
from nikita.db.models.context import ConversationThread, NikitaThought
from nikita.db.models.conversation import Conversation, MessageEmbedding
from nikita.db.models.engagement import EngagementHistory, EngagementState
from nikita.db.models.game import DailySummary, ScoreHistory
from nikita.db.models.generated_prompt import GeneratedPrompt
from nikita.db.models.memory_fact import MemoryFact
from nikita.db.models.ready_prompt import ReadyPrompt
from nikita.db.models.job_execution import JobExecution, JobName, JobStatus
from nikita.db.models.narrative_arc import UserNarrativeArc
from nikita.db.models.pending_registration import PendingRegistration
from nikita.db.models.profile import (
    OnboardingState,
    OnboardingStep,
    UserBackstory,
    UserProfile,
    VenueCache,
)
from nikita.db.models.rate_limit import RateLimit
from nikita.db.models.scheduled_event import EventPlatform, EventStatus, EventType, ScheduledEvent
from nikita.db.models.scheduled_touchpoint import ScheduledTouchpoint
from nikita.db.models.social_circle import UserSocialCircle
from nikita.db.models.psyche_state import PsycheStateRecord
from nikita.db.models.user import User, UserMetrics, UserVicePreference

__all__ = [
    "AuditLog",
    "Base",
    "ErrorLevel",
    "ErrorLog",
    "User",
    "UserMetrics",
    "UserNarrativeArc",
    "UserSocialCircle",
    "UserVicePreference",
    "Conversation",
    "MessageEmbedding",
    "ScoreHistory",
    "DailySummary",
    "PendingRegistration",
    "ConversationThread",
    "NikitaThought",
    "RateLimit",
    "EngagementState",
    "EngagementHistory",
    "GeneratedPrompt",
    "MemoryFact",
    "ReadyPrompt",
    "JobExecution",
    "JobName",
    "JobStatus",
    "UserProfile",
    "UserBackstory",
    "VenueCache",
    "OnboardingState",
    "OnboardingStep",
    "ScheduledEvent",
    "EventPlatform",
    "EventStatus",
    "EventType",
    "ScheduledTouchpoint",
    "PsycheStateRecord",
]
