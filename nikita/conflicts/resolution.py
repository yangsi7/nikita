"""Resolution management for conflict system (Spec 027, Phase E).

Handles conflict resolution evaluation and processing.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from nikita.config.settings import get_settings
from nikita.conflicts.models import (
    ActiveConflict,
    ConflictConfig,
    ConflictType,
    EscalationLevel,
    ResolutionType,
    get_conflict_config,
)
from nikita.conflicts.store import ConflictStore, get_conflict_store


class ResolutionQuality(str, Enum):
    """Quality of a resolution attempt."""

    EXCELLENT = "excellent"  # Grand gesture, sincere apology
    GOOD = "good"  # Thoughtful response, shows understanding
    ADEQUATE = "adequate"  # Minimal acknowledgment
    POOR = "poor"  # Dismissive, defensive
    HARMFUL = "harmful"  # Makes it worse


class ResolutionContext(BaseModel):
    """Context for resolution evaluation.

    Attributes:
        conflict: The conflict being resolved.
        user_message: User's response/resolution attempt.
        previous_attempts: Number of previous attempts.
        relationship_score: Current relationship score.
    """

    conflict: ActiveConflict
    user_message: str
    previous_attempts: int = 0
    relationship_score: int = Field(default=50, ge=0, le=100)


class ResolutionEvaluation(BaseModel):
    """Result of resolution evaluation.

    Attributes:
        quality: Quality of the resolution attempt.
        resolution_type: Resulting resolution type.
        severity_reduction: How much to reduce severity (-1.0 to 1.0).
            Negative values increase severity (harmful responses).
        score_change: Change to relationship score.
        reasoning: Explanation of evaluation.
    """

    quality: ResolutionQuality
    resolution_type: ResolutionType
    severity_reduction: float = Field(default=0.0, ge=-1.0, le=1.0)
    score_change: int = 0
    reasoning: str = ""


class ResolutionManager:
    """Manages conflict resolution attempts.

    Handles:
    - LLM-based evaluation of resolution attempts
    - Resolution type determination
    - Score adjustments
    """

    # Quality to severity reduction mapping
    QUALITY_SEVERITY_REDUCTION = {
        ResolutionQuality.EXCELLENT: 1.0,  # Full resolution
        ResolutionQuality.GOOD: 0.6,
        ResolutionQuality.ADEQUATE: 0.3,
        ResolutionQuality.POOR: 0.0,
        ResolutionQuality.HARMFUL: -0.2,  # Increases severity
    }

    # Quality to score change mapping
    QUALITY_SCORE_CHANGE = {
        ResolutionQuality.EXCELLENT: 10,
        ResolutionQuality.GOOD: 5,
        ResolutionQuality.ADEQUATE: 1,
        ResolutionQuality.POOR: -2,
        ResolutionQuality.HARMFUL: -10,
    }

    # Thresholds for full resolution
    FULL_RESOLUTION_THRESHOLD = 0.8

    def __init__(
        self,
        store: ConflictStore | None = None,
        config: ConflictConfig | None = None,
        llm_enabled: bool = True,
    ):
        """Initialize resolution manager.

        Args:
            store: ConflictStore for persistence.
            config: Conflict configuration.
            llm_enabled: Whether to use LLM for evaluation.
        """
        self._store = store or get_conflict_store()
        self._config = config or get_conflict_config()
        self._llm_enabled = llm_enabled
        self._agent = None

        if llm_enabled:
            settings = get_settings()
            self._agent = Agent(
                model="anthropic:claude-haiku-4-5-20251001",
                output_type=dict[str, Any],
                system_prompt=self._get_evaluation_prompt(),
            )

    def _get_evaluation_prompt(self) -> str:
        """Get the system prompt for LLM evaluation."""
        return """You are an expert at evaluating relationship conflict resolution attempts.
Analyze the user's response to a conflict and evaluate its quality.

Return a JSON object with:
- quality: one of "excellent", "good", "adequate", "poor", "harmful"
- reasoning: brief explanation (2-3 sentences)
- detected_elements: list of detected positive/negative elements

Quality definitions:
- excellent: Sincere apology with understanding, grand gesture, genuine remorse
- good: Thoughtful response, shows empathy, takes responsibility
- adequate: Basic acknowledgment, minimal effort but not dismissive
- poor: Defensive, dismissive, deflecting, not addressing the issue
- harmful: Blaming, gaslighting, insulting, making it worse

Consider:
1. Does the response address the specific conflict type?
2. Is there genuine acknowledgment of the partner's feelings?
3. Is there an apology or taking responsibility?
4. Does the response show understanding of why they're upset?
5. Are there any defensive or dismissive elements?"""

    async def evaluate(
        self,
        context: ResolutionContext,
    ) -> ResolutionEvaluation:
        """Evaluate a resolution attempt.

        Args:
            context: Resolution context with conflict and response.

        Returns:
            ResolutionEvaluation with quality and outcomes.
        """
        # Try LLM evaluation first
        if self._llm_enabled and self._agent:
            quality = await self._evaluate_with_llm(context)
        else:
            quality = self._evaluate_with_rules(context)

        # Calculate outcomes based on quality
        severity_reduction = self.QUALITY_SEVERITY_REDUCTION[quality]
        score_change = self.QUALITY_SCORE_CHANGE[quality]

        # Determine resolution type
        if quality == ResolutionQuality.EXCELLENT:
            resolution_type = ResolutionType.FULL
        elif quality in [ResolutionQuality.GOOD, ResolutionQuality.ADEQUATE]:
            resolution_type = ResolutionType.PARTIAL
        else:
            resolution_type = ResolutionType.FAILED

        # Adjust for escalation level (harder to resolve at higher levels)
        level_multiplier = {
            EscalationLevel.SUBTLE: 1.0,
            EscalationLevel.DIRECT: 0.8,
            EscalationLevel.CRISIS: 0.5,
        }.get(context.conflict.escalation_level, 1.0)

        severity_reduction *= level_multiplier

        # At CRISIS level, only EXCELLENT resolves fully
        if (
            context.conflict.escalation_level == EscalationLevel.CRISIS
            and quality != ResolutionQuality.EXCELLENT
        ):
            resolution_type = ResolutionType.PARTIAL if resolution_type == ResolutionType.FULL else resolution_type

        return ResolutionEvaluation(
            quality=quality,
            resolution_type=resolution_type,
            severity_reduction=severity_reduction,
            score_change=score_change,
            reasoning=f"Quality: {quality.value}, Level: {context.conflict.escalation_level.name}",
        )

    def evaluate_sync(self, context: ResolutionContext) -> ResolutionEvaluation:
        """Synchronous evaluation (rule-based only).

        Args:
            context: Resolution context.

        Returns:
            ResolutionEvaluation based on rules.
        """
        quality = self._evaluate_with_rules(context)

        severity_reduction = self.QUALITY_SEVERITY_REDUCTION[quality]
        score_change = self.QUALITY_SCORE_CHANGE[quality]

        if quality == ResolutionQuality.EXCELLENT:
            resolution_type = ResolutionType.FULL
        elif quality in [ResolutionQuality.GOOD, ResolutionQuality.ADEQUATE]:
            resolution_type = ResolutionType.PARTIAL
        else:
            resolution_type = ResolutionType.FAILED

        level_multiplier = {
            EscalationLevel.SUBTLE: 1.0,
            EscalationLevel.DIRECT: 0.8,
            EscalationLevel.CRISIS: 0.5,
        }.get(context.conflict.escalation_level, 1.0)

        severity_reduction *= level_multiplier

        if (
            context.conflict.escalation_level == EscalationLevel.CRISIS
            and quality != ResolutionQuality.EXCELLENT
        ):
            resolution_type = ResolutionType.PARTIAL if resolution_type == ResolutionType.FULL else resolution_type

        return ResolutionEvaluation(
            quality=quality,
            resolution_type=resolution_type,
            severity_reduction=severity_reduction,
            score_change=score_change,
            reasoning=f"Rule-based evaluation: {quality.value}",
        )

    # Quality to temperature delta mapping (Spec 057)
    QUALITY_TEMPERATURE_DELTA = {
        ResolutionQuality.EXCELLENT: -25.0,
        ResolutionQuality.GOOD: -15.0,
        ResolutionQuality.ADEQUATE: -5.0,
        ResolutionQuality.POOR: 2.0,
        ResolutionQuality.HARMFUL: 5.0,
    }

    def resolve(
        self,
        conflict_id: str,
        evaluation: ResolutionEvaluation,
        conflict_details: dict[str, Any] | None = None,
    ) -> ActiveConflict | None:
        """Apply resolution to a conflict.

        Spec 057: When temperature flag is ON, also updates temperature
        based on resolution quality and records repair in history.

        Args:
            conflict_id: ID of the conflict.
            evaluation: Evaluation result.
            conflict_details: Optional conflict_details JSONB (Spec 057).

        Returns:
            Updated conflict or None if not found.
        """
        conflict = self._store.get_conflict(conflict_id)
        if not conflict or conflict.resolved:
            return None

        # Apply severity reduction
        if evaluation.severity_reduction > 0:
            self._store.reduce_severity(conflict_id, evaluation.severity_reduction)
        elif evaluation.severity_reduction < 0:
            # Harmful response increases severity
            conflict = self._store.get_conflict(conflict_id)
            new_severity = min(1.0, conflict.severity - evaluation.severity_reduction)
            self._store.update_conflict(conflict_id, severity=new_severity)

        # Increment resolution attempts
        self._store.increment_resolution_attempts(conflict_id)

        # Check if fully resolved
        if evaluation.resolution_type == ResolutionType.FULL:
            self._store.resolve_conflict(conflict_id, ResolutionType.FULL)
        elif evaluation.resolution_type == ResolutionType.PARTIAL:
            # Check if severity dropped to 0
            updated = self._store.get_conflict(conflict_id)
            if updated.severity <= 0:
                self._store.resolve_conflict(conflict_id, ResolutionType.PARTIAL)

        # Spec 057: Update temperature and Gottman from resolution
        self._last_updated_conflict_details = self._apply_resolution_temperature(
            evaluation=evaluation,
            conflict_details=conflict_details,
        )

        return self._store.get_conflict(conflict_id)

    def get_last_updated_conflict_details(self) -> dict[str, Any] | None:
        """Get the last updated conflict details from resolve() (Spec 057).

        Returns:
            Updated conflict_details dict, or None.
        """
        return getattr(self, "_last_updated_conflict_details", None)

    def _apply_resolution_temperature(
        self,
        evaluation: ResolutionEvaluation,
        conflict_details: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Apply temperature and Gottman updates from resolution (Spec 057).

        Args:
            evaluation: Resolution evaluation.
            conflict_details: Current conflict details JSONB.

        Returns:
            Updated conflict_details dict, or None if flag OFF.
        """
        from nikita.conflicts import is_conflict_temperature_enabled

        if not is_conflict_temperature_enabled():
            return None

        from datetime import UTC, datetime

        from nikita.conflicts.gottman import GottmanTracker
        from nikita.conflicts.models import ConflictDetails
        from nikita.conflicts.temperature import TemperatureEngine

        details = ConflictDetails.from_jsonb(conflict_details)

        # Temperature delta from resolution quality
        temp_delta = self.QUALITY_TEMPERATURE_DELTA.get(evaluation.quality, 0.0)
        details = TemperatureEngine.update_conflict_details(
            details=details,
            temp_delta=temp_delta,
        )

        # Gottman: positive counter on successful repair (EXCELLENT/GOOD/ADEQUATE)
        is_positive_repair = evaluation.quality in (
            ResolutionQuality.EXCELLENT,
            ResolutionQuality.GOOD,
            ResolutionQuality.ADEQUATE,
        )
        if is_positive_repair:
            is_in_conflict = details.zone in ("hot", "critical")
            details = GottmanTracker.update_conflict_details(
                details=details,
                is_positive=True,
                is_in_conflict=is_in_conflict,
            )

        # Record repair in history
        repair_record = {
            "at": datetime.now(UTC).isoformat(),
            "quality": evaluation.quality.value,
            "temp_delta": temp_delta,
        }
        details.repair_attempts.append(repair_record)

        return details.to_jsonb()

    async def _evaluate_with_llm(
        self,
        context: ResolutionContext,
    ) -> ResolutionQuality:
        """Evaluate using LLM.

        Args:
            context: Resolution context.

        Returns:
            ResolutionQuality.
        """
        if not self._agent:
            return self._evaluate_with_rules(context)

        try:
            prompt = f"""Evaluate this resolution attempt:

Conflict type: {context.conflict.conflict_type.value}
Escalation level: {context.conflict.escalation_level.name}
Previous attempts: {context.previous_attempts}

User's response:
"{context.user_message}"

Evaluate the quality of this response."""

            result = await self._agent.run(prompt)
            quality_str = result.output.get("quality", "adequate").lower()

            try:
                return ResolutionQuality(quality_str)
            except ValueError:
                return ResolutionQuality.ADEQUATE

        except Exception:
            return self._evaluate_with_rules(context)

    def _evaluate_with_rules(self, context: ResolutionContext) -> ResolutionQuality:
        """Rule-based evaluation fallback.

        Args:
            context: Resolution context.

        Returns:
            ResolutionQuality based on rules.
        """
        message = context.user_message.lower()

        # Excellent indicators
        excellent_keywords = [
            "i'm so sorry", "i was wrong", "you're right",
            "i understand", "i love you", "forgive me",
            "let me make it up", "i didn't mean to",
        ]
        excellent_count = sum(1 for kw in excellent_keywords if kw in message)

        # Good indicators
        good_keywords = [
            "sorry", "apologize", "my fault", "understand",
            "won't happen again", "feel bad", "didn't realize",
        ]
        good_count = sum(1 for kw in good_keywords if kw in message)

        # Harmful indicators
        harmful_keywords = [
            "your fault", "you're overreacting", "whatever",
            "get over it", "don't care", "crazy", "paranoid",
            "not a big deal", "you always",
        ]
        harmful_count = sum(1 for kw in harmful_keywords if kw in message)

        # Poor indicators
        poor_keywords = [
            "but", "yeah but", "i guess", "fine", "ok ok",
            "if you say so",
        ]
        poor_count = sum(1 for kw in poor_keywords if kw in message)

        # Determine quality
        if harmful_count >= 2:
            return ResolutionQuality.HARMFUL
        elif harmful_count >= 1 and good_count == 0:
            return ResolutionQuality.HARMFUL

        if excellent_count >= 2:
            return ResolutionQuality.EXCELLENT
        elif excellent_count >= 1 and good_count >= 1:
            return ResolutionQuality.EXCELLENT

        if good_count >= 2:
            return ResolutionQuality.GOOD
        elif good_count >= 1:
            return ResolutionQuality.ADEQUATE

        if poor_count >= 2 or len(message) < 20:
            return ResolutionQuality.POOR

        # Default to adequate for longer messages without clear indicators
        if len(message) >= 50:
            return ResolutionQuality.ADEQUATE

        return ResolutionQuality.POOR


# Global resolution manager instance
_resolution_manager: ResolutionManager | None = None


def get_resolution_manager() -> ResolutionManager:
    """Get the global resolution manager instance.

    Returns:
        ResolutionManager instance.
    """
    global _resolution_manager
    if _resolution_manager is None:
        _resolution_manager = ResolutionManager()
    return _resolution_manager
