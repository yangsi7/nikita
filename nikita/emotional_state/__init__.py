"""Emotional State Engine Module (Spec 023).

This module provides multi-dimensional emotional state tracking for Nikita,
including conflict detection and recovery mechanics.

Key components:
- EmotionalStateModel: Extended 4D state with conflict tracking
- ConflictState: Enum for conflict states (passive_aggressive, cold, vulnerable, explosive)
- StateStore: Persistence layer for emotional states
- StateComputer: Computes state from events and conversations
- ConflictDetector: Detects conflict state transitions
- RecoveryManager: Handles recovery from conflict states
"""

from nikita.emotional_state.computer import (
    ConversationTone,
    LifeEventImpact,
    StateComputer,
    get_state_computer,
)
from nikita.emotional_state.conflict import (
    ConflictDetector,
    get_conflict_detector,
)
from nikita.emotional_state.models import (
    ConflictState,
    EmotionalStateModel,
)
from nikita.emotional_state.recovery import (
    RecoveryApproach,
    RecoveryManager,
    RecoveryResult,
    get_recovery_manager,
)
from nikita.emotional_state.store import StateStore, get_state_store

__all__ = [
    # Models
    "ConflictState",
    "EmotionalStateModel",
    "ConversationTone",
    "LifeEventImpact",
    "RecoveryApproach",
    "RecoveryResult",
    # Store
    "StateStore",
    "get_state_store",
    # Computer
    "StateComputer",
    "get_state_computer",
    # Conflict
    "ConflictDetector",
    "get_conflict_detector",
    # Recovery
    "RecoveryManager",
    "get_recovery_manager",
]
