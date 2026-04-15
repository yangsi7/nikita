"""Portal onboarding API routes — Spec 213 PR 213-3 (FR-13).

New route file decomposed from onboarding.py (FR-13: route file decomposition).
Owns the portal-facing endpoints:
  - POST  /preview-backstory  (FR-4a)
  - (PR 213-4 will add: POST /profile, PATCH /profile, GET /pipeline-ready)

NO prefix= on router — prefix belongs to include_router() in main.py.
Follows existing onboarding.py:43 pattern.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.middleware.rate_limit import preview_rate_limit as _preview_rate_limit
from nikita.db.database import get_async_session
from nikita.onboarding.contracts import BackstoryPreviewRequest, BackstoryPreviewResponse
from nikita.services.portal_onboarding import PortalOnboardingFacade

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Portal Onboarding"])


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
