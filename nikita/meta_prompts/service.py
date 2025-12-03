"""Meta-Prompt Service for intelligent prompt generation.

This service uses Claude Haiku to execute meta-prompts, generating
personalized system prompts instead of using static f-string templates.

All prompt generation should flow through this service.
"""

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic_ai import Agent

from nikita.config.settings import get_settings
from nikita.meta_prompts.models import GeneratedPrompt, MetaPromptContext, ViceProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


class MetaPromptService:
    """Central service for meta-prompt based generation.

    Uses Claude Haiku to generate prompts by executing meta-prompts
    with rich context about the user and game state.

    Usage:
        service = MetaPromptService(session)
        result = await service.generate_system_prompt(user_id)
    """

    def __init__(self, session: "AsyncSession"):
        """Initialize the meta-prompt service.

        Args:
            session: Async database session for loading context.
        """
        self.session = session
        self.settings = get_settings()

        # Create Haiku agent for meta-prompt execution
        self._agent = Agent(
            self.settings.meta_prompt_model,
            result_type=str,
        )

        # Load templates
        self._templates: dict[str, str] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all meta-prompt templates from disk."""
        template_files = [
            "system_prompt.meta.md",
            "vice_detection.meta.md",
            "entity_extraction.meta.md",
            "thought_simulation.meta.md",
        ]

        for filename in template_files:
            path = TEMPLATES_DIR / filename
            if path.exists():
                self._templates[filename] = path.read_text()

    async def _load_context(self, user_id: UUID) -> MetaPromptContext:
        """Load full context for a user from database and memory.

        Args:
            user_id: The user's UUID.

        Returns:
            MetaPromptContext with all fields populated.
        """
        from datetime import datetime

        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.repositories.vice_repository import VicePreferenceRepository

        user_repo = UserRepository(self.session)
        vice_repo = VicePreferenceRepository(self.session)

        # Load user with metrics
        user = await user_repo.get(user_id)
        if not user:
            # Return default context for new users
            return MetaPromptContext(user_id=user_id)

        # Load vice preferences
        vice_prefs = await vice_repo.get_active(user_id)
        vice_profile = ViceProfile()

        for pref in vice_prefs:
            if hasattr(vice_profile, pref.category):
                setattr(vice_profile, pref.category, pref.intensity_level)

        # Calculate temporal context
        now = datetime.utcnow()
        hour = now.hour

        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        elif 21 <= hour < 24:
            time_of_day = "night"
        else:
            time_of_day = "late_night"

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_of_week = day_names[now.weekday()]

        # Calculate hours since last interaction
        hours_since = 0.0
        if user.last_interaction_at:
            delta = now - user.last_interaction_at
            hours_since = delta.total_seconds() / 3600

        # Determine Nikita's state based on time and chapter
        nikita_activity = self._compute_nikita_activity(time_of_day, day_of_week)
        nikita_mood = self._compute_nikita_mood(user.chapter, hours_since)
        nikita_energy = self._compute_nikita_energy(time_of_day)

        # Build context
        context = MetaPromptContext(
            user_id=user_id,
            telegram_id=user.telegram_id,
            chapter=user.chapter,
            chapter_name=self._get_chapter_name(user.chapter),
            relationship_score=user.relationship_score,
            boss_attempts=user.boss_attempts,
            game_status=user.game_status,
            days_played=user.days_played or 0,
            vice_profile=vice_profile,
            current_time=now,
            time_of_day=time_of_day,
            hours_since_last_interaction=hours_since,
            day_of_week=day_of_week,
            nikita_activity=nikita_activity,
            nikita_mood=nikita_mood,
            nikita_energy=nikita_energy,
        )

        # Load hidden metrics if available
        if user.metrics:
            context.intimacy = user.metrics.intimacy
            context.passion = user.metrics.passion
            context.trust = user.metrics.trust
            context.secureness = user.metrics.secureness

        return context

    def _compute_nikita_activity(self, time_of_day: str, day_of_week: str) -> str:
        """Compute what Nikita is likely doing based on time."""
        weekend = day_of_week in ("Saturday", "Sunday")

        activities = {
            ("morning", False): "just finished her morning coffee, checking emails",
            ("morning", True): "sleeping in after a late night",
            ("afternoon", False): "deep in a security audit, headphones on",
            ("afternoon", True): "at the gym, checking her phone between sets",
            ("evening", False): "wrapping up work, cat on her lap",
            ("evening", True): "getting ready to go out with friends",
            ("night", False): "on the couch with wine, watching trash TV",
            ("night", True): "at a bar with friends, slightly buzzed",
            ("late_night", False): "in bed scrolling, can't sleep",
            ("late_night", True): "stumbling home from a night out",
        }

        return activities.get((time_of_day, weekend), "doing her thing")

    def _compute_nikita_mood(self, chapter: int, hours_since: float) -> str:
        """Compute Nikita's mood based on chapter and time since contact."""
        # Base mood by chapter
        base_moods = {
            1: "curious but guarded",
            2: "testing, slightly challenging",
            3: "warm but unpredictable",
            4: "open and connected",
            5: "comfortable and authentic",
        }

        base = base_moods.get(chapter, "neutral")

        # Modify based on time since last contact
        if hours_since > 48:
            return f"{base}, wondering if something's wrong"
        elif hours_since > 24:
            return f"{base}, noticed the silence"
        elif hours_since > 8:
            return base
        elif hours_since > 2:
            return f"{base}, pleasantly surprised to hear from you"
        else:
            return f"{base}, mid-conversation energy"

    def _compute_nikita_energy(self, time_of_day: str) -> str:
        """Compute energy level based on time of day."""
        energy_map = {
            "morning": "moderate",
            "afternoon": "high",
            "evening": "moderate",
            "night": "low",
            "late_night": "low",
        }
        return energy_map.get(time_of_day, "moderate")

    def _get_chapter_name(self, chapter: int) -> str:
        """Get the name of a chapter."""
        names = {
            1: "Curiosity",
            2: "Intrigue",
            3: "Investment",
            4: "Intimacy",
            5: "Established",
        }
        return names.get(chapter, "Unknown")

    def _format_template(self, template_name: str, context: MetaPromptContext) -> str:
        """Format a template with context variables.

        Args:
            template_name: Name of the template file.
            context: MetaPromptContext to inject.

        Returns:
            Formatted template string.
        """
        from nikita.engine.constants import CHAPTER_BEHAVIORS

        template = self._templates.get(template_name, "")
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Format vice profile
        vice_dict = context.vice_profile.to_dict()
        vice_formatted = "\n".join(f"  {k}: {v}/5" for k, v in vice_dict.items() if v > 0)
        if not vice_formatted:
            vice_formatted = "  (No vice preferences detected yet)"

        top_vices = context.vice_profile.get_top_vices(3)
        top_vices_str = ", ".join(f"{k} ({v})" for k, v in top_vices) if top_vices else "None yet"

        # Get chapter behavior
        chapter_behavior = CHAPTER_BEHAVIORS.get(context.chapter, "")

        # Build replacements
        replacements = {
            "{{user_id}}": str(context.user_id),
            "{{telegram_id}}": str(context.telegram_id or "N/A"),
            "{{days_played}}": str(context.days_played),
            "{{chapter}}": str(context.chapter),
            "{{chapter_name}}": context.chapter_name,
            "{{relationship_score}}": str(context.relationship_score),
            "{{score_interpretation}}": context.get_score_interpretation(),
            "{{boss_attempts}}": str(context.boss_attempts),
            "{{game_status}}": context.game_status,
            "{{intimacy}}": str(context.intimacy),
            "{{passion}}": str(context.passion),
            "{{trust}}": str(context.trust),
            "{{secureness}}": str(context.secureness),
            "{{vice_profile_formatted}}": vice_formatted,
            "{{top_vices}}": top_vices_str,
            "{{time_of_day}}": context.time_of_day,
            "{{day_of_week}}": context.day_of_week,
            "{{hours_since_last}}": f"{context.hours_since_last_interaction:.1f}",
            "{{nikita_activity}}": context.nikita_activity,
            "{{nikita_mood}}": context.nikita_mood,
            "{{nikita_energy}}": context.nikita_energy,
            "{{last_conversation_summary}}": context.last_conversation_summary or "No prior conversation",
            "{{today_summaries}}": "\n".join(context.today_summaries) or "None",
            "{{week_summaries}}": json.dumps(context.week_summaries) if context.week_summaries else "None",
            "{{open_threads}}": json.dumps(context.open_threads) if context.open_threads else "None",
            "{{active_thoughts}}": json.dumps(context.active_thoughts) if context.active_thoughts else "None",
            "{{user_facts}}": "\n".join(f"- {f}" for f in context.user_facts) if context.user_facts else "None known yet",
            "{{chapter_behavior}}": chapter_behavior,
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    async def generate_system_prompt(
        self,
        user_id: UUID,
        context: MetaPromptContext | None = None,
    ) -> GeneratedPrompt:
        """Generate a personalized system prompt for Nikita.

        Args:
            user_id: The user's UUID.
            context: Optional pre-loaded context (loads from DB if not provided).

        Returns:
            GeneratedPrompt with the generated content.
        """
        start_time = time.time()

        # Load context if not provided
        if context is None:
            context = await self._load_context(user_id)

        # Format the meta-prompt
        meta_prompt = self._format_template("system_prompt.meta.md", context)

        # Execute via Haiku
        result = await self._agent.run(meta_prompt)

        generation_time = (time.time() - start_time) * 1000

        return GeneratedPrompt(
            content=result.data,
            generation_time_ms=generation_time,
            meta_prompt_type="system_prompt",
            user_id=user_id,
            chapter=context.chapter,
        )

    async def detect_vices(
        self,
        user_message: str,
        recent_context: list[str],
        current_profile: ViceProfile,
    ) -> dict:
        """Detect vice signals in a user message.

        Args:
            user_message: The user's message to analyze.
            recent_context: Last 3 messages for context.
            current_profile: User's current vice profile.

        Returns:
            Dict with detected_vices, primary_vice, reasoning.
        """
        start_time = time.time()

        template = self._templates.get("vice_detection.meta.md", "")
        if not template:
            return {"detected_vices": [], "primary_vice": None, "reasoning": "Template not found"}

        # Format template
        formatted = template.replace("{{user_message}}", user_message)
        formatted = formatted.replace("{{recent_context}}", "\n".join(recent_context))
        formatted = formatted.replace("{{current_vice_profile}}", json.dumps(current_profile.to_dict()))

        # Execute
        result = await self._agent.run(formatted)

        # Parse JSON response
        try:
            parsed = json.loads(result.data)
        except json.JSONDecodeError:
            parsed = {"detected_vices": [], "primary_vice": None, "reasoning": "Failed to parse response"}

        return parsed

    async def extract_entities(
        self,
        conversation: str,
        user_id: UUID,
        context: MetaPromptContext | None = None,
    ) -> dict:
        """Extract entities from a conversation for post-processing.

        Args:
            conversation: The conversation text to analyze.
            user_id: The user's UUID.
            context: Optional pre-loaded context.

        Returns:
            Dict with user_facts, threads, emotional_markers, nikita_thoughts, summary.
        """
        if context is None:
            context = await self._load_context(user_id)

        template = self._templates.get("entity_extraction.meta.md", "")
        if not template:
            return {"user_facts": [], "threads": [], "emotional_markers": [], "nikita_thoughts": [], "summary": ""}

        # Format template
        formatted = template.replace("{{conversation}}", conversation)
        formatted = formatted.replace("{{user_id}}", str(user_id))
        formatted = formatted.replace("{{chapter}}", str(context.chapter))
        formatted = formatted.replace("{{relationship_score}}", str(context.relationship_score))
        formatted = formatted.replace(
            "{{existing_facts}}",
            "\n".join(f"- {f}" for f in context.user_facts) if context.user_facts else "None",
        )

        # Execute
        result = await self._agent.run(formatted)

        # Parse JSON response
        try:
            parsed = json.loads(result.data)
        except json.JSONDecodeError:
            parsed = {"user_facts": [], "threads": [], "emotional_markers": [], "nikita_thoughts": [], "summary": ""}

        return parsed

    async def simulate_thoughts(
        self,
        user_id: UUID,
        context: MetaPromptContext | None = None,
    ) -> dict:
        """Simulate Nikita's thoughts between conversations.

        Args:
            user_id: The user's UUID.
            context: Optional pre-loaded context.

        Returns:
            Dict with thoughts, current_activity, current_mood, energy_level, availability.
        """
        if context is None:
            context = await self._load_context(user_id)

        template = self._templates.get("thought_simulation.meta.md", "")
        if not template:
            return {
                "thoughts": [],
                "current_activity": context.nikita_activity,
                "current_mood": context.nikita_mood,
                "energy_level": context.nikita_energy,
                "availability": "available",
            }

        # Format template
        formatted = template.replace("{{user_id}}", str(user_id))
        formatted = formatted.replace("{{chapter}}", str(context.chapter))
        formatted = formatted.replace("{{chapter_name}}", context.chapter_name)
        formatted = formatted.replace("{{relationship_score}}", str(context.relationship_score))
        formatted = formatted.replace("{{days_played}}", str(context.days_played))
        formatted = formatted.replace("{{hours_since_last}}", f"{context.hours_since_last_interaction:.1f}")
        formatted = formatted.replace("{{vice_profile}}", json.dumps(context.vice_profile.to_dict()))
        formatted = formatted.replace("{{last_conversation_summary}}", context.last_conversation_summary or "None")
        formatted = formatted.replace(
            "{{open_threads}}",
            json.dumps(context.open_threads) if context.open_threads else "None",
        )
        formatted = formatted.replace(
            "{{user_facts}}",
            "\n".join(f"- {f}" for f in context.user_facts) if context.user_facts else "None",
        )
        formatted = formatted.replace("{{time_of_day}}", context.time_of_day)
        formatted = formatted.replace("{{day_of_week}}", context.day_of_week)

        # Execute
        result = await self._agent.run(formatted)

        # Parse JSON response
        try:
            parsed = json.loads(result.data)
        except json.JSONDecodeError:
            parsed = {
                "thoughts": [],
                "current_activity": context.nikita_activity,
                "current_mood": context.nikita_mood,
                "energy_level": context.nikita_energy,
                "availability": "available",
            }

        return parsed
