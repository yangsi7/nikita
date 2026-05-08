"""AC-10a.1 / AC-10a.2 / AC-10a.3 — IdentityPair BE partial-validation (217-3A.3).

The /answer route accepts ``{slot_kind: "identity_pair", value: {name, age}}``;
partial validation rules:

  * full-valid (both name + age accepted) → ``DeterministicAdvanceResponse`` /
    ``CompletionResponse`` (depending on completion gate).
  * partial (name OK, age bad) → ``FieldErrorResponse(errors={"age": ...})``;
    name persisted to ``WizardSlots.display_name``.
  * partial (name bad, age OK) → ``FieldErrorResponse(errors={"name": ...})``;
    NOTHING persisted (per spec FR-10a "name invalid → don't persist").
  * full-invalid → ``FieldErrorResponse(errors={"name": ..., "age": ...})``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def _make_app(user_id: UUID = USER_ID) -> tuple[FastAPI, AsyncMock]:
    from nikita.api.dependencies.auth import (
        AuthenticatedUser,
        get_authenticated_user,
        get_current_user_id,
    )
    from nikita.api.middleware.rate_limit import answer_rate_limit
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
    app.dependency_overrides[answer_rate_limit] = lambda: None
    return app, mock_session


def _make_user(profile: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = USER_ID
    user.onboarding_profile = profile if profile is not None else {}
    user.big5_vector = {}
    return user


def _post_identity_pair(app: FastAPI, value: dict | str):
    client = TestClient(app)
    return client.post(
        "/api/v1/onboarding/answer",
        json={
            "slot_kind": "identity_pair",
            "value": value,
            "turn_id": str(uuid4()),
        },
    )


def _common_patches(user_repo: MagicMock):
    return [
        patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ),
        patch(
            "nikita.onboarding.idempotency.IdempotencyStore.get",
            AsyncMock(return_value=None),
        ),
        patch(
            "nikita.onboarding.idempotency.IdempotencyStore.put",
            AsyncMock(return_value=None),
        ),
        patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(return_value=None),
        ),
        patch(
            "nikita.api.routes.portal_onboarding._persist_state_to_profile",
            AsyncMock(return_value=None),
        ),
    ]


class TestIdentityPairBE:
    """AC-10a.3 — full-valid / partial / full-invalid cases."""

    def test_full_valid_advances_to_deterministic(self) -> None:
        """Both name + age valid → fall through to deterministic-advance branch."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))
        with (
            _common_patches(user_repo)[0],
            _common_patches(user_repo)[1],
            _common_patches(user_repo)[2],
            _common_patches(user_repo)[3],
            _common_patches(user_repo)[4],
        ):
            response = _post_identity_pair(
                app, {"name": "Walker", "age": 27}
            )
        assert response.status_code == 200, response.text
        body = response.json()
        # Either deterministic_advance (incomplete) or completion (impossible
        # here since most slots are still empty) — test the kind explicitly.
        assert body["kind"] == "deterministic_advance"
        assert body["progress_pct"] > 0  # 2 slots advanced
        # Completion gate is Pydantic-driven, NOT a literal — incomplete state
        # MUST yield deterministic_advance, never completion.

    def test_partial_name_ok_age_bad(self) -> None:
        """Name valid + age invalid → FieldErrorResponse(errors={"age"});
        name persisted to WizardSlots.display_name."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))
        with (
            _common_patches(user_repo)[0],
            _common_patches(user_repo)[1],
            _common_patches(user_repo)[2],
            _common_patches(user_repo)[3],
            _common_patches(user_repo)[4],
        ):
            response = _post_identity_pair(
                app, {"name": "Walker", "age": 12}  # under-18
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "field_error"
        assert "age" in body["errors"]
        assert "name" not in body["errors"]

    def test_partial_name_bad_age_ok(self) -> None:
        """Name invalid → FieldErrorResponse(errors={"name"}); nothing persisted."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))
        with (
            _common_patches(user_repo)[0],
            _common_patches(user_repo)[1],
            _common_patches(user_repo)[2],
            _common_patches(user_repo)[3],
            _common_patches(user_repo)[4],
        ):
            response = _post_identity_pair(
                app, {"name": "", "age": 27}  # empty name
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "field_error"
        assert "name" in body["errors"]

    def test_full_invalid(self) -> None:
        """Both fields invalid → FieldErrorResponse with both keys."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))
        with (
            _common_patches(user_repo)[0],
            _common_patches(user_repo)[1],
            _common_patches(user_repo)[2],
            _common_patches(user_repo)[3],
            _common_patches(user_repo)[4],
        ):
            response = _post_identity_pair(
                app, {"name": "", "age": 5}  # under-18 + empty name
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "field_error"
        assert "name" in body["errors"]
        assert "age" in body["errors"]

    def test_value_must_be_dict_for_identity_pair(self) -> None:
        """A string value for identity_pair → field_error or 422 — verify the
        route surfaces the schema mismatch as an error envelope."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user(profile={}))
        with (
            _common_patches(user_repo)[0],
            _common_patches(user_repo)[1],
            _common_patches(user_repo)[2],
            _common_patches(user_repo)[3],
            _common_patches(user_repo)[4],
        ):
            response = _post_identity_pair(app, "not-a-dict")
        # Pydantic accepts both via str|dict union, but the partial-validator
        # converts a string into a field_error envelope.
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "field_error"
