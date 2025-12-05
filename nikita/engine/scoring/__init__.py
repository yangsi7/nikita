"""Scoring engine module (spec 003).

This module implements LLM-based conversation analysis and scoring
for the Nikita relationship game. It analyzes user messages to determine
metric deltas (intimacy, passion, trust, secureness) and applies
engagement-aware multipliers from the 014 engagement model.

Key Components:
- MetricDeltas: Per-interaction score changes (-10 to +10)
- ResponseAnalysis: Full LLM analysis result with behaviors
- ScoreCalculator: Applies deltas with engagement multipliers
- ThresholdEmitter: Emits boss/game-over events

Scoring Flow:
1. User message → ScoreAnalyzer (LLM) → ResponseAnalysis
2. ResponseAnalysis.deltas × engagement_multiplier → adjusted deltas
3. ScoreCalculator applies to UserMetrics → composite score
4. ThresholdEmitter checks boss thresholds (55-75%)
"""

from nikita.engine.scoring.analyzer import ScoreAnalyzer
from nikita.engine.scoring.calculator import (
    CALIBRATION_MULTIPLIERS,
    ScoreCalculator,
    ScoreResult,
)
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
    ScoreChangeEvent,
)
from nikita.engine.scoring.service import ScoringService

__all__ = [
    # Models
    "MetricDeltas",
    "ResponseAnalysis",
    "ConversationContext",
    "ScoreChangeEvent",
    "ScoreResult",
    # Analyzer
    "ScoreAnalyzer",
    # Calculator
    "ScoreCalculator",
    "CALIBRATION_MULTIPLIERS",
    # Service
    "ScoringService",
]
