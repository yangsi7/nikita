"""Health-endpoint alias tests — GH #311 fix.

Verifies both canonical (`/health`, `/health/live`) and `/api/v1/`-prefixed
alias paths return 200 with the same payload shape. Adding the alias
removes the surprise 404 hit by pre-flight automation that assumes the
`/api/v1/*` URL family for ALL backend routes.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nikita.api.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Module-scoped TestClient. Skips lifespan startup.

    Health endpoints return static dicts — no DB / Supabase / settings dep
    beyond `app.title`. Lifespan invokes `task_auth_secret` assertion at
    `nikita/api/main.py:81-85` which fails under CI env (no DEBUG=true,
    no TASK_AUTH_SECRET). Bypass-lifespan via direct construction mirrors
    peer pattern at `tests/platforms/telegram/test_routing.py:252`.
    """
    app = create_app()
    return TestClient(app)


def test_root_health_returns_200(client: TestClient) -> None:
    """Canonical /health endpoint still works (regression guard)."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "service" in body


def test_root_health_live_returns_200(client: TestClient) -> None:
    """Canonical /health/live (Cloud Run liveness target) still works."""
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_v1_health_alias_returns_200(client: TestClient) -> None:
    """GH #311: /api/v1/health alias MUST return 200 (not 404).

    Pre-flight automation (live E2E dogfood walks, docs/scripts referencing
    /api/v1/health) assumes the /api/v1/* family for all backend probes.
    """
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "service" in body


def test_api_v1_health_live_alias_returns_200(client: TestClient) -> None:
    """GH #311: /api/v1/health/live alias MUST return 200."""
    r = client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_v1_health_alias_matches_canonical_payload(client: TestClient) -> None:
    """Alias payload shape MUST match canonical so probes get identical signal."""
    canonical = client.get("/health").json()
    alias = client.get("/api/v1/health").json()
    assert canonical.keys() == alias.keys()
    assert canonical["service"] == alias["service"]
