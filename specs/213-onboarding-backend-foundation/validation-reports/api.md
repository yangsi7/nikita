# API Validation Report — Spec 213

**Spec**: `specs/213-onboarding-backend-foundation/spec.md`
**Status**: FAIL (iteration 2)
**Timestamp**: 2026-04-14T17:30:00Z
**Validator**: sdd-api-validator

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 2 |

**Iteration 1 recap**: All 3 CRITICAL + 6 HIGH + 4 MEDIUM + 2 LOW from iteration 1 are RESOLVED in this revision. The findings below are NEW gaps introduced by the iteration-2 rewrite (particularly FR-3 and FR-12).

---

## Critical Findings

| ID | Category | Issue | Location | Recommendation |
|---|---|---|---|---|
| A-C1 | Response Schema | `BackstoryScenario → BackstoryOption` conversion completely unspecified: `generate_scenarios()` returns `BackstoryScenariosResult` (containing `list[BackstoryScenario]` dataclass, which has NO `id` field), but the facade's return type is `list[BackstoryOption]` (Pydantic, requires `id: str`). No conversion step, no `id` generation formula, and no tone validation (`BackstoryScenario.tone` is `str`; `BackstoryOption.tone` is `Literal["romantic","intellectual","chaotic"]`) are specified anywhere in the spec. | spec.md:168-181 (FR-3 step 5), backstory_generator.py:28-39 | Add a conversion function to FR-3 (or FR-12): `def _scenario_to_option(cache_key: str, index: int, s: BackstoryScenario) -> BackstoryOption: return BackstoryOption(id=hashlib.sha256(f"{cache_key}:{index}".encode()).hexdigest()[:12], venue=s.venue, context=s.context, the_moment=s.the_moment, unresolved_hook=s.unresolved_hook, tone=s.tone)` — define this in `portal_onboarding.py` and specify the id-generation formula explicitly. Also specify that `tone` from the LLM must match the Literal; add a fallback or validation step if LLM returns unexpected value. |

---

## High Findings

| ID | Category | Issue | Location | Recommendation |
|---|---|---|---|---|
| A-H1 | Request Schema | `VenueResearchResult.venues` not unpacked in facade. FR-3 step 5 says: `await asyncio.wait_for(venue_service.research_venues(profile.city, profile.social_scene), ...)`, then passes the result as `venues` to `generate_scenarios(orm_profile, venues)`. But `research_venues()` returns `VenueResearchResult` (a dataclass with `.venues: list[Venue]` and `.fallback_used: bool`), NOT `list[Venue]`. `generate_scenarios(orm_profile, venues)` expects `list[Venue]` (actual signature at `backstory_generator.py:81`). Without unpacking, this produces a `TypeError` at runtime. Mocked unit tests will pass silently. | spec.md:177-179 (FR-3 step 5), venue_research.py:79-83, backstory_generator.py:81-85 | Fix FR-3 step 5 to read: "Assign result to `venue_result = await asyncio.wait_for(...)`. On success, extract `venues = venue_result.venues` and pass to backstory step. If `venue_result.fallback_used`, skip backstory generation and return `[]` (or proceed with empty venues — specify which)." |
| A-H2 | Routes | `compute_backstory_cache_key` function called in FR-3 step 3 but never defined: no module path, no function signature, no cache key format string. The function uses `AGE_BUCKETS` and `OCCUPATION_CATEGORIES` from `tuning.py` but the bucketing algorithm (how to construct the final key string from city + scene + bucketed age + bucketed occupation) is unspecified. Without this, two implementors will produce incompatible cache keys, making the cache ineffective. | spec.md:174 (FR-3 step 3) | Add a concrete definition in FR-3 or FR-4: `def compute_backstory_cache_key(profile: UserOnboardingProfile) -> str` — specify key format as `f"{profile.city.lower()}:{profile.social_scene}:{_age_bucket(profile.age)}:{_occupation_bucket(profile.occupation)}"` (or equivalent) and place this function in `portal_onboarding.py` with helpers `_age_bucket(age) -> str` and `_occupation_bucket(occ) -> str`. List the module path explicitly. |

---

## Medium Findings

| ID | Severity | Issue | Location | Recommendation |
|---|---|---|---|---|
| A-M1 | MEDIUM | `BackstoryCacheRepository.get()` deserialization contract unspecified. ORM column `scenarios: Mapped[list[dict]]` stores raw JSONB. The return type signature says `list[BackstoryOption] | None`, but no serialization/deserialization step is documented (e.g., `[BackstoryOption(**d) for d in row.scenarios]` on read, `.model_dump(mode="json")` on write). Same gap for `set()`. Implementors will correctly guess this, but inconsistency in how `id` field roundtrips (BackstoryOption.id stored in JSONB, retrieved correctly) needs to be explicit given that id generation depends on `cache_key + index`. | spec.md:423-432 (FR-12 repository) | Add to FR-12 repository section: "On `get()`: deserialize via `[BackstoryOption.model_validate(d) for d in row.scenarios]`. On `set()`: serialize via `[o.model_dump(mode='json') for o in scenarios]`. The `id` field is stored verbatim; do not regenerate on retrieval." |
| A-M2 | MEDIUM | `chosen_option` in `OnboardingV2ProfileResponse` is described as "null until user picks" but no backend endpoint or mechanism exists to set it. The spec defines `POST /onboarding/profile`, `PATCH /onboarding/profile`, and `GET /pipeline-ready/{user_id}` — none of which accept a backstory choice. If this field is always `null` from the backend, its presence in the response contract is misleading. If the write mechanism is owned by Spec 214, the spec should say so explicitly. | spec.md:138 | Add a note: "The `chosen_option` field is always `null` in responses from this spec's endpoints. Spec 214 is responsible for defining the backstory selection endpoint (e.g., `POST /onboarding/backstory-choice`) that persists the user's pick and returns the updated `OnboardingV2ProfileResponse` with `chosen_option` populated." |

---

## Low Findings

| ID | Severity | Issue | Location | Recommendation |
|---|---|---|---|---|
| A-L1 | LOW | FR-13 states "Both routers mounted under `/api/v1/onboarding/` prefix" but does not specify the `include_router` addition to `nikita/api/main.py`. The new `portal_onboarding.router` needs a concrete `app.include_router(portal_onboarding.router, prefix="/api/v1/onboarding", tags=["Portal Onboarding"])` call. | spec.md:445 | Add to FR-13: "In `nikita/api/main.py`, after the existing onboarding router mount at line 265-269, add: `from nikita.api.routes import portal_onboarding; app.include_router(portal_onboarding.router, prefix='/api/v1/onboarding', tags=['Portal Onboarding'])`." |
| A-L2 | LOW | FR-5.2 code snippet uses `func`, `cast`, `JSONB`, and `update` without specifying the required SQLAlchemy imports. The repository file currently imports only `select` from `sqlalchemy` (user_repository.py:12). Implementors must add: `from sqlalchemy import func, cast, update` and `from sqlalchemy.dialects.postgresql import JSONB`. | spec.md:311-320 (FR-5.2) | Add import list to FR-5.2: "Required imports: `from sqlalchemy import func, cast, update` and `from sqlalchemy.dialects.postgresql import JSONB`." |

---

## Iteration 1 Finding Resolution Status

All 15 iteration-1 findings are confirmed RESOLVED:

| ID | Status | Evidence |
|---|---|---|
| A-C1 (PortalProfileRequest constraints) | RESOLVED | FR-1d lines 87-93: full Field constraints for name/age/occupation |
| A-C2 (contract types bodies missing) | RESOLVED | FR-2 lines 101-156: all 6 Pydantic class bodies with field-level constraints |
| A-C3 (pipeline_state write path) | RESOLVED | FR-5.1 lines 296-307: 5-transition table + `update_onboarding_profile_key` call |
| A-H1 (403/404 body shapes) | RESOLVED | FR-5 line 280: explicit body strings for 403 and 404 |
| A-H2 (adapter not specified) | RESOLVED | FR-3.1 lines 189-212: `ProfileFromOnboardingProfile` class + field mapping |
| A-H3 (VenueResearchService injection) | RESOLVED | FR-3 step 1 lines 171-172: `VenueCacheRepository(session)` → `VenueResearchService(venue_cache_repository=repo)` |
| A-H4 (pipeline_state write missing) | RESOLVED | Covered by FR-5.1 |
| A-H5 (log schema error_class missing) | RESOLVED | FR-3 logging spec line 184 + NFR-3 table line 578: `error_class: str | None` in both events |
| A-H6 (name vs user_name ambiguity) | RESOLVED | FR-1e lines 95: canonical key = `"name"`, fallback to `"user_name"`, update sites named |
| A-M1 (no poll_interval_s in response) | RESOLVED | `OnboardingV2ProfileResponse` includes `poll_interval_seconds` + `poll_max_wait_seconds` |
| A-M2 (pipeline_ready.poll log ambiguity) | RESOLVED | NFR-3 line 581 explicitly scopes client-side metrics to Spec 214 |
| A-M3 (bucketing before key construction) | RESOLVED | FR-3 step 3 line 174: bucketing applied before key |
| A-M4 (404 for unknown user_id) | RESOLVED | FR-5 line 280 |
| A-L1 (FirstMessageGenerator signature) | RESOLVED | FR-6 lines 330-336: new keyword-only param signature |
| A-L2 (BACKSTORY_HOOK_PROBABILITY) | RESOLVED | tuning.py lines 244-247 |

---

## API Inventory

| Method | Endpoint | Purpose | Auth | Request | Response |
|---|---|---|---|---|---|
| POST | `/api/v1/onboarding/profile` | Save portal profile + trigger pipeline | User JWT | `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` |
| PATCH | `/api/v1/onboarding/profile` | Partial profile update for resume | User JWT | partial `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` |
| GET | `/api/v1/onboarding/pipeline-ready/{user_id}` | Poll pipeline readiness | User JWT (own only) | — | `PipelineReadyResponse` |

### Error Codes

| Status | Body | Trigger |
|---|---|---|
| 403 | `{"detail": "Not authorized"}` | Cross-user pipeline-ready access |
| 404 | `{"detail": "User not found"}` | Unknown user_id on pipeline-ready |
| 422 | FastAPI validation error | Invalid request body |

---

## Contract Module Inventory (FR-2)

All 6 types confirmed fully defined in spec:

| Type | Module | Status |
|---|---|---|
| `PipelineReadyState` | `nikita.onboarding.contracts` | Defined (Literal) |
| `BackstoryOption` | `nikita.onboarding.contracts` | Defined (5 fields + tone Literal) — conversion from `BackstoryScenario` missing (A-C1) |
| `OnboardingV2ProfileRequest` | `nikita.onboarding.contracts` | Defined (10 fields with constraints) |
| `OnboardingV2ProfileResponse` | `nikita.onboarding.contracts` | Defined (7 fields) — `chosen_option` write path deferred (A-M2) |
| `PipelineReadyResponse` | `nikita.onboarding.contracts` | Defined (3 fields) |
| `ErrorResponse` | `nikita.onboarding.contracts` | Defined (1 field, matches existing pattern) |

---

## Verdict

**FAIL** — 1 CRITICAL + 2 HIGH block implementation. Per CLAUDE.md SDD rule 7: fix spec + re-validate (iteration 3 of max 3).

**Priority fixes required before iteration 3**:

1. **(A-C1 — CRITICAL)** Add `BackstoryScenario → BackstoryOption` conversion function to FR-3, including `id` generation formula and `tone` validation strategy.
2. **(A-H1 — HIGH)** Fix FR-3 step 5 to explicitly unpack `venue_result.venues` from `VenueResearchResult` and specify behavior when `fallback_used=True`.
3. **(A-H2 — HIGH)** Define `compute_backstory_cache_key` function: module path, signature, and key format string.
