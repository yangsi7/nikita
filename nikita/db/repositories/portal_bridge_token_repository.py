"""PortalBridgeTokenRepository (Spec 214 FR-11c T1.1).

Single place for CRUD + atomic consume against `portal_bridge_tokens`.

Design invariants (enforced here, mirrored at the DB layer):
- `mint(user_id, reason)` is the ONLY path to create a row. The reason
  is validated pre-DB so a bad literal surfaces as a Python ValueError
  rather than an opaque IntegrityError.
- `consume(token)` is atomic and idempotent. A second call on an
  already-consumed-or-expired token returns None (single-use).
- `revoke_all_for_user(user_id)` is the password-reset hook (AC-11c.12).

NOT used by the legacy `AuthBridgeRepository` (`auth_bridge_tokens`
table). See `nikita/db/models/portal_bridge_token.py` module docstring
for the two-table rationale.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.portal_bridge_token import (
    PortalBridgeReason,
    PortalBridgeToken,
    VALID_REASONS,
)


class PortalBridgeTokenRepository:
    """Repository for PortalBridgeToken.

    Uses a small amount of textual SQL for `consume` to guarantee an
    atomic UPDATE ... WHERE ... RETURNING that cannot race against a
    concurrent second-tap. The ORM-only equivalent (SELECT then
    UPDATE) has a TOCTOU window that would violate AC-T1.1.3.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def mint(
        self,
        user_id: UUID,
        reason: PortalBridgeReason,
    ) -> str:
        """Mint a new bridge token for `user_id` with TTL per `reason`.

        Returns the opaque token string.
        """
        if reason not in VALID_REASONS:
            raise ValueError(
                f"invalid portal bridge reason: {reason!r}. "
                f"Allowed: {sorted(VALID_REASONS)}"
            )
        token = PortalBridgeToken.create(user_id, reason)
        self.session.add(token)
        await self.session.flush()
        return token.token

    async def get_active_for_user(
        self,
        user_id: UUID,
        reason: PortalBridgeReason,
    ) -> PortalBridgeToken | None:
        """Return the most recent active token for `user_id`+`reason`.

        Active = `consumed_at IS NULL AND expires_at > now()`. Used by
        the bridge-URL generator to coalesce repeated `/start` taps onto
        a single token instead of minting one per tap (review finding,
        prevents unbounded mint pressure).
        """
        stmt = (
            select(PortalBridgeToken)
            .where(
                PortalBridgeToken.user_id == user_id,
                PortalBridgeToken.reason == reason,
                PortalBridgeToken.consumed_at.is_(None),
                PortalBridgeToken.expires_at > func.now(),
            )
            .order_by(PortalBridgeToken.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, token: str) -> UUID | None:
        """Atomically consume `token`. Returns user_id or None.

        Predicate guarantees single-use + TTL:
            consumed_at IS NULL AND expires_at > now()

        If the predicate fails (already consumed, expired, or unknown),
        RETURNING produces zero rows and we return None. Concurrent
        second tap hits the same predicate, loses the row lock, and
        returns None. No TOCTOU.
        """
        stmt = text(
            """
            UPDATE portal_bridge_tokens
               SET consumed_at = now()
             WHERE token = :token
               AND consumed_at IS NULL
               AND expires_at > now()
         RETURNING user_id
            """
        )
        result = await self.session.execute(stmt, {"token": token})
        row = result.first()
        if row is None:
            return None
        return row[0]

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """Mark all active tokens for `user_id` as consumed.

        Used by the Supabase password-reset webhook (AC-11c.12) so that
        a compromised Telegram session cannot replay an old link post-
        password-change. Returns the number of rows revoked.
        """
        stmt = text(
            """
            UPDATE portal_bridge_tokens
               SET consumed_at = now()
             WHERE user_id = :user_id
               AND consumed_at IS NULL
            """
        )
        result = await self.session.execute(stmt, {"user_id": user_id})
        return result.rowcount or 0
