"""Internal webhook endpoints (Spec 214 FR-11c T1.4, AC-11c.12).

These endpoints are called by Supabase webhooks and other backend
services. Authentication uses the shared TASK_AUTH_SECRET Bearer token
(same pattern as pg_cron endpoints in `tasks.py`), never a Supabase
user JWT.

Currently:
- POST /auth/password-reset-hook: revoke all portal bridge tokens for
  a user whose Supabase password was changed. Prevents a compromised
  Telegram session from replaying an old deep-link post-reset.
"""

from __future__ import annotations

import hmac
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.config.settings import get_settings
from nikita.db.database import get_async_session
from nikita.db.repositories.portal_bridge_token_repository import (
    PortalBridgeTokenRepository,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Internal"])


def _get_task_secret() -> str | None:
    """Return TASK_AUTH_SECRET from settings (None in dev)."""
    return get_settings().task_auth_secret


async def _verify_task_secret(
    authorization: str | None = Header(None, alias="Authorization"),
) -> None:
    """Bearer-verify the shared task secret. Dev mode logs and allows."""
    secret = _get_task_secret()
    if secret is None:
        logger.warning(
            "Internal endpoint accessed without TASK_AUTH_SECRET (dev mode)."
        )
        return
    if not authorization or not hmac.compare_digest(
        authorization, f"Bearer {secret}"
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


class PasswordResetHookRequest(BaseModel):
    """Body posted by Supabase password-reset webhook."""

    user_id: UUID


class PasswordResetHookResponse(BaseModel):
    revoked: int


@router.post(
    "/auth/password-reset-hook",
    response_model=PasswordResetHookResponse,
    summary="Revoke all active portal bridge tokens for a user",
    description=(
        "Called by the Supabase password-reset webhook. Revokes every "
        "non-consumed portal bridge token for the given user_id so a "
        "stale Telegram deep-link cannot replay after the password "
        "change. AC-11c.12."
    ),
)
async def password_reset_hook(
    body: PasswordResetHookRequest,
    _: None = Depends(_verify_task_secret),
    session: AsyncSession = Depends(get_async_session),
) -> PasswordResetHookResponse:
    repo = PortalBridgeTokenRepository(session)
    revoked = await repo.revoke_all_for_user(body.user_id)
    await session.commit()
    logger.info(
        "password_reset_hook: revoked %d tokens for user_id=%s",
        revoked,
        body.user_id,
    )
    return PasswordResetHookResponse(revoked=revoked)
