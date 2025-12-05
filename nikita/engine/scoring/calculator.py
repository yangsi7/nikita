"""Score calculator for applying deltas and computing composites (spec 003).

This module handles:
- Applying engagement calibration multipliers to deltas
- Updating individual metrics with bounds enforcement
- Calculating weighted composite scores
- Detecting threshold events (boss, critical, game over)
"""

from dataclasses import dataclass, field
from decimal import Decimal

from nikita.config.enums import EngagementState
from nikita.engine.constants import BOSS_THRESHOLDS, METRIC_WEIGHTS
from nikita.engine.scoring.models import MetricDeltas, ResponseAnalysis, ScoreChangeEvent

# Engagement state multipliers (from 014 engagement model)
# Applied to positive deltas only - penalties stay full
CALIBRATION_MULTIPLIERS: dict[EngagementState, Decimal] = {
    EngagementState.IN_ZONE: Decimal("1.0"),
    EngagementState.CALIBRATING: Decimal("0.9"),
    EngagementState.DRIFTING: Decimal("0.8"),
    EngagementState.DISTANT: Decimal("0.6"),
    EngagementState.CLINGY: Decimal("0.5"),
    EngagementState.OUT_OF_ZONE: Decimal("0.2"),
}

# Critical threshold for warnings
CRITICAL_LOW_THRESHOLD = Decimal("20")


@dataclass
class ScoreResult:
    """Result of a score calculation.

    Contains before/after state, deltas applied, and any threshold events.
    """

    score_before: Decimal
    score_after: Decimal
    metrics_before: dict[str, Decimal]
    metrics_after: dict[str, Decimal]
    deltas_applied: MetricDeltas
    multiplier_applied: Decimal
    engagement_state: EngagementState
    events: list[ScoreChangeEvent] = field(default_factory=list)

    @property
    def delta(self) -> Decimal:
        """Net score change."""
        return self.score_after - self.score_before


class ScoreCalculator:
    """Calculates scores with engagement multipliers.

    Handles the full scoring flow:
    1. Apply engagement multiplier to deltas
    2. Update individual metrics (with bounds)
    3. Calculate composite score
    4. Detect threshold events
    """

    def __init__(self):
        """Initialize calculator with standard weights."""
        self.weights = dict(METRIC_WEIGHTS)

    def apply_multiplier(
        self,
        deltas: MetricDeltas,
        engagement_state: EngagementState,
    ) -> MetricDeltas:
        """Apply engagement multiplier to positive deltas.

        Positive deltas are multiplied by the state's multiplier.
        Negative deltas (penalties) are NOT reduced - they stay full.

        Args:
            deltas: The base metric deltas
            engagement_state: Current engagement state

        Returns:
            Adjusted MetricDeltas with multiplier applied to positives
        """
        multiplier = CALIBRATION_MULTIPLIERS.get(engagement_state, Decimal("1.0"))

        def adjust(delta: Decimal) -> Decimal:
            if delta > Decimal("0"):
                return delta * multiplier
            return delta  # Negative stays full

        return MetricDeltas(
            intimacy=adjust(deltas.intimacy),
            passion=adjust(deltas.passion),
            trust=adjust(deltas.trust),
            secureness=adjust(deltas.secureness),
        )

    def calculate_composite(self, metrics: dict[str, Decimal]) -> Decimal:
        """Calculate weighted composite score.

        Formula: sum(metric * weight) for all metrics
        Result is bounded 0-100.

        Args:
            metrics: Dict of metric name -> value

        Returns:
            Composite score (0-100)
        """
        total = Decimal("0")
        for metric, weight in self.weights.items():
            value = metrics.get(metric, Decimal("0"))
            total += value * weight

        # Ensure bounds
        return max(Decimal("0"), min(Decimal("100"), total))

    def update_metrics(
        self,
        current: dict[str, Decimal],
        deltas: MetricDeltas,
    ) -> dict[str, Decimal]:
        """Apply deltas to current metrics with bounds enforcement.

        Args:
            current: Current metric values
            deltas: Deltas to apply

        Returns:
            Updated metrics (all bounded 0-100)
        """

        def clamp(value: Decimal) -> Decimal:
            return max(Decimal("0"), min(Decimal("100"), value))

        return {
            "intimacy": clamp(current["intimacy"] + deltas.intimacy),
            "passion": clamp(current["passion"] + deltas.passion),
            "trust": clamp(current["trust"] + deltas.trust),
            "secureness": clamp(current["secureness"] + deltas.secureness),
        }

    def calculate(
        self,
        current_metrics: dict[str, Decimal],
        analysis: ResponseAnalysis,
        engagement_state: EngagementState,
        chapter: int,
    ) -> ScoreResult:
        """Perform full score calculation.

        Args:
            current_metrics: Current metric values
            analysis: LLM analysis with deltas
            engagement_state: Current engagement state
            chapter: Current chapter (1-5)

        Returns:
            ScoreResult with full before/after state and events
        """
        # Step 1: Calculate score before
        score_before = self.calculate_composite(current_metrics)

        # Step 2: Apply engagement multiplier to deltas
        multiplier = CALIBRATION_MULTIPLIERS.get(engagement_state, Decimal("1.0"))
        adjusted_deltas = self.apply_multiplier(analysis.deltas, engagement_state)

        # Step 3: Update metrics with bounds
        metrics_after = self.update_metrics(current_metrics, adjusted_deltas)

        # Step 4: Calculate score after
        score_after = self.calculate_composite(metrics_after)

        # Step 5: Detect threshold events
        events = self._detect_events(score_before, score_after, chapter)

        return ScoreResult(
            score_before=score_before,
            score_after=score_after,
            metrics_before=dict(current_metrics),
            metrics_after=metrics_after,
            deltas_applied=adjusted_deltas,
            multiplier_applied=multiplier,
            engagement_state=engagement_state,
            events=events,
        )

    def _detect_events(
        self,
        score_before: Decimal,
        score_after: Decimal,
        chapter: int,
    ) -> list[ScoreChangeEvent]:
        """Detect threshold events based on score change.

        Args:
            score_before: Score before change
            score_after: Score after change
            chapter: Current chapter

        Returns:
            List of ScoreChangeEvent for any crossed thresholds
        """
        events = []

        boss_threshold = BOSS_THRESHOLDS.get(chapter, Decimal("55"))

        # Boss threshold reached (rising)
        if score_before < boss_threshold <= score_after:
            events.append(
                ScoreChangeEvent(
                    event_type="boss_threshold_reached",
                    chapter=chapter,
                    score_before=score_before,
                    score_after=score_after,
                    threshold=boss_threshold,
                    details={"threshold_name": f"Chapter {chapter} Boss"},
                )
            )

        # Critical low (falling below 20)
        if score_before >= CRITICAL_LOW_THRESHOLD > score_after:
            events.append(
                ScoreChangeEvent(
                    event_type="critical_low",
                    chapter=chapter,
                    score_before=score_before,
                    score_after=score_after,
                    threshold=CRITICAL_LOW_THRESHOLD,
                )
            )

        # Recovery from critical (rising above 20)
        if score_before < CRITICAL_LOW_THRESHOLD <= score_after:
            events.append(
                ScoreChangeEvent(
                    event_type="recovery_from_critical",
                    chapter=chapter,
                    score_before=score_before,
                    score_after=score_after,
                    threshold=CRITICAL_LOW_THRESHOLD,
                )
            )

        # Game over (hitting 0)
        if score_after <= Decimal("0"):
            events.append(
                ScoreChangeEvent(
                    event_type="game_over",
                    chapter=chapter,
                    score_before=score_before,
                    score_after=score_after,
                    details={"reason": "Score reached 0"},
                )
            )

        return events
