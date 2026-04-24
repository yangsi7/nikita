"""Repository for telegram_signup_sessions FSM operations (Spec 215 §7.2.1).

Every state transition is a compare-and-swap (CAS) UPDATE that asserts the
prior `signup_state` and fails loud when 0 rows are returned. This is the only
correct way to express the FSM — read-modify-write would race under
concurrent webhook delivery.

States (per spec §7.3):
    AWAITING_EMAIL  →  CODE_SENT  →  MAGIC_LINK_SENT  →  COMPLETED

The legacy `PendingRegistrationRepository` (in pending_registration_repository.py)
remains for legacy callers (registration_handler.py / otp_handler.py /
auth.py / api/routes/tasks.py); both repositories share the same underlying
ORM model (`TelegramSignupSession` aliased as `PendingRegistration`). The
legacy repo + handlers are removed in PR-F3.
"""

from datetime import timedelta

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.base import utc_now
from nikita.db.models.telegram_signup_session import TelegramSignupSession


class ConcurrentTransitionError(RuntimeError):
    """Raised when a CAS UPDATE returns 0 rows because the prior state did
    not match (another worker already advanced the FSM)."""


class ExpiredOrConcurrentError(RuntimeError):
    """Raised when a CAS UPDATE returns 0 rows because the row is expired
    (now > expires_at) OR another worker already advanced the FSM."""


class TelegramSignupSessionRepository:
    """Async repository with FSM-safe CAS transition helpers."""

    DEFAULT_EXPIRY_MINUTES = 10

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    # ------------------------------------------------------------------
    # CAS FSM transitions (spec §7.2.1)
    # ------------------------------------------------------------------

    async def transition_to_code_sent(
        self,
        telegram_id: int,
        email: str,
    ) -> str:
        """AWAITING_EMAIL → CODE_SENT (after FR-3 sign_in_with_otp succeeds).

        Returns:
            The row id (uuid as str) on success.

        Raises:
            ConcurrentTransitionError: 0 rows returned (another worker
            already advanced the state, or the row is missing).
        """
        stmt = (
            update(TelegramSignupSession)
            .where(
                TelegramSignupSession.telegram_id == telegram_id,
                TelegramSignupSession.signup_state == "awaiting_email",
            )
            .values(
                signup_state="code_sent",
                email=email,
                expires_at=utc_now() + timedelta(minutes=5),
                attempts=0,
                last_attempt_at=utc_now(),
            )
            .returning(TelegramSignupSession.telegram_id)
        )
        result = await self._session.execute(stmt)
        row_id = result.scalar_one_or_none()
        if row_id is None:
            raise ConcurrentTransitionError(
                f"telegram_id={telegram_id}: AWAITING_EMAIL → CODE_SENT "
                "blocked (state mismatch or row missing)"
            )
        return row_id

    async def transition_to_magic_link_sent(
        self,
        telegram_id: int,
        hashed_token: str,
        verification_type: str,
    ) -> str:
        """CODE_SENT → MAGIC_LINK_SENT (after FR-4 verify_otp + FR-5
        generate_link succeed).

        The CAS clause includes `now() <= expires_at` to enforce the 5min
        OTP window; if expired, the update is rejected and the caller is
        expected to NOT dispatch the Telegram message.

        Args:
            telegram_id: target row.
            hashed_token: HASHED token from supabase.auth.admin.generate_link
                (NEVER the raw action_link query-string token, per
                data-layer H5).
            verification_type: passed VERBATIM from the Supabase
                generate_link response (no normalization, per Testing H2).

        Returns:
            Row id on success.

        Raises:
            ExpiredOrConcurrentError: 0 rows returned (expired or
            concurrent advance).
        """
        stmt = (
            update(TelegramSignupSession)
            .where(
                TelegramSignupSession.telegram_id == telegram_id,
                TelegramSignupSession.signup_state == "code_sent",
                TelegramSignupSession.expires_at >= utc_now(),
            )
            .values(
                signup_state="magic_link_sent",
                magic_link_token=hashed_token,
                magic_link_sent_at=utc_now(),
                verification_type=verification_type,
            )
            .returning(TelegramSignupSession.telegram_id)
        )
        result = await self._session.execute(stmt)
        row_id = result.scalar_one_or_none()
        if row_id is None:
            raise ExpiredOrConcurrentError(
                f"telegram_id={telegram_id}: CODE_SENT → MAGIC_LINK_SENT "
                "blocked (expired or already advanced)"
            )
        return row_id

    async def delete_on_completion(self, telegram_id: int) -> int:
        """MAGIC_LINK_SENT → COMPLETED (delete row after /auth/confirm bind).

        Idempotent — re-tap (no row) returns 0 without raising. The CAS
        clause restricts the delete to the magic_link_sent state so that a
        concurrent state change in either direction is safe.

        Returns:
            Number of rows deleted (0 or 1).
        """
        stmt = delete(TelegramSignupSession).where(
            TelegramSignupSession.telegram_id == telegram_id,
            TelegramSignupSession.signup_state == "magic_link_sent",
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def increment_attempts(self, telegram_id: int) -> int | None:
        """Atomic attempt increment on invalid OTP (spec §7.2.1).

        Restricted to rows in CODE_SENT — increments outside that state
        return None. Updates `last_attempt_at` for the rate-limit window.

        Returns:
            New attempts count, or None if the row was not in CODE_SENT.
        """
        stmt = (
            update(TelegramSignupSession)
            .where(
                TelegramSignupSession.telegram_id == telegram_id,
                TelegramSignupSession.signup_state == "code_sent",
            )
            .values(
                attempts=TelegramSignupSession.attempts + 1,
                last_attempt_at=utc_now(),
            )
            .returning(TelegramSignupSession.attempts)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Convenience helpers (used by handler code; not part of the FSM)
    # ------------------------------------------------------------------

    async def get(self, telegram_id: int) -> TelegramSignupSession | None:
        """Fetch a non-expired session by telegram_id."""
        stmt = select(TelegramSignupSession).where(
            TelegramSignupSession.telegram_id == telegram_id,
            TelegramSignupSession.expires_at > utc_now(),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> TelegramSignupSession | None:
        """Fetch a non-expired session by email (used during /auth/confirm
        bind to recover telegram_id)."""
        stmt = select(TelegramSignupSession).where(
            TelegramSignupSession.email == email,
            TelegramSignupSession.expires_at > utc_now(),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


