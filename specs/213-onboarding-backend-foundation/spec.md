# Feature Specification: Onboarding Backend Foundation

**Spec ID**: 213-onboarding-backend-foundation
**Status**: Draft — iteration 2
**Created**: 2026-04-14
**Predecessor**: Spec 210 (timing) MERGED, Spec 212 (phone capture) COMPLETE, PR #277 (recovery) MERGED
**Successor**: Spec 214 (portal-onboarding-wizard) — depends on `contracts.py` from this spec
**Brief**: `.claude/plans/onboarding-overhaul-brief.md`
**Validation**: `validation-findings.md` tracks 60 iteration-1 findings; this rewrite addresses ALL severities (per user policy)

---

## Overview

### Problem Statement

The portal onboarding handoff produces a degraded user experience because:

1. **Profile is stripped at handoff**: After PR #277 restored PR #273's fixes, the structural pipeline-bootstrap bugs are gone, but only fields that exist on `UserOnboardingProfile` are passed through. New fields the user wants Nikita to know (name, age, occupation in user-profiles ORM) are not collected, not stored, and therefore not used in the first message or in the post-processing pipeline.
2. **City research + backstory generation are not invoked from portal**: Both `VenueResearchService` and `BackstoryGeneratorService` exist in `nikita/services/` and were wired into the OLD Telegram-first onboarding (see `nikita/platforms/telegram/onboarding/handler.py`). After Spec 081's portal migration, these services were never plumbed into `save_portal_profile`. The first message therefore lacks city-aware flavor, scenario-aware backstory hooks, and the "introducing your friends" beat that gave the original Telegram experience its sense of progression.
3. **No pipeline-readiness gate**: The user can interact with Nikita the moment the wizard submits, but the post-processing pipeline (prompt builder, memory seeding, scoring init) may still be running. The user receives a generic, pre-pipeline first message; the bug surfaces as Nikita "forgetting" what she just said because the seeded conversation was not yet processed when the user replied. There is also no `pipeline_state` JSONB key written today (verified across all Python files).
4. **No type contract for the portal/voice → backend boundary**: `PortalProfileRequest`, the handoff result, and the backstory option list are scattered across modules. Spec 214 (portal wizard) cannot start in parallel because it has no shared, frozen contract to consume.

### Proposed Solution

Add a **backend foundation** that supports a richer, more engaging onboarding experience:

1. **Expand `user_profiles` schema + `UserOnboardingProfile` Pydantic + `PortalProfileRequest`** to collect `name`, `age`, `occupation` alongside the fields restored by PR #277. (NOTE: `age` already exists on `UserOnboardingProfile` Pydantic at `models.py:122`; only `name` is net-new on the Pydantic model. `occupation` already exists at `models.py:87`.)
2. **Wire `VenueResearchService` + `BackstoryGeneratorService`** into a new thin facade `nikita/services/portal_onboarding.py` invoked from a new `nikita/api/routes/portal_onboarding.py` route file. Each service has a named timeout budget (`VENUE_RESEARCH_TIMEOUT_S=15`, `BACKSTORY_GEN_TIMEOUT_S=20`) and a graceful-degradation fallback. The facade reuses the existing `_ProfileFromAnswers` adapter (promoted to `nikita/onboarding/adapters.py`) for the Pydantic→ORM bridge.
3. **Publish `nikita/onboarding/contracts.py`** as the FIRST PR — a single module exporting `OnboardingV2ProfileRequest`, `OnboardingV2ProfileResponse`, `BackstoryOption`, `PipelineReadyState`, `PipelineReadyResponse`, `ErrorResponse`. Spec 214 imports from this module. Frozen after PR #1.
4. **Add `/pipeline-ready` poll endpoint** that returns the readiness state for the user's seeded conversation, with a 2s poll interval and 20s max wait. State is read from a NEW JSONB key `users.onboarding_profile.pipeline_state` written by `_bootstrap_pipeline` (FR-5.1).
5. **Enhance `FirstMessageGenerator.generate()`** to use the chosen backstory scenario as a coda when present, in addition to PR #273's city/scene flavor.
6. **R8 — Conversation continuity** (already restored via PR #277's `_seed_conversation`): the seeded conversation MUST contain the first message as an assistant turn before the pipeline starts; this spec adds a regression test that proves the user cannot make Nikita "deny" the first message.

### Type-Layer Disambiguation (Load-Bearing Reference)
- `UserOnboardingProfile` = Pydantic model, lives in `nikita/onboarding/models.py`, persisted as JSONB on `users.onboarding_profile`.
- `UserProfile` = SQLAlchemy ORM model, lives in `nikita/db/models/profile.py`, persists to `user_profiles` table.
- `BackstoryGeneratorService.generate_scenarios(profile, venues)` at `:81` accepts a `UserProfile`-shaped object (ORM), NOT `UserOnboardingProfile` (Pydantic). The existing adapter `_ProfileFromAnswers` at `nikita/platforms/telegram/onboarding/handler.py:41-56` will be promoted to a shared module (FR-3).

### Success Criteria

- [ ] **SC-1**: After portal onboarding completes with city="Berlin" + scene="techno" + occupation="designer" + name="Anna" + age=29, the first Telegram message Nikita sends contains at least 2 of these tokens (city, scene, occupation, name). Verified by E2E test in `tests/onboarding/test_e2e.py::test_full_profile_personalizes_first_message` marked `@pytest.mark.e2e`.
- [ ] **SC-2**: The user cannot interact with Nikita until `/pipeline-ready` returns `ready` OR the 20-second hard cap elapses. Verified by ASGI integration test `tests/onboarding/test_pipeline_gate_integration.py::test_blocks_until_ready` and Cloud Run log inspection.
- [ ] **SC-3**: User replies to Nikita with the verbatim first-message text within 10 minutes of onboarding; Nikita's response acknowledges (does not deny) the prior turn. Verified by `tests/onboarding/test_r8_conversation_continuity.py::test_no_denial_of_seeded_turn` (N=10 mocked agent runs).
- [ ] **SC-4**: City research and backstory generation each respect their named timeout budgets. On timeout, the user-facing experience degrades gracefully (no error message, fallback first message used). Verified by `tests/services/test_portal_onboarding_facade.py::{test_venue_timeout, test_backstory_failure}` integration tests with simulated timeouts.
- [ ] **SC-5**: `OnboardingV2ProfileRequest` / `OnboardingV2ProfileResponse` / `BackstoryOption` / `PipelineReadyState` / `PipelineReadyResponse` / `ErrorResponse` are importable from `nikita.onboarding.contracts` and frozen (no field changes after PR #1 merges). Verified by Spec 214's CI build succeeding against this contract.
- [ ] **SC-6**: PII fields (`name`, `age`, `occupation`, `phone`) never appear in structured logs. Verified by both: (a) static `rg "name=|age=|occupation=" nikita/api/routes/portal_onboarding.py nikita/onboarding/handoff.py nikita/services/portal_onboarding.py` returns zero hits inside log statements, AND (b) runtime test `tests/onboarding/test_portal_onboarding_facade.py::test_pii_redaction_in_logs` using `caplog` to verify name/age values absent from all records produced.
- [ ] **SC-7**: New `user_profiles` columns (`name`, `occupation`, `age`) have RLS such that user can only `SELECT`/`UPDATE` their own row. Verified via Supabase `mcp__supabase__list_policies` (existing 5 policies cover new columns automatically — PostgreSQL row-level) AND `tests/db/test_rls_user_profiles.py` marked `@pytest.mark.integration` (live Supabase, NOT in unit CI gate).
- [ ] **SC-8**: All 6 SDD validators return PASS with 0 findings across CRITICAL + HIGH + MEDIUM + LOW. Verified by validation-findings.md showing 0/0/0/0 in iteration N.
- [ ] **SC-9**: Coverage: `contracts.py` 100%, `tuning.py` 100%, `portal_onboarding.py` ≥90%, route additions ≥85%. Verified by `pytest --cov` with `--cov-fail-under` thresholds.

---

## Functional Requirements

### FR-1: Profile Field Expansion (3 layers + ORM)
**Priority**: P1
**Description**: Expand profile fields across DB, ORM, Pydantic, and API request schema.

**Net-new fields**: `name` (DB + ORM + Pydantic + API). `age` net-new on DB + ORM only (already exists on `UserOnboardingProfile:122`). `occupation` net-new on DB + ORM only (already exists on `UserOnboardingProfile:87`).

**Sub-requirements**:

- **FR-1a — Supabase migration** (file: `supabase/migrations/YYYYMMDDHHMMSS_alter_user_profiles_add_name_occupation_age.sql` — use timestamp format matching existing project convention, NOT `0091_*`):
  ```sql
  ALTER TABLE user_profiles ADD COLUMN name TEXT;
  ALTER TABLE user_profiles ADD COLUMN occupation TEXT;
  ALTER TABLE user_profiles ADD COLUMN age SMALLINT CHECK (age IS NULL OR (age BETWEEN 18 AND 99));
  CREATE INDEX idx_user_profiles_age ON user_profiles(age) WHERE age IS NOT NULL;
  ```
  RLS coverage: existing 5 policies cover new columns automatically (PostgreSQL is row-level, not column-level). Rollback script: `ALTER TABLE user_profiles DROP COLUMN name, DROP COLUMN occupation, DROP COLUMN age;` documented in migration file.

- **FR-1b — ORM additions** (file: `nikita/db/models/profile.py`):
  ```python
  name: Mapped[str | None] = mapped_column(String, nullable=True)
  occupation: Mapped[str | None] = mapped_column(String, nullable=True)
  age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
  ```
  Use `SmallInteger` (PostgreSQL `SMALLINT`), NOT `Integer`. Without ORM mapping, Supabase silently discards writes to columns not in the mapping.

- **FR-1c — Pydantic UserOnboardingProfile additions** (file: `nikita/onboarding/models.py:76`): only `name` is net-new (age + occupation already exist). Add:
  ```python
  name: str | None = Field(default=None, min_length=1, max_length=100, description="User's first name")
  ```
  Update `ProfileFieldUpdate.validate_field_name` allow-list at `:204-219` to add `"name"`.

- **FR-1d — API PortalProfileRequest extension** (file: `nikita/api/routes/onboarding.py:647`):
  ```python
  name: str | None = Field(default=None, min_length=1, max_length=100)
  age: int | None = Field(default=None, ge=18, le=99)
  occupation: str | None = Field(default=None, min_length=1, max_length=100)
  ```
  Note: same Pydantic `Field` constraints as DB CHECK to keep app-layer error messages clear before DB rejection.

- **FR-1e — JSONB key canonical name**: User name persists in `users.onboarding_profile` as key `"name"` (NOT `"user_name"`). Existing read sites at `nikita/api/routes/onboarding.py:458-460, :556-557` that read `"user_name"` MUST be updated to read `"name"` (with fallback to `"user_name"` for one release cycle for backwards compat).

### FR-2: Contract Module (Ships First)
**Priority**: P1
**Description**: Create `nikita/onboarding/contracts.py` exporting the following Pydantic types. **CONSTRAINT**: this module MUST NOT import from `nikita.onboarding.models`, `nikita/db/models/`, or `nikita.engine.constants` — it is a standalone contract module to prevent circular imports. After PR #1 merges, the contract is FROZEN — any field addition requires an ADR + re-coordination with Spec 214.

**`PipelineReadyState`** (string Literal, NOT enum, for JSON serialization simplicity):
```python
PipelineReadyState = Literal["pending", "ready", "degraded", "failed"]
```

**`BackstoryOption`** (mirrors `BackstoryScenario` dataclass at `nikita/services/backstory_generator.py:29`):
```python
class BackstoryOption(BaseModel):
    id: str = Field(description="Opaque ID, stable per (cache_key, index)")
    venue: str = Field(description="Where the meeting happened")
    context: str = Field(description="Setting / vibe in 2-3 sentences")
    the_moment: str = Field(description="The catalyst moment")
    unresolved_hook: str = Field(description="One-liner Nikita can reference in first message")
    tone: Literal["romantic", "intellectual", "chaotic"]
```

**`OnboardingV2ProfileRequest`** (extends current `PortalProfileRequest`):
```python
class OnboardingV2ProfileRequest(BaseModel):
    location_city: str = Field(min_length=2, max_length=100)
    social_scene: Literal["techno", "art", "food", "cocktails", "nature"]
    drug_tolerance: int = Field(ge=1, le=5)
    life_stage: Literal["tech","finance","creative","student","entrepreneur","other"] | None = None
    interest: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, min_length=8, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=18, le=99)
    occupation: str | None = Field(default=None, min_length=1, max_length=100)
    wizard_step: int | None = Field(default=None, ge=1, le=11, description="Last completed wizard step for resume detection")
```

**`OnboardingV2ProfileResponse`** (returned by `POST /onboarding/profile`):
```python
class OnboardingV2ProfileResponse(BaseModel):
    user_id: UUID
    pipeline_state: PipelineReadyState  # initial state, typically "pending"
    backstory_options: list[BackstoryOption]  # may be empty on degraded path
    chosen_option: BackstoryOption | None  # ALWAYS None from this spec's endpoints
    poll_endpoint: str  # absolute path to /pipeline-ready/{user_id}
    poll_interval_seconds: float  # = PIPELINE_GATE_POLL_INTERVAL_S
    poll_max_wait_seconds: float  # = PIPELINE_GATE_MAX_WAIT_S
```

**Note on `chosen_option`**: This field is ALWAYS `None` in responses from Spec 213 endpoints (POST/PATCH `/onboarding/profile`, GET `/pipeline-ready`). Spec 214 owns defining the backstory-selection endpoint (e.g., `POST /api/v1/onboarding/backstory-choice`) that persists the user's pick and returns an updated `OnboardingV2ProfileResponse` with `chosen_option` populated. The field is in this contract so Spec 214 doesn't need to widen it later.

**`PipelineReadyResponse`** (returned by `GET /pipeline-ready/{user_id}`):
```python
class PipelineReadyResponse(BaseModel):
    state: PipelineReadyState
    message: str | None = None  # optional user-facing explanation, present on degraded/failed
    checked_at: datetime  # ISO-8601, for monitoring/debugging
    venue_research_status: Literal["pending", "complete", "failed", "cache_hit"] = "pending"  # FR-2a, default if JSONB key missing
    backstory_available: bool = False  # FR-2a, default if JSONB key missing (True once scenarios persisted)
```

**Missing-key defaults**: if `users.onboarding_profile.venue_research_status` is absent → return `"pending"`. If `backstory_available` absent → return `False`. This keeps `/pipeline-ready` as a single-SELECT NFR-1 path. Existing `PipelineReadyResponse` construction sites (tests, mocks) may omit the new fields — defaults cover them.

**`BackstoryPreviewRequest`** (input to NEW `POST /onboarding/preview-backstory` — FR-4a, added iter-6):
```python
class BackstoryPreviewRequest(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    social_scene: Literal["techno", "art", "food", "cocktails", "nature"]
    darkness_level: int = Field(ge=1, le=5)  # maps to drug_tolerance in OnboardingV2ProfileRequest (legacy-name compat)
    life_stage: Literal["tech", "finance", "creative", "student", "entrepreneur", "other"] | None = None  # Literal match with OnboardingV2ProfileRequest for cache_key parity
    interest: str | None = Field(default=None, max_length=200)
    age: int | None = Field(default=None, ge=18, le=99)
    occupation: str | None = Field(default=None, max_length=100)
```

**Naming note**: `darkness_level` here matches `UserOnboardingProfile.darkness_level`. `OnboardingV2ProfileRequest` uses `drug_tolerance` for legacy-ORM compat. Backend maps `OnboardingV2ProfileRequest.drug_tolerance → UserOnboardingProfile.darkness_level` when recomputing cache_key on submit, guaranteeing parity with preview.

**`BackstoryPreviewResponse`**:
```python
class BackstoryPreviewResponse(BaseModel):
    scenarios: list[BackstoryOption]  # 2-3 options; empty on degraded path
    venues_used: list[str]  # venue names incorporated into scenarios (for wizard UI)
    cache_key: str  # opaque; returned for debugging/observability (NOT echoed back — backend recomputes)
    degraded: bool  # True if backstory service failed; scenarios will be empty or generic
```

**Cache coherence mechanism** (replaces earlier "echo back" wording): backend RECOMPUTES `cache_key` from submitted `OnboardingV2ProfileRequest` fields on final `POST /onboarding/profile`. Since `compute_backstory_cache_key` is deterministic over the same inputs, and `BackstoryPreviewRequest` carries the same semantic fields as `OnboardingV2ProfileRequest`, the recomputed key matches the preview key → cache hit → no duplicate Claude call. No echo field needed. The `cache_key` in the response is informational only (observability, debugging).

**`ErrorResponse`** (matches existing FastAPI shape used at `onboarding.py:140`):
```python
class ErrorResponse(BaseModel):
    detail: str
```

### FR-2a (iter-6 amendment): Pipeline-Ready Response Extension
**Priority**: P1
**Description**: Extend `PipelineReadyResponse` (FR-2) with `venue_research_status` + `backstory_available` fields (defaults shown in contract above). These support portal dossier wizard showing live venue research state during step 4 and gating step 8 on scenario availability. `/pipeline-ready` becomes single source of truth for ALL wizard-blocking state.

**Write paths** (both keys written by `_bootstrap_pipeline` + facade, NOT preview endpoint):
- `venue_research_status`: set to `"pending"` at pipeline entry → `"complete"`/`"failed"`/`"cache_hit"` after venue research step. Via `user_repo.update_onboarding_profile_key(user_id, "venue_research_status", value)` (FR-5.2).
- `backstory_available`: set to `True` immediately after `BackstoryCacheRepository.set` succeeds (either in facade post-handoff OR after final-POST cache hit). Via `user_repo.update_onboarding_profile_key(user_id, "backstory_available", True)`.

**Read path** (GET `/pipeline-ready/{user_id}`):
- Single SELECT on `users.onboarding_profile` JSONB (existing NFR-1 p99 ≤200ms guarantee preserved)
- Read `pipeline_state`, `venue_research_status`, `backstory_available` from JSONB
- Missing keys → Pydantic defaults (`"pending"` / `False`)
- No second table query to `backstory_cache` — strictly JSONB read

**Acceptance Criteria** (adds to US-2):
- [ ] AC-2.5: `/pipeline-ready` response includes `venue_research_status` + `backstory_available` fields. Test: `tests/api/routes/test_portal_onboarding.py::test_pipeline_ready_includes_new_fields` (consolidates into existing portal_onboarding route test file per Test File Inventory convention). Mock `users.onboarding_profile = {"pipeline_state": "ready", "venue_research_status": "complete", "backstory_available": True}` → assert response body contains all three. Sibling test `test_pipeline_ready_defaults`: mock with empty JSONB `{}` → assert defaults `("pending", False)` are returned.

### FR-4a (iter-6 amendment): Backstory Preview Endpoint (for pre-submit reveal)
**Priority**: P1
**Description**: Add `POST /api/v1/onboarding/preview-backstory` accepting `BackstoryPreviewRequest` and returning `BackstoryPreviewResponse`. Called by portal wizard at Step 8 (dossier reveal) BEFORE the final `POST /onboarding/profile`. The portal dossier flow needs backstory BEFORE phone capture (Step 9) — per UX expert review, backstory is the emotional climax that justifies the phone ask.

**Auth**: requires user JWT (existing `get_current_user_id`). Rate limit 5 req/min per user via NEW `preview_rate_limit` dependency (FR-4a.1 below).

**Dependencies** (FastAPI route handler signature):
```python
@router.post("/preview-backstory", response_model=BackstoryPreviewResponse)
async def preview_backstory(
    request: BackstoryPreviewRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    _: None = Depends(preview_rate_limit),  # 429 on exceeded
) -> BackstoryPreviewResponse:
```

**Service instantiation** (before numbered steps — mirrors FR-3 facade pattern):
```python
venue_cache_repo = VenueCacheRepository(session)
venue_service = VenueResearchService(venue_cache_repository=venue_cache_repo)
backstory_repo = BackstoryCacheRepository(session)
backstory_service = BackstoryGeneratorService()  # no constructor args per backstory_generator.py:77
```

**Behavior**:
1. Construct `pseudo_profile` explicitly as duck-typed namespace (NOT a `UserOnboardingProfile` since request fields may not all match): `pseudo_profile = SimpleNamespace(city=request.city, social_scene=request.social_scene, darkness_level=request.darkness_level, life_stage=request.life_stage, interest=request.interest, age=request.age, occupation=request.occupation)`. Then `cache_key = compute_backstory_cache_key(pseudo_profile)` (function is duck-typed via attribute reads — FR-3 step 3 helper works on any object with these attrs).
2. Check `backstory_repo.get(cache_key)` — if hit, deserialize stored envelope `{scenarios, venues_used}` → return cached `BackstoryPreviewResponse(scenarios=[BackstoryOption.model_validate(d) for d in envelope["scenarios"]], venues_used=envelope["venues_used"], cache_key=cache_key, degraded=False)`.
3. On miss: `venue_result = await asyncio.wait_for(VenueResearchService.research_venues(city, scene), timeout=VENUE_RESEARCH_TIMEOUT_S)`. On timeout → log + return `degraded=True, scenarios=[], venues_used=[]` (no cache write). **Preview endpoint does NOT write to `users.onboarding_profile` JSONB** — that's the handoff/pipeline path's responsibility (FR-5.1). Keeps preview stateless.
4. `venues_list = venue_result.venues` (extract from dataclass per FR-3 step 5 correction). `venue_names = [v.name for v in venues_list]`.
5. `orm_like_profile = ProfileFromOnboardingProfile.from_pydantic(user_id=current_user_id, profile=pseudo_profile)` (adapter accepts duck-typed input for `profile` param). `scenarios_result = await asyncio.wait_for(backstory_service.generate_scenarios(orm_like_profile, venues_list), timeout=BACKSTORY_GEN_TIMEOUT_S)`. On timeout/exception → log + return `BackstoryPreviewResponse(scenarios=[], venues_used=venue_names, cache_key=cache_key, degraded=True)`.
6. Convert `BackstoryScenario[] → BackstoryOption[]` via `_scenario_to_option(cache_key, index, scenario)` (FR-3.2).
7. Persist envelope `{scenarios: [opt.model_dump(mode="json") for opt in options], venues_used: venue_names}` via `BackstoryCacheRepository.set(cache_key, envelope, ttl_days=BACKSTORY_CACHE_TTL_DAYS)`.
8. Return `BackstoryPreviewResponse(scenarios=options, venues_used=venue_names, cache_key=cache_key, degraded=False)`.

**Cache coherence mechanism** (no echo needed): on final `POST /onboarding/profile`, backend route handler constructs its own `UserOnboardingProfile` from the submitted `OnboardingV2ProfileRequest` (mapping `drug_tolerance → darkness_level`), computes `cache_key = compute_backstory_cache_key(profile)`, and passes to facade. Facade calls `BackstoryCacheRepository.get(cache_key)` — if preview was called with the same semantic fields, cache_key matches → cache hit → scenarios reused → no duplicate Claude call. Deterministic function over stable inputs = no echo field needed.

#### FR-4a.1 — Preview Rate Limit Dependency

**Approach**: standalone `preview_rate_limit` FastAPI dependency (avoids modifying the shared `DatabaseRateLimiter.check()` signature):

```python
# nikita/api/middleware/rate_limit.py
from nikita.onboarding.tuning import PREVIEW_RATE_LIMIT_PER_MIN

class _PreviewRateLimiter(DatabaseRateLimiter):
    """Subclass that overrides MAX_PER_MINUTE with a separate counter key prefix."""
    MAX_PER_MINUTE = PREVIEW_RATE_LIMIT_PER_MIN

    def _get_minute_window(self) -> str:
        # Override matches actual parent method at rate_limiter.py:445 (no user_id param).
        # Returns prefixed window key; check() at line 301 reads this to build the DB row key.
        return f"preview:{super()._get_minute_window()}"  # separate counter from voice

async def preview_rate_limit(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    limiter = _PreviewRateLimiter(session)
    result = await limiter.check(current_user_id)
    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
```

This approach:
- Does NOT modify the existing `DatabaseRateLimiter.check(user_id)` signature (no breaking change to voice rate limiter)
- Uses a subclass to override `MAX_PER_MINUTE` = 5 and `_get_minute_window` for separate counter (prefix `preview:`)
- Returns `Retry-After: 60` header on 429

Tuning constant:
```python
PREVIEW_RATE_LIMIT_PER_MIN: Final[int] = 5
"""Per-user rate limit for /onboarding/preview-backstory.
Prior values: none (new in Spec 213).
Rationale: each call triggers Claude + Firecrawl; 5/min covers wizard step-navigation retries
without enabling abuse. Voice rate limit is 20/min (different surface). Separate counter key
avoids sharing quota."""
```

Add new dependency `preview_rate_limit` in `nikita/api/middleware/rate_limit.py` modeled on existing `voice_rate_limit`:
- The subclass pattern shown above is the AUTHORITATIVE approach — do NOT modify `DatabaseRateLimiter.check()` signature
- Separate counter key prefix (`preview:`) avoids sharing quota with voice endpoints
- On exceeded: `HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})`

**Tests**:
- `tests/services/test_preview_backstory.py::test_cache_key_stable` — same profile inputs produce identical cache_key (facade-level unit test, mocks `BackstoryCacheRepository`)
- `tests/services/test_preview_backstory.py::test_degraded_returns_empty` — backstory service failure → `degraded=True`, `scenarios=[]`, `venues_used=<venue_names>` (facade-level, mocks BackstoryGeneratorService + VenueResearchService)
- `tests/api/routes/test_preview_backstory_route.py::test_profile_post_reuses_cache` — integration via FastAPI TestClient. POST `/preview-backstory` → POST `/profile` with same profile fields → assert `BackstoryCacheRepository.get` returns preview's cached envelope; assert Claude NOT called on second POST.
- `tests/api/routes/test_preview_backstory_route.py::test_rate_limit` — 6th call in 1 minute returns 429 with `Retry-After: 60` header.
- `tests/api/routes/test_preview_backstory_route.py::test_stateless_no_jsonb_write` — assert `users.onboarding_profile` is unchanged after preview call.

### FR-3: Portal Onboarding Facade
**Priority**: P1
**Description**: Create `nikita/services/portal_onboarding.py` — a thin facade with single responsibility (no business logic).

**Signature**:
```python
async def process(
    user_id: UUID,
    profile: UserOnboardingProfile,
    session: AsyncSession,  # passed in; facade NEVER opens own session
) -> list[BackstoryOption]:
```

**Behavior**:
1. Construct `VenueCacheRepository(session)` and inject into `VenueResearchService(venue_cache_repository=repo)` per existing constructor at `venue_research.py:68`.
2. Construct `BackstoryCacheRepository(session)` (NEW per FR-12).
2b. Construct `backstory_service = BackstoryGeneratorService()` (no constructor args required per `backstory_generator.py:77`).
3. Compute `cache_key = compute_backstory_cache_key(profile)` using `AGE_BUCKETS` + `OCCUPATION_CATEGORIES` from `tuning.py` to bucket age and occupation BEFORE constructing key; missing values → `"unknown"` bucket.

   **Function definitions** (all in `nikita/onboarding/tuning.py`):
   ```python
   def _age_bucket(age: int | None) -> str:
       """Map age to bucket label per AGE_BUCKETS. Returns 'unknown' if None."""
       if age is None:
           return "unknown"
       for low, high, label in AGE_BUCKETS:
           if low <= age <= high:
               return label
       return "unknown"  # outside any bucket

   def _occupation_bucket(occupation: str | None) -> str:
       """Map occupation string to coarse category per OCCUPATION_CATEGORIES.
       Substring match (lowercased). Returns 'other' if no match, 'unknown' if None."""
       if occupation is None:
           return "unknown"
       occ_lower = occupation.lower()
       for substring, category in OCCUPATION_CATEGORIES.items():
           if substring in occ_lower:
               return category
       return "other"

   def compute_backstory_cache_key(profile: UserOnboardingProfile) -> str:
       """Deterministic cache key for backstory generation.
       Format: 'city|scene|darkness|life_stage|interest|age_bucket|occupation_bucket'
       with 'unknown' substituted for None values. City normalized to lowercase."""
       city = (profile.city or "unknown").lower()
       scene = profile.social_scene or "unknown"
       darkness = str(profile.darkness_level)
       life_stage = profile.life_stage or "unknown"
       interest = (profile.interest or "unknown").lower()
       age_bkt = _age_bucket(profile.age)
       occ_bkt = _occupation_bucket(profile.occupation)
       return f"{city}|{scene}|{darkness}|{life_stage}|{interest}|{age_bkt}|{occ_bkt}"
   ```
4. Cache lookup via `BackstoryCacheRepository.get(cache_key)` — if hit, return cached `list[BackstoryOption]` and log `cache_hit=True`.
4. On cache **hit**: deserialize envelope — `options = [BackstoryOption.model_validate(d) for d in envelope["scenarios"]]`. Log `cache_hit=True`. Return `options`. (Cache stores full envelope `{scenarios, venues_used}` per FR-12; facade reads `scenarios` only for its return type, but the same envelope shape must be written on miss for consistency.)
5. On cache **miss**:
   - `venue_result = await asyncio.wait_for(venue_service.research_venues(profile.city, profile.social_scene), timeout=VENUE_RESEARCH_TIMEOUT_S)` — returns `VenueResearchResult` dataclass with `.venues: list[Venue]` and `.fallback_used: bool`. On `asyncio.TimeoutError`, log outcome=`timeout` + return `[]` (no cache write on failure).
   - Extract: `venues_list = venue_result.venues`. `venue_names = [v.name for v in venues_list]`. If `venue_result.fallback_used`, proceed with empty venues_list (backstory will use generic flavor).
   - Adapter step: `orm_profile = ProfileFromOnboardingProfile.from_pydantic(user_id, profile)` (FR-3.1 below).
   - `scenarios_result = await asyncio.wait_for(backstory_service.generate_scenarios(orm_profile, venues_list), timeout=BACKSTORY_GEN_TIMEOUT_S)` — returns `BackstoryScenariosResult` containing `list[BackstoryScenario]` dataclass. On timeout/`RuntimeError`/`anthropic.APIError`, log outcome=`timeout`/`failure` + return `[]`.
   - Convert each `BackstoryScenario` → `BackstoryOption` via `_scenario_to_option(cache_key, index, scenario)` (FR-3.2 below).
   - Validate `tone` field: if scenario.tone not in `{"romantic","intellectual","chaotic"}`, default to `"chaotic"` (most flexible) + log `tone_invalid_fallback`.
   - **Persist envelope** matching FR-4a + FR-12 shape: `envelope = {"scenarios": [opt.model_dump(mode="json") for opt in options], "venues_used": venue_names}`. Then `BackstoryCacheRepository.set(cache_key, envelope, ttl_days=BACKSTORY_CACHE_TTL_DAYS)`. **Both writers (facade + preview endpoint) produce identical envelope shape** — cache readers (either path) can safely expect both keys.
   - After successful cache set: `await user_repo.update_onboarding_profile_key(user_id, "backstory_available", True)` (FR-2a write path).
6. Return `list[BackstoryOption]` (empty on degraded path; venues_used consumed only by preview endpoint response, facade returns options only).

#### FR-3.2 — Scenario-to-Option Converter
Define in `nikita/services/portal_onboarding.py`:
```python
import hashlib
from nikita.onboarding.contracts import BackstoryOption
from nikita.services.backstory_generator import BackstoryScenario

def _scenario_to_option(cache_key: str, index: int, s: BackstoryScenario) -> BackstoryOption:
    """Convert backstory_generator dataclass → frozen contract Pydantic.
    id formula: sha256(cache_key:index)[:12] — deterministic, stable, opaque."""
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
```

The `id` is deterministic so cache hits return the same `id` to the portal — the portal references it back when user picks (Spec 214's `chosen_option` write).

**Logging** (FR-7 compliant — no PII):
- `portal_handoff.venue_research`: `{event, user_id, outcome, duration_ms, cache_hit, error_class}` where `outcome ∈ {"success","timeout","failure","cache_hit"}` and `error_class: str | None` (only on `timeout`/`failure`).
- `portal_handoff.backstory`: `{event, user_id, outcome, duration_ms, cache_hit, scenario_count, error_class}` where `scenario_count: int = len(scenarios)`.

**Session safety**: facade NEVER calls `get_session_maker()()` itself. Caller (route handler) opens session. This pattern matches the fix modeled at `handoff.py:579-583` in `_bootstrap_pipeline`. Background tasks calling this facade MUST open a fresh session inside the background task body, not pass request-scoped session.

#### FR-3.1 — Pydantic↔ORM Adapter (Promoted)
Promote existing adapter `_ProfileFromAnswers` from `nikita/platforms/telegram/onboarding/handler.py:41-56` to a shared module:

**File**: `nikita/onboarding/adapters.py`

**IMPORTANT**: `BackstoryGeneratorService._build_scenario_prompt` (at `backstory_generator.py:180,183,220`) accesses `profile.city` (NOT `location_city`) and `profile.primary_passion` (NOT `primary_interest`). These are DUCK-TYPED attribute names, NOT real `UserProfile` ORM columns. The adapter returns a `SimpleNamespace`-like object, NOT a real `UserProfile` row. The existing `_ProfileFromAnswers` at `handler.py:41-56` is the canonical reference — promotion preserves its duck-typing.

```python
from dataclasses import dataclass
from uuid import UUID
from nikita.onboarding.models import UserOnboardingProfile

@dataclass
class BackstoryPromptProfile:
    """Duck-typed adapter matching attribute names BackstoryGeneratorService reads.
    NOT a real UserProfile ORM object. Required attrs: city, social_scene,
    life_stage, primary_passion, drug_tolerance, name, age, occupation."""
    city: str | None
    social_scene: str | None
    life_stage: str | None
    primary_passion: str | None  # mapped from profile.interest (name collision)
    drug_tolerance: int
    name: str | None
    age: int | None
    occupation: str | None


class ProfileFromOnboardingProfile:
    """Bridges UserOnboardingProfile (Pydantic) → duck-typed BackstoryPromptProfile
    for BackstoryGeneratorService.generate_scenarios(). DO NOT return a real UserProfile ORM row —
    the service reads .city and .primary_passion which do NOT exist on UserProfile."""

    @staticmethod
    def from_pydantic(user_id: UUID, profile: UserOnboardingProfile) -> BackstoryPromptProfile:
        return BackstoryPromptProfile(
            city=profile.city,
            social_scene=profile.social_scene,
            life_stage=profile.life_stage,
            primary_passion=profile.interest,  # NAME COLLISION — generator expects primary_passion
            drug_tolerance=profile.darkness_level,
            name=profile.name,
            age=profile.age,
            occupation=profile.occupation,
        )
```

Field-mapping table (canonical):

| UserOnboardingProfile (Pydantic) | BackstoryPromptProfile (duck-typed) | Rationale |
|---|---|---|
| `city` | `city` | same name |
| `social_scene` | `social_scene` | same name |
| `life_stage` | `life_stage` | same name |
| `interest` | **`primary_passion`** | generator reads `profile.primary_passion` (legacy name) |
| `darkness_level` | `drug_tolerance` | legacy name in ORM + generator |
| `name` | `name` | NEW field |
| `age` | `age` | same name |
| `occupation` | `occupation` | same name |

`BackstoryGeneratorService.generate_scenarios(profile, venues)` signature accepts any object with these attributes (duck typing). Do NOT try to construct a real `UserProfile` — its columns are `location_city`, `primary_interest`, etc. which do NOT match the generator's reads.

Both Telegram path (`handler.py`) and portal path (`portal_onboarding.py`) import from `adapters.py`. Avoid two unsynchronized adapters.

### FR-4: Tuning Constants
**Priority**: P1
**Description**: Define in `nikita/onboarding/tuning.py` per `.claude/rules/tuning-constants.md`. **CONSTRAINT**: `tuning.py` MUST NOT import from `nikita.engine.constants` — different domain.

```python
VENUE_RESEARCH_TIMEOUT_S: Final[float] = 15.0
"""Per-call timeout for VenueResearchService.research_venues.
Prior values: none (new in Spec 213, GH #213).
Rationale: Firecrawl typical p95 ~8s; 15s budget covers cold cache + 1 retry."""

BACKSTORY_GEN_TIMEOUT_S: Final[float] = 20.0
"""Per-call timeout for BackstoryGeneratorService.generate_scenarios.
Prior values: none (new in Spec 213, GH #213).
Rationale: Claude Haiku typical p95 ~12s; 20s covers tail latency + 1 retry."""

PIPELINE_GATE_POLL_INTERVAL_S: Final[float] = 2.0
"""Portal poll interval for /pipeline-ready endpoint.
Prior values: none (new in Spec 213, GH #213).
Rationale: balances perceived responsiveness vs Cloud Run cold-start churn."""

PIPELINE_GATE_MAX_WAIT_S: Final[float] = 20.0
"""Maximum portal wait for pipeline readiness before unblocking.
Prior values: none (new in Spec 213, GH #213).
Rationale: covers Cloud Run cold-start (5s) + venue research (15s) + safety margin."""

BACKSTORY_CACHE_TTL_DAYS: Final[int] = 30
"""Backstory cache TTL for unique (city, scene, ...) profile shape.
Prior values: none (new in Spec 213, GH #213).
Rationale: matches existing VenueCache TTL; balances cost vs scenario freshness."""

BACKSTORY_HOOK_PROBABILITY: Final[float] = 0.50
"""Probability that FirstMessageGenerator includes a backstory hook in the first message.
Prior values: none (new in Spec 213, GH #213).
Rationale: 50% creates variety; testable via patched value (1.0 always-include, 0.0 never-include)."""

PREVIEW_RATE_LIMIT_PER_MIN: Final[int] = 5
"""Per-user rate limit for POST /onboarding/preview-backstory endpoint (FR-4a.1).
Prior values: none (new in Spec 213, iter-7).
Rationale: each call triggers Claude + Firecrawl; 5/min covers wizard step navigation + legitimate
retries but prevents abuse/DoS. Voice rate limit is 20/min — different surface + different cost profile.
Separate counter key prefix 'preview:' avoids sharing quota with voice rate limiter."""

AGE_BUCKETS: Final[tuple[tuple[int, int, str], ...]] = (
    (18, 24, "young_adult"),
    (25, 34, "twenties"),
    (35, 49, "midlife"),
    (50, 99, "experienced"),
)
"""Age bucketing for backstory cache key. Inclusive boundaries.
Prior values: none (new in Spec 213).
Rationale: 4 buckets balance cache hit ratio vs personalization granularity."""

OCCUPATION_CATEGORIES: Final[dict[str, str]] = {
    # mapping: lowercase substring → coarse category for cache key
    "engineer": "tech", "developer": "tech", "designer": "tech",
    "artist": "arts", "musician": "arts", "writer": "arts",
    "banker": "finance", "trader": "finance", "analyst": "finance",
    "nurse": "healthcare", "doctor": "healthcare",
    "student": "student",
    "barista": "service", "server": "service", "retail": "service",
}
"""Coarse occupation categorization for backstory cache key.
Original full string preserved in profile.occupation; this is for cache bucketing only.
Prior values: none (new in Spec 213).
Rationale: 6 categories balance cache hit ratio vs persona variety. Default: 'other'."""
```

Each constant has regression-guard test in `tests/onboarding/test_tuning_constants.py` asserting exact value + comment referencing GH issue.

### FR-5: Pipeline-Readiness Endpoint
**Priority**: P1
**Description**: Add `GET /api/v1/onboarding/pipeline-ready/{user_id}` returning `PipelineReadyResponse`.

**Auth**: requires user JWT (existing `get_current_user_id` dependency at `onboarding.py:139`). User can only query their own state. Cross-user access returns HTTP 403 with body `{"detail": "Not authorized"}` (matches existing pattern at `onboarding.py:140`). Unknown user_id returns HTTP 404 with body `{"detail": "User not found"}`.

**Implementation**: reads `users.onboarding_profile.pipeline_state` JSONB key set by `_bootstrap_pipeline` per FR-5.1. Single SELECT query, p99 ≤200ms (NFR-1).

**Response shape**: HTTP 200 body matches `PipelineReadyResponse`. Missing `pipeline_state` JSONB key (user exists but key absent) = `state="pending"` (not error).

**Portal Behavior Contract** (consumed by Spec 214):
| State | Portal Action |
|---|---|
| `pending` | Show "Nikita is getting ready..." spinner with ARIA `role="status"` + `aria-live="polite"` |
| `ready` | Dismiss spinner, navigate to next step (backstory picker if backstory_options non-empty, else direct to handoff completion) |
| `degraded` | Navigate forward with toast warning "Some personalization is still loading — Nikita will catch up shortly" |
| `failed` | Show error banner with retry CTA; do not block redirect after 2 retries |

**File location** (FR-13): this endpoint lives in NEW `nikita/api/routes/portal_onboarding.py`, not in the existing 34KB `onboarding.py`.

#### FR-5.1: Pipeline State Write Contract (CRITICAL — was missing in iteration 1)
**Description**: `_bootstrap_pipeline` at `nikita/onboarding/handoff.py:551-625` MUST write `pipeline_state` to `users.onboarding_profile` JSONB at every state transition:

| Trigger | Write `pipeline_state` to |
|---|---|
| Function entry (after settings flag check, before `orchestrator.process`) | `"pending"` |
| `orchestrator.process()` returns success | `"ready"` |
| `orchestrator.process()` returns success but venue OR backstory was degraded (passed via context) | `"degraded"` |
| `orchestrator.process()` raises exception | `"failed"` |
| `_bootstrap_pipeline` re-entered with `pipeline_state == "ready"` | (no-op — idempotent per FR-11) |

**Repository call**: `await user_repo.update_onboarding_profile_key(user_id, "pipeline_state", value)` — NEW method on `UserRepository` (FR-5.2).

#### FR-5.2: UserRepository Helper
**Description**: Add method `update_onboarding_profile_key(user_id: UUID, key: str, value: Any) -> None` to `nikita/db/repositories/user_repository.py` using `jsonb_set` for atomic single-key merge.

**Required imports** (must be added to `user_repository.py`):
```python
import json
from sqlalchemy import func, cast, update
from sqlalchemy.dialects.postgresql import JSONB
```

**Implementation** (CRITICAL: `json.dumps` required — bare Python strings are NOT valid PostgreSQL jsonb literals; `cast("pending", JSONB)` produces `CAST('pending' AS jsonb)` which PostgreSQL rejects because unquoted `pending` is not JSON):
```python
stmt = update(User).where(User.id == user_id).values(
    onboarding_profile=func.jsonb_set(
        User.onboarding_profile,
        f'{{{key}}}',
        cast(json.dumps(value), JSONB),  # json.dumps produces '"pending"' — valid JSON
        True  # create_missing
    )
)
await session.execute(stmt)
```
`json.dumps("pending")` returns `'"pending"'` (a JSON string literal with quotes); `json.dumps(123)` returns `'123'`; `json.dumps(True)` returns `'true'`. All are valid JSON. Cast then succeeds.

Atomic — concurrent writes to different keys do not race.

**Alternative** (simpler but less atomic): fetch user row, merge `{key: value}` into `user.onboarding_profile` dict, flush. Matches existing `update_onboarding_profile()` pattern at `user_repository.py:622`. Acceptable if atomic jsonb_set proves problematic in testing.

### FR-6: Enhanced FirstMessageGenerator
**Priority**: P2
**Description**: Extend `FirstMessageGenerator.generate()` (currently at `handoff.py:127`) to accept an optional backstory scenario.

**New signature** (keyword-only param to avoid breaking existing call sites):
```python
def generate(
    self,
    profile: UserOnboardingProfile,
    user_name: str = "you",  # preserved from existing default (handoff.py:132); only backstory_scenario is net-new
    *,
    backstory_scenario: BackstoryOption | None = None,
) -> str:
```

When `backstory_scenario` is present, include `backstory_scenario.unresolved_hook` as a one-line coda at probability `BACKSTORY_HOOK_PROBABILITY` (FR-4 constant). All existing call sites (`execute_handoff`, `execute_handoff_with_voice_callback`) updated to pass the chosen scenario when available; default `None` keeps backwards compat.

### FR-7: PII Handling + RLS Hardening
**Priority**: P1
**Description**:

- **RLS hardening DDL** (ships in PR 213-2 migration alongside FR-1a/FR-12):
  ```sql
  -- Add WITH CHECK to UPDATE policy (currently null per DB verification)
  ALTER POLICY "Users can update own profile" ON user_profiles
      WITH CHECK (id = (SELECT auth.uid()));

  -- Convert DELETE policy bare auth.uid() to subquery form (perf + consistency)
  ALTER POLICY "Users can delete own profile" ON user_profiles
      USING (id = (SELECT auth.uid()));
  ```
  Existing 5 policies on `user_profiles` cover new columns automatically (PostgreSQL is row-level, not column-level). Verify post-migration via `mcp__supabase__list_policies`.
- **Log redaction**: structured logs in `nikita/api/routes/portal_onboarding.py`, `nikita/api/routes/onboarding.py`, `nikita/onboarding/handoff.py`, `nikita/services/portal_onboarding.py` MUST NOT include `name`, `age`, `occupation`, `phone` values. Allowed: `user_id`, boolean flags (`name_present=True`), enum values (`occupation_category="tech"`).
- **Exception echoes**: `logger.error(f"...: {e}")` and `logger.error("...: %s", e)` MUST NOT receive exceptions whose `str(e)` contains PII. Use `logger.exception("...", extra={"user_id": str(user_id)})` instead.
- **Pre-existing violation fixes** (in scope for PR 213-3): `nikita/api/routes/onboarding.py:154` and `:239` MUST be migrated to `logger.exception("...", extra={"user_id": str(user_id)})` pattern. Spec-identified security gaps cannot be deferred to "out of spec" per absolute-zero policy.

### FR-8: Conversation Continuity Regression
**Priority**: P1
**Description**: Add `tests/onboarding/test_r8_conversation_continuity.py::test_no_denial_of_seeded_turn` proving user's #1 reported complaint cannot recur:
- Mock seeded conversation with assistant turn `T = "Hey Anna, so you're in Berlin..."`
- Patch `nikita.agents.text.agent.NikitaAgent.run` with `AsyncMock(return_value=MagicMock(output="She seems interesting"))`.
- Simulate user reply `f"You said: {T}"`
- Run pipeline (mocked agent) for N=10 iterations
- Assert each iteration: `re.search(r"I never said|you must be mistaken", result, re.IGNORECASE) is None`
- Assert text agent's prompt history includes `T` as assistant turn (verify via `mock_run.call_args.kwargs["messages"]` contains `{"role":"assistant","content":T}`)
- Independent from FR-6 (R7 message-personalization)

### FR-9: Re-Onboarding Detection
**Priority**: P2
**Description**: `save_portal_profile` detects re-onboarding via `users.onboarding_status != "completed" AND users.onboarding_profile != '{}'::jsonb` (using EXISTING `onboarding_status` field, NOT `onboarding_completed_at` — that column does not exist per data-layer validator D-C1).

**Mechanism**: introduce `PATCH /api/v1/onboarding/profile` endpoint (NEW, in `portal_onboarding.py`) that:
- Accepts partial `OnboardingV2ProfileRequest` (all fields optional)
- Merges into existing JSONB via `jsonb_set` (does NOT reset existing fields)
- Bypasses the `save_portal_profile` idempotency guard at `:752-769`
- Re-triggers `_trigger_portal_handoff` only if `pipeline_state` is missing or `failed`

On final submission via either POST or PATCH, backstory cache hit if `(city, scene, darkness, life_stage, interest, age_bucket, occupation_bucket)` matches prior key → no second Claude call.

### FR-10: Voice-First User Routing
**Priority**: P2
**Description**: Spec 212 added phone-conditional routing in `_trigger_portal_handoff`. This spec preserves that contract: voice-first users go through the same wizard backend (city research + backstory still relevant for voice prompt personalization). Pre-call webhook auth mechanism (per Spec 212 HMAC) UNCHANGED — only the payload content changes (now includes `OnboardingV2ProfileResponse` shape).

### FR-11: Pipeline Bootstrap Idempotence
**Priority**: P2
**Description**: `_bootstrap_pipeline` MUST be idempotent. Implementation: on entry, read `users.onboarding_profile.pipeline_state`. If `"ready"`, return immediately (log `pipeline_bootstrap.skip outcome="already_ready"`). If `"pending"` (concurrent bootstrap), return immediately (log `outcome="already_pending"`).

**Test specification** (`tests/onboarding/test_pipeline_bootstrap.py::test_idempotent_double_call`):
```python
# Mock JSONB read returns None state on call 1, "ready" on call 2
mock_user_repo.get.side_effect = [
    MagicMock(onboarding_profile={}),                          # call 1: no state
    MagicMock(onboarding_profile={"pipeline_state": "ready"}), # call 2: ready
]
# Two invocations:
await manager._bootstrap_pipeline(user_id)  # processes
await manager._bootstrap_pipeline(user_id)  # skips
assert mock_orchestrator.process.call_count == 1
```

### FR-12: BackstoryCache Repository (DDL + ORM + Repo)
**Priority**: P1
**Description**: Persist backstory scenarios for cache reuse.

**Migration** (file: `supabase/migrations/YYYYMMDDHHMMSS_create_backstory_cache.sql`):
```sql
CREATE TABLE backstory_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key TEXT NOT NULL,
    scenarios JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_backstory_cache_key UNIQUE (cache_key)
);
CREATE INDEX idx_backstory_cache_expires ON backstory_cache(expires_at);

-- RLS: deny by default; admin-only via existing is_admin() function
ALTER TABLE backstory_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins can manage backstory cache"
    ON backstory_cache FOR ALL TO public
    USING (is_admin()) WITH CHECK (is_admin());
```

**RLS rationale**: users do not query backstory_cache directly — only the backend facade does (via service role). `is_admin()` function already exists in the project (verified: used by `user_profiles` and `user_backstories` policies). Without explicit `ENABLE ROW LEVEL SECURITY` + policy, PostgreSQL leaves the table open to all authenticated users.

**ORM** (`nikita/db/models/backstory_cache.py`):
```python
class BackstoryCache(Base):
    __tablename__ = "backstory_cache"
    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)
    cache_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    scenarios: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
```

**Repository** (`nikita/db/repositories/backstory_cache_repository.py`) — returns raw `dict` envelope to keep `db/` layer free of domain contract types (matches `VenueCacheRepository` pattern at `profile_repository.py:397-482`):
```python
class BackstoryCacheRepository:
    def __init__(self, session: AsyncSession): ...

    async def get(self, cache_key: str) -> dict | None:
        """Query-time filter: WHERE cache_key=? AND expires_at > NOW().
        Returns envelope {scenarios: list[dict], venues_used: list[str]} on hit; None on miss/expired.
        Facade is responsible for `[BackstoryOption.model_validate(d) for d in envelope['scenarios']]`."""

    async def set(self, cache_key: str, envelope: dict, ttl_days: int) -> None:
        """UPSERT with ON CONFLICT (cache_key) DO UPDATE SET scenarios=excluded.scenarios,
        expires_at=NOW() + INTERVAL '<ttl_days> days'.
        Envelope shape: {scenarios: [opt.model_dump(mode='json') for opt in options], venues_used: [v.name for v in venues_list]}
        Facade serializes before calling."""
```

**Envelope rationale**: both `scenarios` (for BackstoryOption[]) and `venues_used` (for portal UI display) are needed on cache hit. Storing them together in one JSONB column avoids a second table query or a separate venue lookup on every cache hit. Matches the "keep repository layer simple with raw dicts; facade handles contract types" principle.

**Layering rationale**: `db/repositories/` returns ORM-level types (raw dicts for JSONB, ORM objects for tables) — never domain contracts. The facade in `services/portal_onboarding.py` performs serialization/deserialization. This matches existing `VenueCacheRepository.store(venues: list[dict])` precedent and avoids cross-layer imports of `nikita.onboarding.contracts` from `nikita.db.repositories`.

**TTL strategy**: query-time filter (`WHERE expires_at > NOW()`) — no background cleanup needed. Optional pg_cron job for storage hygiene only (not correctness).

### FR-13: Route File Decomposition
**Priority**: P1
**Description**: `nikita/api/routes/onboarding.py` is 34KB serving 5 concerns (voice initiate, status, server-tool, webhook, portal profile). Adding FR-5 `/pipeline-ready` and FR-9 `PATCH /profile` would push to 7 concerns.

**Action**: create NEW `nikita/api/routes/portal_onboarding.py` containing:
- `POST /api/v1/onboarding/profile` (move from existing `onboarding.py`)
- `PATCH /api/v1/onboarding/profile` (NEW per FR-9)
- `GET /api/v1/onboarding/pipeline-ready/{user_id}` (NEW per FR-5)

Existing voice-onboarding endpoints stay in `onboarding.py`. Both routers mounted under `/api/v1/onboarding/` prefix.

**Router definition** (top of new `nikita/api/routes/portal_onboarding.py` — NO `prefix=` argument to avoid double-prefix collision with `include_router` below):
```python
from fastapi import APIRouter
router = APIRouter(tags=["Portal Onboarding"])
```
(Matches existing `onboarding.py:43` pattern — prefix belongs to `include_router`, not `APIRouter()`.)

**Router registration** (`nikita/api/main.py`, after existing onboarding router mount at line ~265):
```python
from nikita.api.routes import portal_onboarding
app.include_router(
    portal_onboarding.router,
    prefix="/api/v1/onboarding",
    tags=["Portal Onboarding"],
)
```
Without this `include_router` call, the new route file exists but is unreachable.

### FR-14: Session-Scope Safety Pattern
**Priority**: P1
**Description**: Background tasks MUST NOT receive request-scoped `AsyncSession` or repository instances. Pattern (modeled at `handoff.py:579-583`):
```python
async def background_task_body(user_id: UUID, **kwargs):
    async with get_session_maker()() as session:  # fresh session
        repo = SomeRepository(session)
        # ... work
        await session.commit()

# Caller:
background_tasks.add_task(background_task_body, user_id=user_id)  # no session/repo passed
```

**Action**: refactor `_trigger_portal_handoff` at `onboarding.py:821-827` to follow this pattern. Ship as part of FR-13's route move (atomic refactor).

---

## User Stories

### US-1: New user completes portal onboarding with full profile
**As a** new user signing up via the portal
**I want to** provide my name, age, city, scene, occupation, life stage, interest, darkness level, and (optionally) phone
**So that** Nikita's first message feels personal and references things I told her about myself

**Acceptance Criteria**:
- [ ] AC-1.1: `POST /onboarding/profile` accepts `name`, `age`, `occupation` without 422 error (test: `tests/api/routes/test_portal_onboarding.py::test_post_accepts_new_fields`)
- [ ] AC-1.2: After submission, `users.onboarding_profile` JSONB contains all collected fields (test: integration via Supabase MCP read)
- [ ] AC-1.3: After submission, `user_profiles` row contains `name`, `occupation`, `age` columns populated (test: same integration)
- [ ] AC-1.4: Within 25 seconds of submission, the first Telegram message is received and contains at least 2 of {city, scene, occupation, name} (test: `tests/onboarding/test_e2e.py::test_full_profile_personalizes_first_message` marked `@pytest.mark.e2e` requiring Telegram MCP — NOT in unit CI gate)
- [ ] AC-1.5: The first message references a backstory scenario hook OR (on degraded path) uses generic-but-personalized opener; never falls back to "So we meet again..." (test: `tests/onboarding/test_handoff.py::TestFirstMessageGeneratorWithBackstory::test_no_meta_opener` regex-asserts result against `r"So we meet again"`)

**Priority**: P1

### US-2: Pipeline-readiness gate prevents premature interaction
**As a** new user who just submitted onboarding
**I want to** see a "Nikita is getting ready..." indicator
**So that** I don't message Nikita while her brain is still loading

**Acceptance Criteria**:
- [ ] AC-2.1: `GET /pipeline-ready/{user_id}` returns each `PipelineReadyState` value (test: `tests/api/routes/test_portal_onboarding.py::test_pipeline_ready_states` parametrized over 4 states; mock `user_repo.get.return_value.onboarding_profile = {"pipeline_state": state}`)
- [ ] AC-2.2: Polling at 2s interval reaches a terminal state in 100% of test runs (test: `tests/onboarding/test_pipeline_gate_integration.py::test_polling_terminates`; mock `AsyncMock(side_effect=[{"pipeline_state":"pending"}]*4 + [{"pipeline_state":"ready"}])` over 5 calls; assert loop exits at iteration ≤5; sibling test with `[{"pipeline_state":"failed"}]` for immediate-exit; 10 trials in pytest parametrize)
- [ ] AC-2.3: After 20s timeout (`PIPELINE_GATE_MAX_WAIT_S`), endpoint returns `state="degraded"` with `message` populated; do not block user indefinitely (test: same file, `test_max_wait_returns_degraded`)
- [ ] AC-2.4: Auth: user A querying user B's `/pipeline-ready/B` returns 403 with body `{"detail": "Not authorized"}` (test: `test_cross_user_403_with_correct_body`)

**Priority**: P1

### US-3: City research times out without breaking onboarding
**As a** user from an obscure city not in the Firecrawl cache
**I want to** still finish onboarding even if venue research times out
**So that** I'm not blocked by an external service issue

**Acceptance Criteria**:
- [ ] AC-3.1: With `VenueResearchService.research_venues` mocked to sleep 30s, `portal_onboarding.process(...)` returns within `VENUE_RESEARCH_TIMEOUT_S + 1s` (test: `tests/services/test_portal_onboarding_facade.py::test_venue_timeout`; uses `time.monotonic()` assertion)
- [ ] AC-3.2: On venue timeout, `caplog` contains record with `event="portal_handoff.venue_research"` AND `outcome="timeout"` AND `error_class="TimeoutError"` (test: same file)
- [ ] AC-3.3: First message still sends; uses scene-only flavor (test: `test_first_message_falls_back_to_scene_only`)
- [ ] AC-3.4: `pipeline_state` advances to `"degraded"` (not `"failed"`) — test: `caplog` and JSONB-read mock

**Priority**: P1

### US-4: Backstory generation fails gracefully
**As a** user
**I want to** still get a personalized first message even if Claude is rate-limited or down
**So that** the experience degrades, not breaks

**Acceptance Criteria**:
- [ ] AC-4.1: With `BackstoryGeneratorService.generate_scenarios` mocked to raise `RuntimeError`, `portal_onboarding.process(...)` returns `[]` (test: `test_backstory_failure_returns_empty`; patch `nikita.services.backstory_generator.BackstoryGeneratorService.generate_scenarios`)
- [ ] AC-4.2: First message uses default persona prompt (no scenario-specific) but still includes city/scene/occupation flavor (test: `test_first_message_keeps_flavor_on_backstory_fail`)
- [ ] AC-4.3: `caplog` contains `event="portal_handoff.backstory"` AND `outcome="failure"` AND `error_class="RuntimeError"` AND no PII (test: `test_backstory_failure_log_no_pii`)
- [ ] AC-4.4: `pipeline_state` advances to `"degraded"`

**Priority**: P1

### US-5: User replies with first-message verbatim, Nikita acknowledges
**As a** user testing if Nikita remembers what she said
**I want** Nikita to acknowledge her own prior turn when I quote it back
**So that** the experience feels coherent (not the broken "I never said that" bug)

**Acceptance Criteria**:
- [ ] AC-5.1: Given a seeded conversation with assistant turn `T`, user replies `f"You said: {T}"`, the pipeline run loads `T` into history (test: `tests/onboarding/test_r8_conversation_continuity.py::test_loads_seeded_turn`; mock `ConversationRepository.get` returning conv with `[T]`)
- [ ] AC-5.2: The text agent's prompt includes the prior assistant turn (test: same file, `test_agent_receives_history`; assert `mock_run.call_args.kwargs["messages"]` contains `{"role":"assistant","content":T}`)
- [ ] AC-5.3: The response does not contain denial phrases (`"I never said"`, `"you must be mistaken"`) — N=10 mocked runs (test: same file, `test_no_denial_phrases`; patch `nikita.agents.text.agent.NikitaAgent.run` with `AsyncMock(return_value=MagicMock(output="She seems interesting"))`; loop 10x; assert `re.search(r"I never said|you must be mistaken", out, re.IGNORECASE) is None`)
- [ ] AC-5.4: Independent from US-1 (test runs even if first-message generation produced generic opener)

**Priority**: P1

### US-6: Re-onboarding user resumes from last step
**As a** user who started onboarding, closed the tab, and returned next day
**I want to** resume from where I left off (not start over)
**So that** I don't lose progress

**Acceptance Criteria**:
- [ ] AC-6.1: User with `users.onboarding_profile = {"wizard_step": 5, "location_city": "Berlin", ...}` and `onboarding_status != "completed"` → backend PRESERVES `wizard_step` in JSONB without overwriting (test: `tests/api/routes/test_portal_onboarding.py::test_patch_preserves_wizard_step` asserts JSONB read after PATCH still contains `wizard_step=5`). Spec 214 reads this key and navigates to step 5 — portal navigation tested in Spec 214, NOT here. Backend does NOT echo `wizard_step` in `OnboardingV2ProfileResponse` (frozen contract).
- [ ] AC-6.2: `PATCH /onboarding/profile` accepts partial updates without resetting existing fields (test: `tests/api/routes/test_portal_onboarding.py::test_patch_merges_jsonb`)
- [ ] AC-6.3: Backend returns `field=None` for missing new fields in response (test: `test_patch_returns_null_for_unset_fields`)
- [ ] AC-6.4: On final submission, backstory cache hit if `cache_key` matches → no second Claude call (test: `tests/services/test_portal_onboarding_facade.py::test_cache_hit_skips_claude`)

**Priority**: P2

### US-7: Voice-first user routes correctly with full profile
**As a** user who provided phone during onboarding
**I want** the voice call to use my full profile (city, scene, occupation, backstory)
**So that** the voice agent feels as personalized as the text agent would

**Acceptance Criteria**:
- [ ] AC-7.1: User with phone → `_trigger_portal_handoff` calls `execute_handoff_with_voice_callback` (existing test: `tests/onboarding/test_handoff_phone_routing.py::TestVoiceBranch`)
- [ ] AC-7.2: The voice pre-call webhook receives `OnboardingV2ProfileResponse` containing all collected fields + chosen backstory option (test: `tests/api/routes/test_voice_pre_call_webhook.py::test_payload_includes_v2_profile_response`)
- [ ] AC-7.3: Voice agent's system prompt includes city/scene/occupation/backstory hooks (test: `tests/onboarding/test_handoff.py::TestFirstMessageGeneratorWithBackstory::test_voice_prompt_includes_backstory`; pass `BackstoryOption(unresolved_hook="Berghain eye contact", ...)` and assert `"Berghain"` in result when `BACKSTORY_HOOK_PROBABILITY` patched to 1.0; assert absent when patched to 0.0)
- [ ] AC-7.4: On voice-callback failure, fallback to Telegram first message (existing per Spec 212)

**Priority**: P2

---

## Non-Functional Requirements

### NFR-1: Performance
- `portal_onboarding.process(...)` p95 latency: ≤ `VENUE_RESEARCH_TIMEOUT_S + BACKSTORY_GEN_TIMEOUT_S + 5s` = 40s end-to-end (cold path)
- `/pipeline-ready` endpoint: p99 latency ≤ 200ms (single JSONB read)
- Backstory cache hit ratio target: ≥ 60% after 30 days of traffic on the top-10 city/scene combinations

### NFR-2: Cost
- `BackstoryGenerator` Claude cost ≤ $0.05 per unique profile shape (Haiku at $0.25/MTok input, ≤200 tokens prompt)
- `VenueResearchService` Firecrawl cost ≤ $0.02 per unique city
- Budget alert: >100 unique cities/day → log warning + investigate

### NFR-3: Observability
Structured log keys for every facade outcome (all values are server-side, emitted once per call):

| Event | Fields |
|---|---|
| `portal_handoff.venue_research` | `event, user_id, outcome, duration_ms, cache_hit, error_class` (outcome ∈ {`success`, `timeout`, `failure`, `cache_hit`}; `error_class: str \| None`) |
| `portal_handoff.backstory` | `event, user_id, outcome, duration_ms, cache_hit, scenario_count, error_class` (`scenario_count: int = len(scenarios)`) |
| `pipeline_bootstrap` | `event, user_id, outcome, pipeline_state` (outcome ∈ {`processed`, `skip_already_ready`, `skip_already_pending`, `failed`}) |
| `pipeline_ready.request` | `event, user_id, state, requesting_user_id` (server-side per request; client-side metrics like `attempts`/`total_wait_ms` are emitted by Spec 214's portal telemetry, NOT here) |

Cloud Run log query: `resource.labels.service_name="nikita-api" AND jsonPayload.event=~"portal_handoff|pipeline_(bootstrap|ready)"`

### NFR-4: Reliability
- All async service calls wrapped in `asyncio.wait_for(...)` with named timeout constants from FR-4
- All exception handlers use specific types (no bare `except Exception` at boundaries unless logging then re-raising)
- Pipeline bootstrap is idempotent (FR-11)
- Background tasks open fresh DB sessions (FR-14)

### NFR-5: Security / PII
- See FR-7

### NFR-6: Backwards Compatibility
- Existing voice-onboarded users continue without migration
- New nullable columns on `user_profiles` do not break existing rows
- `PortalProfileRequest` new fields are optional; old portal client (pre-Spec 214) continues to work
- `name` JSONB key with one-cycle fallback to `user_name` for in-flight users

### NFR-7: Coverage
- `nikita/onboarding/contracts.py` — 100% line coverage (frozen contract)
- `nikita/onboarding/tuning.py` — 100% line coverage (regression guards)
- `nikita/services/portal_onboarding.py` — ≥90% line + branch coverage
- `nikita/api/routes/portal_onboarding.py` — ≥85% line coverage
- `nikita/onboarding/adapters.py` — 100% line coverage

**CI command** for spec-related runs (split into 2 commands to enforce per-module thresholds):
```bash
# Strict 100% modules — fail-under separately
pytest --cov=nikita.onboarding.contracts --cov=nikita.onboarding.tuning \
       --cov=nikita.onboarding.adapters --cov-fail-under=100

# Mixed-threshold modules — use coverage config (pyproject.toml [tool.coverage.report] section)
pytest --cov=nikita.services.portal_onboarding \
       --cov=nikita.api.routes.portal_onboarding --cov-fail-under=85
```

Per-module enforcement above 85% requires `[tool.coverage.report]` config in `pyproject.toml`:
```toml
[tool.coverage.report]
fail_under = 85  # global floor
# Per-module 90% for portal_onboarding facade enforced via separate test step or coverage badge
```

Acceptable: combined `--cov-fail-under=85` with manual review of per-module coverage report. Strict per-file enforcement (90% for facade) is a Phase 9 polish, not a Phase 8 blocker.

---

## Test Strategy

### Test File Inventory (named in spec for TDD readiness)

| File | Purpose | Marker |
|---|---|---|
| `tests/onboarding/test_tuning_constants.py` | Regression guards on every constant in `tuning.py`. Compound constants (`AGE_BUCKETS` tuple-of-tuples, `OCCUPATION_CATEGORIES` dict) use deep-equality assertion AND explicit boundary tests (e.g., `assert age_to_bucket(24) == "young_adult"`, `assert age_to_bucket(25) == "twenties"` — verifies inclusive edges). Includes `test_compute_backstory_cache_key_signature` asserting function lives at `nikita.onboarding.tuning.compute_backstory_cache_key`. | unit |
| `tests/onboarding/test_contracts.py` | Pydantic validation of all 6 contract types | unit |
| `tests/onboarding/test_adapters.py` | `ProfileFromOnboardingProfile.from_pydantic` field mapping | unit |
| `tests/services/test_portal_onboarding_facade.py` | facade.process happy/timeout/failure/cache-hit + PII redaction caplog | integration (uses asyncio mocks) |
| `tests/services/test_backstory_cache_repository.py` | upsert + TTL filter + cache_key uniqueness | unit |
| `tests/api/routes/test_portal_onboarding.py` | POST + PATCH + GET pipeline-ready + 403/404 | integration (FastAPI TestClient) |
| `tests/onboarding/test_pipeline_gate_integration.py` | ASGI-level blocking gate (SC-2 end-to-end) | integration (ASGI transport) |
| `tests/onboarding/test_pipeline_bootstrap.py` | extend with `test_idempotent_double_call`, `test_writes_pipeline_state_*` | unit |
| `tests/onboarding/test_handoff.py` | extend with `TestFirstMessageGeneratorWithBackstory` | unit |
| `tests/onboarding/test_r8_conversation_continuity.py` | NEW — N=10 denial-phrase regex test | unit |
| `tests/onboarding/test_log_observability.py` | NEW — caplog assertions for all 4 NFR-3 events | unit |
| `tests/db/test_rls_user_profiles.py` | NEW — 5 RLS policies on new columns | integration (live Supabase) |
| `tests/onboarding/test_e2e.py` | extend `test_full_profile_personalizes_first_message` | e2e (Telegram MCP) |
| `tests/api/routes/test_voice_pre_call_webhook.py` | NEW — `test_payload_includes_v2_profile_response` (AC-7.2) verifies pre-call webhook receives `OnboardingV2ProfileResponse` shape | unit |
| `tests/services/test_portal_onboarding_facade.py` (extend) | `test_portal_onboarding_session_isolation` proves facade NEVER opens own session (FR-14 risk mitigation); calls facade with mocked session, asserts `get_session_maker` not invoked inside | unit |
| `tests/services/test_preview_backstory.py` (FR-4a facade unit tests) | `test_cache_key_stable` (same inputs → identical cache_key), `test_degraded_returns_empty` (backstory service failure → `degraded=True`, `scenarios=[]`, `venues_used=<venue_names>`) | unit |
| `tests/api/routes/test_preview_backstory_route.py` (FR-4a route integration) | `test_profile_post_reuses_cache` (cross-endpoint cache coherence: preview → POST profile reuses cache, no duplicate Claude call), `test_rate_limit` (6th call in 1min returns 429 with `Retry-After: 60`), `test_stateless_no_jsonb_write` (preview does NOT mutate users.onboarding_profile) | integration (FastAPI TestClient) |

### Test Pyramid Target
- Unit (~70%): tuning constants, contracts validation, adapters, FirstMessageGenerator branches
- Integration (~25%): facade with mocks, pipeline gate ASGI, RLS
- E2E (~5%): full profile → first message via Telegram MCP

### Patch Convention
Per `.claude/rules/testing.md` patch-source-module rule: patch at source module, not importer. Examples:
- `patch("nikita.services.venue_research.VenueResearchService.research_venues", ...)`
- `patch("nikita.services.backstory_generator.BackstoryGeneratorService.generate_scenarios", ...)`
- `patch("nikita.agents.text.agent.NikitaAgent.run", new_callable=AsyncMock)`

### Non-Empty Fixture Compliance
Every test mocking a query result MUST provide at least one non-empty path. AC-2.2 explicitly lists `side_effect=[...]` to avoid vacuous-pass. FR-11 idempotence test uses `side_effect=[state_none, state_ready]` (NOT `return_value=None`).

---

## Constraints & Assumptions

- Cloud Run scale-to-zero: cold starts add up to 5s — measured with `gcloud run services describe`
- Firecrawl + Claude API keys available in environment (already configured for Telegram path)
- Supabase RLS already enforced on `user_profiles` (verified)
- Pydantic `UserOnboardingProfile` already has `occupation` (`models.py:87`) AND `age` (`models.py:122`) fields — only `name` is net-new
- `BackstoryGeneratorService.generate_scenarios` accepts `UserProfile` ORM-shape — adapter required (FR-3.1)
- `users.onboarding_completed_at` column DOES NOT exist (verified via Supabase MCP); FR-9 uses existing `onboarding_status` field instead
- PR #277 (recovery) is the basis for this spec — assumes `_seed_conversation`, `build_profile_from_jsonb`, JSONB persistence, voice-path bootstrap are all on master
- Migration naming convention: `YYYYMMDDHHMMSS_name` (project standard, latest: `20260409185138`)
- Existing `_ProfileFromAnswers` adapter at `nikita/platforms/telegram/onboarding/handler.py:41-56` will be promoted

---

## Out of Scope

- Portal UI changes — owned by Spec 214
- Voice agent prompt template structural changes beyond consuming new contracts
- New analytics dashboards for backstory adoption
- A/B testing of backstory personalization vs generic
- Migration of existing voice-onboarded users to populate `name`/`age`/`occupation` retroactively (will prompt on next portal visit if missing)
- Multi-language support for backstory scenarios (English only)
- `wizard_step` JSONB key WRITE — owned by Spec 214 (this spec only documents that the backend reads it for resume detection)
- Background pg_cron cleanup of expired BackstoryCache rows — query-time filter is sufficient; cleanup is hygiene-only

(PII exception-echo fixes at `onboarding.py:154` and `:239` ARE in scope — see FR-7 + Implementation Notes. Previously listed here in error; removed iter-4.)

---

## Open Questions

(All questions resolved — zero `[NEEDS CLARIFICATION]` markers)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `BackstoryGenerator` Claude rate-limit on launch day | Medium | High | 30-day cache; backstory degraded path; circuit-breaker pattern wraps Claude calls |
| `VenueResearchService` Firecrawl auth failure | Low | High | 30-day cache; fallback to scene-only first message; alert on 5xx rate >10% |
| Pydantic vs ORM type confusion in facade | Low | High | Promoted shared adapter (FR-3.1); single source of truth |
| `OnboardingV2ProfileRequest` contract churn delays Spec 214 | Medium | High | Ship contracts.py in PR #1; mark frozen; require ADR for any change |
| PII leak in exception echoes | Medium | High | FR-7 + log redaction unit tests + `rg` audit; pre-existing fixed in Phase 8 |
| Pipeline gate timeout (20s) too short for slow Claude | Low | Medium | NFR-1 budget includes margin; observability surfaces real p95 |
| Bug in facade leaks ORM session across requests | Low | Critical | FR-14 explicit pattern; integration test `test_portal_onboarding_session_isolation` |
| `pipeline_state` JSONB write race condition (concurrent bootstrap) | Low | Medium | FR-11 idempotence + `jsonb_set` atomic merge per FR-5.2 |
| BackstoryCache table grows unbounded | Low | Low | TTL via query-time filter; optional pg_cron cleanup as hygiene |
| Migration ordering conflict with existing `YYYYMMDDHHMMSS_*` files | Low | Low | Use timestamp at PR creation time; verify ordering manually |

---

## Implementation Notes (for plan.md)

- 5-PR decomposition target (each ≤400 LOC):
  - **PR 213-1**: `contracts.py` + `tuning.py` + adapter + tests (frozen contract surface for Spec 214 to begin)
  - **PR 213-2**: Migration (user_profiles columns + backstory_cache table) + ORM additions + repository
  - **PR 213-3**: facade `portal_onboarding.py` + `_trigger_portal_handoff` rewire + tests (FR-3, FR-7, NFR-3)
  - **PR 213-4**: route file `portal_onboarding.py` + `/pipeline-ready` + `PATCH /profile` + FR-14 session pattern
  - **PR 213-5**: FirstMessageGenerator FR-6 + R8 regression test + e2e + ROADMAP sync to COMPLETE
- TDD: tests committed BEFORE implementation per Article IX
- Authoritative PR mapping for in-scope fixes:
  - FR-7 PII fixes at `nikita/api/routes/onboarding.py:154, :239` — **in scope, PR 213-3**
  - FR-7 RLS DDL (WITH CHECK on UPDATE, subquery form on DELETE) — **in scope, PR 213-2**
  - NO Phase-8/out-of-scope deferral exists for these fixes (per absolute-zero policy). Any prior "out of spec" reference in this document is stale and must be ignored.

---

## Quality Gates (Self-Check)

- [x] FR Coverage: 14 functional requirements (>= 3)
- [x] AC Minimum: each user story has ≥4 ACs (>= 2)
- [x] Testability: every AC names a test file + assertion type
- [x] No Ambiguity: 0 [NEEDS CLARIFICATION] markers
- [x] Article I (Intelligence-First): plan-rewrite + sub-research + 6 validators in iteration 1
- [x] Article III (Test-First): all ACs name test files; FR-8, US-5 explicitly require tests-first
- [x] Article IV (Spec-First): this is the spec; plan.md follows
- [x] Iteration 1 validator findings: all 60 addressed in this rewrite (CRITICAL fixes via FR-1c/d, FR-5.1, FR-12, FR-2 contract bodies; HIGH fixes via FR-3.1 adapter, FR-13 route split, FR-14 session pattern; MEDIUM/LOW fixes via test file naming, coverage thresholds, log schema, migration naming)
