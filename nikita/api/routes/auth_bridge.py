"""Auth bridge token exchange endpoint.

Exchanges a short-lived bridge token (from Telegram onboarding) for a
Supabase hashed_token that the portal can use with verifyOtp() to
establish a session without PKCE.

Flow:
1. Portal sends bridge token (from Telegram button URL)
2. Backend verifies token (single-use, deletes it)
3. Backend calls admin.generate_link() to get hashed_token
4. Returns hashed_token + email to portal
5. Portal calls verifyOtp({token_hash}) → session created
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.database import get_async_session, get_supabase_client
from nikita.db.repositories.auth_bridge_repository import AuthBridgeRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth Bridge"])


class BridgeTokenRequest(BaseModel):
    """Request body for bridge token exchange."""

    token: str


class BridgeTokenResponse(BaseModel):
    """Response with Supabase credentials for verifyOtp."""

    hashed_token: str
    email: str
    redirect_path: str


async def get_bridge_repo(
    session: AsyncSession = Depends(get_async_session),
) -> AuthBridgeRepository:
    """Dependency for bridge token repository."""
    return AuthBridgeRepository(session)


@router.post(
    "/exchange-bridge-token",
    response_model=BridgeTokenResponse,
    summary="Exchange bridge token for Supabase auth credentials",
    description="Exchanges a one-time bridge token for hashed_token + email. "
    "The portal uses the returned hashed_token to call "
    "supabase.auth.verifyOtp({token_hash, type: 'magiclink'}) "
    "which establishes a session without PKCE.",
)
async def exchange_bridge_token(
    body: BridgeTokenRequest,
    bridge_repo: AuthBridgeRepository = Depends(get_bridge_repo),
) -> BridgeTokenResponse:
    """Exchange a one-time bridge token for Supabase auth credentials."""
    # 1. Verify bridge token (single-use — deleted on verify)
    result = await bridge_repo.verify_token(body.token)
    if result is None:
        raise HTTPException(
            status_code=401, detail="Invalid or expired bridge token"
        )

    user_id, redirect_path = result

    try:
        # 2. Look up email from Supabase auth.users
        supabase = await get_supabase_client()
        auth_user = await supabase.auth.admin.get_user_by_id(str(user_id))
        email = auth_user.user.email
        if not email:
            raise HTTPException(status_code=500, detail="User has no email")

        # 3. Generate magic link to extract hashed_token
        # admin.generate_link() returns GenerateLinkProperties with:
        #   action_link, email_otp, hashed_token, redirect_to, verification_type
        # We only need hashed_token — the portal will use it with verifyOtp()
        link_result = await supabase.auth.admin.generate_link(
            {
                "type": "magiclink",
                "email": email,
            }
        )
        hashed_token = link_result.properties.hashed_token

        logger.info(f"Bridge token exchanged for user_id={user_id}")

        return BridgeTokenResponse(
            hashed_token=hashed_token,
            email=email,
            redirect_path=redirect_path,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Bridge token exchange failed for user_id={user_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Auth bridge exchange failed"
        )
