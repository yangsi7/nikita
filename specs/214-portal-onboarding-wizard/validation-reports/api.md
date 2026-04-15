## API Validation Report

**Spec:** specs/214-portal-onboarding-wizard/spec.md
**Status:** PASS
**Timestamp:** 2026-04-15T00:00:00Z
**Iteration:** 6 (re-validation after iter-5 fix commit fac2936)

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

---

### Iter-5 Fix Verification

The iter-5 HIGH finding is **fully resolved**. All three locations now consistently describe the correct data source and attribute bridge.

| Location | Fix Status |
|----------|-----------|
| spec.md:337–363 (facade docstring) | CORRECT (fixed in iter-4, commit 8301d97) |
| spec.md:315 (Semantics bullet) | FIXED in iter-5, commit fac2936 |
| spec.md:483 (AC-10.3) | FIXED in iter-5, commit fac2936 |

**Line 315 now reads**: "Ownership is inferred by recomputing `cache_key` from the authenticated user's `users.onboarding_profile` JSONB (NOT `user_profiles` table — portal wizard writes to `onboarding_profile` via PATCH; `user_profiles` is voice-onboarding scope only). Load via `UserRepository(session).get(user_id)`, then build a `SimpleNamespace` bridging JSONB keys to the attribute names expected by `compute_backstory_cache_key()` (`location_city → city`, `drug_tolerance → darkness_level`)..." — correct.

**Line 483 now reads**: "Validation path (MUST match facade docstring at FR-10.1): load `users.onboarding_profile` JSONB (NOT `user_profiles` table — see Semantics note above), build `SimpleNamespace(city=jsonb.get("location_city"), darkness_level=jsonb.get("drug_tolerance"), ...)`..." — correct.

The remaining `user_profiles` occurrences in the spec (lines 338–339 in the facade docstring parenthetical and lines 801–802 in Out of Scope) are legitimate contextual references, not stale ownership-check descriptions. No other occurrences exist that describe the wrong data source.

No new gaps introduced by the iter-5 fix commit.

---

### Findings

None.

---

### API Inventory

| Method | Endpoint | Purpose | Auth | Request | Response |
|--------|----------|---------|------|---------|----------|
| POST | `/api/v1/onboarding/preview-backstory` | Generate backstory previews at step 8 | JWT | `BackstoryPreviewRequest` | `BackstoryPreviewResponse` |
| GET | `/api/v1/onboarding/pipeline-ready/{user_id}` | Poll pipeline readiness (and resume wizard_step) | JWT | Path param UUID | `PipelineReadyResponse` (extended with `wizard_step`) |
| POST | `/api/v1/onboarding/profile` | Final profile submit (step 10) | JWT | `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` |
| PATCH | `/api/v1/onboarding/profile` | Mid-wizard partial update (steps 4-9) | JWT | `OnboardingV2ProfilePatchRequest` | `OnboardingV2ProfileResponse` |
| PUT | `/api/v1/onboarding/profile/chosen-option` | Persist backstory card selection (FR-10.1) | JWT | `BackstoryChoiceRequest` | `OnboardingV2ProfileResponse` |

**Router mount**: `portal_onboarding_router` at prefix `/api/v1/onboarding` (main.py:272–278). No URL collision with existing routes.

---

### Server Actions

None. Client-side API calls via `apiClient` from `portal/src/lib/api/client.ts`. No Next.js Server Actions. Consistent with Spec 213 patterns.

---

### Request/Response Schemas

#### `BackstoryChoiceRequest` (NEW — FR-10.1)
```python
class BackstoryChoiceRequest(BaseModel):
    chosen_option_id: str = Field(..., min_length=1, max_length=64)
    cache_key: str = Field(..., min_length=1, max_length=128)
```
Status: Well-formed. Comments note actual IDs are sha256[:12] (12 hex chars); max_length=64 is safe headroom.

#### `PipelineReadyResponse` (EXTENDED — FR-10.2)
```python
class PipelineReadyResponse(BaseModel):
    state: PipelineReadyState
    message: str | None = None
    checked_at: datetime
    venue_research_status: str = Field(default="pending")
    backstory_available: bool = Field(default=False)
    wizard_step: int | None = Field(default=None, ge=1, le=11)  # NEW
```
Status: Correct. `ge=1` unified across PATCH write and GET read.

#### Existing consumed schemas (confirmed live and correct)
- `OnboardingV2ProfileRequest`: 9 data fields + optional `wizard_step` (`ge=1, le=11`). Live at `contracts.py:57–78`.
- `OnboardingV2ProfileResponse`: 7 fields including `chosen_option: BackstoryOption | None`. PUT endpoint returns this with `chosen_option` populated.
- `BackstoryPreviewRequest` / `BackstoryPreviewResponse`: Confirmed live.
- `BackstoryOption`: 6 fields (id, venue, context, the_moment, unresolved_hook, tone). Stable.

---

### Rate Limiter Architecture

| Limiter | Class | Prefix | Limit | Dependency | Endpoint |
|---------|-------|--------|-------|------------|---------|
| Voice (existing) | `DatabaseRateLimiter` | (none) | 20/min | `voice_rate_limit` | Voice paths |
| Preview (existing) | `_PreviewRateLimiter` | `preview:` | 5/min | `preview_rate_limit` | POST /preview-backstory |
| Choice (NEW) | `_ChoiceRateLimiter` | `choice:` | 10/min | `choice_rate_limit` | PUT /chosen-option |
| Poll (NEW) | `_PipelineReadyRateLimiter` | `poll:` | 30/min | `pipeline_ready_rate_limit` | GET /pipeline-ready |

All four limiters: `_get_minute_window()` and `_get_day_window()` override with namespace prefix. All `check()` calls pass bare UUID. All 429 responses include `Retry-After: 60`.

---

### Error Code Inventory

| Code | Status | Description | User Message | Endpoint |
|------|--------|-------------|-------------|----------|
| VALIDATION_ERROR | 422 | Pydantic schema violation | FastAPI default (list shape) | All endpoints |
| NOT_AUTHORIZED | 403 | JWT user != path user_id | "Not authorized" | GET /pipeline-ready |
| NOT_FOUND | 404 | User not found | "User not found" | GET /pipeline-ready |
| RATE_LIMIT | 429 | Rate limit exceeded (+ Retry-After: 60) | "Rate limit exceeded" | POST /preview-backstory |
| CACHE_MISMATCH | 403 | cache_key recompute mismatch | "Clearance mismatch. Start over." | PUT /profile/chosen-option |
| CACHE_MISS | 404 | No cache row for cache_key | Nikita-voiced | PUT /profile/chosen-option |
| OPTION_NOT_FOUND | 409 | chosen_option_id not in cache scenarios | "That scenario doesn't exist. Pick one she actually generated for you." | PUT /profile/chosen-option |
| RATE_LIMIT | 429 | Rate limit exceeded (+ Retry-After: 60) | "Rate limit exceeded" | PUT /profile/chosen-option, GET /pipeline-ready |

**Error shape**: handler-raised (403/404/409/429) use flat `{"detail": string}`; Pydantic 422 uses list `{"detail": [{loc, msg, type}]}`.

---

### Recommendations

None. Spec is ready for implementation planning.
