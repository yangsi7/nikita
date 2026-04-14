## API Validation Report

**Spec:** specs/081-onboarding-redesign-progressive-discovery/spec.md
**Status:** FAIL
**Timestamp:** 2026-03-22T12:00:00Z

### Summary
- CRITICAL: 2
- HIGH: 5
- MEDIUM: 4
- LOW: 2

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | CRITICAL | Routes | `JobName` enum missing `CHECK_DRIPS` value | spec.md:907, job_execution.py:18-27 | The endpoint calls `job_repo.start_execution("check_drips")` but `JobName` enum has no `CHECK_DRIPS` member. Existing pattern uses `JobName.VALUE.value` (e.g., `JobName.DECAY.value`). Without an enum entry, the job name is a raw string, which breaks admin portal job filtering. Add `CHECK_DRIPS = "check_drips"` to `JobName` enum. |
| 2 | CRITICAL | Integration | `HandoffManager` has no `self.session` -- spec code references `self.session` in `_schedule_welcome_messages` | spec.md:814, handoff.py:333-335 | `HandoffManager.__init__()` takes zero parameters (line 333). The spec code for `_schedule_welcome_messages` uses `ScheduledEventRepository(self.session)` but no session exists on the instance. Either: (a) add `session` parameter to `HandoffManager.__init__`, or (b) open a new session inside `_schedule_welcome_messages` using `get_session_maker()` (fire-and-forget pattern consistent with `_bootstrap_pipeline`). Option (b) is safer since it avoids changing the existing constructor signature that callers depend on. |
| 3 | HIGH | Schemas | `UserStatsResponse` missing `welcome_completed` field | spec.md:1114-1128, portal.py:27-41 | Spec says `GET /portal/stats` will return `welcome_completed: false` but the existing `UserStatsResponse` Pydantic schema (nikita/api/schemas/portal.py:27-41) has no such field. Spec must explicitly call out that `UserStatsResponse` needs a new field: `welcome_completed: bool = False`. Without this, the field is silently dropped from the response. |
| 4 | HIGH | Schemas | `UpdateSettingsRequest` missing `welcome_completed` field | spec.md:1130-1138, portal.py:167-171 | Spec says `PUT /portal/settings` should accept `{"welcome_completed": true}` but the existing `UpdateSettingsRequest` (portal.py:167-171) only has `timezone` and `notifications_enabled`. The schema must be extended AND the `update_user_settings` handler (portal.py:489-526) must be updated to pass `welcome_completed` through to `user_repo.update_settings()`. Spec does not document either change. |
| 5 | HIGH | Integration | Spec calls `schedule_event()` but actual method is `create_event()` | spec.md:819, scheduled_event_repository.py:53 | The spec code calls `event_repo.schedule_event(...)` but `ScheduledEventRepository` exposes `create_event()` (line 53), not `schedule_event()`. Method name mismatch will cause `AttributeError` at runtime. Update spec to use `create_event(user_id, platform, event_type, content, scheduled_at)`. |
| 6 | HIGH | Schemas | `DripManager.process_all()` return schema inconsistent -- missing `status` key on success | spec.md:738-743 vs 1101-1109 | The `process_all()` docstring (spec.md:743) shows return `{"evaluated": int, "delivered": int, "rate_limited": int, "errors": int}` but the API response example (spec.md:1101-1109) adds `"status": "ok"` and `"magic_link_failures"`. The endpoint code (spec.md:917) does `return result` directly from `manager.process_all()`, so whatever `process_all()` returns IS the HTTP response. Either `process_all()` must return `status` and `magic_link_failures`, or the endpoint must wrap the result. Codebase convention is `{"status": "ok", ...}` at the route level -- recommend the endpoint wraps `process_all()` output. |
| 7 | HIGH | Error Handling | `check-drips` endpoint error response does not return HTTP status 200 -- implicit mismatch with pg_cron | spec.md:919-924 | The endpoint catches exceptions and returns `{"status": "error", ...}` as a dict, which FastAPI serializes as HTTP 200. This matches existing codebase convention (all task endpoints return 200 with status in body). However, the spec does not document this explicitly. More importantly: if any uncaught exception escapes (e.g., from `get_session_maker()`), FastAPI returns HTTP 500, and pg_cron's `net.http_post` will NOT retry. Spec should document that the outer try-except must cover session creation too. Currently, `session_maker = get_session_maker()` is outside the try block (spec.md:904), same pattern as existing endpoints -- consistent but fragile. |
| 8 | MEDIUM | Validation | No idempotency guard on `check-drips` endpoint | spec.md:890-925 | All other high-frequency task endpoints (decay, process-conversations) include `job_repo.has_recent_execution()` idempotency guards to prevent overlapping runs when pg_cron fires faster than the job completes. The `check-drips` endpoint has no such guard. While drip delivery itself is idempotent (checks `drips_delivered` JSONB), a slow run could overlap with the next cron trigger, causing double evaluation and wasted compute. Recommend adding: `if await job_repo.has_recent_execution("check_drips", window_minutes=4): return {"status": "skipped"}`. |
| 9 | MEDIUM | Integration | `_schedule_welcome_messages` parameter mismatch with `create_event` | spec.md:819-836 | The spec calls `event_repo.schedule_event(..., platform="telegram")` but `create_event()` requires `platform` as `EventPlatform | str`. While passing `"telegram"` as a string works (the method handles string values), the spec also omits the required `event_type` parameter name alignment -- spec uses named param `event_type="welcome_message_1"` which works, but `"welcome_message_1"` is not in the `EventType` enum. Confirm that string event types are acceptable (they are -- the method converts to string). However, document this as a new event type for future traceability. |
| 10 | MEDIUM | Performance | `DripManager.process_all()` lacks user query specification | spec.md:738-742 | The spec says the method "iterates eligible users" but does not define the SQL query to find them. Critical questions: (a) Which users? Only `onboarding_status='completed'`? Only `game_status='active'`? (b) Does it load all users into memory or paginate? (c) Does it eagerly load `metrics` and `engagement_state`? Existing pattern (`get_active_users_for_decay`) returns only `game_status='active'` users. The drip system should probably target `onboarding_status='completed' AND game_status IN ('active', 'boss_fight')` to include users in boss fights (for drip 6). Specify the query. |
| 11 | MEDIUM | External API | Supabase Admin `generate_link` API -- synchronous client in async context | spec.md:859-883 | The magic link generation code uses `create_client()` (sync Supabase client) inside an async method. This blocks the event loop during the HTTP call to Supabase Auth API. For a pg_cron batch job processing many users, this could cause significant latency. Options: (a) use `create_async_client()` from `supabase`, (b) run in `asyncio.to_thread()`, (c) accept the blocking call since magic link generation is fast (~100ms) and runs infrequently. Recommend at minimum documenting the choice. |
| 12 | LOW | Naming | pg_cron job name uses hyphen but `JobName` enum value uses underscore | spec.md:927-937 | The pg_cron schedule name is `'check-drips'` (hyphen) but `start_execution("check_drips")` uses underscore. This is a cosmetic inconsistency. Existing codebase has `process-conversations` (hyphen in pg_cron) mapped to `PROCESS_CONVERSATIONS` enum value `"process-conversations"` (hyphen). Recommend using `"check-drips"` (hyphen) for the job name string to stay consistent: `CHECK_DRIPS = "check-drips"`. |
| 13 | LOW | Documentation | Drip trigger conditions reference game state but don't specify exact SQL/ORM queries | spec.md:1001-1009 | Drip 5 (`boss_warning`) checks `relationship_score >= (boss_threshold - 5)`. Boss thresholds vary by chapter (55, 60, 65, 70, 75). Drip 6 checks `game_status changed from boss_fight` -- this is a state transition detection that cannot be determined from a point-in-time snapshot of `game_status`. Spec should clarify whether drip 6 checks `boss_attempts > (previous value)` or uses `score_history` event_type `boss_pass`/`boss_fail`. |

### API Inventory

| Method | Endpoint | Purpose | Auth | Request | Response |
|--------|----------|---------|------|---------|----------|
| POST | /api/v1/tasks/check-drips | Evaluate and deliver progressive drips | Bearer TASK_AUTH_SECRET | Empty body | `{"status","evaluated","delivered","rate_limited","errors","magic_link_failures"}` |
| GET | /api/v1/portal/stats | Dashboard stats (modification) | JWT | Query params | Add `welcome_completed: bool` to existing `UserStatsResponse` |
| PUT | /api/v1/portal/settings | Update settings (modification) | JWT | `{"welcome_completed": true}` | Existing `UserSettingsResponse` |

### Server Actions

Not applicable (backend is FastAPI/Python, not Next.js server actions).

### Request/Response Schemas

**POST /api/v1/tasks/check-drips**

Request: Empty body (pg_cron trigger).
Auth: `Authorization: Bearer <TASK_AUTH_SECRET>`.

Response (success):
```python
{
    "status": "ok",           # MISSING from process_all() return spec
    "evaluated": int,         # Users checked
    "delivered": int,         # Drips sent
    "rate_limited": int,      # Users skipped (2hr cooldown)
    "errors": int,            # Per-user failures
    "magic_link_failures": int  # Magic link generation failures
}
```

Response (error):
```python
{
    "status": "error",
    "error": str              # Exception message
}
```

**DripDefinition model** (spec.md:783-791):
```python
@dataclass
class DripDefinition:
    drip_id: str                          # e.g., "first_score"
    priority: int                         # Evaluation order (1 = highest)
    trigger_type: str                     # "event" | "threshold" | "time"
    portal_path: str                      # e.g., "/dashboard"
    templates: dict[int, list[str]]       # darkness_level -> template variants
    button_text: str                      # Inline keyboard button label
```

Note: `trigger_type` is a string, not an enum. Consider a `TriggerType` enum for type safety, consistent with `TriggerType` already in `nikita/touchpoints/models.py`.

**drips_delivered JSONB schema**:
```python
# On users table
{"drip_id": "2026-03-22T10:00:00Z", ...}  # ISO timestamp of delivery
```

**welcome_completed column**:
```python
# On users table
welcome_completed: bool = False
```

### Error Code Inventory

| Code | Status | Description | User Message |
|------|--------|-------------|-------------|
| 200 | OK | Drip evaluation completed | N/A (internal endpoint) |
| 200 | OK | Drip evaluation failed (error in body) | N/A (internal endpoint) |
| 401 | Unauthorized | Missing or invalid TASK_AUTH_SECRET | "Unauthorized" |

Note: All task endpoints return HTTP 200 with `{"status": "error"}` in the body for caught exceptions. Only auth failures return HTTP 401.

### Positive Patterns (to replicate)

1. **Fire-and-forget isolation**: Welcome messages use `scheduled_events` table (existing infrastructure) rather than inline delivery, ensuring handoff is never blocked. This is excellent.
2. **Magic link fallback**: Graceful degradation to regular portal URL when magic link generation fails or user has no email. Matches codebase convention.
3. **Existing infrastructure reuse**: Uses `scheduled_events` + `deliver` cron job for welcome messages, `score_history` for trigger detection, `BOSS_THRESHOLDS` for proximity checks. No new infrastructure invented.
4. **Rate limiting via JSONB**: Checking `drips_delivered` timestamps is simple and avoids a separate rate-limit table. Good for a batch job.
5. **Consistent auth pattern**: Uses existing `verify_task_secret` dependency, matching all other task endpoints.

### Recommendations

1. **CRITICAL (Finding #1):** Add `CHECK_DRIPS = "check-drips"` to `JobName` enum in `nikita/db/models/job_execution.py` and update the endpoint to use `JobName.CHECK_DRIPS.value`. This is a one-line enum addition but blocks admin portal job monitoring.

2. **CRITICAL (Finding #2):** The `_schedule_welcome_messages` method must not reference `self.session`. Change spec code to open a new session internally:
   ```python
   async def _schedule_welcome_messages(self, user_id, telegram_id, darkness_level):
       from nikita.db.database import get_session_maker
       from nikita.db.repositories.scheduled_event_repository import ScheduledEventRepository
       async with get_session_maker()() as session:
           event_repo = ScheduledEventRepository(session)
           # ... schedule events ...
           await session.commit()
   ```
   This is consistent with `_bootstrap_pipeline` (handoff.py:573-617) which also opens its own session.

3. **HIGH (Finding #3 + #4):** Add `welcome_completed: bool = False` to `UserStatsResponse` (portal.py:27) AND `welcome_completed: bool | None = None` to `UpdateSettingsRequest` (portal.py:167). Also update `update_user_settings` handler to pass `welcome_completed` through to the repository. Document all three changes in the spec.

4. **HIGH (Finding #5):** Replace all `event_repo.schedule_event(...)` calls with `event_repo.create_event(...)` in the spec. The actual method is `create_event()` at scheduled_event_repository.py:53.

5. **HIGH (Finding #6):** Standardize the response: have the endpoint wrap the `process_all()` result:
   ```python
   stats = await manager.process_all()
   result = {"status": "ok", **stats}
   ```
   And add `magic_link_failures` to `process_all()` return docstring.

6. **HIGH (Finding #7):** Document that `get_session_maker()` is outside the try block, consistent with existing task endpoints. This is an accepted risk in the codebase -- if the session factory fails, FastAPI returns 500 and pg_cron silently drops the response.

7. **MEDIUM (Finding #8):** Add idempotency guard to `check-drips` endpoint, consistent with `/decay`:
   ```python
   if await job_repo.has_recent_execution("check-drips", window_minutes=4):
       return {"status": "skipped", "reason": "recent_execution"}
   ```

8. **MEDIUM (Finding #10):** Define the user eligibility query for `DripManager.process_all()`:
   ```python
   # Users eligible for drip evaluation:
   SELECT * FROM users
   WHERE onboarding_status = 'completed'
     AND game_status IN ('active', 'boss_fight')
     AND onboarded_at IS NOT NULL
   ```

9. **MEDIUM (Finding #11):** Use `asyncio.to_thread(supabase.auth.admin.generate_link, ...)` to avoid blocking the event loop, or document that the sync call is acceptable for the expected batch size.
