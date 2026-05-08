"""JSONB sidecar persistence helpers for ``users.onboarding_profile.pending_followup``.

Spec 217-3A AC-8.2 — the sidecar is set when the agent emits
``FollowUpQuestion`` and cleared when the user's next answer resolves
the followup. Cleanup MUST use the JSONB ``#-`` (key removal) operator,
NOT a JSON ``null`` literal write — see AC-8.2 forbidden-shape rule.
The cleanup test (AC-8.2bis) asserts ``onboarding_profile ?
'pending_followup'`` returns ``False`` after resolution.

Why a separate module:
  - The /answer route (``portal_onboarding.py``) is large (~2075 LOC);
    co-locating sidecar SQL there increases the route's surface area.
  - 217-3A.3 wires these helpers into the route. Until then, having
    them in a dedicated module lets the unit tests cover SQL shape
    without booting the full route stack.

Hard Rule §1 separation (``.claude/rules/agentic-design-patterns.md``):
  ``WizardSlots`` holds cumulative slot data — gate input.
  ``AgentEmissionState`` (transient) holds ``pending_followup`` —
    NEVER a slot, NEVER feeds ``FinalForm.model_validate``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.onboarding.converse_contracts import FollowUpQuestion


async def persist_pending_followup(
    session: AsyncSession,
    *,
    user_id: UUID,
    followup: FollowUpQuestion,
) -> None:
    """Set ``users.onboarding_profile.pending_followup`` to the followup JSONB.

    Spec 217-3A AC-8.2. ``jsonb_set`` upserts the key under
    ``onboarding_profile``; if ``onboarding_profile`` itself is NULL the
    update is a no-op (defensive: the /answer route hydrates the column
    to ``{}`` before reaching this call site, so NULL is unreachable in
    production). The followup is serialized via ``model_dump`` so the
    JSONB writer round-trips with key absence (``exclude_none=True`` is
    not required here — ``FollowUpQuestion`` has no nullable fields).
    """
    payload = followup.model_dump_json()
    await session.execute(
        text(
            "UPDATE users "
            "SET onboarding_profile = jsonb_set("
            "  COALESCE(onboarding_profile, '{}'::jsonb), "
            "  '{pending_followup}', "
            "  CAST(:payload AS jsonb)"
            ") "
            "WHERE id = :user_id"
        ),
        {"user_id": str(user_id), "payload": payload},
    )


async def clear_pending_followup(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> None:
    """Remove the ``pending_followup`` key from ``onboarding_profile``.

    Spec 217-3A AC-8.2 forbidden-shape rule: the ``#-`` operator deletes
    the key at the given path. Setting the value to a JSON ``null``
    literal (e.g., ``jsonb_set(..., 'null'::jsonb)``) is FORBIDDEN —
    it leaves the key present and forces every downstream reader to
    disambiguate "absent" vs "null". After this call, AC-8.2bis verifies
    ``SELECT onboarding_profile ? 'pending_followup' FROM users WHERE
    id = :uid`` returns ``False``.
    """
    await session.execute(
        text(
            "UPDATE users "
            "SET onboarding_profile = onboarding_profile #- '{pending_followup}' "
            "WHERE id = :user_id"
        ),
        {"user_id": str(user_id)},
    )


__all__ = ["clear_pending_followup", "persist_pending_followup"]
