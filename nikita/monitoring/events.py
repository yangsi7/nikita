"""Signup-funnel telemetry events (Spec 215 §8.7 Testing H5).

Each of the 9 funnel events is a Pydantic v2 model carrying ONLY hashed PII
(`email_hash`, `telegram_id_hash`) — no raw email, no raw telegram_id, no
phone, no name. The hashing helpers (`email_hash`, `telegram_id_hash`)
return `sha256(...)[:12]` so the dashboard can dedupe events without
de-anonymising users.

Each model has a paired `emit_*` helper that serialises the event and writes
it through the structured logger at INFO level. The structured-log envelope
is intentionally JSON so downstream telemetry sinks (Cloud Logging →
BigQuery) can parse without regex.

Anti-pattern guarded by `tests/monitoring/test_signup_funnel_events.py`:
no raw PII kwargs in any emitter call site.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger("nikita.signup_funnel")


# ---------------------------------------------------------------------------
# Hashing helpers — sha256(...)[:12] for dashboard-stable, non-PII identifiers.
# ---------------------------------------------------------------------------


def email_hash(value: str) -> str:
    """Return a 12-char sha256 prefix of the email (case-insensitive,
    whitespace-trimmed) for dashboard correlation without storing the raw
    email."""
    norm = value.strip().lower().encode("utf-8")
    return hashlib.sha256(norm).hexdigest()[:12]


def telegram_id_hash(value: int) -> str:
    """Return a 12-char sha256 prefix of the telegram_id for dashboard
    correlation."""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# 9 Pydantic event models (per spec §8.7 H5 table)
# ---------------------------------------------------------------------------


class SignupStartedTelegramEvent(BaseModel):
    """`/start welcome` consumed; user entered the FSM."""

    telegram_id_hash: str
    ts: datetime


class SignupEmailReceivedEvent(BaseModel):
    """User typed an email in AWAITING_EMAIL."""

    telegram_id_hash: str
    email_hash: str
    ts: datetime


class SignupCodeSentEvent(BaseModel):
    """`sign_in_with_otp` returned successfully and the FSM advanced to
    CODE_SENT."""

    email_hash: str
    ts: datetime
    supabase_response_code: int


class SignupCodeVerifiedEvent(BaseModel):
    """User submitted a valid OTP code."""

    email_hash: str
    attempts_count: int
    ts: datetime


class SignupMagicLinkMintedEvent(BaseModel):
    """`admin.generate_link` returned; FSM advanced to MAGIC_LINK_SENT."""

    email_hash: str
    ts: datetime
    action_link_ttl_seconds: int
    verification_type: Literal["magiclink", "signup"]


class SignupMagicLinkClickedEvent(BaseModel):
    """User tapped the magic link in Telegram."""

    email_hash: str
    ts: datetime
    latency_ms_from_mint: int


class SignupWizardSessionMintedEvent(BaseModel):
    """Portal `/auth/confirm` succeeded and a session was minted."""

    user_id: UUID
    ts: datetime


class SignupWizardCompletedEvent(BaseModel):
    """Wizard reached COMPLETED state and the user landed on /dashboard."""

    user_id: UUID
    ts: datetime
    total_signup_to_complete_ms: int


class SignupFailedEvent(BaseModel):
    """A terminal failure in the FSM (rate-limit hit, expired code with
    no recovery, etc.)."""

    telegram_id_hash: str
    stage: Literal["awaiting_email", "code_sent", "magic_link_sent"]
    reason: str
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Emitter helpers — one per event, all accept the named Pydantic model.
# ---------------------------------------------------------------------------


def _emit(event_name: str, model: BaseModel) -> None:
    """Write the event to the structured logger with a stable JSON envelope.

    `event_name` is logged as a top-level field so downstream filtering
    (e.g., BigQuery WHERE clauses) can index on it cheaply.
    """
    payload = json.loads(model.model_dump_json())
    logger.info(
        "signup_funnel_event",
        extra={"event": event_name, "payload": payload},
    )


def emit_signup_started_telegram(event: SignupStartedTelegramEvent) -> None:
    _emit("signup_started_telegram", event)


def emit_signup_email_received(event: SignupEmailReceivedEvent) -> None:
    _emit("signup_email_received", event)


def emit_signup_code_sent(event: SignupCodeSentEvent) -> None:
    _emit("signup_code_sent", event)


def emit_signup_code_verified(event: SignupCodeVerifiedEvent) -> None:
    _emit("signup_code_verified", event)


def emit_signup_magic_link_minted(event: SignupMagicLinkMintedEvent) -> None:
    _emit("signup_magic_link_minted", event)


def emit_signup_magic_link_clicked(event: SignupMagicLinkClickedEvent) -> None:
    _emit("signup_magic_link_clicked", event)


def emit_signup_wizard_session_minted(event: SignupWizardSessionMintedEvent) -> None:
    _emit("signup_wizard_session_minted", event)


def emit_signup_wizard_completed(event: SignupWizardCompletedEvent) -> None:
    _emit("signup_wizard_completed", event)


def emit_signup_failed(event: SignupFailedEvent) -> None:
    _emit("signup_failed", event)


__all__ = [
    "email_hash",
    "telegram_id_hash",
    # Models
    "SignupStartedTelegramEvent",
    "SignupEmailReceivedEvent",
    "SignupCodeSentEvent",
    "SignupCodeVerifiedEvent",
    "SignupMagicLinkMintedEvent",
    "SignupMagicLinkClickedEvent",
    "SignupWizardSessionMintedEvent",
    "SignupWizardCompletedEvent",
    "SignupFailedEvent",
    # Emitters
    "emit_signup_started_telegram",
    "emit_signup_email_received",
    "emit_signup_code_sent",
    "emit_signup_code_verified",
    "emit_signup_magic_link_minted",
    "emit_signup_magic_link_clicked",
    "emit_signup_wizard_session_minted",
    "emit_signup_wizard_completed",
    "emit_signup_failed",
]
