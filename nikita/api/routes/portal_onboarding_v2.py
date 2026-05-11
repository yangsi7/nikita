"""Spec 218 Slice 218-2 — v2 route handler + R12 hard-error + R15 retry.

The v2 surface is intentionally a separate module from the legacy
``portal_onboarding.py`` to keep slice rollout reversible (per plan
§Per-slice constants R10). PR-218-8 will atomically delete both v1 and
this transitional shim once v2 covers all 11 Phase-1 slots.

Routes added in this slice:
  - ``POST /api/v1/converse/onboarding/retry`` (R15)

The flag-gated v2 branch inside the existing ``POST /answer`` handler
is wired in ``portal_onboarding.py`` itself (see plan R1 — flag check
MUST precede any persistence call).

Exception types defined here are caught at the route boundary and
converted to the R12 error envelope.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.onboarding.v2.decorator_agent import (
    V2Deps,
    get_decorator_agent,
)
from nikita.agents.onboarding.v2.envelope import (
    AskUnion,
    HandlerHandoffAsk,
    TextShortAsk,
)
from nikita.agents.onboarding.v2.router import pick_next_target
from nikita.agents.onboarding.v2.session_helper import (
    migration_or_init_v2_session,
)
from nikita.agents.onboarding.v2.state import (
    SlotDeltaV2,
    SlotKindV2,
    WizardSlotsV2,
)
from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
)
from nikita.api.routes.portal_onboarding import get_async_session
from nikita.db.repositories.user_repository import UserRepository
from nikita.onboarding.idempotency import IdempotencyStore


router = APIRouter(tags=["Portal Onboarding v2"])


# ---------------------------------------------------------------------------
# Exceptions — converted to R12 / R15 envelopes at route boundary
# ---------------------------------------------------------------------------


@dataclass
class V2DecoratorFailure(Exception):
    """Raised by ``handle_v2_answer`` when decorator agent invocation fails.

    Per plan R12: response is HTTP 500 with envelope
    ``{error_code: "v2_decorator_failure", session_id, retry_url}``.
    NO automatic v1 fallback — that would corrupt state schema and
    violate the sticky-flag invariant (R11).
    """

    error_code: str
    session_id: UUID
    retry_url: str
    detail: str | None = None


@dataclass
class RetryBudgetExhausted(Exception):
    """Raised by ``handle_v2_retry`` after 3 retries on the same slot.

    Per plan R15: response is HTTP 503 with envelope
    ``{error: "session_unrecoverable"}``. FE shows "restart onboarding"
    CTA.
    """

    session_id: UUID


# ---------------------------------------------------------------------------
# Retry-budget tracking (R15)
# ---------------------------------------------------------------------------


_RETRY_BUDGET_HARD_LIMIT: int = 3
"""Hard cap on retry calls for a single (session_id) — R15.

Current value: 3 (Spec 218 Slice 218-2, plan R15).
Prior values: none (new in PR-218-2).
Rationale: budget is per-session, counts ALL retry POSTs for that
session regardless of which slot. After 3, FE shows restart-onboarding
CTA. Counts toward `cost_guard.FLOW_HARD_CEILING_USD` separately at
invocation time.
"""


# In-process counter keyed by session_id. Acceptable for solo-dev
# single-instance Cloud Run scaled-to-zero (Cloud Run resets on cold
# start, which doubles as a coarse eviction signal). Pre-launch posture:
# zero retained users + ephemeral state is the constraint, not the bug.
#
# TODO (post-launch, when traffic > 1 RPS OR multi-instance):
# - Back this counter with `users.onboarding_profile` JSONB
#   (`retry_counts: {session_id: int}`) for cross-instance durability.
# - Add per-session TTL eviction (clear on Phase-1 complete OR after
#   24h idle) so the dict cannot grow unboundedly within a single
#   long-lived instance.
_retry_counts: dict[UUID, int] = {}


def get_retry_count(session_id: UUID) -> int:
    """Return the number of retry POSTs observed for ``session_id``.

    Mockable seam for ``handle_v2_retry`` (tests patch this).
    """
    return _retry_counts.get(session_id, 0)


def _increment_retry_count(session_id: UUID) -> int:
    new_count = _retry_counts.get(session_id, 0) + 1
    _retry_counts[session_id] = new_count
    return new_count


# ---------------------------------------------------------------------------
# Request / response contracts
# ---------------------------------------------------------------------------


class V2RetryRequest(BaseModel):
    """Body for ``POST /api/v1/converse/onboarding/retry``.

    ``retry_token`` is the client's idempotency key. Same
    ``(session_id, retry_token)`` MUST return the same envelope (or
    HTTP 410 if the session resolved between calls).
    """

    session_id: UUID
    retry_token: str = Field(min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# Handler — v2 /answer branch
# ---------------------------------------------------------------------------


async def handle_v2_answer(
    req: Any,
    user: Any,
    session: AsyncSession,
) -> AskUnion:
    """Run one v2 turn for the given user.

    The caller (the existing ``/answer`` handler in ``portal_onboarding.py``)
    invokes this AFTER ``migration_or_init_v2_session`` confirms ``use_v2``.

    Raises:
        V2DecoratorFailure — wrapping any exception raised by the
            decorator agent's ``run()`` call (Pydantic AI exceptions,
            model timeouts, output-validator exhaustion). The route
            boundary catches and emits the R12 envelope.

    Returns:
        One ``AskUnion`` envelope (typically ``TextShortAsk`` for the
        target slot OR ``HandlerHandoffAsk`` when target is not covered
        by this slice).
    """
    # Hydrate cumulative state from the user's JSONB. Defensive on
    # non-dict payloads (test mocks, malformed DB rows) — fall back to
    # an empty WizardSlotsV2 rather than ValidationError mid-turn.
    profile_raw = user.onboarding_profile
    profile: dict[str, Any] = profile_raw if isinstance(profile_raw, dict) else {}
    slots_payload = profile.get("slots", {})
    slots = (
        WizardSlotsV2.model_validate(slots_payload)
        if isinstance(slots_payload, dict) and slots_payload
        else WizardSlotsV2()
    )

    # Router picks the next target slot (deterministic).
    target = pick_next_target(slots)
    if target is None:
        # Phase 1 complete — emit a CompleteAsk-equivalent handoff.
        # Slice 218-2 routes Phase-1-complete sessions through v1 for
        # backstory generation (Phase 2 lands in slice 218-6).
        return HandlerHandoffAsk(
            component="handler_handoff",
            handler="v1",
            next_url="/api/v1/converse/onboarding",
        )

    deps = V2Deps(
        user_id=user.id,
        slots=slots,
        target_slot=target.value if hasattr(target, "value") else str(target),
    )

    agent = get_decorator_agent()
    try:
        result = await agent.run(
            "",  # Prompt body comes from dynamic instructions + message_history.
            message_history=profile.get("messages", []),
            deps=deps,
        )
    except Exception as exc:  # noqa: BLE001 — intentional R12 catch-all
        # Derive a stable session_id from the user's real identity so
        # the client's `/retry` POST scopes the retry-count bucket
        # against the actual onboarding session, not a phantom UUID
        # (which would silently reset the budget every failure and
        # break the R15 3-retry hard cap).
        raise V2DecoratorFailure(
            error_code="v2_decorator_failure",
            session_id=deps.conversation_id,
            retry_url="/api/v1/converse/onboarding/retry",
            detail=str(exc),
        ) from exc

    return result.output


# ---------------------------------------------------------------------------
# Handler — /retry endpoint (R15)
# ---------------------------------------------------------------------------


async def handle_v2_retry(
    session_id: UUID,
    retry_token: str,
    user_id: UUID,
    session: AsyncSession,
) -> dict[str, Any]:
    """Re-emit the envelope for the current target slot.

    Idempotent on ``(session_id, retry_token)`` via ``IdempotencyStore``.
    Counts toward ``_RETRY_BUDGET_HARD_LIMIT``; exhaustion raises
    ``RetryBudgetExhausted`` (caller emits HTTP 503).
    """
    if get_retry_count(session_id) >= _RETRY_BUDGET_HARD_LIMIT:
        raise RetryBudgetExhausted(session_id=session_id)

    # Idempotency replay path.
    idem = IdempotencyStore(session)
    # Synthesize a stable turn_id from (session_id, retry_token) for
    # the cache key via SHA-256 over the full token. The earlier
    # naive truncation of first 16 bytes collided for tokens sharing
    # a 16-byte prefix; hashing the full token bytes is collision-safe
    # and uses all 128 chars of the token's keyspace. Scoping the hash
    # by session_id additionally prevents cross-session token reuse.
    digest = hashlib.sha256(
        b"v2-retry|" + str(session_id).encode() + b"|" + retry_token.encode()
    ).digest()
    cache_key_turn = UUID(bytes=digest[:16])
    cached = await idem.get(user_id, cache_key_turn)
    if cached is not None:
        cached_body, _status = cached
        return cached_body

    # Cache miss → re-run the v2 handler for the current target slot.
    repo = UserRepository(session)
    user = await repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Minimal request stub — handle_v2_answer reads from user.onboarding_profile.
    envelope = await handle_v2_answer(req=None, user=user, session=session)
    body = envelope.model_dump(mode="json")

    await idem.put(
        user_id=user_id,
        turn_id=cache_key_turn,
        response_body=body,
        status_code=200,
    )
    _increment_retry_count(session_id)
    return body


# ---------------------------------------------------------------------------
# Route — POST /api/v1/converse/onboarding/retry
# ---------------------------------------------------------------------------


@router.post(
    "/converse/onboarding/retry",
    summary="Spec 218 R15 — retry the current v2 envelope",
    description=(
        "Re-emits the v2 envelope for the current target slot. Idempotent "
        "on (session_id, retry_token). After 3 retries the response is "
        "503 with {error: 'session_unrecoverable'}."
    ),
)
async def retry_endpoint(
    req: V2RetryRequest,
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    try:
        return await handle_v2_retry(
            session_id=req.session_id,
            retry_token=req.retry_token,
            user_id=current_user.id,
            session=session,
        )
    except RetryBudgetExhausted as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "session_unrecoverable", "session_id": str(exc.session_id)},
        ) from exc


__all__ = [
    "RetryBudgetExhausted",
    "V2DecoratorFailure",
    "V2RetryRequest",
    "get_retry_count",
    "handle_v2_answer",
    "handle_v2_retry",
    "router",
]
