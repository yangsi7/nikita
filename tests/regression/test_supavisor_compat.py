"""Regression test for Supavisor compatibility settings.

Prevents removal of connect_args that disable prepared statement caching,
which causes 'prepared statement does not exist' errors with Supabase pooler.

Updated 2026-04-19 (GH #359): event listeners on engine.sync_engine were
removed because their sync cursor.execute() calls violated greenlet_spawn
in async background-task contexts. statement_timeout now flows through
asyncpg server_settings via connect_args (see nikita/db/database.py
_build_connect_args).
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
                db_statement_timeout_ms=30000,
            )
            mock_engine = MagicMock()
            mock_engine.sync_engine = MagicMock()
            with patch("nikita.db.database.create_async_engine", return_value=mock_engine) as mock_create:
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
                db_statement_timeout_ms=30000,
            )
            mock_engine = MagicMock()
            mock_engine.sync_engine = MagicMock()
            with patch("nikita.db.database.create_async_engine", return_value=mock_engine) as mock_create:
                get_async_engine()

                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs.get("pool_reset_on_return") == "rollback"

        get_async_engine.cache_clear()

    def test_connect_args_has_server_settings_statement_timeout(self):
        """GH #359: statement_timeout MUST be in asyncpg server_settings, not via @event listener."""
        from nikita.db.database import _build_connect_args
        from nikita.config.settings import Settings
        cargs = _build_connect_args(Settings(_env_file=None))
        assert "server_settings" in cargs, (
            "Missing server_settings — statement_timeout used to live in a sync "
            "@event.listens_for(connect/checkout) block which violated greenlet_spawn "
            "in async background-task contexts (Walk M 2026-04-19, GH #359)."
        )
        assert cargs["server_settings"].get("statement_timeout") == "30000"
