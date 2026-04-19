"""Regression guard for portal_bridge_token tuning constants.

Per `.claude/rules/tuning-constants.md`: every TTL / threshold matrix
needs an exact-value test pointing at the driving issue. Silent drift
in the TTL matrix would change the bridge-link UX (24h resume window
vs 1h re-onboard) without anyone reviewing the change.

Driver: Spec 214 FR-11c AC-11c.12 (PR 1 nitpick — promote private
constants to public so importers and tests share one source of truth).
"""

from __future__ import annotations

from datetime import timedelta

from nikita.db.models.portal_bridge_token import (
    TTL_BY_REASON,
    VALID_REASONS,
)


def test_ttl_matrix_locked() -> None:
    """TTL matrix exact values: resume=24h, re-onboard=1h."""
    assert TTL_BY_REASON == {
        "resume": timedelta(hours=24),
        "re-onboard": timedelta(hours=1),
    }


def test_valid_reasons_locked() -> None:
    """Allowed reasons are exactly {'resume', 're-onboard'}."""
    assert VALID_REASONS == frozenset({"resume", "re-onboard"})
