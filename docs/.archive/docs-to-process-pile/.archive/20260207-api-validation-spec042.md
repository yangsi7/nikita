# API Audit: Post-Spec 042 Endpoint Inventory & Decision Map

**Date**: 2026-02-07
**Auditor**: api-auditor agent
**Scope**: All 7 route files, 4 schema files, main.py
**Context**: Spec 042 (Unified Pipeline) deleted `nikita/context/`, `nikita/context_engine/`, `nikita/meta_prompts/`, `nikita/post_processing/`, replaced with `nikita/pipeline/` (9-stage orchestrator), `nikita/memory/supabase_memory.py` (pgVector), `nikita/prompts/` (Jinja2 templates)

---

## 1. CRITICAL ISSUES (Must Fix)

### CRIT-1: Stale Import — `nikita.context.session_detector` [BROKEN]
- **File**: `nikita/api/routes/tasks.py:529`
- **Import**: `from nikita.context.session_detector import detect_stale_sessions`
- **Problem**: `nikita/context/` was deleted in Spec 042. This import will crash at runtime when the `process-conversations` pg_cron job fires.
- **Impact**: PRODUCTION — pg_cron calls POST `/api/v1/tasks/process-conversations` every 5 min
- **Fix**: Move `detect_stale_sessions` logic into `nikita/pipeline/` or `nikita/db/repositories/conversation_repository.py` (ConversationRepository already has `.detect_stuck()`)

### CRIT-2: Duplicate Route — `/touchpoints` [SHADOW BUG]
- **File**: `nikita/api/routes/tasks.py:612` AND `nikita/api/routes/tasks.py:733`
- **Problem**: Two handlers registered on same path `POST /touchpoints`. FastAPI registers the LAST one (line 733 `process_touchpoints`), silently shadowing line 612 `deliver_scheduled_touchpoints`.
- **Impact**: Line 612's handler is unreachable dead code.
- **Fix**: Delete one (prefer keeping line 612 which has proper logging; or merge them).

---

## 2. STALE REFERENCES REPORT

| File:Line | Reference | Status | Severity |
|-----------|-----------|--------|----------|
| `tasks.py:529` | `nikita.context.session_detector` | DELETED MODULE | CRITICAL |
| `tasks.py:578-586` | Legacy post_processing branch (feature flag else) | DEAD CODE | LOW |
| `tasks.py:306` | Comment: "MetaPromptService deprecated" | STALE COMMENT | LOW |
| `tasks.py:412` | Hardcoded: "Daily summary generation deprecated (Spec 042)" | STUB RESPONSE | MEDIUM |
| `admin_debug.py:663` | Prompt preview returns stub: "Prompt generation deprecated (Spec 042)" | STUB | MEDIUM |
| `admin.py:991` | `get_pipeline_health` returns `status="deprecated"` | DEPRECATED | LOW |

**No stale references found in**: `portal.py`, `voice.py`, `telegram.py`, `onboarding.py`, schemas/

---

## 3. PIPELINE STAGE NAME MISMATCH

**Spec 042 actual stages** (from `nikita/pipeline/orchestrator.py:38-48`):
1. `extraction` (ExtractionStage, critical)
2. `memory_update` (MemoryUpdateStage, critical)
3. `life_sim` (LifeSimStage)
4. `emotional` (EmotionalStage)
5. `game_state` (GameStateStage)
6. `conflict` (ConflictStage)
7. `touchpoint` (TouchpointStage)
8. `summary` (SummaryStage)
9. `prompt_builder` (PromptBuilderStage)

**admin_debug.py:1232-1282 uses OLD stage names**:
1. "Ingestion" (hardcoded)
2. "Entity Extraction"
3. "Analysis"
4. "Thread Resolution"
5. "Thought Generation"
6. "Graph Updates"
7. "Summary Rollups"
8. "Vice Processing"
9. "Finalization"

**Impact**: Admin debug panel shows wrong pipeline stage names. This misleads developers debugging pipeline issues.

**Fix**: Update `admin_debug.py:1197-1294` to use `PipelineOrchestrator.STAGE_DEFINITIONS` or query `job_executions` for actual stage timing data.

---

## 4. FULL ENDPOINT INVENTORY

### 4.1 Portal Routes (`/api/v1/portal` — 13 endpoints)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | GET | /stats | `get_user_stats` | 67 | KEEP | Core dashboard data |
| 2 | GET | /metrics | `get_user_metrics` | 120 | KEEP | 4-metric breakdown |
| 3 | GET | /engagement | `get_engagement_state` | 158 | KEEP | Engagement state machine |
| 4 | GET | /vices | `get_vice_preferences` | 195 | KEEP | Vice personalization |
| 5 | GET | /score-history | `get_score_history` | 232 | KEEP | Score timeline for chart |
| 6 | GET | /daily-summaries | `get_daily_summaries` | 270 | KEEP | Nikita's daily recaps |
| 7 | GET | /conversations | `list_conversations` | 310 | KEEP | Conversation list |
| 8 | GET | /conversations/{id} | `get_conversation` | 353 | KEEP | Conversation detail |
| 9 | GET | /decay | `get_decay_status` | 393 | KEEP | Decay warning |
| 10 | GET | /settings | `get_user_settings` | 416 | KEEP | User preferences |
| 11 | PUT | /settings | `update_user_settings` | 441 | KEEP | Update preferences |
| 12 | DELETE | /account | `delete_account` | 480 | KEEP | GDPR deletion |
| 13 | POST | /link-telegram | `link_telegram` | 503 | KEEP | Telegram linking |

**Verdict**: All 13 portal endpoints are CLEAN. No stale references.

### 4.2 Admin Routes (`/api/v1/admin` — 25 endpoints)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | GET | /users | `list_users` | 68 | KEEP | User listing |
| 2 | GET | /users/{id} | `get_user` | 121 | KEEP | User detail |
| 3 | GET | /users/{id}/metrics | `get_user_metrics` | 179 | KEEP | Metrics detail |
| 4 | GET | /users/{id}/engagement | `get_user_engagement` | 218 | KEEP | Engagement detail |
| 5 | GET | /users/{id}/vices | `get_user_vices` | 256 | KEEP | Vice detail |
| 6 | GET | /users/{id}/conversations | `get_user_conversations` | 295 | KEEP | Conversation list |
| 7 | GET | /users/{id}/memory | `get_user_memory` | 340 | KEEP | Uses SupabaseMemory (post-042) |
| 8 | GET | /users/{id}/scores | `get_user_scores` | 390 | KEEP | Score history |
| 9 | GET | /users/{id}/boss | `get_user_boss` | 430 | KEEP | Boss encounter status |
| 10 | PUT | /users/{id}/score | `set_user_score` | 468 | KEEP | Admin mutation |
| 11 | PUT | /users/{id}/chapter | `set_user_chapter` | 525 | KEEP | Admin mutation |
| 12 | PUT | /users/{id}/status | `set_user_status` | 573 | KEEP | Admin mutation |
| 13 | PUT | /users/{id}/engagement | `set_user_engagement` | 616 | KEEP | Admin mutation |
| 14 | POST | /users/{id}/reset-boss | `reset_boss_fight` | 670 | KEEP | Admin mutation |
| 15 | POST | /users/{id}/clear-engagement | `clear_engagement` | 715 | KEEP | Admin mutation |
| 16 | GET | /prompts | `list_prompts` | 797 | MODIFY | Returns empty list (TODO stub) |
| 17 | GET | /prompts/{id} | `get_prompt` | 825 | MODIFY | Returns 501 Not Implemented |
| 18 | GET | /conversations | `list_conversations` | 850 | KEEP | Admin conversation list |
| 19 | GET | /conversations/{id}/prompts | `get_conversation_prompts` | 895 | KEEP | Prompt history |
| 20 | GET | /conversations/{id}/pipeline | `get_conversation_pipeline` | 940 | KEEP | Pipeline status for conv |
| 21 | GET | /health | `get_health` | 966 | KEEP | System health |
| 22 | GET | /stats | `get_system_stats` | 980 | KEEP | System statistics |
| 23 | GET | /pipeline-health | `get_pipeline_health` | 991 | DEPRECATE | Returns deprecated status |
| 24 | GET | /unified-pipeline/health | `get_unified_pipeline_health` | 1326 | KEEP | Spec 042 pipeline health |
| 25 | GET | /processing-stats | `get_processing_stats` | 1020 | KEEP | Processing statistics |
| 26 | GET | /errors | `get_recent_errors` | 1060 | KEEP | Error log viewer |
| 27 | GET | /audit-logs | `get_audit_logs` | 1100 | KEEP | Audit trail |
| 28 | GET | /metrics/overview | `get_metrics_overview` | 1140 | KEEP | Aggregate metrics |

**Issues**:
- #16-17: Prompt viewer stubs need implementation (can now query `ready_prompts` and `generated_prompts` tables)
- #23: `/pipeline-health` should be removed or redirect to `/unified-pipeline/health`

### 4.3 Admin Debug Routes (`/admin/debug` — ~20 endpoints)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | GET | /voice/conversations | `list_voice_conversations` | 68 | KEEP | Voice call list |
| 2 | GET | /voice/conversations/{id} | `get_voice_conversation` | 115 | KEEP | Voice call detail |
| 3 | GET | /voice/health | `get_voice_health` | 160 | KEEP | ElevenLabs health |
| 4 | GET | /voice/stats | `get_voice_stats` | 200 | KEEP | Voice statistics |
| 5 | POST | /voice/test-call | `create_test_call` | 240 | KEEP | Test voice call |
| 6 | POST | /context-test | `context_test` | 300 | KEEP | Context engine test |
| 7 | GET | /text/conversations | `list_text_conversations` | 370 | KEEP | Text conversation list |
| 8 | GET | /text/conversations/{id} | `get_text_conversation` | 415 | KEEP | Text conversation detail |
| 9 | GET | /text/conversations/{id}/prompt | `get_conversation_prompt` | 460 | KEEP | Generated prompt |
| 10 | POST | /memory-test | `memory_test` | 506 | KEEP | Uses SupabaseMemory (post-042) |
| 11 | POST | /prompts/{user_id}/preview | `preview_next_prompt` | 643 | MODIFY | Returns deprecated stub |
| 12 | GET | /text/pipeline/{conv_id} | `get_pipeline_status` | 1197 | MODIFY | Uses OLD stage names |
| 13 | GET | /text/threads | `list_threads` | 1297 | KEEP | Thread viewer |
| 14 | GET | /text/thoughts | `list_thoughts` | 1330 | KEEP | Thought viewer |
| 15 | GET | /stats | `get_system_stats` | 1100 | KEEP | System overview |
| 16 | GET | /text/scoring-test | `scoring_test` | 550 | KEEP | Scoring test |
| 17 | GET | /text/prompt-test | `prompt_test` | 590 | KEEP | Prompt test |
| 18 | POST | /pipeline-test | `pipeline_test` | 700 | KEEP | Pipeline integration test |
| 19 | GET | /users/search | `search_users` | 800 | KEEP | User search |
| 20 | GET | /text/conversations/{id}/messages | `get_messages` | 900 | KEEP | Message viewer |

**Issues**:
- #11: `preview_next_prompt` needs to use new `PromptGenerator` (from `nikita/prompts/generator.py`)
- #12: `get_pipeline_status` uses old hardcoded stage names (see Section 3)

### 4.4 Voice Routes (`/api/v1/voice` — 7 endpoints)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | GET | /availability | `check_availability` | 68 | KEEP | |
| 2 | POST | /initiate | `initiate_call` | 110 | KEEP | |
| 3 | POST | /pre-call | `pre_call_setup` | 200 | KEEP | |
| 4 | POST | /server-tool | `handle_server_tool` | 300 | KEEP | |
| 5 | POST | /webhook | `handle_webhook` | 500 | KEEP | Uses unified pipeline |
| 6 | POST | /callback | `handle_callback` | 700 | KEEP | |
| 7 | GET | /health | `get_health` | 900 | KEEP | |

**Verdict**: All CLEAN. Voice routes correctly use unified pipeline at `voice.py:727`.

### 4.5 Onboarding Routes (`/api/v1/onboarding` — 7 endpoints)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | POST | /start | `start_onboarding` | 68 | KEEP | |
| 2 | POST | /server-tool | `handle_server_tool` | 150 | KEEP | |
| 3 | POST | /webhook | `handle_webhook` | 300 | KEEP | |
| 4 | GET | /status/{user_id} | `get_status` | 400 | KEEP | |
| 5 | POST | /complete | `complete_onboarding` | 450 | KEEP | |
| 6 | POST | /skip | `skip_onboarding` | 500 | KEEP | |
| 7 | GET | /health | `get_health` | 550 | KEEP | |

**Verdict**: All CLEAN. No stale references.

### 4.6 Task Routes (`/api/v1/tasks` — 9 endpoints, 1 duplicate)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | POST | /decay | `run_decay` | 58 | KEEP | pg_cron hourly |
| 2 | POST | /deliver | `deliver_messages` | 124 | KEEP | Scheduled message delivery |
| 3 | POST | /summary | `generate_summaries` | 278 | MODIFY | Returns deprecated stub |
| 4 | POST | /cleanup | `cleanup_registrations` | 465 | KEEP | Cleanup expired |
| 5 | POST | /process-conversations | `process_conversations` | 505 | FIX | Stale import (CRIT-1) |
| 6 | POST | /touchpoints | `deliver_scheduled_touchpoints` | 612 | KEEP | Spec 025 |
| 7 | POST | /detect-stuck | `detect_stuck_conversations` | 661 | KEEP | |
| 8 | POST | /touchpoints | `process_touchpoints` | 733 | DELETE | DUPLICATE (CRIT-2) |
| 9 | POST | /recover-stuck | `recover_stuck_conversations` | 792 | KEEP | |

### 4.7 Telegram Routes (`/api/v1/telegram` — 3 endpoints)

| # | Method | Path | Handler | Line | Classification | Notes |
|---|--------|------|---------|------|----------------|-------|
| 1 | POST | /webhook | `handle_webhook` | 68 | KEEP | Main webhook |
| 2 | POST | /auth/confirm | `confirm_auth` | 800 | KEEP | OTP confirmation |
| 3 | POST | /set-webhook | `set_webhook` | 1050 | KEEP | Webhook setup |

**Verdict**: All CLEAN.

---

## 5. ADMIN MUTATION AUDIT

### Existing Mutations (6 — all KEEP)

| Mutation | Endpoint | Line | Notes |
|----------|----------|------|-------|
| Set score | `PUT /admin/users/{id}/score` | admin.py:468 | |
| Set chapter | `PUT /admin/users/{id}/chapter` | admin.py:525 | |
| Set game status | `PUT /admin/users/{id}/status` | admin.py:573 | |
| Set engagement | `PUT /admin/users/{id}/engagement` | admin.py:616 | |
| Reset boss | `POST /admin/users/{id}/reset-boss` | admin.py:670 | |
| Clear engagement | `POST /admin/users/{id}/clear-engagement` | admin.py:715 | |

### Missing Mutations (Recommended for Portal Respec)

| Mutation | Why Needed | Priority |
|----------|-----------|----------|
| Trigger pipeline for user | Admin can re-run pipeline on demand | HIGH |
| View/search memory facts | Browse pgVector facts per user | HIGH |
| Delete memory fact | Clean up incorrect facts | MEDIUM |
| View ready_prompts | See cached prompts per user | HIGH |
| Delete ready_prompt | Force prompt regeneration | MEDIUM |
| Set user metrics (individual) | Fine-tune intimacy/passion/trust/secureness | MEDIUM |
| Trigger touchpoint | Force Nikita-initiated message | LOW |
| View pipeline execution history | Timeline of pipeline runs per user | HIGH |

---

## 6. SCHEMA MISMATCH REPORT

### admin.py schemas (admin.py:384 lines)
- `PipelineStageStatus` schema defines `stage_name: str, stage_number: int` — compatible with both old and new names
- `AdminPipelineHealthResponse` references `stage_definitions` — used by new unified endpoint
- No stale schema references to deleted modules

### monitoring.py schemas (349 lines)
- `ProcessingStatsResponse` — still valid
- `PipelineMetricsResponse` — still valid
- No stale references

### admin_debug.py schemas (532 lines)
- `PipelineStatusResponse` — used by debug endpoint with old stage names
- `PipelineStageStatus` — compatible but populated with wrong names

### portal.py schemas (184 lines)
- All clean, no pipeline references

---

## 7. DATA GAPS FOR NEW PORTAL

### Available Data (can serve today)
- User stats, metrics, engagement, vices, scores, boss status
- Conversation list + detail + messages
- Daily summaries
- Decay status
- Score history (chart data)
- Memory facts (via SupabaseMemory)
- Pipeline health (via unified endpoint)

### Missing Data Endpoints (need for redesigned portal)
1. **Pipeline execution timeline** — no endpoint returns per-user pipeline run history with stage timings
2. **Memory fact viewer** — admin can see facts but no user-facing browsing
3. **Ready prompt viewer** — no endpoint exposes cached ready_prompts
4. **Engagement history** — no endpoint for engagement state transition timeline
5. **Active threads summary** — threads endpoint exists in debug but not in portal
6. **Active thoughts summary** — thoughts endpoint exists in debug but not in portal

---

## 8. SUMMARY & RECOMMENDATIONS

### Immediate Fixes (before any new development)
1. **CRIT-1**: Fix `tasks.py:529` stale import — move `detect_stale_sessions` to pipeline module or conversation_repository
2. **CRIT-2**: Delete duplicate `tasks.py:733` route
3. Update `admin_debug.py:1197-1294` pipeline stage names to match Spec 042

### Before Portal Respec
4. Implement prompt viewer endpoints (`admin.py:797-828` stubs)
5. Remove deprecated `/pipeline-health` endpoint (`admin.py:991`)
6. Replace deprecated stubs: summary generation (`tasks.py:412`), prompt preview (`admin_debug.py:663`)

### New Endpoints for Portal
7. Pipeline execution history per user (stage timings, success/failure)
8. Memory fact browser (search, filter, delete)
9. Engagement state transition history
10. User-facing thread/thought summary (currently admin-only)

### Endpoint Count Summary

| Route File | Total | KEEP | MODIFY | DEPRECATE | DELETE | FIX |
|------------|-------|------|--------|-----------|--------|-----|
| portal.py | 13 | 13 | 0 | 0 | 0 | 0 |
| admin.py | 28 | 25 | 2 | 1 | 0 | 0 |
| admin_debug.py | ~20 | 18 | 2 | 0 | 0 | 0 |
| tasks.py | 9 | 6 | 1 | 0 | 1 | 1 |
| voice.py | 7 | 7 | 0 | 0 | 0 | 0 |
| onboarding.py | 7 | 7 | 0 | 0 | 0 | 0 |
| telegram.py | 3 | 3 | 0 | 0 | 0 | 0 |
| **TOTAL** | **~87** | **79** | **5** | **1** | **1** | **1** |

**Bottom line**: 91% of endpoints are CLEAN. 2 CRITICAL issues (stale import + duplicate route), 5 need modification, 1 deprecated. The API surface is healthy for a portal redesign — the main work is adding NEW endpoints for pipeline visibility, memory browsing, and prompt viewing.
