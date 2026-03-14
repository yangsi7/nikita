"""Tests for ViceStage (Spec 114, GE-006).

RED tests — written before implementation. All should fail until:
1. nikita/pipeline/stages/vice.py is created
2. nikita/pipeline/orchestrator.py is updated (STAGE_DEFINITIONS + stages_total=11)
3. nikita/config/settings.py gets vice_pipeline_enabled
"""

from __future__ import annotations

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from nikita.pipeline.models import PipelineContext
from nikita.pipeline.orchestrator import PipelineOrchestrator


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_ctx(messages: list | None = None) -> PipelineContext:
    """Build a minimal PipelineContext with optional conversation messages."""
    ctx = PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(timezone.utc),
        platform="text",
        chapter=3,
    )
    if messages is not None:
        ctx.conversation = SimpleNamespace(messages=messages)
    return ctx


_TWO_MESSAGES = [
    {"role": "user", "content": "Hey Nikita, want to grab coffee?"},
    {"role": "nikita", "content": "I'd love that! When are you free?"},
]

_SETTINGS_ENABLED = {
    "supabase_url": "https://test.supabase.co",
    "supabase_key": "test-key",
    "supabase_service_role_key": "test-service-key",
    "database_url": "postgresql://test",
    "anthropic_api_key": "test-key",
    "vice_pipeline_enabled": True,
}

_SETTINGS_DISABLED = {**_SETTINGS_ENABLED, "vice_pipeline_enabled": False}


# ── AC-001: position in pipeline ──────────────────────────────────────────────

class TestViceStagePosition:
    """AC-001: ViceStage is between EmotionalStage and GameStateStage."""

    def test_vice_stage_position(self):
        """Inspect STAGE_DEFINITIONS class var — no instantiation needed."""
        names = [d[0] for d in PipelineOrchestrator.STAGE_DEFINITIONS]
        assert "vice" in names, "ViceStage not registered in STAGE_DEFINITIONS"
        idx = names.index("vice")
        assert names[idx - 1] == "emotional", (
            f"Expected 'emotional' before 'vice', got '{names[idx - 1]}'"
        )
        assert names[idx + 1] == "game_state", (
            f"Expected 'game_state' after 'vice', got '{names[idx + 1]}'"
        )
        # is_critical must be False
        assert PipelineOrchestrator.STAGE_DEFINITIONS[idx][2] is False


# ── AC-002: calls ViceService with last exchange ──────────────────────────────

class TestViceStageCallsService:
    """AC-002: ViceService.process_conversation called with correct args."""

    @pytest.mark.asyncio
    async def test_vice_stage_calls_service(self):
        """ViceService.process_conversation called with last exchange + chapter."""
        from nikita.pipeline.stages.vice import ViceStage

        ctx = _make_ctx(messages=_TWO_MESSAGES)
        stage = ViceStage()

        mock_result = {"discovered": 1, "updated": 0}
        mock_process = AsyncMock(return_value=mock_result)

        with (
            patch("nikita.config.settings.get_settings") as mock_settings,
            patch("nikita.engine.vice.service.ViceService") as MockViceService,
        ):
            settings = MagicMock()
            settings.vice_pipeline_enabled = True
            mock_settings.return_value = settings

            instance = MagicMock()
            instance.process_conversation = mock_process
            MockViceService.return_value = instance

            result = await stage._run(ctx)

        mock_process.assert_awaited_once()
        call_kwargs = mock_process.await_args.kwargs
        assert call_kwargs["user_id"] == ctx.user_id
        assert call_kwargs["user_message"] == "Hey Nikita, want to grab coffee?"
        assert call_kwargs["nikita_message"] == "I'd love that! When are you free?"
        assert call_kwargs["conversation_id"] == ctx.conversation_id
        assert call_kwargs["chapter"] == 3
        assert result == mock_result


# ── AC-003: flag disabled → skip ─────────────────────────────────────────────

class TestViceStageFlagDisabled:
    """AC-003: Stage is a no-op when vice_pipeline_enabled=False."""

    @pytest.mark.asyncio
    async def test_vice_stage_flag_disabled(self):
        """ViceService not called when flag is False."""
        from nikita.pipeline.stages.vice import ViceStage

        ctx = _make_ctx(messages=_TWO_MESSAGES)
        stage = ViceStage()

        with (
            patch("nikita.config.settings.get_settings") as mock_settings,
            patch("nikita.engine.vice.service.ViceService") as MockViceService,
        ):
            settings = MagicMock()
            settings.vice_pipeline_enabled = False
            mock_settings.return_value = settings

            result = await stage._run(ctx)

            MockViceService.assert_not_called()

        assert result["skipped"] is True
        assert result["reason"] == "vice_pipeline_disabled"


# ── AC-004: failure is non-fatal ──────────────────────────────────────────────

class TestViceStageFailureNonFatal:
    """AC-004: Stage failure returns StageResult.fail (pipeline continues)."""

    @pytest.mark.asyncio
    async def test_vice_stage_failure_non_fatal(self):
        """Non-fatal contract lives in BaseStage.execute() — test via execute()."""
        from nikita.pipeline.stages.vice import ViceStage

        ctx = _make_ctx(messages=_TWO_MESSAGES)
        stage = ViceStage()

        # Override _run to raise an exception
        stage._run = AsyncMock(side_effect=RuntimeError("LLM boom"))

        # Non-fatal because is_critical=False — BaseStage.execute() catches and returns StageResult.fail
        result = await stage.execute(ctx)

        assert result.success is False
        assert "LLM boom" in result.error


# ── AC-005: insufficient messages → skip ─────────────────────────────────────

class TestViceStageInsufficientMessages:
    """AC-005: Stage skipped when fewer than 2 valid messages."""

    @pytest.mark.asyncio
    async def test_vice_stage_single_message(self):
        """Single message → ViceService not called."""
        from nikita.pipeline.stages.vice import ViceStage

        ctx = _make_ctx(messages=[{"role": "user", "content": "Hello?"}])
        stage = ViceStage()

        with (
            patch("nikita.config.settings.get_settings") as mock_settings,
            patch("nikita.engine.vice.service.ViceService") as MockViceService,
        ):
            settings = MagicMock()
            settings.vice_pipeline_enabled = True
            mock_settings.return_value = settings

            result = await stage._run(ctx)

            MockViceService.assert_not_called()

        assert result["skipped"] is True
        assert result["reason"] == "insufficient_messages"

    @pytest.mark.asyncio
    async def test_vice_stage_no_conversation(self):
        """No conversation on ctx → skipped."""
        from nikita.pipeline.stages.vice import ViceStage

        ctx = _make_ctx(messages=None)  # ctx.conversation not set
        stage = ViceStage()

        with (
            patch("nikita.config.settings.get_settings") as mock_settings,
            patch("nikita.engine.vice.service.ViceService") as MockViceService,
        ):
            settings = MagicMock()
            settings.vice_pipeline_enabled = True
            mock_settings.return_value = settings

            result = await stage._run(ctx)

            MockViceService.assert_not_called()

        assert result["skipped"] is True


# ── _extract_last_exchange unit tests ─────────────────────────────────────────

class TestExtractLastExchange:
    """Pure helper — no mocks needed."""

    def _fn(self, messages):
        from nikita.pipeline.stages.vice import _extract_last_exchange
        return _extract_last_exchange(messages)

    def test_text_format_returns_pair(self):
        msgs = [
            {"role": "user", "content": "Hi"},
            {"role": "nikita", "content": "Hey!"},
        ]
        user_msg, nikita_msg = self._fn(msgs)
        assert user_msg == "Hi"
        assert nikita_msg == "Hey!"

    def test_empty_list_returns_none_pair(self):
        assert self._fn([]) == (None, None)

    def test_single_message_returns_none_pair(self):
        assert self._fn([{"role": "user", "content": "Hi"}]) == (None, None)

    def test_multiple_exchanges_returns_last_pair(self):
        msgs = [
            {"role": "user", "content": "First user"},
            {"role": "nikita", "content": "First nikita"},
            {"role": "user", "content": "Second user"},
            {"role": "nikita", "content": "Second nikita"},
        ]
        user_msg, nikita_msg = self._fn(msgs)
        assert user_msg == "Second user"
        assert nikita_msg == "Second nikita"

    def test_non_consecutive_user_roles_skips(self):
        """user, user, nikita — finds user+nikita pair at index 1+2."""
        msgs = [
            {"role": "user", "content": "First user"},
            {"role": "user", "content": "Second user"},
            {"role": "nikita", "content": "Nikita reply"},
        ]
        user_msg, nikita_msg = self._fn(msgs)
        assert user_msg == "Second user"
        assert nikita_msg == "Nikita reply"

    def test_empty_content_skipped(self):
        """Pair with empty content → continue searching."""
        msgs = [
            {"role": "user", "content": "Real user msg"},
            {"role": "nikita", "content": "Real nikita msg"},
            {"role": "user", "content": ""},
            {"role": "nikita", "content": ""},
        ]
        user_msg, nikita_msg = self._fn(msgs)
        assert user_msg == "Real user msg"
        assert nikita_msg == "Real nikita msg"

    def test_no_valid_pair_returns_none(self):
        """Only nikita messages → no user+nikita pair."""
        msgs = [
            {"role": "nikita", "content": "A"},
            {"role": "nikita", "content": "B"},
        ]
        assert self._fn(msgs) == (None, None)
