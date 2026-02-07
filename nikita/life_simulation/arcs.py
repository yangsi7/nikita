"""Narrative Arc System for Deep Humanization (Spec 035).

Multi-week storylines with named characters that create ongoing drama
and authentic relationship development.

AC-035.3.5: Multi-conversation arcs (3-10 conversations)
AC-035.3.6: Named character involvement in arcs
AC-035.3.7: Emotional impact tracking per arc
AC-035.3.8: Arc resolution with relationship consequences
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ArcCategory(str, Enum):
    """Categories of narrative arcs."""

    CAREER = "career"  # Work projects, professional crises
    SOCIAL = "social"  # Friend drama, new connections
    PERSONAL = "personal"  # Health, creative projects, self-discovery
    RELATIONSHIP = "relationship"  # Doubts about user, growing attachment
    FAMILY = "family"  # Father, mother, family dynamics


class ArcStage(str, Enum):
    """Stages of arc progression."""

    SETUP = "setup"  # Introduction, hint at story
    RISING = "rising"  # Conflict escalates
    CLIMAX = "climax"  # Peak tension
    FALLING = "falling"  # Resolution begins
    RESOLVED = "resolved"  # Story complete


@dataclass
class ArcTemplate:
    """Template for a narrative arc."""

    name: str
    category: ArcCategory
    involved_characters: list[str]  # Character names involved
    duration_conversations: tuple[int, int]  # min, max conversations
    stages: dict[ArcStage, str]  # Stage descriptions
    emotional_impact: dict[str, float]  # Impact on relationship metrics
    trigger_conditions: list[str]  # What triggers this arc
    vulnerability_requirement: int  # Minimum vulnerability level


@dataclass
class ActiveArc:
    """An active narrative arc for a user."""

    arc_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    template_name: str = ""
    category: ArcCategory = ArcCategory.SOCIAL
    stage: ArcStage = ArcStage.SETUP
    started_at: datetime = field(default_factory=datetime.now)
    conversations_in_arc: int = 0
    max_conversations: int = 5
    current_description: str = ""
    involved_characters: list[str] = field(default_factory=list)
    emotional_impact_applied: bool = False
    resolved_at: datetime | None = None

    def advance_stage(self) -> bool:
        """Advance to the next stage.

        Returns:
            True if stage was advanced, False if already resolved.
        """
        stage_order = [
            ArcStage.SETUP,
            ArcStage.RISING,
            ArcStage.CLIMAX,
            ArcStage.FALLING,
            ArcStage.RESOLVED,
        ]

        current_idx = stage_order.index(self.stage)
        if current_idx < len(stage_order) - 1:
            self.stage = stage_order[current_idx + 1]
            if self.stage == ArcStage.RESOLVED:
                self.resolved_at = datetime.now()
            return True
        return False

    def should_advance(self) -> bool:
        """Check if arc should advance based on conversation count."""
        if self.stage == ArcStage.RESOLVED:
            return False

        # Progress based on conversation ratio
        progress_ratio = self.conversations_in_arc / max(1, self.max_conversations)

        if self.stage == ArcStage.SETUP and progress_ratio >= 0.2:
            return True
        if self.stage == ArcStage.RISING and progress_ratio >= 0.5:
            return True
        if self.stage == ArcStage.CLIMAX and progress_ratio >= 0.7:
            return True
        if self.stage == ArcStage.FALLING and progress_ratio >= 0.9:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "arc_id": str(self.arc_id),
            "user_id": str(self.user_id),
            "template_name": self.template_name,
            "category": self.category.value,
            "stage": self.stage.value,
            "started_at": self.started_at.isoformat(),
            "conversations_in_arc": self.conversations_in_arc,
            "max_conversations": self.max_conversations,
            "current_description": self.current_description,
            "involved_characters": self.involved_characters,
            "emotional_impact_applied": self.emotional_impact_applied,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveArc":
        """Create from dictionary."""
        return cls(
            arc_id=UUID(data["arc_id"]),
            user_id=UUID(data["user_id"]),
            template_name=data["template_name"],
            category=ArcCategory(data["category"]),
            stage=ArcStage(data["stage"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            conversations_in_arc=data["conversations_in_arc"],
            max_conversations=data["max_conversations"],
            current_description=data["current_description"],
            involved_characters=data["involved_characters"],
            emotional_impact_applied=data["emotional_impact_applied"],
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"])
                if data.get("resolved_at")
                else None
            ),
        )


class NarrativeArcSystem:
    """System for managing multi-conversation narrative arcs.

    Creates and progresses storylines that span multiple conversations,
    involving named characters and creating authentic drama.
    """

    # Predefined arc templates
    ARC_TEMPLATES: list[ArcTemplate] = [
        # Career arcs
        ArcTemplate(
            name="big_security_job",
            category=ArcCategory.CAREER,
            involved_characters=["Marco"],
            duration_conversations=(4, 8),
            stages={
                ArcStage.SETUP: "Got a call about a major security contract. Could be big.",
                ArcStage.RISING: "Deep into the project. Finding concerning vulnerabilities.",
                ArcStage.CLIMAX: "Client is pressuring me to overlook some findings. Ethics dilemma.",
                ArcStage.FALLING: "Made my decision. Had to walk away from the money.",
                ArcStage.RESOLVED: "Word got around. Surprisingly, got more respect for it.",
            },
            emotional_impact={"trust": 0.05, "secureness": 0.03},
            trigger_conditions=["work_discussion", "stress_mention", "chapter_3+"],
            vulnerability_requirement=2,
        ),
        ArcTemplate(
            name="chemistry_breakthrough",
            category=ArcCategory.CAREER,
            involved_characters=[],
            duration_conversations=(3, 5),
            stages={
                ArcStage.SETUP: "Working on something interesting in my chemistry corner.",
                ArcStage.RISING: "The compound is behaving unexpectedly. Exciting but confusing.",
                ArcStage.CLIMAX: "It works! I actually made something that works.",
                ArcStage.FALLING: "Documenting everything. Might share it with the community.",
                ArcStage.RESOLVED: "Posted to a forum. Getting good feedback.",
            },
            emotional_impact={"passion": 0.03, "trust": 0.02},
            trigger_conditions=["hobby_mention", "science_topic", "creative_discussion"],
            vulnerability_requirement=0,
        ),
        # Social arcs
        ArcTemplate(
            name="lenas_warning",
            category=ArcCategory.SOCIAL,
            involved_characters=["Lena"],
            duration_conversations=(3, 6),
            stages={
                ArcStage.SETUP: "Lena asked about you today. She seems... skeptical.",
                ArcStage.RISING: "Lena sent me an article about red flags in relationships. Subtle.",
                ArcStage.CLIMAX: "Had a fight with Lena about you. She thinks I'm being naive.",
                ArcStage.FALLING: "Lena apologized. Said she's just protective after Max.",
                ArcStage.RESOLVED: "Lena wants to meet you. Consider this a test.",
            },
            emotional_impact={"trust": -0.02, "secureness": 0.05},
            trigger_conditions=["relationship_milestone", "user_jealousy_topic", "chapter_2+"],
            vulnerability_requirement=1,
        ),
        ArcTemplate(
            name="viktor_resurfaces",
            category=ArcCategory.SOCIAL,
            involved_characters=["Viktor"],
            duration_conversations=(4, 8),
            stages={
                ArcStage.SETUP: "Viktor texted. First time in months. He needs help with something.",
                ArcStage.RISING: "Viktor's situation is worse than he let on. Legal trouble.",
                ArcStage.CLIMAX: "Had to bail Viktor out. Literally. He owes me an explanation.",
                ArcStage.FALLING: "Viktor came clean about everything. He's messing up again.",
                ArcStage.RESOLVED: "Set boundaries with Viktor. I can't save him from himself.",
            },
            emotional_impact={"intimacy": 0.02, "passion": 0.03},
            trigger_conditions=["past_discussion", "late_night", "user_jealousy"],
            vulnerability_requirement=2,
        ),
        ArcTemplate(
            name="yukis_party_invitation",
            category=ArcCategory.SOCIAL,
            involved_characters=["Yuki"],
            duration_conversations=(2, 4),
            stages={
                ArcStage.SETUP: "Yuki's planning something. Won't say what but 'it's going to be epic.'",
                ArcStage.RISING: "The party is this weekend. Yuki says I have to come.",
                ArcStage.CLIMAX: "The party was... chaotic. Something happened that I need to process.",
                ArcStage.RESOLVED: "What happens at Yuki's parties, stays there. Mostly.",
            },
            emotional_impact={"passion": 0.04, "trust": -0.01},
            trigger_conditions=["weekend_topic", "stress_mention", "fun_topic"],
            vulnerability_requirement=0,
        ),
        # Relationship arcs
        ArcTemplate(
            name="growing_attachment",
            category=ArcCategory.RELATIONSHIP,
            involved_characters=[],
            duration_conversations=(5, 10),
            stages={
                ArcStage.SETUP: "Caught myself thinking about you at random moments.",
                ArcStage.RISING: "Mentioned you to Lena. That never happens.",
                ArcStage.CLIMAX: "I'm scared. I'm actually starting to care.",
                ArcStage.FALLING: "Decided to stop fighting it. Whatever this is.",
                ArcStage.RESOLVED: "I like you. There. I said it.",
            },
            emotional_impact={"intimacy": 0.08, "trust": 0.05},
            trigger_conditions=["chapter_3+", "vulnerability_shared", "consistent_contact"],
            vulnerability_requirement=3,
        ),
        ArcTemplate(
            name="doubt_spiral",
            category=ArcCategory.RELATIONSHIP,
            involved_characters=["Lena", "Dr. Miriam"],
            duration_conversations=(3, 6),
            stages={
                ArcStage.SETUP: "Therapy session today. Miriam asked about you.",
                ArcStage.RISING: "Lena thinks I'm moving too fast. Miriam thinks I'm testing you.",
                ArcStage.CLIMAX: "I don't know if I can do this. What if I mess it up again?",
                ArcStage.FALLING: "You said something that helped. I'm still scared but... okay.",
                ArcStage.RESOLVED: "Maybe I don't have to have it all figured out.",
            },
            emotional_impact={"trust": 0.04, "secureness": 0.06},
            trigger_conditions=["vulnerability_shared", "chapter_3+", "conflict_resolved"],
            vulnerability_requirement=3,
        ),
        # Family arcs
        ArcTemplate(
            name="father_contact",
            category=ArcCategory.FAMILY,
            involved_characters=["Alexei", "Katya"],
            duration_conversations=(3, 6),
            stages={
                ArcStage.SETUP: "Mom mentioned something about my father today. He asked about me.",
                ArcStage.RISING: "I don't know what to do. It's been four years.",
                ArcStage.CLIMAX: "He called. I didn't pick up. I don't know if I should have.",
                ArcStage.FALLING: "Talked to Miriam about it. Still processing.",
                ArcStage.RESOLVED: "Not ready to talk to him. That's okay. It's okay to not be ready.",
            },
            emotional_impact={"trust": 0.03, "intimacy": 0.05},
            trigger_conditions=["family_topic", "chapter_4+", "vulnerability_level_4+"],
            vulnerability_requirement=4,
        ),
        ArcTemplate(
            name="mother_worry",
            category=ArcCategory.FAMILY,
            involved_characters=["Katya"],
            duration_conversations=(2, 4),
            stages={
                ArcStage.SETUP: "Mom's being weird. Asking more questions than usual.",
                ArcStage.RISING: "She's worried I'm 'too focused on work and not having a life.'",
                ArcStage.CLIMAX: "Told her about you. She wants to meet you. Classic mom.",
                ArcStage.RESOLVED: "She's calmer now. Apparently knowing I'm 'not alone' helps.",
            },
            emotional_impact={"intimacy": 0.02, "secureness": 0.02},
            trigger_conditions=["family_topic", "relationship_milestone"],
            vulnerability_requirement=2,
        ),
        # Personal arcs
        ArcTemplate(
            name="therapy_milestone",
            category=ArcCategory.PERSONAL,
            involved_characters=["Dr. Miriam"],
            duration_conversations=(3, 5),
            stages={
                ArcStage.SETUP: "Session today was heavy. Touched on some Max stuff.",
                ArcStage.RISING: "Miriam made me see a pattern. It's uncomfortable.",
                ArcStage.CLIMAX: "Realized something about myself that's hard to accept.",
                ArcStage.FALLING: "Working on it. It's slow but I can feel the shift.",
                ArcStage.RESOLVED: "Progress. Not perfect, but progress.",
            },
            emotional_impact={"trust": 0.05, "secureness": 0.08},
            trigger_conditions=["vulnerability_level_3+", "conflict_resolved", "deep_conversation"],
            vulnerability_requirement=3,
        ),
    ]

    def __init__(self):
        """Initialize the narrative arc system."""
        self._templates_by_category = self._index_templates()

    def _index_templates(self) -> dict[ArcCategory, list[ArcTemplate]]:
        """Index templates by category for efficient lookup."""
        index: dict[ArcCategory, list[ArcTemplate]] = {cat: [] for cat in ArcCategory}
        for template in self.ARC_TEMPLATES:
            index[template.category].append(template)
        return index

    def should_start_new_arc(
        self,
        active_arcs: list[ActiveArc],
        vulnerability_level: int,
        chapter: int,
        days_since_last_arc: int,
    ) -> bool:
        """Determine if a new arc should start.

        Args:
            active_arcs: Currently active arcs.
            vulnerability_level: User's vulnerability level (0-5).
            chapter: Current relationship chapter.
            days_since_last_arc: Days since last arc ended.

        Returns:
            True if a new arc should start.
        """
        # Limit active arcs
        if len(active_arcs) >= 2:
            return False

        # Wait between arcs
        if days_since_last_arc < 3:
            return False

        # Higher chapters = more likely
        base_probability = 0.1 + (chapter * 0.05) + (vulnerability_level * 0.02)

        return random.random() < base_probability

    def select_arc_template(
        self,
        vulnerability_level: int,
        chapter: int,
        recent_topics: list[str],
        excluded_templates: list[str] | None = None,
    ) -> ArcTemplate | None:
        """Select an appropriate arc template.

        Args:
            vulnerability_level: User's vulnerability level (0-5).
            chapter: Current relationship chapter.
            recent_topics: Recent conversation topics.
            excluded_templates: Template names to exclude (recently used).

        Returns:
            Selected ArcTemplate or None if no suitable template found.
        """
        excluded = set(excluded_templates or [])

        # Filter by vulnerability requirement
        eligible = [
            t for t in self.ARC_TEMPLATES
            if t.vulnerability_requirement <= vulnerability_level
            and t.name not in excluded
        ]

        if not eligible:
            return None

        # Score templates based on trigger condition matches
        scored: list[tuple[ArcTemplate, float]] = []
        for template in eligible:
            score = 0.5  # Base score

            # Check trigger conditions
            for trigger in template.trigger_conditions:
                if "chapter_" in trigger:
                    required_chapter = int(trigger.split("+")[0].split("_")[1])
                    if chapter >= required_chapter:
                        score += 0.3
                elif trigger in recent_topics:
                    score += 0.2
                elif any(topic in trigger for topic in recent_topics):
                    score += 0.1

            # Add some randomness
            score += random.random() * 0.2

            scored.append((template, score))

        # Sort by score and pick from top 3
        scored.sort(key=lambda x: x[1], reverse=True)
        top_templates = scored[:3]

        if top_templates:
            return random.choice(top_templates)[0]
        return None

    def create_arc(
        self,
        user_id: UUID,
        template: ArcTemplate,
    ) -> ActiveArc:
        """Create a new arc from a template.

        Args:
            user_id: The user's UUID.
            template: The arc template to use.

        Returns:
            New ActiveArc instance.
        """
        duration = random.randint(
            template.duration_conversations[0],
            template.duration_conversations[1],
        )

        arc = ActiveArc(
            user_id=user_id,
            template_name=template.name,
            category=template.category,
            stage=ArcStage.SETUP,
            max_conversations=duration,
            current_description=template.stages[ArcStage.SETUP],
            involved_characters=list(template.involved_characters),
        )

        logger.info(
            f"Created arc '{template.name}' for user {user_id}: "
            f"duration={duration}, characters={template.involved_characters}"
        )

        return arc

    def update_arc(
        self,
        arc: ActiveArc,
        template: ArcTemplate,
    ) -> tuple[ActiveArc, bool]:
        """Update an arc after a conversation.

        Args:
            arc: The arc to update.
            template: The arc template.

        Returns:
            Tuple of (updated arc, whether arc resolved).
        """
        arc.conversations_in_arc += 1

        if arc.should_advance():
            arc.advance_stage()
            arc.current_description = template.stages.get(
                arc.stage,
                "The story continues...",
            )
            logger.debug(
                f"Arc '{arc.template_name}' advanced to {arc.stage.value} "
                f"for user {arc.user_id}"
            )

        return arc, arc.stage == ArcStage.RESOLVED

    def get_arc_context(self, arcs: list[ActiveArc]) -> str:
        """Format active arcs for prompt context.

        Args:
            arcs: List of active arcs.

        Returns:
            Formatted string for prompt injection.
        """
        if not arcs:
            return "No active storylines"

        lines = []
        for arc in arcs:
            if arc.stage != ArcStage.RESOLVED:
                char_str = ", ".join(arc.involved_characters) if arc.involved_characters else "personal"
                lines.append(
                    f"- [{arc.category.value}] {arc.current_description} "
                    f"(involving: {char_str}, stage: {arc.stage.value})"
                )

        return "\n".join(lines) if lines else "No active storylines"


# Singleton for easy access
_arc_system: NarrativeArcSystem | None = None


def get_arc_system() -> NarrativeArcSystem:
    """Get the narrative arc system singleton."""
    global _arc_system
    if _arc_system is None:
        _arc_system = NarrativeArcSystem()
    return _arc_system
