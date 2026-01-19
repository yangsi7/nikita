"""Proactive Touchpoint System (Spec 025).

Enables Nikita to initiate 20-30% of conversations based on:
- Time-based triggers (morning/evening)
- Life event triggers (022)
- Gap-based triggers (>24h without contact)

Architecture:
- TouchpointScheduler: Evaluates and schedules touchpoints
- MessageGenerator: Creates message content via MetaPromptService
- TouchpointEngine: Orchestrates delivery
- TouchpointStore: Database persistence

Example Usage:
    from nikita.touchpoints import TouchpointEngine

    engine = TouchpointEngine()
    await engine.evaluate_and_schedule_for_user(user_id)
    await engine.deliver_due_touchpoints()
"""

from nikita.touchpoints.models import (
    ScheduledTouchpoint,
    TouchpointConfig,
    TriggerContext,
    TriggerType,
)
from nikita.touchpoints.scheduler import TouchpointScheduler
from nikita.touchpoints.generator import MessageGenerator, generate_touchpoint_message
from nikita.touchpoints.silence import (
    SilenceDecision,
    SilenceReason,
    StrategicSilence,
    should_apply_silence,
)
from nikita.touchpoints.engine import (
    DeliveryResult,
    TouchpointEngine,
    deliver_due_touchpoints,
)
from nikita.touchpoints.store import TouchpointStore

__all__ = [
    "ScheduledTouchpoint",
    "TouchpointConfig",
    "TriggerContext",
    "TriggerType",
    "TouchpointScheduler",
    "MessageGenerator",
    "generate_touchpoint_message",
    "SilenceDecision",
    "SilenceReason",
    "StrategicSilence",
    "should_apply_silence",
    "DeliveryResult",
    "TouchpointEngine",
    "deliver_due_touchpoints",
    "TouchpointStore",
]
