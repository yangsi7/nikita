"""Authentication dependencies for FastAPI.

Validates Supabase JWT tokens and extracts user IDs.
"""

from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from nikita.config.settings import get_settings

security = HTTPBearer()


@dataclass
class AuthenticatedUser:
    """User identity extracted from JWT."""

    id: UUID
    email: str | None = None


async def _decode_jwt(
    credentials: HTTPAuthorizationCredentials,
) -> dict:
    """Decode and validate a Supabase JWT, returning the raw payload.

    Shared helper used by all auth dependencies to eliminate duplication.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        Decoded JWT payload dict.

    Raises:
        HTTPException: 401 if token is invalid/expired.
        HTTPException: 500 if JWT secret is not configured.
    """
    settings = get_settings()

    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    token = credentials.credentials

    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """Extract and validate user ID from Supabase JWT.

    Decodes the JWT token from the Authorization header, validates it
    against the Supabase JWT secret, and returns the user ID from the
    'sub' claim.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        User ID (UUID) from JWT 'sub' claim.

    Raises:
        HTTPException: 401 if token is invalid/expired.
        HTTPException: 403 if token is missing required claims.
        HTTPException: 500 if JWT secret is not configured.
    """
    payload = await _decode_jwt(credentials)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing user ID (sub claim)",
        )

    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user ID format in token",
        )


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthenticatedUser:
    """Extract user ID and email from Supabase JWT.

    Returns an AuthenticatedUser with both id and email (if present in token).
    Use this instead of get_current_user_id when the email is needed.
    """
    payload = await _decode_jwt(credentials)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing user ID (sub claim)",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user ID format in token",
        )

    return AuthenticatedUser(id=user_id, email=payload.get("email"))


def _is_admin_claim(claims: dict) -> bool:
    """Check if JWT claims grant admin access.

    Admin is gated exclusively on the `app_metadata.role` JWT claim.
    `app_metadata` is service-role-only — it cannot be written from the
    browser via `supabase.auth.updateUser()`. By contrast,
    `user_metadata` IS client-writable, and reading admin status from
    it would enable self-escalation by any authenticated user.

    Args:
        claims: Decoded JWT payload.

    Returns:
        True iff `claims["app_metadata"]["role"] == "admin"`.
    """
    app_metadata = claims.get("app_metadata") or {}
    return app_metadata.get("role") == "admin"


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """Extract and validate admin user from Supabase JWT.

    Validates that the JWT contains a valid user ID AND that the JWT's
    `app_metadata.role` claim equals `"admin"`. `app_metadata` is a
    service-role-only Supabase surface, so this cannot be forged from
    the browser.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        User ID (UUID) from JWT 'sub' claim if caller is admin.

    Raises:
        HTTPException: 401 if token is invalid/expired.
        HTTPException: 403 if app_metadata.role != "admin" or sub missing.
        HTTPException: 500 if JWT secret is not configured.
    """
    payload = await _decode_jwt(credentials)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing user ID (sub claim)",
        )

    if not _is_admin_claim(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user ID format in token",
        )
