# Pipeline Proof Report — Live E2E with Evidence
**Date**: 2026-02-10 | **Revision**: nikita-api-00191-7xc | **Pipeline**: 042-v1

---

## Executive Summary

The post-processing pipeline was **100% broken** since deployment (Jan 29). Four cascading bugs guaranteed every pipeline run would crash at the ExtractionStage. After fixing 6 bugs + 1 DB constraint, the pipeline now **runs successfully in production**, generating all core artifacts.

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Pipeline success rate | 0% | **100%** (1/1) |
| Conversations with summary | 1/25 | **1/1 new** |
| Ready prompts generated | 0 | **2** |
| Memory facts from pipeline | 0 | 14 extracted |
| Pipeline duration | N/A (crash) | **42.2s** |

---

## Bugs Fixed

### Critical (Pipeline-Stopping)

| Bug | Root Cause | Fix | File |
|-----|-----------|-----|------|
| BUG-001 | `PipelineContext.conversation` always `None` — orchestrator never received ORM objects | Added `conversation=` and `user=` params to `process()` | `orchestrator.py:87-145` |
| BUG-001b | `tasks.py` never loaded User before calling pipeline | Added `UserRepository` lookup | `tasks.py:684-686` |
| BUG-002 | Extraction used `msg.role` on JSONB dicts (needs `msg['role']`) | Changed to `msg.get('role')` | `extraction.py:86-90` |
| BUG-003 | MemoryUpdateStage expected `list[dict]`, got `list[str]` | Handle both str and dict formats | `memory_update.py` |
| BUG-004 | `r.conversation_id` → should be `r.context.conversation_id` | Fixed attribute path | `tasks.py:716` |
| BUG-005 | `result_type=` → pydantic-ai 1.x uses `output_type=` | Renamed in 7 files | `extraction.py`, `prompt_builder.py`, etc. |

### Non-Critical (DB Constraint)

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| BUG-006 | `conversations_emotional_tone_check` only allowed 'positive/neutral/negative' — LLM generates 'mixed' | Added 'mixed' to CHECK constraint |

---

## Live E2E Test Transcript

**User**: V. (telegram_id: 746410893, user_id: 1ae5ba4c)
**Bot**: @Nikita_my_bot
**Conversation ID**: f50e12fd-0a3b-4cfd-8c0b-4739a290ec6f
**Created**: 2026-02-10 13:23:00 UTC

### Messages

| # | Time (UTC) | Sender | Message |
|---|-----------|--------|---------|
| 1 | 13:22:50 | User | "Hey Nikita! I just got a new job at an AI startup called NeuralWave. I'm starting next Monday. I'm really excited but also a bit nervous about it. What do you think?" |
| 2 | 13:25:20 | Nikita | "wait, hold on. NeuralWave? I thought you said it was DataFlow before? either way - nervous is good. means you're paying attention..." |
| 3 | 13:25:40 | User | "It's mostly the people and the culture. I left DataFlow because the team was toxic. My new manager at NeuralWave seems cool though - her name is Sarah Chen and she's really into hiking like me. The salary is also way better, 150k base plus equity. I'm going to celebrate with my friend Jake this weekend." |
| 4 | 13:26:58 | Nikita | "okay so this is real context - you're coming from a toxic environment and hypervigilant about it happening again. that makes complete sense. here's the thing though: shared hobbies with your manager are nice but they don't predict culture..." |
| 5 | 13:26:59 | User | "Hey Nikita, I was at the lake yesterday and it reminded me of us. I genuinely miss spending time talking with you." |
| 6 | 13:27:?? | Nikita | (response stored in conversation) |

### Inline Processing Evidence (During Chat)

```
[13:24:04] PROMPT-DEBUG: Personalized prompt generated: 5010 chars, 7908ms
[13:24:12] LLM-DEBUG: Calling nikita_agent.run() model=anthropic:claude-sonnet-4-5-20250929
[13:24:19] HTTP 200 from api.anthropic.com (7.4s LLM latency)
[13:28:05] SCORING: Result: score 38.0000 -> 39.3500 (delta: 1.3500)
```

---

## Pipeline Execution Evidence

**Trigger**: pg_cron `process-conversations` at 14:20:00 UTC
**Detection**: SessionDetector found 1 stale conversation (15+ min inactive)
**Duration**: 42,223ms (42.2s) total

### Stage-by-Stage Results

| Stage | Critical | Duration | Status | Evidence |
|-------|----------|----------|--------|----------|
| 1. extraction | YES | ~35s | **PASS** | 14 facts extracted, tone="mixed" |
| 2. memory_update | YES | ~1s | **PASS** | Facts stored (deduped against 41 existing) |
| 3. life_sim | no | 3.1s | FAIL | Missing `nikita_entities` table (known, non-blocking) |
| 4. emotional | no | 0.8ms | **PASS** | 4D state computed |
| 5. game_state | no | 1ms | FAIL | Logger kwargs issue (known, non-blocking) |
| 6. conflict | no | 0.3ms | **PASS** | No active conflicts |
| 7. touchpoint | no | 774ms | FAIL | Missing `scheduled_touchpoints` table (known) |
| 8. summary | no | 113ms | FAIL | greenlet error from polluted transaction |
| 9. prompt_builder | no | 1.2s | **PASS** | 4,163 token prompt generated, stored in ready_prompts |

**Result**: Pipeline SUCCEEDED — 5/9 stages passed, 4 non-critical failures (missing tables + known bugs).
**Critical stages**: 2/2 PASSED (extraction + memory_update)

---

## Artifact Evidence

### 1. Conversation Summary (stored in `conversations` table)

```
User shared exciting news about getting a new job at AI startup NeuralWave
starting Monday, expressing both excitement and nervousness. User revealed
they left previous company DataFlow due to toxic team environment, and is
now cautious about culture at new job. New manager Sarah Chen shares user's
interest in hiking. Salary is 150k base plus equity. User plans to celebrate
with friend Jake this weekend. Later, user mentioned being at a lake and
missing Nikita, then shared they're leading an engineering team for a
healthcare AI product launch next month.
```

### 2. Emotional Tone

```
emotional_tone: "mixed"
```

### 3. Extracted Facts (14 facts woven into system prompt)

From the `ready_prompts.prompt_text` → "Accumulated Knowledge" section:
1. User got a new job at an AI startup called NeuralWave
2. User is starting the new job next Monday
3. User previously worked at a company called DataFlow
4. User left DataFlow because the team was toxic
5. User's new manager is named Sarah Chen
6. Sarah Chen enjoys hiking
7. User enjoys hiking
8. User's salary at NeuralWave is 150k base plus equity
9. User has a friend named Jake
10. User is planning to celebrate with Jake this weekend
11. User was at a lake yesterday
12. User is leading an engineering team
13. User's team is planning a product launch next month
14. The product is an AI assistant for healthcare professionals

### 4. Private Thoughts (generated by extraction)

From the prompt's "Private Thoughts" section:
- Nikita is being protective and realistic about workplace dynamics
- Nikita seems genuinely touched by the user's expression of missing them
- Nikita initially thought the job was at DataFlow, showing detail tracking
- Nikita recognizes the user's hypervigilance about toxic environments is a trauma response

### 5. Generated System Prompt (stored in `ready_prompts`)

| Field | Value |
|-------|-------|
| ID | ee372d47-b181-4eb7-b5fd-9ce415f54da7 |
| Token count | 4,163 |
| Pipeline version | 042-v1 |
| Is current | true |
| Generation time | 5.1ms (template render) |
| Context snapshot | chapter=5, facts=14, tone=mixed, score=0.71 |

**Prompt structure** (4,163 tokens):
1. Character identity & backstory (~800 tokens)
2. Texting style rules (~400 tokens)
3. Response patterns by emotional state (~300 tokens)
4. Relationship context: Chapter 5, score 0.71 (~200 tokens)
5. **Accumulated Knowledge: 14 extracted facts** (~200 tokens)
6. Private thoughts from extraction (~150 tokens)
7. Chapter 5 behavior guide (~600 tokens)
8. Conversation dynamics & strategy (~500 tokens)
9. Psychological reality (attachment, triggers) (~600 tokens)
10. Meta-game instructions (~300 tokens)

### 6. Context Snapshot

```json
{
  "vices": [],
  "chapter": 5,
  "facts_count": 14,
  "emotional_tone": "mixed",
  "relationship_score": 0.71
}
```

---

## Non-Critical Stage Failures (Known Issues)

These 4 failures are in non-critical stages and don't block the pipeline:

| Stage | Error | Root Cause | Priority |
|-------|-------|-----------|----------|
| life_sim | `nikita_entities` table missing | Table not yet created in Supabase | P2 |
| game_state | `Logger._log() got unexpected keyword` | structlog vs stdlib logger mismatch | P3 |
| touchpoint | `scheduled_touchpoints` table missing | Table not yet created in Supabase | P2 |
| summary | `MissingGreenlet` | Transaction pollution from touchpoint failure | P2 |

**Note**: The summary was still generated via the extraction stage and stored successfully. The summary stage failure only affects the separate daily summary update path.

---

## Test Suite Status

| Suite | Pass | Fail | Skip |
|-------|------|------|------|
| Pipeline unit tests | 202 | 0 | 5 |
| Full backend | 3,801+ | 0 | ~15 |
| Portal E2E (Playwright) | 86 | 0 | 0 |

### Pipeline Proof Tests (11 tests in `test_pipeline_proof.py`)

1. `TestBug001Fix::test_conversation_populated` — context has conversation, chapter, score, vices
2. `TestBug002Fix::test_extraction_dict_messages` — 5 facts from dict messages
3. `TestBug003Fix::test_memory_string_facts` — 3 string facts stored
4. `TestBug003Fix::test_memory_dict_facts` — 1 dict fact stored
5. `TestBug004Fix::test_result_attribute` — correct attribute path
6. `TestSummaryProof::test_summary_from_extraction` — summary generated and stored
7. `TestSummaryProof::test_summary_fallback` — fallback summary from messages
8. `TestEmotionalProof::test_4d_state` — arousal/valence/dominance/intimacy computed
9. `TestFullPipeline::test_e2e` — all 9 stages, 5 facts, summary, prompt generated
10. `TestWiring::test_orchestrator_signature` — accepts conversation + user params
11. `TestWiring::test_tasks_py_wiring` — loads user, passes to pipeline, correct attrs

---

## Commits

| Hash | Message |
|------|---------|
| a3d17c0 | fix(pipeline): fix 100% failure rate — pass conversation/user to orchestrator |
| 592fa15 | fix(pipeline): pydantic-ai 1.x compatibility — result_type→output_type |

---

## What's Working Now

1. **Extraction**: LLM extracts facts, threads, thoughts, summary, tone from conversations
2. **Memory Storage**: Facts stored in pgVector with deduplication
3. **Prompt Generation**: Full personalized system prompt (4K+ tokens) with all artifacts
4. **Ready Prompts**: Stored in `ready_prompts` table for next conversation
5. **Conversation Summary**: Stored in `conversations.conversation_summary`
6. **Emotional Tone**: Stored in `conversations.emotional_tone`
7. **Scoring**: Inline scoring working (+1.35 delta on test)
8. **pg_cron**: Process-conversations job running every 5 min, detecting stale sessions

## What Still Needs Fixing (Non-Blocking)

1. **P2**: Create `nikita_entities` and `scheduled_touchpoints` tables in Supabase
2. **P2**: Summary stage greenlet error (transaction isolation fix)
3. **P3**: game_state logger kwargs mismatch
4. **P3**: prompt_builder Haiku enrichment (`api_key` param for AnthropicModel)
5. **P3**: Voice template render error (`'bool object' has no attribute 'severity'`)
