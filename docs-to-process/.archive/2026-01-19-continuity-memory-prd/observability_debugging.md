# Observability & debugging requirements

Memory systems fail in silent, non-obvious ways.

This doc specifies what we need to log and how to inspect it so we can answer:

> “What did the model see, and why did it respond like that?”

---

## Goals

1. **Prompt provenance**: for every response, we can reconstruct the exact prompt + context injected.
2. **Memory provenance**: we know *where* each memory item came from (graph, summary, thread, etc.).
3. **Post-processing health**: we can see processing completion rates and failures.

---

## Existing observability (already in repo)

### generated_prompts table

- `generated_prompts.prompt_content`
- `generated_prompts.token_count`
- `generated_prompts.generation_time_ms`
- `generated_prompts.meta_prompt_template`
- `generated_prompts.context_snapshot`

This is already a strong foundation.

---

## Required additions (P0)

### O1 — Prompt assembly metadata per response

For each response generation, persist a structured JSON blob (can live inside `generated_prompts.context_snapshot`):

```json
{
  "conversation": {
    "active_conversation_id": "...",
    "included_turns": 28,
    "dropped_turns": 14,
    "history_strategy": "message_history|transcript_block",
    "history_token_estimate": 1320
  },
  "episodic": {
    "daily_summary_id": "...",
    "included_key_moments": 3,
    "last_time_source": "conversation_summary|daily_summary"
  },
  "threads": {
    "included_threads": 5,
    "included_thoughts": 2
  },
  "graphs": {
    "enabled": true,
    "user_facts": 12,
    "relationship_episodes": 8,
    "nikita_events": 4
  },
  "budgets": {
    "total_tokens": 4300,
    "per_section": {
      "persona": 900,
      "relationship": 650,
      "working_memory": 1320,
      "today": 380,
      "threads": 210,
      "long_term": 540
    }
  }
}
```

This makes truncation decisions debuggable.

### O2 — Post-processing execution records

We already have `job_executions`. Requirements:

- Store one record per pipeline run with:
  - conversation_id list
  - counts processed/succeeded/failed
  - error summaries (top exceptions)
  - duration

If we keep multiple pipelines, log which one ran.

### O3 — Stuck processing detection

Add monitoring logic:

- if a conversation is `processing` for > X minutes (e.g. 10), mark it `failed` and log a job execution entry.

---

## Required tooling (P1)

### T1 — Admin endpoint: “show me prompt input”

An internal endpoint that returns:

- the system prompt that was used
- the working-memory turns included
- the episodic and semantic sections
- the model response

This should be gated (admin-only).

### T2 — Memory inspector UI (optional)

A simple internal dashboard view:

- today’s summary
- open threads
- top graph facts
- last processed conversation summaries

---

## Logging + privacy notes

- Treat prompt logs as sensitive (they contain user content).
- Enforce RLS and access control for any admin endpoints.

---

## Engineering pointers

- Prompt generation logging happens in `nikita/meta_prompts/service.py`.
- For text response generation, hook metadata at `nikita/agents/text/agent.py`.
- For voice cache refresh, hook metadata in `nikita/api/routes/voice.py`.
