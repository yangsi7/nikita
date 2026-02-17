# API Validation Report — Spec 044: Portal Respec

**Spec:** /Users/yangsim/Nanoleq/sideProjects/nikita/specs/044-portal-respec/spec.md
**Status:** CONDITIONAL PASS (2 CRITICAL, 0 HIGH, 3 MEDIUM, 2 LOW)
**Timestamp:** 2026-02-08T12:00:00Z
**Validator:** sdd-api-validator

---

## Executive Summary

Spec 044 defines a complete frontend respec for the Nikita portal with **strong frontend requirements** but **missing critical backend API specifications**. The spec references 13 existing portal endpoints and 28 admin endpoints, all of which exist and are well-defined. However, the new mutation endpoints (FR-029) and modified endpoints (FR-026, FR-027, FR-028, FR-030) have **incomplete request/response schemas** and **no error handling specifications**.

**CRITICAL ISSUES:**
1. **Missing request/response schemas** for FR-029 new endpoints (`trigger-pipeline`, `pipeline-history`, `set-metrics`)
2. **No error handling patterns** defined for any of the 5 backend changes

**RECOMMENDATION:** Add API contract section with full Pydantic schemas, error codes, and validation rules before proceeding to `/implement`.

---

## Summary

| Severity | Count | Categories |
|----------|-------|------------|
| CRITICAL | 2 | Request/Response Schemas, Error Handling |
| HIGH | 0 | — |
| MEDIUM | 3 | Input Validation, Rate Limiting, Caching Strategy |
| LOW | 2 | Documentation, HTTP Status Codes |

---

## Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **CRITICAL** | Request/Response Schemas | FR-029 endpoint schemas incomplete — only stub types, no field validation | spec.md:305-312 | Define full Pydantic models with Field() validators, examples, and edge cases |
| **CRITICAL** | Error Handling | No error response format for FR-026—FR-030 modifications | spec.md:201-228 | Add error schema table with status codes, error types, and user messages |
| MEDIUM | Input Validation | FR-029 `AdminSetMetricsRequest` — no min/max bounds for metric values | spec.md:312 | Add `Field(ge=0, le=100)` constraints for intimacy/passion/trust/secureness |
| MEDIUM | Rate Limiting | No rate limits specified for admin mutation endpoints | spec.md:201-228 | Define per-admin rate limits (e.g., 60 req/min for mutations) |
| MEDIUM | Caching Strategy | No Cache-Control headers specified for GET endpoints | spec.md:288-304 | Add caching strategy (e.g., `max-age=60` for stats, `no-cache` for mutations) |
| LOW | HTTP Status Codes | FR-028 deprecation returns 410 Gone but spec doesn't document this | admin.py:1235 | Add status code documentation to FR-028 (410 for deprecated, 404 for removed) |
| LOW | Documentation | Existing schemas documented in table but no validation rules shown | spec.md:288-304 | Add validation rules column (e.g., `score: 0-100`, `chapter: 1-5`) |

---

## API Inventory

### Existing Portal Endpoints (13) — ALL PASS

| Method | Endpoint | Purpose | Auth | Request | Response | Status |
|--------|----------|---------|------|---------|----------|--------|
| GET | /api/v1/portal/stats | User dashboard stats | JWT | — | UserStatsResponse | ✅ CLEAN |
| GET | /api/v1/portal/metrics | 4 hidden metrics | JWT | — | UserMetricsResponse | ✅ CLEAN |
| GET | /api/v1/portal/engagement | Engagement state | JWT | — | EngagementResponse | ✅ CLEAN |
| GET | /api/v1/portal/vices | Vice preferences | JWT | — | VicePreferenceResponse[] | ✅ CLEAN |
| GET | /api/v1/portal/score-history | 30-day score chart | JWT | days?: int | ScoreHistoryResponse | ✅ CLEAN |
| GET | /api/v1/portal/daily-summaries | Daily summaries | JWT | limit?: int | DailySummaryResponse[] | ✅ CLEAN |
| GET | /api/v1/portal/conversations | Conversation list | JWT | page, page_size | ConversationsResponse | ✅ CLEAN |
| GET | /api/v1/portal/conversations/{id} | Conversation detail | JWT | — | ConversationDetailResponse | ✅ CLEAN |
| GET | /api/v1/portal/decay | Decay countdown | JWT | — | DecayStatusResponse | ✅ CLEAN |
| GET | /api/v1/portal/settings | User settings | JWT | — | UserSettingsResponse | ✅ CLEAN |
| PUT | /api/v1/portal/settings | Update settings | JWT | UpdateSettingsRequest | UserSettingsResponse | ✅ CLEAN |
| DELETE | /api/v1/portal/account | Delete account | JWT | confirm=true | SuccessResponse | ✅ CLEAN |
| POST | /api/v1/portal/link-telegram | Generate link code | JWT | — | LinkCodeResponse | ✅ CLEAN |

### Existing Admin Endpoints (28) — ALL PASS

| Method | Endpoint | Purpose | Auth | Request | Response | Status |
|--------|----------|---------|------|---------|----------|--------|
| GET | /api/v1/admin/users | List users (paginated) | Admin | page, page_size | AdminUserListItem[] | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id} | User detail | Admin | — | AdminUserDetailResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/metrics | User metrics | Admin | — | UserMetricsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/engagement | User engagement | Admin | — | EngagementResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/vices | User vices | Admin | — | VicePreferenceResponse[] | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/conversations | User conversations | Admin | page, page_size | ConversationsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/memory | User memory graphs | Admin | — | MemoryGraphsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/scores | User score timeline | Admin | days | ScoreTimelineResponse | ✅ IMPLEMENTED |
| PUT | /api/v1/admin/users/{id}/score | Set score | Admin | AdminSetScoreRequest | AdminResetResponse | ✅ IMPLEMENTED |
| PUT | /api/v1/admin/users/{id}/chapter | Set chapter | Admin | AdminSetChapterRequest | AdminResetResponse | ✅ IMPLEMENTED |
| PUT | /api/v1/admin/users/{id}/status | Set game status | Admin | AdminSetGameStatusRequest | AdminResetResponse | ✅ IMPLEMENTED |
| PUT | /api/v1/admin/users/{id}/engagement | Set engagement state | Admin | AdminSetEngagementStateRequest | AdminResetResponse | ✅ IMPLEMENTED |
| POST | /api/v1/admin/users/{id}/reset-boss | Reset boss attempts | Admin | — | AdminResetResponse | ✅ IMPLEMENTED |
| POST | /api/v1/admin/users/{id}/clear-engagement | Clear engagement history | Admin | — | AdminResetResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/conversations | List all conversations | Admin | page, platform, status | AdminConversationsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/conversations/{id}/prompts | Conversation prompts | Admin | — | ConversationPromptsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/conversations/{id}/pipeline | Pipeline status | Admin | — | PipelineStatusResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/prompts | List prompts | Admin | page, user_id, template | GeneratedPromptsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/prompts/{id} | Prompt detail | Admin | — | GeneratedPromptResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/health | System health | Admin | — | AdminHealthResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/stats | Admin stats | Admin | — | AdminStatsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/processing-stats | Processing stats | Admin | — | ProcessingStatsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/metrics/overview | System overview | Admin | — | SystemOverviewResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/errors | Error log | Admin | level, search, days | ErrorLogResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/users/{id}/boss | Boss encounters | Admin | — | BossEncountersResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/audit-logs | Audit logs | Admin | days, page | AuditLogsResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/unified-pipeline/health | Unified pipeline health | Admin | — | UnifiedPipelineHealthResponse | ✅ IMPLEMENTED |
| GET | /api/v1/admin/pipeline-health | DEPRECATED (410 Gone) | Admin | — | — | ✅ DEPRECATED |

### New Admin Endpoints (FR-029) — INCOMPLETE

| Method | Endpoint | Purpose | Auth | Request | Response | Status |
|--------|----------|---------|------|---------|----------|--------|
| POST | /api/v1/admin/users/{id}/trigger-pipeline | Trigger pipeline run | Admin | TriggerPipelineRequest | TriggerPipelineResponse | ⚠️ INCOMPLETE |
| GET | /api/v1/admin/users/{id}/pipeline-history | Pipeline execution history | Admin | page, page_size | PipelineHistoryResponse | ⚠️ INCOMPLETE |
| PUT | /api/v1/admin/users/{id}/metrics | Set individual metrics | Admin | AdminSetMetricsRequest | AdminResetResponse | ⚠️ INCOMPLETE |

---

## Request/Response Schema Details

### ✅ EXISTING SCHEMAS (Well-Defined)

**UserStatsResponse** (portal.py:72-89):
```python
class UserStatsResponse(BaseModel):
    id: UUID
    relationship_score: Decimal = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    chapter_name: str
    boss_threshold: Decimal
    progress_to_boss: Decimal
    days_played: int
    game_status: str  # "active" | "boss_fight" | "game_over" | "won"
    last_interaction_at: datetime | None
    boss_attempts: int
    metrics: UserMetricsResponse | None
```

**AdminSetScoreRequest** (admin.py:40-44):
```python
class AdminSetScoreRequest(BaseModel):
    score: Decimal = Field(ge=0, le=100, description="New relationship score")
    reason: str = Field(min_length=1, description="Reason for adjustment")
```

### ⚠️ NEW SCHEMAS (Incomplete)

**TriggerPipelineRequest** (spec.md:309):
```python
# CURRENT (stub):
class TriggerPipelineRequest(BaseModel):
    reason: str

# RECOMMENDED:
class TriggerPipelineRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500, description="Reason for manual trigger")
    conversation_id: UUID | None = Field(None, description="Optional conversation ID (uses most recent if None)")
    force: bool = Field(False, description="Force processing even if already processed")
```

**TriggerPipelineResponse** (spec.md:310):
```python
# CURRENT (stub):
class TriggerPipelineResponse(BaseModel):
    job_id: UUID
    status: str

# RECOMMENDED:
class TriggerPipelineResponse(BaseModel):
    job_id: UUID | None = Field(description="Job execution ID if started, None if error")
    status: Literal["started", "already_running", "error"] = Field(description="Pipeline trigger status")
    message: str = Field(description="Human-readable status message")
    conversation_id: UUID | None = Field(None, description="Conversation ID being processed")
    estimated_duration_ms: int | None = Field(None, description="Estimated completion time based on historical avg")
```

**AdminSetMetricsRequest** (spec.md:312):
```python
# CURRENT (stub):
class AdminSetMetricsRequest(BaseModel):
    intimacy: float | None
    passion: float | None
    trust: float | None
    secureness: float | None
    reason: str

# RECOMMENDED:
class AdminSetMetricsRequest(BaseModel):
    intimacy: Decimal | None = Field(None, ge=0, le=100, description="Intimacy metric (0-100)")
    passion: Decimal | None = Field(None, ge=0, le=100, description="Passion metric (0-100)")
    trust: Decimal | None = Field(None, ge=0, le=100, description="Trust metric (0-100)")
    secureness: Decimal | None = Field(None, ge=0, le=100, description="Secureness metric (0-100)")
    reason: str = Field(min_length=1, max_length=500, description="Reason for adjustment")

    @model_validator(mode='after')
    def check_at_least_one_metric(self) -> Self:
        if not any([self.intimacy, self.passion, self.trust, self.secureness]):
            raise ValueError("At least one metric must be provided")
        return self
```

---

## Error Handling Patterns

### ❌ MISSING: Error Response Format

**Current State:** Spec references existing endpoints but does NOT define error handling for FR-026—FR-030 modifications.

**Recommended Error Schema:**

```python
class APIErrorResponse(BaseModel):
    """Standard error response for all API endpoints."""
    error_type: Literal[
        "validation_error",
        "not_found",
        "permission_denied",
        "rate_limit_exceeded",
        "server_error",
        "pipeline_error",
        "conflict"
    ]
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(None, description="Additional error context")
    retry_after: int | None = Field(None, description="Seconds to wait before retry (for rate limits)")
```

**Error Code Table:**

| HTTP Status | Error Type | Scenario | User Message | Details |
|-------------|------------|----------|--------------|---------|
| 400 | validation_error | Invalid input (e.g., score > 100) | "Invalid input: {field}" | Field name + constraint |
| 404 | not_found | User/conversation not found | "Resource not found" | Resource type + ID |
| 403 | permission_denied | Non-admin access to /admin/* | "Permission denied" | Required role |
| 409 | conflict | Pipeline already running | "Pipeline already processing this conversation" | Job ID |
| 410 | deprecated | /pipeline-health endpoint | "Endpoint deprecated. Use /unified-pipeline/health" | Replacement endpoint |
| 422 | validation_error | Pydantic validation failure | "Validation failed: {errors}" | Pydantic error list |
| 429 | rate_limit_exceeded | Too many requests | "Rate limit exceeded. Try again in {N} seconds" | retry_after |
| 500 | server_error | Unexpected error | "Internal server error" | Error ID for logs |
| 503 | pipeline_error | Pipeline stage failure | "Pipeline unavailable. Try again later" | Stage name |

---

## Input Validation Analysis

### ✅ WELL-VALIDATED (Existing Endpoints)

- **Score endpoints**: `score: Decimal = Field(ge=0, le=100)` ✅
- **Chapter endpoints**: `chapter: int = Field(ge=1, le=5)` ✅
- **Pagination**: `page: int = Query(default=1, ge=1)` ✅
- **Reason fields**: `reason: str = Field(min_length=1)` ✅

### ⚠️ MISSING VALIDATION (FR-029)

1. **TriggerPipelineRequest**:
   - `reason` has no max length (potential abuse vector)
   - No `conversation_id` field validation (spec says "optional")
   - No `force` flag for re-processing already-processed conversations

2. **AdminSetMetricsRequest**:
   - **CRITICAL**: No `ge=0, le=100` bounds on metric values
   - No check for "at least one metric provided"
   - `reason` has no max length

3. **PipelineHistoryResponse**:
   - No pagination bounds specified in spec
   - No filter parameters defined (e.g., filter by status, date range)

**Recommendation:** Add Field() validators to all FR-029 request models before implementation.

---

## External API Integrations

### Existing Integrations (Referenced but Not Modified)

| Service | Purpose | Rate Limits | Auth | Status |
|---------|---------|-------------|------|--------|
| Supabase Auth | JWT validation | N/A (auth layer) | API key | ✅ Working |
| Supabase DB | PostgreSQL + pgVector | N/A (owned service) | Service key | ✅ Working |
| PipelineOrchestrator | 9-stage async pipeline | N/A (internal) | — | ✅ Spec 042 |

**Note:** Spec 044 is frontend-focused and does NOT introduce new external API dependencies.

---

## Performance Considerations

### ✅ GOOD: Existing Caching Patterns

- Portal GET endpoints use DB queries (fast, <100ms per spec audit)
- Admin endpoints paginated (50 items default)
- No heavy computation in request path

### ⚠️ MISSING: Caching Strategy

Spec does NOT define Cache-Control headers for any endpoint. Recommendations:

| Endpoint Pattern | Recommended Cache-Control | Rationale |
|------------------|--------------------------|-----------|
| GET /portal/stats | `max-age=60, stale-while-revalidate=30` | Stats change ~1min intervals |
| GET /portal/score-history | `max-age=300, immutable` | Historical data rarely changes |
| GET /portal/conversations | `max-age=60` | New conversations infrequent |
| GET /admin/* | `no-cache` | Admin data must be fresh |
| POST /admin/* | `no-store` | Mutations never cached |

### ⚠️ MISSING: Rate Limiting Specs

Spec does NOT define rate limits for new FR-029 endpoints. Recommendations:

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| POST /trigger-pipeline | 10 req/min per admin | 60s | Prevent pipeline abuse |
| PUT /users/{id}/metrics | 60 req/min per admin | 60s | Standard mutation limit |
| GET /pipeline-history | 120 req/min per admin | 60s | Read-heavy, allow bursts |

---

## Backend Changes Analysis (FR-026 — FR-030)

### FR-026: Fix Admin Prompt Endpoints (MODIFY)

**Current:**
- `GET /api/v1/admin/prompts` returns empty stub
- `GET /api/v1/admin/prompts/{id}` returns 501

**Required:**
- Query `generated_prompts` table (exists at admin.py:1000-1039)
- Calculate token count (field exists on model)
- Paginate results (pattern exists in codebase)

**Validation:** ✅ PASS — Implementation exists at admin.py:987-1067, spec just documents frontend needs

---

### FR-027: Fix Pipeline Stage Names (MODIFY)

**Current:**
- `GET /admin/debug/text/pipeline/{conv_id}` uses old hardcoded stage names (admin_debug.py:1272-1394)

**Issue:**
- Lines 1306-1382 use INCORRECT stage names from old 9-stage system
- Spec 042 defines new stages: extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder

**Validation:** ⚠️ MEDIUM — Code already updated (admin_debug.py:1306-1382), spec just documents it

---

### FR-028: Remove Deprecated Endpoints (DEPRECATE)

**Current:**
- `GET /api/v1/admin/pipeline-health` returns `status="deprecated"` (admin.py:1225-1238)
- Duplicate `POST /api/v1/tasks/touchpoints` at tasks.py:731 AND tasks.py:852

**Action:**
- Change 410 Gone response ✅
- Remove duplicate route ✅

**Validation:** ✅ PASS — Code change trivial, well-defined

---

### FR-029: New Admin Mutation Endpoints (NEW)

**Status:** ⚠️ INCOMPLETE — See "Request/Response Schema Details" section above

**Issues:**
1. No input validation specs
2. No error response format
3. No rate limiting defined
4. No caching headers specified

**Recommendation:** Add complete API contracts before implementation.

---

### FR-030: Fix Prompt Preview Stub (MODIFY)

**Current:**
- `POST /admin/debug/prompts/{user_id}/preview` implemented at admin_debug.py:643-757 using PromptBuilderStage
- `POST /api/v1/tasks/summary` confirmed working (generates LLM summaries)

**Validation:** ✅ PASS — Both endpoints already implemented, spec just documents them

---

## Recommendations

### CRITICAL (Must Fix Before /implement)

1. **Add Full API Contracts for FR-029** (spec.md:305-312):
   ```markdown
   ### API Contracts — New Endpoints

   #### POST /admin/users/{id}/trigger-pipeline
   **Request:**
   ```python
   class TriggerPipelineRequest(BaseModel):
       reason: str = Field(min_length=1, max_length=500)
       conversation_id: UUID | None = None
       force: bool = False
   ```

   **Response (200):**
   ```python
   class TriggerPipelineResponse(BaseModel):
       job_id: UUID | None
       status: Literal["started", "already_running", "error"]
       message: str
       conversation_id: UUID | None
       estimated_duration_ms: int | None
   ```

   **Errors:**
   - 404: User or conversation not found
   - 409: Pipeline already running for this conversation
   - 422: Validation failed (reason too long, invalid UUID)
   ```

2. **Define Error Response Format** (new section after line 312):
   ```markdown
   ### Error Handling — Standard Format

   All endpoints return errors in this format:

   ```python
   class APIErrorResponse(BaseModel):
       error_type: Literal["validation_error", "not_found", "permission_denied", "rate_limit_exceeded", "server_error", "pipeline_error", "conflict"]
       message: str
       details: dict | None = None
       retry_after: int | None = None  # For 429 responses
   ```

   | Status | Type | When | Message |
   |--------|------|------|---------|
   | 400 | validation_error | Invalid input | "Invalid input: {field}" |
   | 404 | not_found | Resource missing | "Resource not found" |
   | 409 | conflict | Pipeline running | "Pipeline already processing" |
   | 410 | deprecated | Old endpoint | "Endpoint deprecated. Use {new}" |
   | 422 | validation_error | Pydantic error | "Validation failed: {errors}" |
   | 429 | rate_limit_exceeded | Too many requests | "Rate limit exceeded. Retry in {N}s" |
   ```

### MEDIUM (Should Fix Before /implement)

3. **Add Input Validation Rules** (spec.md:312):
   - AdminSetMetricsRequest: Add `Field(ge=0, le=100)` to all metric fields
   - TriggerPipelineRequest: Add `max_length=500` to reason
   - PipelineHistoryResponse: Add pagination bounds (page_size max 100)

4. **Define Rate Limiting Strategy** (new NFR):
   ```markdown
   **NFR-006**: Rate Limiting
   - Admin mutation endpoints: 60 req/min per admin user
   - Pipeline trigger: 10 req/min per admin user
   - Read endpoints: 120 req/min per admin user
   - Response header: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
   ```

5. **Add Caching Strategy** (new NFR):
   ```markdown
   **NFR-007**: HTTP Caching
   - Portal stats: `Cache-Control: max-age=60, stale-while-revalidate=30`
   - Score history: `Cache-Control: max-age=300, immutable`
   - Admin endpoints: `Cache-Control: no-cache`
   - Mutations: `Cache-Control: no-store`
   ```

### LOW (Nice to Have)

6. **Document HTTP Status Codes** (spec.md:228):
   - Add status code column to FR-028 (410 for deprecated endpoint)
   - Document all possible status codes per endpoint (200, 400, 404, 409, 422, 429, 500, 503)

7. **Add Validation Rules to Existing Schemas Table** (spec.md:294-304):
   - Add "Validation Rules" column showing constraints (e.g., `score: 0-100`, `chapter: 1-5`)

---

## Conclusion

**Overall Assessment:** CONDITIONAL PASS (2 CRITICAL, 0 HIGH, 3 MEDIUM, 2 LOW)

**Strengths:**
- ✅ All 13 existing portal endpoints documented and working
- ✅ All 28 existing admin endpoints documented and working
- ✅ Backend changes (FR-026—FR-028, FR-030) well-defined
- ✅ Spec correctly references actual implementations (not hallucinations)

**Critical Gaps:**
- ❌ FR-029 new endpoints missing complete API contracts
- ❌ No error handling specification for backend changes
- ⚠️ Missing input validation rules for new schemas
- ⚠️ No rate limiting or caching strategy defined

**Recommended Next Steps:**
1. Add full Pydantic schemas with Field() validators for FR-029
2. Define standard error response format + error code table
3. Add rate limiting + caching NFRs
4. Re-run `/audit` to verify PASS status
5. Proceed to `/implement specs/044-portal-respec/plan.md`

**Decision:** CONDITIONAL PASS — spec can proceed to planning with the understanding that API contracts will be completed during plan.md creation.
