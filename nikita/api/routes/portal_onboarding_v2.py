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

import datetime as _dt
import logging
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.onboarding.v2.backstory_commit import (
    BackstoryGenerationError,
    generate_v2_backstory,
)
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
    CompleteAsk,
    TextShortAsk,
)
from nikita.agents.onboarding.v2.research_agent import (
    V2ResearchDeps,
    get_research_agent,
    phase_2_gate,
)
from nikita.agents.onboarding.v2.router import pick_next_target
from nikita.agents.onboarding.v2.session_helper import (
    migration_or_init_v2_session,
)
from nikita.agents.onboarding.v2.state import (
    PHASE_2_MAX_TURNS,
    Phase,
    SlotDeltaV2,
    SlotKindV2,
    WizardSlotsV2,
    WizardStateV2,
)
from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
)
from nikita.agents.onboarding.v2.message_history import hydrate_v2_message_history
from nikita.api.middleware.rate_limit import answer_rate_limit
from nikita.db.database import get_async_session
from nikita.db.repositories.profile_repository import ProfileRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository
from nikita.config.settings import get_settings
from nikita.life_simulation.simulator import LifeSimulator
from nikita.memory.supabase_memory import SupabaseMemory
from nikita.onboarding.idempotency import IdempotencyStore

logger = logging.getLogger(__name__)


_AGENT_BOOTSTRAP_PROMPT: str = "Begin."
"""Non-empty user prompt for the first turn of a v2 agent run (GH #604).

On turn 1 there is no ``message_history``. Calling ``agent.run("")`` with
no history makes Pydantic AI send an empty ``messages`` array to the
model, which Anthropic rejects with 400 "messages: at least one message
is required" — the v2 wizard 500s for every new user on portal entry.

The v2 decorator + research agents are instruction-driven (dynamic
``instructions`` carries the full directive; the user prompt is a no-op
trigger), so a constant non-empty bootstrap prompt satisfies the API
contract without changing agent behaviour. Only the empty-history branch
needs it — turn 2+ already has a non-empty ``messages`` array hydrated
from ``message_history``."""


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


def _build_decorator_failure(
    exc: Exception, session_id: UUID
) -> V2DecoratorFailure:
    """Wrap a decorator/research agent exception in the R12 envelope type.

    GH #602: the originating exception (e.g. an Anthropic 400 "credit
    balance is too low") was invisible in prod logs because the wrap
    happened silently. Emit a server-side ERROR log carrying ``str(exc)``
    BEFORE returning the envelope so the failure is greppable in Cloud
    Run logs without needing a live walk to surface it.
    """
    logger.error(
        "v2_decorator_failure session_id=%s detail=%s", session_id, exc
    )
    return V2DecoratorFailure(
        error_code="v2_decorator_failure",
        session_id=session_id,
        retry_url="/api/v1/converse/onboarding/retry",
        detail=str(exc),
    )


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
# Phase-2 helpers (slice 218-6)
# ---------------------------------------------------------------------------


def _force_phase2_complete_envelope(
    state: WizardStateV2,
    backstory_preview: str | None = None,
) -> CompleteAsk:
    """Return a terminal CompleteAsk for forced Phase-2 completion.

    Used when MAX_TURNS is reached (the agent tried to continue) and
    in the wrong-output recovery path. Backstory preview is optional
    at this layer — `_run_phase2_complete` fills it after generation.
    """
    return CompleteAsk(
        next_route="/dashboard",
        backstory_preview=backstory_preview,
    )


async def _run_phase2_complete(
    state: WizardStateV2,
    profile: dict[str, Any],
    user: Any,
    *,
    repo: Any,
    session: Any = None,
    backstory_preview: str | None = None,
) -> CompleteAsk:
    """Commit Phase-2 completion: generate backstory, persist phase=complete,
    run completion side-effects, and return CompleteAsk envelope.

    Called both for normal completion (agent signalled done after MIN_TURNS)
    and forced completion (MAX_TURNS reached).

    Side-effects mirror v1 ``save_portal_profile`` (GH #611, GH #612):
    1. Create ``user_profiles`` row from v2 slots.
    2. Flip ``onboarding_status`` → 'completed'.
    3. Call ``activate_game()``.
    4. Seed vices from darkness_level slot.
    All guarded by an idempotency check (status already 'completed' OR
    profile row already exists → skip).
    """
    # Extract Phase-2 message history for backstory context
    messages_raw = profile.get("messages")
    phase2_messages: list[dict[str, Any]] = (
        messages_raw if isinstance(messages_raw, list) else []
    )

    # Generate backstory preview (non-blocking: failure logs but does NOT
    # raise — wizard must complete even if LLM backstory generation fails).
    if backstory_preview is None:
        try:
            backstory_preview = await generate_v2_backstory(
                state.slots, phase2_messages
            )
        except BackstoryGenerationError:
            # Non-fatal: celebrate without preview rather than block
            backstory_preview = None

    # Persist phase transition + final turn count + backstory
    await repo.update_onboarding_profile(
        user_id=user.id,
        profile_updates={
            "phase": Phase.complete.value,
            "phase_2_turn_count": state.phase_2_turn_count,
            "completion": {
                "backstory_preview": backstory_preview,
            },
        },
    )

    # ------------------------------------------------------------------
    # Completion side-effects (GH #611, GH #612)
    # Mirror v1 save_portal_profile chain. session must always be provided
    # by callers — omitting it is a programming error that would silently
    # skip #611/#612 fixes. Both current call sites pass it.
    # NOTE: users.onboarding_profile JSONB (phase=complete, backstory, etc.)
    # is written by update_onboarding_profile above — side-effects below
    # do NOT need to repeat that write.
    # ------------------------------------------------------------------
    assert session is not None, (
        "_run_phase2_complete: session must be provided — omitting it "
        "silently skips create_profile / activate_game / seed_vices (GH #611, #612)"
    )
    await _run_completion_side_effects(
        user=user,
        state=state,
        user_repo=repo,
        session=session,
    )

    return CompleteAsk(
        next_route="/dashboard",
        backstory_preview=backstory_preview,
    )


def _scale_darkness_to_drug_tolerance(darkness_level: int) -> int:
    """Scale v2 darkness_level (0-10) → drug_tolerance (1-5).

    Formula: raw = (darkness_level + 1) // 2, then clamp to [1, 5].
    Bucket mapping (verified by formula, not docstring):
      0     → 1
      1-2   → 1
      3-4   → 2
      5-6   → 3
      7-8   → 4
      9-10  → 5
    Satisfies DB CHECK constraint ``drug_tolerance BETWEEN 1 AND 5``.
    """
    raw = (darkness_level + 1) // 2  # 0→0, 1→1, 2→1, 3→2, 4→2, 5→3, 6→3, 7→4, 8→4, 9→5, 10→5
    return max(1, min(5, raw))


async def _run_completion_side_effects(
    *,
    user: Any,
    state: WizardStateV2,
    user_repo: Any,
    session: Any,
) -> None:
    """Run v1-equivalent completion side-effects for v2 wizard.

    Idempotent: no-op if status is already 'completed' OR profile row exists.
    """
    user_id = user.id
    slots = state.slots

    # Idempotency guard — check both status and profile existence
    if getattr(user, "onboarding_status", None) == "completed":
        return
    profile_repo = ProfileRepository(session)
    existing_profile = await profile_repo.get_by_user_id(user_id)
    if existing_profile is not None:
        return

    # --- Extract slot values -------------------------------------------------
    city_slot = slots.city or {}
    location_city: str | None = city_slot.get("city")

    display_name_slot = slots.display_name or {}
    name: str | None = display_name_slot.get("display_name")

    age_slot = slots.age or {}
    age: int | None = age_slot.get("age")

    occupation_slot = slots.occupation or {}
    occupation: str | None = occupation_slot.get("occupation")

    hangouts_slot = slots.hangouts_personalized or {}
    hangouts_list = hangouts_slot.get("hangouts_personalized") or []
    social_scene: str | None = hangouts_list[0] if hangouts_list else None

    hobbies_slot = slots.primary_hobbies or {}
    hobbies_list = hobbies_slot.get("primary_hobbies") or []
    primary_interest: str | None = hobbies_list[0] if hobbies_list else None

    darkness_slot = slots.darkness_level or {}
    raw_darkness: int = darkness_slot.get("darkness_level", 0)
    drug_tolerance: int = _scale_darkness_to_drug_tolerance(raw_darkness)

    # --- 1. Create user_profiles row ----------------------------------------
    # life_stage: intentionally NULL — v2 has no life_stage slot. Column is
    # nullable (profile.py:83). Voice-opening selector handles None gracefully
    # (openings/selector.py:95-98). No downstream code requires it non-NULL.
    # location_country: not collected in v2 either — nullable, pass-through NULL.
    await profile_repo.create_profile(
        user_id=user_id,
        location_city=location_city,
        social_scene=social_scene,
        drug_tolerance=drug_tolerance,
        primary_interest=primary_interest,
        name=name,
        age=age,
        occupation=occupation,
    )

    # --- 2. Flip onboarding_status → 'completed' ----------------------------
    await user_repo.update_onboarding_status(user_id, "completed")

    # --- 3. Activate game ----------------------------------------------------
    await user_repo.activate_game(user_id)

    # --- 4. Seed vices (non-fatal) -------------------------------------------
    try:
        from nikita.engine.vice.seeder import seed_vices_from_profile  # noqa: PLC0415

        vice_repo = VicePreferenceRepository(session)
        await seed_vices_from_profile(
            user_id=user_id,
            profile={"darkness_level": drug_tolerance},
            vice_repo=vice_repo,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "seed_vices_from_profile failed for user_id=%s (non-fatal)", user_id
        )

    # --- 5. Seed SupabaseMemory with onboarding facts (H2, non-fatal) --------
    # New users start with empty memory_facts. Without seeding here, the agent
    # has NO facts to recall on turn 1 — it cannot reference the user's name,
    # city, hobbies, or the backstory_preview generated in Phase 2.
    try:
        settings = get_settings()
        if not settings.openai_api_key:
            logger.warning(
                "onboarding_memory_seeding skipped: openai_api_key not configured user_id=%s",
                user_id,
            )
        else:
            geek_out_on_slot = getattr(slots, "geek_out_on", {}) or {}
            geek_out_on_val: str | None = geek_out_on_slot.get("geek_out_on") if isinstance(geek_out_on_slot, dict) else None
            saturday_morning_slot = getattr(slots, "saturday_morning", {}) or {}
            saturday_morning_val: str | None = saturday_morning_slot.get("saturday_morning") if isinstance(saturday_morning_slot, dict) else None

            # Read backstory_preview from JSONB (written by generate_v2_backstory)
            op = getattr(user, "onboarding_profile", None)
            backstory_preview_val: str | None = None
            if isinstance(op, dict):
                backstory_preview_val = op.get("completion", {}).get("backstory_preview")

            memory = SupabaseMemory(
                session=session,
                user_id=user_id,
                openai_api_key=settings.openai_api_key,
            )
            facts_to_seed: list[tuple[str, str]] = []  # (fact, graph_type)
            if name:
                facts_to_seed.append((f"User's name is {name}", "user"))
            if age and location_city:
                facts_to_seed.append((f"User is {age} years old and lives in {location_city}", "user"))
            elif location_city:
                facts_to_seed.append((f"User lives in {location_city}", "user"))
            if occupation:
                facts_to_seed.append((f"User works as {occupation}", "user"))
            if hobbies_list:
                facts_to_seed.append((f"User's hobbies include {', '.join(str(h) for h in hobbies_list)}", "user"))
            if geek_out_on_val:
                facts_to_seed.append((f"User geeks out on: {geek_out_on_val}", "user"))
            if saturday_morning_val:
                facts_to_seed.append((f"User's Saturday morning vibe: {saturday_morning_val}", "user"))
            if backstory_preview_val:
                facts_to_seed.append((f"[first impression] {backstory_preview_val}", "relationship"))

            for fact_text, graph_type in facts_to_seed:
                await memory.add_fact(
                    fact=fact_text,
                    graph_type=graph_type,
                    source="onboarding",
                    confidence=1.0,
                )
            logger.info(
                "onboarding_memory_seeded user_id=%s facts=%d", user_id, len(facts_to_seed)
            )
    except Exception:  # noqa: BLE001
        logger.exception(
            "onboarding_memory_seeding failed for user_id=%s (non-fatal)", user_id
        )

    # --- 6. Initialize LifeSimulator entities (H3, non-fatal) ----------------
    # Without this call, new users have no life-sim entities → no daily events
    # → the world feels dead. initialize_user() is idempotent (returns False if
    # already initialized). Must be called once at wizard completion.
    try:
        simulator = LifeSimulator()
        await simulator.initialize_user(user_id)
        logger.info("life_sim_initialized user_id=%s", user_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "life_sim_initialize_user failed for user_id=%s (non-fatal)", user_id
        )


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
        # Phase 1 complete — run Phase-2 open-bounce (slice 218-6).
        # Reconstruct the full WizardStateV2 from the persisted profile so
        # phase_2_gate has turn_count + phase fields available.
        phase_str = profile.get("phase", Phase.phase2.value)
        try:
            current_phase = Phase(phase_str)
        except ValueError:
            current_phase = Phase.phase2
        turn_count = int(profile.get("phase_2_turn_count", 0))

        wizard_state = WizardStateV2(
            slots=slots,
            phase=current_phase,
            phase_2_turn_count=turn_count,
            phase_2_started_at=profile.get("phase_2_started_at"),
        )

        # Check if already complete (idempotent re-entry after completion)
        if current_phase == Phase.complete:
            backstory_preview = profile.get("completion", {}).get(
                "backstory_preview"
            )
            return CompleteAsk(
                next_route="/dashboard",
                backstory_preview=backstory_preview,
            )

        # FR-008: max-ceiling forced complete?
        complete, forced = phase_2_gate(wizard_state, agent_signals_done=False)
        if complete and forced:
            return await _run_phase2_complete(
                wizard_state, profile, user, repo=UserRepository(session), session=session
            )

        # Stamp phase_2_started_at atomically with phase transition
        # (FR-002: set in same update as final Phase-1 slot acceptance).
        if wizard_state.phase_2_started_at is None:
            started_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
            repo_p2 = UserRepository(session)
            await repo_p2.update_onboarding_profile(
                user_id=user.id,
                profile_updates={
                    "phase": Phase.phase2.value,
                    "phase_2_started_at": started_at,
                    "phase_2_turn_count": 0,
                },
            )
            wizard_state = wizard_state.model_copy(
                update={
                    "phase": Phase.phase2,
                    "phase_2_started_at": started_at,
                }
            )
            profile = {
                **profile,
                "phase": Phase.phase2.value,
                "phase_2_started_at": started_at,
                "phase_2_turn_count": 0,
            }

        # Run Phase-2 research agent turn
        research_deps = V2ResearchDeps(
            user_id=str(user.id),
            state=wizard_state,
        )
        research_agent = get_research_agent()
        try:
            messages_raw = profile.get("messages")
            message_history = hydrate_v2_message_history(
                messages_raw if isinstance(messages_raw, list) else None
            )
            # Use explicit non-None+non-empty check to keep contract
            # stable regardless of whether hydrator returns [] or None
            # (QA iter-3 fragility flag).
            if message_history is not None and len(message_history) > 0:
                research_result = await research_agent.run(
                    "", deps=research_deps, message_history=message_history
                )
            else:
                # GH #604: non-empty bootstrap prompt — empty-history
                # turn would send an empty `messages` array => 400.
                research_result = await research_agent.run(
                    _AGENT_BOOTSTRAP_PROMPT, deps=research_deps
                )
        except Exception as exc:  # noqa: BLE001
            raise _build_decorator_failure(exc, user.id) from exc

        agent_output = research_result.output

        # Determine if agent signalled completion
        agent_signals_done = isinstance(agent_output, CompleteAsk)

        # Increment turn count for this turn
        new_turn_count = wizard_state.phase_2_turn_count + 1
        updated_state = wizard_state.model_copy(
            update={"phase_2_turn_count": new_turn_count}
        )

        complete, forced = phase_2_gate(updated_state, agent_signals_done=agent_signals_done)

        if complete:
            return await _run_phase2_complete(
                updated_state,
                profile,
                user,
                repo=UserRepository(session),
                session=session,
                backstory_preview=(
                    agent_output.backstory_preview
                    if isinstance(agent_output, CompleteAsk)
                    else None
                ),
            )

        # Persist incremented turn count and return the follow-up str as a
        # TextShortAsk envelope so the FE can render it uniformly.
        repo_turn = UserRepository(session)
        await repo_turn.update_onboarding_profile(
            user_id=user.id,
            profile_updates={"phase_2_turn_count": new_turn_count},
        )

        follow_up_text = (
            str(agent_output)
            if not isinstance(agent_output, CompleteAsk)
            else "What else would you like to share?"
        )
        return TextShortAsk(
            component="text_short",
            handler="v2",
            slot="phase2_followup",
            prompt=follow_up_text,
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
        messages_raw = profile.get("messages")
        message_history = hydrate_v2_message_history(
            messages_raw if isinstance(messages_raw, list) else None
        )
        # Explicit non-None+non-empty (see QA iter-3 fragility flag at the
        # Phase-2 call site; same contract applies here).
        if message_history is not None and len(message_history) > 0:
            result = await agent.run("", deps=deps, message_history=message_history)
        else:
            # GH #604: first turn has no message_history — pass a
            # non-empty bootstrap prompt so Pydantic AI sends a valid
            # (non-empty) `messages` array to the model.
            result = await agent.run(_AGENT_BOOTSTRAP_PROMPT, deps=deps)
    except Exception as exc:  # noqa: BLE001 — intentional R12 catch-all
        # Derive a stable session_id from the user's real identity so
        # the client's `/retry` POST scopes the retry-count bucket
        # against a per-user stable key (NOT `deps.conversation_id`,
        # which has `default_factory=uuid4` and is freshly minted on
        # every V2Deps construction). For Spec 218 the onboarding
        # session is 1:1 with the user (a user has one v2 session at
        # a time per sticky-flag R11), so `user.id` is the durable
        # session identifier across retries.
        raise _build_decorator_failure(exc, user.id) from exc

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


# ---------------------------------------------------------------------------
# Slice 218-7: Phone-demo consent + end-call endpoints (FR-009/FR-010/FR-011)
# ---------------------------------------------------------------------------


class PhoneDemoConsentRequest(BaseModel):
    """Request body for POST /onboarding/phone-demo/consent (FR-009)."""

    phone_e164: str = Field(
        ...,
        description="E.164-formatted phone number collected in Phase-1 phone slot",
        examples=["+14155552671"],
        pattern=r"^\+[1-9]\d{7,14}$",
    )


class PhoneDemoConsentResponse(BaseModel):
    """Response body for POST /onboarding/phone-demo/consent."""

    status: str
    provider_call_id: str | None = None
    message: str


@router.post(
    "/onboarding/phone-demo/consent",
    response_model=PhoneDemoConsentResponse,
    summary="Record phone-demo opt-in consent and dispatch outbound call (FR-009)",
    status_code=200,
)
async def phone_demo_consent_endpoint(
    req: PhoneDemoConsentRequest,
    http_request: Request,
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
) -> PhoneDemoConsentResponse:
    """
    Record server-side consent and dispatch the phone-demo outbound call.

    Idempotency: DB UNIQUE constraint on user_id enforces FR-011 lifetime cap.
    Duplicate calls return HTTP 409.
    """
    from nikita.agents.onboarding.v2.phone_demo import record_consent_and_dispatch

    client_ip = http_request.client.host if http_request.client else None
    user_agent_header = http_request.headers.get("user-agent")
    result = await record_consent_and_dispatch(
        session=session,
        user_id=current_user.id,
        phone_e164=req.phone_e164,
        client_ip=client_ip,
        user_agent=user_agent_header,
    )
    if not result.get("inserted"):
        raise HTTPException(
            status_code=409,
            detail={"error": "phone_demo_already_used", "message": "Phone demo already used for this account"},
        )
    return PhoneDemoConsentResponse(
        status=result["status"],
        provider_call_id=result.get("provider_call_id"),
        message="Call dispatched",
    )


class PhoneDemoEndCallResponse(BaseModel):
    """Response body for POST /onboarding/phone-demo/end-call."""

    success: bool
    message: str


@router.post(
    "/onboarding/phone-demo/end-call",
    response_model=PhoneDemoEndCallResponse,
    summary="Abort phone-demo call (FR-010 End early button)",
    status_code=200,
)
async def phone_demo_end_call_endpoint(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
) -> PhoneDemoEndCallResponse:
    """
    Gracefully abort the user's in-flight phone-demo call.

    Used by the FR-010 "End early" button (post 5s minimum delay).
    """
    from nikita.agents.onboarding.v2.phone_demo import end_call

    result = await end_call(
        session=session,
        user_id=current_user.id,
    )
    return PhoneDemoEndCallResponse(
        success=result["success"],
        message=result["message"],
    )


# ---------------------------------------------------------------------------
# Route — POST /api/v1/onboarding/answer  (PR-218-8: v2-only, v1 deleted)
# ---------------------------------------------------------------------------


class V2AnswerRequest(BaseModel):
    """Request body for POST /api/v1/onboarding/answer (v2-only).

    PR-218-8: replaces the v1 ``AnswerRequest`` (deleted with
    ``portal_onboarding.py``). This schema is the minimal surface needed
    by ``handle_v2_answer`` + ``_apply_prior_submission``.
    """

    slot_kind: SlotKindV2 | None = None
    """The slot the client is submitting a value for. ``None`` for Phase-2
    open-bounce turns (no deterministic slot, just a free-text exchange)."""

    value: Any = None
    """Raw slot value from the client. Parsed and validated by
    ``_slot_payload`` inside ``_apply_prior_submission``."""

    turn_id: uuid.UUID | None = None
    """Optional client-generated idempotency key. Duplicate POSTs with the
    same ``turn_id`` return the cached envelope without re-running the agent."""


@router.post(
    "/onboarding/answer",
    summary="v2 stateful onboarding answer turn (PR-218-8)",
    responses={429: {"description": "Rate limit exceeded"}},
    description=(
        "Processes one v2 wizard turn. Applies any prior submission via "
        "``_apply_prior_submission``, runs the decorator agent, and returns "
        "a discriminated AskUnion envelope. Supports idempotency via "
        "``turn_id``; repeat calls within 5 minutes return the cached envelope."
    ),
)
async def answer_v2(
    req: V2AnswerRequest,
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
    _rate_limit: None = Depends(answer_rate_limit),
) -> dict[str, Any]:
    """v2-only answer handler (portal_onboarding.py deleted in PR-218-8).

    Idempotency: if ``req.turn_id`` is provided and a cached response
    exists for ``(user.id, turn_id)``, returns it verbatim. Otherwise
    runs ``handle_v2_answer``, caches the result, and returns it.
    """
    from fastapi.responses import JSONResponse  # noqa: PLC0415

    # Idempotency short-circuit.
    if req.turn_id is not None:
        idempotency = IdempotencyStore(session)
        cached = await idempotency.get(current_user.id, req.turn_id)
        if cached is not None:
            cached_body, _status = cached
            return JSONResponse(status_code=200, content=cached_body)

    # Load the user row (handle_v2_answer expects a user ORM object).
    repo = UserRepository(session)
    user = await repo.get(current_user.id)
    if user is None:
        from fastapi import HTTPException  # noqa: PLC0415
        raise HTTPException(status_code=404, detail="User not found")

    try:
        envelope = await handle_v2_answer(req=req, user=user, session=session)
    except V2DecoratorFailure as failure:
        return JSONResponse(
            status_code=500,
            content={
                "error_code": failure.error_code,
                "session_id": str(failure.session_id),
                "retry_url": failure.retry_url,
            },
        )

    body = envelope.model_dump(mode="json")

    # Cache for idempotency replay.
    if req.turn_id is not None:
        idempotency = IdempotencyStore(session)
        await idempotency.put(
            user_id=current_user.id,
            turn_id=req.turn_id,
            response_body=body,
            status_code=200,
        )

    return JSONResponse(status_code=200, content=body)


__all__ = [
    "PhoneDemoConsentRequest",
    "PhoneDemoConsentResponse",
    "PhoneDemoEndCallResponse",
    "RetryBudgetExhausted",
    "V2AnswerRequest",
    "V2DecoratorFailure",
    "V2RetryRequest",
    "_force_phase2_complete_envelope",
    "_run_phase2_complete",
    "answer_v2",
    "get_retry_count",
    "handle_v2_answer",
    "handle_v2_retry",
    "phone_demo_consent_endpoint",
    "phone_demo_end_call_endpoint",
    "router",
]
