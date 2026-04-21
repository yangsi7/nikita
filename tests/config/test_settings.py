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


# ---------------------------------------------------------------------------
# GH #374 — portal_url canonical-host regression guard
# ---------------------------------------------------------------------------


class TestPortalUrlCanonical:
    """GH #374 regression: settings.portal_url default must be the canonical
    host nikita-mygirl.com, NOT the stale portal-phi-orcin.vercel.app
    Vercel preview alias.

    Walk N (2026-04-20) caught a /start reply with a button URL host of
    portal-phi-orcin.vercel.app — driven by 5 production sites that fall
    back to that literal when ``settings.portal_url is None``. Cloud Run
    PORTAL_URL env var is unset; settings default is also None; the 5
    fallbacks fire. Fix: settings default = canonical, drop the 5
    fallbacks, set Cloud Run env var.

    Per .claude/rules/vercel-cors-canonical.md: canonical is apex
    nikita-mygirl.com (no redirect). Backend CORS allowlist already
    matches.
    """

    def test_portal_url_default_is_canonical(self):
        """AC-#374-001: settings.portal_url default must be canonical host."""
        settings = Settings()
        assert settings.portal_url == "https://nikita-mygirl.com", (
            f"settings.portal_url default drifted to {settings.portal_url!r}. "
            f"Should be canonical https://nikita-mygirl.com per Vercel "
            f"canonical-redirect setup (PR #294)."
        )

    def test_no_stale_portal_url_fallback_in_production_code(self):
        """AC-#374-002: zero hardcoded ``or "https://portal-phi-orcin..."``
        fallbacks remain in production code (nikita/ + portal/).

        Greps for the FALLBACK PATTERN (or "https://portal-phi-...") not
        the bare URL — comments documenting why the fallback was removed
        legitimately mention the alias and shouldn't trip the gate.

        Scope strictly to nikita/ + portal/ — historical references in
        .claude/, docs/, ROADMAP.md, event-stream.md, specs/archive/, and
        tests/ are out of scope (separate hygiene PR).
        """
        import subprocess

        # Match `or "https://portal-phi-orcin..."` — the actual bug pattern.
        # Uses POSIX `grep -rE` (always available on CI runners; `rg` is not
        # installed on the GitHub Actions Ubuntu image by default).
        result = subprocess.run(
            [
                "grep",
                "-rlE",
                r'or[[:space:]]+"https://portal-phi-orcin',
                "nikita/",
                "portal/",
            ],
            capture_output=True,
            text=True,
        )
        # grep exits 0 if matches found, 1 if none, 2 on error. Want exit 1.
        assert result.returncode == 1, (
            f"Stale portal-phi-orcin fallback patterns remain in production code:\n"
            f"{result.stdout}\n"
            f"All `or 'https://portal-phi-orcin.vercel.app'` fallbacks must be "
            f"removed; settings.portal_url default is now canonical so the "
            f"fallback is dead code (#374)."
        )

    def test_portal_url_env_override(self, monkeypatch):
        """env override changes portal_url after cache_clear (sanity check)."""
        monkeypatch.setenv("PORTAL_URL", "https://staging.nikita-mygirl.com")
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.portal_url == "https://staging.nikita-mygirl.com"
