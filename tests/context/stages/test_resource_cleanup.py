"""Tests for resource cleanup in context managers.

Spec 037 US-1: Pipeline Reliability - Tests for AC-1.1 through AC-1.5.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestNikitaMemoryContextManager:
    """Tests for NikitaMemory async context manager (Spec 037 T1.1)."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        """AC-T1.1.1: __aenter__ returns self."""
        from nikita.memory.graphiti_client import NikitaMemory

        # Mock the graphiti to avoid actual initialization
        mock_graphiti = MagicMock()
        memory = NikitaMemory(user_id="test-user", graphiti=mock_graphiti)

        result = await memory.__aenter__()

        assert result is memory

    @pytest.mark.asyncio
    async def test_aexit_marks_as_closed(self):
        """AC-T1.1.2: __aexit__ marks client as closed."""
        from nikita.memory.graphiti_client import NikitaMemory

        mock_graphiti = MagicMock()
        memory = NikitaMemory(user_id="test-user", graphiti=mock_graphiti)

        await memory.__aenter__()
        assert not memory._closed

        await memory.__aexit__(None, None, None)
        assert memory._closed

    @pytest.mark.asyncio
    async def test_aexit_logs_exception_but_doesnt_suppress(self):
        """AC-T1.1.3: Exceptions are logged but not suppressed."""
        from nikita.memory.graphiti_client import NikitaMemory

        mock_graphiti = MagicMock()
        memory = NikitaMemory(user_id="test-user", graphiti=mock_graphiti)

        # Simulate exception during context
        result = await memory.__aexit__(ValueError, ValueError("test error"), None)

        # Should return False (don't suppress)
        assert result is False
        assert memory._closed

    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Test context manager works with async with statement."""
        from nikita.memory.graphiti_client import NikitaMemory

        mock_graphiti = MagicMock()

        async with NikitaMemory(user_id="test-user", graphiti=mock_graphiti) as memory:
            assert memory.user_id == "test-user"
            assert not memory._closed

        assert memory._closed

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test explicit close method."""
        from nikita.memory.graphiti_client import NikitaMemory

        mock_graphiti = MagicMock()
        memory = NikitaMemory(user_id="test-user", graphiti=mock_graphiti)

        assert not memory._closed
        await memory.close()
        assert memory._closed


class TestViceServiceContextManager:
    """Tests for ViceService async context manager (Spec 037 T1.2)."""

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        """AC-T1.2.1: __aenter__ returns self."""
        from nikita.engine.vice.service import ViceService

        async with ViceService() as vs:
            assert vs is not None
            assert isinstance(vs, ViceService)

    @pytest.mark.asyncio
    async def test_aexit_closes_scorer(self):
        """AC-T1.2.2: __aexit__ closes scorer session."""
        from nikita.engine.vice.service import ViceService

        vs = ViceService()
        vs._scorer.close = AsyncMock()

        await vs.__aenter__()
        await vs.__aexit__(None, None, None)

        vs._scorer.close.assert_called_once()
        assert vs._closed

    @pytest.mark.asyncio
    async def test_aexit_logs_exception_but_doesnt_suppress(self):
        """AC-T1.2.3: Exceptions are logged but not suppressed."""
        from nikita.engine.vice.service import ViceService

        vs = ViceService()
        vs._scorer.close = AsyncMock()

        result = await vs.__aexit__(RuntimeError, RuntimeError("test"), None)

        assert result is False
        assert vs._closed

    @pytest.mark.asyncio
    async def test_aexit_handles_close_error_gracefully(self):
        """Close errors during __aexit__ are logged, not raised."""
        from nikita.engine.vice.service import ViceService

        vs = ViceService()
        vs._scorer.close = AsyncMock(side_effect=Exception("close failed"))

        # Should not raise
        result = await vs.__aexit__(None, None, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test explicit close method."""
        from nikita.engine.vice.service import ViceService

        vs = ViceService()
        vs._scorer.close = AsyncMock()

        assert not vs._closed
        await vs.close()
        assert vs._closed
        vs._scorer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Close can be called multiple times safely."""
        from nikita.engine.vice.service import ViceService

        vs = ViceService()
        vs._scorer.close = AsyncMock()

        await vs.close()
        await vs.close()  # Should not raise

        # Scorer close should only be called once
        vs._scorer.close.assert_called_once()


class TestViceScorerClose:
    """Tests for ViceScorer close method."""

    @pytest.mark.asyncio
    async def test_close_commits_session(self):
        """Close commits the session."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        mock_session = AsyncMock()
        scorer._session = mock_session

        await scorer.close()

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        assert scorer._closed

    @pytest.mark.asyncio
    async def test_close_rollbacks_on_commit_error(self):
        """Close rollbacks if commit fails."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=Exception("commit failed"))
        scorer._session = mock_session

        await scorer.close()

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        assert scorer._closed

    @pytest.mark.asyncio
    async def test_close_without_session(self):
        """Close works even if no session was created."""
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        assert scorer._session is None

        await scorer.close()  # Should not raise

        assert scorer._closed


class TestResourceCleanupOnException:
    """Integration tests for resource cleanup when exceptions occur."""

    @pytest.mark.asyncio
    async def test_memory_cleaned_up_on_exception(self):
        """NikitaMemory resources cleaned up even when code raises."""
        from nikita.memory.graphiti_client import NikitaMemory

        mock_graphiti = MagicMock()
        memory = None

        with pytest.raises(ValueError):
            async with NikitaMemory(user_id="test", graphiti=mock_graphiti) as memory:
                raise ValueError("Simulated error")

        assert memory._closed

    @pytest.mark.asyncio
    async def test_vice_service_cleaned_up_on_exception(self):
        """ViceService resources cleaned up even when code raises."""
        from nikita.engine.vice.service import ViceService

        vs = None
        with pytest.raises(RuntimeError):
            async with ViceService() as vs:
                vs._scorer.close = AsyncMock()
                raise RuntimeError("Simulated error")

        assert vs._closed
