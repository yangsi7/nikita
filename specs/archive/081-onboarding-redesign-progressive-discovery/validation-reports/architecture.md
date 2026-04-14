# Architecture Validation Report

**Spec:** `specs/081-onboarding-redesign-progressive-discovery/spec.md`
**Status:** FAIL
**Timestamp:** 2026-03-22T12:00:00Z
**Validator:** sdd-architecture-validator

---

## Summary

- CRITICAL: 0
- HIGH: 2
- MEDIUM: 4
- LOW: 2

---

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | **HIGH** | API Contract | Spec references `schedule_event()` method on `ScheduledEventRepository`, but the actual method is `create_event()` with a different parameter signature. The spec shows `event_repo.schedule_event(user_id=..., platform="telegram", content=..., scheduled_at=..., event_type=...)`, but the real method is `create_event(self, user_id, platform, event_type, content, scheduled_at, source_conversation_id=None)` with `platform` and `event_type` as positional args (not kwargs by name). | spec.md line ~810-836 vs `nikita/db/repositories/scheduled_event_repository.py:create_event()` | Update spec code snippet to use `create_event()` with the correct parameter order. The `event_type` argument must be the 3rd positional parameter, not a kwarg at the end. |
| 2 | **HIGH** | Data Access | Spec assumes `User` model has an `email` field for magic link generation (`_generate_magic_link(email=user_email)`), but the `User` model in `nikita/db/models/user.py` has NO `email` column. Email is stored only in Supabase Auth (`auth.users`) and accessed via JWT claims in `nikita/api/dependencies/auth.py`. The DripManager cannot obtain user email from the `users` table. | spec.md line ~104, ~757-770, ~841-883 vs `nikita/db/models/user.py` | Spec must document how DripManager obtains user email. Two options: (a) Add a Supabase Admin API call `supabase.auth.admin.get_user_by_id(user.id)` to fetch email at drip evaluation time, or (b) cache email on the `users` table during registration/onboarding. Option (a) is preferred for consistency with existing patterns (no email column exists). Update the `evaluate_user` / `deliver_drip` flow to show this lookup. |
| 3 | **MEDIUM** | Separation of Concerns | `HandoffManager` currently has no session dependency (it creates sessions internally via `get_session_maker()`). The spec's `_schedule_welcome_messages` code snippet uses `self.session` (line ~814: `event_repo = ScheduledEventRepository(self.session)`), but `HandoffManager.__init__` does not accept or store a session. | spec.md line ~800-837 vs `nikita/onboarding/handoff.py:324-335` | Either: (a) modify `HandoffManager.__init__` to accept an optional `session` parameter, or (b) create a session inside `_schedule_welcome_messages` using `get_session_maker()` (matching the existing pattern in `_update_user_status` and `_bootstrap_pipeline`). Option (b) is more consistent with the existing codebase. |
| 4 | **MEDIUM** | Module Organization | `ScheduledEventRepository` does NOT inherit from `BaseRepository[T]` (it is a standalone class), which is inconsistent with all other repositories in the codebase (18 repositories use `BaseRepository[T]`). The spec does not call this out, and new code that interacts with it should be aware of the different interface (no `.get()`, `.create()`, etc. from BaseRepository). | `nikita/db/repositories/scheduled_event_repository.py` | Not a spec issue per se, but the implementation plan should note this difference. DripManager should use `ScheduledEventRepository.create_event()` directly rather than assuming BaseRepository patterns. Consider documenting in the plan that this repo has a custom interface. |
| 5 | **MEDIUM** | Type Safety | The spec defines `DripDefinition` as a `@dataclass` with `templates: dict[int, list[str]]` (darkness_level to template variants). However, no Pydantic model is defined for the drip evaluation result or delivery result. The `process_all()` return type is `dict` (untyped). Other pipeline/task endpoints in the codebase use Pydantic models for structured returns. | spec.md line ~783-791, ~738-741 | Define a `DripEvaluationResult` Pydantic model (or at minimum a TypedDict) for the `process_all()` return value. This ensures the `/check-drips` endpoint returns a validated schema, consistent with the `JobExecution` result pattern used by other task endpoints. |
| 6 | **MEDIUM** | Error Handling | Spec defines drip trigger conditions that require cross-table queries (e.g., Drip 3 requires checking `score_history` for decay events, Drip 6 requires detecting `game_status` transition from `boss_fight`). The `DripManager` class sketch shows only `UserRepository` injection. No mention of `ScoreHistoryRepository`, `ConversationRepository`, or how to detect game_status transitions. | spec.md line ~734-737 vs drip definitions at line ~1001-1009 | Add repository dependencies to `DripManager.__init__`. At minimum: `ScoreHistoryRepository` (for Drip 3 decay detection), `ConversationRepository` (for Drip 1 first processed conversation, Drip 2 conversation count). Document how Drip 6 detects "game_status changed from boss_fight" -- this likely requires a `boss_last_resolved_at` timestamp or checking `score_history` for boss events. |
| 7 | **LOW** | Naming Convention | Spec places `drip_templates.py` in `nikita/onboarding/` (line ~1023). The existing onboarding module is specifically for voice onboarding (Spec 028). The progressive drip system is a post-onboarding feature with different concerns (pg_cron scheduling, Telegram delivery, magic links). Co-locating them conflates two distinct lifecycle phases. | spec.md line ~714, ~1023 | Acceptable for now given the spec's rationale (drips are an extension of the onboarding journey). However, the plan should note that if the drip system grows beyond 7 drips or gains admin UI, it should be extracted to `nikita/drip/` or `nikita/discovery/`. The `onboarding/CLAUDE.md` module doc should be updated to reflect the expanded scope. |
| 8 | **LOW** | Portal Structure | The spec proposes `/dashboard/welcome` as a Server Component that fetches stats server-side (line ~946-965). However, the existing `/dashboard/page.tsx` is a Client Component (`"use client"` directive) that uses TanStack React Query hooks (`useUserStats`). The welcome page would be the only page under `/dashboard/` using a different data-fetching pattern (server-side fetch vs. client-side React Query). | spec.md line ~939-965 vs `portal/src/app/dashboard/page.tsx` | Consider two approaches: (a) Make `welcome/page.tsx` a Client Component using `useUserStats()` for consistency with all other dashboard pages, or (b) keep the Server Component approach but document it as intentional (welcome page benefits from SSR for SEO-irrelevant but first-paint-speed reasons). Either is architecturally valid; the inconsistency should be a conscious decision, not accidental. |

---

## Proposed Structure

The spec introduces the following new files, which fit cleanly within the existing directory hierarchy:

```
nikita/
  onboarding/
    drip_manager.py          # NEW: DripManager class (FR-002)
    drip_templates.py         # NEW: 7x5 template constants (darkness variants)
    handoff.py                # MODIFIED: add _schedule_welcome_messages()
  api/
    routes/
      tasks.py                # MODIFIED: add POST /check-drips endpoint
      portal.py               # MODIFIED: add welcome_completed to stats/settings
    schemas/
      portal.py               # MODIFIED: add welcome_completed to UserStatsResponse, UpdateSettingsRequest
  db/
    models/
      user.py                 # MODIFIED: add drips_delivered JSONB, welcome_completed BOOLEAN
  config/
    settings.py               # EXISTING: portal_url already present (line 114)

portal/
  src/
    app/
      dashboard/
        welcome/
          page.tsx            # NEW: Server Component shell (FR-004)
          welcome-client.tsx  # NEW: Client Component (animations, steps)
        page.tsx              # MODIFIED: add first-visit redirect check
    components/
      dashboard/
        chapter-stepper.tsx   # NEW: Chapter roadmap visualization
      charts/
        score-ring.tsx        # EXISTING: reused in welcome page

supabase/
  migrations/
    20260322000000_add_drips_delivered_and_welcome_completed.sql  # NEW: 2-line comment stub
```

---

## Module Dependency Graph

```
                    pg_cron (every 5 min)
                         |
                         v
             api/routes/tasks.py
             POST /check-drips
                         |
                         v
            onboarding/drip_manager.py
           /          |           \
          v           v            v
  UserRepository  ScoreHistory  Supabase Auth
  (users table)   Repository    Admin API
       |              |         (magic links)
       v              v              |
  drips_delivered  score_history     v
  (JSONB col)      (table)     Portal URL
       |                        + magic token
       v                             |
  TelegramBot.send_message           v
  (inline keyboard + link)    portal/auth/callback
                                     |
                                     v
                             /dashboard/welcome
                             or /dashboard
```

### Handoff Welcome Message Flow

```
  onboarding/handoff.py
  execute_handoff()
       |
       +--> send first Nikita message (existing)
       |
       +--> _schedule_welcome_messages() (NEW, fire-and-forget)
                |
                v
        ScheduledEventRepository.create_event()
        (2 events: 30-60s delay, 3-5min delay)
                |
                v
        pg_cron deliver job (every 1 min)
                |
                v
        TelegramBot.send_message
```

---

## Separation of Concerns Analysis

| Layer | Responsibility | Spec Compliance | Notes |
|-------|---------------|-----------------|-------|
| `onboarding/drip_manager.py` | Drip evaluation logic, trigger checking, rate limiting | OK | Single responsibility: evaluate + deliver drips. Template selection delegated to `drip_templates.py`. |
| `onboarding/drip_templates.py` | Static template data (7 drips x 5 darkness levels) | OK | Pure data, no logic. Correct separation from manager. |
| `onboarding/handoff.py` | Extended to schedule welcome messages | OK with caveat | Welcome messages are a natural extension of handoff. The `_schedule_welcome_messages` method is fire-and-forget, consistent with existing `_bootstrap_pipeline` pattern. Session access needs fixing (Finding #3). |
| `api/routes/tasks.py` | New `/check-drips` endpoint | OK | Follows exact same pattern as existing `process-conversations`, `decay`, `summaries` endpoints. Uses `verify_task_secret` dependency. |
| `api/routes/portal.py` + schemas | Add `welcome_completed` to stats/settings | OK | Additive changes only. No breaking changes to existing clients. |
| `db/models/user.py` | 2 new columns: `drips_delivered`, `welcome_completed` | OK | Lightweight additions. JSONB for drips is appropriate (avoids a separate drip_delivery table for 7 items). |
| Portal welcome page | Interactive guided tour | OK | Reuses existing components (ScoreRing, GlassCard). New ChapterStepper is domain-specific, correctly placed in `components/dashboard/`. |
| Magic link generation | Supabase Admin API call inside DripManager | Needs clarification | The Supabase client creation inside `_generate_magic_link` is acceptable (same pattern as `generate_and_store_social_circle` in handoff.py). However, email source is unresolved (Finding #2). |

---

## Import Pattern Checklist

- [x] Portal uses `@/` import alias (confirmed in `portal/src/app/dashboard/page.tsx`)
- [x] Backend uses `nikita.` absolute imports (confirmed in all `nikita/` modules)
- [x] No circular dependency risk: `drip_manager.py` imports from `db/repositories/` (downward dependency)
- [x] Lazy imports used for heavy dependencies (spec shows `from nikita.onboarding.drip_manager import DripManager` inside endpoint function, matching existing pattern)
- [x] `TYPE_CHECKING` guard used in models (confirmed in `user.py`)
- [x] New portal components will use `@/components/` alias (consistent with existing pages)

---

## Security Architecture

- [x] `check-drips` endpoint protected by `verify_task_secret` (Bearer token auth, same as 6 existing task endpoints)
- [x] Magic link uses Supabase service role key (server-side only, never exposed to client)
- [x] RLS on `users` table covers new columns automatically (existing policy: `auth.uid() = id`)
- [x] `welcome_completed` update goes through authenticated `PUT /portal/settings` endpoint (JWT required)
- [x] No new secrets introduced (uses existing `TASK_AUTH_SECRET` and `supabase_service_key`)
- [x] Magic link fallback: if generation fails, regular portal URL used (no auth bypass)
- [ ] **Note**: The pg_cron `check-drips` job SQL will contain `TASK_AUTH_SECRET` in the schedule definition. Document this in the implementation plan (same pattern as 6 existing jobs, but reminder: if secret rotates, all 7 jobs need updating).

---

## Recommendations

### Priority 1 (Must fix before planning -- HIGH severity)

1. **Fix `schedule_event` -> `create_event` method name.** Update spec section "Backend: Welcome messages in handoff.py" (line ~810-836) to use `ScheduledEventRepository.create_event()` with correct parameter order: `create_event(user_id=..., platform=EventPlatform.TELEGRAM, event_type="welcome_message_1", content=..., scheduled_at=...)`.

2. **Resolve email source for magic link generation.** The `User` model has no `email` column. Add a section to the spec's Technical Architecture documenting how DripManager obtains email. Recommended: use `supabase.auth.admin.get_user_by_id(str(user.id))` which returns the auth user record including email. Update `_generate_magic_link` to show this lookup. Handle the case where Supabase Admin API is unavailable (fall back to regular portal URL).

### Priority 2 (Should fix -- MEDIUM severity)

3. **Fix session access in `_schedule_welcome_messages`.** Change the code snippet to create its own session via `get_session_maker()` rather than using `self.session`, matching the existing pattern in `HandoffManager._update_user_status()` and `_bootstrap_pipeline()`.

4. **Add repository dependencies to DripManager.** The class needs `ScoreHistoryRepository` and `ConversationRepository` in addition to `UserRepository` to evaluate trigger conditions for Drips 1, 2, 3, and 6. Update the `__init__` and class sketch.

5. **Define typed return model for `process_all()`.** Add a `DripProcessResult` Pydantic model with fields: `status`, `evaluated`, `delivered`, `rate_limited`, `errors`, `magic_link_failures`.

### Priority 3 (Good to address -- LOW severity)

6. **Document module scope expansion.** Update `nikita/onboarding/CLAUDE.md` to reflect the new drip system alongside the existing voice onboarding modules. Note that the module now covers both onboarding initiation AND post-onboarding discovery.

7. **Choose data-fetching pattern for welcome page.** Decide whether `/dashboard/welcome` will be a Server Component (spec's proposal) or a Client Component (matching all other dashboard pages). Document the rationale.
