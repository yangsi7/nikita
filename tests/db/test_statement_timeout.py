"""Tests for configurable statement_timeout (GH #83) + engine listener regression (GH #359)."""
from unittest.mock import MagicMock, patch
import pytest
from nikita.config.settings import Settings


class TestStatementTimeoutConfig:
    """Verify statement_timeout is configurable via settings."""

    def test_default_is_30000ms(self):
        """Default db_statement_timeout_ms should be 30000."""
        settings = Settings(
            _env_file=None,  # Don't read .env
        )
        assert settings.db_statement_timeout_ms == 30000

    def test_validation_minimum(self):
        """Must be >= 1000ms."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(_env_file=None, db_statement_timeout_ms=500)

    def test_validation_maximum(self):
        """Must be <= 120000ms."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(_env_file=None, db_statement_timeout_ms=200000)

    def test_custom_value_accepted(self):
        """Custom value within range should be accepted."""
        settings = Settings(_env_file=None, db_statement_timeout_ms=60000)
        assert settings.db_statement_timeout_ms == 60000


class TestEngineConnectArgs:
    """Regression guard for GH #359 — sync cursor in async listeners.

    Walk M (2026-04-19) caught:
        nikita.onboarding.handoff - WARNING - Pipeline bootstrap failed:
        greenlet_spawn has not been called; can't call await_only() here.

    Root cause: @event.listens_for(engine.sync_engine, "connect"|"checkout")
    blocks ran sync cursor.execute("ROLLBACK") + cursor.execute("SET
    statement_timeout=...") inside async coroutine context. asyncpg's DBAPI
    wrapper requires await_only() to be inside greenlet_spawn. Background-task
    DB writes (handoff.py:283 → social_circle_repository.flush) hit this on
    every fresh pool checkout.

    Fix: drop the listeners; use asyncpg-native server_settings in connect_args
    + rely on pool_reset_on_return='rollback' (already configured) for cleanup.
    """

    def test_no_event_listeners_on_engine(self, monkeypatch):
        """Engine MUST NOT have nikita-defined @event.listens_for callbacks (greenlet-unsafe)."""
        # CI env has no DATABASE_URL; stub one so create_async_engine() can build
        # the engine shell. We only inspect dispatch listeners, never execute queries.
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://stub:stub@localhost/stub")

        from nikita.config.settings import get_settings
        from nikita.db.database import get_async_engine

        get_settings.cache_clear()
        get_async_engine.cache_clear()
        engine = get_async_engine()
        # When no listener is registered, dispatch.<event> raises AttributeError.
        # Treat absence as "no custom listener" (the desired post-fix state).
        for event_name in ("connect", "checkout"):
            try:
                listeners = list(getattr(engine.sync_engine.dispatch, event_name))
            except AttributeError:
                continue  # no listeners registered = pass
            custom = [
                fn for fn in listeners
                if getattr(fn, "__module__", "").startswith("nikita.db.database")
            ]
            assert custom == [], (
                f"Greenlet-unsafe {event_name} listener present: {custom}. "
                "Use connect_args server_settings + pool_reset_on_return='rollback' — see GH #359."
            )

    def test_statement_timeout_in_server_settings(self):
        """_build_connect_args MUST set statement_timeout via asyncpg server_settings."""
        from nikita.db.database import _build_connect_args

        cargs = _build_connect_args(Settings(_env_file=None))
        assert "server_settings" in cargs, (
            f"connect_args missing server_settings: {cargs}. See GH #359."
        )
        st = cargs["server_settings"].get("statement_timeout")
        assert st is not None and st != "", (
            f"server_settings.statement_timeout missing or empty: {cargs}"
        )
        # Default 30000ms (3 zeros means raw asyncpg syntax; pg accepts as 'milliseconds')
        assert st == "30000", f"Expected '30000' (default), got {st!r}"

    def test_statement_cache_disabled(self):
        """Supavisor compat — both prepared_statement_cache_size and statement_cache_size = 0."""
        from nikita.db.database import _build_connect_args

        cargs = _build_connect_args(Settings(_env_file=None))
        assert cargs["statement_cache_size"] == 0
        assert cargs["prepared_statement_cache_size"] == 0
