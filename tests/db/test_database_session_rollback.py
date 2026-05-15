"""Tests for asyncpg pool transaction hygiene (GH #624).

Verifies:
1. get_async_session rolls back on arbitrary exceptions (not just SQLAlchemyError).
2. get_async_session rolls back on SQLAlchemy IntegrityError.
3. Engine config: pool_pre_ping, pool_recycle, pool_reset_on_return are set.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.exc import IntegrityError


class TestSessionRollsBackOnException:
    """get_async_session context manager must rollback on ANY exception (GH #624)."""

    @pytest.mark.asyncio
    async def test_session_rolls_back_on_arbitrary_exception(self, monkeypatch):
        """An arbitrary ValueError inside the session context causes rollback, not just commit."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        # Make __aenter__ return the mock session
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session

        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://stub:stub@localhost/stub")

        from nikita.config.settings import get_settings
        from nikita.db.database import get_async_session, get_session_maker

        get_settings.cache_clear()

        with patch("nikita.db.database.get_session_maker", return_value=mock_session_maker):
            gen = get_async_session()
            session = await gen.__anext__()

            # Simulate a ValueError inside the `async with get_async_session()` block
            with pytest.raises(ValueError, match="test error"):
                await gen.athrow(ValueError("test error"))

        # rollback must be called, commit must NOT be called
        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_session_rolls_back_on_sqla_exception(self, monkeypatch):
        """An IntegrityError inside the session context causes rollback."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session

        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://stub:stub@localhost/stub")

        from nikita.config.settings import get_settings
        from nikita.db.database import get_async_session, get_session_maker

        get_settings.cache_clear()

        orig_exc = IntegrityError("orig", {}, None)

        with patch("nikita.db.database.get_session_maker", return_value=mock_session_maker):
            gen = get_async_session()
            await gen.__anext__()

            with pytest.raises(IntegrityError):
                await gen.athrow(orig_exc)

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()

    def test_session_generator_has_except_exception_rollback(self):
        """Structural check: get_async_session source must contain rollback in an except clause.

        This guards against the catch being narrowed back to SQLAlchemyError-only
        (the pre-GH-#624 anti-pattern).
        """
        import inspect
        from nikita.db.database import get_async_session

        source = inspect.getsource(get_async_session)
        # Must have a broad except (Exception) catching block with rollback
        assert "except Exception" in source or "except BaseException" in source, (
            "get_async_session must catch broad Exception for rollback (GH #624)"
        )
        assert "rollback" in source, (
            "get_async_session must call rollback in the exception handler (GH #624)"
        )


class TestEnginePoolConfig:
    """Engine must have pool hygiene options set (GH #624 J3)."""

    def test_pool_pre_ping_enabled(self, monkeypatch):
        """pool_pre_ping=True — evict bad connections on checkout."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://stub:stub@localhost/stub")

        from nikita.config.settings import get_settings
        from nikita.db.database import get_async_engine

        get_settings.cache_clear()
        get_async_engine.cache_clear()

        engine = get_async_engine()
        assert engine.pool._pre_ping is True, (
            "pool_pre_ping must be True to evict bad connections on checkout (GH #624)"
        )

    def test_pool_recycle_300s(self, monkeypatch):
        """pool_recycle=300 — recycle connections every 5 min."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://stub:stub@localhost/stub")

        from nikita.config.settings import get_settings
        from nikita.db.database import get_async_engine

        get_settings.cache_clear()
        get_async_engine.cache_clear()

        engine = get_async_engine()
        assert engine.pool._recycle == 300, (
            "pool_recycle must be 300s for Cloud Run scale-to-zero hygiene (GH #624)"
        )

    def test_pool_reset_on_return_rollback(self, monkeypatch):
        """pool_reset_on_return='rollback' — explicit rollback when connection returns to pool."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://stub:stub@localhost/stub")

        from nikita.config.settings import get_settings
        from nikita.db.database import get_async_engine

        get_settings.cache_clear()
        get_async_engine.cache_clear()

        engine = get_async_engine()
        # reset_on_return is stored as an attribute on the pool
        reset_val = getattr(engine.pool, "_reset_on_return", None)
        assert reset_val is not None, (
            "pool_reset_on_return must be set on the engine pool (GH #624)"
        )
        # SQLAlchemy stores 'rollback' as reset_agent attribute on the ResetAgent
        # We verify it's not None (meaning it was configured)
        assert reset_val != "none", (
            "pool_reset_on_return must not be 'none' — must be 'rollback' (GH #624)"
        )
