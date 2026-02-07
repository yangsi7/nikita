"""Prompt builder stage - generates system prompt (T3.3 + T3.4).

Generates BOTH text and voice prompts in one pass.
Non-critical: failure does not stop the pipeline.

Implements:
- AC-3.3.1: Loads Jinja2 template, renders with PipelineContext data
- AC-3.3.2: Calls Claude Haiku for narrative enrichment (optional)
- AC-3.3.3: Falls back to raw Jinja2 output if Haiku fails
- AC-3.3.4: Stores result in ready_prompts via ReadyPromptRepository.set_current()
- AC-3.3.5: Generates BOTH text and voice prompts in one pass
- AC-3.4.1: Text prompt post-enrichment: 5,500-6,500 tokens (warn if outside range)
- AC-3.4.2: Voice prompt post-enrichment: 1,800-2,200 tokens (warn if outside range)
- AC-3.4.3: If over budget, truncate lower-priority sections (Vice → Chapter → Psychology)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import logging

from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession


class PromptBuilderStage(BaseStage):
    """Generate system prompts for both text and voice platforms.

    Renders Jinja2 templates with PipelineContext data, optionally enriches
    with Claude Haiku for narrative depth, enforces token budgets, and stores
    results in ready_prompts table.
    """

    name = "prompt_builder"
    is_critical = False
    timeout_seconds = 30.0

    # Token budgets (AC-3.4.1, AC-3.4.2)
    TEXT_TOKEN_MIN = 5500
    TEXT_TOKEN_MAX = 6500
    VOICE_TOKEN_MIN = 1800
    VOICE_TOKEN_MAX = 2200

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Generate system prompts for both text and voice platforms.

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
        results = {}

        # Generate text prompt (AC-3.3.5)
        text_prompt, text_tokens, text_time = await self._generate_prompt(ctx, "text")
        results["text_generated"] = text_prompt is not None
        results["text_tokens"] = text_tokens
        results["text_time_ms"] = text_time

        # Generate voice prompt (AC-3.3.5)
        voice_prompt, voice_tokens, voice_time = await self._generate_prompt(ctx, "voice")
        results["voice_generated"] = voice_prompt is not None
        results["voice_tokens"] = voice_tokens
        results["voice_time_ms"] = voice_time

        # Set on context (use the prompt matching ctx.platform)
        # Note: Empty string after truncation is a valid (though degenerate) result
        if ctx.platform == "voice" and voice_prompt is not None:
            ctx.generated_prompt = voice_prompt
            ctx.prompt_token_count = voice_tokens
        elif text_prompt is not None:
            ctx.generated_prompt = text_prompt
            ctx.prompt_token_count = text_tokens

        results["generated"] = results["text_generated"] or results["voice_generated"]
        return results

    async def _generate_prompt(
        self, ctx: PipelineContext, platform: str
    ) -> tuple[str | None, int, float]:
        """Generate a single prompt for a platform.

        Args:
            ctx: Pipeline context with user state and extraction results.
            platform: 'text' or 'voice'.

        Returns:
            (prompt_text, token_count, generation_time_ms)
        """
        start = time.perf_counter()

        # Step 1: Render Jinja2 template (AC-3.3.1)
        template_name = "system_prompt.j2" if platform == "text" else "voice_prompt.j2"
        try:
            raw_prompt = self._render_template(template_name, ctx)
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

    def _render_template(self, template_name: str, ctx: PipelineContext) -> str:
        """Render a Jinja2 template with PipelineContext data.

        Args:
            template_name: Template file name (e.g., "system_prompt.j2").
            ctx: Pipeline context.

        Returns:
            Rendered prompt text.
        """
        from nikita.pipeline.templates import render_template

        # Build template context dict from PipelineContext
        template_vars = self._build_template_vars(ctx)
        return render_template(template_name, **template_vars)

    def _build_template_vars(self, ctx: PipelineContext) -> dict:
        """Convert PipelineContext to flat dict for Jinja2 template.

        Args:
            ctx: Pipeline context.

        Returns:
            Template variables dict.
        """
        return {
            # Core
            "platform": ctx.platform,
            "user_id": str(ctx.user_id),
            "conversation_id": str(ctx.conversation_id),
            # User state
            "chapter": ctx.chapter,
            "relationship_score": float(ctx.relationship_score),
            "game_status": ctx.game_status,
            "engagement_state": ctx.engagement_state,
            "vices": ctx.vices,
            "metrics": {k: float(v) for k, v in ctx.metrics.items()} if ctx.metrics else {},
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
            "active_conflict": ctx.active_conflict,
            "conflict_type": ctx.conflict_type,
            # Touchpoints
            "touchpoint_scheduled": ctx.touchpoint_scheduled,
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

            # Use Haiku for cost efficiency
            model = AnthropicModel("claude-haiku-4-5-20251001", api_key=settings.anthropic_api_key)
            agent = Agent(model=model)
            result = await agent.run(enrichment_prompt)

            if result.data and len(result.data) > len(raw_prompt) * 0.5:
                return result.data
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
                pipeline_version="042-v1",
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
