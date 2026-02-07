# Spec 043: Integration Wiring Fixes

**Status**: DRAFT
**Created**: 2026-02-07
**Depends On**: Spec 042 (Unified Pipeline)

---

## Problem Statement

Spec 042 built the unified pipeline architecture (9 stages, SupabaseMemory, PromptBuilderStage, ReadyPromptRepository), but left **5 confirmed integration gaps** that prevent the pipeline from functioning in production:

1. **Feature flags default OFF** - Pipeline is dormant (`unified_pipeline_enabled=False`, `unified_pipeline_rollout_pct=0`)
2. **Voice prompt cache not synced** - `prompt_builder.py` writes to `ready_prompts` but NOT to `user.cached_voice_prompt`; outbound calls (`service.py:110`) still read `user.cached_voice_prompt`
3. **pg_cron legacy fallback is a dead end** - When `unified_pipeline_enabled=False` (current production), `tasks.py:578-586` skips ALL conversations with a warning log
4. **Text agent ready_prompt loading gated behind disabled flag** - `agent.py:309` checks `is_unified_pipeline_enabled_for_user()` which returns False
5. **Onboarding handoff has no pipeline bootstrap** - `handoff.py:execute_handoff()` sends a first Telegram message but never triggers a pipeline run for initial personalization
6. **Daily summary generation broken** - `tasks.py:411` returns hardcoded placeholder `"Daily summary generation deprecated (Spec 042)"` instead of LLM-generated text

---

## Functional Requirements

### FR-001: Feature Flag Activation
Enable unified pipeline for all users in production.

**Evidence**: `config/settings.py:133-142` — `unified_pipeline_enabled` defaults to `False`, `unified_pipeline_rollout_pct` defaults to `0`. No env var set in Cloud Run, Dockerfile, or any `.env` file.

**Acceptance Criteria**:
- AC-001.1: `unified_pipeline_enabled` defaults to `True`
- AC-001.2: `unified_pipeline_rollout_pct` defaults to `100`
- AC-001.3: Cloud Run env var `UNIFIED_PIPELINE_ENABLED=true` documented
- AC-001.4: Rollback: can set `UNIFIED_PIPELINE_ENABLED=false` via env var to disable

### FR-002: Voice Prompt Cache Sync
When prompt_builder generates a voice prompt and stores in `ready_prompts`, also update `user.cached_voice_prompt` for backward compatibility with outbound calls.

**Evidence**:
- `pipeline/stages/prompt_builder.py:345-389` writes to `ready_prompts` via `ReadyPromptRepository.set_current()`
- `agents/voice/service.py:110` reads `user.cached_voice_prompt` for outbound calls
- `agents/voice/inbound.py:444` reads `ready_prompts` first (correct), then falls back to `cached_voice_prompt` (line 448)
- **Gap**: `prompt_builder.py` has ZERO references to `cached_voice_prompt` — outbound calls always get stale/None cache

**Acceptance Criteria**:
- AC-002.1: After `PromptBuilderStage._store_prompt()` saves voice prompt to `ready_prompts`, it also updates `user.cached_voice_prompt` and `user.cached_voice_prompt_at`
- AC-002.2: Outbound calls via `service.py:initiate_call()` attempt `ready_prompts` first, fall back to `cached_voice_prompt`
- AC-002.3: Test verifies voice prompt stored in both locations

### FR-003: pg_cron Pipeline Routing Fix
When `unified_pipeline_enabled=False`, `process-conversations` endpoint should NOT silently skip all conversations. Either enable the flag or provide a working legacy fallback.

**Evidence**: `api/routes/tasks.py:549-586` — When `unified_pipeline_enabled=False`, it logs a warning and sets `processed_count=0`, meaning ALL detected stale conversations are skipped.

**Acceptance Criteria**:
- AC-003.1: With FR-001 active, `process-conversations` routes through `PipelineOrchestrator`
- AC-003.2: Pipeline processing logs conversation_id, user_id, and result for each processed conversation
- AC-003.3: Test confirms pipeline processes at least one conversation when flag is enabled

### FR-004: Text Agent Ready Prompt Loading
Text agent should load pre-built prompts from `ready_prompts` when available.

**Evidence**:
- `agents/text/agent.py:309` checks `settings.is_unified_pipeline_enabled_for_user(user.id)`
- This returns `False` because flag defaults are OFF (GAP-2)
- When `True`, it correctly loads from `ReadyPromptRepository` via `_try_load_ready_prompt()` (agent.py:202-266)
- Falls back to `_build_system_prompt_legacy()` (line 326) which uses static NIKITA_PERSONA

**Acceptance Criteria**:
- AC-004.1: With FR-001 active, `build_system_prompt()` loads from `ready_prompts` table
- AC-004.2: If no ready_prompt exists, falls back to legacy prompt with WARNING log
- AC-004.3: Test verifies prompt loaded from ready_prompts when available

### FR-005: Onboarding Pipeline Bootstrap
After onboarding completes, trigger an initial pipeline run to generate personalized prompts before the user's first text message.

**Evidence**: `onboarding/handoff.py:336-421` — `execute_handoff()` does:
1. Generate social circle (line 371)
2. Generate first message (line 388)
3. Send via Telegram (line 391)
4. **NO pipeline trigger** — first text message uses static fallback

**Acceptance Criteria**:
- AC-005.1: After onboarding completes, `execute_handoff()` triggers a pipeline run for the user
- AC-005.2: Pipeline generates initial text + voice prompts using onboarding profile data
- AC-005.3: First text message after onboarding uses personalized prompt (not static fallback)
- AC-005.4: Pipeline trigger is non-blocking (failure doesn't break handoff)

### FR-006: Daily Summary LLM Generation
Replace hardcoded placeholder in `tasks.py` summary endpoint with actual LLM-generated summaries, either via unified pipeline or standalone.

**Evidence**: `api/routes/tasks.py:409-415` — After Spec 042 deleted MetaPromptService, summary generation was replaced with:
```python
summary_data = {
    "summary_text": "Daily summary generation deprecated (Spec 042)",
    "key_moments": [],
    "emotional_tone": "neutral",
}
```

**Acceptance Criteria**:
- AC-006.1: Daily summaries use Claude Haiku to generate nikita_summary_text from conversation data
- AC-006.2: Summary includes key_moments extracted from conversations
- AC-006.3: Summary includes emotional_tone analysis
- AC-006.4: Graceful fallback to basic summary if LLM fails

---

## Non-Functional Requirements

### NFR-001: Backward Compatibility
All changes must be backward-compatible via feature flag override. Setting `UNIFIED_PIPELINE_ENABLED=false` must restore pre-042 behavior.

### NFR-002: No Breaking Changes
Existing inbound voice path (`inbound.py` ready_prompt → cached_voice_prompt → fallback) must not be altered in a breaking way.

### NFR-003: Performance
- Voice prompt loading must remain <100ms (pre-call latency requirement)
- Text prompt loading from ready_prompts must be <50ms
- Pipeline bootstrap after onboarding must complete <30s

### NFR-004: Observability
All gap fixes must include structured logging with `user_id`, `conversation_id`, and timing metrics.

---

## User Stories

### US-1: Voice Personalization Works
**As a** user making a voice call,
**I want** my voice agent prompt to reflect my recent text conversations and profile,
**So that** Nikita remembers what we talked about across channels.

**Acceptance Criteria**:
- AC-US1.1: Inbound voice call loads prompt from `ready_prompts(platform='voice')` when pipeline active
- AC-US1.2: Outbound voice call loads prompt from `ready_prompts` OR `cached_voice_prompt`
- AC-US1.3: Pipeline stores voice prompt in both `ready_prompts` AND `user.cached_voice_prompt`

### US-2: Text Personalization Works
**As a** user sending text messages via Telegram,
**I want** Nikita's system prompt to include my memory, vices, emotional state, and context,
**So that** conversations feel personalized and continuous.

**Acceptance Criteria**:
- AC-US2.1: Text agent loads pre-built prompt from `ready_prompts(platform='text')` when available
- AC-US2.2: If no ready_prompt, falls back to legacy prompt generation with warning
- AC-US2.3: pg_cron `process-conversations` triggers pipeline to refresh prompts

### US-3: Onboarding Bootstraps Pipeline
**As a** newly onboarded user,
**I want** my first text conversation with Nikita to reflect what I shared during onboarding,
**So that** the transition feels seamless and personal.

**Acceptance Criteria**:
- AC-US3.1: After `execute_handoff()` completes, pipeline generates initial prompts
- AC-US3.2: First text message after onboarding uses pipeline-generated prompt
- AC-US3.3: Pipeline failure during bootstrap does not block handoff

---

## Data Model Changes

### No Schema Changes Required

All necessary tables and columns already exist:
- `ready_prompts` table (Migration 0009, Spec 042)
- `users.cached_voice_prompt` column (Migration 0008)
- `users.cached_voice_prompt_at` column (Migration 0008)

### Configuration Changes

| Setting | Current Default | New Default | Rationale |
|---------|----------------|-------------|-----------|
| `unified_pipeline_enabled` | `False` | `True` | Pipeline built but dormant |
| `unified_pipeline_rollout_pct` | `0` | `100` | No reason for gradual rollout; pipeline tested |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Pipeline bugs in production | MEDIUM | Feature flag rollback (`UNIFIED_PIPELINE_ENABLED=false`) |
| Ready prompt stale after flag change | LOW | Fallback to legacy prompt generation exists |
| Onboarding bootstrap timeout | LOW | Non-blocking trigger, handoff succeeds regardless |
| Daily summary LLM cost increase | LOW | Claude Haiku (~$0.001/summary), capped at 50 users |
| Prompt builder concurrent writes | LOW | ReadyPromptRepository.set_current() is atomic (deactivate+insert) |

---

## Files to Modify

| File | Change | Gap |
|------|--------|-----|
| `nikita/config/settings.py:133-142` | Change defaults to `True`/`100` | GAP-2 |
| `nikita/pipeline/stages/prompt_builder.py:345-389` | Add `cached_voice_prompt` sync | GAP-1 |
| `nikita/agents/voice/service.py:108-125` | Add `ready_prompts` lookup before `cached_voice_prompt` | GAP-1 |
| `nikita/api/routes/tasks.py:549-586` | Remove legacy fallback branch (now dead code) | GAP-3 |
| `nikita/api/routes/tasks.py:409-415` | Replace placeholder with LLM generation | GAP-6 |
| `nikita/onboarding/handoff.py:386-398` | Add pipeline bootstrap trigger | GAP-5 |
| Tests: 6+ new test files | Cover all gap fixes | All |
