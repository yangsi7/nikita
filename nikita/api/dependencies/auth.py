"""Authentication dependencies for FastAPI.

Validates Supabase JWT tokens and extracts user IDs.
"""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from nikita.config.settings import get_settings

security = HTTPBearer()


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
    settings = get_settings()

    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured",
        )

    token = credentials.credentials

    try:
        # Decode and verify the JWT
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase default audience for authenticated users
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

    # Extract user ID from 'sub' claim
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


# Admin email domain for access control
ADMIN_EMAIL_DOMAIN = "@silent-agents.com"


def _is_admin_email(email: str) -> bool:
    """Check if email is authorized for admin access.

    Admin access is granted if:
    1. Email ends with @silent-agents.com (domain-based), OR
    2. Email is in the explicit admin_emails list from settings

    Args:
        email: User's email address from JWT.

    Returns:
        True if email is authorized for admin access.
    """
    # Always allow @silent-agents.com domain
    if email.lower().endswith(ADMIN_EMAIL_DOMAIN):
        return True

    # Check explicit admin emails from settings
    settings = get_settings()
    admin_emails = settings.admin_emails or []
    return email.lower() in [e.lower() for e in admin_emails]


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """Extract and validate admin user from Supabase JWT.

    Validates that the JWT contains a valid user ID AND that the user's
    email ends with @silent-agents.com (admin domain).

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        User ID (UUID) from JWT 'sub' claim if email is admin domain.

    Raises:
        HTTPException: 401 if token is invalid/expired.
        HTTPException: 403 if not admin email domain or missing claims.
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
        # Decode and verify the JWT
        payload = jwt.decode(
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

    # Extract user ID from 'sub' claim
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing user ID (sub claim)",
        )

    # Extract and validate email for admin access
    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing email claim",
        )

    # Validate admin email - must be @silent-agents.com domain OR in explicit allowlist
    if not _is_admin_email(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Only authorized emails allowed.",
        )

    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user ID format in token",
        )
