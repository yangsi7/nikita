"""Tests for portal_auth.generate_magiclink_for_telegram_user (Spec 215 §7.6).

ACs:
- AC-1: end-user JWT returns 401 (service-role guard).
- AC-2: valid service-role call returns Pydantic GenerateMagiclinkResponse with
  verification_type taken VERBATIM from Supabase response (no normalization).
- AC-3: static-grep fixture asserts no 'magiclink' or 'signup' string literal in
  handler source outside Pydantic Literal[...] annotation (Testing H2).

Pattern: AsyncMock for DB session + AsyncMock for Supabase client; service-role
guard tested via Authorization header check.
"""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# AC-3: static-grep — handler source must not hardcode the literal strings
# 'magiclink' / 'signup' on the FR-5 path. Allowed contexts: type annotations
# (`Literal["magiclink", "signup"]`), docstrings, and comments. Disallowed:
# any other string usage in handler logic.
# ---------------------------------------------------------------------------

HANDLER_PATH = (
    Path(__file__).resolve().parents[3]
    / "nikita"
    / "api"
    / "routes"
    / "portal_auth.py"
)


def test_handler_source_has_no_hardcoded_verification_type_literals():
    """Testing H2: verification_type must come VERBATIM from Supabase response.

    Scan handler source. Allow: Literal[...] annotations, docstrings, comments.
    Disallow: bare 'magiclink' / 'signup' literal usage in code.
    """
    source = HANDLER_PATH.read_text()

    # Strip allowed contexts:
    # 1. Pydantic Literal[...] annotations (multi-line via DOTALL)
    cleaned = re.sub(r"Literal\[[^\]]*\]", "", source, flags=re.DOTALL)
    # 2. Triple-quoted docstrings
    cleaned = re.sub(r'"""[\s\S]*?"""', "", cleaned)
    cleaned = re.sub(r"'''[\s\S]*?'''", "", cleaned)
    # 3. Single-line comments
    cleaned = re.sub(r"#[^\n]*", "", cleaned)

    # Now search for any remaining 'magiclink' / 'signup' string literal.
    matches = re.findall(r"['\"](magiclink|signup)['\"]", cleaned)
    assert matches == [], (
        f"Found hardcoded verification_type literal(s) in handler "
        f"outside annotation contexts: {matches}. "
        "Per Spec 215 §7.6 + Testing H2 the value must come VERBATIM "
        "from the Supabase generate_link response."
    )


# ---------------------------------------------------------------------------
# AC-1 + AC-2: HTTP-level handler tests via FastAPI TestClient.
# ---------------------------------------------------------------------------


def _build_test_app():
    """Build a minimal FastAPI app wiring just the portal_auth router."""
    from nikita.api.routes.portal_auth import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/admin")
    return app


def test_endpoint_rejects_non_service_role_jwt():
    """AC-1: end-user JWT (or missing/garbage) MUST return 401."""
    app = _build_test_app()
    client = TestClient(app)

    # No Authorization header → 401
    resp = client.post(
        "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
        json={"telegram_id": 42, "email": "user@example.com"},
    )
    assert resp.status_code == 401, resp.text

    # Garbage Bearer → 401
    resp = client.post(
        "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
        headers={"Authorization": "Bearer not-the-service-key"},
        json={"telegram_id": 42, "email": "user@example.com"},
    )
    assert resp.status_code == 401, resp.text


def test_endpoint_returns_verification_type_verbatim_from_supabase():
    """AC-2: valid service-role call returns verification_type VERBATIM.

    Mock Supabase admin.generate_link to return verification_type="signup".
    Assert the response body echoes "signup" (NOT "magiclink") and that the
    repo persistence call received "signup" verbatim.
    """
    from nikita.config.settings import get_settings

    settings = get_settings()
    service_key = "test-service-key-deadbeef"

    # Patch settings so the handler accepts our test key as service-role.
    with patch.object(settings, "supabase_service_key", service_key):
        app = _build_test_app()

        # Mock Supabase client
        fake_link_props = MagicMock()
        fake_link_props.action_link = "https://example.com/auth/confirm?token_hash=abc&type=signup"
        fake_link_props.hashed_token = "hash-deadbeef"
        fake_link_props.verification_type = "signup"  # <-- from Supabase verbatim

        fake_link_result = MagicMock()
        fake_link_result.properties = fake_link_props

        fake_supabase = MagicMock()
        fake_supabase.auth.admin.generate_link = AsyncMock(
            return_value=fake_link_result
        )

        # Mock repo
        fake_repo = AsyncMock()
        fake_repo.transition_to_magic_link_sent.return_value = "row-id"

        # FastAPI Depends() captures the function reference at module load,
        # so module-level patching of _get_repo_for_request doesn't reach
        # the resolved dep. Use the official escape hatch instead.
        from nikita.api.routes.portal_auth import _get_repo_for_request

        async def _override_repo():
            return fake_repo

        app.dependency_overrides[_get_repo_for_request] = _override_repo

        with patch(
            "nikita.api.routes.portal_auth.get_supabase_client",
            new=AsyncMock(return_value=fake_supabase),
        ):
            client = TestClient(app)
            resp = client.post(
                "/api/v1/admin/auth/generate-magiclink-for-telegram-user",
                headers={"Authorization": f"Bearer {service_key}"},
                json={"telegram_id": 42, "email": "user@example.com"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Verbatim from Supabase: "signup", not normalized to "magiclink"
        assert body["verification_type"] == "signup"
        assert body["hashed_token"] == "hash-deadbeef"

        # Repo persistence got the verbatim verification_type
        fake_repo.transition_to_magic_link_sent.assert_awaited_once()
        kwargs = fake_repo.transition_to_magic_link_sent.await_args.kwargs
        assert kwargs["verification_type"] == "signup"
        assert kwargs["hashed_token"] == "hash-deadbeef"
        assert kwargs["telegram_id"] == 42
