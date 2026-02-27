"""Trigger detection for conflict generation (Spec 027, Phase B).

Detects potential conflict triggers from user messages and context.
Uses a combination of rule-based and LLM-based detection.
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from nikita.config.models import Models
from nikita.config.settings import get_settings
from nikita.conflicts.models import ConflictTrigger, TriggerType
from nikita.llm import llm_retry


class DetectionContext(BaseModel):
    """Context for trigger detection.

    Attributes:
        user_id: User being analyzed.
        message: Current message text.
        chapter: Current game chapter (1-5).
        relationship_score: Current relationship score (0-100).
        last_interaction: Time of last user interaction.
        recent_messages: Recent message history.
        conversation_duration_minutes: How long current conversation has lasted.
    """

    user_id: str
    message: str
    chapter: int = Field(default=1, ge=1, le=5)
    relationship_score: int = Field(default=50, ge=0, le=100)
    last_interaction: datetime | None = None
    recent_messages: list[str] = Field(default_factory=list)
    conversation_duration_minutes: int = 0


class DetectionResult(BaseModel):
    """Result of trigger detection.

    Attributes:
        triggers: List of detected triggers.
        detection_time: When detection was performed.
        context_analyzed: The context that was analyzed.
        updated_conflict_details: Updated conflict details JSONB (Spec 057).
    """

    triggers: list[ConflictTrigger] = Field(default_factory=list)
    detection_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context_analyzed: DetectionContext | None = None
    updated_conflict_details: dict[str, Any] | None = Field(default=None)

    @property
    def has_triggers(self) -> bool:
        """Check if any triggers were detected."""
        return len(self.triggers) > 0

    @property
    def highest_severity(self) -> float:
        """Get the highest severity among detected triggers."""
        if not self.triggers:
            return 0.0
        return max(t.severity for t in self.triggers)


class TriggerDetector:
    """Detects conflict triggers in user messages.

    Uses a combination of:
    - Rule-based detection (message length, time gaps)
    - LLM-based detection (tone analysis, content detection)
    - Pattern matching (keywords, sentiment)
    """

    # Thresholds for rule-based detection
    SHORT_MESSAGE_THRESHOLD = 10  # chars
    NEGLECT_GAP_HOURS = 24
    CONSECUTIVE_SHORT_THRESHOLD = 3

    # Keywords for different trigger types
    JEALOUSY_KEYWORDS = [
        "friend", "coworker", "ex", "crush", "date", "met someone",
        "hanging out with", "went out with", "cute", "attractive",
    ]

    BOUNDARY_KEYWORDS = [
        "nude", "naked", "send pic", "show me", "come over",
        "tonight", "your place", "my place", "alone",
    ]

    # Chapter-based sensitivity multipliers (higher = more sensitive)
    CHAPTER_SENSITIVITY = {
        1: 1.5,  # Early relationship, very sensitive
        2: 1.3,
        3: 1.0,  # Baseline
        4: 0.9,
        5: 0.8,  # Established relationship, less sensitive
    }

    def __init__(
        self,
        llm_enabled: bool = True,
    ):
        """Initialize trigger detector.

        Args:
            llm_enabled: Whether to use LLM for detection.
        """
        self._llm_enabled = llm_enabled
        self._agent = None

        if llm_enabled:
            settings = get_settings()
            self._agent = Agent(
                model=Models.haiku(),
                output_type=list[dict[str, Any]],
                system_prompt=self._get_detection_prompt(),
            )

    def _get_detection_prompt(self) -> str:
        """Get the system prompt for LLM-based detection."""
        return """You are an expert at detecting relationship conflicts and triggers.
Analyze the message and context to detect potential conflict triggers.

For each trigger detected, return a JSON object with:
- trigger_type: one of "dismissive", "neglect", "jealousy", "boundary", "trust"
- severity: float from 0.0 to 1.0 (how severe this trigger is)
- reason: brief explanation

Only detect genuine triggers. Be conservative - don't flag normal conversation.

Trigger definitions:
- dismissive: Short, uninterested responses; topic changes to avoid engagement
- neglect: Long gaps without explanation; ignoring messages
- jealousy: Positive mentions of other romantic interests; comparing partner
- boundary: Pushing physical/emotional boundaries too fast for relationship stage
- trust: Inconsistencies; catching lies; broken promises

Return an empty list [] if no triggers are detected."""

    async def detect(
        self,
        context: DetectionContext,
        conflict_details: dict[str, Any] | None = None,
    ) -> DetectionResult:
        """Detect triggers in the given context.

        Spec 057: When temperature flag is ON and conflict_details provided,
        also updates temperature based on detected trigger types.

        Args:
            context: Detection context with message and history.
            conflict_details: Optional conflict_details JSONB (Spec 057).

        Returns:
            DetectionResult with any detected triggers.
        """
        triggers: list[ConflictTrigger] = []

        # Rule-based detection (always runs)
        triggers.extend(self._detect_dismissive_rules(context))
        triggers.extend(self._detect_neglect_rules(context))
        triggers.extend(self._detect_jealousy_rules(context))
        triggers.extend(self._detect_boundary_rules(context))

        # LLM-based detection (optional, for more nuanced detection)
        if self._llm_enabled and self._agent:
            try:
                llm_triggers = await self._detect_with_llm(context)
            except Exception:
                # LLM detection failure is not critical
                llm_triggers = []
            # Merge LLM triggers, avoiding duplicates
            for lt in llm_triggers:
                if not any(t.trigger_type == lt.trigger_type for t in triggers):
                    triggers.append(lt)

        # Apply chapter sensitivity to severities
        sensitivity = self.CHAPTER_SENSITIVITY.get(context.chapter, 1.0)
        for trigger in triggers:
            adjusted_severity = min(1.0, trigger.severity * sensitivity)
            # Create new trigger with adjusted severity (immutable model)
            idx = triggers.index(trigger)
            triggers[idx] = ConflictTrigger(
                trigger_id=trigger.trigger_id,
                trigger_type=trigger.trigger_type,
                severity=adjusted_severity,
                detected_at=trigger.detected_at,
                context=trigger.context,
                user_messages=trigger.user_messages,
            )

        # Spec 057: Update temperature from detected triggers
        result = DetectionResult(
            triggers=triggers,
            detection_time=datetime.now(UTC),
            context_analyzed=context,
        )
        result.updated_conflict_details = self._apply_trigger_temperature(
            triggers=triggers,
            conflict_details=conflict_details,
        )

        return result

    def _apply_trigger_temperature(
        self,
        triggers: list[ConflictTrigger],
        conflict_details: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Apply temperature deltas from detected triggers (Spec 057).

        Gated behind feature flag. Returns None when flag is OFF or no triggers.

        Args:
            triggers: Detected triggers.
            conflict_details: Current conflict details JSONB.

        Returns:
            Updated conflict_details dict, or None if no update.
        """
        if not triggers:
            return None

        from nikita.conflicts.models import ConflictDetails
        from nikita.conflicts.temperature import TemperatureEngine

        details = ConflictDetails.from_jsonb(conflict_details)

        total_delta = 0.0
        for trigger in triggers:
            total_delta += TemperatureEngine.calculate_delta_from_trigger(trigger.trigger_type)

        if total_delta > 0:
            details = TemperatureEngine.update_conflict_details(
                details=details,
                temp_delta=total_delta,
            )

        return details.to_jsonb()

    def _detect_dismissive_rules(
        self,
        context: DetectionContext,
    ) -> list[ConflictTrigger]:
        """Detect dismissive behavior using rules.

        Checks for:
        - Very short messages
        - Consecutive short messages
        - One-word responses
        """
        triggers = []
        message = context.message.strip()

        # Short message detection
        if len(message) < self.SHORT_MESSAGE_THRESHOLD:
            severity = 0.3
            # Single word is more severe
            if " " not in message:
                severity = 0.4
            # Very short (1-3 chars) is most severe
            if len(message) <= 3:
                severity = 0.5

            triggers.append(self._create_trigger(
                trigger_type=TriggerType.DISMISSIVE,
                severity=severity,
                context={"reason": "short_message", "length": len(message)},
                messages=[message],
            ))

        # Consecutive short messages
        recent_short = sum(
            1 for m in context.recent_messages[-5:]
            if len(m.strip()) < self.SHORT_MESSAGE_THRESHOLD
        )
        if recent_short >= self.CONSECUTIVE_SHORT_THRESHOLD:
            triggers.append(self._create_trigger(
                trigger_type=TriggerType.DISMISSIVE,
                severity=0.6,
                context={"reason": "consecutive_short", "count": recent_short},
                messages=context.recent_messages[-5:],
            ))

        return triggers

    def _detect_neglect_rules(
        self,
        context: DetectionContext,
    ) -> list[ConflictTrigger]:
        """Detect neglect using time-based rules.

        Checks for:
        - Long gaps between interactions
        - Short conversation sessions
        """
        triggers = []

        # Time gap detection
        if context.last_interaction:
            gap = datetime.now(UTC) - context.last_interaction
            gap_hours = gap.total_seconds() / 3600

            if gap_hours >= self.NEGLECT_GAP_HOURS:
                # Severity increases with gap length
                severity = min(0.9, 0.3 + (gap_hours / 48) * 0.3)
                triggers.append(self._create_trigger(
                    trigger_type=TriggerType.NEGLECT,
                    severity=severity,
                    context={"reason": "time_gap", "hours": gap_hours},
                    messages=[],
                ))

        # Short session detection
        if (
            context.conversation_duration_minutes > 0
            and context.conversation_duration_minutes < 5
            and len(context.recent_messages) <= 3
        ):
            triggers.append(self._create_trigger(
                trigger_type=TriggerType.NEGLECT,
                severity=0.25,
                context={
                    "reason": "short_session",
                    "duration": context.conversation_duration_minutes,
                },
                messages=context.recent_messages,
            ))

        return triggers

    def _detect_jealousy_rules(
        self,
        context: DetectionContext,
    ) -> list[ConflictTrigger]:
        """Detect jealousy triggers using keyword matching.

        Checks for:
        - Mentions of other people
        - Dating/romantic context
        """
        triggers = []
        message_lower = context.message.lower()

        # Keyword detection
        matched_keywords = [
            kw for kw in self.JEALOUSY_KEYWORDS
            if kw in message_lower
        ]

        if matched_keywords:
            # More keywords = higher severity
            severity = min(0.8, 0.3 + len(matched_keywords) * 0.15)
            triggers.append(self._create_trigger(
                trigger_type=TriggerType.JEALOUSY,
                severity=severity,
                context={"reason": "keywords", "matched": matched_keywords},
                messages=[context.message],
            ))

        return triggers

    def _detect_boundary_rules(
        self,
        context: DetectionContext,
    ) -> list[ConflictTrigger]:
        """Detect boundary violations using keyword matching.

        Checks for:
        - Sexual pressure (chapter-aware)
        - Pushy behavior
        """
        triggers = []
        message_lower = context.message.lower()

        # Keyword detection
        matched_keywords = [
            kw for kw in self.BOUNDARY_KEYWORDS
            if kw in message_lower
        ]

        if matched_keywords:
            # Base severity + bonus per keyword
            base_severity = 0.4
            # Early chapters are more sensitive
            if context.chapter <= 2:
                base_severity = 0.6

            severity = min(0.9, base_severity + len(matched_keywords) * 0.1)
            triggers.append(self._create_trigger(
                trigger_type=TriggerType.BOUNDARY,
                severity=severity,
                context={
                    "reason": "keywords",
                    "matched": matched_keywords,
                    "chapter": context.chapter,
                },
                messages=[context.message],
            ))

        return triggers

    @llm_retry
    async def _detect_with_llm(
        self,
        context: DetectionContext,
    ) -> list[ConflictTrigger]:
        """Use LLM for nuanced trigger detection.

        Retries on transient errors (rate limits, server errors, timeouts).

        Args:
            context: Detection context.

        Returns:
            List of triggers detected by LLM.

        Raises:
            Exception: On non-retryable errors or after retry exhaustion.
        """
        if not self._agent:
            return []

        prompt = f"""Analyze this message for conflict triggers:

Message: "{context.message}"
Chapter: {context.chapter} (1=new relationship, 5=established)
Relationship score: {context.relationship_score}/100
Recent messages: {context.recent_messages[-3:] if context.recent_messages else 'none'}

Detect any triggers (dismissive, neglect, jealousy, boundary, trust).
Return JSON list of triggers or empty list if none."""

        result = await self._agent.run(prompt)
        triggers = []

        for item in result.output:
            trigger_type_str = item.get("trigger_type", "").lower()
            try:
                trigger_type = TriggerType(trigger_type_str)
            except ValueError:
                continue

            triggers.append(self._create_trigger(
                trigger_type=trigger_type,
                severity=float(item.get("severity", 0.5)),
                context={
                    "reason": "llm_detection",
                    "explanation": item.get("reason", ""),
                },
                messages=[context.message],
            ))

        return triggers

    def _create_trigger(
        self,
        trigger_type: TriggerType,
        severity: float,
        context: dict[str, Any],
        messages: list[str],
    ) -> ConflictTrigger:
        """Create a ConflictTrigger instance.

        Args:
            trigger_type: Type of trigger.
            severity: Severity score.
            context: Additional context.
            messages: Related messages.

        Returns:
            ConflictTrigger instance.
        """
        import uuid
        return ConflictTrigger(
            trigger_id=str(uuid.uuid4()),
            trigger_type=trigger_type,
            severity=severity,
            context=context,
            user_messages=messages,
        )

    def detect_sync(self, context: DetectionContext) -> DetectionResult:
        """Synchronous detection (rule-based only, no LLM).

        Useful for testing or when async is not available.

        Args:
            context: Detection context.

        Returns:
            DetectionResult with rule-based triggers only.
        """
        triggers: list[ConflictTrigger] = []

        triggers.extend(self._detect_dismissive_rules(context))
        triggers.extend(self._detect_neglect_rules(context))
        triggers.extend(self._detect_jealousy_rules(context))
        triggers.extend(self._detect_boundary_rules(context))

        # Apply chapter sensitivity
        sensitivity = self.CHAPTER_SENSITIVITY.get(context.chapter, 1.0)
        adjusted_triggers = []
        for trigger in triggers:
            adjusted_severity = min(1.0, trigger.severity * sensitivity)
            adjusted_triggers.append(ConflictTrigger(
                trigger_id=trigger.trigger_id,
                trigger_type=trigger.trigger_type,
                severity=adjusted_severity,
                detected_at=trigger.detected_at,
                context=trigger.context,
                user_messages=trigger.user_messages,
            ))

        return DetectionResult(
            triggers=adjusted_triggers,
            detection_time=datetime.now(UTC),
            context_analyzed=context,
        )
