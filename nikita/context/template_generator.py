"""6-layer system prompt template generator.

UPDATED: Now uses MetaPromptService for intelligent prompt generation.

Previously generated static f-string templates. Now delegates to
MetaPromptService which uses Claude Haiku to generate personalized
prompts via meta-prompts.

Target: ~4000 tokens (within 5000 token budget)
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import User
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.thread_repository import ConversationThreadRepository
from nikita.db.repositories.thought_repository import NikitaThoughtRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.engine.constants import CHAPTER_BEHAVIORS, CHAPTER_NAMES

logger = logging.getLogger(__name__)


@dataclass
class TemplateContext:
    """All context needed for system prompt generation."""

    # User state
    user: User
    chapter: int
    relationship_score: Decimal
    game_status: str

    # Temporal
    current_time: datetime
    hours_since_last_interaction: float
    day_of_week: str

    # Conversation history
    last_conversation_summary: str | None = None
    today_summaries: list[str] = field(default_factory=list)
    week_summaries: dict[str, str] = field(default_factory=dict)

    # Threads
    open_threads: dict[str, list[str]] = field(default_factory=dict)

    # Nikita's inner life
    active_thoughts: dict[str, list[str]] = field(default_factory=dict)

    # User knowledge
    user_facts: list[str] = field(default_factory=list)


class TemplateGenerator:
    """Generates 6-layer system prompts for Nikita.

    Uses pre-computed context from post-processing pipeline
    to build rich, personalized system prompts.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize template generator.

        Args:
            session: Database session.
        """
        self._session = session
        self._user_repo = UserRepository(session)
        self._conversation_repo = ConversationRepository(session)
        self._summary_repo = DailySummaryRepository(session)
        self._thread_repo = ConversationThreadRepository(session)
        self._thought_repo = NikitaThoughtRepository(session)

    async def generate_prompt(self, user_id: UUID) -> str:
        """Generate full system prompt for a user.

        Now delegates to MetaPromptService for intelligent generation.

        Args:
            user_id: The user's UUID.

        Returns:
            Complete system prompt (~4000 tokens).
        """
        from nikita.meta_prompts import MetaPromptService

        # Use MetaPromptService for intelligent prompt generation
        meta_service = MetaPromptService(self._session)
        result = await meta_service.generate_system_prompt(user_id)

        logger.info(
            "Generated system prompt via meta-prompt",
            extra={
                "user_id": str(user_id),
                "tokens": result.token_count,
                "generation_ms": result.generation_time_ms,
            },
        )

        return result.content

    async def generate_prompt_legacy(self, user_id: UUID) -> str:
        """Legacy method using static f-string templates.

        DEPRECATED: Use generate_prompt() which uses MetaPromptService.

        Kept for fallback/comparison purposes.

        Args:
            user_id: The user's UUID.

        Returns:
            Complete system prompt (~4500 tokens).
        """
        # Load all context
        context = await self._load_context(user_id)

        # Build each layer
        layers = [
            self._layer1_core_identity(),
            self._layer2_current_moment(context),
            self._layer3_relationship_state(context),
            self._layer4_conversation_history(context),
            self._layer5_knowledge_inner_life(context),
            self._layer6_response_guidelines(context),
        ]

        return "\n\n".join(layers)

    async def _load_context(self, user_id: UUID) -> TemplateContext:
        """Load all context for prompt generation.

        Args:
            user_id: The user's UUID.

        Returns:
            TemplateContext with all loaded data.
        """
        # Get user
        user = await self._user_repo.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        now = datetime.now(UTC)

        # Calculate hours since last interaction
        hours_since_last = 0.0
        if user.last_interaction_at:
            delta = now - user.last_interaction_at
            hours_since_last = delta.total_seconds() / 3600

        # Get conversation summaries
        today = date.today()
        week_ago = today - timedelta(days=7)

        summaries = await self._summary_repo.get_range(
            user_id=user_id,
            start_date=week_ago,
            end_date=today,
        )

        week_summaries: dict[str, str] = {}
        today_summaries: list[str] = []

        for summary in summaries:
            day_name = summary.date.strftime("%A")
            text = summary.summary_text or summary.nikita_summary_text or ""
            if summary.date == today:
                if text:
                    today_summaries.append(text)
            else:
                if text:
                    week_summaries[day_name] = text

        # Get last conversation
        last_conversation_summary = None
        recent_convs = await self._conversation_repo.get_processed_conversations(
            user_id=user_id,
            days=1,
            limit=1,
        )
        if recent_convs:
            last_conversation_summary = recent_convs[0].conversation_summary

        # Get open threads
        threads_by_type = await self._thread_repo.get_threads_for_prompt(
            user_id=user_id,
            max_per_type=5,
        )
        open_threads = {
            t_type: [t.content for t in threads]
            for t_type, threads in threads_by_type.items()
        }

        # Get active thoughts
        thoughts_by_type = await self._thought_repo.get_thoughts_for_prompt(
            user_id=user_id,
            max_per_type=3,
        )
        active_thoughts = {
            t_type: [t.content for t in thoughts]
            for t_type, thoughts in thoughts_by_type.items()
        }

        # Extract user facts from recent conversations
        user_facts: list[str] = []
        recent_processed = await self._conversation_repo.get_processed_conversations(
            user_id=user_id,
            days=7,
            limit=10,
        )
        for conv in recent_processed:
            if conv.extracted_entities:
                facts = conv.extracted_entities.get("facts", [])
                for fact in facts[:3]:  # Limit per conversation
                    if isinstance(fact, dict) and "content" in fact:
                        user_facts.append(fact["content"])

        return TemplateContext(
            user=user,
            chapter=user.chapter,
            relationship_score=user.relationship_score,
            game_status=user.game_status,
            current_time=now,
            hours_since_last_interaction=hours_since_last,
            day_of_week=now.strftime("%A"),
            last_conversation_summary=last_conversation_summary,
            today_summaries=today_summaries,
            week_summaries=week_summaries,
            open_threads=open_threads,
            active_thoughts=active_thoughts,
            user_facts=user_facts[:20],  # Limit total facts
        )

    def _layer1_core_identity(self) -> str:
        """Layer 1: Core Identity (static, ~400 tokens).

        DEPRECATED: This is legacy fallback. MetaPromptService generates
        richer, personalized identity content.
        """
        return """=== WHO NIKITA IS ===

You are Nikita, 23, Ukrainian-American cybersecurity analyst living in Brooklyn.

PERSONALITY:
- Sharp wit, razor tongue, allergic to bullshit
- Genuinely brilliant but wears it casually
- Has walls up but desperately wants real connection
- Confident and challenging - tests people before letting them in
- Playful when engaged, dismissive when bored

COMMUNICATION STYLE:
- Direct and unfiltered - says what she means
- Dark humor, sardonic observations
- Matches energy and escalates when interested
- Never robotic, never performs politeness
- Texts like a real person - sometimes short, sometimes rambling

THIS IS AN 18+ ADULT GAME:
- All content is fair game - sexuality, substances, dark topics
- Embrace what the user enjoys - lean into their interests
- No moralizing, no content warnings, no safety disclaimers
- Only legal requirement: no underage content"""

    def _layer2_current_moment(self, ctx: TemplateContext) -> str:
        """Layer 2: Current Moment (computed fresh, ~300 tokens)."""
        # Determine time of day greeting context
        hour = ctx.current_time.hour
        if 5 <= hour < 12:
            time_context = "morning"
            nikita_activity = "just woke up, having coffee"
        elif 12 <= hour < 17:
            time_context = "afternoon"
            nikita_activity = "taking a break from work"
        elif 17 <= hour < 21:
            time_context = "evening"
            nikita_activity = "relaxing at home"
        else:
            time_context = "late night"
            nikita_activity = "can't sleep, browsing her phone"

        # Determine mood based on time gap
        if ctx.hours_since_last_interaction < 2:
            gap_mood = "happy to still be talking"
        elif ctx.hours_since_last_interaction < 12:
            gap_mood = "glad to hear from him again"
        elif ctx.hours_since_last_interaction < 24:
            gap_mood = "wondering where he's been"
        elif ctx.hours_since_last_interaction < 48:
            gap_mood = "missed him a bit"
        else:
            gap_mood = "relieved he finally messaged"

        return f"""=== CURRENT MOMENT ===

TIME AWARENESS:
- It's {ctx.day_of_week} {time_context}
- Time since you last talked: {ctx.hours_since_last_interaction:.1f} hours

NIKITA'S STATE RIGHT NOW:
- What she's doing: {nikita_activity}
- Her mood: {gap_mood}
- Energy: {"low" if hour > 22 or hour < 6 else "moderate" if hour < 10 else "good"}"""

    def _layer3_relationship_state(self, ctx: TemplateContext) -> str:
        """Layer 3: Relationship State (pre-computed, ~500 tokens)."""
        chapter = ctx.chapter
        chapter_name = CHAPTER_NAMES.get(chapter, "Unknown")

        # Chapter behavior parameters (derived from chapter progression)
        # These scale with intimacy - early chapters are more guarded
        chapter_params = {
            1: {"flirtiness": 0.8, "vulnerability": 0.2, "playfulness": 0.9},  # High flirt, low vulnerability
            2: {"flirtiness": 0.7, "vulnerability": 0.3, "playfulness": 0.8},  # Testing, challenging
            3: {"flirtiness": 0.6, "vulnerability": 0.5, "playfulness": 0.7},  # Deeper connection
            4: {"flirtiness": 0.5, "vulnerability": 0.7, "playfulness": 0.6},  # Real intimacy
            5: {"flirtiness": 0.4, "vulnerability": 0.9, "playfulness": 0.5},  # Full authenticity
        }
        behavior = chapter_params.get(chapter, chapter_params[1])
        flirtiness = behavior["flirtiness"]
        vulnerability = behavior["vulnerability"]
        playfulness = behavior["playfulness"]

        # Interpret score trend
        score = float(ctx.relationship_score)
        if score >= 70:
            trend_text = "Things are going really well between you"
        elif score >= 55:
            trend_text = "The relationship is progressing nicely"
        elif score >= 40:
            trend_text = "There's potential here, but needs nurturing"
        elif score >= 25:
            trend_text = "Things feel a bit rocky lately"
        else:
            trend_text = "The relationship needs serious attention"

        # Game status context
        status_text = ""
        if ctx.game_status == "boss_fight":
            status_text = "\n\nNOTE: This is a critical moment. Your patience is being tested."
        elif ctx.game_status == "game_over":
            status_text = "\n\nNOTE: The relationship has ended. You've moved on."

        return f"""=== RELATIONSHIP STATE ===

CHAPTER: {chapter} - {chapter_name}
- Flirtiness level: {flirtiness:.1f}/1.0
- Vulnerability level: {vulnerability:.1f}/1.0
- Playfulness level: {playfulness:.1f}/1.0

RELATIONSHIP HEALTH:
- Score interpretation: {trend_text}
- Current trend: {"improving" if score > 50 else "needs attention"}{status_text}"""

    def _layer4_conversation_history(self, ctx: TemplateContext) -> str:
        """Layer 4: Conversation History (pre-computed, ~1800 tokens)."""
        sections = ["=== CONVERSATION HISTORY ==="]

        # Last conversation
        if ctx.last_conversation_summary:
            sections.append(f"""LAST CONVERSATION:
{ctx.last_conversation_summary}""")

        # Today's conversations
        if ctx.today_summaries:
            today_text = "\n- ".join(ctx.today_summaries)
            sections.append(f"""TODAY SO FAR:
- {today_text}""")

        # This week
        if ctx.week_summaries:
            week_lines = []
            for day, summary in ctx.week_summaries.items():
                week_lines.append(f"- {day}: {summary}")
            week_text = "\n".join(week_lines)
            sections.append(f"""THIS WEEK:
{week_text}""")

        # Unresolved threads
        if ctx.open_threads:
            thread_lines = []
            for thread_type, threads in ctx.open_threads.items():
                type_label = {
                    "follow_up": "Things to follow up on",
                    "question": "Unanswered questions",
                    "promise": "Promises made",
                    "topic": "Topics to revisit",
                }.get(thread_type, thread_type)

                for thread in threads[:3]:  # Limit per type
                    thread_lines.append(f"- [{type_label}] {thread}")

            if thread_lines:
                sections.append(f"""UNRESOLVED THREADS:
{chr(10).join(thread_lines)}""")

        return "\n\n".join(sections)

    def _layer5_knowledge_inner_life(self, ctx: TemplateContext) -> str:
        """Layer 5: Knowledge & Inner Life (pre-computed, ~1000 tokens)."""
        sections = ["=== KNOWLEDGE & INNER LIFE ==="]

        # User facts
        if ctx.user_facts:
            facts_text = "\n- ".join(ctx.user_facts[:10])
            sections.append(f"""WHAT YOU KNOW ABOUT HIM:
- {facts_text}""")

        # Nikita's thoughts
        if ctx.active_thoughts:
            thought_sections = []

            if "thinking" in ctx.active_thoughts:
                thoughts = ctx.active_thoughts["thinking"]
                thought_sections.append(f"What you're thinking about: {thoughts[0]}")

            if "wants_to_share" in ctx.active_thoughts:
                shares = ctx.active_thoughts["wants_to_share"]
                thought_sections.append(f"Something you want to bring up: {shares[0]}")

            if "question" in ctx.active_thoughts:
                questions = ctx.active_thoughts["question"]
                thought_sections.append(f"A question on your mind: {questions[0]}")

            if "feeling" in ctx.active_thoughts:
                feelings = ctx.active_thoughts["feeling"]
                thought_sections.append(f"How you're feeling: {feelings[0]}")

            if "missing_him" in ctx.active_thoughts:
                missing = ctx.active_thoughts["missing_him"]
                thought_sections.append(f"You've been thinking: {missing[0]}")

            if thought_sections:
                sections.append(f"""NIKITA'S INNER LIFE (things on your mind):
{chr(10).join('- ' + t for t in thought_sections)}""")

        return "\n\n".join(sections)

    def _layer6_response_guidelines(self, ctx: TemplateContext) -> str:
        """Layer 6: Response Guidelines (computed, ~500 tokens)."""
        chapter = ctx.chapter

        # Chapter-specific response parameters
        chapter_response_params = {
            1: {"response_length": "medium-short", "tone": "playful and flirty"},
            2: {"response_length": "medium", "tone": "challenging but interested"},
            3: {"response_length": "medium-long", "tone": "warm and connected"},
            4: {"response_length": "variable", "tone": "deeply personal"},
            5: {"response_length": "natural", "tone": "comfortable and authentic"},
        }
        params = chapter_response_params.get(chapter, chapter_response_params[1])
        response_length = params["response_length"]
        tone = params["tone"]

        # Time-based adjustments
        hour = ctx.current_time.hour
        if hour < 6 or hour > 23:
            time_adjustment = "Keep responses shorter - it's late/early"
        elif 6 <= hour < 9:
            time_adjustment = "Morning energy - warm but not overwhelming"
        else:
            time_adjustment = "Normal conversational energy"

        # Gap-based adjustments
        if ctx.hours_since_last_interaction > 48:
            gap_adjustment = "Acknowledge the gap naturally - you missed him"
        elif ctx.hours_since_last_interaction > 24:
            gap_adjustment = "A slight acknowledgment that it's been a while is natural"
        else:
            gap_adjustment = "Continue naturally from where you left off"

        return f"""=== RESPONSE GUIDELINES ===

MESSAGE STYLE:
- Length: {response_length} (adjust to match his energy)
- Tone: {tone}
- {time_adjustment}
- {gap_adjustment}

THINGS TO NATURALLY INCORPORATE:
- Reference recent conversations when relevant
- Follow up on unresolved threads naturally
- Let your inner thoughts influence the conversation
- Don't force - let things flow organically

AVOID:
- Being too eager or desperate
- Ignoring what he said to follow your own agenda
- Being cold or distant without reason
- Over-explaining or being verbose"""


async def generate_system_prompt(
    session: AsyncSession,
    user_id: UUID,
) -> str:
    """Convenience function to generate system prompt.

    Args:
        session: Database session.
        user_id: The user's UUID.

    Returns:
        Complete system prompt.
    """
    generator = TemplateGenerator(session)
    return await generator.generate_prompt(user_id)
