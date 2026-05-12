"""Spec 218 Slice 218-2 / 218-3 — v2 route handler + R12 + R15 + apply-persist.

The v2 surface is intentionally a separate module from the legacy
``portal_onboarding.py`` to keep slice rollout reversible (per plan
§Per-slice constants R10). PR-218-8 will atomically delete both v1 and
this transitional shim once v2 covers all 11 Phase-1 slots.

Routes added:
  - Slice 218-2: ``POST /api/v1/converse/onboarding/retry`` (R15)

Slice 218-3 additions:
  - ``_apply_prior_submission`` helper extracts req.slot_kind+value,
    builds ``SlotDeltaV2``, persists updated ``onboarding_profile.slots``
    JSONB via ``UserRepository.update_onboarding_profile`` BEFORE the
    decorator picks the next target. Closes the slice-218-2 latent gap
    where ``handle_v2_answer`` emitted asks but never advanced state.
  - Supported v2 slot persistence: display_name, age (ISO DoB → int),
    city (option value), occupation. Slices 218-4 / 218-5 extend.

The flag-gated v2 branch inside the existing ``POST /answer`` handler
is wired in ``portal_onboarding.py`` itself (see plan R1 — flag check
MUST precede any persistence call).

Exception types defined here are caught at the route boundary and
converted to the R12 error envelope.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.onboarding.v2.decorator_agent import (
    CHIP_MULTI_MAX_PICK,
    SLIDER_MAX_VAL,
    SLIDER_MIN_VAL,
    TEXT_LONG_MAX_CHARS,
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
from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history
from nikita.api.routes.portal_onboarding import get_async_session
from nikita.db.repositories.user_repository import UserRepository
from nikita.onboarding.idempotency import IdempotencyStore


# ---------------------------------------------------------------------------
# Apply-prior-submission helper (Slice 218-3)
# ---------------------------------------------------------------------------


_PERSISTABLE_SLOT_NAMES: frozenset[str] = frozenset(
    {
        SlotKindV2.display_name.value,
        SlotKindV2.age.value,
        SlotKindV2.city.value,
        SlotKindV2.occupation.value,
        SlotKindV2.primary_hobbies.value,
        SlotKindV2.hangouts_personalized.value,
        SlotKindV2.voice_or_text.value,
        SlotKindV2.phone.value,
        SlotKindV2.saturday_morning.value,
        SlotKindV2.darkness_level.value,
        SlotKindV2.geek_out_on.value,
    }
)
"""Slot names whose submissions slice-218-5 knows how to persist (full Phase-1).

Slice 218-8 collapses this into the full Phase-1 set as v1 is bulldozed.
"""


def _today() -> date:
    """Return today's date. Injectable seam for tests that need to
    freeze the wall clock (e.g., reproducible age computation across
    midnight crossovers). Tests monkeypatch this function via
    ``monkeypatch.setattr(portal_onboarding_v2, "_today", lambda: date(...))``.
    """
    return date.today()


def _slot_payload(slot_name: str, raw_value: Any) -> dict[str, Any] | None:
    """Wrap raw request value into the slot-specific data payload dict.

    Returns ``None`` when the raw value is malformed for the slot (caller
    treats this as "ignore — re-ask the same target").

    Per-slot conversion:
      - display_name         : non-empty string -> ``{display_name: stripped}``
      - age                  : ISO date string  -> ``{age: int, dob: "YYYY-MM-DD"}``
      - city                 : non-empty string -> ``{city: stripped}``
      - occupation           : non-empty string -> ``{occupation: stripped}``
      - primary_hobbies      : list[str] 1-5 non-empty items -> ``{primary_hobbies: [..]}``
      - hangouts_personalized: list[str] 1-5 non-empty items -> ``{hangouts_personalized: [..]}``
      - voice_or_text        : "voice"|"text"   -> ``{voice_or_text: value}``
      - phone                : E.164 str        -> ``{phone: value}``
    """
    import re  # noqa: PLC0415 — local import keeps module top-level lean

    if slot_name == SlotKindV2.display_name.value:
        if isinstance(raw_value, str) and raw_value.strip():
            return {"display_name": raw_value.strip()}
        return None
    if slot_name == SlotKindV2.age.value:
        if not isinstance(raw_value, str):
            return None
        try:
            dob = date.fromisoformat(raw_value)
        except ValueError:
            return None
        today = _today()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        # Reject age <= 0 (DoB == today or in the future) and age > 130
        # (clearly nonsensical). FinalForm cross-field validator separately
        # enforces ``age >= MIN_USER_AGE`` (18) at Phase-1 completion; we
        # use the weaker bound here so the slot can be persisted during
        # collection without violating the gate prematurely.
        if age <= 0 or age > 130:
            return None
        return {"age": age, "dob": raw_value}
    if slot_name == SlotKindV2.city.value:
        if isinstance(raw_value, str) and raw_value.strip():
            return {"city": raw_value.strip()}
        return None
    if slot_name == SlotKindV2.occupation.value:
        if isinstance(raw_value, str) and raw_value.strip():
            return {"occupation": raw_value.strip()}
        return None
    if slot_name in (
        SlotKindV2.primary_hobbies.value,
        SlotKindV2.hangouts_personalized.value,
    ):
        # chip_multi: list[str] with 1-5 non-empty items.
        if not isinstance(raw_value, list):
            return None
        items = [v.strip() for v in raw_value if isinstance(v, str) and v.strip()]
        if not items or len(items) > CHIP_MULTI_MAX_PICK:
            return None
        return {slot_name: items}
    if slot_name == SlotKindV2.voice_or_text.value:
        if raw_value not in ("voice", "text"):
            return None
        return {"voice_or_text": raw_value}
    if slot_name == SlotKindV2.phone.value:
        # E.164: starts with +, followed by 7-15 digits, first digit ≠ 0.
        # Regex: ^\+[1-9]\d{6,14}$  (total 7-15 digit chars after the +).
        if not isinstance(raw_value, str):
            return None
        if not re.match(r"^\+[1-9]\d{6,14}$", raw_value):
            return None
        return {"phone": raw_value}
    if slot_name in (
        SlotKindV2.saturday_morning.value,
        SlotKindV2.darkness_level.value,
    ):
        # slider: int in [0, 10]; floats and out-of-range ints are rejected.
        if not isinstance(raw_value, int) or isinstance(raw_value, bool):
            return None
        if raw_value < SLIDER_MIN_VAL or raw_value > SLIDER_MAX_VAL:
            return None
        return {slot_name: raw_value}
    if slot_name == SlotKindV2.geek_out_on.value:
        # text_long: non-empty string stripped, max TEXT_LONG_MAX_CHARS chars.
        if not isinstance(raw_value, str):
            return None
        stripped = raw_value.strip()
        if not stripped or len(stripped) > TEXT_LONG_MAX_CHARS:
            return None
        return {"geek_out_on": stripped}
    return None


def _apply_prior_submission(
    req: Any,
    slots: WizardSlotsV2,
    profile: dict[str, Any],
) -> tuple[WizardSlotsV2, dict[str, Any] | None]:
    """If ``req`` carries a known slot submission, apply + return new state.

    Returns ``(new_slots, profile_updates_or_None)``. When
    ``profile_updates_or_None`` is not None, the caller MUST persist via
    ``UserRepository.update_onboarding_profile`` BEFORE invoking the
    decorator agent.

    Reasons we may return ``(slots, None)`` (no-op):
      - ``req`` is None (caller bypasses; e.g., /retry endpoint)
      - ``req`` lacks slot_kind / value attributes
      - slot_kind not in ``_PERSISTABLE_SLOT_NAMES``
      - raw value malformed for the slot (e.g., unparseable DoB)

    Silent-ignore on malformed input is deliberate — the decorator
    re-asks the same target on the next turn, giving the user another
    attempt. Hard-fail would corrupt the sticky-flag invariant (R11).

    Pop semantics (FR-007 DAG invalidation):
      When ``invalidate_dependents`` returns non-empty ``invalidated``,
      this helper ``pop``-s those keys from ``merged_slots``. The pop
      is effective because ``UserRepository.update_onboarding_profile``
      MERGES at the TOP-level profile dict (``{**existing, **updates}``)
      which means the entire ``slots`` sub-dict is REPLACED by
      ``merged_slots`` — popped keys are dropped from the persisted
      JSONB. If ``update_onboarding_profile`` ever switches to a
      patch-merge at the slot level, this pop-semantics breaks; in that
      case the helper would need to write explicit ``slot_name: None``
      override values rather than dropping keys.
    """
    if req is None:
        return slots, None
    # Distinguish "attribute absent" (req schema lacks slot_kind) from
    # "attribute present but None". The latter would be a client bug
    # we want to flag in logs rather than swallow silently — but
    # ``AnswerRequest`` rejects None at Pydantic validation before this
    # helper sees the request, so this guard is defense-in-depth only.
    if not hasattr(req, "slot_kind") or not hasattr(req, "value"):
        return slots, None
    slot_kind = req.slot_kind
    raw_value = req.value
    if slot_kind is None or raw_value is None:
        return slots, None
    slot_name = slot_kind.value if hasattr(slot_kind, "value") else str(slot_kind)
    if slot_name not in _PERSISTABLE_SLOT_NAMES:
        return slots, None
    payload = _slot_payload(slot_name, raw_value)
    if payload is None:
        return slots, None
    delta = SlotDeltaV2(kind=slot_name, data=payload)
    new_slots = slots.apply(delta)

    # FR-007 DAG invalidation: when the user re-edits an anchor slot
    # (e.g., re-picks city), any filled downstream slot that depended on
    # it MUST be null-ed out. Slice 218-3 covered anchors {age, city,
    # occupation} are all hangouts_personalized predecessors. Hangouts is
    # slice-218-4 territory so in practice the invalidated list is empty
    # for slice-218-3 sessions, but we wire it now so slice-218-4 lands
    # the FR-007 surface for free + FE R2 callback receives the list.
    new_slots, invalidated = new_slots.invalidate_dependents(slot_name)

    # Merge new slot into JSONB slots payload (preserve any other v2
    # state under `onboarding_profile.slots`). Apply invalidations as
    # explicit None overrides so the persisted JSONB shape matches the
    # in-memory ``new_slots``.
    raw_slots = profile.get("slots")
    existing_slots: dict[str, Any] = raw_slots if isinstance(raw_slots, dict) else {}
    merged_slots: dict[str, Any] = {**existing_slots, slot_name: payload}
    for name in invalidated:
        merged_slots.pop(name, None)
    # Always emit `invalidated` (possibly empty) so the JSONB key is
    # overwritten every turn that persists. FR-007 semantics: the field
    # describes invalidations from THIS turn only — a stale list from a
    # prior turn must not leak through. The merge-write `{**existing,
    # **updates}` in update_onboarding_profile then guarantees a fresh
    # value lands.
    updates: dict[str, Any] = {"slots": merged_slots, "invalidated": invalidated}
    return new_slots, updates


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
# Tracked: GH #581 (eviction post-launch). Block before Cloud Run
# min-instances > 0 OR before launch. Eviction options:
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

    # Slice 218-3: apply prior submission (if any) BEFORE the router
    # picks the next target. Persist atomically so that a partial-turn
    # failure leaves user state consistent and the same submit-replay
    # advances correctly. NOTE: ``IdempotencyStore.put`` at the parent
    # route layer caches the eventual envelope under the turn_id, so a
    # client retry that already persisted the slot lands the cached
    # envelope without re-running this branch — no double-write risk.
    new_slots, profile_updates = _apply_prior_submission(req, slots, profile)
    if profile_updates is not None:
        repo = UserRepository(session)
        await repo.update_onboarding_profile(
            user_id=user.id,
            profile_updates=profile_updates,
        )
        slots = new_slots
        # Reflect the merged slots locally for the router; the JSONB
        # already has them via update_onboarding_profile above.
        profile = {**profile, **profile_updates}

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
        # Hydrate v2 JSONB message list → Pydantic AI ModelMessage list
        # (GH #582). Required for Phase-2 free-bouncing in slice 218-6;
        # also improves Phase-1 context continuity within a slot exchange.
        # Per ADR-009 Hard Rule §6: official multi-turn primitive.
        messages_raw = profile.get("messages") if profile else None
        message_history = hydrate_v2_message_history(
            messages_raw if isinstance(messages_raw, list) else None
        )
        if message_history:
            result = await agent.run("", deps=deps, message_history=message_history)
        else:
            result = await agent.run("", deps=deps)
    except Exception as exc:  # noqa: BLE001 — intentional R12 catch-all
        # Derive a stable session_id from the user's real identity so
        # the client's `/retry` POST scopes the retry-count bucket
        # against a per-user stable key (NOT `deps.conversation_id`,
        # which has `default_factory=uuid4` and is freshly minted on
        # every V2Deps construction). For Spec 218 the onboarding
        # session is 1:1 with the user (a user has one v2 session at
        # a time per sticky-flag R11), so `user.id` is the durable
        # session identifier across retries.
        raise V2DecoratorFailure(
            error_code="v2_decorator_failure",
            session_id=user.id,
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

    Invariant: ``session_id == user_id`` per plan R11 (sticky-flag,
    1:1 user:onboarding-session). Mismatched pairs (e.g., spoofed
    request body) reject with 400 — the auth-derived ``user_id`` is
    authoritative; the body-supplied ``session_id`` must match.
    """
    if session_id != user_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "session_id must equal auth-derived user_id "
                "(plan R11 sticky-flag invariant: 1:1 user:session)."
            ),
        )

    # Idempotency replay path — checked BEFORE budget accounting so
    # network-layer replays of the same (session_id, retry_token) pair
    # do not burn budget. Only cache-miss (actual new retry running the
    # agent) consumes the 3-retry cap.
    idem = IdempotencyStore(session)
    # Synthesize an RFC-4122-valid v5 UUID from (session_id, retry_token)
    # for the cache key. `uuid5` is SHA-1-based deterministic, uses the
    # full token keyspace (no truncation collisions), and properly
    # encodes version + variant bits per RFC 4122 — safer than wrapping
    # a raw SHA-256 prefix in `UUID(bytes=...)` (which leaves variant
    # bits arbitrary). Scoping by session_id prevents cross-session
    # token reuse from sharing cache rows.
    cache_key_turn = uuid.uuid5(
        uuid.NAMESPACE_URL, f"v2-retry|{session_id}|{retry_token}"
    )
    cached = await idem.get(user_id, cache_key_turn)
    if cached is not None:
        cached_body, _status = cached
        return cached_body

    # Cache miss → consume budget atomically BEFORE running the agent.
    # Increment-first-then-compare is race-free on Cloud Run's single
    # event loop; two concurrent cache-miss POSTs both observe their
    # own post-increment count, so the 3-cap holds. (For a future
    # Redis-backed counter this becomes `INCR` + `if >LIMIT: DECR`.)
    new_count = _increment_retry_count(session_id)
    if new_count > _RETRY_BUDGET_HARD_LIMIT:
        raise RetryBudgetExhausted(session_id=session_id)

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
    except V2DecoratorFailure as failure:
        # R12 envelope on decorator agent failure during retry. Without
        # this catch, the inner handle_v2_answer's V2DecoratorFailure
        # would propagate as a raw FastAPI 500, breaking the contract
        # that says retries get the same structured error shape as the
        # parent /answer path. FE retry-handler relies on this envelope
        # to distinguish recoverable transient failures from terminal
        # 503 budget exhaustion.
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": failure.error_code,
                "session_id": str(failure.session_id),
                "retry_url": failure.retry_url,
            },
        ) from failure


__all__ = [
    "RetryBudgetExhausted",
    "V2DecoratorFailure",
    "V2RetryRequest",
    "get_retry_count",
    "handle_v2_answer",
    "handle_v2_retry",
    "router",
]
