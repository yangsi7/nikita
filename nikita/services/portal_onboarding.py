"""Portal onboarding facade — Spec 213 PR 213-3 (FR-3, FR-4a).

Thin facade: no business logic. Orchestrates VenueResearchService +
BackstoryGeneratorService with named timeouts, cache coherence, and
graceful degradation.

Session safety: facade NEVER opens its own session. Caller passes session in.
Background tasks MUST open a fresh session inside the task body.

PII policy (FR-7 / NFR-3): name, age, occupation, phone values MUST NOT appear
in any structured log. Allowed: user_id, boolean presence flags, enum values.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import HTTPException

from nikita.db.repositories.backstory_cache_repository import BackstoryCacheRepository
from nikita.db.repositories.profile_repository import VenueCacheRepository
from nikita.onboarding.adapters import ProfileFromOnboardingProfile
from nikita.onboarding.contracts import BackstoryOption, BackstoryPreviewRequest, BackstoryPreviewResponse
from nikita.onboarding.tuning import (
    BACKSTORY_CACHE_TTL_DAYS,
    BACKSTORY_GEN_TIMEOUT_S,
    VENUE_RESEARCH_TIMEOUT_S,
    compute_backstory_cache_key,
)
from nikita.services.backstory_generator import BackstoryGeneratorService, BackstoryScenario
from nikita.services.venue_research import VenueResearchService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scenario → Option converter (FR-3.2)
# ---------------------------------------------------------------------------


def _scenario_to_option(cache_key: str, index: int, s: BackstoryScenario) -> BackstoryOption:
    """Convert backstory_generator dataclass → frozen contract Pydantic model.

    id formula: sha256(cache_key:index)[:12] — deterministic, stable, opaque.
    The id is stable across cache hits so the portal can reference it when
    the user picks (Spec 214 chosen_option write path).

    Args:
        cache_key: Canonical cache key for this profile shape.
        index: Position of the scenario in the generated list (0-based).
        s: BackstoryScenario dataclass from BackstoryGeneratorService.

    Returns:
        BackstoryOption Pydantic model suitable for API response.
    """
    opaque_id = hashlib.sha256(f"{cache_key}:{index}".encode()).hexdigest()[:12]
    valid_tone = s.tone if s.tone in ("romantic", "intellectual", "chaotic") else "chaotic"
    return BackstoryOption(
        id=opaque_id,
        venue=s.venue,
        context=s.context,
        the_moment=s.the_moment,
        unresolved_hook=s.unresolved_hook,
        tone=valid_tone,
    )


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class PortalOnboardingFacade:
    """Thin facade orchestrating venue research + backstory generation.

    Single responsibility: wire services together with timeouts + cache.
    No business logic lives here — each service handles its own domain.

    Instantiated per-request (stateless). Session injected by caller.
    """

    async def process(
        self,
        user_id: UUID,
        profile: object,
        session: "AsyncSession",
    ) -> list[BackstoryOption]:
        """Run venue research + backstory generation for a full profile submission.

        This is the main handoff path called after portal profile is saved.
        Returns list[BackstoryOption] (may be empty on degraded path).

        Cache coherence: reads cache first; writes only on successful generation.
        Cache envelope shape: {"scenarios": [...], "venues_used": [...]}

        Args:
            user_id: User UUID (for logging and adapter).
            profile: Duck-typed profile object. Must expose: city, social_scene,
                     darkness_level, life_stage, interest, age, occupation.
                     UserOnboardingProfile or SimpleNamespace both work.
            session: AsyncSession. Caller manages lifecycle; facade never commits.

        Returns:
            List of BackstoryOption (empty list on any failure path).
        """
        cache_repo = BackstoryCacheRepository(session)
        cache_key = compute_backstory_cache_key(profile)

        # Cache read
        cached_raw = await cache_repo.get(cache_key)
        if cached_raw is not None:
            # FR-7/NFR-3: cache_key contains city (PII-adjacent). Log a short hash only.
            cache_key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:8]
            logger.info(
                "portal_handoff.backstory cache_hit=True user_id=%s cache_key_hash=%s",
                user_id,
                cache_key_hash,
            )
            return self._deserialize_options(cached_raw)

        # Cache miss — run full pipeline with state machine (FR-5.1 / FR-11)
        return await self._bootstrap_pipeline(
            user_id=user_id,
            profile=profile,
            session=session,
        )

    async def generate_preview(
        self,
        user_id: UUID,
        request: BackstoryPreviewRequest,
        session: "AsyncSession",
    ) -> BackstoryPreviewResponse:
        """Generate backstory preview for the portal dossier step (FR-4a).

        Stateless: does NOT write to users.onboarding_profile JSONB.
        Uses the same cache coherence path as process() — cache hits from
        preview calls will be reused by the final POST /profile submission.

        Args:
            user_id: Authenticated user UUID (for adapter + logging).
            request: BackstoryPreviewRequest from portal wizard step 8.
            session: AsyncSession (caller manages lifecycle).

        Returns:
            BackstoryPreviewResponse with scenarios, venues_used, cache_key, degraded.
        """
        # Build duck-typed pseudo_profile from preview request fields
        pseudo_profile = SimpleNamespace(
            city=request.city,
            social_scene=request.social_scene,
            darkness_level=request.darkness_level,
            life_stage=request.life_stage,
            interest=request.interest,
            age=request.age,
            occupation=request.occupation,
        )
        cache_key = compute_backstory_cache_key(pseudo_profile)

        cache_repo = BackstoryCacheRepository(session)

        # Cache hit: envelope has both 'scenarios' and 'venues_used'
        envelope = await cache_repo.get_envelope(cache_key)
        if envelope is not None:
            # FR-7/NFR-3: cache_key contains city (PII-adjacent). Log a short hash only.
            cache_key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:8]
            logger.info(
                "portal_handoff.preview cache_hit=True user_id=%s cache_key_hash=%s",
                user_id,
                cache_key_hash,
            )
            scenario_dicts = envelope["scenarios"]
            venues_used = envelope["venues_used"]
            options = [BackstoryOption.model_validate(d) for d in scenario_dicts]
            return BackstoryPreviewResponse(
                scenarios=options,
                venues_used=venues_used,
                cache_key=cache_key,
                degraded=False,
            )

        # Cache miss — venue research
        venue_cache_repo = VenueCacheRepository(session)
        venue_service = VenueResearchService(venue_cache_repository=venue_cache_repo)
        backstory_service = BackstoryGeneratorService()

        try:
            venue_result = await asyncio.wait_for(
                venue_service.research_venues(request.city, request.social_scene),
                timeout=VENUE_RESEARCH_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "portal_handoff.preview venue_research outcome=timeout user_id=%s",
                user_id,
            )
            return BackstoryPreviewResponse(
                scenarios=[],
                venues_used=[],
                cache_key=cache_key,
                degraded=True,
            )

        venues_list = venue_result.venues
        venue_names = [v.name for v in venues_list]

        # Adapter: pseudo_profile → BackstoryPromptProfile (duck-typed for generator)
        orm_like_profile = ProfileFromOnboardingProfile.from_pydantic(user_id, pseudo_profile)

        try:
            scenarios_result = await asyncio.wait_for(
                backstory_service.generate_scenarios(orm_like_profile, venues_list),
                timeout=BACKSTORY_GEN_TIMEOUT_S,
            )
        except Exception as exc:
            logger.warning(
                "portal_handoff.preview backstory outcome=failure user_id=%s error_class=%s",
                user_id,
                type(exc).__name__,
            )
            return BackstoryPreviewResponse(
                scenarios=[],
                venues_used=venue_names,
                cache_key=cache_key,
                degraded=True,
            )

        options = [
            _scenario_to_option(cache_key, i, s)
            for i, s in enumerate(scenarios_result.scenarios)
        ]

        # Persist envelope to cache — same shape as process() for coherence
        envelope_scenarios = [opt.model_dump(mode="json") for opt in options]
        await cache_repo.set(
            cache_key,
            envelope_scenarios,
            venue_names,
            BACKSTORY_CACHE_TTL_DAYS,
        )

        return BackstoryPreviewResponse(
            scenarios=options,
            venues_used=venue_names,
            cache_key=cache_key,
            degraded=False,
        )

    async def set_chosen_option(
        self,
        user_id: UUID,
        chosen_option_id: str,
        cache_key: str,
        session: "AsyncSession",
    ) -> BackstoryOption:
        """Validate + persist the user's backstory selection (Spec 214 FR-10.1).

        Ownership is inferred by recomputing cache_key from the authenticated
        user's ``users.onboarding_profile`` JSONB. ``backstory_cache`` has no
        ``user_id`` column — the recomputed-key check is the ownership guard.

        A duck-typed ``SimpleNamespace`` bridges JSONB keys to the attribute
        names expected by ``compute_backstory_cache_key`` (``location_city →
        city``, ``drug_tolerance → darkness_level``). This mirrors the
        ``generate_preview`` pattern at ``portal_onboarding.py:155-163``.

        Args:
            user_id: Authenticated user UUID.
            chosen_option_id: Opaque ``sha256[:12]`` id from BackstoryOption.
            cache_key: Cache key echoed from ``BackstoryPreviewResponse``.
            session: AsyncSession; caller manages lifecycle.

        Returns:
            BackstoryOption snapshot of the chosen scenario.

        Raises:
            HTTPException(403): supplied cache_key does not match recompute
                (stale profile or cross-user attempt).
            HTTPException(404): no ``backstory_cache`` row for ``cache_key``.
            HTTPException(409): ``chosen_option_id`` not in stored scenarios.
        """
        # Local imports — mirrors _bootstrap_pipeline; prevents UserRepository
        # appearing at module scope (see test_preview_does_not_write_jsonb) and
        # enables tests to patch at the source module (per
        # .claude/rules/testing.md "patch source module, not importer").
        from nikita.db.repositories.backstory_cache_repository import (
            BackstoryCacheRepository as _BackstoryCacheRepository,
        )
        from nikita.db.repositories.user_repository import UserRepository

        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)
        profile_jsonb: dict[str, Any] = (
            (user.onboarding_profile or {}) if user is not None else {}
        )

        # SimpleNamespace bridge: JSONB keys → attr names used by
        # compute_backstory_cache_key.
        pseudo = SimpleNamespace(
            city=profile_jsonb.get("location_city"),
            darkness_level=profile_jsonb.get("drug_tolerance"),
            social_scene=profile_jsonb.get("social_scene"),
            life_stage=profile_jsonb.get("life_stage"),
            interest=profile_jsonb.get("interest"),
            age=profile_jsonb.get("age"),
            occupation=profile_jsonb.get("occupation"),
        )
        recomputed_key = compute_backstory_cache_key(pseudo)
        if recomputed_key != cache_key:
            # FR-7/NFR-3: no PII in error detail; Nikita-voiced message.
            raise HTTPException(
                status_code=403,
                detail="Clearance mismatch. Start over.",
            )

        cache_repo = _BackstoryCacheRepository(session)
        cached_scenarios = await cache_repo.get(cache_key)
        if cached_scenarios is None:
            raise HTTPException(
                status_code=404,
                detail="Backstory not found. Start over.",
            )

        # Locate the chosen scenario by id in the stored envelope.
        matched: dict[str, Any] | None = None
        for scenario in cached_scenarios:
            if scenario.get("id") == chosen_option_id:
                matched = scenario
                break
        if matched is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "That scenario doesn't exist. Pick one she actually "
                    "generated for you."
                ),
            )

        # Snapshot full 6-field BackstoryOption into JSONB (not just the id —
        # survives backstory_cache eviction).
        chosen_option = BackstoryOption.model_validate(matched)
        await user_repo.update_onboarding_profile_key(
            user_id,
            "chosen_option",
            chosen_option.model_dump(mode="json"),
        )
        await session.commit()

        # FR-7/NFR-3: emit structured event with tone+venue (scenario-derived,
        # NOT user-provided) + cache_key_hash (cache_key contains city which is
        # PII-adjacent). Never include name/age/occupation/phone/city raw.
        cache_key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:8]
        logger.info(
            "onboarding.backstory_chosen user_id=%s chosen_option_id=%s "
            "tone=%s venue=%s cache_key_hash=%s",
            user_id,
            chosen_option_id,
            chosen_option.tone,
            chosen_option.venue,
            cache_key_hash,
        )

        return chosen_option

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _bootstrap_pipeline(
        self,
        user_id: UUID,
        profile: object,
        session: "AsyncSession",
    ) -> list[BackstoryOption]:
        """Run venue research + backstory generation with pipeline_state transitions.

        Implements FR-5.1 (state machine) and FR-11 (idempotence):
        - Reads pipeline_state from users.onboarding_profile before running.
        - If already "ready", skips all work and returns [] (idempotent).
        - Otherwise transitions: pending → ready | degraded | failed.

        State transitions written via UserRepository.update_onboarding_profile_key
        (FR-5.2, uses jsonb_set to avoid full-profile roundtrips).

        IMPORTANT: UserRepository is imported locally to avoid polluting the
        module namespace.  The test_preview_does_not_write_jsonb test asserts
        that `UserRepository` is NOT a module-level name in portal_onboarding.

        Args:
            user_id: User UUID (for logging and state writes).
            profile: Duck-typed profile object — same duck type as process().
            session: AsyncSession.  Caller manages lifecycle; this method
                never commits.

        Returns:
            List of BackstoryOption (may be empty on degraded/failed paths).
        """
        # Local import — must NOT appear at module level (see test_preview_does_not_write_jsonb)
        from nikita.db.repositories.user_repository import UserRepository

        user_repo = UserRepository(session)

        # FR-11 idempotence: skip if pipeline already ready
        user = await user_repo.get(user_id)
        existing_state = (
            (user.onboarding_profile or {}).get("pipeline_state")
            if user is not None
            else None
        )
        if existing_state == "ready":
            logger.info(
                "portal_handoff.bootstrap_pipeline outcome=skipped "
                "user_id=%s pipeline_state=ready",
                user_id,
            )
            return []

        # FR-11: skip if a concurrent bootstrap is already in progress
        if existing_state == "pending":
            logger.info(
                "portal_handoff.bootstrap_pipeline outcome=already_pending user_id=%s",
                user_id,
            )
            return []

        # T3.2 / FR-2a: write pending on entry for both pipeline_state and venue_research_status
        await user_repo.update_onboarding_profile_key(user_id, "pipeline_state", "pending")
        await user_repo.update_onboarding_profile_key(user_id, "venue_research_status", "pending")

        cache_repo = BackstoryCacheRepository(session)
        cache_key = compute_backstory_cache_key(profile)

        venue_cache_repo = VenueCacheRepository(session)
        venue_service = VenueResearchService(venue_cache_repository=venue_cache_repo)
        backstory_service = BackstoryGeneratorService()

        city = getattr(profile, "city", None) or "unknown"
        scene = getattr(profile, "social_scene", None) or "unknown"

        try:
            # Venue research — T3.4: timeout → degraded
            try:
                venue_result = await asyncio.wait_for(
                    venue_service.research_venues(city, scene),
                    timeout=VENUE_RESEARCH_TIMEOUT_S,
                )
                # FR-2a: mark venue research complete after success
                await user_repo.update_onboarding_profile_key(
                    user_id, "venue_research_status", "complete"
                )
                logger.info(
                    "portal_handoff.venue_research outcome=success user_id=%s "
                    "fallback_used=%s",
                    user_id,
                    venue_result.fallback_used,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "portal_handoff.venue_research outcome=timeout user_id=%s",
                    user_id,
                )
                # T3.4 / FR-2a: write degraded on venue timeout + venue_research_status=failed
                await user_repo.update_onboarding_profile_key(
                    user_id, "pipeline_state", "degraded"
                )
                await user_repo.update_onboarding_profile_key(
                    user_id, "venue_research_status", "failed"
                )
                return []

            venues_list = venue_result.venues
            venue_names = [v.name for v in venues_list]

            # Adapter: profile → BackstoryPromptProfile
            orm_like_profile = ProfileFromOnboardingProfile.from_pydantic(user_id, profile)

            # Backstory generation — T4.3: failure → degraded
            try:
                scenarios_result = await asyncio.wait_for(
                    backstory_service.generate_scenarios(orm_like_profile, venues_list),
                    timeout=BACKSTORY_GEN_TIMEOUT_S,
                )
                logger.info(
                    "portal_handoff.backstory outcome=success user_id=%s "
                    "scenario_count=%d",
                    user_id,
                    len(scenarios_result.scenarios),
                )
            except Exception as exc:
                logger.warning(
                    "portal_handoff.backstory outcome=failure user_id=%s error_class=%s",
                    user_id,
                    type(exc).__name__,
                )
                # T4.3: write degraded on backstory failure
                await user_repo.update_onboarding_profile_key(
                    user_id, "pipeline_state", "degraded"
                )
                return []

        except Exception:
            # Uncaught exception (not TimeoutError, not backstory Exception):
            # write 'failed' then re-raise so caller can handle/log.
            logger.exception(
                "portal_handoff.bootstrap_pipeline outcome=failed user_id=%s",
                user_id,
            )
            await user_repo.update_onboarding_profile_key(
                user_id, "pipeline_state", "failed"
            )
            raise

        options = [
            _scenario_to_option(cache_key, i, s)
            for i, s in enumerate(scenarios_result.scenarios)
        ]

        # Persist to cache
        envelope_scenarios = [opt.model_dump(mode="json") for opt in options]
        await cache_repo.set(
            cache_key,
            envelope_scenarios,
            venue_names,
            BACKSTORY_CACHE_TTL_DAYS,
        )

        # FR-2a: mark backstory_available=True immediately after cache write succeeds
        await user_repo.update_onboarding_profile_key(user_id, "backstory_available", True)
        logger.info(
            "portal_handoff.backstory_available user_id=%s backstory_available=True",
            user_id,
        )

        # T3.2: write ready on full success
        await user_repo.update_onboarding_profile_key(user_id, "pipeline_state", "ready")
        logger.info(
            "portal_handoff.pipeline_state_transition user_id=%s state=ready",
            user_id,
        )

        return options

    def _deserialize_options(self, cached_raw: object) -> list[BackstoryOption]:
        """Deserialize cached list[dict] into BackstoryOption list.

        BackstoryCacheRepository.get() returns list[dict] | None — never a
        dict envelope.  The envelope shape (with "scenarios" / "venues_used"
        keys) is read by generate_preview() via get_envelope() separately.

        Args:
            cached_raw: Value returned by BackstoryCacheRepository.get();
                either list[dict] or None.

        Returns:
            List of BackstoryOption (may be empty).
        """
        scenario_dicts = cached_raw or []
        return [BackstoryOption.model_validate(d) for d in scenario_dicts]
