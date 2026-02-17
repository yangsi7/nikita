# Humanization Layer Gap Analysis - 2026-01-26

## Executive Summary

Analysis of the humanization layer revealed **partial implementation** with several critical gaps preventing full context surfacing in prompts.

---

## Phase 1: Table Data Verification

| Table | Records | Users | Status | Verdict |
|-------|---------|-------|--------|---------|
| `conversation_threads` | 1 | 1 | Has data (2026-01-22) | ✅ Pipeline works |
| `nikita_thoughts` | 1 | 1 | Has data (2026-01-22) | ✅ Pipeline works |
| `user_backstories` | 1 | 1 | Has data (2026-01-26) | ✅ Onboarding works |
| `user_social_circles` | **0** | **0** | EMPTY | ❌ **NOT GENERATED** |
| `user_narrative_arcs` | **0** | **0** | EMPTY | ❌ **NOT GENERATED** |
| `engagement_history` | **0** | **0** | EMPTY | ❌ **NOT GENERATED** |

### Key Finding #1: Social Circles & Narrative Arcs Not Being Generated

The post-processing pipeline IS running (threads and thoughts exist), but:
- Social circle generation is not wired or not triggered
- Narrative arc generation is not wired or not triggered
- Engagement history tracking is not implemented

**Root Cause**: These features likely require separate generation triggers that haven't been connected to the post-processing pipeline.

---

## Phase 2: Context Injection Analysis

### Context Snapshot Structure

The `generated_prompts.context_snapshot` stores **COUNTS only**, not content:

```json
{
  "thread_count": 1,
  "thought_count": 1,
  "has_backstory": true,
  "user_fact_count": 6,
  "relationship_episode_count": 5,
  "nikita_event_count": 0
}
```

### Key Finding #2: Thread/Thought Content Not In Final Prompts

SQL analysis of `generated_prompts.prompt_content`:
- Contains: "curiosity is piqued" (thought type influence)
- Missing: Specific thread content ("Details about quitting job...")
- Missing: Specific thought content ("I wonder what made him quit...")
- Missing: "Unfinished Topics:" section

**Evidence**:
```sql
-- Thread exists with content
SELECT content FROM conversation_threads WHERE user_id = '...'
-- Returns: "Details about quitting job and future work plans"

-- But prompt doesn't contain this text
SELECT CASE WHEN prompt_content ILIKE '%quitting job%' THEN 'YES' ELSE 'NO' END
-- Returns: NO
```

### Prompt Architecture

The meta-prompt template includes `{{open_threads}}` and `{{active_thoughts}}` placeholders that ARE formatted correctly in `_load_context()` and `_format_template()`.

**However**: The final output from Claude Haiku is a **persona description**, not a data dump. The thread/thought context is INPUT to Haiku but may not always appear explicitly in OUTPUT.

**Recommendation**: Verify meta-prompt template instructs Haiku to preserve thread/thought references in final prompt.

---

## Phase 3: Live Test Results

### Timeline (2026-01-26)

| Time | Event | Status |
|------|-------|--------|
| 11:45:38 | Webhook received message (118 chars) | ✅ |
| 11:45:40 | User lookup + route to MessageHandler | ✅ |
| 11:45:45 | Conversation created (d06bcbc5...) | ✅ |
| 11:45:50 | "typing" action sent to Telegram | ✅ |
| 11:45:50 | TextAgentHandler.handle called | ✅ |
| 11:46:52 | Neo4j cold start complete (61.33s) | ⚠️ SLOW |
| 11:46:53 | generate_response called | ✅ |
| 11:46:53 | "treating as new session" logged | ✅ |
| 11:47:xx+ | **NO COMPLETION LOG** | ❌ TIMEOUT? |

### Key Finding #3: Neo4j Cold Start = 61+ Seconds

The Graphiti/Neo4j initialization takes over 60 seconds on cold start. This plus LLM latency may exceed Cloud Run's default timeout.

### Key Finding #4: LLM Request Appears to Timeout

- Conversation was created but NOT persisted to DB
- No Telegram response sent
- No completion/error logs visible

**Likely Cause**: Cloud Run request timeout (default 300s, but Neo4j 61s + LLM ~30s + prompt gen may chain timeouts)

---

## Issues to Create

### Issue #21: Social Circle Generation Not Triggered
**Severity**: HIGH
**Tables**: `user_social_circles`
**Expected**: After onboarding or first conversation, generate social circle characters
**Actual**: 0 records after multiple conversations

### Issue #22: Narrative Arc Generation Not Triggered
**Severity**: HIGH
**Tables**: `user_narrative_arcs`
**Expected**: After reaching certain game states, generate narrative arcs
**Actual**: 0 records after user in Chapter 5

### Issue #23: Thread/Thought Content Not Surfacing in Prompts
**Severity**: MEDIUM
**Component**: `MetaPromptService._format_template()` or Haiku output
**Expected**: Prompt contains "Unfinished Topics: [curiosity]: Details about quitting job..."
**Actual**: Prompt has `thread_count: 1` but no actual content

### Issue #24: Neo4j Cold Start Performance (61+ seconds)
**Severity**: HIGH
**Component**: `nikita/memory/graphiti_client.py`
**Expected**: Cold start < 10 seconds
**Actual**: 61.33 seconds observed

### Issue #25: LLM Request Timeout/Silent Failure
**Severity**: CRITICAL
**Component**: Text agent generate_response flow
**Expected**: Response generated and persisted
**Actual**: No response, no error, conversation rolled back

---

## Recommended Actions

1. **Immediate**: Investigate Issue #25 (LLM timeout) - bot is non-functional
2. **High Priority**: Fix social circle/narrative arc generation (Issues #21, #22)
3. **Medium Priority**: Verify thread content injection (Issue #23)
4. **Optimization**: Address Neo4j cold start (Issue #24)

---

## Files Investigated

| File | Relevant Code |
|------|--------------|
| `nikita/meta_prompts/service.py` | `_load_context()`, `_format_template()`, `_format_open_threads_section()` |
| `nikita/db/repositories/thread_repository.py` | `get_threads_for_prompt()`, `get_open_threads()` |
| `nikita/db/models/context.py` | `THREAD_TYPES` definition |
| `nikita/meta_prompts/templates/system_prompt.meta.md` | `{{open_threads}}`, `{{active_thoughts}}` placeholders |

---

## Verification Commands

```sql
-- Check humanization tables
SELECT COUNT(*), COUNT(DISTINCT user_id) FROM conversation_threads;
SELECT COUNT(*), COUNT(DISTINCT user_id) FROM nikita_thoughts;
SELECT COUNT(*), COUNT(DISTINCT user_id) FROM user_social_circles;
SELECT COUNT(*), COUNT(DISTINCT user_id) FROM user_narrative_arcs;

-- Check context_snapshot contents
SELECT context_snapshot FROM generated_prompts WHERE context_snapshot IS NOT NULL ORDER BY created_at DESC LIMIT 1;

-- Check thread content in prompts
SELECT CASE WHEN prompt_content ILIKE '%Unfinished Topics%' THEN 'YES' ELSE 'NO' END FROM generated_prompts ORDER BY created_at DESC LIMIT 1;
```
