"""T-B3-4 (Spec 216-B3): GET /api/v1/onboarding/state route handler.

Read-only state projection mirroring the new stateful contract:

  - Reads ``users.onboarding_profile`` JSONB
  - Reconstructs cumulative WizardSlots via build_state_from_conversation
  - Returns last_assistant_turn + progress_pct + is_complete + link_code +
    elided_extracted + conversation_id

Distinct from the legacy GET /conversation (which still serves /converse
clients during the 216-C migration window). /state is the canonical post-216-B3
hydration endpoint.

Hard rules verified here:
  - Hard Rule §1 (cumulative state): progress_pct comes from
    WizardSlots.progress_pct, not _compute_progress.
  - Hard Rule §2 (Pydantic gate): is_complete is the @computed_field
    FinalForm.model_validate result.
  - AC B1.14: shape matches StateResponse contract (T-B3-2).
  - Read-only: never mints a link_code (mirrors GET /conversation policy).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _make_app(user_id: UUID = USER_ID) -> tuple[FastAPI, AsyncMock]:
    """Build a FastAPI app with portal_onboarding router + bypassed auth/rate-limit."""
    from nikita.api.dependencies.auth import (
        AuthenticatedUser,
        get_authenticated_user,
        get_current_user_id,
    )
    from nikita.api.routes.portal_onboarding import router
    from nikita.db.database import get_async_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")
    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    async def _auth_override() -> AuthenticatedUser:
        return AuthenticatedUser(id=user_id, email="test@example.com")

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_authenticated_user] = _auth_override
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app, mock_session


def _make_user(profile: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = USER_ID
    user.onboarding_profile = profile if profile is not None else {}
    return user


class TestStateEndpoint:
    """B1.14 — GET /state returns cumulative-state projection."""

    def test_empty_profile_returns_zero_progress(self) -> None:
        """New user with empty JSONB → progress_pct=0, is_complete=False."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))

        link_repo = MagicMock()
        link_repo.get_active_for_user = AsyncMock(return_value=None)

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=link_repo,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/onboarding/state")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["progress_pct"] == 0
        assert body["is_complete"] is False
        assert body["last_assistant_turn"] is None
        assert body["link_code"] is None
        assert body["elided_extracted"] == {}
        assert body["conversation_id"] is None

    def test_partial_state_returns_progress_and_last_turn(self) -> None:
        """Profile with 2 slots filled → progress_pct ~ 15%, last_assistant_turn matches."""
        app, _ = _make_app()
        last_nikita = {
            "role": "nikita",
            "content": "got it.",
            "timestamp": "2026-05-03T00:00:00Z",
            "source": "llm",
            "conversation_id": "11111111-2222-3333-4444-555555555555",
        }
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "Sam",
                    "extracted": {
                        "kind": "display_name",
                        "display_name": "Sam",
                    },
                    "timestamp": "2026-05-03T00:00:00Z",
                    "conversation_id": "11111111-2222-3333-4444-555555555555",
                },
                {
                    "role": "user",
                    "content": "Zürich",
                    "extracted": {"kind": "city", "city": "Zürich"},
                    "timestamp": "2026-05-03T00:00:01Z",
                    "conversation_id": "11111111-2222-3333-4444-555555555555",
                },
                last_nikita,
            ],
            "elided_extracted": {},
        }

        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile=profile))

        link_repo = MagicMock()
        link_repo.get_active_for_user = AsyncMock(return_value=None)

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=link_repo,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/onboarding/state")

        assert response.status_code == 200
        body = response.json()
        assert body["progress_pct"] > 0, "Two slots filled MUST move progress."
        assert body["progress_pct"] < 100, "2/13 is not complete."
        assert body["is_complete"] is False
        assert body["last_assistant_turn"] == last_nikita
        assert body["conversation_id"] == "11111111-2222-3333-4444-555555555555"

    def test_active_link_code_returned_readonly(self) -> None:
        """If a TelegramLinkCode is active, GET /state returns it.

        Read-only — handler MUST NOT call create_link_code (mirrors
        /conversation policy; only POST /answer mints).
        """
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))

        active_code = MagicMock()
        active_code.code = "ABC123"
        active_code.expires_at = datetime.now(UTC) + timedelta(hours=23)

        link_repo = MagicMock()
        link_repo.get_active_for_user = AsyncMock(return_value=active_code)
        link_repo.create_link_code = AsyncMock()  # MUST NOT be called

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=link_repo,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/onboarding/state")

        assert response.status_code == 200
        assert response.json()["link_code"] == "ABC123"
        link_repo.create_link_code.assert_not_awaited(), (
            "GET /state MUST be read-only — no link-code minting."
        )

    def test_user_not_found_returns_empty_state(self) -> None:
        """Repo.get returns None → empty state (do NOT 404)."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)

        link_repo = MagicMock()
        link_repo.get_active_for_user = AsyncMock(return_value=None)

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ),
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=link_repo,
            ),
        ):
            client = TestClient(app)
            response = client.get("/api/v1/onboarding/state")

        assert response.status_code == 200, (
            "Missing user row should not 404 — wizard hydration must "
            "tolerate a not-yet-created user record."
        )
        body = response.json()
        assert body["progress_pct"] == 0
        assert body["is_complete"] is False
