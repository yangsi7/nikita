"""Telegram-first signup FSM handler — Spec 215 PR-F1b.

Consolidates the legacy `registration_handler.py` + `otp_handler.py` flow
into a single state-machine handler that drives:

    UNKNOWN
      └─ /start welcome ──▶ AWAITING_EMAIL    (FR-2)
                                  │
                                  └─ valid email ──▶ CODE_SENT       (FR-3)
                                                          │
                                                          └─ valid OTP ──▶ MAGIC_LINK_SENT (FR-5)

Every state transition uses the CAS helpers on
`TelegramSignupSessionRepository` (no read-modify-write). The handler does
not own state mutation logic — it only drives transitions.

Key contracts:
- Magic-link Telegram delivery MUST set `disable_web_page_preview=True`
  (NFR-Sec-1, Testing H1).
- Telemetry events use the named Pydantic models from
  `nikita.monitoring.events` (Testing H5 — no free-form dicts).
- `verification_type` is forwarded VERBATIM from Supabase (Testing H2 —
  no hardcoded literal substitution at the handler level; the admin
  endpoint is where that contract lives).
- Post-magic-link `update_telegram_id` is idempotent — when the
  `public.users` row does not yet exist, the no-op is the correct
  behavior (binding happens later via the existing FR-11b /start <code>
  path).

The legacy registration_handler + otp_handler files remain for compile
compatibility; PR-F3 deletes them once W1 dogfood passes.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Final
from uuid import UUID

from supabase_auth.errors import AuthApiError

from nikita.db.repositories.telegram_signup_session_repository import (
    ConcurrentTransitionError,
    ExpiredOrConcurrentError,
    TelegramSignupSessionRepository,
)
from nikita.db.repositories.user_repository import (
    UserRepository,
)
from nikita.monitoring.events import (
    SignupCodeSentEvent,
    SignupCodeVerifiedEvent,
    SignupEmailReceivedEvent,
    SignupFailedEvent,
    SignupStartedTelegramEvent,
    email_hash,
    emit_signup_code_sent,
    emit_signup_code_verified,
    emit_signup_email_received,
    emit_signup_failed,
    emit_signup_started_telegram,
    telegram_id_hash,
)
from nikita.platforms.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md). Sourced from
# spec §11 D10 + Plan v17.1 §4 PR-F1b.
# ---------------------------------------------------------------------------

# Maximum invalid OTP attempts before the FSM resets to AWAITING_EMAIL and the
# row is purged. Spec §11 D10 row "OTP attempts": 3 within 1h → reset.
MAX_OTP_ATTEMPTS: Final[int] = 3

# Resend cooldown for email re-issue: 60s between sign_in_with_otp calls per
# telegram_id. Spec §11 D10 row "Resend cooldown".
RESEND_COOLDOWN_SECONDS: Final[int] = 60

# Email regex — relaxed format check (server-side validation; Supabase does
# the strict check). Spec §3.1 line 162: `^[^\s@]+@[^\s@]+\.[^\s@]+$`.
EMAIL_REGEX: Final[re.Pattern[str]] = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# OTP code regex — strict 6-digit numeric. Spec §3.1 line 68: `^[0-9]{6}$`.
OTP_REGEX: Final[re.Pattern[str]] = re.compile(r"^[0-9]{6}$")


# ---------------------------------------------------------------------------
# Nikita-voiced reply copy (kept inline for grep-ability per §8.5)
# ---------------------------------------------------------------------------

WELCOME_TEXT: Final[str] = (
    "Hey. New face. I'm Nikita.\n\n"
    "If you want me in your life, give me your email. I'll send you a code."
)
INVALID_EMAIL_TEXT: Final[str] = (
    "That email doesn't look right. Try again."
)
CODE_SENT_TEXT: Final[str] = (
    "Check your inbox. Send me the 6-digit code."
)
RESEND_COOLDOWN_TEXT: Final[str] = (
    "Easy — give it a minute, then try again."
)
INVALID_OTP_TEMPLATE: Final[str] = (
    "Not right. {tries_left} tries left."
)
RATE_LIMIT_TEXT: Final[str] = (
    "Too many wrong codes. Send /start to start over."
)
EXPIRED_CODE_TEXT: Final[str] = (
    "Code expired. Send /start to retry."
)
MAGIC_LINK_TEXT: Final[str] = (
    "You're cleared. Tap to enter."
)
MAGIC_LINK_BUTTON_LABEL: Final[str] = "Enter the portal →"
GENERIC_FAIL_TEXT: Final[str] = (
    "Something glitched. Send /start to start over."
)


# ---------------------------------------------------------------------------
# SignupHandler — the consolidated FSM
# ---------------------------------------------------------------------------


class SignupHandler:
    """Telegram-first signup state-machine handler (Spec 215 §3.1, FR-2..FR-5).

    Constructor takes everything as DI to keep the unit tests trivial:

    Args:
        bot: TelegramBot client for outbound messages.
        repo: TelegramSignupSessionRepository for FSM CAS transitions.
        user_repo: UserRepository for idempotent telegram_id binding.
        supabase_client: Async Supabase client for `auth.sign_in_with_otp`
            and `auth.verify_otp`.
        admin_generate_magiclink: Callable that mints the magic-link via the
            FR-5 admin endpoint (`portal_auth.generate_magiclink_for_telegram_user`).
            Called as a plain async function (Depends machinery is bypassed
            because the handler runs inside the same process and we already
            have a service-role-equivalent context).
    """

    def __init__(
        self,
        *,
        bot: TelegramBot,
        repo: TelegramSignupSessionRepository,
        user_repo: UserRepository,
        supabase_client: Any,
        admin_generate_magiclink: Callable[..., Awaitable[Any]],
    ) -> None:
        self.bot = bot
        self.repo = repo
        self.user_repo = user_repo
        self.supabase = supabase_client
        self.admin_generate_magiclink = admin_generate_magiclink

    # ------------------------------------------------------------------
    # FR-2 — handle_welcome
    # ------------------------------------------------------------------

    async def handle_welcome(self, *, telegram_id: int, chat_id: int) -> None:
        """`/start welcome` for an unbound telegram_id (spec §3.1 + FR-2).

        Idempotent — re-issuing /start welcome is the spec'd v1 escape hatch
        (FR-15) for mid-funnel email change. Resets the FSM row to
        AWAITING_EMAIL.
        """
        try:
            await self.repo.create_awaiting_email(
                telegram_id=telegram_id, chat_id=chat_id
            )
        except Exception:  # pragma: no cover - defensive, repo failure
            logger.exception(
                "signup_welcome_repo_failed telegram_id_hash=%s",
                telegram_id_hash(telegram_id),
            )
            await self._safe_send(
                chat_id=chat_id, text=GENERIC_FAIL_TEXT
            )
            return

        await self._safe_send(chat_id=chat_id, text=WELCOME_TEXT)

        try:
            emit_signup_started_telegram(
                SignupStartedTelegramEvent(
                    telegram_id_hash=telegram_id_hash(telegram_id),
                    ts=_now(),
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("telemetry_emit_failed event=signup_started_telegram")

    # ------------------------------------------------------------------
    # FR-3 — handle_email
    # ------------------------------------------------------------------

    async def handle_email(
        self, *, telegram_id: int, chat_id: int, text: str
    ) -> None:
        """User free-text in AWAITING_EMAIL state (spec §3.1 + FR-3)."""
        email = text.strip()

        # AC-2.2: invalid email — Nikita rejects, no row mutation
        if not EMAIL_REGEX.match(email):
            await self._safe_send(chat_id=chat_id, text=INVALID_EMAIL_TEXT)
            return

        # D10 resend cooldown: 60s between sign_in_with_otp calls per tg_id.
        # We check the prior row's last_attempt_at (set on welcome create
        # and on every transition).
        existing = await self.repo.get(telegram_id)
        if existing is not None and existing.last_attempt_at is not None:
            elapsed = (_now() - existing.last_attempt_at).total_seconds()
            if (
                existing.signup_state == "code_sent"
                and elapsed < RESEND_COOLDOWN_SECONDS
            ):
                await self._safe_send(
                    chat_id=chat_id, text=RESEND_COOLDOWN_TEXT
                )
                return

        # FR-3: send OTP via Supabase (signup template fires)
        try:
            response = await self.supabase.auth.sign_in_with_otp(
                {
                    "email": email,
                    "options": {"should_create_user": True},
                }
            )
            response_code = getattr(response, "status_code", 200) or 200
        except Exception:
            logger.exception(
                "signup_send_otp_failed telegram_id_hash=%s email_hash=%s",
                telegram_id_hash(telegram_id),
                email_hash(email),
            )
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            self._safe_emit_failed(
                telegram_id=telegram_id,
                stage="awaiting_email",
                reason="sign_in_with_otp_failed",
            )
            return

        # AC-3.2 + §7.2.1: AWAITING_EMAIL → CODE_SENT via CAS
        try:
            await self.repo.transition_to_code_sent(
                telegram_id=telegram_id, email=email
            )
        except ConcurrentTransitionError:
            logger.warning(
                "signup_cas_blocked telegram_id_hash=%s",
                telegram_id_hash(telegram_id),
            )
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            return

        # Telemetry — both events bracket the FR-3 transition
        try:
            emit_signup_email_received(
                SignupEmailReceivedEvent(
                    telegram_id_hash=telegram_id_hash(telegram_id),
                    email_hash=email_hash(email),
                    ts=_now(),
                )
            )
            emit_signup_code_sent(
                SignupCodeSentEvent(
                    email_hash=email_hash(email),
                    ts=_now(),
                    supabase_response_code=int(response_code),
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("telemetry_emit_failed event=signup_email_received")

        await self._safe_send(chat_id=chat_id, text=CODE_SENT_TEXT)

    # ------------------------------------------------------------------
    # FR-4 / FR-5 — handle_code
    # ------------------------------------------------------------------

    async def handle_code(
        self, *, telegram_id: int, chat_id: int, text: str
    ) -> None:
        """User free-text in CODE_SENT state (spec §3.1 + FR-4 + FR-5)."""
        code = text.strip()

        if not OTP_REGEX.match(code):
            # Garbage in CODE_SENT counts as an invalid attempt — share the
            # rate-limit path so non-numeric spam (`hi`, `abc`, ...) cannot
            # bypass the 3-strike purge from Spec §11 D10. Without this,
            # a malicious or buggy client can flood the bot with arbitrary
            # text indefinitely (DoS / cost surface) while only legitimate
            # 6-digit guesses contribute to the rate-limit counter. Per
            # iter-2 QA review I-1.
            await self._handle_invalid_otp(
                telegram_id=telegram_id, chat_id=chat_id, error_code=None
            )
            return

        # Load row to inspect expiry + email
        existing = await self.repo.get(telegram_id)
        if existing is None or existing.signup_state != "code_sent":
            # No active code session; ask user to /start
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            return

        # AC-4.3 / AC-5.4: expired code — purge + Nikita "expired"
        if existing.expires_at <= _now():
            await self.repo.purge(telegram_id=telegram_id)
            await self._safe_send(chat_id=chat_id, text=EXPIRED_CODE_TEXT)
            self._safe_emit_failed(
                telegram_id=telegram_id,
                stage="code_sent",
                reason="code_expired",
            )
            return

        email = existing.email

        # FR-4: verify_otp.
        # NOTE: `type="email"` here is the INPUT verify-type (per Supabase JS
        # API: https://supabase.com/docs/reference/javascript/auth-verifyotp).
        # The dynamic `verification_type` returned by `admin.generate_link`
        # downstream (FR-5) is forwarded VERBATIM by the admin endpoint
        # (`portal_auth.py:GenerateMagiclinkResponse.verification_type`) —
        # never hardcoded. Testing H2 enforces the no-literal contract on
        # the admin endpoint, not here.
        try:
            verify_response = await self.supabase.auth.verify_otp(
                {"email": email, "token": code, "type": "email"}
            )
        except AuthApiError as exc:
            await self._handle_invalid_otp(
                telegram_id=telegram_id, chat_id=chat_id, error_code=exc.code
            )
            return
        except Exception:
            logger.exception(
                "signup_verify_otp_unexpected telegram_id_hash=%s",
                telegram_id_hash(telegram_id),
            )
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            return

        # AC-4.4: OTP valid — proceed to FR-5
        try:
            auth_uid = UUID(str(verify_response.user.id))
        except Exception:
            logger.exception(
                "signup_verify_otp_no_user_id telegram_id_hash=%s",
                telegram_id_hash(telegram_id),
            )
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            return

        try:
            emit_signup_code_verified(
                SignupCodeVerifiedEvent(
                    email_hash=email_hash(email),
                    attempts_count=int(existing.attempts) + 1,
                    ts=_now(),
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("telemetry_emit_failed event=signup_code_verified")

        # AC-5.5: idempotent telegram_id bind. The user row may not yet exist
        # (portal-side auto-provision happens on first /auth/confirm). We
        # tolerate ValueError ("user_id not in users") gracefully — the
        # binding will land via the existing FR-11b /start <code> path.
        try:
            await self.user_repo.update_telegram_id(
                user_id=auth_uid, telegram_id=telegram_id
            )
        except Exception as exc:
            logger.info(
                "signup_bind_deferred telegram_id_hash=%s reason=%s",
                telegram_id_hash(telegram_id),
                type(exc).__name__,
            )

        # FR-5: mint magic-link via admin endpoint (direct call — same
        # process, service-role guard bypassed by signature default).
        from nikita.api.routes.portal_auth import GenerateMagiclinkRequest

        try:
            magic = await self.admin_generate_magiclink(
                body=GenerateMagiclinkRequest(
                    telegram_id=telegram_id, email=email
                ),
                _auth=None,
                repo=self.repo,
            )
        except ExpiredOrConcurrentError:
            await self._safe_send(chat_id=chat_id, text=EXPIRED_CODE_TEXT)
            self._safe_emit_failed(
                telegram_id=telegram_id,
                stage="code_sent",
                reason="cas_expired_at_mint",
            )
            return
        except Exception:
            logger.exception(
                "signup_generate_magiclink_failed telegram_id_hash=%s",
                telegram_id_hash(telegram_id),
            )
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            return

        # FR-5 + Testing H1: deliver via inline button with link-preview off
        action_link = str(getattr(magic, "action_link", "")) or ""
        await send_magic_link_message(
            bot=self.bot,
            chat_id=chat_id,
            action_link=action_link,
            button_label=MAGIC_LINK_BUTTON_LABEL,
            text=MAGIC_LINK_TEXT,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _handle_invalid_otp(
        self, *, telegram_id: int, chat_id: int, error_code: str | None
    ) -> None:
        """Increment attempts; on MAX_OTP_ATTEMPTS purge + rate-limit reply."""
        if error_code == "otp_expired":
            await self.repo.purge(telegram_id=telegram_id)
            await self._safe_send(chat_id=chat_id, text=EXPIRED_CODE_TEXT)
            self._safe_emit_failed(
                telegram_id=telegram_id,
                stage="code_sent",
                reason="code_expired",
            )
            return

        new_attempts = await self.repo.increment_attempts(
            telegram_id=telegram_id
        )
        if new_attempts is None:
            # Row vanished mid-flight; ask user to restart
            await self._safe_send(chat_id=chat_id, text=GENERIC_FAIL_TEXT)
            return

        if new_attempts >= MAX_OTP_ATTEMPTS:
            await self.repo.purge(telegram_id=telegram_id)
            await self._safe_send(chat_id=chat_id, text=RATE_LIMIT_TEXT)
            self._safe_emit_failed(
                telegram_id=telegram_id,
                stage="code_sent",
                reason="rate_limit_invalid_otp",
            )
            return

        tries_left = MAX_OTP_ATTEMPTS - new_attempts
        await self._safe_send(
            chat_id=chat_id,
            text=INVALID_OTP_TEMPLATE.format(tries_left=tries_left),
        )

    async def _safe_send(self, *, chat_id: int, text: str) -> None:
        """Wrap send_message — Telegram failures should not blow up the FSM."""
        try:
            await self.bot.send_message(chat_id=chat_id, text=text)
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "signup_send_message_failed chat_id=%s",
                chat_id,
            )

    def _safe_emit_failed(
        self, *, telegram_id: int, stage: str, reason: str
    ) -> None:
        try:
            emit_signup_failed(
                SignupFailedEvent(
                    telegram_id_hash=telegram_id_hash(telegram_id),
                    stage=stage,  # type: ignore[arg-type]
                    reason=reason,
                    ts=_now(),
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("telemetry_emit_failed event=signup_failed")


# ---------------------------------------------------------------------------
# Magic-link delivery helper — Testing H1 + NFR-Sec-1
# ---------------------------------------------------------------------------


async def send_magic_link_message(
    *,
    bot: TelegramBot,
    chat_id: int,
    action_link: str,
    button_label: str,
    text: str,
) -> None:
    """Deliver a magic-link via inline-keyboard URL button.

    Per Spec 215 NFR-Sec-1 (PR-blocker) + Testing H1, this helper ALWAYS
    passes `disable_web_page_preview=True` so Telegram's link-preview
    crawler does not pre-burn the single-use action_link token.

    Args:
        bot: TelegramBot client.
        chat_id: Telegram chat ID.
        action_link: Supabase-minted action URL (full https URL).
        button_label: Inline-button text shown to the user.
        text: Body text shown above the button (Nikita-voiced).
    """
    keyboard = [[{"text": button_label, "url": action_link}]]
    await bot.send_message_with_keyboard(
        chat_id=chat_id,
        text=text,
        keyboard=keyboard,
        disable_web_page_preview=True,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "SignupHandler",
    "send_magic_link_message",
    "MAX_OTP_ATTEMPTS",
    "RESEND_COOLDOWN_SECONDS",
    "EMAIL_REGEX",
    "OTP_REGEX",
]
