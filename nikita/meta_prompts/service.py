"""Meta-Prompt Service for intelligent prompt generation.

This service uses Claude Haiku to execute meta-prompts, generating
personalized system prompts instead of using static f-string templates.

All prompt generation should flow through this service.
"""

import json
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic_ai import Agent

from nikita.config.settings import get_settings
from nikita.meta_prompts.models import GeneratedPrompt, MetaPromptContext, ViceProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from nikita.db.repositories.generated_prompt_repository import GeneratedPromptRepository

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
            output_type=str,
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

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a text string using tiktoken.

        Uses cl100k_base encoding for accurate token counting.
        Falls back to character estimation if tiktoken unavailable.

        Args:
            text: The text to count tokens for.

        Returns:
            Token count.
        """
        from nikita.context.utils.token_counter import count_tokens

        return count_tokens(text)

    async def _log_prompt(
        self,
        user_id: UUID,
        prompt_content: str,
        generation_time_ms: float,
        meta_prompt_template: str,
        conversation_id: UUID | None = None,
        context_snapshot: dict[str, Any] | None = None,
    ) -> None:
        """Log generated prompt to database.

        Args:
            user_id: The user's UUID.
            prompt_content: The generated prompt text.
            generation_time_ms: Time taken to generate in milliseconds.
            meta_prompt_template: Template used for generation.
            conversation_id: Optional conversation UUID.
            context_snapshot: Optional context data.
        """
        from nikita.db.repositories.generated_prompt_repository import GeneratedPromptRepository

        repo = GeneratedPromptRepository(self.session)
        await repo.create_log(
            user_id=user_id,
            prompt_content=prompt_content,
            token_count=self._count_tokens(prompt_content),
            generation_time_ms=generation_time_ms,
            meta_prompt_template=meta_prompt_template,
            conversation_id=conversation_id,
            context_snapshot=context_snapshot,
        )

    async def _load_context(self, user_id: UUID) -> MetaPromptContext:
        """Load full context for a user from database and memory.

        Spec 012 Phase 4: Now includes profile and backstory loading
        for personalized prompt generation.

        Args:
            user_id: The user's UUID.

        Returns:
            MetaPromptContext with all fields populated.
        """
        from datetime import datetime

        from nikita.db.repositories.user_repository import UserRepository
        from nikita.db.repositories.vice_repository import VicePreferenceRepository
        from nikita.db.repositories.profile_repository import (
            ProfileRepository,
            BackstoryRepository,
        )
        from nikita.meta_prompts.models import BackstoryContext

        user_repo = UserRepository(self.session)
        vice_repo = VicePreferenceRepository(self.session)
        profile_repo = ProfileRepository(self.session)
        backstory_repo = BackstoryRepository(self.session)

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

        # Load engagement state (spec 014)
        engagement_state = "calibrating"
        calibration_score = Decimal("0.50")
        engagement_multiplier = Decimal("0.90")
        if user.engagement_state:
            engagement_state = user.engagement_state.state
            calibration_score = user.engagement_state.calibration_score
            engagement_multiplier = user.engagement_state.multiplier

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
            engagement_state=engagement_state,
            calibration_score=calibration_score,
            engagement_multiplier=engagement_multiplier,
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

        # Spec 012: Load profile and backstory for personalization
        try:
            profile = await profile_repo.get_by_user_id(user_id)
            backstory = await backstory_repo.get_by_user_id(user_id)

            if backstory:
                context.backstory = BackstoryContext.from_model(backstory)
                import logging
                logging.getLogger(__name__).debug(
                    f"Loaded backstory for user {user_id}: {context.backstory.venue}"
                )
        except Exception as e:
            # Graceful degradation: continue without profile/backstory
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to load profile/backstory for user {user_id}: {e}"
            )

        # FR-013, FR-014: Load memory from Graphiti, threads, thoughts, summaries
        await self._load_memory_context(user_id, context)

        return context

    async def _load_memory_context(
        self,
        user_id: UUID,
        context: MetaPromptContext,
    ) -> None:
        """Load memory context from Graphiti, threads, thoughts, and summaries.

        FR-013: Graphiti Memory Loading - user_facts from knowledge graph
        FR-014: Conversation Summaries - today/week summaries

        This method populates:
        - context.user_facts from Graphiti
        - context.open_threads from ThreadRepository
        - context.active_thoughts from ThoughtRepository
        - context.today_summaries from DailySummaryRepository
        - context.week_summaries from DailySummaryRepository

        Args:
            user_id: The user's UUID.
            context: MetaPromptContext to populate with memory.
        """
        import logging
        from datetime import timedelta

        from nikita.db.repositories.thread_repository import ConversationThreadRepository
        from nikita.db.repositories.thought_repository import ThoughtRepository
        from nikita.db.repositories.summary_repository import DailySummaryRepository

        logger = logging.getLogger(__name__)

        # FR-013: Load user facts from Graphiti
        try:
            from nikita.memory.graphiti_client import get_memory_client

            memory = await get_memory_client(str(user_id))
            user_facts = await memory.get_user_facts(limit=20)
            context.user_facts = user_facts
            logger.debug(f"Loaded {len(user_facts)} user facts from Graphiti for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to load Graphiti memory for user {user_id}: {e}")

        # Load threads for prompt
        try:
            thread_repo = ConversationThreadRepository(self.session)
            threads_by_type = await thread_repo.get_threads_for_prompt(user_id, max_per_type=3)
            context.open_threads = {
                thread_type: [t.content for t in threads]
                for thread_type, threads in threads_by_type.items()
            }
            logger.debug(f"Loaded {sum(len(v) for v in context.open_threads.values())} threads for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to load threads for user {user_id}: {e}")

        # Load active thoughts
        try:
            thought_repo = ThoughtRepository(self.session)
            thoughts_by_type = await thought_repo.get_thoughts_for_prompt(user_id, max_per_type=3)
            context.active_thoughts = {
                thought_type: [t.content for t in thoughts]
                for thought_type, thoughts in thoughts_by_type.items()
            }
            logger.debug(f"Loaded {sum(len(v) for v in context.active_thoughts.values())} thoughts for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to load thoughts for user {user_id}: {e}")

        # FR-014: Load conversation summaries
        try:
            summary_repo = DailySummaryRepository(self.session)
            today = context.current_time.date()

            # Today's summary (if exists)
            today_summary = await summary_repo.get_by_date(user_id, today)
            if today_summary and today_summary.summary_text:
                context.today_summaries = [today_summary.summary_text]

            # Last 7 days summaries
            week_ago = today - timedelta(days=7)
            week_summaries = await summary_repo.get_range(user_id, week_ago, today)
            context.week_summaries = {
                s.date.isoformat(): s.summary_text or ""
                for s in week_summaries
                if s.summary_text
            }
            logger.debug(f"Loaded {len(context.week_summaries)} week summaries for {user_id}")
        except Exception as e:
            logger.warning(f"Failed to load summaries for user {user_id}: {e}")

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
            # Engagement state (spec 014)
            "{{engagement_state}}": context.engagement_state,
            "{{calibration_status}}": context.get_calibration_status(),
            "{{engagement_hint}}": context.get_engagement_hint(),
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

        # Backstory section (conditional - only if backstory exists)
        backstory_section = ""
        if context.backstory and context.backstory.has_backstory():
            parts = []
            parts.append("### Our Backstory (AC-T5.3-001: 017-enhanced-onboarding)")
            parts.append("```")
            if context.backstory.venue:
                parts.append(f"Venue: {context.backstory.venue}")
            if context.backstory.how_we_met:
                parts.append(f"How We Met: {context.backstory.how_we_met}")
            if context.backstory.the_moment:
                parts.append(f"The Moment: {context.backstory.the_moment}")
            if context.backstory.unresolved_hook:
                parts.append(f"Unresolved Hook: {context.backstory.unresolved_hook}")
            if context.backstory.tone:
                parts.append(f"Tone: {context.backstory.tone}")
            parts.append("```")
            parts.append("")
            parts.append("**User Context:**")
            parts.append("```")
            if context.backstory.city:
                parts.append(f"City: {context.backstory.city}")
            if context.backstory.life_stage:
                parts.append(f"Life Stage: {context.backstory.life_stage}")
            if context.backstory.social_scene:
                parts.append(f"Social Scene: {context.backstory.social_scene}")
            if context.backstory.primary_passion:
                parts.append(f"Primary Passion: {context.backstory.primary_passion}")
            parts.append("```")

            # Persona adaptations
            if context.backstory.persona_overrides:
                parts.append("")
                parts.append("**Persona Adaptations (AC-T5.4):**")
                formatted = getattr(context.backstory, 'persona_overrides_formatted', None)
                if formatted:
                    parts.append(formatted)

            backstory_section = "\n".join(parts)

        replacements["{{backstory_section}}"] = backstory_section

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    async def generate_system_prompt(
        self,
        user_id: UUID,
        context: MetaPromptContext | None = None,
        conversation_id: UUID | None = None,
        skip_logging: bool = False,
    ) -> GeneratedPrompt:
        """Generate a personalized system prompt for Nikita.

        Args:
            user_id: The user's UUID.
            context: Optional pre-loaded context (loads from DB if not provided).
            conversation_id: Optional conversation UUID for logging.
            skip_logging: If True, skip logging to database (for preview mode).

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

        # Build context snapshot for response
        context_snapshot = {
            "chapter": context.chapter,
            "relationship_score": float(context.relationship_score),
            "time_of_day": context.time_of_day,
            "hours_since_last": context.hours_since_last_interaction,
            "engagement_state": context.engagement_state,
        }

        # Log to database (unless skip_logging is True for preview mode)
        if not skip_logging:
            await self._log_prompt(
                user_id=user_id,
                prompt_content=result.output,
                generation_time_ms=generation_time,
                meta_prompt_template="system_prompt",
                conversation_id=conversation_id,
                context_snapshot=context_snapshot,
            )

        return GeneratedPrompt(
            content=result.output,
            generation_time_ms=generation_time,
            meta_prompt_type="system_prompt",
            user_id=user_id,
            chapter=context.chapter,
            context_snapshot=context_snapshot,
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
            parsed = json.loads(result.output)
        except json.JSONDecodeError:
            parsed = {"detected_vices": [], "primary_vice": None, "reasoning": "Failed to parse response"}

        return parsed

    async def extract_entities(
        self,
        conversation: str,
        user_id: UUID,
        context: MetaPromptContext | None = None,
        open_threads: list[dict] | None = None,
    ) -> dict:
        """Extract entities from a conversation for post-processing.

        Args:
            conversation: The conversation text to analyze.
            user_id: The user's UUID.
            context: Optional pre-loaded context.
            open_threads: List of open thread dicts with 'id', 'type', 'content' keys.

        Returns:
            Dict with user_facts, threads, resolved_thread_ids, emotional_markers, nikita_thoughts, summary.
        """
        if context is None:
            context = await self._load_context(user_id)

        template = self._templates.get("entity_extraction.meta.md", "")
        if not template:
            return {"user_facts": [], "threads": [], "resolved_thread_ids": [], "emotional_markers": [], "nikita_thoughts": [], "summary": ""}

        # Format open threads for the template
        if open_threads:
            threads_text = "\n".join(
                f"- ID: {t['id']} | Type: {t['type']} | Topic: {t['content']}"
                for t in open_threads
            )
        else:
            threads_text = "No open threads"

        # Format template
        formatted = template.replace("{{conversation}}", conversation)
        formatted = formatted.replace("{{user_id}}", str(user_id))
        formatted = formatted.replace("{{chapter}}", str(context.chapter))
        formatted = formatted.replace("{{relationship_score}}", str(context.relationship_score))
        formatted = formatted.replace(
            "{{existing_facts}}",
            "\n".join(f"- {f}" for f in context.user_facts) if context.user_facts else "None",
        )
        formatted = formatted.replace("{{open_threads}}", threads_text)

        # Execute
        result = await self._agent.run(formatted)

        # Parse JSON response
        try:
            parsed = json.loads(result.output)
        except json.JSONDecodeError:
            parsed = {"user_facts": [], "threads": [], "resolved_thread_ids": [], "emotional_markers": [], "nikita_thoughts": [], "summary": ""}

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
            parsed = json.loads(result.output)
        except json.JSONDecodeError:
            parsed = {
                "thoughts": [],
                "current_activity": context.nikita_activity,
                "current_mood": context.nikita_mood,
                "energy_level": context.nikita_energy,
                "availability": "available",
            }

        return parsed

    async def generate_daily_summary(
        self,
        user_id: UUID,
        summary_date: date,
        score_start: Decimal,
        score_end: Decimal,
        decay_applied: Decimal,
        conversations_data: list[dict],
        new_facts: list[str],
        new_threads: list[dict],
        nikita_thoughts: list[str],
        context: MetaPromptContext | None = None,
    ) -> dict:
        """Generate Nikita's daily summary for a user.

        Args:
            user_id: The user's UUID.
            summary_date: Date of the summary.
            score_start: Score at start of day.
            score_end: Score at end of day.
            decay_applied: Decay amount applied.
            conversations_data: List of conversation summaries.
            new_facts: Facts learned today.
            new_threads: Threads created today.
            nikita_thoughts: Thoughts generated today.
            context: Optional pre-loaded context.

        Returns:
            Dict with summary_text, emotional_tone, key_moments, engagement_score.
        """
        if context is None:
            context = await self._load_context(user_id)

        template = self._templates.get("daily_summary.meta.md", "")
        if not template:
            return {
                "summary_text": "No conversations today.",
                "emotional_tone": "neutral",
                "key_moments": [],
                "engagement_score": Decimal("0.5"),
            }

        # Calculate score delta and trend
        score_delta = score_end - score_start
        if score_delta > Decimal("0"):
            score_trend = "improving"
        elif score_delta < Decimal("0"):
            score_trend = "declining"
        else:
            score_trend = "stable"

        # Format conversations summary
        if conversations_data:
            conv_lines = []
            for i, conv in enumerate(conversations_data, 1):
                summary = conv.get("summary", "No summary")
                tone = conv.get("emotional_tone", "neutral")
                conv_lines.append(f"{i}. [{tone}] {summary}")
            conversations_summary = "\n".join(conv_lines)
        else:
            conversations_summary = "No conversations today"

        # Format key moments
        key_moments = []
        for conv in conversations_data:
            if conv.get("key_moment"):
                key_moments.append(f"- {conv['key_moment']}")
        key_moments_text = "\n".join(key_moments) if key_moments else "None"

        # Format template
        formatted = template.replace("{{chapter}}", str(context.chapter))
        formatted = formatted.replace("{{chapter_name}}", context.chapter_name)
        formatted = formatted.replace("{{score_start}}", str(score_start))
        formatted = formatted.replace("{{score_end}}", str(score_end))
        formatted = formatted.replace("{{score_delta}}", f"{score_delta:+.1f}")
        formatted = formatted.replace("{{score_trend}}", score_trend)
        formatted = formatted.replace("{{decay_applied}}", str(decay_applied))
        formatted = formatted.replace("{{conversations_summary}}", conversations_summary)
        formatted = formatted.replace("{{key_moments}}", key_moments_text)
        formatted = formatted.replace(
            "{{new_facts}}",
            "\n".join(f"- {f}" for f in new_facts) if new_facts else "None"
        )
        formatted = formatted.replace(
            "{{new_threads}}",
            "\n".join(f"- {t.get('topic', t.get('content', 'Thread'))}" for t in new_threads) if new_threads else "None"
        )
        formatted = formatted.replace(
            "{{nikita_thoughts}}",
            "\n".join(f"- {t}" for t in nikita_thoughts) if nikita_thoughts else "None"
        )

        # Execute LLM
        result = await self._agent.run(formatted)

        # Parse JSON response
        try:
            parsed = json.loads(result.output)
            # Ensure engagement_score is Decimal
            if "engagement_score" in parsed:
                parsed["engagement_score"] = Decimal(str(parsed["engagement_score"]))
        except json.JSONDecodeError:
            parsed = {
                "summary_text": "Quiet day, nothing much happened.",
                "emotional_tone": "neutral",
                "key_moments": [],
                "engagement_score": Decimal("0.5"),
            }

        return parsed
