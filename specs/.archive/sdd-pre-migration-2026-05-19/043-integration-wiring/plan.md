# Spec 043: Integration Wiring Fixes — Implementation Plan

**Status**: DRAFT
**Created**: 2026-02-07
**Spec**: [spec.md](spec.md)

---

## Architecture Overview

```
CURRENT STATE (broken):
  pg_cron → tasks.py → unified_pipeline_enabled=False → SKIP ALL
  Text msg → agent.py → is_unified_pipeline_enabled=False → static fallback
  Voice inbound → inbound.py → ready_prompts (empty) → cached_voice_prompt (stale/None) → fallback
  Voice outbound → service.py → cached_voice_prompt (never written by pipeline) → fallback
  Onboarding → handoff.py → send text msg → NO pipeline bootstrap

TARGET STATE (fixed):
  pg_cron → tasks.py → unified_pipeline_enabled=True → PipelineOrchestrator → ready_prompts
  Text msg → agent.py → ready_prompts(text) → personalized prompt
  Voice inbound → inbound.py → ready_prompts(voice) → personalized prompt
  Voice outbound → service.py → ready_prompts(voice) → cached_voice_prompt → personalized prompt
  Onboarding → handoff.py → send text + trigger pipeline → ready_prompts populated
  Pipeline → prompt_builder → ready_prompts + user.cached_voice_prompt (synced)
```

---

## Phase 1: Feature Flag Activation + Cache Sync (Critical Path)

**Tasks**: T1.1-T1.3
**Duration**: ~30 min
**Impact**: Unblocks all other fixes

### T1.1: Change Feature Flag Defaults
**File**: `nikita/config/settings.py:132-142`
**Change**:
```python
# Before
unified_pipeline_enabled: bool = Field(default=False, ...)
unified_pipeline_rollout_pct: int = Field(default=0, ...)

# After
unified_pipeline_enabled: bool = Field(default=True, ...)
unified_pipeline_rollout_pct: int = Field(default=100, ...)
```
**Rollback**: Set `UNIFIED_PIPELINE_ENABLED=false` env var in Cloud Run

### T1.2: Voice Prompt Cache Sync in PromptBuilder
**File**: `nikita/pipeline/stages/prompt_builder.py:345-389`
**Change**: After storing in `ready_prompts`, also update `user.cached_voice_prompt`
```python
# In _store_prompt(), after repo.set_current():
if platform == "voice":
    await self._sync_cached_voice_prompt(ctx.user_id, prompt_text)

async def _sync_cached_voice_prompt(self, user_id, prompt_text):
    """Sync voice prompt to user.cached_voice_prompt for outbound calls."""
    from nikita.db.repositories.user_repository import UserRepository
    repo = UserRepository(self._session)
    user = await repo.get(user_id)
    if user:
        user.cached_voice_prompt = prompt_text
        user.cached_voice_prompt_at = datetime.now(timezone.utc)
```

### T1.3: Outbound Voice Ready Prompt Lookup
**File**: `nikita/agents/voice/service.py:108-125`
**Change**: Add ready_prompt lookup before cached_voice_prompt fallback
```python
# Try ready_prompts first (unified pipeline path)
prompt_content = await self._try_load_ready_prompt(user_id)
prompt_source = "ready_prompt"

if not prompt_content:
    # Fallback to cached_voice_prompt
    prompt_content = user.cached_voice_prompt
    prompt_source = "cached"

if not prompt_content:
    prompt_content = self._generate_fallback_prompt(user)
    prompt_source = "fallback"
```

---

## Phase 2: Pipeline Routing + Onboarding Bootstrap

**Tasks**: T2.1-T2.3
**Duration**: ~45 min

### T2.1: Clean Up Dead Legacy Branch in tasks.py
**File**: `nikita/api/routes/tasks.py:549-586`
**Change**: Remove the `else` branch that skips all conversations when flag is off. Since flag is now `True` by default, this branch is dead code. Replace with a clear error message.
```python
# Remove lines 578-586 (legacy skip branch)
# Replace with:
else:
    logger.error(
        "unified_pipeline_disabled_but_no_legacy_fallback "
        "conversations_skipped=%d", len(queued_ids)
    )
    processed_count = 0
    failed_ids = [str(cid) for cid in queued_ids]
```

### T2.2: Onboarding Pipeline Bootstrap
**File**: `nikita/onboarding/handoff.py:386-398`
**Change**: After sending first Telegram message, trigger a non-blocking pipeline run.
```python
# After send_result check (line 398):
# Non-blocking pipeline bootstrap (FR-005)
try:
    await self._bootstrap_pipeline(user_id)
except Exception as e:
    logger.warning(f"Pipeline bootstrap failed for user {user_id}: {e}")
```

New method:
```python
async def _bootstrap_pipeline(self, user_id: UUID) -> None:
    """Trigger initial pipeline run for newly onboarded user."""
    from nikita.config.settings import get_settings
    settings = get_settings()
    if not settings.unified_pipeline_enabled:
        return

    from nikita.db.database import get_session_maker
    from nikita.pipeline.orchestrator import PipelineOrchestrator
    from nikita.db.repositories.conversation_repository import ConversationRepository

    async with get_session_maker()() as session:
        # Get most recent conversation for this user
        conv_repo = ConversationRepository(session)
        recent = await conv_repo.get_recent_for_user(user_id, limit=1)
        if recent:
            orchestrator = PipelineOrchestrator(session)
            await orchestrator.process(
                conversation_id=recent[0].id,
                user_id=user_id,
                platform="text",
            )
            await session.commit()
        else:
            logger.info(f"No conversations found for pipeline bootstrap user={user_id}")
```

### T2.3: Daily Summary LLM Generation
**File**: `nikita/api/routes/tasks.py:409-415`
**Change**: Replace placeholder with Claude Haiku LLM call for summary generation.
```python
# Replace hardcoded summary_data with:
summary_data = await _generate_summary_with_llm(
    conversations_data=conversations_data,
    new_threads=new_threads,
    nikita_thoughts=nikita_thoughts,
    user_chapter=user.chapter,
)
```

New function:
```python
async def _generate_summary_with_llm(
    conversations_data, new_threads, nikita_thoughts, user_chapter
) -> dict:
    """Generate daily summary using Claude Haiku."""
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.anthropic import AnthropicModel
        from nikita.config.settings import get_settings

        settings = get_settings()
        if not settings.anthropic_api_key:
            return _fallback_summary(conversations_data)

        prompt = _build_summary_prompt(conversations_data, new_threads, nikita_thoughts, user_chapter)
        model = AnthropicModel("claude-haiku-4-5-20251001", api_key=settings.anthropic_api_key)
        agent = Agent(model=model)
        result = await agent.run(prompt)

        # Parse structured response
        return _parse_summary_response(result.data)
    except Exception as e:
        logger.warning(f"LLM summary generation failed: {e}")
        return _fallback_summary(conversations_data)
```

---

## Phase 3: Testing

**Tasks**: T3.1-T3.4
**Duration**: ~60 min

### T3.1: Feature Flag Tests
- Test `unified_pipeline_enabled=True` default
- Test env var override `UNIFIED_PIPELINE_ENABLED=false`
- Test rollout percentage logic still works

### T3.2: Voice Prompt Cache Sync Tests
- Test `_store_prompt()` updates both `ready_prompts` AND `cached_voice_prompt`
- Test outbound call loads from `ready_prompts` first
- Test fallback chain: ready_prompt → cached_voice_prompt → static

### T3.3: Pipeline Routing Tests
- Test `process-conversations` routes through `PipelineOrchestrator`
- Test pipeline processes conversation and generates prompts
- Test error handling for failed pipeline runs

### T3.4: Onboarding Bootstrap Tests
- Test `execute_handoff()` triggers pipeline after sending first message
- Test pipeline failure doesn't block handoff
- Test pipeline generates initial prompts for new user

### T3.5: Daily Summary Tests
- Test LLM summary generation with mock
- Test fallback to basic summary on LLM failure
- Test summary includes key_moments and emotional_tone

---

## Rollback Strategy

### Level 1: Feature Flag (Instant)
```bash
gcloud run deploy nikita-api --update-env-vars UNIFIED_PIPELINE_ENABLED=false
```
Reverts to pre-042 behavior. Text uses static prompt, voice uses cached_voice_prompt, pg_cron skips processing.

### Level 2: Code Revert (5 min)
```bash
git revert HEAD  # Revert spec 043 commit
gcloud run deploy nikita-api --source . --region us-central1
```

---

## File Change Summary

| File | Lines Changed | Type |
|------|---------------|------|
| `nikita/config/settings.py` | 2 | Default change |
| `nikita/pipeline/stages/prompt_builder.py` | +15 | Cache sync |
| `nikita/agents/voice/service.py` | +20 | Ready prompt lookup |
| `nikita/onboarding/handoff.py` | +25 | Pipeline bootstrap |
| `nikita/api/routes/tasks.py` | +40 | Dead code cleanup + LLM summary |
| `tests/pipeline/test_cache_sync.py` | +80 | New test file |
| `tests/pipeline/test_feature_flags.py` | +50 | New test file |
| `tests/onboarding/test_pipeline_bootstrap.py` | +60 | New test file |
| `tests/api/routes/test_summary_llm.py` | +70 | New test file |
| **Total** | ~360 lines | 5 production + 4 test files |

---

## Dependencies

- **Spec 042**: Unified pipeline must be complete (confirmed: 45/45 tasks DONE)
- **ReadyPromptRepository**: Must exist with `set_current()` and `get_current()` (confirmed: `nikita/db/repositories/ready_prompt_repository.py`)
- **Migration 0009**: `ready_prompts` table must exist (confirmed)
- **Migration 0008**: `cached_voice_prompt` column must exist (confirmed)
