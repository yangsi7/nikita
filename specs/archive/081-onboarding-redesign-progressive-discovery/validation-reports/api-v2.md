## API Validation Report

**Spec:** specs/081-onboarding-redesign-progressive-discovery/spec.md (v2)
**Status:** FAIL
**Timestamp:** 2026-03-22T14:00:00Z
**Validator:** sdd-api-validator

### Summary
- CRITICAL: 3
- HIGH: 6
- MEDIUM: 4
- LOW: 2

---

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | CRITICAL | Routes | Spec calls `complete_onboarding(user_id)` with 1 arg but actual method signature is `complete_onboarding(user_id, call_id, profile)` requiring 3 args | spec.md:1362, user_repository.py:579-583 | Either (a) add a new `complete_portal_onboarding(user_id)` method that only needs user_id, or (b) update spec to call `update_onboarding_status(user_id, "completed")` which already handles setting `onboarded_at` |
| 2 | CRITICAL | Routes | Spec calls `profile_repo.upsert(user_id, location_city, social_scene, drug_tolerance)` but `ProfileRepository` has no `upsert()` method -- only `create_profile()` and `update_from_onboarding()` | spec.md:1354-1358, profile_repository.py:31-94 | Define a new `upsert()` method in `ProfileRepository` or rewrite the spec to use existing `create_profile()` with a pre-check via `get_by_user_id()` + update pattern |
| 3 | CRITICAL | Routes | Spec calls `VenueResearchService().research(user_id, city, scene)` but actual method is `research_venues(self, city, scene)` -- wrong method name and wrong argument list (no `user_id` param, no constructor args) | spec.md:1370-1372, venue_research.py:79-83 | Fix spec to: (a) instantiate `VenueResearchService(session)` with a DB session, (b) call `research_venues(city, scene)` instead of `research(user_id, city, scene)` |
| 4 | HIGH | Routes | Spec says to add file `nikita/api/routes/onboarding.py` as new but this file already exists with 583 lines of voice onboarding endpoints (Spec 028). Adding a new router with `prefix="/onboarding"` in the spec code (line 1325) conflicts with the existing router already mounted at `/api/v1/onboarding` | spec.md:1313, 1325, 1379 vs onboarding.py (existing) | Add the new `/profile` endpoint to the EXISTING `onboarding.py` router rather than creating a new file. Or create a separate `onboarding_portal.py` and mount at a distinct prefix |
| 5 | HIGH | Schemas | `onboarding_completed_at` column does not exist in User model or DB. The model has `onboarded_at` (user.py:118). Spec references `onboarding_completed_at` throughout (FR-004 step 4, FR-006, FR-007, DB changes, stats response, fallback logic) | spec.md:202, 228, 236, 1450-1468, user.py:118 | Decide: either (a) add a NEW `onboarding_completed_at` column as specified (different semantic from `onboarded_at`) and clarify the distinction, or (b) reuse existing `onboarded_at` and update all spec references to `onboarded_at` |
| 6 | HIGH | Schemas | `UserStatsResponse` in `schemas/portal.py` does not include `onboarding_completed_at` or `welcome_completed`. Spec says to add them (lines 1556-1580) but the current schema (portal.py:27-41) has neither field | spec.md:1556-1580, schemas/portal.py:27-41 | This is a required schema change. Spec correctly identifies the gap but the portal `page.tsx` code (spec.md:1234-1237) depends on `stats.onboarding_completed_at` existing in the response. Must be implemented together |
| 7 | HIGH | Routes | Spec imports `from nikita.db.session import get_session_maker` in `_schedule_onboarding_fallback()` but no module `nikita.db.session` exists. The correct import is `from nikita.db.database import get_session_maker` | spec.md:1413 | Fix import to `from nikita.db.database import get_session_maker` |
| 8 | HIGH | Routes | `EventType` enum has 4 values: `MESSAGE_DELIVERY`, `CALL_REMINDER`, `BOSS_PROMPT`, `FOLLOW_UP`. Spec uses `event_type="onboarding_fallback"` which is not in the enum. While `create_event()` accepts `str`, a new enum value should be added for type safety | spec.md:1424, scheduled_event.py:42-48 | Add `ONBOARDING_FALLBACK = "onboarding_fallback"` to `EventType` enum. The `create_event()` method extracts `.value` from enums, so using the string directly works but misses validation |
| 9 | HIGH | Routes | Spec uses sync `create_client()` from `supabase` library inside `_generate_portal_magic_link()` (an async method). The sync Supabase client blocks the event loop. Also, `admin.get_user_by_id()` and `admin.generate_link()` are called synchronously | spec.md:1179-1199 | Use `create_async_client()` from `supabase` or wrap sync calls in `asyncio.to_thread()`. The existing `TelegramAuth` uses the async supabase client pattern -- reuse that |
| 10 | MEDIUM | Errors | `POST /api/v1/onboarding/profile` error responses are listed (400, 401, 500) but no standardized error response schema is defined. The spec returns raw HTTPException detail strings. Other endpoints in this file use `ErrorResponse(detail=str)` model | spec.md:1336-1377, 1551-1554 | Add `responses={400: {"model": ErrorResponse}, 401: ...}` decorator to the endpoint definition, matching the existing pattern in onboarding.py |
| 11 | MEDIUM | Routes | `_schedule_onboarding_fallback()` passes `user_id` as `str` to `create_event()` but the `ScheduledEventRepository.create_event()` expects `user_id: UUID`. The OTP handler has `user_id: str` from the caller | spec.md:1405, 1421 | Cast to UUID: `user_id=UUID(user_id)` in the call to `create_event()` |
| 12 | MEDIUM | Caching | No `Cache-Control` or caching strategy specified for `POST /api/v1/onboarding/profile`. The portal Server Component fetches stats with `cache: "no-store"` which is correct, but the profile POST response should explicitly include `Cache-Control: no-store` | spec.md:1336 | Add `no-store` cache header to profile response. This is a POST so browsers won't cache, but proxies might without explicit headers |
| 13 | MEDIUM | Routes | Spec says `BackstoryGeneratorService.generate()` is called as fire-and-forget (FR-004 step 6, line 204) but the actual code in the Technical Architecture section (lines 1366-1374) only calls `VenueResearchService`. The `BackstoryGeneratorService.generate()` call is missing from the implementation code | spec.md:204 vs 1366-1374 | Add `BackstoryGeneratorService` fire-and-forget call to the profile endpoint implementation, matching FR-004 step 6 |
| 14 | LOW | Routes | The fallback event handler logic (checking `onboarding_completed_at` and triggering `OnboardingHandler.start()`) is described in prose (spec.md:1436-1438) but no code is provided for the event delivery handler that processes `onboarding_fallback` events. The `deliver` pg_cron job needs to know how to handle this new event type | spec.md:1436-1438 | Add implementation code or clear pseudocode for the `onboarding_fallback` event handler in the deliver task, showing how it checks the completion flag and triggers text onboarding |
| 15 | LOW | Routes | The spec defines `router = APIRouter(prefix="/onboarding", tags=["onboarding"])` with a prefix (line 1325), but the existing pattern in `main.py` is to mount routers with prefix at `include_router` time (line 257: `prefix="/api/v1/onboarding"`). Having prefix on both the router and the mount would create `/api/v1/onboarding/onboarding/profile` | spec.md:1325 vs main.py:255-258 | Remove `prefix="/onboarding"` from the APIRouter constructor since it is already applied at mount time. Or, if creating a new router, mount without prefix overlap |

---

### API Inventory

| Method | Endpoint | Purpose | Auth | Request Schema | Response Schema | Status |
|--------|----------|---------|------|----------------|-----------------|--------|
| POST | /api/v1/onboarding/profile | Save profile from portal cinematic onboarding | JWT (get_current_user_id) | OnboardingProfileRequest | `{"status": "ok", "user_id": "..."}` | NEW |
| GET | /api/v1/portal/stats | Dashboard stats (modified) | JWT | None | UserStatsResponse + 2 new fields | MODIFIED |
| PUT | /api/v1/portal/settings | Update settings (modified) | JWT | UpdateSettingsRequest + welcome_completed | Settings response | MODIFIED |
| GET | /api/v1/onboarding/status/{user_id} | Check onboarding status | None (existing) | Path: user_id | OnboardingStatusResponse | EXISTING (unchanged) |
| POST | /api/v1/onboarding/initiate/{user_id} | Initiate voice onboarding call | None (existing) | InitiateOnboardingRequest | InitiateOnboardingResponse | EXISTING (unchanged) |
| POST | /api/v1/onboarding/server-tool | ElevenLabs server tool handler | Signature | OnboardingToolRequest | OnboardingToolResponse | EXISTING (unchanged) |
| POST | /api/v1/onboarding/webhook | ElevenLabs webhook | Signature | Raw body | `{"status": "ok"}` | EXISTING (unchanged) |
| POST | /api/v1/onboarding/pre-call | Pre-call webhook | None | Raw body | Dynamic variables | EXISTING (unchanged) |
| POST | /api/v1/onboarding/call/{user_id} | Initiate outbound call | None | None | Call result dict | EXISTING (unchanged) |
| POST | /api/v1/onboarding/skip/{user_id} | Skip onboarding | None | None | OnboardingStatusResponse | EXISTING (unchanged) |

### Server Actions

No Next.js Server Actions are introduced. The portal uses client-side `fetch()` to the backend API.

| Action | Purpose | Form Binding | Revalidation |
|--------|---------|--------------|-------------|
| N/A | Profile is submitted via client-side fetch to /api/v1/onboarding/profile | No | No |

### Request/Response Schemas

#### OnboardingProfileRequest (NEW)

```python
class OnboardingProfileRequest(BaseModel):
    location_city: str = Field(..., min_length=1, max_length=100)
    social_scene: str = Field(...)  # Must be in {"techno", "art", "food", "cocktails", "nature"}
    drug_tolerance: int = Field(..., ge=1, le=5)
```

Validation: Pydantic enforces min_length, max_length, ge, le. Custom validation for `social_scene` membership via endpoint logic (not Pydantic validator).

**Gap**: `social_scene` should use a Pydantic `Literal` type or a custom validator instead of checking in endpoint logic:
```python
social_scene: Literal["techno", "art", "food", "cocktails", "nature"] = Field(...)
```

#### Profile endpoint success response (NEW, untyped)

```json
{"status": "ok", "user_id": "uuid-string"}
```

**Gap**: No Pydantic response model defined. Should add:
```python
class OnboardingProfileResponse(BaseModel):
    status: str
    user_id: str
```

#### UserStatsResponse modifications (EXISTING, needs update)

Current schema (portal.py:27-41) needs two new fields:
```python
onboarding_completed_at: datetime | None = None
welcome_completed: bool = False
```

### Error Code Inventory

| Code | Status | Description | User Message | Location |
|------|--------|-------------|-------------|----------|
| VALIDATION_ERROR | 400 | Invalid scene value | `"Invalid scene. Must be one of: {VALID_SCENES}"` | spec.md:1348 |
| VALIDATION_ERROR | 400 | Empty location / drug_tolerance out of range | Pydantic auto-generated | Pydantic |
| AUTH_ERROR | 401 | No valid JWT | FastAPI default 401 | get_current_user_id dependency |
| SERVER_ERROR | 500 | Database error | HTTPException detail | spec.md:1554 |

---

### Recommendations

#### CRITICAL (must fix before implementation)

1. **CRITICAL #1 -- `complete_onboarding()` signature mismatch**: The existing `UserRepository.complete_onboarding(user_id, call_id, profile)` requires a `call_id` (ElevenLabs call ID) and a `profile` dict. The portal flow has neither. Recommended fix: add a new method `complete_portal_onboarding(user_id: UUID)` that sets `onboarding_status = "completed"` and `onboarded_at = now()` without requiring voice-specific fields. Alternatively, use the existing `update_onboarding_status(user_id, "completed")` which already sets `onboarded_at` when status is "completed" (user_repository.py:538-539).

2. **CRITICAL #2 -- `ProfileRepository.upsert()` does not exist**: The repository has `create_profile()` and `update_from_onboarding()` but no `upsert()`. The spec's idempotency requirement (FR-004 line 206) needs an upsert. Recommended fix: add an `upsert()` method using PostgreSQL `INSERT ... ON CONFLICT (id) DO UPDATE` via SQLAlchemy `insert().on_conflict_do_update()`. Or use `get_by_user_id()` + conditional `create_profile()` / `update()`.

3. **CRITICAL #3 -- `VenueResearchService` wrong method name and signature**: The spec calls `.research(user_id, city, scene)` but the actual method is `.research_venues(city, scene)` with no `user_id` parameter. Additionally, `VenueResearchService()` may require a session parameter for DB access. Verify constructor and fix spec to match actual API.

#### HIGH (must fix before implementation)

4. **HIGH #4 -- Existing `onboarding.py` conflict**: The file already exists with 6 endpoints. The spec must clarify whether the new `/profile` endpoint is added to the existing file or a new file is created. If added to existing file, remove the `APIRouter(prefix=...)` from the spec code since the mount prefix is already set in `main.py`.

5. **HIGH #5 -- `onboarding_completed_at` vs `onboarded_at`**: The User model has `onboarded_at` (set by `update_onboarding_status` and `complete_onboarding`). The spec introduces a separate `onboarding_completed_at`. Clarify: are these different columns with different semantics (voice completion vs portal completion), or should the spec reuse `onboarded_at`? If separate, explain when each is set.

6. **HIGH #6 -- Stats response schema update**: The `UserStatsResponse` needs `onboarding_completed_at` and `welcome_completed` fields added. The portal Server Component depends on this for the redirect check. Include the portal route handler (`routes/portal.py`) update to populate these fields from the User model.

7. **HIGH #7 -- Wrong import path**: Fix `from nikita.db.session import get_session_maker` to `from nikita.db.database import get_session_maker`.

8. **HIGH #8 -- Missing `EventType` enum value**: Add `ONBOARDING_FALLBACK = "onboarding_fallback"` to the `EventType` enum to maintain type safety consistency with existing event types.

9. **HIGH #9 -- Sync Supabase client in async context**: The `_generate_portal_magic_link()` uses synchronous `create_client()` and synchronous admin API calls inside an async method. This blocks the event loop. Use `create_async_client()` or wrap in `asyncio.to_thread()`.

#### MEDIUM

10. Add `responses={}` decorator with `ErrorResponse` model to the profile endpoint (consistency with existing onboarding endpoints).
11. Cast `user_id` from `str` to `UUID` when calling `create_event()`.
12. Add explicit `Cache-Control: no-store` to profile POST response.
13. Add `BackstoryGeneratorService.generate()` fire-and-forget call to match FR-004 step 6.

#### LOW

14. Provide implementation code for the `onboarding_fallback` event handler in the deliver task.
15. Remove duplicate `prefix="/onboarding"` from `APIRouter()` constructor to avoid double-prefix bug.

---

### Positive Patterns

- **Pydantic validation on request body**: `OnboardingProfileRequest` uses `Field()` constraints (min_length, max_length, ge, le) -- good practice.
- **Fire-and-forget for non-critical async work**: Venue research and scenario generation do not block the response -- correct architecture.
- **JWT auth via existing dependency**: Reuses `get_current_user_id` from `dependencies/auth.py` -- no new auth mechanism.
- **Idempotency consideration**: FR-004 explicitly calls out upsert behavior for repeated submissions.
- **Fallback strategy**: 5-minute timeout with text onboarding fallback ensures no player is stuck.
- **Magic link failure isolation**: Falls back to regular portal URL -- never blocks OTP success flow.
- **Comprehensive error isolation**: NFR-005 explicitly documents failure modes for all async operations.
