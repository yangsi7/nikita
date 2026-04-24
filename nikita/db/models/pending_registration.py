"""Backward-compat shim — Spec 215 PR-F1a renamed this model.

The model now lives in `telegram_signup_session.py`. This file re-exports
`PendingRegistration` (aliased to `TelegramSignupSession`) so existing
imports keep working until PR-F3 deletes the legacy handlers and migrates
all callers to the new name.
"""

from nikita.db.models.telegram_signup_session import (  # noqa: F401
    PendingRegistration,
    TelegramSignupSession,
)
