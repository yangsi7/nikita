"""Tests for portal_auth.autobind_telegram_on_confirm (Spec 216 EM-2 + PR-E repair).

Path B of the Telegram-first signup flow: portal /auth/confirm calls
this endpoint AFTER verifyOtp succeeds; the handler looks up the
in-flight `telegram_signup_sessions` row by the JWT subject's email
and atomically binds `users.telegram_id`.

ACs covered (post-216-H PR-E):
- happy-path: in-flight session row found → atomic bind → BOUND + delete
- already-bound idempotency: ALREADY_BOUND_SAME_USER returned, no error
- no-session + telegram_id already SET → 200, already_bound=True (idempotent re-tap)
- no-session + telegram_id NULL → 409 telegram_bind_failed_fsm_missing (PR-E fatal)
- 409 conflict: telegram_id held by a DIFFERENT user → 409 telegram_already_bound_to_other_user
- ValueError on update_telegram_id (user row missing) → 409 telegram_bind_failed_user_row_missing (PR-E fatal)
- JWT without email → 200 no_session=True (defensive)
- delete_on_completion failure does not break response
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
)
from nikita.api.routes.portal_auth import user_router
from nikita.db.database import get_async_session
from nikita.db.repositories.user_repository import (
    BindResult,
    TelegramIdAlreadyBoundByOtherUserError,
)


_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
_USER_EMAIL = "walker+em2@example.com"
_TELEGRAM_ID = 1234567890


def _make_session_row(
    *,
    telegram_id: int = _TELEGRAM_ID,
    email: str = _USER_EMAIL,
    expires_at: datetime | None = None,
) -> MagicMock:
    """Build a stand-in `TelegramSignupSession` ORM row."""
    row = MagicMock()
    row.telegram_id = telegram_id
    row.email = email
    row.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(minutes=5))
    return row


def _make_user_row(*, telegram_id: int | None) -> MagicMock:
    """Stand-in `User` ORM row exposing `.telegram_id`."""
    row = MagicMock()
    row.telegram_id = telegram_id
    return row


def _build_app(
    *,
    user: AuthenticatedUser,
    session_row,
    bind_outcome,
    delete_count: int = 1,
    existing_user: MagicMock | None = None,
) -> tuple[FastAPI, MagicMock, MagicMock]:
    """Wire a FastAPI app with the autobind router + dep overrides.

    `bind_outcome` is either a BindResult value or an Exception
    instance to raise from `update_telegram_id`. `existing_user` is
    the result `user_repo.get(user.id)` returns when `session_row` is
    None (PR-E disambiguation between idempotent re-tap and FSM-
    missing fatal).
    """

    app = FastAPI()
    app.include_router(user_router, prefix="/api/v1")

    fake_repo = MagicMock()
    fake_repo.get_by_email = AsyncMock(return_value=session_row)
    fake_repo.delete_on_completion = AsyncMock(return_value=delete_count)

    fake_user_repo = MagicMock()
    fake_user_repo.get = AsyncMock(return_value=existing_user)
    if isinstance(bind_outcome, Exception):
        fake_user_repo.update_telegram_id = AsyncMock(side_effect=bind_outcome)
    else:
        fake_user_repo.update_telegram_id = AsyncMock(return_value=bind_outcome)

    # Patch the repo classes at the module the route uses them from
    # (function-local lookups resolve through the imported names).
    # The route imports the classes at module scope, so we patch
    # there via dependency-override + monkeypatching repository
    # classes via `unittest.mock.patch` is unnecessary: the route
    # constructs the repos with `repo_cls(session)`; we override
    # the session dep AND the repo classes.
    import nikita.api.routes.portal_auth as portal_auth_mod

    portal_auth_mod.TelegramSignupSessionRepository = (  # type: ignore[assignment]
        lambda _session: fake_repo
    )
    portal_auth_mod.UserRepository = (  # type: ignore[assignment]
        lambda _session: fake_user_repo
    )

    async def _fake_session():
        # The handler never touches the session directly — repos are
        # the only consumer and they are mocked.
        yield MagicMock()

    app.dependency_overrides[get_async_session] = _fake_session
    app.dependency_overrides[get_authenticated_user] = lambda: user

    return app, fake_repo, fake_user_repo


def test_happy_path_fresh_bind_returns_200_bound_true():
    """In-flight session + BOUND result → 200, bound=True, session deleted."""
    app, repo, user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=_make_session_row(),
        bind_outcome=BindResult.BOUND,
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body == {"bound": True, "already_bound": False, "no_session": False}
    repo.get_by_email.assert_awaited_once_with(_USER_EMAIL)
    user_repo.update_telegram_id.assert_awaited_once_with(
        user_id=_USER_ID, telegram_id=_TELEGRAM_ID
    )
    repo.delete_on_completion.assert_awaited_once_with(telegram_id=_TELEGRAM_ID)


def test_already_bound_returns_200_already_bound_true():
    """Re-call with the same telegram_id → ALREADY_BOUND_SAME_USER, no error."""
    app, repo, user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=_make_session_row(),
        bind_outcome=BindResult.ALREADY_BOUND_SAME_USER,
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 200
    assert res.json() == {
        "bound": False,
        "already_bound": True,
        "no_session": False,
    }


def test_no_session_with_existing_telegram_id_returns_200_already_bound():
    """PR-E: Idempotent re-tap of magic-link AFTER successful prior bind.

    `telegram_signup_sessions` row was deleted by `delete_on_completion`
    on the first successful confirm; user retaps the same magic-link.
    `users.telegram_id` is already SET, so the autobind handler must
    return 200 with `already_bound=True` and let the front-end continue.
    """
    app, repo, user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=None,
        bind_outcome=BindResult.BOUND,
        existing_user=_make_user_row(telegram_id=_TELEGRAM_ID),
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 200, res.text
    assert res.json() == {
        "bound": False,
        "already_bound": True,
        "no_session": False,
    }
    repo.get_by_email.assert_awaited_once_with(_USER_EMAIL)
    user_repo.get.assert_awaited_once_with(_USER_ID)
    user_repo.update_telegram_id.assert_not_called()
    repo.delete_on_completion.assert_not_called()


def test_no_session_with_unbound_user_returns_409_fsm_missing():
    """PR-E: FSM row missing AND users.telegram_id IS NULL → fatal 409.

    Pre-PR-E this case silently returned 200 no_session=True, mounting
    the wizard with a NULL Telegram bind. Every downstream Nikita system
    (decay DMs, scheduled events, voice, push) requires telegram_id and
    silently no-op'd. Post-216-G the canonical TG-first flow always
    creates the FSM row in `signup_handler.handle_welcome`, so this
    case is a fatal bug — surface it to the user.

    Falsifier: removing the `existing.telegram_id is not None` branch in
    `autobind_telegram_on_confirm` and reverting to a blanket 200 on
    `sess is None` would make this test fail with status 200.
    """
    app, repo, user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=None,
        bind_outcome=BindResult.BOUND,
        existing_user=_make_user_row(telegram_id=None),
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 409, res.text
    assert res.json()["detail"] == "telegram_bind_failed_fsm_missing"
    repo.get_by_email.assert_awaited_once_with(_USER_EMAIL)
    user_repo.get.assert_awaited_once_with(_USER_ID)
    user_repo.update_telegram_id.assert_not_called()
    repo.delete_on_completion.assert_not_called()


def test_no_session_with_missing_user_row_returns_409_user_row_missing():
    """Spec 219 C1 R1: `user_repo.get` returns None (user row absent) → 409 user_row_missing.

    When the FSM session row is absent AND the user row is also absent,
    the error is a missing user row (e.g. after a DB wipe or admin delete),
    NOT a missing FSM session. The two cases must emit distinct error codes
    so the FE can route portal-first (fsm_missing → fall through) vs
    truly broken (user_row_missing → /login error).

    RED: fails until portal_auth.py splits the two branches.
    """
    app, repo, user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=None,
        bind_outcome=BindResult.BOUND,
        existing_user=None,
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 409
    assert res.json()["detail"] == "telegram_bind_failed_user_row_missing"


def test_conflict_returns_409():
    """telegram_id already bound to another user → 409 Conflict.

    Plan §EDGE CASES E4: "this email's already linked to another telegram".
    """
    app, _repo, _user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=_make_session_row(),
        bind_outcome=TelegramIdAlreadyBoundByOtherUserError(
            "telegram_id 1234567890 bound to a different user"
        ),
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 409
    assert res.json()["detail"] == "telegram_already_bound_to_other_user"


def test_user_row_missing_returns_409_user_row_missing():
    """PR-E: ValueError from update_telegram_id → 409 (was 200 silent skip).

    Pre-PR-E this returned 200 no_session=True on the assumption that
    `/start <code>` would bind it later. Post-216-G the canonical
    TG-first flow has no /start <code> rebind path for fresh signups,
    so silent-skip is fatal. Surface to /login?error=telegram_bind_failed.
    """
    app, _repo, _user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=_make_session_row(),
        bind_outcome=ValueError("user_id not in users"),
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 409
    assert res.json()["detail"] == "telegram_bind_failed_user_row_missing"


def test_jwt_without_email_returns_200_no_session():
    """Defensive: JWT missing the email claim → 200 no_session=True."""
    app, repo, _user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=None),
        session_row=None,
        bind_outcome=BindResult.BOUND,
    )
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")
    assert res.status_code == 200
    assert res.json() == {
        "bound": False,
        "already_bound": False,
        "no_session": True,
    }
    # Must not even attempt the repo lookup without an email.
    repo.get_by_email.assert_not_called()


def test_delete_on_completion_failure_does_not_break_response():
    """QA finding 4: defensive swallow of `delete_on_completion` errors.

    The telegram_id binding is the user-visible commit; a failure on the
    subsequent FSM-row delete (unique-constraint, transient DB error,
    etc.) must NOT cause the route to 5xx after a successful bind. The
    response body must still report `bound=True`. The orphan FSM row
    that survives is then mopped up later — either by a follow-up
    autobind call (`get_by_email` returns it again, idempotent
    `update_telegram_id` returns ALREADY_BOUND_SAME_USER) or by an
    eventual TTL purge (`expires_at` cleanup).

    Falsifier: removing the try/except around `delete_on_completion`
    in `autobind_telegram_on_confirm` would surface the exception as
    a 500 and this test would fail with a non-200 status.
    """
    app, repo, _user_repo = _build_app(
        user=AuthenticatedUser(id=_USER_ID, email=_USER_EMAIL),
        session_row=_make_session_row(),
        bind_outcome=BindResult.BOUND,
    )
    # Override the delete to raise after the bind succeeds.
    repo.delete_on_completion = AsyncMock(
        side_effect=RuntimeError("simulated transient DB error")
    )

    with TestClient(app) as client:
        res = client.post("/api/v1/auth/autobind-telegram")

    assert res.status_code == 200, res.text
    # Bind landed; FSM-row cleanup failure is an internal-only concern.
    assert res.json() == {
        "bound": True,
        "already_bound": False,
        "no_session": False,
    }
    # The defensive swallow path was actually exercised.
    repo.delete_on_completion.assert_awaited_once_with(
        telegram_id=_TELEGRAM_ID
    )
