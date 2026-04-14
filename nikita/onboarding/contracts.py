"""Contract types for Spec 213 onboarding backend (PR 213-1).

Standalone Pydantic request/response types for the portal onboarding v2 API.

CONSTRAINT: This module MUST NOT import from nikita.onboarding.models,
nikita.db.*, or nikita.engine.constants. It is a frozen contract surface
shared with Spec 214 (portal wizard). Any field addition requires an ADR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared type aliases
# ---------------------------------------------------------------------------

PipelineReadyState = Literal["pending", "ready", "degraded", "failed"]
"""Pipeline readiness state (string Literal for JSON serialization simplicity).

Intentionally NOT an enum so serialization is trivial and consumers can
do simple string comparison without importing enum members.
"""


# ---------------------------------------------------------------------------
# BackstoryOption
# ---------------------------------------------------------------------------


class BackstoryOption(BaseModel):
    """One backstory scenario offered to the user.

    Mirrors BackstoryScenario dataclass at nikita/services/backstory_generator.py:29.
    id is deterministic: sha256(cache_key:index)[:12] — stable across cache hits.
    """

    id: str = Field(description="Opaque ID, stable per (cache_key, index)")
    venue: str = Field(description="Where the meeting happened")
    context: str = Field(description="Setting / vibe in 2-3 sentences")
    the_moment: str = Field(description="The catalyst moment")
    unresolved_hook: str = Field(description="One-liner Nikita can reference in first message")
    tone: Literal["romantic", "intellectual", "chaotic"] = Field(
        description="Emotional tone of the backstory scenario"
    )


# ---------------------------------------------------------------------------
# OnboardingV2ProfileRequest / Response
# ---------------------------------------------------------------------------


class OnboardingV2ProfileRequest(BaseModel):
    """Portal onboarding profile submission (v2).

    Extends current PortalProfileRequest with name/age/occupation/wizard_step.
    Maps to UserOnboardingProfile via handoff.py facade.
    """

    location_city: str = Field(min_length=2, max_length=100)
    social_scene: Literal["techno", "art", "food", "cocktails", "nature"]
    drug_tolerance: int = Field(ge=1, le=5)
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


class OnboardingV2ProfileResponse(BaseModel):
    """Response from POST /onboarding/profile.

    Note: chosen_option is ALWAYS None from Spec 213 endpoints.
    Spec 214 owns the backstory-selection endpoint that populates it.
    """

    user_id: UUID
    pipeline_state: PipelineReadyState
    backstory_options: list[BackstoryOption]
    chosen_option: BackstoryOption | None = None
    poll_endpoint: str = Field(description="Absolute path to /pipeline-ready/{user_id}")
    poll_interval_seconds: float = Field(description="Polling interval in seconds")
    poll_max_wait_seconds: float = Field(description="Max portal wait for pipeline readiness")


# ---------------------------------------------------------------------------
# PipelineReadyResponse (FR-2 + FR-2a extension)
# ---------------------------------------------------------------------------


class PipelineReadyResponse(BaseModel):
    """Response from GET /pipeline-ready/{user_id}.

    FR-2a fields (venue_research_status, backstory_available) default to
    conservative values when JSONB keys are absent — keeps the read path
    as a single-SELECT NFR-1 path (p99 ≤200ms).
    """

    state: PipelineReadyState
    message: str | None = None
    """Optional user-facing explanation, present on degraded/failed states."""
    checked_at: datetime
    """ISO-8601 timestamp of the check, for monitoring/debugging."""

    # FR-2a: pipeline sub-state fields (default to safe values when JSONB key absent)
    venue_research_status: Literal["pending", "complete", "failed", "cache_hit"] = "pending"
    """Venue research progress. Defaults to 'pending' if JSONB key missing."""
    backstory_available: bool = False
    """True once scenarios have been persisted to backstory_cache. Defaults False."""


# ---------------------------------------------------------------------------
# BackstoryPreviewRequest / Response (FR-4a)
# ---------------------------------------------------------------------------


class BackstoryPreviewRequest(BaseModel):
    """Input to POST /onboarding/preview-backstory.

    Called by portal wizard at Step 8 (dossier reveal) BEFORE final profile submit.
    darkness_level here matches UserOnboardingProfile.darkness_level.
    OnboardingV2ProfileRequest uses drug_tolerance for legacy-ORM compat;
    backend maps drug_tolerance → darkness_level when recomputing cache_key.
    """

    city: str = Field(min_length=2, max_length=100)
    social_scene: Literal["techno", "art", "food", "cocktails", "nature"]
    darkness_level: int = Field(ge=1, le=5)
    life_stage: Literal["tech", "finance", "creative", "student", "entrepreneur", "other"] | None = None
    interest: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=18, le=99)
    # SPEC-INTENTIONAL ASYMMETRY: the preview endpoint (this schema) is
    # deliberately LOOSER than OnboardingV2ProfileRequest (which requires
    # min_length=1). Spec 213 §FR-4a L167 declares only ``max_length=100``
    # here. Rationale: the preview path is exploratory — an empty-string
    # occupation buckets to ``"other"`` in compute_backstory_cache_key and
    # produces a usable preview; only the final POST /profile needs the
    # stricter constraint. Any change to add min_length requires a spec
    # update and ADR before modifying this line.
    occupation: str | None = Field(default=None, max_length=100)


class BackstoryPreviewResponse(BaseModel):
    """Response from POST /onboarding/preview-backstory.

    scenarios is empty on degraded path (service timeout or error).
    cache_key is informational only — backend recomputes on final submit.
    """

    scenarios: list[BackstoryOption]
    venues_used: list[str]
    """Venue names incorporated into scenarios (for wizard UI)."""
    cache_key: str
    """Opaque cache key for debugging/observability (NOT echoed back on submit)."""
    degraded: bool
    """True if backstory service failed; scenarios will be empty or generic."""


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Error response matching existing FastAPI shape at onboarding.py:140."""

    detail: str
