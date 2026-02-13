# Plan: Spec 049 — Game Mechanics Remediation

## Implementation Phases

### Phase 1: Pipeline Filtering (US-3) — 30 min
**Files**: `nikita/pipeline/orchestrator.py`, `tests/pipeline/test_orchestrator.py`

Add early return in `PipelineOrchestrator.process()` after user load (line ~121) when `game_status in ("game_over", "won")`. Return a result dict with `skipped=True, reason="game_status:{status}"`.

### Phase 2: Boss Fight Timeout (US-1) — 1h
**Files**: `nikita/api/routes/tasks.py`, `nikita/engine/chapters/boss.py`, tests

1. Add `resolve_stale_boss_fights()` method to BossStateMachine
2. Add `/tasks/boss-timeout` endpoint to tasks.py
3. SQL: query users WHERE game_status='boss_fight' AND updated_at < now()-24h
4. For each: set game_status='active', increment boss_attempts, send Telegram msg
5. pg_cron: every 6h call the endpoint

### Phase 3: BreakupManager Wiring (US-2) — 1h
**Files**: `nikita/pipeline/stages/conflict.py`, `nikita/conflicts/breakup.py`, tests

1. Import BreakupManager in ConflictStage
2. After conflict detection, call `breakup_manager.check_threshold(user_id, session)`
3. If threshold met, set `ctx.game_over_triggered = True`
4. In message_handler post-pipeline, check `result.get("game_over_triggered")` and persist

### Phase 4: Decay Notification (US-4) — 30 min
**Files**: `nikita/engine/decay/processor.py`, tests

1. Add `telegram_bot` parameter to DecayProcessor (optional)
2. In `_handle_game_over()`, if bot available, send notification message
3. Update tasks.py decay endpoint to pass bot instance

### Phase 5: Won State Content (US-5) — 15 min
**Files**: `nikita/platforms/telegram/message_handler.py`, tests

1. Add list of 5+ won messages
2. Random selection in `_send_game_status_response()`

## Dependencies
- Phase 1 has no deps (do first)
- Phases 2-5 are independent of each other
- Phase 3 depends on BreakupManager existing code being correct

## Risk Assessment
- LOW: All changes are additive, no breaking changes
- Boss timeout SQL query needs index on (game_status, updated_at) — verify exists
