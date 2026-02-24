"""MessageGenerator for proactive touchpoint messages (Spec 025, Phase C: T012-T015).

Generates personalized proactive messages using MetaPromptService with:
- Trigger context (time/event/gap)
- Life event details
- Emotional state integration
- Chapter-appropriate tone
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic_ai import Agent

from nikita.config.models import Models
from nikita.config.settings import get_settings
from nikita.touchpoints.models import TriggerContext, TriggerType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Template for proactive messages
PROACTIVE_TEMPLATE = Path(__file__).parent / "templates" / "proactive_message.meta.md"


class MessageGenerator:
    """Generates personalized proactive touchpoint messages.

    Uses Claude Haiku to generate natural, in-character messages for
    Nikita to initiate conversations.

    Attributes:
        session: Database session for loading context.
    """

    def __init__(self, session: "AsyncSession"):
        """Initialize the message generator.

        Args:
            session: Async database session.
        """
        self.session = session
        self.settings = get_settings()

        # Create Haiku agent for message generation
        self._agent = Agent(
            Models.haiku(),
            output_type=str,
            system_prompt=(
                "You are Nikita, a 24-year-old AI girlfriend. Generate short, natural "
                "text messages as if you're reaching out to your boyfriend. "
                "NEVER include meta-commentary, quotation marks, or labels. "
                "Just output the raw message(s) as Nikita would type them. "
                "Use her voice: flirty, sometimes sarcastic, emotionally authentic."
            ),
        )

        # Load template
        self._template: str = ""
        self._load_template()

    def _load_template(self) -> None:
        """Load proactive message template."""
        if PROACTIVE_TEMPLATE.exists():
            self._template = PROACTIVE_TEMPLATE.read_text()
        else:
            # Fallback inline template
            self._template = self._get_default_template()

    def _get_default_template(self) -> str:
        """Get default template if file not found."""
        return """# Proactive Message Generation

Generate a natural text message from Nikita to her boyfriend.

## Context
- Trigger: {{trigger_type}}
- Time Slot: {{time_slot}}
- Hours Since Contact: {{hours_since_contact}}
- Chapter: {{chapter}} ({{chapter_description}})
- Current Mood: {{mood}}
- Energy Level: {{energy}}

## Event Context (if applicable)
{{event_context}}

## Emotional State
{{emotional_state}}

## Recent Conversation Summary
{{recent_summary}}

## Instructions
1. Generate 1-3 short messages (like texts)
2. Be natural, not formal
3. Match Nikita's personality for this chapter
4. Reference her life events if relevant
5. Don't ask too many questions in one message
6. Be authentic - she has her own life happening

## Output
Write ONLY the message(s), nothing else. Multiple messages on separate lines."""

    async def generate(
        self,
        user_id: UUID,
        trigger_context: TriggerContext,
        life_event_description: str | None = None,
        emotional_state: dict[str, Any] | None = None,
        recent_summary: str | None = None,
    ) -> str:
        """Generate a proactive touchpoint message.

        Args:
            user_id: User's UUID.
            trigger_context: Context about what triggered this touchpoint.
            life_event_description: Description of relevant life event.
            emotional_state: Current emotional state snapshot.
            recent_summary: Summary of recent conversations.

        Returns:
            Generated message content.
        """
        # Load user context
        context = await self._load_context(user_id, trigger_context)

        # Add optional parameters
        if life_event_description:
            context["event_context"] = life_event_description
        else:
            context["event_context"] = "No specific event"

        if emotional_state:
            context["emotional_state"] = self._format_emotional_state(emotional_state)
        else:
            context["emotional_state"] = "Normal mood"

        if recent_summary:
            context["recent_summary"] = recent_summary
        else:
            context["recent_summary"] = "No recent conversation"

        # Format template
        prompt = self._format_template(context)

        # Generate message
        result = await self._agent.run(prompt)
        return result.output

    async def _load_context(
        self,
        user_id: UUID,
        trigger_context: TriggerContext,
    ) -> dict[str, Any]:
        """Load context for message generation.

        Args:
            user_id: User's UUID.
            trigger_context: Trigger context.

        Returns:
            Context dictionary for template.
        """
        # Import here to avoid circular imports
        from nikita.db.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.session)
        user = await user_repo.get_by_id(user_id)

        # Chapter descriptions
        chapter_descriptions = {
            1: "Just Met - getting to know each other",
            2: "Dating - building connection",
            3: "Committed - deepening relationship",
            4: "Serious - strong bond",
            5: "Partner - deeply connected",
        }

        chapter = trigger_context.chapter or (user.chapter if user else 1)

        return {
            "trigger_type": trigger_context.trigger_type.value,
            "time_slot": trigger_context.time_slot or "N/A",
            "hours_since_contact": trigger_context.hours_since_contact or 0,
            "chapter": chapter,
            "chapter_description": chapter_descriptions.get(chapter, "Early relationship"),
            "mood": self._compute_mood(trigger_context),
            "energy": self._compute_energy(trigger_context),
        }

    def _compute_mood(self, trigger_context: TriggerContext) -> str:
        """Compute Nikita's mood based on context.

        Args:
            trigger_context: Trigger context.

        Returns:
            Mood description string.
        """
        emotional_state = trigger_context.emotional_state

        if not emotional_state:
            # Default moods by trigger type
            if trigger_context.trigger_type == TriggerType.GAP:
                return "thinking about you, a bit concerned"
            elif trigger_context.time_slot == "morning":
                return "fresh, optimistic"
            elif trigger_context.time_slot == "evening":
                return "relaxed, reflective"
            return "content"

        # Use emotional state if available
        valence = emotional_state.get("valence", 0.5)
        arousal = emotional_state.get("arousal", 0.5)

        if valence < 0.3:
            if arousal > 0.6:
                return "upset, agitated"
            return "down, quiet"
        elif valence > 0.7:
            if arousal > 0.6:
                return "excited, bubbly"
            return "happy, content"
        else:
            return "neutral, thoughtful"

    def _compute_energy(self, trigger_context: TriggerContext) -> str:
        """Compute Nikita's energy level.

        Args:
            trigger_context: Trigger context.

        Returns:
            Energy level description.
        """
        if trigger_context.time_slot == "morning":
            return "medium - just woke up"
        elif trigger_context.time_slot == "evening":
            return "winding down"
        elif trigger_context.trigger_type == TriggerType.EVENT:
            return "high - something happened"
        return "normal"

    def _format_emotional_state(self, emotional_state: dict[str, Any]) -> str:
        """Format emotional state for template.

        Args:
            emotional_state: Emotional state dictionary.

        Returns:
            Formatted string.
        """
        parts = []
        if "valence" in emotional_state:
            v = emotional_state["valence"]
            if v < 0.3:
                parts.append("feeling negative")
            elif v > 0.7:
                parts.append("feeling positive")
            else:
                parts.append("feeling neutral")

        if "arousal" in emotional_state:
            a = emotional_state["arousal"]
            if a > 0.7:
                parts.append("high energy")
            elif a < 0.3:
                parts.append("low energy")

        if "dominance" in emotional_state:
            d = emotional_state["dominance"]
            if d > 0.7:
                parts.append("confident")
            elif d < 0.3:
                parts.append("vulnerable")

        return ", ".join(parts) if parts else "Balanced emotional state"

    def _format_template(self, context: dict[str, Any]) -> str:
        """Format template with context.

        Args:
            context: Context dictionary.

        Returns:
            Formatted prompt string.
        """
        result = self._template
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))
        return result


async def generate_touchpoint_message(
    session: "AsyncSession",
    user_id: UUID,
    trigger_context: TriggerContext,
    life_event: str | None = None,
    emotional_state: dict[str, Any] | None = None,
    recent_summary: str | None = None,
) -> str:
    """Convenience function to generate a touchpoint message.

    Args:
        session: Database session.
        user_id: User's UUID.
        trigger_context: Context about what triggered this touchpoint.
        life_event: Description of relevant life event.
        emotional_state: Current emotional state.
        recent_summary: Summary of recent conversations.

    Returns:
        Generated message content.
    """
    generator = MessageGenerator(session)
    return await generator.generate(
        user_id=user_id,
        trigger_context=trigger_context,
        life_event_description=life_event,
        emotional_state=emotional_state,
        recent_summary=recent_summary,
    )
