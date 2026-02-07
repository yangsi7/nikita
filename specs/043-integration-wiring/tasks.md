# Spec 043: Integration Wiring Fixes — Tasks

**Status**: DRAFT
**Created**: 2026-02-07
**Plan**: [plan.md](plan.md)

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1: Feature Flags + Cache Sync | 3 | 0 | Pending |
| Phase 2: Routing + Bootstrap | 3 | 0 | Pending |
| Phase 3: Testing | 5 | 0 | Pending |
| **Total** | **11** | **0** | **Pending** |

---

## Phase 1: Feature Flag Activation + Cache Sync

### T1.1: Change Feature Flag Defaults
- **Status**: [ ] Pending
- **Gap**: GAP-2 (Feature flags default OFF)
- **File**: `nikita/config/settings.py:132-142`
- **Description**: Change `unified_pipeline_enabled` default from `False` to `True` and `unified_pipeline_rollout_pct` from `0` to `100`.
- **ACs**:
  - [ ] AC-1.1.1: `unified_pipeline_enabled` defaults to `True` in Settings model
  - [ ] AC-1.1.2: `unified_pipeline_rollout_pct` defaults to `100` in Settings model
  - [ ] AC-1.1.3: `is_unified_pipeline_enabled_for_user()` returns `True` for any user with defaults
  - [ ] AC-1.1.4: Setting `UNIFIED_PIPELINE_ENABLED=false` env var overrides to `False`
- **Est. Tests**: 4

### T1.2: Voice Prompt Cache Sync in PromptBuilder
- **Status**: [ ] Pending
- **Gap**: GAP-1 (Voice prompt cache NOT WIRED)
- **File**: `nikita/pipeline/stages/prompt_builder.py:345-389`
- **Description**: After `_store_prompt()` writes voice prompt to `ready_prompts`, also update `user.cached_voice_prompt` and `user.cached_voice_prompt_at` for backward compatibility with outbound calls.
- **ACs**:
  - [ ] AC-1.2.1: `_store_prompt()` calls `_sync_cached_voice_prompt()` when platform is "voice"
  - [ ] AC-1.2.2: `user.cached_voice_prompt` updated with new prompt text
  - [ ] AC-1.2.3: `user.cached_voice_prompt_at` updated with current timestamp
  - [ ] AC-1.2.4: Sync failure logged but does not fail the stage
- **Est. Tests**: 4

### T1.3: Outbound Voice Ready Prompt Lookup
- **Status**: [ ] Pending
- **Gap**: GAP-1 (Voice prompt cache NOT WIRED)
- **File**: `nikita/agents/voice/service.py:108-125`
- **Description**: Add `ready_prompts` table lookup in `initiate_call()` before falling back to `user.cached_voice_prompt`. Mirrors the pattern already used in `inbound.py:444`.
- **ACs**:
  - [ ] AC-1.3.1: `initiate_call()` tries `ready_prompts(platform='voice')` first
  - [ ] AC-1.3.2: Falls back to `user.cached_voice_prompt` if no ready_prompt
  - [ ] AC-1.3.3: Falls back to static prompt if neither exists
  - [ ] AC-1.3.4: Logging includes prompt source ("ready_prompt", "cached", "fallback")
- **Est. Tests**: 3

---

## Phase 2: Pipeline Routing + Onboarding Bootstrap

### T2.1: Clean Up Dead Legacy Branch
- **Status**: [ ] Pending
- **Gap**: GAP-3 (pg_cron routing)
- **File**: `nikita/api/routes/tasks.py:549-586`
- **Description**: Remove the dead `else` branch that skips all conversations when `unified_pipeline_enabled=False`. With T1.1, this branch is dead code. Replace with error log for safety.
- **ACs**:
  - [ ] AC-2.1.1: Legacy skip branch replaced with explicit error log
  - [ ] AC-2.1.2: Pipeline path is the only active path for `process-conversations`
  - [ ] AC-2.1.3: Comment documents the change and rollback mechanism
- **Est. Tests**: 2

### T2.2: Onboarding Pipeline Bootstrap
- **Status**: [ ] Pending
- **Gap**: GAP-5 (Onboarding-to-pipeline gap)
- **File**: `nikita/onboarding/handoff.py:386-398`
- **Description**: After sending first Telegram message in `execute_handoff()`, trigger a non-blocking pipeline run to generate initial personalized prompts for the user.
- **ACs**:
  - [ ] AC-2.2.1: `execute_handoff()` calls `_bootstrap_pipeline()` after sending first message
  - [ ] AC-2.2.2: Pipeline generates text + voice prompts for new user
  - [ ] AC-2.2.3: Pipeline failure does NOT fail the handoff (non-blocking)
  - [ ] AC-2.2.4: Logging includes pipeline bootstrap result
  - [ ] AC-2.2.5: Skipped if `unified_pipeline_enabled=False`
- **Est. Tests**: 5

### T2.3: Daily Summary LLM Generation
- **Status**: [ ] Pending
- **Gap**: GAP-6 (Daily summary broken)
- **File**: `nikita/api/routes/tasks.py:409-415`
- **Description**: Replace hardcoded placeholder `"Daily summary generation deprecated (Spec 042)"` with Claude Haiku LLM call that generates actual nikita_summary_text from conversation data.
- **ACs**:
  - [ ] AC-2.3.1: Summary endpoint calls Claude Haiku to generate nikita_summary_text
  - [ ] AC-2.3.2: Summary includes key_moments list extracted from conversations
  - [ ] AC-2.3.3: Summary includes emotional_tone analysis
  - [ ] AC-2.3.4: Falls back to basic summary (conversation count + score change) if LLM fails
  - [ ] AC-2.3.5: LLM call uses timeout (10s) to prevent pg_cron job delays
- **Est. Tests**: 5

---

## Phase 3: Testing

### T3.1: Feature Flag Tests
- **Status**: [ ] Pending
- **File**: `tests/pipeline/test_feature_flags.py` (new)
- **Description**: Test feature flag defaults, env var override, and rollout logic.
- **ACs**:
  - [ ] AC-3.1.1: Default Settings has `unified_pipeline_enabled=True`
  - [ ] AC-3.1.2: Default Settings has `unified_pipeline_rollout_pct=100`
  - [ ] AC-3.1.3: `is_unified_pipeline_enabled_for_user()` returns True with defaults
  - [ ] AC-3.1.4: Override via env var `UNIFIED_PIPELINE_ENABLED=false` returns False
- **Est. Tests**: 4

### T3.2: Voice Prompt Cache Sync Tests
- **Status**: [ ] Pending
- **File**: `tests/pipeline/test_cache_sync.py` (new)
- **Description**: Test that prompt_builder syncs voice prompt to both ready_prompts and cached_voice_prompt.
- **ACs**:
  - [ ] AC-3.2.1: Voice prompt stored in `ready_prompts` table
  - [ ] AC-3.2.2: Voice prompt synced to `user.cached_voice_prompt`
  - [ ] AC-3.2.3: Text prompt NOT synced to `cached_voice_prompt` (voice only)
  - [ ] AC-3.2.4: Sync failure does not fail the pipeline stage
- **Est. Tests**: 4

### T3.3: Outbound Voice Prompt Loading Tests
- **Status**: [ ] Pending
- **File**: `tests/agents/voice/test_outbound_prompt.py` (new)
- **Description**: Test outbound call prompt loading chain: ready_prompt → cached → fallback.
- **ACs**:
  - [ ] AC-3.3.1: Outbound call uses ready_prompt when available
  - [ ] AC-3.3.2: Outbound call uses cached_voice_prompt when no ready_prompt
  - [ ] AC-3.3.3: Outbound call uses static fallback when nothing cached
- **Est. Tests**: 3

### T3.4: Onboarding Bootstrap Tests
- **Status**: [ ] Pending
- **File**: `tests/onboarding/test_pipeline_bootstrap.py` (new)
- **Description**: Test pipeline bootstrap after onboarding handoff.
- **ACs**:
  - [ ] AC-3.4.1: `execute_handoff()` triggers pipeline bootstrap
  - [ ] AC-3.4.2: Pipeline failure does not fail handoff
  - [ ] AC-3.4.3: Pipeline generates prompts for new user
  - [ ] AC-3.4.4: Bootstrap skipped if flag disabled
- **Est. Tests**: 4

### T3.5: Daily Summary LLM Tests
- **Status**: [ ] Pending
- **File**: `tests/api/routes/test_summary_llm.py` (new)
- **Description**: Test LLM-powered daily summary generation.
- **ACs**:
  - [ ] AC-3.5.1: LLM generates summary from conversation data (mocked)
  - [ ] AC-3.5.2: Fallback to basic summary on LLM failure
  - [ ] AC-3.5.3: Summary includes key_moments and emotional_tone
  - [ ] AC-3.5.4: LLM timeout (10s) prevents blocking
- **Est. Tests**: 4

---

## Estimated Test Count

| Phase | Tests |
|-------|-------|
| Phase 1 | 11 |
| Phase 2 | 12 |
| Phase 3 | 19 |
| **Total** | **~42** |

---

## Version History

| Date | Change | By |
|------|--------|-----|
| 2026-02-07 | Initial task breakdown from gap audit | system-auditor |
