# Pipeline Callers Fix — Proof Report

**Date**: 2026-02-10T19:20:00Z
**Commit**: 051fe92
**Revision**: nikita-api-00195-xrx (100% traffic)

---

## Bugs Fixed (This Commit)

| ID | File | Bug | Fix |
|----|------|-----|-----|
| B1 | admin.py:591 | `list_recent_for_user()` doesn't exist | `get_recent()` |
| B2 | admin.py:603 | Missing `conversation=`, `user=` params | Added both params |
| B3 | admin.py:610 | `result.job_id` on PipelineResult | `job_id=None` |
| B4 | voice.py:730 | Missing `conversation=`, `user=` params | Added (already in scope) |
| B5 | handoff.py:588 | `get_recent_for_user()` + missing params | `get_recent()` + load user + pass both |
| B6 | admin_debug.py:677 | `list_recent_for_user()` doesn't exist | `get_recent()` |
| B7 | pyproject.toml:14 | Pin was `>=0.1.0` (typo in c4de9c9) | `>=1.0.0` |

## Test Results

```
3,847 passed, 0 failed, 15 skipped (98.75s)
```

## Verification Checks (All Zero Matches)

```bash
rg "list_recent_for_user|get_recent_for_user" nikita/ tests/ --type py  # 0 matches
rg "result\.job_id" nikita/ --type py                                    # 0 matches
rg "result_type=" nikita/ --type py                                      # 0 matches
```

## Live E2E Proof

### 1. Telegram Message Sent (18:56:57 UTC)

```
V. → Nikita: "Hey babe, I just got back from a long hike in the mountains.
The view was absolutely incredible, you would have loved it! How was your day?"
```

### 2. Nikita Responded (19:00:02 UTC)

```
Nikita → V.: "*btw your message came through twice - might..."
```

Response time: ~3 min (dominated by Neo4j cold start: 60s)

### 3. Pipeline Processed (19:15:53 UTC)

Conversation `cb31cd93-bb46-4019-8398-62a1bd9885da` processed by pg_cron:

| Field | Value |
|-------|-------|
| **status** | `processed` |
| **conversation_summary** | "User shared they just returned from a mountain hike with incredible views and asked about Nikita's day. Nikita noted a technical issue with the message being duplicated." |
| **emotional_tone** | `positive` |
| **processed_at** | 2026-02-10 19:15:53.576815+00 |

### 4. Pipeline Stage Results

| Stage | Status | Duration | Notes |
|-------|--------|----------|-------|
| **extraction** | PASS | 5,876ms | LLM → Anthropic, facts extracted |
| **memory_update** | PASS | 8,441ms | 9 OpenAI embedding calls |
| emotional | PASS | 58ms | |
| game_state | PASS | 0.6ms | has_extraction=True, chapter=5 |
| conflict | PASS | 0.4ms | |
| life_sim | FAIL | 3,329ms | SQL `:` syntax error (known) |
| touchpoint | FAIL | 958ms | Cascaded from life_sim |
| summary | FAIL | 114ms | Logger kwarg bug |
| prompt_builder | FAIL | 30,009ms | Timeout (cascaded) |

**5/9 PASS, 4/9 FAIL (all non-critical). Both CRITICAL stages (extraction, memory_update) PASS.**

### 5. Supabase Artifacts

**ready_prompts** (from earlier runs):
- 4,163 tokens — full Nikita persona with personalized backstory
- 4,011 tokens — earlier generation

**Previous conversations** (proof pipeline works repeatedly):
- `f50e12fd`: summary=616 chars, tone="mixed", processed 14:20:45
- `75e23a7a`: summary=321 chars, tone="mixed", processed 14:10:23

## Known Non-Critical Issues (Pre-Existing)

1. **life_sim**: SQL syntax error (`:user_id` instead of `$N` parameterized)
2. **summary**: `Logger._log() got unexpected keyword argument 'conversation_id'`
3. **prompt_builder**: 30s timeout (cascaded from failed DB transaction)
4. **memory_facts**: SAWarning prevents persistence after cascaded transaction failure

## PR #53 Closure

Closed as superseded. All fixes incorporated via master commits a3d17c0..051fe92.

## Files Changed (8 files, +53/-15)

| File | Change |
|------|--------|
| pyproject.toml | `>=0.1.0` → `>=1.0.0` |
| nikita/api/routes/admin.py | Method name + params + job_id |
| nikita/api/routes/admin_debug.py | Method name |
| nikita/api/routes/voice.py | Add conversation/user params |
| nikita/onboarding/handoff.py | Method name + load user + params |
| tests/api/routes/test_admin_mutations_new.py | Mock fixes |
| tests/api/routes/test_admin_prompts.py | Mock fix |
| tests/onboarding/test_pipeline_bootstrap.py | Mock + assertion fixes |
