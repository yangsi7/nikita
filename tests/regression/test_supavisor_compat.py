"""Regression test for Supavisor compatibility settings.

Prevents removal of connect_args that disable prepared statement caching,
which causes 'prepared statement does not exist' errors with Supabase pooler.

Adapted for Spec 109 database.py which uses flat connect_args (integer values)
and SQLAlchemy event listeners on engine.sync_engine.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSupavisorCompatibility:
    """Ensure database engine has Supavisor-compatible settings."""

    def test_engine_has_statement_cache_disabled(self):
        """connect_args must disable statement caching for Supavisor."""
        from nikita.db.database import get_async_engine
        get_async_engine.cache_clear()

        with patch("nikita.db.database.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database_url="postgresql+asyncpg://test:test@localhost/test",
                debug=False,
            )
            mock_engine = MagicMock()
            mock_engine.sync_engine = MagicMock()
            with patch("nikita.db.database.create_async_engine", return_value=mock_engine) as mock_create:
                with patch("nikita.db.database.event"):  # suppress event.listens_for
                    get_async_engine()

                call_kwargs = mock_create.call_args.kwargs
                assert "connect_args" in call_kwargs, (
                    "Missing connect_args — Supavisor requires statement_cache_size=0"
                )
                connect_args = call_kwargs["connect_args"]
                assert connect_args.get("statement_cache_size") == 0, (
                    "statement_cache_size must be 0 (integer) for Supavisor compatibility"
                )
                assert connect_args.get("prepared_statement_cache_size") == 0, (
                    "prepared_statement_cache_size must be 0 (integer) for Supavisor compatibility"
                )

        get_async_engine.cache_clear()

    def test_engine_has_pool_reset_on_return(self):
        """pool_reset_on_return=rollback ensures clean connections."""
        from nikita.db.database import get_async_engine
        get_async_engine.cache_clear()

        with patch("nikita.db.database.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                database_url="postgresql+asyncpg://test:test@localhost/test",
                debug=False,
            )
            mock_engine = MagicMock()
            mock_engine.sync_engine = MagicMock()
            with patch("nikita.db.database.create_async_engine", return_value=mock_engine) as mock_create:
                with patch("nikita.db.database.event"):
                    get_async_engine()

                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs.get("pool_reset_on_return") == "rollback"

        get_async_engine.cache_clear()
