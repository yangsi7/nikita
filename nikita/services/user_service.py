"""UserService — single source of truth for idempotent user-row creation.

Spec 216 EM-3b: prior to this service, multiple call sites in
``nikita/api/routes/portal.py`` and ``nikita/platforms/telegram/auth.py``
independently invoked ``UserRepository.create_with_metrics(...)`` with their
own (or no) idempotency wiring — divergent default-init risk per the smell
documented in ``docs/diagrams/architecture-2026-05-05/SMELLS.md`` §"3-call
user-creation drift".

This service consolidates that pattern into a single ``create_or_get`` method
backed by ``UserRepository``:

  - lookup by ``user_id`` (Supabase auth UUID); return existing row if any
  - otherwise create via ``UserRepository.create_with_metrics`` with default
    metrics (50/50/50/50) + default engagement state (calibrating)
  - swallow the rare race-conflict (concurrent create) by rolling back the
    failed savepoint and re-fetching

Callers should depend on this service rather than touching
``UserRepository.create_with_metrics`` directly. The repository method
remains public for the existing legacy callers in
``nikita/platforms/telegram/auth.py`` until they are migrated incrementally.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.user import User
from nikita.db.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service-layer facade for idempotent user creation.

    Wraps ``UserRepository`` so that all "ensure a user row exists" call sites
    share one implementation.

    Email is intentionally NOT a parameter: the ``users`` row carries no
    email column (per ``project_users_table_schema.md`` — email lives on
    ``auth.users``), so accepting it here would be a silent no-op. Callers
    that need to log the authenticated email should do so at the caller
    level alongside their other request telemetry.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        session: AsyncSession,
    ) -> None:
        self._user_repo = user_repo
        self._session = session

    async def create_or_get(
        self,
        supabase_id: UUID,
        telegram_id: int | None = None,
        phone: str | None = None,
    ) -> User:
        """Return the user row for ``supabase_id``, creating it if missing.

        Args:
            supabase_id: Supabase auth user UUID. Used as the public.users PK.
            telegram_id: Optional Telegram numeric ID (linked-account flow).
            phone: Optional E.164 phone number.

        Returns:
            The User row (existing or newly-created), with default metrics
            and engagement state attached.

        Raises:
            IntegrityError: only when the IntegrityError on create was NOT a
                race (re-fetch returns no row). Other DB errors propagate.
        """
        existing = await self._user_repo.get(supabase_id)
        if existing is not None:
            return existing

        try:
            return await self._user_repo.create_with_metrics(
                user_id=supabase_id,
                telegram_id=telegram_id,
                phone=phone,
            )
        except IntegrityError:
            # Race: another concurrent request created the row between our
            # get() and create_with_metrics(). After IntegrityError the
            # SQLAlchemy session is in a failed state — any subsequent
            # operation on it raises PendingRollbackError. Roll back the
            # failed transaction before re-fetching the winning row.
            logger.warning(
                "user_service.create_or_get race-conflict for supabase_id=%s; "
                "rolling back failed transaction and refetching",
                supabase_id,
            )
            await self._session.rollback()
            row = await self._user_repo.get(supabase_id)
            if row is None:
                # Defensive: IntegrityError without a winning row implies a
                # different constraint violation (FK, check). Re-raise so the
                # caller sees the real error.
                raise
            return row
