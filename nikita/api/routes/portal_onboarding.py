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

import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.middleware.rate_limit import preview_rate_limit as _preview_rate_limit
from nikita.db.database import get_async_session
from nikita.onboarding.contracts import (
    BackstoryPreviewRequest,
    BackstoryPreviewResponse,
    OnboardingV2ProfileRequest,
    OnboardingV2ProfileResponse,
    PipelineReadyResponse,
)
from nikita.onboarding.tuning import (
    PIPELINE_GATE_MAX_WAIT_S,
    PIPELINE_GATE_POLL_INTERVAL_S,
)
from nikita.services.portal_onboarding import PortalOnboardingFacade

# UserRepository imported locally inside handler bodies — ensures the preview
# endpoint cannot write to JSONB even if accidentally wired to (test assertion
# in test_stateless_no_jsonb_write verifies UserRepository is not a module-level name).

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Portal Onboarding"])


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

    # Build optional user-facing message for degraded/failed states only
    message: str | None = None
    if pipeline_state in ("degraded", "failed"):
        message = (
            "Your personalization is taking longer than expected. "
            "Nikita will reach out shortly — no action needed."
        )

    logger.info(
        "portal_pipeline_ready.polled user_id=%s state=%s venue_status=%s backstory=%s",
        user_id,
        pipeline_state,
        venue_research_status,
        backstory_available,
    )

    return PipelineReadyResponse(
        state=pipeline_state,
        venue_research_status=venue_research_status,
        backstory_available=backstory_available,
        checked_at=datetime.now(UTC),
        message=message,
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
