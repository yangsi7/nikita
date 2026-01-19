"""Data models for Behavioral Meta-Instructions (Spec 024, T002).

Provides Pydantic models for meta-instructions and situation contexts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class SituationType(str, Enum):
    """Types of conversational situations.

    Priority order (highest to lowest):
    1. CONFLICT - User is in conflict state
    2. AFTER_GAP - More than 6 hours since last message
    3. MORNING - Morning greeting context (6am-11am)
    4. EVENING - Evening context (6pm-10pm)
    5. MID_CONVERSATION - Active conversation, no special situation
    """

    CONFLICT = "conflict"
    AFTER_GAP = "after_gap"
    MORNING = "morning"
    EVENING = "evening"
    MID_CONVERSATION = "mid_conversation"


class SituationCategory(str, Enum):
    """Categories for grouping instructions.

    Used for organizing and presenting instructions in the prompt.
    """

    EMOTIONAL = "emotional"  # Mood-related guidance
    CONVERSATIONAL = "conversational"  # Flow and style guidance
    RELATIONAL = "relational"  # Relationship-appropriate guidance
    TACTICAL = "tactical"  # Strategic behavior guidance


class SituationContext(BaseModel):
    """Context information for situation detection.

    Contains all information needed to detect the current situation
    and select appropriate meta-instructions.
    """

    user_id: UUID = Field(default_factory=uuid4)
    situation_type: SituationType = Field(default=SituationType.MID_CONVERSATION)
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Time-based context
    hours_since_last_message: float = Field(
        default=0.0,
        ge=0.0,
        description="Hours since user's last message",
    )
    user_local_hour: int = Field(
        default=12,
        ge=0,
        le=23,
        description="User's current local hour (0-23)",
    )

    # Relationship context
    chapter: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Current relationship chapter",
    )
    relationship_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Current relationship score",
    )

    # Emotional context (from Spec 023)
    conflict_state: str = Field(
        default="none",
        description="Current conflict state from EmotionalState",
    )

    # Engagement context (from Spec 014)
    engagement_state: str = Field(
        default="in_zone",
        description="Current engagement state",
    )

    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetaInstruction(BaseModel):
    """A single meta-instruction for behavioral guidance.

    Meta-instructions provide directional guidance without prescribing
    exact responses. They use language like "lean toward", "consider",
    "avoid" rather than "always" or "never".
    """

    instruction_id: str = Field(
        description="Unique identifier for the instruction",
    )
    situation_type: SituationType = Field(
        description="Which situation this applies to",
    )
    category: SituationCategory = Field(
        description="Category for grouping",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority (1=highest, 10=lowest)",
    )
    instruction: str = Field(
        description="The directional instruction text",
        min_length=10,
    )
    conditions: dict[str, Any] = Field(
        default_factory=dict,
        description="Conditions for when this instruction applies",
    )

    @field_validator("conditions", mode="before")
    @classmethod
    def conditions_none_to_dict(cls, v: Any) -> dict[str, Any]:
        """Convert None to empty dict for conditions field."""
        if v is None:
            return {}
        return v

    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Relative weight for selection (1.0 = normal)",
    )

    def applies_to_context(self, context: SituationContext) -> bool:
        """Check if this instruction applies to the given context.

        Evaluates conditions against the context to determine applicability.

        Args:
            context: The current situation context.

        Returns:
            True if all conditions are met, False otherwise.
        """
        if not self.conditions:
            return True

        # Check chapter conditions
        if "chapter_min" in self.conditions:
            if context.chapter < self.conditions["chapter_min"]:
                return False

        if "chapter_max" in self.conditions:
            if context.chapter > self.conditions["chapter_max"]:
                return False

        # Check relationship score conditions
        if "relationship_score_min" in self.conditions:
            if context.relationship_score < self.conditions["relationship_score_min"]:
                return False

        if "relationship_score_max" in self.conditions:
            if context.relationship_score > self.conditions["relationship_score_max"]:
                return False

        # Check conflict state conditions
        if "conflict_states" in self.conditions:
            if context.conflict_state not in self.conditions["conflict_states"]:
                return False

        # Check engagement state conditions
        if "engagement_states" in self.conditions:
            if context.engagement_state not in self.conditions["engagement_states"]:
                return False

        return True


class InstructionSet(BaseModel):
    """A collection of selected instructions for a situation.

    Groups instructions by category and provides formatting methods.
    """

    situation_type: SituationType
    context: SituationContext
    instructions: list[MetaInstruction] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def by_category(self) -> dict[SituationCategory, list[MetaInstruction]]:
        """Group instructions by category.

        Returns:
            Dictionary mapping categories to lists of instructions.
        """
        result: dict[SituationCategory, list[MetaInstruction]] = {}
        for instruction in self.instructions:
            if instruction.category not in result:
                result[instruction.category] = []
            result[instruction.category].append(instruction)
        return result

    def format_for_prompt(self) -> str:
        """Format instructions for inclusion in LLM prompt.

        Groups by category and formats as readable text.

        Returns:
            Formatted string suitable for prompt injection.
        """
        if not self.instructions:
            return ""

        lines = [
            "## Behavioral Guidance",
            "",
            f"**Current Situation**: {self.situation_type.value.replace('_', ' ').title()}",
            "",
        ]

        by_cat = self.by_category()
        for category in SituationCategory:
            if category in by_cat:
                lines.append(f"### {category.value.title()}")
                for inst in sorted(by_cat[category], key=lambda x: x.priority):
                    lines.append(f"- {inst.instruction}")
                lines.append("")

        return "\n".join(lines).strip()
