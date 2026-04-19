"""Portal bridge token model (Spec 214 FR-11c T1.1).

Short-lived, single-use tokens that bridge a Telegram `/start` reply
into an authenticated portal session on the `/onboarding/auth` route.

Distinct from `AuthBridgeToken` (`auth_bridge_tokens` table):
- AuthBridgeToken is the 5-minute post-OTP zero-click bridge (GH #187)
  used by `/onboard` + OTP handler → route `/auth/bridge?token=`.
- PortalBridgeToken is the Spec 214 FR-11c bridge with a per-reason TTL
  matrix (24h resume / 1h re-onboard) used by `_handle_start` + the
  pre-onboard gate → route `/onboarding/auth?bridge=`.

The two tables MUST NOT be conflated: they have different call sites,
different TTLs, different revocation stories (FR-11c revokes on
password-reset). Keep imports fully qualified.

Schema per plan.md D1 (resolves auth-M-A):

    CREATE TABLE portal_bridge_tokens (
      token TEXT PRIMARY KEY,
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      reason TEXT NOT NULL CHECK (reason IN ('resume', 're-onboard')),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      expires_at TIMESTAMPTZ NOT NULL,
      consumed_at TIMESTAMPTZ NULL
    );
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base, utc_now

# Bridge-token reason values. Mirrors the CHECK constraint in the SQL
# migration. Keep in sync; a DB row with an unknown reason cannot be
# written from this repo (mint() raises ValueError), but a manual
# INSERT bypassing the repo would still fail at the DB constraint.
PortalBridgeReason = Literal["resume", "re-onboard"]
_VALID_REASONS: frozenset[str] = frozenset({"resume", "re-onboard"})

# TTL matrix per AC-11c.12. `resume` covers pending/in_progress/limbo
# users who are mid-flow and need a generous window to return. `re-onboard`
# covers game_over/won users whose session should feel fresh; a shorter
# TTL keeps the re-entry cinematic and prevents stale links circulating
# in chats.
_TTL_BY_REASON: dict[str, timedelta] = {
    "resume": timedelta(hours=24),
    "re-onboard": timedelta(hours=1),
}


def generate_portal_bridge_token() -> str:
    """Generate a URL-safe, cryptographically random bridge token.

    `secrets.token_urlsafe(32)` → 32 random bytes → ~43-char base64url
    string. Matches the `auth_bridge_tokens` convention exactly so ops
    tooling (grep, inspect) stays uniform across both tables.
    """
    return secrets.token_urlsafe(32)


class PortalBridgeToken(Base):
    """Single-use token binding a Telegram entry to a portal session.

    Primary key: token (opaque string). `consumed_at IS NULL` indicates
    an active token; the repo's consume() sets it atomically.
    """

    __tablename__ = "portal_bridge_tokens"

    token: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"PortalBridgeToken(token={self.token[:8]}..., "
            f"user_id={self.user_id}, reason={self.reason})"
        )

    def is_expired(self, *, at: datetime | None = None) -> bool:
        """Return True if `expires_at` has passed."""
        return (at or utc_now()) > self.expires_at

    @classmethod
    def create(
        cls,
        user_id: UUID,
        reason: PortalBridgeReason,
    ) -> "PortalBridgeToken":
        """Build a new PortalBridgeToken with TTL matching `reason`.

        Not persisted; caller is responsible for `session.add(...)`.
        """
        if reason not in _VALID_REASONS:
            raise ValueError(
                f"invalid portal bridge reason: {reason!r}. "
                f"Allowed: {sorted(_VALID_REASONS)}"
            )
        ttl = _TTL_BY_REASON[reason]
        return cls(
            token=generate_portal_bridge_token(),
            user_id=user_id,
            reason=reason,
            expires_at=utc_now() + ttl,
        )
