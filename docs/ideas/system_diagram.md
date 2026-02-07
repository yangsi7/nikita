# Nikita System Diagram (2026-02-05)

## Actor / Archivist / Director split

```text
            ┌───────────────────────────────┐
            │          INPUT LAYER          │
            │ Telegram / Portal / Voice     │
            └───────────────┬───────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                       ACTOR (hot path)                         │
│  Goal: respond fast; never depend on slow tools                │
│                                                               │
│  1) Log message → Supabase                                     │
│  2) ContextEngine (parallel collectors, fast DB reads)         │
│  3) PromptGenerator (token budget + sections)                  │
│  4) LLM generates response                                     │
│  5) Deliver response                                           │
└───────────────────────────────┬───────────────────────────────┘
                                │ enqueue durable work
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                ARCHIVIST / DIRECTOR (cold path)               │
│  Goal: update canon + plan Nikita’s life + research            │
│                                                               │
│  Cloud Tasks → /internal/pipeline/run                          │
│    Phase 1: extraction (entities, sentiment, topics)           │
│    Phase 2: canonical updates (facts versioning, scores, loops)│
│    Phase 3: async jobs (research, summary rollups, day-plans)  │
│    Phase 4: finalize + cache warm                              │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                        DATA LAYER                              │
│  Supabase Postgres (truth) + pgvector                           │
│  Redis (cache only, voice context)                              │
└───────────────────────────────────────────────────────────────┘
```

## Memory layers (what gets injected into prompts)

```text
Stable canon (slow-changing)     Episodic continuity      Daily life continuity     Topical reality
────────────────────────────     ───────────────────      ─────────────────────     ──────────────
- user profile (city/tz/etc)     - last convo summary     - today’s day plan        - research snippets (TTL)
- Nikita profile (job/bio)       - weekly rollup          - recent events           - optional daily news digest
- long-term facts (versioned)    - open loops / promises  - active conflict thread  - local places list
```
