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
from pydantic import BaseModel, Field, ValidationError
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
    get_conversation_agent,
    pick_primary_extraction,
)
from nikita.agents.onboarding.conversation_persistence import (
    append_conversation_turn,
)
from nikita.agents.onboarding.converse_contracts import (
    ConverseRequest,
    ConverseResponse,
    RateLimitResponse,
)
from nikita.agents.onboarding.extraction_schemas import NoExtraction
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
import time as _time
_PROCESS_START_MONOTONIC: float = _time.monotonic()


def get_converse_timeout_ms() -> int:
    """Return the appropriate /converse agent.run timeout in milliseconds.

    GH #378: Cloud Run scale-to-zero adds 5-15s startup; LLM warmup adds
    more. The first 30s of process life gets the cold-start budget; after
    that the instance is fully warm and we apply the tighter warm budget.
    """
    uptime_sec = _time.monotonic() - _PROCESS_START_MONOTONIC
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
    #    B1 QA iter-1: agent now returns plain text in `result.output`;
    #    structured extractions are accumulated in `deps.extracted` by
    #    the tool-call sidecar.
    deps = ConverseDeps(user_id=current_user.id, locale=req.locale)
    agent = get_conversation_agent()
    timeout_ms = get_converse_timeout_ms()

    # B3 QA iter-1: split exception handlers — TimeoutError is the
    # success-path bound; everything else is an unexpected failure.
    # Validation errors raised inside tool calls (e.g. age<18
    # IdentityExtraction) bubble out of the agent run; we map those to
    # an in-character `validation_reject` response (I9 QA iter-1).
    try:
        result = await asyncio.wait_for(
            agent.run(
                sanitized,
                deps=deps,
                model_settings=CACHE_SETTINGS,
            ),
            timeout=timeout_ms / 1000,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "converse_agent_timeout user_id=%s timeout_ms=%d cold=%s",
            current_user.id,
            timeout_ms,
            timeout_ms == CONVERSE_TIMEOUT_MS_COLD,
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))
    except ValidationError as exc:
        # I9 QA iter-1: surface age<18 (and other schema rejections) as
        # a 200 in-character message rather than a 422 leak.
        logger.warning(
            "converse_validation_reject user_id=%s err_count=%d",
            current_user.id,
            len(exc.errors()),
        )
        return _fallback_response(
            latency_ms=_elapsed_ms(started),
            source="validation_reject",
            nikita_reply=_VALIDATION_REJECT_AGE_REPLY,
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
        return _fallback_response(latency_ms=_elapsed_ms(started))
    except Exception as exc:
        # Catch-all preserves traceback (I1 QA iter-1) and ensures the
        # endpoint never 500s on a transient model/network blip.
        logger.exception(
            "converse_agent_unexpected user_id=%s exc=%s",
            current_user.id,
            type(exc).__name__,
        )
        return _fallback_response(latency_ms=_elapsed_ms(started))

    # 5. Pick the primary extraction from the deps-scoped sidecar
    #    (B1 QA iter-1). Multi-tool turns collapse to the highest-
    #    priority extraction per AC-T2.5.9.
    primary_extraction = pick_primary_extraction(deps.extracted)
    if primary_extraction is None or isinstance(primary_extraction, NoExtraction):
        extracted_fields: dict = {}
    else:
        extracted_fields = primary_extraction.model_dump()

    # 6. Source the reply text from `result.output` (B1/B5 QA iter-1).
    #    Empty/None → fall through to fallback with source="fallback".
    raw_reply: object = getattr(result, "output", None)
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

    response = ConverseResponse(
        nikita_reply=reply_text,
        extracted_fields=extracted_fields,
        confirmation_required=_needs_confirmation(primary_extraction),
        next_prompt_type="text",
        next_prompt_options=None,
        progress_pct=_compute_progress(extracted_fields),
        conversation_complete=False,
        source="llm",
        latency_ms=_elapsed_ms(started),
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


def _needs_confirmation(extraction) -> bool:
    """AC-11d.3 / CONFIDENCE_CONFIRMATION_THRESHOLD gate."""
    if extraction is None or isinstance(extraction, NoExtraction):
        return False
    return extraction.confidence < CONFIDENCE_CONFIRMATION_THRESHOLD


def _compute_progress(extracted_fields: dict) -> int:
    """Rough progress percentage based on committed profile fields."""
    if not extracted_fields:
        return 0
    # Six target fields ultimately — coarse mapping for Phase A.
    kind = extracted_fields.get("kind")
    progress_map = {
        "location": 20,
        "scene": 40,
        "darkness": 50,
        "identity": 70,
        "backstory": 85,
        "phone": 100,
        "no_extraction": 0,
    }
    return progress_map.get(kind, 0)


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)

