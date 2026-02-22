"""Extracted handler classes for Telegram message processing (Strangler Fig).

Each handler encapsulates a distinct concern extracted from MessageHandler:
- BossEncounterHandler: Boss fight lifecycle (opening, judging, outcomes)
- ScoringOrchestrator: Score computation, persistence, boss-threshold detection
- EngagementOrchestrator: Engagement state machine updates and game-over detection

These classes are standalone — they can be unit-tested independently
and will progressively replace equivalent code in MessageHandler.
"""

from nikita.platforms.telegram.handlers.boss_encounter import BossEncounterHandler
from nikita.platforms.telegram.handlers.engagement_orchestrator import EngagementOrchestrator
from nikita.platforms.telegram.handlers.scoring_orchestrator import ScoringOrchestrator

__all__ = ["BossEncounterHandler", "ScoringOrchestrator", "EngagementOrchestrator"]
