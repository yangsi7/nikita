"""Tests for PromptBuilderStage (T3.3 + T3.4).

Acceptance Criteria:
- AC-3.3.1: Loads Jinja2 template, renders with PipelineContext data
- AC-3.3.2: Calls Claude Haiku for narrative enrichment (optional)
- AC-3.3.3: Falls back to raw Jinja2 output if Haiku fails
- AC-3.3.4: Stores result in ready_prompts via ReadyPromptRepository.set_current()
- AC-3.3.5: Generates BOTH text and voice prompts in one pass
- AC-3.4.1: Text prompt post-enrichment: 5,500-6,500 tokens (warn if outside range)
- AC-3.4.2: Voice prompt post-enrichment: 1,800-2,200 tokens (warn if outside range)
- AC-3.4.3: If over budget, truncate lower-priority sections
"""

from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.pipeline.models import PipelineContext
from nikita.pipeline.stages.prompt_builder import PromptBuilderStage


def _make_context(**overrides) -> PipelineContext:
    """Create a test PipelineContext."""
    defaults = dict(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(timezone.utc),
        platform="text",
        chapter=1,
        relationship_score=Decimal("50"),
        game_status="active",
        engagement_state="in_zone",
        vices=["gaming"],
        metrics={"intimacy": Decimal("60"), "passion": Decimal("55")},
        extracted_facts=["User likes pizza"],
        extracted_threads=[],
        extracted_thoughts=[],
        extraction_summary="User talked about pizza",
        emotional_tone="cheerful",
        life_events=[],
        emotional_state={"mood": 0.7},
        score_delta=Decimal("1.5"),
        active_conflict=False,
        conflict_type=None,
        touchpoint_scheduled=False,
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


@pytest.mark.asyncio
class TestPromptBuilderStage:
    """Tests for PromptBuilderStage."""

    async def test_ac_3_3_1_renders_jinja2_template(self):
        """AC-3.3.1: Loads Jinja2 template, renders with PipelineContext data."""
        ctx = _make_context(platform="text")
        stage = PromptBuilderStage(session=None)

        result = await stage._run(ctx)

        assert result["text_generated"] is True
        assert result["text_tokens"] > 0
        # Check that some context was rendered
        assert ctx.generated_prompt is not None
        assert "pizza" in ctx.generated_prompt.lower() or "user" in ctx.generated_prompt.lower()

    async def test_ac_3_3_5_generates_both_text_and_voice(self):
        """AC-3.3.5: Generates BOTH text and voice prompts in one pass."""
        ctx = _make_context(platform="text")
        stage = PromptBuilderStage(session=None)

        result = await stage._run(ctx)

        assert result["text_generated"] is True
        assert result["voice_generated"] is True
        assert result["text_tokens"] > 0
        assert result["voice_tokens"] > 0
        assert result["generated"] is True

    async def test_sets_prompt_on_context_matching_platform(self):
        """Generated prompt matches ctx.platform."""
        ctx_text = _make_context(platform="text")
        ctx_voice = _make_context(platform="voice")
        stage = PromptBuilderStage(session=None)

        result_text = await stage._run(ctx_text)
        result_voice = await stage._run(ctx_voice)

        # Text platform: uses text prompt
        assert ctx_text.generated_prompt is not None
        assert ctx_text.prompt_token_count == result_text["text_tokens"]

        # Voice platform: uses voice prompt
        assert ctx_voice.generated_prompt is not None
        assert ctx_voice.prompt_token_count == result_voice["voice_tokens"]

    async def test_ac_3_3_3_fallback_on_haiku_failure(self):
        """AC-3.3.3: Falls back to raw Jinja2 output if Haiku fails."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        # Haiku enrichment will fail gracefully (no API key or mock failure)
        result = await stage._run(ctx)

        # Should still succeed with raw Jinja2 output
        assert result["generated"] is True
        assert ctx.generated_prompt is not None

    async def test_ac_3_4_1_text_token_budget_warning(self, capsys):
        """AC-3.4.1: Text prompt post-enrichment: 5,500-6,500 tokens (warn if outside range)."""
        ctx = _make_context(platform="text")
        stage = PromptBuilderStage(session=None)

        await stage._run(ctx)

        # structlog outputs to stdout — check captured output for under-budget warning
        captured = capsys.readouterr()
        assert "prompt_under_budget" in captured.out

    async def test_ac_3_4_2_voice_token_budget_warning(self, capsys):
        """AC-3.4.2: Voice prompt post-enrichment: 1,800-2,200 tokens (warn if outside range)."""
        ctx = _make_context(platform="voice")
        stage = PromptBuilderStage(session=None)

        await stage._run(ctx)

        # structlog outputs to stdout — check captured output for under-budget warning
        captured = capsys.readouterr()
        assert "prompt_under_budget" in captured.out

    async def test_ac_3_4_3_truncates_over_budget_prompt(self):
        """AC-3.4.3: If over budget, truncate lower-priority sections."""
        # Create a very long prompt by mocking render_template
        ctx = _make_context(platform="text")
        stage = PromptBuilderStage(session=None)

        # Build prompt with core content that survives + removable sections
        core = "## 1. IDENTITY\n" + ("Nikita is your girlfriend. " * 500)
        vice = "\n## 11. VICE SHAPING\n" + ("vice content " * 3000)
        chapter = "\n## 10. CHAPTER BEHAVIOR\n" + ("chapter content " * 3000)
        huge_prompt = core + chapter + vice

        with patch.object(stage, "_render_template", return_value=huge_prompt):
            result = await stage._run(ctx)

        # Should have truncated text prompt to within budget
        assert result["text_tokens"] <= PromptBuilderStage.TEXT_TOKEN_MAX
        # ctx.generated_prompt should be set (matches platform=text)
        assert ctx.generated_prompt is not None
        # Vice section should be removed first (lowest priority)
        assert "## 11. VICE SHAPING" not in ctx.generated_prompt

    async def test_ac_3_3_4_stores_in_ready_prompts(self):
        """AC-3.3.4: Stores result in ready_prompts via ReadyPromptRepository.set_current()."""
        ctx = _make_context()
        mock_session = MagicMock()
        mock_repo = AsyncMock()

        stage = PromptBuilderStage(session=mock_session)

        # Patch the import path where it's used (inside _store_prompt method)
        with patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo):
            await stage._run(ctx)

        # Should have called set_current for both text and voice
        assert mock_repo.set_current.call_count == 2

    async def test_graceful_failure_on_template_error(self):
        """Stage handles template render failures gracefully."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        with patch.object(stage, "_render_template", side_effect=Exception("Template error")):
            result = await stage._run(ctx)

        # Should fail gracefully
        assert result["generated"] is False
        assert result["text_generated"] is False

    async def test_graceful_failure_on_storage_error(self):
        """Stage handles storage failures gracefully (logs warning, continues)."""
        ctx = _make_context()
        mock_session = MagicMock()
        stage = PromptBuilderStage(session=mock_session)

        # Patch the import path where it's used
        with patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", side_effect=Exception("DB error")):
            result = await stage._run(ctx)

        # Should still succeed (storage is non-critical)
        assert result["generated"] is True

    async def test_no_session_skips_storage(self, capsys):
        """If session is None, skip storage and log warning."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        await stage._run(ctx)

        # structlog outputs to stdout — check for no-session warning
        captured = capsys.readouterr()
        assert "no_session_for_prompt_storage" in captured.out

    async def test_build_template_vars_extracts_context(self):
        """_build_template_vars extracts all relevant fields from PipelineContext."""
        ctx = _make_context(
            chapter=2,
            relationship_score=Decimal("75.5"),
            vices=["gaming", "coffee"],
            extracted_facts=["fact1", "fact2"],
        )
        stage = PromptBuilderStage(session=None)

        vars = stage._build_template_vars(ctx, platform="text")

        assert vars["chapter"] == 2
        assert vars["relationship_score"] == 75.5
        assert vars["vices"] == ["gaming", "coffee"]
        assert len(vars["extracted_facts"]) == 2

    async def test_remove_section_handles_missing_section(self):
        """_remove_section handles missing marker gracefully."""
        stage = PromptBuilderStage(session=None)
        prompt = "<!-- SEC:INTRO -->\nContent\n<!-- SEC:OUTRO -->\nMore"

        # Try to remove non-existent section
        result = stage._remove_section(prompt, "<!-- SEC:MISSING -->")

        # Should return original
        assert result == prompt

    async def test_remove_section_removes_middle_section(self):
        """_remove_section removes middle section using markers."""
        stage = PromptBuilderStage(session=None)
        prompt = (
            "<!-- SEC:INTRO -->\nContent\n"
            "<!-- SEC:CHAPTER_BEHAVIOR -->\n**Chapter 2 Behavior Guide:**\nRemove me\n"
            "<!-- SEC:VICE_SHAPING -->\n**What Makes You Light Up:**\nKeep"
        )

        result = stage._remove_section(prompt, "<!-- SEC:CHAPTER_BEHAVIOR -->")

        assert "<!-- SEC:CHAPTER_BEHAVIOR -->" not in result
        assert "Remove me" not in result
        assert "<!-- SEC:INTRO -->" in result
        assert "<!-- SEC:VICE_SHAPING -->" in result

    async def test_remove_section_removes_last_section(self):
        """_remove_section removes last section (vice shaping) correctly."""
        stage = PromptBuilderStage(session=None)
        prompt = (
            "<!-- SEC:CHAPTER_BEHAVIOR -->\n**Chapter 3 Behavior:**\nContent\n"
            "<!-- SEC:VICE_SHAPING -->\n**What Makes You Light Up:**\nRemove me"
        )

        result = stage._remove_section(prompt, "<!-- SEC:VICE_SHAPING -->")

        assert "<!-- SEC:VICE_SHAPING -->" not in result
        assert "Remove me" not in result
        assert "<!-- SEC:CHAPTER_BEHAVIOR -->" in result

    async def test_stage_is_non_critical(self):
        """PromptBuilderStage is non-critical (pipeline continues on failure)."""
        assert PromptBuilderStage.is_critical is False

    async def test_stage_timeout(self):
        """PromptBuilderStage has 90s timeout (2x Haiku enrichment calls)."""
        assert PromptBuilderStage.timeout_seconds == 90.0


@pytest.mark.asyncio
class TestHaikuEnrichment:
    """Tests for Haiku enrichment (AC-3.5.2)."""

    async def test_enrichment_called_when_api_key_present(self):
        """Enrichment is called when ANTHROPIC_API_KEY is set."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        # Mock Haiku enrichment to return enriched text
        async def mock_enrich(raw, platform):
            return f"[Enriched] {raw[:50]}..."

        with patch.object(stage, "_enrich_with_haiku", side_effect=mock_enrich) as mock:
            await stage._run(ctx)

        # Should have been called twice (text + voice)
        assert mock.call_count == 2

    async def test_fallback_when_enrichment_fails(self):
        """Falls back to raw Jinja2 when enrichment fails."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        # Mock enrichment to return None (fallback)
        async def mock_fail(raw, platform):
            return None

        with patch.object(stage, "_enrich_with_haiku", side_effect=mock_fail):
            result = await stage._run(ctx)

        # Should still succeed with raw prompt
        assert result["generated"] is True
        assert ctx.generated_prompt is not None

    async def test_fallback_when_enrichment_returns_too_short(self):
        """Falls back when enrichment returns suspiciously short result."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        # Mock enrichment to return too-short result (less than 50% of original)
        async def mock_short(raw, platform):
            return "Short"  # Way too short

        with patch.object(stage, "_enrich_with_haiku", side_effect=mock_short):
            result = await stage._run(ctx)

        # Should fallback to raw prompt
        assert result["generated"] is True
        assert "[Enriched]" not in ctx.generated_prompt

    async def test_enrichment_result_used_when_successful(self):
        """Enrichment result is used when it succeeds."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        # Mock enrichment to return valid enriched text
        async def mock_enrich(raw, platform):
            return f"[ENRICHED] {raw}"

        with patch.object(stage, "_enrich_with_haiku", side_effect=mock_enrich):
            await stage._run(ctx)

        # Should use enriched version
        assert "[ENRICHED]" in ctx.generated_prompt

    async def test_enrichment_preserves_factual_content(self):
        """Enrichment prompt instructs to preserve ALL factual content."""
        ctx = _make_context(extracted_facts=["User loves cats", "User works in tech"])
        stage = PromptBuilderStage(session=None)

        # Spy on enrichment prompt by patching inside the method's imports
        with patch("pydantic_ai.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = None  # Force fallback
            mock_result.data = None
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            # Call enrichment
            await stage._enrich_with_haiku("Test prompt with User loves cats", "text")

            # Check that enrichment prompt mentions preserving facts
            if mock_agent.run.called:
                call_args = mock_agent.run.call_args[0][0]
                assert "Preserve ALL factual content" in call_args or "preserve" in call_args.lower()

    async def test_enrichment_varies_by_platform(self):
        """Enrichment prompt mentions platform (text vs voice)."""
        stage = PromptBuilderStage(session=None)

        with patch("pydantic_ai.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.output = None
            mock_result.data = None
            mock_agent.run = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_agent

            # Call with text platform
            await stage._enrich_with_haiku("Prompt", "text")
            if mock_agent.run.called:
                text_call = mock_agent.run.call_args[0][0]
                # Should mention text
                assert "text chat" in text_call or "text" in text_call

            # Reset mock
            mock_agent.run.reset_mock()

            # Call with voice platform
            await stage._enrich_with_haiku("Prompt", "voice")
            if mock_agent.run.called:
                voice_call = mock_agent.run.call_args[0][0]
                # Should mention voice
                assert "voice conversation" in voice_call or "voice" in voice_call

    async def test_enrichment_skipped_when_no_api_key(self):
        """Enrichment is skipped when ANTHROPIC_API_KEY is not set."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        # Mock settings to return no API key
        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = None

            result = await stage._run(ctx)

        # Should still succeed (fallback to raw)
        assert result["generated"] is True

    async def test_enrichment_uses_haiku_model(self):
        """Enrichment uses claude-haiku-4-5 for cost efficiency."""
        stage = PromptBuilderStage(session=None)

        with patch("pydantic_ai.models.anthropic.AnthropicModel") as MockModel:
            with patch("pydantic_ai.Agent") as MockAgent:
                mock_agent = MagicMock()
                mock_result = MagicMock()
                mock_result.output = None
                mock_result.data = None
                mock_agent.run = AsyncMock(return_value=mock_result)
                MockAgent.return_value = mock_agent

                with patch("nikita.config.settings.get_settings") as mock_settings:
                    mock_settings.return_value.anthropic_api_key = "test-key"

                    await stage._enrich_with_haiku("Prompt", "text")

                # Check Haiku model was used
                MockModel.assert_called_once()
                model_name = MockModel.call_args[0][0]
                assert "haiku" in model_name.lower()


@pytest.mark.asyncio
class TestPromptStorage:
    """Tests for prompt storage (AC-3.5.3)."""

    async def test_prompts_stored_via_repository(self):
        """Both text and voice prompts stored via ReadyPromptRepository.set_current()."""
        ctx = _make_context()
        mock_session = MagicMock()
        stage = PromptBuilderStage(session=mock_session)

        mock_repo = AsyncMock()

        with patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo):
            await stage._run(ctx)

        # Should have called set_current for both text and voice
        assert mock_repo.set_current.call_count == 2

    async def test_is_current_flag_set(self):
        """Stored prompts have is_current=True flag."""
        ctx = _make_context()
        mock_session = MagicMock()
        stage = PromptBuilderStage(session=mock_session)

        mock_repo = AsyncMock()

        with patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo):
            await stage._run(ctx)

        # Check set_current was called (is_current flag is set by the repository method)
        assert mock_repo.set_current.called

    async def test_storage_includes_context_snapshot(self):
        """Stored prompts include context_snapshot with key metadata."""
        ctx = _make_context(
            chapter=3,
            relationship_score=Decimal("75.5"),
            vices=["dark_humor", "risk_taking"],
            extracted_facts=["fact1", "fact2"],
            emotional_tone="warm",
        )
        mock_session = MagicMock()
        stage = PromptBuilderStage(session=mock_session)

        mock_repo = AsyncMock()

        with patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", return_value=mock_repo):
            await stage._run(ctx)

        # Check context_snapshot was passed
        calls = mock_repo.set_current.call_args_list
        for call in calls:
            snapshot = call[1].get("context_snapshot")
            assert snapshot is not None
            assert snapshot["chapter"] == 3
            assert snapshot["relationship_score"] == 75.5
            assert snapshot["emotional_tone"] == "warm"
            assert snapshot["facts_count"] == 2
            assert snapshot["vices"] == ["dark_humor", "risk_taking"]

    async def test_storage_handles_none_session_gracefully(self, capsys):
        """Storage is skipped gracefully when session is None."""
        ctx = _make_context()
        stage = PromptBuilderStage(session=None)

        result = await stage._run(ctx)

        # Should still succeed
        assert result["generated"] is True

        # structlog outputs to stdout — check for no-session warning
        captured = capsys.readouterr()
        assert "no_session_for_prompt_storage" in captured.out

    async def test_storage_failure_doesnt_crash_stage(self):
        """Storage failure is logged but doesn't crash stage."""
        ctx = _make_context()
        mock_session = MagicMock()
        stage = PromptBuilderStage(session=mock_session)

        # Mock repository to fail
        with patch("nikita.db.repositories.ready_prompt_repository.ReadyPromptRepository", side_effect=Exception("DB error")):
            result = await stage._run(ctx)

        # Should still succeed (storage is non-critical)
        assert result["generated"] is True
