"""Engagement model module (spec 014).

This module implements the 6-state engagement model that tracks how
players interact with Nikita. The engagement state affects scoring
multipliers and Nikita's behavioral responses.

States:
- CALIBRATING: Learning player's engagement style (0.9x)
- IN_ZONE: Found the sweet spot (1.0x)
- DRIFTING: Engagement is off but recoverable (0.8x)
- CLINGY: Player messaging too much (0.5x)
- DISTANT: Player not engaging enough (0.6x)
- OUT_OF_ZONE: Crisis mode, needs recovery (0.2x)

Key Components:
- EngagementState enum with multipliers
- Detection algorithms (clinginess, neglect)
- Calibration score calculator
- State machine with transition rules
- Recovery mechanics
"""

from nikita.config.enums import EngagementState
from nikita.engine.engagement import calculator, detection, models, recovery, state_machine
from nikita.engine.engagement.calculator import (
    CALIBRATION_WEIGHTS,
    CalibrationCalculator,
    OptimalFrequencyCalculator,
    map_score_to_state,
)
from nikita.engine.engagement.detection import (
    ClinginessDetector,
    NeglectDetector,
    analyze_distraction,
    analyze_neediness,
    clear_analysis_cache,
)
from nikita.engine.engagement.models import (
    CalibrationResult,
    ClinginessResult,
    EngagementSnapshot,
    NeglectResult,
    StateTransition,
)
from nikita.engine.engagement.recovery import (
    GameOverResult,
    RecoveryAction,
    RecoveryCheckResult,
    RecoveryManager,
)
from nikita.engine.engagement.state_machine import EngagementStateMachine

__all__ = [
    # Enum
    "EngagementState",
    # Modules
    "models",
    "detection",
    "calculator",
    "state_machine",
    "recovery",
    # Models
    "EngagementSnapshot",
    "ClinginessResult",
    "NeglectResult",
    "CalibrationResult",
    "StateTransition",
    # Detectors
    "ClinginessDetector",
    "NeglectDetector",
    # LLM Analysis
    "analyze_neediness",
    "analyze_distraction",
    "clear_analysis_cache",
    # Calculators
    "OptimalFrequencyCalculator",
    "CalibrationCalculator",
    "map_score_to_state",
    "CALIBRATION_WEIGHTS",
    # State Machine
    "EngagementStateMachine",
    # Recovery
    "RecoveryManager",
    "RecoveryAction",
    "RecoveryCheckResult",
    "GameOverResult",
]
