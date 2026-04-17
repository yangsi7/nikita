"""Tests for nikita.config.settings.Settings (Spec 215 PR 215-A T5.2).

Currently covers only the heartbeat-engine fields (Spec 215 FR-020 rollback
contract). Other settings fields are exercised indirectly via the modules
that consume them; this file is the home for additions added by Spec 215+.
"""

import pytest

from nikita.config.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Reset the cached singleton between tests so env mutations take effect.

    Per .claude/rules/testing.md "Singleton Cache-Clearing": ``get_settings``
    is wrapped in ``@lru_cache`` so a once-loaded Settings instance survives
    later ``monkeypatch.setenv`` calls. Clearing the cache before AND after
    each test guarantees:

    1. The test reads its own env state (pre-clear ensures no carry-over from
       prior tests).
    2. Subsequent tests in the same suite are not poisoned by env mutations
       from this test (post-clear).
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestHeartbeatEngineSettings:
    """T5.2 — heartbeat_engine_enabled + heartbeat_cost_circuit_breaker_usd_per_day.

    AC-T5.2-001: heartbeat_engine_enabled defaults to False (rollback contract
                 per FR-020 — feature ships disabled).
    AC-T5.2-002: heartbeat_cost_circuit_breaker_usd_per_day defaults to 50.0
                 USD/day; mutation via env var reflected after cache_clear().
    """

    def test_heartbeat_engine_enabled_default_false(self):
        """AC-T5.2-001: rollback contract — flag defaults False (FR-020)."""
        settings = Settings()
        assert settings.heartbeat_engine_enabled is False, (
            "heartbeat_engine_enabled must default False per FR-020 rollback contract; "
            "shipping with True would silently activate the heartbeat loop on deploy."
        )

    def test_heartbeat_cost_circuit_breaker_default_50(self):
        """AC-T5.2-002: cost ceiling defaults to 50.0 USD/day."""
        settings = Settings()
        assert settings.heartbeat_cost_circuit_breaker_usd_per_day == 50.0

    def test_heartbeat_engine_enabled_env_override(self, monkeypatch):
        """env override flips the flag to True after cache_clear."""
        monkeypatch.setenv("HEARTBEAT_ENGINE_ENABLED", "true")
        get_settings.cache_clear()  # explicit per AC-T5.1-004 contract
        settings = get_settings()
        assert settings.heartbeat_engine_enabled is True

    def test_heartbeat_cost_circuit_breaker_env_override(self, monkeypatch):
        """env override changes the cost ceiling after cache_clear."""
        monkeypatch.setenv(
            "HEARTBEAT_COST_CIRCUIT_BREAKER_USD_PER_DAY", "100.0"
        )
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.heartbeat_cost_circuit_breaker_usd_per_day == 100.0
