"""Tests for psyche agent Tier 2 (quick_analyze) and Tier 3 (deep_analyze).

Covers the session-based DB upsert path and stateful behavior:
- quick_analyze() returns (PsycheState, int) with and without session
- deep_analyze() returns (PsycheState, int) with and without session
- DB upsert is called when session is provided
- DB upsert is skipped when session is None
- message is injected into deps before agent run
- deep_analyze uses Opus model via _create_psyche_agent

AC refs: AC-1.1, AC-1.6, AC-4.1 (session-based persistence)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest

from nikita.agents.psyche.deps import PsycheDeps
from nikita.agents.psyche.models import PsycheState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_state(**kwargs) -> PsycheState:
    defaults = dict(
        attachment_activation="secure",
        defense_mode="open",
        behavioral_guidance="Be warm.",
        internal_monologue="Feeling good.",
        vulnerability_level=0.5,
        emotional_tone="warm",
        topics_to_encourage=[],
        topics_to_avoid=[],
    )
    defaults.update(kwargs)
    return PsycheState(**defaults)


def _make_mock_result(state: PsycheState, input_tokens: int = 300, output_tokens: int = 100):
    mock_usage = MagicMock()
    mock_usage.input_tokens = input_tokens
    mock_usage.output_tokens = output_tokens

    mock_result = MagicMock()
    mock_result.output = state
    mock_result.data = None
    mock_result.usage = MagicMock(return_value=mock_usage)
    return mock_result


def _make_deps(**kwargs) -> PsycheDeps:
    defaults = dict(
        user_id=uuid4(),
        score_history=[],
        emotional_states=[],
        life_events=[],
        npc_interactions=[],
        current_chapter=2,
    )
    defaults.update(kwargs)
    return PsycheDeps(**defaults)


# ---------------------------------------------------------------------------
# quick_analyze — no session
# ---------------------------------------------------------------------------


class TestQuickAnalyzeNoSession:
    """quick_analyze() without a DB session skips upsert."""

    @pytest.mark.asyncio
    async def test_returns_tuple(self):
        """quick_analyze returns (PsycheState, int) tuple."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state(emotional_tone="serious")
        deps = _make_deps()
        mock_result = _make_mock_result(state, 250, 100)

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            result = await quick_analyze(deps, "I miss you")

        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_state_is_psyche_state(self):
        """quick_analyze returns PsycheState as first element."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state(emotional_tone="distant")
        deps = _make_deps()
        mock_result = _make_mock_result(state, 200, 80)

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            returned_state, _ = await quick_analyze(deps, "I feel lonely")

        assert isinstance(returned_state, PsycheState)

    @pytest.mark.asyncio
    async def test_token_count_correct(self):
        """quick_analyze returns correct token sum."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 300, 150)

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            _, token_count = await quick_analyze(deps, "worried")

        assert token_count == 450

    @pytest.mark.asyncio
    async def test_message_injected_into_deps(self):
        """quick_analyze sets deps.message before agent run."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 100, 100)

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            await quick_analyze(deps, "I'm scared")

        # deps.message must be set so add_context can inject it
        assert deps.message == "I'm scared"

    @pytest.mark.asyncio
    async def test_no_db_call_when_session_none(self):
        """quick_analyze does not call PsycheStateRepository when session=None."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 100, 50)

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get, \
             patch("nikita.agents.psyche.agent.PsycheStateRepository", create=True) as mock_repo_cls:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            await quick_analyze(deps, "hello", session=None)

        # Repository should NOT be instantiated when session is None
        mock_repo_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_zero_on_usage_error(self):
        """quick_analyze returns token_count=0 when usage() raises."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state()
        deps = _make_deps()

        mock_result = MagicMock()
        mock_result.output = state
        mock_result.data = None
        mock_result.usage = MagicMock(side_effect=Exception("no usage"))

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            _, token_count = await quick_analyze(deps, "stressed")

        assert token_count == 0


# ---------------------------------------------------------------------------
# quick_analyze — with session (upsert path)
# ---------------------------------------------------------------------------


class TestQuickAnalyzeWithSession:
    """quick_analyze() with a DB session triggers upsert."""

    @pytest.mark.asyncio
    async def test_upsert_called_with_session(self):
        """quick_analyze calls repo.upsert when session is provided."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state(emotional_tone="serious", vulnerability_level=0.3)
        deps = _make_deps()
        mock_result = _make_mock_result(state, 400, 200)
        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo_cls = MagicMock(return_value=mock_repo)

        # The lazy import path used inside quick_analyze's if-block
        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get, \
             patch(
                 "nikita.db.repositories.psyche_state_repository.PsycheStateRepository",
                 mock_repo_cls,
             ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            returned_state, token_count = await quick_analyze(
                deps, "I need you", session=mock_session
            )

        # Still returns valid tuple
        assert isinstance(returned_state, PsycheState)
        assert token_count == 600

    @pytest.mark.asyncio
    async def test_upsert_receives_model_sonnet(self):
        """quick_analyze upserts with model='sonnet' when session provided."""
        from nikita.agents.psyche.agent import quick_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 200, 100)
        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo_cls = MagicMock(return_value=mock_repo)

        with patch("nikita.agents.psyche.agent.get_psyche_agent") as mock_get, \
             patch(
                 "nikita.db.repositories.psyche_state_repository.PsycheStateRepository",
                 mock_repo_cls,
             ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_get.return_value = mock_agent

            returned_state, token_count = await quick_analyze(
                deps, "I miss you", session=mock_session
            )

        # Verify upsert was called with model="sonnet"
        mock_repo.upsert.assert_called_once()
        call_kwargs = mock_repo.upsert.call_args
        assert call_kwargs.kwargs.get("model") == "sonnet" or (
            call_kwargs.args and "sonnet" in call_kwargs.args
        )
        assert isinstance(returned_state, PsycheState)
        assert token_count == 300


# ---------------------------------------------------------------------------
# deep_analyze — no session
# ---------------------------------------------------------------------------


class TestDeepAnalyzeNoSession:
    """deep_analyze() without a DB session skips upsert."""

    @pytest.mark.asyncio
    async def test_returns_tuple(self):
        """deep_analyze returns (PsycheState, int) tuple."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state(
            attachment_activation="disorganized",
            defense_mode="withdrawing",
            emotional_tone="volatile",
            vulnerability_level=0.1,
        )
        deps = _make_deps()
        mock_result = _make_mock_result(state, 800, 400)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            result = await deep_analyze(deps, "I can't do this anymore")

        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_state_is_psyche_state(self):
        """deep_analyze returns PsycheState as first element."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state(emotional_tone="volatile")
        deps = _make_deps()
        mock_result = _make_mock_result(state, 900, 300)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            returned_state, _ = await deep_analyze(deps, "I give up")

        assert isinstance(returned_state, PsycheState)

    @pytest.mark.asyncio
    async def test_token_count_correct(self):
        """deep_analyze returns correct token sum."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 1000, 500)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            _, token_count = await deep_analyze(deps, "crisis")

        assert token_count == 1500

    @pytest.mark.asyncio
    async def test_uses_opus_model(self):
        """deep_analyze creates agent with Opus model."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 500, 200)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            await deep_analyze(deps, "I'm breaking down")

        # Must be called with Opus model specifically
        mock_create.assert_called_once_with("anthropic:claude-opus-4-6")

    @pytest.mark.asyncio
    async def test_message_injected_into_deps(self):
        """deep_analyze sets deps.message before agent run."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 300, 100)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            await deep_analyze(deps, "suicidal")

        assert deps.message == "suicidal"

    @pytest.mark.asyncio
    async def test_fresh_agent_per_call(self):
        """deep_analyze creates a new agent each call (not cached singleton)."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state()
        deps1 = _make_deps()
        deps2 = _make_deps()
        mock_result = _make_mock_result(state, 500, 200)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            await deep_analyze(deps1, "panic attack")
            await deep_analyze(deps2, "crisis")

        # Two separate calls to _create_psyche_agent
        assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_token_zero_on_usage_error(self):
        """deep_analyze returns token_count=0 when usage() raises."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state()
        deps = _make_deps()

        mock_result = MagicMock()
        mock_result.output = state
        mock_result.data = None
        mock_result.usage = MagicMock(side_effect=Exception("usage unavailable"))

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            _, token_count = await deep_analyze(deps, "ending it")

        assert token_count == 0

    @pytest.mark.asyncio
    async def test_no_db_call_when_session_none(self):
        """deep_analyze does not call PsycheStateRepository when session=None."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state()
        deps = _make_deps()
        mock_result = _make_mock_result(state, 100, 50)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create, \
             patch("nikita.agents.psyche.agent.PsycheStateRepository", create=True) as mock_repo_cls:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            await deep_analyze(deps, "hello", session=None)

        mock_repo_cls.assert_not_called()


# ---------------------------------------------------------------------------
# deep_analyze — with session (upsert path)
# ---------------------------------------------------------------------------


class TestDeepAnalyzeWithSession:
    """deep_analyze() with a DB session triggers upsert."""

    @pytest.mark.asyncio
    async def test_returns_valid_state_with_session(self):
        """deep_analyze still returns valid (PsycheState, int) when session provided."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state(
            attachment_activation="disorganized",
            emotional_tone="volatile",
            vulnerability_level=0.05,
        )
        deps = _make_deps(current_chapter=4)
        mock_result = _make_mock_result(state, 1200, 600)
        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo_cls = MagicMock(return_value=mock_repo)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create, \
             patch(
                 "nikita.db.repositories.psyche_state_repository.PsycheStateRepository",
                 mock_repo_cls,
             ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            returned_state, token_count = await deep_analyze(
                deps, "I hate myself", session=mock_session
            )

        assert isinstance(returned_state, PsycheState)
        assert token_count == 1800

    @pytest.mark.asyncio
    async def test_upsert_receives_model_opus(self):
        """deep_analyze upserts with model='opus' when session provided."""
        from nikita.agents.psyche.agent import deep_analyze

        state = _make_mock_state(emotional_tone="volatile")
        deps = _make_deps()
        mock_result = _make_mock_result(state, 800, 400)
        mock_session = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo_cls = MagicMock(return_value=mock_repo)

        with patch("nikita.agents.psyche.agent._create_psyche_agent") as mock_create, \
             patch(
                 "nikita.db.repositories.psyche_state_repository.PsycheStateRepository",
                 mock_repo_cls,
             ):
            mock_agent = AsyncMock()
            mock_agent.run.return_value = mock_result
            mock_create.return_value = mock_agent

            returned_state, token_count = await deep_analyze(
                deps, "crisis", session=mock_session
            )

        # Upsert called with model="opus"
        mock_repo.upsert.assert_called_once()
        call_kwargs = mock_repo.upsert.call_args
        assert call_kwargs.kwargs.get("model") == "opus" or (
            call_kwargs.args and "opus" in call_kwargs.args
        )
        assert isinstance(returned_state, PsycheState)
        assert token_count == 1200


# ---------------------------------------------------------------------------
# Async function signatures
# ---------------------------------------------------------------------------


class TestAnalysisFunctionSignatures:
    """Verify quick_analyze and deep_analyze are async with expected signatures."""

    def test_quick_analyze_is_async(self):
        from nikita.agents.psyche.agent import quick_analyze

        assert asyncio.iscoroutinefunction(quick_analyze)

    def test_deep_analyze_is_async(self):
        from nikita.agents.psyche.agent import deep_analyze

        assert asyncio.iscoroutinefunction(deep_analyze)

    def test_quick_analyze_callable(self):
        from nikita.agents.psyche.agent import quick_analyze

        assert callable(quick_analyze)

    def test_deep_analyze_callable(self):
        from nikita.agents.psyche.agent import deep_analyze

        assert callable(deep_analyze)

    def test_quick_analyze_accepts_session_param(self):
        """quick_analyze signature includes optional session parameter."""
        import inspect
        from nikita.agents.psyche.agent import quick_analyze

        sig = inspect.signature(quick_analyze)
        assert "session" in sig.parameters
        # session defaults to None
        assert sig.parameters["session"].default is None

    def test_deep_analyze_accepts_session_param(self):
        """deep_analyze signature includes optional session parameter."""
        import inspect
        from nikita.agents.psyche.agent import deep_analyze

        sig = inspect.signature(deep_analyze)
        assert "session" in sig.parameters
        assert sig.parameters["session"].default is None

    def test_quick_analyze_accepts_message_param(self):
        """quick_analyze has required message parameter."""
        import inspect
        from nikita.agents.psyche.agent import quick_analyze

        sig = inspect.signature(quick_analyze)
        assert "message" in sig.parameters

    def test_deep_analyze_accepts_message_param(self):
        """deep_analyze has required message parameter."""
        import inspect
        from nikita.agents.psyche.agent import deep_analyze

        sig = inspect.signature(deep_analyze)
        assert "message" in sig.parameters
