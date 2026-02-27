"""Conflict Generation System (Spec 027).

This module implements realistic relationship conflicts with:
- Trigger detection (dismissive, neglect, jealousy, boundary, trust)
- Conflict generation with severity calculation
- Escalation mechanics (subtle → direct → crisis)
- Resolution evaluation (apology, explanation, grand gestures)
- Breakup risk and game over state

Usage:
    from nikita.conflicts import (
        TriggerDetector,
        ConflictGenerator,
        EscalationManager,
        ResolutionManager,
        BreakupManager,
    )

    # Detect triggers in user message
    triggers = detector.detect(user_message, context)

    # Generate conflict if triggers warrant
    conflict = generator.generate(triggers, user_state)

    # Check for escalation
    escalation_manager.check_escalation(conflict)

    # Evaluate resolution attempt
    resolution = resolution_manager.evaluate(user_response, conflict)
"""

from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictSummary,
    ConflictTrigger,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    TriggerType,
    get_conflict_config,
    trigger_to_conflict_type,
)
from nikita.conflicts.detector import (
    DetectionContext,
    DetectionResult,
    TriggerDetector,
)
from nikita.conflicts.generator import (
    ConflictGenerator,
    GenerationContext,
    GenerationResult,
    get_conflict_generator,
)
from nikita.conflicts.escalation import (
    EscalationManager,
    EscalationResult,
    get_escalation_manager,
)
from nikita.conflicts.resolution import (
    ResolutionContext,
    ResolutionEvaluation,
    ResolutionManager,
    ResolutionQuality,
    get_resolution_manager,
)
from nikita.conflicts.breakup import (
    BreakupManager,
    BreakupResult,
    BreakupRisk,
    ThresholdResult,
    get_breakup_manager,
)

__all__ = [
    # Models
    "ActiveConflict",
    "ConflictConfig",
    "ConflictSummary",
    "ConflictTrigger",
    "ConflictType",
    "EscalationLevel",
    "ResolutionType",
    "TriggerType",
    # Functions
    "get_conflict_config",
    "trigger_to_conflict_type",
    # Detector (Phase B)
    "DetectionContext",
    "DetectionResult",
    "TriggerDetector",
    # Generator (Phase C)
    "ConflictGenerator",
    "GenerationContext",
    "GenerationResult",
    "get_conflict_generator",
    # Escalation (Phase D)
    "EscalationManager",
    "EscalationResult",
    "get_escalation_manager",
    # Resolution (Phase E)
    "ResolutionContext",
    "ResolutionEvaluation",
    "ResolutionManager",
    "ResolutionQuality",
    "get_resolution_manager",
    # Breakup (Phase F)
    "BreakupManager",
    "BreakupResult",
    "BreakupRisk",
    "ThresholdResult",
    "get_breakup_manager",
]
