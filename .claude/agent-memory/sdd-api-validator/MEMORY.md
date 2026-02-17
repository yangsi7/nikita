# SDD API Validator Memory — Nikita Project

## Backend Architecture
- FastAPI backend with route files: portal.py (13 endpoints), admin.py (28), admin_debug.py (~20), tasks.py (9), voice.py (7), onboarding.py (7), telegram.py (3)
- Total ~87 endpoints
- Schemas in: `nikita/api/schemas/` (admin.py, portal.py, game.py, monitoring.py, user.py)
- Auth: Supabase JWT via dependency injection (`get_current_user`, `get_current_admin_user`)
- Mutations use `AdminResetResponse` pattern (`success: bool, message: str`)

## Spec 042 Pipeline Architecture
- 9 stages: extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder
- Orchestrator at `nikita/pipeline/orchestrator.py`
- Old stage names in `admin_debug.py:1197-1294` are stale (Ingestion, Entity Extraction, etc.)
- Pipeline status endpoints fixed at admin_debug.py:1306-1382 (uses correct Spec 042 names)

## Known Issues (Feb 2026)
- Stale import: `tasks.py:646` imports `nikita.context.session_detector` (deleted module)
- Duplicate route: `POST /touchpoints` at lines 731 AND 852 in tasks.py
- Deprecated endpoint: `admin.py:1225-1238` `/pipeline-health` returns 410 Gone (replaced by `/unified-pipeline/health`)

## Validation Patterns
- API audit doc at `docs-to-process/20260207-api-validation-spec042.md` has stale line numbers (audit was done on older file state)
- Always verify line numbers against current code — they drift between sessions
- `POST /tasks/summary` at tasks.py:395 is a full implementation (generates LLM summaries via PromptGenerator)
- Portal endpoints (all 13) are CLEAN — no stale references
- Admin endpoints (28/28) IMPLEMENTED — prompt viewer works (admin.py:987-1067)
- Prompt preview endpoint WORKING at admin_debug.py:643-757 (uses PromptBuilderStage)

## Spec 044 Learnings (2026-02-08)
- Frontend-heavy specs still need backend API contracts validated
- Missing error handling is CRITICAL even if endpoints seem "simple"
- Input validation gaps (missing Field() bounds) are common in mutation endpoints
- Rate limiting + caching specs often missing in frontend-focused specs
- Existing endpoint documentation != API contract (need explicit schemas + error codes)
- FR-029 pattern: new mutation endpoints need FULL Pydantic models with validators, not just stub types
