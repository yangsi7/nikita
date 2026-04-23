"""Portal onboarding API routes — Spec 213 PR 213-3/4 (FR-13, FR-5, FR-9).

New route file decomposed from onboarding.py (FR-13: route file decomposition).
Owns the portal-facing endpoints:
  - POST  /preview-backstory      (FR-4a)
  - GET   /pipeline-ready/{id}    (FR-5, FR-2a — PR 213-4, D1)
  - PATCH /profile                (FR-9 — PR 213-4, D2)

NO prefix= on router — prefix belongs to include_router() in main.py.
Follows existing onboarding.py:43 pattern.

PII policy (SC-6 / NFR-3): name, age, occupation, phone values MUST NOT appear
in any structured log. Allowed: user_id (UUID), boolean flags, enum values.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_ai.exceptions import (
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.agents.onboarding.control_selection import (
    ControlSelection,
    TextControl,
)
from nikita.agents.onboarding.conversation_agent import (
    CACHE_SETTINGS,
    ConverseDeps,
    TurnOutput,
    get_conversation_agent,
)
from nikita.agents.onboarding.conversation_persistence import (
    append_conversation_turn,
)
from nikita.agents.onboarding.state import FinalForm, WizardSlots
from nikita.agents.onboarding.state_reconstruction import build_state_from_conversation
from nikita.agents.onboarding.converse_contracts import (
    ConverseRequest,
    ConverseResponse,
    RateLimitResponse,
)
from nikita.agents.onboarding.message_history import hydrate_message_history
from nikita.agents.onboarding.state import SlotDelta
from nikita.agents.onboarding.validators import (
    FALLBACK_REPLY,
    sanitize_user_input,
    validate_reply,
)
from nikita.api.dependencies.auth import (
    AuthenticatedUser,
    get_authenticated_user,
    get_current_user_id,
)
from nikita.api.middleware.rate_limit import (
    choice_rate_limit,
    converse_rate_limit,
    pipeline_ready_rate_limit,
)
from nikita.api.middleware.rate_limit import preview_rate_limit as _preview_rate_limit
from nikita.db.database import get_async_session
from nikita.onboarding.contracts import (
    BackstoryChoiceRequest,
    BackstoryPreviewRequest,
    BackstoryPreviewResponse,
    OnboardingV2ProfileRequest,
    OnboardingV2ProfileResponse,
    PipelineReadyResponse,
)
from nikita.onboarding.idempotency import IdempotencyStore
from nikita.onboarding.spend_ledger import (
    ESTIMATED_TURN_COST_USD,
    LLMSpendLedger,
    compute_turn_cost,
)
from nikita.onboarding.tuning import (
    CONFIDENCE_CONFIRMATION_THRESHOLD,
    CONVERSE_429_RETRY_AFTER_SEC,
    CONVERSE_COLD_WARMUP_WINDOW_SEC,
    CONVERSE_DAILY_LLM_CAP_USD,
    CONVERSE_TIMEOUT_MS_COLD,
    CONVERSE_TIMEOUT_MS_WARM,
    PIPELINE_GATE_MAX_WAIT_S,
    PIPELINE_GATE_POLL_INTERVAL_S,
)
from nikita.services.portal_onboarding import PortalOnboardingFacade

# UserRepository imported locally inside handler bodies — ensures the preview
# endpoint cannot write to JSONB even if accidentally wired to (test assertion
# in test_stateless_no_jsonb_write verifies UserRepository is not a module-level name).

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Portal Onboarding"])


# GH #378 — process-uptime tracker for cold/warm timeout selection.
# Captured at module import time; the first ~30s of process life uses the
# larger CONVERSE_TIMEOUT_MS_COLD budget to absorb Cloud Run cold-start +
# LLM warmup latency. After the warmup window expires we tighten to
# CONVERSE_TIMEOUT_MS_WARM (8s) — empirically sufficient for all warm
# /converse calls observed in Walk P (2026-04-21).
_PROCESS_START_MONOTONIC: float = time.monotonic()


def get_converse_timeout_ms(now: float | None = None) -> int:
    """Return the appropriate /converse agent.run timeout in milliseconds.

    GH #378: Cloud Run scale-to-zero adds 5-15s startup; LLM warmup adds
    more. The first 30s of process life gets the cold-start budget; after
    that the instance is fully warm and we apply the tighter warm budget.

    Args:
        now: Optional monotonic clock override (seconds). When provided,
            treats ``now`` as the "current" reading instead of calling
            ``time.monotonic()``. DI-friendly; tests can pass a specific
            float without mutating module state.
    """
    current = now if now is not None else time.monotonic()
    uptime_sec = current - _PROCESS_START_MONOTONIC
    if uptime_sec < CONVERSE_COLD_WARMUP_WINDOW_SEC:
        return CONVERSE_TIMEOUT_MS_COLD
    return CONVERSE_TIMEOUT_MS_WARM


# ---------------------------------------------------------------------------
# PATCH-specific request model (all fields optional for partial update)
# ---------------------------------------------------------------------------


class OnboardingV2ProfilePatchRequest(BaseModel):
    """Partial-update body for PATCH /onboarding/profile.

    All fields are optional — only set fields are written to JSONB via jsonb_set
    (AC-6.1: preserves untouched keys). This is the PATCH-specific variant of
    OnboardingV2ProfileRequest where required fields become optional.

    Frozen contract OnboardingV2ProfileRequest (in contracts.py) is NOT modified
    because it is shared with Spec 214 and frozen per spec FR-2 constraints.
    """

    location_city: str | None = Field(default=None, min_length=2, max_length=100)
    social_scene: Literal["techno", "art", "food", "cocktails", "nature"] | None = None
    drug_tolerance: int | None = Field(default=None, ge=1, le=5)
    life_stage: Literal["tech", "finance", "creative", "student", "entrepreneur", "other"] | None = None
    interest: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, min_length=8, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=18, le=99)
    occupation: str | None = Field(default=None, min_length=1, max_length=100)
    wizard_step: int | None = Field(
        default=None,
        ge=1,
        le=11,
        description="Last completed wizard step for resume detection",
    )


@router.post(
    "/preview-backstory",
    response_model=BackstoryPreviewResponse,
    summary="Preview backstory scenarios (Spec 213 FR-4a)",
    description="""
    Generate backstory scenario previews before final profile submission.

    Called by the portal wizard at Step 8 (dossier reveal) BEFORE the user
    completes the final profile POST. Returns up to 3 backstory scenarios.

    Cache coherence: if the same profile inputs are submitted in the final
    POST /profile, the backend recomputes the same cache_key and short-circuits
    — no duplicate Claude call.

    Rate limited to 5 req/min per user (FR-4a.1). Returns 429 on exceeded.
    """,
)
async def preview_backstory(
    request: BackstoryPreviewRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    _: None = Depends(_preview_rate_limit),
) -> BackstoryPreviewResponse:
    """Generate backstory previews for the portal dossier wizard step.

    Stateless: does NOT write to users.onboarding_profile JSONB.
    Backstory cache is written so the final submission can reuse results.

    Args:
        request: BackstoryPreviewRequest (city, social_scene, darkness_level, ...optional).
        current_user_id: Authenticated user UUID (from JWT).
        session: Async database session (injected by FastAPI DI).
        _: Rate limit dependency (raises 429 if exceeded — return value unused).

    Returns:
        BackstoryPreviewResponse with scenarios, venues_used, cache_key, degraded.
    """
    logger.info(
        "portal_preview.request user_id=%s",
        current_user_id,
    )
    facade = PortalOnboardingFacade()
    response = await facade.generate_preview(current_user_id, request, session)
    logger.info(
        "portal_preview.response user_id=%s degraded=%s scenario_count=%d",
        current_user_id,
        response.degraded,
        len(response.scenarios),
    )
    return response


# ---------------------------------------------------------------------------
# D1: GET /pipeline-ready/{user_id}  (US-2, FR-5, FR-2a)
# ---------------------------------------------------------------------------


@router.get(
    "/pipeline-ready/{user_id}",
    response_model=PipelineReadyResponse,
    summary="Poll pipeline readiness for a user (Spec 213 FR-5, FR-2a)",
    description="""
    Returns the pipeline readiness state from users.onboarding_profile JSONB.

    AC-2.4: Callers may only poll their own user_id — 403 if mismatched.
    AC-2.5: Response includes FR-2a sub-state fields (venue_research_status,
    backstory_available) with safe defaults when JSONB keys are absent.
    message field is present on degraded/failed states only.
    """,
)
async def get_pipeline_ready(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    _: None = Depends(pipeline_ready_rate_limit),
) -> PipelineReadyResponse:
    """Return pipeline readiness state for the authenticated user.

    Args:
        user_id: Target user UUID (path parameter).
        current_user_id: Authenticated caller UUID (from JWT).
        session: Async database session (injected by FastAPI DI).

    Returns:
        PipelineReadyResponse with state, FR-2a sub-states, and checked_at.

    Raises:
        HTTPException(403): caller user_id != path user_id.
        HTTPException(404): user not found in database.
    """
    # AC-2.4: callers can only poll their own pipeline state
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    from nikita.db.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    profile = user.onboarding_profile or {}

    # Read with safe defaults (FR-2a: conservative when JSONB key absent)
    pipeline_state = profile.get("pipeline_state", "pending")
    venue_research_status = profile.get("venue_research_status", "pending")
    backstory_available = profile.get("backstory_available", False)
    # Spec 214 FR-10.2: wizard_step passthrough (None when absent)
    wizard_step = profile.get("wizard_step")

    # Build optional user-facing message for degraded/failed states only
    message: str | None = None
    if pipeline_state in ("degraded", "failed"):
        message = (
            "Your personalization is taking longer than expected. "
            "Nikita will reach out shortly — no action needed."
        )

    logger.info(
        "portal_pipeline_ready.polled user_id=%s state=%s venue_status=%s backstory=%s wizard_step=%s",
        user_id,
        pipeline_state,
        venue_research_status,
        backstory_available,
        wizard_step,
    )

    return PipelineReadyResponse(
        state=pipeline_state,
        venue_research_status=venue_research_status,
        backstory_available=backstory_available,
        checked_at=datetime.now(UTC),
        message=message,
        wizard_step=wizard_step,
    )


# ---------------------------------------------------------------------------
# D2: PATCH /profile  (US-6, FR-9)
# ---------------------------------------------------------------------------


@router.patch(
    "/profile",
    response_model=OnboardingV2ProfileResponse,
    summary="Partial-update onboarding profile (Spec 213 FR-9)",
    description="""
    Update one or more fields in users.onboarding_profile JSONB via
    jsonb_set (AC-6.1: preserves untouched keys).

    FR-14: If pipeline_state is missing OR 'failed', schedules a fresh
    _trigger_portal_handoff background task (user_id + drug_tolerance only,
    no session passed).

    Returns OnboardingV2ProfileResponse with current pipeline_state and
    poll endpoint for the caller to begin polling.
    """,
)
async def patch_profile(
    body: OnboardingV2ProfilePatchRequest,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> OnboardingV2ProfileResponse:
    """Partial-update the authenticated user's onboarding profile.

    Each field in the request body is written via update_onboarding_profile_key
    (jsonb_set) — unset fields are NOT written, preserving JSONB keys set by
    other write paths (AC-6.1 JSONB merge semantics).

    If pipeline_state is absent or 'failed', reschedules the portal handoff
    background task (FR-14 session isolation: task opens its own session).

    Args:
        body: OnboardingV2ProfileRequest fields (all optional except those
              required by OnboardingV2ProfileRequest schema).
        background_tasks: FastAPI BackgroundTasks for handoff scheduling.
        current_user_id: Authenticated user UUID (from JWT).
        session: Async database session (injected by FastAPI DI).

    Returns:
        OnboardingV2ProfileResponse with current pipeline_state + poll metadata.
    """
    from nikita.api.routes.onboarding import _trigger_portal_handoff
    from nikita.db.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)

    # AC-6.2: write each set field individually via jsonb_set
    for key, value in body.model_dump(exclude_unset=True).items():
        await user_repo.update_onboarding_profile_key(current_user_id, key, value)

    # Read current pipeline_state for handoff decision + response
    user = await user_repo.get(current_user_id)
    profile = (user.onboarding_profile or {}) if user is not None else {}
    pipeline_state = profile.get("pipeline_state")

    # FR-14: retrigger when pipeline_state missing OR failed
    if pipeline_state is None or pipeline_state == "failed":
        # Determine drug_tolerance for handoff: use body if provided, else JSONB
        drug_tolerance: int = (
            body.drug_tolerance
            if body.drug_tolerance is not None
            else int(profile.get("darkness_level", 3))
        )
        logger.info(
            "portal_patch_profile.handoff_scheduled user_id=%s pipeline_state=%s",
            current_user_id,
            pipeline_state,
        )
        background_tasks.add_task(
            _trigger_portal_handoff,
            user_id=current_user_id,
            drug_tolerance=drug_tolerance,
        )

    # Normalise missing pipeline_state to "pending" for response
    response_state = pipeline_state if pipeline_state is not None else "pending"

    logger.info(
        "portal_patch_profile.done user_id=%s pipeline_state=%s",
        current_user_id,
        response_state,
    )

    return OnboardingV2ProfileResponse(
        user_id=current_user_id,
        pipeline_state=response_state,
        backstory_options=[],
        chosen_option=None,
        poll_endpoint=f"/api/v1/onboarding/pipeline-ready/{current_user_id}",
        poll_interval_seconds=PIPELINE_GATE_POLL_INTERVAL_S,
        poll_max_wait_seconds=PIPELINE_GATE_MAX_WAIT_S,
    )


# ---------------------------------------------------------------------------
# Spec 214 PR 214-D: PUT /profile/chosen-option  (FR-10.1)
# ---------------------------------------------------------------------------


@router.put(
    "/profile/chosen-option",
    response_model=OnboardingV2ProfileResponse,
    summary="Record chosen backstory scenario (Spec 214 FR-10.1)",
    description="""
    Validate + persist the authenticated user's backstory selection.

    Idempotent: PUT with the same (user_id, chosen_option_id, cache_key)
    returns 200 and the same snapshot on every call.

    Ownership is enforced by recomputing cache_key from the user's
    onboarding_profile JSONB (backstory_cache has no user_id column).
    Stale profile changes between preview and PUT → 403.

    Rate limited to 10 req/min per user (FR-10.1). 429 responses include
    Retry-After: 60 header (RFC 6585).
    """,
)
async def put_chosen_option(
    body: BackstoryChoiceRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    _: None = Depends(choice_rate_limit),
) -> OnboardingV2ProfileResponse:
    """Record the authenticated user's backstory selection.

    Raises:
        HTTPException(403): cache_key mismatch (stale/cross-user attempt).
        HTTPException(404): no backstory_cache row for cache_key.
        HTTPException(409): chosen_option_id not in the stored scenarios.
        HTTPException(429): rate limit exceeded (Retry-After: 60).
    """
    from nikita.db.repositories.user_repository import UserRepository

    facade = PortalOnboardingFacade()
    chosen_option = await facade.set_chosen_option(
        user_id=current_user_id,
        chosen_option_id=body.chosen_option_id,
        cache_key=body.cache_key,
        session=session,
    )

    # Refresh user to pick up pipeline_state after the write above.
    user_repo = UserRepository(session)
    user = await user_repo.get(current_user_id)
    profile = (user.onboarding_profile or {}) if user is not None else {}
    pipeline_state = profile.get("pipeline_state", "pending")

    logger.info(
        "portal_put_chosen_option.done user_id=%s pipeline_state=%s",
        current_user_id,
        pipeline_state,
    )

    # 214-D: selection endpoint never re-emits backstory_options (per the
    # OnboardingV2ProfileResponse contract — options are only emitted by the
    # POST /profile + GET /pipeline-ready endpoints during the wizard's
    # backstory-reveal step). Empty list signals "selection complete".
    return OnboardingV2ProfileResponse(
        user_id=current_user_id,
        pipeline_state=pipeline_state,
        backstory_options=[],
        chosen_option=chosen_option,
        poll_endpoint=f"/api/v1/onboarding/pipeline-ready/{current_user_id}",
        poll_interval_seconds=PIPELINE_GATE_POLL_INTERVAL_S,
        poll_max_wait_seconds=PIPELINE_GATE_MAX_WAIT_S,
    )


# ===========================================================================
# Spec 214 FR-11d — POST /onboarding/converse
# ===========================================================================


def _normalize_user_input(user_input: str | ControlSelection) -> str:
    """Collapse ``ControlSelection`` or raw string into a single string.

    Chip/slider/toggle/cards → their ``value`` (string-coerced). Text →
    the raw string. The agent always sees a plain string; the portal
    carries the ``kind`` metadata separately.
    """
    if isinstance(user_input, str):
        return user_input
    # ControlSelection variants all expose ``.value``; coerce to str.
    return str(user_input.value)


def _fallback_response(
    *,
    progress_pct: int = 0,
    conversation_complete: bool = False,
    latency_ms: int = 0,
    extracted_fields: dict | None = None,
    source: Literal["fallback", "validation_reject"] = "fallback",
    nikita_reply: str | None = None,
) -> ConverseResponse:
    """Build a 200 fallback response used by timeout / validator / authz
    / sanitizer rejection branches (AC-T2.5.6 / 7 / 10).

    QA iter-1 B2/I9: ``source`` widened so the response distinguishes
    timeout/sanitizer/validator failures (``fallback``) from age<18 /
    schema-validation rejections (``validation_reject``). Both still
    return HTTP 200 with an in-character reply.
    """
    return ConverseResponse(
        nikita_reply=nikita_reply or FALLBACK_REPLY,
        extracted_fields=extracted_fields or {},
        confirmation_required=False,
        next_prompt_type="text",
        next_prompt_options=None,
        progress_pct=progress_pct,
        conversation_complete=conversation_complete,
        source=source,
        latency_ms=latency_ms,
    )


def _rate_limit_429_body() -> dict:
    """In-character 429 body (AC-T2.5.4). String intentionally em-dash-free.

    Schema is ``RateLimitResponse`` (B4 QA iter-1) — distinct from
    ``ConverseResponse`` so OpenAPI advertises the correct shape on the
    429 path.
    """
    return RateLimitResponse(
        nikita_reply="easy, tiger. give me a sec.",
        source="fallback",
        retry_after_sec=CONVERSE_429_RETRY_AFTER_SEC,
    ).model_dump(mode="json")


# In-character age<18 rejection (I9 QA iter-1). Plain ASCII punctuation
# only — em-dashes banned in user-facing strings per CLAUDE.md.
# QA iter-2 nitpick: `Final[str]` is idiomatic for single-value string
# constants; `Literal[...]` is for value-constrained type annotations
# elsewhere in the module.
_VALIDATION_REJECT_AGE_REPLY: Final[str] = (
    "we need you to be 18 or older. catch me when you are."
)


def _is_age_under_18_error(errors: list[dict]) -> bool:
    """Decide whether a Pydantic ValidationError is actually an age<18
    rejection vs. some other tool-arg schema failure.

    GH #382 (D2): before this helper, ANY ValidationError from the agent
    mapped to the age-under-18 template, even when the failing constraint
    was phone format / _at_least_one_field / no_extraction.reason literal.
    Walk Q user (age=32) saw the age-18 template on EVERY turn because
    the LLM was tripping a different validator.

    Heuristic: the error is "age<18" iff the first error's `loc` ends
    with ``"age"`` AND the type is ``greater_than_equal``. Any other
    shape is routed to the generic ``FALLBACK_REPLY``.
    """
    if not errors:
        return False
    first = errors[0]
    loc = first.get("loc") or ()
    if not loc:
        return False
    # `loc` may be ("age",) or ("model_name", "age") etc. — check last entry.
    last = loc[-1]
    err_type = first.get("type", "")
    return last == "age" and err_type == "greater_than_equal"


def _summarize_validation_errors(errors: list[dict]) -> dict:
    """PII-safe summary of a Pydantic ValidationError for logging (D3).

    Returns only the structural shape (loc + type) of the FIRST error.
    Omits ``input`` (would leak user-provided values) and ``msg`` (often
    echoes user input).
    """
    if not errors:
        return {"tool": "unknown", "loc": "", "type": ""}
    first = errors[0]
    loc = first.get("loc") or ()
    return {
        "loc": ".".join(str(p) for p in loc),
        "type": first.get("type", ""),
        "err_count": len(errors),
    }


# _form_is_complete removed — use slots_after.is_complete (WizardSlots.is_complete
# @computed_field, single source of truth per agentic-design-patterns.md §2 + Finding 4).


async def _persist_user_turn_best_effort(
    session: AsyncSession,
    user_id: UUID,
    sanitized_input: str,
) -> bool:
    """Best-effort user-turn append on fallback branches (GH #382 D7).

    Walk Q showed that every /converse fallback branch (timeout,
    validation_reject, agent error) was returning a fallback reply
    without persisting the user's turn. Result: the next retry had
    zero history in message_history, so the LLM made the same mistake.

    This helper appends a user turn with no extracted fields to JSONB.
    Any DB error is caught, session rolled back explicitly so a later
    ledger.add_spend call on the same session doesn't cascade into
    ``InFailedSqlTransaction``, and the error is logged. Returns
    ``True`` on success so callers can decide whether to proceed with
    a coupled side-effect (e.g. spend accrual).

    PR #383 QA iter-1 fix: returns bool + explicit rollback so the
    caller can avoid charging spend for a ghost turn if persist fails.
    """
    try:
        await append_conversation_turn(
            session,
            user_id,
            {
                "role": "user",
                "content": sanitized_input,
                "timestamp": datetime.now(UTC).isoformat(),
                "extracted": {},
            },
        )
        return True
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "converse_user_turn_persist_failed user_id=%s exc=%s",
            user_id,
            type(exc).__name__,
        )
        # Rollback is idempotent in SQLAlchemy async (no-op on already-
        # rolled-back / non-active sessions); the inner except guards
        # against transport-level failures on a dead connection.
        try:
            await session.rollback()
        except Exception:  # pragma: no cover — defensive
            pass
        return False


async def _charge_estimated_spend(
    spend_ledger: LLMSpendLedger,
    user_id: UUID,
) -> None:
    """Charge ESTIMATED_TURN_COST_USD on a validator-reject path (GH #382 D8).

    The LLM actually ran and burned tokens before the tool call failed
    Pydantic validation. Skipping spend accrual would let a determined
    caller evade the daily $2 cap by triggering repeated schema
    errors. Defensive: swallow ledger errors so the fallback still
    returns on time.

    PR #383 QA iter-1 nitpick: reuses the in-scope ``spend_ledger``
    rather than instantiating a new one — ledgers are stateless
    wrappers around the session but this is idiomatic.
    """
    try:
        await spend_ledger.add_spend(user_id, ESTIMATED_TURN_COST_USD)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "converse_spend_add_failed user_id=%s exc=%s",
            user_id,
            type(exc).__name__,
        )


class ConversationTurn(BaseModel):
    """Single turn in the onboarding conversation stored in onboarding_profile JSONB."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["nikita", "user"]
    content: str
    timestamp: str
    source: Literal["llm", "fallback", "idempotent", "validation_reject"] | None = None
    extracted: dict | None = None


class ConversationProfileResponse(BaseModel):
    """GH #385 — prior conversation turns for wizard hydration on page reload.

    AC-11d.7: exposes ``link_code``, ``link_expires_at``, and
    ``link_code_expired`` so the wizard can restore a pending Telegram
    deep-link without minting a new code (GET is read-only; minting
    happens in POST /converse on the terminal turn only).
    """

    model_config = ConfigDict(extra="forbid")

    conversation: list[ConversationTurn] = Field(default_factory=list)
    progress_pct: int = Field(default=0, ge=0, le=100)
    elided_extracted: dict = Field(default_factory=dict)
    # AC-11d.7 — read existing active link code row; None if no code yet.
    link_code: str | None = None
    link_expires_at: datetime | None = None
    link_code_expired: bool = False


@router.get(
    "/conversation",
    response_model=ConversationProfileResponse,
    summary="Fetch prior conversation turns for wizard hydration (GH #385)",
    description="""
    Returns the authenticated user's prior onboarding conversation turns so
    the chat wizard can restore state on page reload instead of restarting.

    Returns empty ``conversation`` list for new users (wizard shows the
    hardcoded opener). ``progress_pct`` is computed from committed extracted
    fields; ``elided_extracted`` carries fields committed in prior sessions.
    """,
)
async def get_conversation(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
) -> ConversationProfileResponse:
    """Return prior conversation turns from the user's onboarding profile.

    AC-11d.10: progress_pct is computed from cumulative WizardSlots
    (elided_extracted FIRST, live turns override), not _compute_progress.

    AC-11d.7: reads the active telegram_link_codes row for this user and
    returns link_code / link_expires_at / link_code_expired so the wizard
    can restore a pending deep-link without re-minting. GET is READ-ONLY;
    it MUST NOT call create_link_code.
    """
    from nikita.db.repositories.user_repository import UserRepository  # intentional: module policy line 97-99
    from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository

    repo = UserRepository(session)
    user = await repo.get(current_user.id)
    if user is None:
        return ConversationProfileResponse()

    profile: dict = user.onboarding_profile or {}
    conversation = profile.get("conversation", [])
    elided_extracted = profile.get("elided_extracted", {})

    # AC-11d.10: cumulative reconstruction via WizardSlots
    slots = build_state_from_conversation(profile)
    progress_pct = slots.progress_pct

    # AC-11d.7: read existing active link code row (read-only, never mint here)
    link_code: str | None = None
    link_expires_at: datetime | None = None
    link_code_expired: bool = False
    try:
        link_repo = TelegramLinkRepository(session)
        existing = await link_repo.get_active_for_user(current_user.id)
        if existing is not None:
            link_code = existing.code
            link_expires_at = existing.expires_at
            link_code_expired = existing.expires_at < datetime.now(UTC)
    except Exception:  # pragma: no cover — defensive; link codes are optional
        pass

    return ConversationProfileResponse(
        conversation=conversation,
        progress_pct=progress_pct,
        elided_extracted=elided_extracted,
        link_code=link_code,
        link_expires_at=link_expires_at,
        link_code_expired=link_code_expired,
    )


@router.post(
    "/converse",
    response_model=ConverseResponse,
    summary="Conversational onboarding turn (Spec 214 FR-11d)",
    # B4 QA iter-1: advertise the 429 schema explicitly so the OpenAPI
    # contract no longer claims `ConverseResponse` shape on rate-limit
    # / spend-cap responses.
    responses={429: {"model": RateLimitResponse}},
    description="""
    Stateless single-turn endpoint powering the chat-first onboarding
    wizard. Each call receives the full conversation history + the
    user's latest input; returns Nikita's reply + any structured
    extraction committed this turn + UI hints for the next prompt.

    Identity is derived from the Bearer JWT. Body MUST NOT carry
    ``user_id`` (extra="forbid" at schema level).

    Rate-limited per-user (20 rpm), per-IP (30 rpm), and per-day
    ($2.00 LLM spend cap). Breaches return 429 with in-character body.

    Idempotency: ``Idempotency-Key`` HTTP header OR ``turn_id`` body
    field; HIT within 5 minutes short-circuits and returns the cached
    response verbatim without re-running the agent.
    """,
)
async def converse(
    req: ConverseRequest,
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_async_session),
    _rate_limit: None = Depends(converse_rate_limit),
    idempotency_key_header: str | None = Header(
        default=None, alias="Idempotency-Key"
    ),
) -> ConverseResponse:
    """Handle one conversational onboarding turn."""
    started = time.monotonic()

    # 1. Idempotency short-circuit (AC-T2.5.3).
    turn_id = _resolve_turn_id(idempotency_key_header, req.turn_id)
    idempotency = IdempotencyStore(session)
    if turn_id is not None:
        cached = await idempotency.get(current_user.id, turn_id)
        if cached is not None:
            cached_body, cached_status = cached
            logger.info(
                "converse_idempotency_hit user_id=%s turn_id=%s",
                current_user.id,
                turn_id,
            )
            # B2 QA iter-1: cache HIT now reports `source="idempotent"`
            # so the caller can distinguish a real LLM turn from a
            # short-circuited one. We mutate the cached body in-place
            # before returning; the cached row stays untouched (the
            # next HIT also gets `idempotent`).
            if cached_status == 200 and isinstance(cached_body, dict):
                cached_body = {**cached_body, "source": "idempotent"}
            return JSONResponse(
                status_code=cached_status, content=cached_body
            )  # type: ignore[return-value]

    # 2. Daily LLM spend cap (AC-T2.5.4).
    spend_ledger = LLMSpendLedger(session)
    today_spend = await spend_ledger.get_today(current_user.id)
    if today_spend >= Decimal(str(CONVERSE_DAILY_LLM_CAP_USD)):
        logger.warning(
            "converse_spend_cap_exceeded user_id=%s spend_usd=%s",
            current_user.id,
            today_spend,
        )
        return JSONResponse(
            status_code=429,
            content=_rate_limit_429_body(),
            headers={"Retry-After": str(CONVERSE_429_RETRY_AFTER_SEC)},
        )  # type: ignore[return-value]

    # 3. Normalize + sanitize input (AC-T2.5.5).
    raw_input = _normalize_user_input(req.user_input)
    sanitized, rejected = sanitize_user_input(raw_input)
    if rejected:
        logger.warning(
            "converse_input_reject user_id=%s input_len=%d",
            current_user.id,
            len(raw_input),
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))

    # 4. Run the agent under cold/warm timeout (AC-T2.5.6 + GH #378).
    #    GH #402/#403 (Walk W 2026-04-23): consolidated TurnOutput.
    #    result.output is a TurnOutput with delta (SlotDelta|None) + reply (str).
    #    No tool-call sidecar — deps.extracted removed (AC-11d.5 path a).
    #    GH #382 (D1): pass hydrated message_history so the LLM sees the
    #    full wizard conversation, not just the latest user message. Before
    #    this fix, every turn was cold; the LLM guessed wrong structured-output
    #    shapes and retry loops exhausted on the same ValidationError.
    # Pre-run slot reconstruction (T11, PR-B).
    # Build cumulative WizardSlots from the conversation history the client
    # sent — each Turn carries its prior extracted dict. This gives the
    # dynamic-instructions callable (render_dynamic_instructions) the
    # missing-slot list it needs BEFORE agent.run begins.
    _pre_profile: dict = {
        "conversation": [t.model_dump() for t in req.conversation_history]
    }
    _pre_state = build_state_from_conversation(_pre_profile)

    deps = ConverseDeps(
        user_id=current_user.id, locale=req.locale, state=_pre_state
    )
    agent = get_conversation_agent()
    timeout_ms = get_converse_timeout_ms()

    message_history = hydrate_message_history(req.conversation_history)
    # Pydantic AI skips re-running system_prompt when message_history is
    # non-empty; pass None (omit kwarg via default) on a fresh session so
    # the prompt is emitted per pydantic-ai docs.
    run_kwargs: dict = {
        "deps": deps,
        "model_settings": CACHE_SETTINGS,
    }
    if message_history:
        run_kwargs["message_history"] = message_history

    # B3 QA iter-1: split exception handlers — TimeoutError is the
    # success-path bound; everything else is an unexpected failure.
    # Validation errors raised inside tool calls (e.g. age<18
    # IdentityExtraction) bubble out of the agent run; we map those to
    # an in-character `validation_reject` response (I9 QA iter-1).
    try:
        result = await asyncio.wait_for(
            agent.run(sanitized, **run_kwargs),
            timeout=timeout_ms / 1000,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "converse_agent_timeout user_id=%s timeout_ms=%d cold=%s",
            current_user.id,
            timeout_ms,
            timeout_ms == CONVERSE_TIMEOUT_MS_COLD,
        )
        # D7: persist user turn even on timeout so the next retry has
        # the attempted message in its message_history context.
        # Bool return is intentionally discarded here — no coupled side
        # effect follows on the timeout branch (spend ledger not charged
        # because we can't confirm the LLM actually ran to completion).
        _ = await _persist_user_turn_best_effort(
            session, current_user.id, sanitized
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))
    except ValidationError as exc:
        # I9 QA iter-1: surface age<18 (and other schema rejections) as
        # a 200 in-character message rather than a 422 leak.
        # GH #382 (D2, D3, D7, D8):
        #   D2: only return the age-18 template when the error is actually
        #       on the age field. Other schema rejections get FALLBACK_REPLY.
        #   D3: log includes loc + type (PII-safe) so triage doesn't need
        #       to reproduce locally.
        #   D7: persist user turn even on reject so retries have context.
        #   D8: charge estimated turn cost — the LLM ran and burned tokens.
        errors = exc.errors()
        is_age_under_18 = _is_age_under_18_error(errors)
        summary = _summarize_validation_errors(errors)
        logger.warning(
            "converse_validation_reject user_id=%s loc=%s type=%s err_count=%d is_age_under_18=%s",
            current_user.id,
            summary["loc"],
            summary["type"],
            summary["err_count"],
            is_age_under_18,
        )
        # PR #383 QA iter-1 fix: persist BEFORE charging spend so a
        # failed persist doesn't leave the user paying for a ghost turn.
        # The helper handles rollback internally if the append fails.
        persisted = await _persist_user_turn_best_effort(
            session, current_user.id, sanitized
        )
        # D8: charge spend even though the run ended in ValidationError —
        # the LLM actually ran; skipping would let callers evade the cap.
        # Only charge if the user-turn was actually persisted (persisted
        # transaction state is safe) — otherwise we'd be charging for an
        # effectively-lost turn.
        if persisted:
            await _charge_estimated_spend(spend_ledger, current_user.id)
        return _fallback_response(
            latency_ms=_elapsed_ms(started),
            source="validation_reject",
            nikita_reply=(
                _VALIDATION_REJECT_AGE_REPLY if is_age_under_18 else FALLBACK_REPLY
            ),
        )
    except (
        UnexpectedModelBehavior,
        UsageLimitExceeded,
        UserError,
    ) as exc:
        # I1 QA iter-1: keep traceback for unexpected agent failures.
        logger.exception(
            "converse_agent_failed user_id=%s exc=%s",
            current_user.id,
            type(exc).__name__,
        )
        # D7: persist attempted user turn for continuity. Bool discarded
        # intentionally — no coupled side effect on this terminal branch.
        _ = await _persist_user_turn_best_effort(
            session, current_user.id, sanitized
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))
    except Exception as exc:
        # Catch-all preserves traceback (I1 QA iter-1) and ensures the
        # endpoint never 500s on a transient model/network blip. Bool
        # discarded intentionally — terminal branch, no coupled spend.
        logger.exception(
            "converse_agent_unexpected user_id=%s exc=%s",
            current_user.id,
            type(exc).__name__,
        )
        _ = await _persist_user_turn_best_effort(
            session, current_user.id, sanitized
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))

    # 5. Unpack TurnOutput — consolidated output (GH #402/#403, AC-11d.5).
    #    result.output is always a TurnOutput instance (never raw str).
    #    delta carries the extracted SlotDelta (or None on clarification turns).
    #    reply carries the conversational response.
    turn_output: TurnOutput | None = getattr(result, "output", None)
    if not isinstance(turn_output, TurnOutput):
        logger.warning(
            "converse_unexpected_output_type user_id=%s type=%s",
            current_user.id,
            type(turn_output).__name__,
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))

    extracted_delta: SlotDelta | None = turn_output.delta
    if extracted_delta is not None:
        extracted_fields: dict = {"kind": extracted_delta.kind, **extracted_delta.data}
    else:
        extracted_fields = {}

    # 6. Source the reply text from TurnOutput.reply (GH #402/#403).
    #    Empty/None → fall through to fallback with source="fallback".
    raw_reply = turn_output.reply
    if not isinstance(raw_reply, str) or not raw_reply.strip():
        logger.warning(
            "converse_empty_reply user_id=%s",
            current_user.id,
        )
        return _fallback_response(
            latency_ms=_elapsed_ms(started),
            extracted_fields=extracted_fields,
        )

    reply_text = raw_reply.strip()

    # 7. Reply validation (AC-T2.5.7 / T2.5.10).
    ok, reason = validate_reply(reply_text)
    if not ok:
        logger.warning(
            "converse_reply_reject user_id=%s reason=%s",
            current_user.id,
            reason,
        )
        return _fallback_response(
            latency_ms=_elapsed_ms(started),
            extracted_fields=extracted_fields,
        )

    # 8. Successful turn — accumulate spend + persist idempotency.
    #    I6 QA iter-1: prefer real RunUsage when the model wrapper
    #    surfaces it; fall back to ESTIMATED_TURN_COST_USD otherwise.
    usage_obj = None
    usage_attr = getattr(result, "usage", None)
    if callable(usage_attr):
        try:
            usage_obj = usage_attr()
        except Exception:
            usage_obj = None
    elif usage_attr is not None:
        usage_obj = usage_attr
    actual_cost = compute_turn_cost(usage_obj)
    if actual_cost <= 0:
        actual_cost = ESTIMATED_TURN_COST_USD
    await spend_ledger.add_spend(current_user.id, actual_cost)

    # AC-T2.8.1/2/3: persist both turns to users.onboarding_profile.conversation
    # inside the same transaction as the idempotency cache + spend ledger so
    # the trio is atomic. Skipped on cache HIT (returned earlier) and 429
    # rate-limit branches (returned earlier) — QA iter-2 I1 fix.
    turn_ts = datetime.now(UTC).isoformat()
    await append_conversation_turn(
        session,
        current_user.id,
        {
            "role": "user",
            "content": sanitized,
            "timestamp": turn_ts,
            "extracted": extracted_fields,
        },
    )
    await append_conversation_turn(
        session,
        current_user.id,
        {
            "role": "nikita",
            "content": reply_text,
            "timestamp": turn_ts,
            "source": "llm",
        },
    )

    # AC-11d.2/AC-11d.3: cumulative completion gate via FinalForm.model_validate.
    # Reads the user's full onboarding_profile after both turns are persisted
    # and reconstructs cumulative WizardSlots — elided_extracted FIRST, live
    # turns in order. This replaces the per-turn _compute_progress() anti-pattern
    # (Walk V incident, 2026-04-22; agentic-design-patterns.md Hard Rule §2).
    #
    # progress_pct is a @computed_field of cumulative WizardSlots — monotonic
    # by construction.  conversation_complete is the FinalForm gate result —
    # NEVER a hardcoded boolean.
    #
    # AC-11d.7/AC-11d.8: on the terminal turn (when conversation_complete is True),
    # mint a TelegramLinkCode so the frontend can render the deep-link without
    # a second API call. The code is idempotent: create_link_code deletes any
    # existing code first. GET /conversation reads the code; POST /converse mints.
    from nikita.db.repositories.telegram_link_repository import TelegramLinkRepository  # local import per module policy
    from sqlalchemy import select as _select_post  # avoid shadowing top-level 'select'

    # Re-load profile after the two append_conversation_turn calls above.
    from nikita.db.repositories.user_repository import UserRepository as _UR  # local per policy
    _repo = _UR(session)
    _user_after = await _repo.get(current_user.id)
    _profile_after = _user_after.onboarding_profile if _user_after else {}

    slots_after = build_state_from_conversation(_profile_after or {})

    # AC-11d.4: regex phone fallback — defense in depth against LLM tool-selection bias.
    # Applied AFTER cumulative slot reconstruction, BEFORE the completion gate.
    from nikita.agents.onboarding.regex_fallback import regex_phone_fallback  # local per module policy
    _user_input_text = req.user_input if isinstance(req.user_input, str) else None
    _fallback_delta = regex_phone_fallback(_user_input_text, slots_after)
    if _fallback_delta is not None:
        slots_after = slots_after.apply(_fallback_delta)
        logger.info("converse_regex_phone_fallback_applied user_id=%s", current_user.id)

    # GH #407 fix: write-through identity slots to user_profiles structured columns.
    # Triggered on the CURRENT TURN's delta only (not cumulative state) so the
    # upsert fires exactly once per identity extraction, not on every subsequent
    # turn after identity is set.  Only non-None fields are written so partial
    # extractions (name-only) do not overwrite existing age/occupation with None.
    # Applied AFTER slot reconstruction + fallback, BEFORE the completion gate.
    if extracted_delta is not None and extracted_delta.kind == "identity":
        from sqlalchemy.exc import SQLAlchemyError  # local per module policy

        from nikita.db.repositories.profile_repository import ProfileRepository  # local per module policy
        profile_repo = ProfileRepository(session)
        try:
            await profile_repo.upsert_identity_slots(
                user_id=current_user.id,
                name=extracted_delta.data.get("name"),
                age=extracted_delta.data.get("age"),
                occupation=extracted_delta.data.get("occupation"),
            )
        except SQLAlchemyError:  # pragma: no cover — defensive; slot still committed to JSONB
            # Narrow to DB errors so programmer errors (TypeError, AttributeError)
            # still fail loudly in dev/test. logger.exception captures stack trace.
            logger.exception(
                "converse_identity_upsert_failed user_id=%s",
                current_user.id,
            )

    progress_pct = slots_after.progress_pct

    conversation_complete = slots_after.is_complete

    # Mint link code on terminal turn only (AC-11d.7).
    link_code_str: str | None = None
    link_expires_at_val: datetime | None = None
    if conversation_complete:
        try:
            _link_repo = TelegramLinkRepository(session)
            _link = await _link_repo.create_link_code(current_user.id)
            link_code_str = _link.code
            link_expires_at_val = _link.expires_at
        except Exception:  # pragma: no cover — defensive; wizard still completes
            logger.warning(
                "converse_link_mint_failed user_id=%s",
                current_user.id,
            )

    response = ConverseResponse(
        nikita_reply=reply_text,
        extracted_fields=extracted_fields,
        confirmation_required=_needs_confirmation(extracted_delta),
        next_prompt_type="text",
        next_prompt_options=None,
        progress_pct=progress_pct,
        conversation_complete=conversation_complete,
        source="llm",
        latency_ms=_elapsed_ms(started),
        link_code=link_code_str,
        link_expires_at=link_expires_at_val,
    )

    if turn_id is not None:
        await idempotency.put(
            user_id=current_user.id,
            turn_id=turn_id,
            response_body=response.model_dump(mode="json"),
            status_code=200,
        )

    return response


def _resolve_turn_id(header_val, body_val):
    """Prefer the ``Idempotency-Key`` header; fall back to ``turn_id`` body.

    If both present AND differ → raise 409 per decision D3.
    """
    if header_val and body_val:
        try:
            header_uuid = UUID(header_val)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Idempotency-Key must be a UUID"
            )
        if header_uuid != body_val:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key header does not match body turn_id",
            )
        return body_val
    if body_val is not None:
        return body_val
    if header_val:
        try:
            return UUID(header_val)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Idempotency-Key must be a UUID"
            )
    return None


def _needs_confirmation(delta: SlotDelta | None) -> bool:
    """AC-11d.3 / CONFIDENCE_CONFIRMATION_THRESHOLD gate.

    GH #402/#403: delta is now a SlotDelta (or None). Confidence lives in
    delta.data["confidence"] for all extraction schemas.
    """
    if delta is None:
        return False
    confidence = delta.data.get("confidence", 1.0)
    return float(confidence) < CONFIDENCE_CONFIRMATION_THRESHOLD


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)

