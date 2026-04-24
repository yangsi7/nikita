"""TelegramSignupSession model — Spec 215 PR-F1a §7.2.

Renamed from `PendingRegistration` (table `pending_registrations` →
`telegram_signup_sessions`). The column rename happens in
`supabase/migrations/20260424120000_rename_pending_registrations_to_telegram_signup_sessions.sql`:

    otp_state    → signup_state    (domain expanded)
    otp_attempts → attempts

Plus new columns: magic_link_token (HASHED only, per data-layer H5),
magic_link_sent_at, verification_type, last_attempt_at.

Backward-compat alias `PendingRegistration = TelegramSignupSession` is exported
to avoid a 26-file mass-rename in PR-F1a. Legacy callers continue to compile.
The full mass-rename happens in PR-F3 when registration_handler.py /
otp_handler.py / auth.py legacy paths are deleted.

FSM (per spec §7.3):
    [UNKNOWN] -> AWAITING_EMAIL -> CODE_SENT -> MAGIC_LINK_SENT -> COMPLETED

Every transition is a CAS UPDATE asserting the prior state (see
`telegram_signup_session_repository.py` for CAS helpers).
"""

from datetime import datetime, timedelta

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class TelegramSignupSession(Base):
    """Telegram signup session row in the FSM (spec §7.2 + §7.2.1).

    Table: telegram_signup_sessions (renamed from pending_registrations).
    Primary Key: telegram_id (one in-flight session per telegram user).

    The legacy alias `PendingRegistration` is exported below for
    backward-compat; the full rename in callers happens in PR-F3.
    """

    __tablename__ = "telegram_signup_sessions"

    # Telegram user ID — one in-flight session per user.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        nullable=False,
    )

    # Email collected in AWAITING_EMAIL.
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Telegram chat_id (FR-11c routing dependency, data-layer H1 — preserved
    # verbatim from the legacy table).
    chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # FSM state — domain enforced by DB CHECK constraint:
    # ('awaiting_email','code_sent','magic_link_sent','completed').
    # Renamed from `otp_state` per data-layer H2.
    signup_state: Mapped[str] = mapped_column(
        String(20),
        default="awaiting_email",
        nullable=False,
    )

    # Magic-link tracking (Spec 215 FR-5).
    # STORAGE CONTRACT (data-layer H5): stores ONLY the hashed_token returned
    # by supabase.auth.admin.generate_link — NEVER the raw action_link
    # query-string token. The action_link itself is delivered via Telegram
    # and not stored server-side after dispatch.
    magic_link_token: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    magic_link_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verification_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Attempt counter (renamed from `otp_attempts` per data-layer H2).
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now() + timedelta(minutes=10),
        nullable=False,
    )

    # ----- Backward-compat aliases for legacy callers -----
    # Code in registration_handler.py / otp_handler.py / auth.py still reads
    # `obj.otp_state` and `obj.otp_attempts`. These properties keep the
    # legacy access pattern working until PR-F3 deletes those handlers.

    @property
    def otp_state(self) -> str:
        return self.signup_state

    @otp_state.setter
    def otp_state(self, value: str) -> None:
        self.signup_state = value

    @property
    def otp_attempts(self) -> int:
        return self.attempts

    @otp_attempts.setter
    def otp_attempts(self, value: int) -> None:
        self.attempts = value

    def __repr__(self) -> str:
        return (
            f"TelegramSignupSession(telegram_id={self.telegram_id}, "
            f"email={self.email}, chat_id={self.chat_id}, "
            f"signup_state={self.signup_state}, attempts={self.attempts}, "
            f"expires_at={self.expires_at})"
        )

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        from nikita.db.models.base import utc_now
        return utc_now() > self.expires_at


# Backward-compat alias — legacy callers import this name. Full rename
# happens in PR-F3 alongside the registration_handler/otp_handler deletion.
PendingRegistration = TelegramSignupSession
