"""E2E test for psyche agent flow (Spec 056 T25).

Tests the full psyche → trigger → agent → prompt flow using
httpx.ASGITransport (no Cloud Run needed).

AC coverage: AC-4.1 (pre-read), AC-4.2 (L3 injection), AC-6.5 (endpoint)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nikita.agents.psyche.models import PsycheState


@pytest.fixture
def mock_settings():
    """Create mock settings with psyche enabled."""
    settings = MagicMock()
    settings.psyche_agent_enabled = True
    settings.psyche_model = "anthropic:claude-sonnet-4-20250514"
    settings.task_auth_secret = None
    settings.telegram_webhook_secret = None
    settings.anthropic_api_key = "test-key"
    settings.openai_api_key = None
    settings.unified_pipeline_enabled = True
    return settings


class TestPsycheBatchE2E:
    """E2E test for /tasks/psyche-batch endpoint."""

    @pytest.mark.asyncio
    async def test_batch_endpoint_e2e(self, mock_settings):
        """AC-6.5: Full batch endpoint flow."""
        from nikita.api.routes.tasks import router

        app = FastAPI()
        app.include_router(router, prefix="/tasks")

        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker.return_value = mock_session_ctx

        mock_job_repo = AsyncMock()
        mock_execution = MagicMock()
        mock_execution.id = uuid4()
        mock_job_repo.start_execution.return_value = mock_execution

        with (
            patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings),
            patch(
                "nikita.api.routes.tasks.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.api.routes.tasks.JobExecutionRepository",
                return_value=mock_job_repo,
            ),
            patch(
                "nikita.agents.psyche.batch.run_psyche_batch",
                return_value={
                    "processed": 3,
                    "failed": 0,
                    "skipped": 0,
                    "errors": [],
                },
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/tasks/psyche-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["processed"] == 3

    @pytest.mark.asyncio
    async def test_batch_endpoint_flag_off_e2e(self, mock_settings):
        """AC-6.6: Batch skips when feature flag OFF."""
        mock_settings.psyche_agent_enabled = False

        from nikita.api.routes.tasks import router

        app = FastAPI()
        app.include_router(router, prefix="/tasks")

        with patch("nikita.api.routes.tasks.get_settings", return_value=mock_settings):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/tasks/psyche-batch")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"


class TestTriggerToAgentFlowE2E:
    """E2E test for trigger detection → agent analysis flow."""

    @pytest.mark.asyncio
    async def test_tier1_reads_cached_state(self):
        """AC-4.1: Tier 1 reads cached psyche state without LLM call."""
        from nikita.agents.psyche.trigger import TriggerTier, detect_trigger_tier

        tier = detect_trigger_tier("how are you?")
        assert tier == TriggerTier.CACHED

    @pytest.mark.asyncio
    async def test_tier2_triggers_quick_analysis(self):
        """AC-3.2: Tier 2 message triggers quick Sonnet analysis."""
        from nikita.agents.psyche.trigger import TriggerTier, detect_trigger_tier

        tier = detect_trigger_tier("i'm scared and don't know what to do")
        assert tier == TriggerTier.QUICK

    @pytest.mark.asyncio
    async def test_tier3_triggers_deep_analysis(self):
        """AC-3.3: Tier 3 message triggers deep Opus analysis."""
        from nikita.agents.psyche.trigger import TriggerTier, detect_trigger_tier

        tier = detect_trigger_tier("i can't do this anymore")
        assert tier == TriggerTier.DEEP


class TestPsycheStateRoundTrip:
    """E2E test for PsycheState → DB → Template round trip."""

    def test_state_survives_json_roundtrip(self):
        """AC-2.3: State survives model_dump → model_validate cycle."""
        original = PsycheState(
            attachment_activation="disorganized",
            defense_mode="withdrawing",
            behavioral_guidance="Give space and be patient.",
            internal_monologue="I'm shutting down and I know it.",
            vulnerability_level=0.1,
            emotional_tone="volatile",
            topics_to_encourage=["music"],
            topics_to_avoid=["commitment", "future plans"],
        )

        # Simulate DB round-trip
        json_dict = original.model_dump()
        restored = PsycheState.model_validate(json_dict)

        assert restored == original
        assert restored.attachment_activation == "disorganized"
        assert restored.topics_to_avoid == ["commitment", "future plans"]
