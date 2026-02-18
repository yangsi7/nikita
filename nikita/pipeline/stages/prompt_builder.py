"""Prompt builder stage - generates system prompt (T3.3 + T3.4 + Spec 045).

Generates BOTH text and voice prompts in one pass from unified template.
Non-critical: failure does not stop the pipeline.

Implements:
- AC-3.3.1: Loads Jinja2 template, renders with PipelineContext data
- AC-3.3.2: Calls Claude Haiku for narrative enrichment (optional)
- AC-3.3.3: Falls back to raw Jinja2 output if Haiku fails
- AC-3.3.4: Stores result in ready_prompts via ReadyPromptRepository.set_current()
- AC-3.3.5: Generates BOTH text and voice prompts in one pass
- AC-3.4.1: Text prompt post-enrichment: 5,500-6,500 tokens (warn if outside range)
- AC-3.4.2: Voice prompt post-enrichment: 1,800-2,200 tokens (warn if outside range)
- AC-3.4.3: If over budget, truncate lower-priority sections (Vice -> Chapter -> Psychology)

Spec 045 additions:
- WP-1: _enrich_context() loads conversation history, memory episodes, Nikita state
- WP-2: Unified template (system_prompt.j2 with platform conditionals)
- WP-3: Conversation summaries (last, today, week) included in prompts
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession


class PromptBuilderStage(BaseStage):
    """Generate system prompts for both text and voice platforms.

    Renders unified Jinja2 template with PipelineContext data, optionally enriches
    with Claude Haiku for narrative depth, enforces token budgets, and stores
    results in ready_prompts table.

    Spec 045: Uses single system_prompt.j2 with platform conditionals for
    both text and voice, replacing the old separate voice_prompt.j2.
    """

    name = "prompt_builder"
    is_critical = False
    timeout_seconds = 90.0

    # Token budgets (AC-3.4.1, AC-3.4.2)
    TEXT_TOKEN_MIN = 5500
    TEXT_TOKEN_MAX = 6500
    VOICE_TOKEN_MIN = 1800
    VOICE_TOKEN_MAX = 2200

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Generate system prompts for both text and voice platforms.

        Spec 045: Enriches context before rendering to fill all template sections.

        Returns:
            dict with keys:
                - text_generated: bool
                - text_tokens: int
                - text_time_ms: float
                - voice_generated: bool
                - voice_tokens: int
                - voice_time_ms: float
                - generated: bool (True if at least one succeeded)
        """
        # Spec 045 WP-1: Enrich context with conversation history, memory, state
        await self._enrich_context(ctx)

        results = {}

        # Generate text prompt (AC-3.3.5) — unified template
        text_prompt, text_tokens, text_time = await self._generate_prompt(ctx, "text")
        results["text_generated"] = text_prompt is not None
        results["text_tokens"] = text_tokens
        results["text_time_ms"] = text_time

        # Generate voice prompt (AC-3.3.5) — same unified template, different platform
        voice_prompt, voice_tokens, voice_time = await self._generate_prompt(ctx, "voice")
        results["voice_generated"] = voice_prompt is not None
        results["voice_tokens"] = voice_tokens
        results["voice_time_ms"] = voice_time

        # Set on context (use the prompt matching ctx.platform)
        if ctx.platform == "voice" and voice_prompt is not None:
            ctx.generated_prompt = voice_prompt
            ctx.prompt_token_count = voice_tokens
        elif text_prompt is not None:
            ctx.generated_prompt = text_prompt
            ctx.prompt_token_count = text_tokens

        results["generated"] = results["text_generated"] or results["voice_generated"]
        return results

    async def _enrich_context(self, ctx: PipelineContext) -> None:
        """Load all missing context data for template rendering (Spec 045 WP-1).

        Populates PipelineContext fields that sections 4-9 of system_prompt.j2
        need but were previously left empty. Loads conversation summaries,
        memory episodes, Nikita state, and computed values.

        All loads are try/except guarded — enrichment failure is non-critical.
        """
        from nikita.utils.nikita_state import (
            compute_day_of_week,
            compute_nikita_activity,
            compute_nikita_energy,
            compute_nikita_mood,
            compute_time_of_day,
            compute_vulnerability_level,
        )

        # Compute Nikita's simulated state
        now = datetime.now()
        time_of_day = compute_time_of_day(now.hour)
        day_of_week = compute_day_of_week()

        ctx.time_of_day = time_of_day
        ctx.nikita_activity = compute_nikita_activity(time_of_day, day_of_week)
        ctx.nikita_energy = compute_nikita_energy(time_of_day)
        ctx.nikita_mood = compute_nikita_mood(
            ctx.chapter, float(ctx.relationship_score), ctx.emotional_state or None
        )
        ctx.vulnerability_level = compute_vulnerability_level(ctx.chapter)

        # Load conversation summaries (WP-3)
        if self._session:
            try:
                from nikita.db.repositories.conversation_repository import ConversationRepository

                conv_repo = ConversationRepository(self._session)
                summaries = await conv_repo.get_conversation_summaries_for_prompt(
                    user_id=ctx.user_id,
                    exclude_conversation_id=ctx.conversation_id,
                )
                ctx.last_conversation_summary = summaries.get("last_summary")
                ctx.today_summaries = summaries.get("today_summaries")
                ctx.week_summaries = summaries.get("week_summaries")
            except Exception as e:
                self._logger.warning("enrich_conversation_summaries_failed error=%s", str(e))

        # Compute hours since last interaction
        if self._session:
            try:
                from nikita.db.repositories.user_repository import UserRepository

                user_repo = UserRepository(self._session)
                user = await user_repo.get(ctx.user_id)
                if user:
                    # Store user reference for template (profile, backstory, etc.)
                    ctx.user = user
                    if hasattr(user, "last_interaction_at") and user.last_interaction_at:
                        delta = datetime.now(timezone.utc) - user.last_interaction_at
                        ctx.hours_since_last = round(delta.total_seconds() / 3600, 1)
            except Exception as e:
                self._logger.warning("enrich_user_data_failed error=%s", str(e))

        # Load memory episodes (relationship history + nikita events)
        if self._session:
            try:
                from nikita.config.settings import get_settings
                from nikita.memory.supabase_memory import SupabaseMemory

                settings = get_settings()
                if settings.openai_api_key:
                    memory = SupabaseMemory(
                        session=self._session,
                        user_id=ctx.user_id,
                        openai_api_key=settings.openai_api_key,
                    )
                    # Relationship episodes
                    try:
                        rel_facts = await memory.search(
                            query="shared moments relationship history",
                            fact_types=["relationship"],
                            limit=10,
                        )
                        ctx.relationship_episodes = [f.fact for f in rel_facts]
                    except Exception:
                        pass

                    # Nikita's own life events
                    try:
                        nikita_facts = await memory.search(
                            query="nikita life events activities",
                            fact_types=["nikita"],
                            limit=10,
                        )
                        ctx.nikita_events = [f.fact for f in nikita_facts]
                    except Exception:
                        pass
            except Exception as e:
                self._logger.warning("enrich_memory_failed error=%s", str(e))

        # Load open threads from extracted data (already in ctx from extraction stage)
        # ctx.extracted_threads is already populated, use it for open_threads
        if ctx.extracted_threads:
            ctx.open_threads = ctx.extracted_threads

        self._logger.info(
            "context_enriched summaries=%s episodes=%d nikita_events=%d mood=%s vuln=%s",
            bool(ctx.last_conversation_summary or ctx.today_summaries),
            len(ctx.relationship_episodes),
            len(ctx.nikita_events),
            ctx.nikita_mood,
            ctx.vulnerability_level,
        )

    async def _generate_prompt(
        self, ctx: PipelineContext, platform: str
    ) -> tuple[str | None, int, float]:
        """Generate a single prompt for a platform.

        Spec 045 WP-2: Always uses system_prompt.j2 (unified template).

        Args:
            ctx: Pipeline context with user state and extraction results.
            platform: 'text' or 'voice'.

        Returns:
            (prompt_text, token_count, generation_time_ms)
        """
        start = time.perf_counter()

        # Step 1: Render unified Jinja2 template (Spec 045 WP-2)
        template_name = "system_prompt.j2"
        try:
            raw_prompt = self._render_template(template_name, ctx, platform)
        except Exception as e:
            self._logger.error("template_render_failed platform=%s error=%s", platform, str(e))
            return None, 0, (time.perf_counter() - start) * 1000

        # Step 2: Count tokens
        token_count = self._count_tokens(raw_prompt)

        # Step 3: Optional Haiku enrichment (AC-3.3.2, AC-3.3.3)
        enriched_prompt = await self._enrich_with_haiku(raw_prompt, platform)
        if enriched_prompt:
            token_count = self._count_tokens(enriched_prompt)
            final_prompt = enriched_prompt
        else:
            final_prompt = raw_prompt

        # Step 4: Token budget validation + truncation (AC-3.4.1, AC-3.4.2, AC-3.4.3)
        final_prompt, token_count = self._enforce_token_budget(final_prompt, token_count, platform)

        # Step 5: Store in ready_prompts (AC-3.3.4)
        gen_time_ms = (time.perf_counter() - start) * 1000
        await self._store_prompt(ctx, platform, final_prompt, token_count, gen_time_ms)

        return final_prompt, token_count, gen_time_ms

    def _render_template(self, template_name: str, ctx: PipelineContext, platform: str) -> str:
        """Render a Jinja2 template with PipelineContext data.

        Args:
            template_name: Template file name (e.g., "system_prompt.j2").
            ctx: Pipeline context.
            platform: 'text' or 'voice' — passed to template for conditionals.

        Returns:
            Rendered prompt text.
        """
        from nikita.pipeline.templates import render_template

        template_vars = self._build_template_vars(ctx, platform)
        return render_template(template_name, **template_vars)

    def _build_template_vars(self, ctx: PipelineContext, platform: str) -> dict:
        """Convert PipelineContext to flat dict for Jinja2 template (Spec 045 WP-1).

        Now passes ALL variables expected by system_prompt.j2 sections 1-11,
        including enriched context from _enrich_context().

        Args:
            ctx: Pipeline context.
            platform: 'text' or 'voice'.

        Returns:
            Template variables dict.
        """
        # Safely extract user profile data (guard against MissingGreenlet)
        user = ctx.user
        user_profile = None
        try:
            if user and hasattr(user, "profile"):
                user_profile = user.profile
        except Exception:
            pass  # Lazy-load failure, user_profile stays None

        return {
            # Core
            "platform": platform,
            "user_id": str(ctx.user_id),
            "conversation_id": str(ctx.conversation_id),
            # User state
            "chapter": ctx.chapter,
            "relationship_score": float(ctx.relationship_score),
            "game_status": ctx.game_status,
            "engagement_state": ctx.engagement_state,
            "vices": ctx.vices,
            "metrics": {k: float(v) for k, v in ctx.metrics.items()} if ctx.metrics else {},
            # User object for template (profile access)
            "user": user if user_profile else None,
            # Extraction results
            "extracted_facts": ctx.extracted_facts,
            "extracted_threads": ctx.extracted_threads,
            "extracted_thoughts": ctx.extracted_thoughts,
            "extraction_summary": ctx.extraction_summary,
            "emotional_tone": ctx.emotional_tone,
            # Life sim
            "life_events": ctx.life_events,
            # Emotional state
            "emotional_state": ctx.emotional_state,
            # Game state
            "score_delta": float(ctx.score_delta),
            "active_conflict": ctx.active_conflict if ctx.active_conflict else None,
            "conflict_type": ctx.conflict_type,
            # Touchpoints
            "touchpoint_scheduled": ctx.touchpoint_scheduled,
            # Spec 045 WP-1: Enriched context — Nikita state
            "nikita_activity": ctx.nikita_activity,
            "nikita_mood": ctx.nikita_mood,
            "nikita_energy": ctx.nikita_energy,
            "time_of_day": ctx.time_of_day,
            "vulnerability_level": ctx.vulnerability_level,
            "nikita_daily_events": ctx.nikita_daily_events,
            # Spec 045 WP-3: Conversation history
            "last_conversation_summary": ctx.last_conversation_summary,
            "today_summaries": ctx.today_summaries,
            "week_summaries": ctx.week_summaries,
            "hours_since_last": ctx.hours_since_last,
            # Spec 045 WP-1: Memory & threads
            "open_threads": ctx.open_threads,
            "relationship_episodes": ctx.relationship_episodes,
            "nikita_events": ctx.nikita_events,
            # Spec 045 WP-1: Inner life
            "inner_monologue": ctx.inner_monologue,
            "active_thoughts": ctx.active_thoughts,
            # Spec 056: Psyche state for L3 injection
            "psyche_state": ctx.psyche_state,
        }

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken.

        Args:
            text: Text to count.

        Returns:
            Token count.
        """
        from nikita.context.utils.token_counter import count_tokens

        return count_tokens(text)

    async def _enrich_with_haiku(self, raw_prompt: str, platform: str) -> str | None:
        """Optional narrative enrichment via Claude Haiku.

        Calls Claude Haiku to improve narrative flow and emotional depth
        while preserving all factual content.

        Args:
            raw_prompt: Raw Jinja2-rendered prompt.
            platform: 'text' or 'voice'.

        Returns:
            Enriched text or None on failure.
        """
        try:
            from pydantic_ai import Agent
            from pydantic_ai.models.anthropic import AnthropicModel
            from nikita.config.settings import get_settings

            settings = get_settings()
            if not settings.anthropic_api_key:
                return None

            enrichment_prompt = (
                "You are a narrative editor. Improve the following system prompt "
                "to be more vivid, emotionally coherent, and narratively rich. "
                "Preserve ALL factual content (names, facts, numbers, rules). "
                "Only enhance the narrative flow and emotional depth. "
                f"This is for a {'text chat' if platform == 'text' else 'voice conversation'} agent.\n\n"
                f"Original prompt:\n{raw_prompt}"
            )

            # Use Haiku for cost efficiency — pydantic-ai 1.x reads ANTHROPIC_API_KEY from env
            model = AnthropicModel("claude-haiku-4-5-20251001")
            agent = Agent(model=model)
            result = await agent.run(enrichment_prompt)

            # pydantic-ai 1.x uses .output, older versions use .data
            enriched = getattr(result, "output", None) or getattr(result, "data", None)
            if enriched and len(enriched) > len(raw_prompt) * 0.5:
                return enriched
            return None

        except Exception as e:
            self._logger.warning("haiku_enrichment_failed error=%s", str(e))
            return None

    def _enforce_token_budget(
        self, prompt: str, token_count: int, platform: str
    ) -> tuple[str, int]:
        """Validate and enforce token budget. Truncate if over.

        Args:
            prompt: Prompt text.
            token_count: Current token count.
            platform: 'text' or 'voice'.

        Returns:
            (potentially_truncated_prompt, final_token_count)
        """
        if platform == "text":
            max_tokens = self.TEXT_TOKEN_MAX
            min_tokens = self.TEXT_TOKEN_MIN
        else:
            max_tokens = self.VOICE_TOKEN_MAX
            min_tokens = self.VOICE_TOKEN_MIN

        if token_count < min_tokens:
            self._logger.warning(
                "prompt_under_budget platform=%s tokens=%d min=%d",
                platform,
                token_count,
                min_tokens,
            )

        if token_count > max_tokens:
            self._logger.warning(
                "prompt_over_budget platform=%s tokens=%d max=%d truncating",
                platform,
                token_count,
                max_tokens,
            )
            prompt = self._truncate_prompt(prompt, max_tokens)
            token_count = self._count_tokens(prompt)

        return prompt, token_count

    def _truncate_prompt(self, prompt: str, target_tokens: int) -> str:
        """Truncate prompt by removing lower-priority sections.

        Priority (lowest first, remove first):
        1. Vice Shaping
        2. Chapter Behavior
        3. Psychological Depth

        Args:
            prompt: Prompt text.
            target_tokens: Target token count.

        Returns:
            Truncated prompt.
        """
        from nikita.context.utils.token_counter import TokenCounter

        counter = TokenCounter(budget=target_tokens)

        # Try removing sections in priority order (AC-3.4.3)
        sections_to_remove = [
            "## 11. VICE SHAPING",
            "## 10. CHAPTER BEHAVIOR",
            "## 9. PSYCHOLOGICAL DEPTH",
        ]

        current = prompt
        for section_header in sections_to_remove:
            if counter.fits_budget(current):
                break
            current = self._remove_section(current, section_header)

        # If still over, hard truncate
        if not counter.fits_budget(current):
            current = counter.truncate_to_budget(current)

        return current

    def _remove_section(self, prompt: str, section_header: str) -> str:
        """Remove a section from the prompt by header.

        Args:
            prompt: Full prompt text.
            section_header: Section header to remove (e.g., "## 11. VICE SHAPING").

        Returns:
            Prompt with section removed.
        """
        start = prompt.find(section_header)
        if start == -1:
            return prompt

        # Find next section header
        next_section = prompt.find("\n## ", start + len(section_header))
        if next_section == -1:
            # Last section - remove to end
            return prompt[:start].rstrip()
        else:
            return prompt[:start] + prompt[next_section:]

    async def _store_prompt(
        self,
        ctx: PipelineContext,
        platform: str,
        prompt_text: str,
        token_count: int,
        gen_time_ms: float,
    ) -> None:
        """Store generated prompt in ready_prompts table.

        Args:
            ctx: Pipeline context.
            platform: 'text' or 'voice'.
            prompt_text: Generated prompt text.
            token_count: Token count.
            gen_time_ms: Generation time in milliseconds.
        """
        if not self._session:
            self._logger.warning("no_session_for_prompt_storage")
            return

        try:
            from nikita.db.repositories.ready_prompt_repository import ReadyPromptRepository

            repo = ReadyPromptRepository(self._session)
            context_snapshot = {
                "chapter": ctx.chapter,
                "relationship_score": float(ctx.relationship_score),
                "emotional_tone": ctx.emotional_tone,
                "facts_count": len(ctx.extracted_facts),
                "vices": ctx.vices,
            }

            await repo.set_current(
                user_id=ctx.user_id,
                platform=platform,
                prompt_text=prompt_text,
                token_count=token_count,
                pipeline_version="045-v1",
                generation_time_ms=gen_time_ms,
                context_snapshot=context_snapshot,
                conversation_id=ctx.conversation_id,
            )

            # Spec 043 T1.2: Sync voice prompt to user.cached_voice_prompt for outbound calls
            if platform == "voice":
                await self._sync_cached_voice_prompt(ctx.user_id, prompt_text)

        except Exception as e:
            self._logger.warning("prompt_store_failed platform=%s error=%s", platform, str(e))

    async def _sync_cached_voice_prompt(self, user_id, prompt_text: str) -> None:
        """Sync voice prompt to user.cached_voice_prompt for outbound calls.

        Spec 043 T1.2: Backward compatibility - outbound calls (service.py)
        read user.cached_voice_prompt. This keeps it in sync with ready_prompts.
        Failure is logged but does not fail the pipeline stage.
        """
        try:
            from datetime import datetime, timezone

            from nikita.db.repositories.user_repository import UserRepository

            repo = UserRepository(self._session)
            user = await repo.get(user_id)
            if user:
                user.cached_voice_prompt = prompt_text
                user.cached_voice_prompt_at = datetime.now(timezone.utc)
                self._logger.info(
                    "cached_voice_prompt_synced user_id=%s chars=%d",
                    user_id,
                    len(prompt_text),
                )
            else:
                self._logger.warning(
                    "cached_voice_prompt_sync_user_not_found user_id=%s", user_id
                )
        except Exception as e:
            self._logger.warning(
                "cached_voice_prompt_sync_failed user_id=%s error=%s",
                user_id,
                str(e),
            )
