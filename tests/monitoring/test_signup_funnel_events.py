"""Tests for signup funnel telemetry events (Spec 215 §8.7 Testing H5).

Each of the 9 funnel events is a Pydantic v2 model. Per row:
(a) emitter call uses the named Pydantic model (not free-form dict)
(b) model_dump_json() round-trip emits NO PII (no raw email, telegram_id,
    phone, name) — only *_hash derivatives
(c) anti-pattern grep gate (`test_no_raw_pii_in_emitter_calls`) on the
    production source.
"""

import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# AC-1: emitter helpers exist + use the named Pydantic model.
# ---------------------------------------------------------------------------


def test_event_module_exports_all_nine_models_and_emitters():
    """All 9 Pydantic models + their emitter helpers exist."""
    from nikita.monitoring import events

    expected_models = [
        "SignupStartedTelegramEvent",
        "SignupEmailReceivedEvent",
        "SignupCodeSentEvent",
        "SignupCodeVerifiedEvent",
        "SignupMagicLinkMintedEvent",
        "SignupMagicLinkClickedEvent",
        "SignupWizardSessionMintedEvent",
        "SignupWizardCompletedEvent",
        "SignupFailedEvent",
    ]
    for name in expected_models:
        assert hasattr(events, name), f"Missing event model: {name}"

    expected_emitters = [
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
    for name in expected_emitters:
        assert hasattr(events, name), f"Missing emitter helper: {name}"


# ---------------------------------------------------------------------------
# AC-2: model_dump_json() round-trip — no PII fields.
# ---------------------------------------------------------------------------

PII_KEYS = {"email", "telegram_id", "phone", "name"}


def _assert_no_pii(payload_dict: dict, model_name: str) -> None:
    """Recursive assertion that no PII keys appear in the dump."""
    for k in payload_dict:
        assert k not in PII_KEYS, (
            f"{model_name} contains raw PII key '{k}'. "
            "Use *_hash derivative (sha256(...)[:12])."
        )
    # Also assert the JSON string body has no obvious PII keys
    blob = json.dumps(payload_dict)
    for pii in PII_KEYS:
        assert f'"{pii}"' not in blob, (
            f"{model_name} JSON dump contains key '{pii}': {blob}"
        )


@pytest.mark.parametrize(
    "model_name,kwargs",
    [
        (
            "SignupStartedTelegramEvent",
            {"telegram_id_hash": "abc123def456", "ts": datetime.now(timezone.utc)},
        ),
        (
            "SignupEmailReceivedEvent",
            {
                "telegram_id_hash": "abc123def456",
                "email_hash": "def456abc789",
                "ts": datetime.now(timezone.utc),
            },
        ),
        (
            "SignupCodeSentEvent",
            {
                "email_hash": "def456abc789",
                "ts": datetime.now(timezone.utc),
                "supabase_response_code": 200,
            },
        ),
        (
            "SignupCodeVerifiedEvent",
            {
                "email_hash": "def456abc789",
                "attempts_count": 1,
                "ts": datetime.now(timezone.utc),
            },
        ),
        (
            "SignupMagicLinkMintedEvent",
            {
                "email_hash": "def456abc789",
                "ts": datetime.now(timezone.utc),
                "action_link_ttl_seconds": 3600,
                "verification_type": "magiclink",
            },
        ),
        (
            "SignupMagicLinkClickedEvent",
            {
                "email_hash": "def456abc789",
                "ts": datetime.now(timezone.utc),
                "latency_ms_from_mint": 1200,
            },
        ),
        (
            "SignupWizardSessionMintedEvent",
            {"user_id": uuid4(), "ts": datetime.now(timezone.utc)},
        ),
        (
            "SignupWizardCompletedEvent",
            {
                "user_id": uuid4(),
                "ts": datetime.now(timezone.utc),
                "total_signup_to_complete_ms": 60000,
            },
        ),
        (
            "SignupFailedEvent",
            {
                "telegram_id_hash": "abc123def456",
                "stage": "code_sent",
                "reason": "invalid_otp",
            },
        ),
    ],
)
def test_event_model_serializes_without_pii(model_name, kwargs):
    """Each event model round-trips JSON cleanly with NO PII keys."""
    from nikita.monitoring import events

    Model = getattr(events, model_name)
    instance = Model(**kwargs)

    # Pydantic v2 model_dump_json() should succeed and contain no PII keys.
    blob = instance.model_dump_json()
    parsed = json.loads(blob)
    _assert_no_pii(parsed, model_name)


# ---------------------------------------------------------------------------
# AC-2 supplemental: hashing helpers return sha256(...)[:12].
# ---------------------------------------------------------------------------


def test_email_hash_helper_returns_12_char_sha256_prefix():
    from nikita.monitoring.events import email_hash

    h = email_hash("user@example.com")
    assert isinstance(h, str)
    assert len(h) == 12
    # Deterministic for same input
    assert h == email_hash("user@example.com")
    # Different for different input
    assert h != email_hash("other@example.com")


def test_telegram_id_hash_helper_returns_12_char_sha256_prefix():
    from nikita.monitoring.events import telegram_id_hash

    h = telegram_id_hash(424242)
    assert isinstance(h, str)
    assert len(h) == 12
    assert h == telegram_id_hash(424242)
    assert h != telegram_id_hash(515151)


# ---------------------------------------------------------------------------
# AC-3: anti-pattern grep gate over the events module — no raw PII kwargs
# inside the module itself when emitter helpers internally invoke logger.
# ---------------------------------------------------------------------------


def test_no_raw_pii_in_emitter_calls():
    """Search the production events module: no `email=`, `telegram_id=`,
    `phone=`, or `name=` kwargs in emitter call sites except in hashing
    helper functions.
    """
    src_path = Path(__file__).resolve().parents[2] / "nikita" / "monitoring" / "events.py"
    source = src_path.read_text()

    # Strip the helper definitions (email_hash, telegram_id_hash) bodies —
    # they legitimately accept raw PII.
    for fn in ("email_hash", "telegram_id_hash"):
        source = re.sub(
            rf"def {fn}\([^)]*\)[^:]*:.*?(?=\ndef |\nclass |\Z)",
            "",
            source,
            flags=re.DOTALL,
        )

    # Now search emitter functions for raw-PII kwargs.
    bad = re.findall(r"\b(email|telegram_id|phone|name)\s*=\s*[^_h]", source)
    # Filter to only the bad kwargs, not field names within Pydantic models
    # (which have `: type = Field(...)` patterns). Use a tighter regex:
    bad_calls = []
    for line_num, line in enumerate(source.splitlines(), start=1):
        # Match function CALLS (parenthesized arg lists), not class definitions
        if re.search(
            r"(emit_|logger\.(?:info|warning|error|debug|exception)).*\b(email|telegram_id|phone|name)\s*=",
            line,
        ):
            # Allow if the value is a hash (e.g., email_hash=email_hash(...))
            if not re.search(r"\b(email_hash|telegram_id_hash)\s*=", line):
                bad_calls.append((line_num, line.strip()))

    assert bad_calls == [], (
        f"Found raw PII kwargs in emitter call sites: {bad_calls}. "
        "Use email_hash() / telegram_id_hash() helpers."
    )
