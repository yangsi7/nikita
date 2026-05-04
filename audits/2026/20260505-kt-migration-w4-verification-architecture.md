# W4 KT Migration — ARCHITECTURE Verification

**Date**: 2026-05-05
**Wave**: W4 (KT migration with code-verification gate)
**Source**: `docs/knowledge-transfer/ARCHITECTURE_ALTERNATIVES.md` (559 lines)
**Verifier**: `pr-codebase-intel` subagent (HARD CAP 15, read-only)
**Method**: Every claim grep-confirmed against `nikita/`, `portal/`, `supabase/migrations/`. KT NOT trusted.

## Verdict: DO NOT MIGRATE — drop or move to specs/archive/

This file is (a) self-declared stale at line 3 (Neo4j/Graphiti note), (b) ~85% subjective vendor-comparison + Evaluation Score opinion content with no code anchor, (c) the 4 still-true items are already in root CLAUDE.md Tech Stack section.

## Verification Table

| # | KT Claim (paraphrased) | KT line | Verification target | Code file:line | Status | Migrate? |
|---|---|---|---|---|---|---|
| 0 | Self-declared stale: Neo4j/Graphiti replaced by SupabaseMemory per Spec 042 | 3 | nikita/memory/ | `nikita/memory/supabase_memory.py` (sole memory module) | VERIFIED (the staleness disclaimer itself) | NO |
| 1 | "Current: Graphiti + Neo4j Aura" memory backend | 23 | nikita/memory/ | only `supabase_memory.py` + `__init__.py`; rg neo4j/graphiti = 0 hits | STALE — Replaced by SupabaseMemory (pgVector) per Spec 042 | NO |
| 2 | "Current: Pydantic AI" agent framework | 137 | nikita/agents/text/agent.py | model id `claude-sonnet-4-6` set via Pydantic AI in `nikita/config/settings.py:47` | VERIFIED | NO (already in root CLAUDE.md) |
| 3 | "Current: ElevenLabs Conversational AI" voice | 208 | nikita/agents/voice/ | `nikita/agents/voice/__init__.py:1` confirms ElevenLabs Conversational AI 2.0; 16 files reference ElevenLabs | VERIFIED | NO (already in root CLAUDE.md) |
| 4 | "Current: Supabase (PostgreSQL)" database | 276 | supabase/migrations/ | supabase/ + pgVector via supabase_memory.py | VERIFIED | NO (already in root CLAUDE.md) |
| 5 | "Current: Google Cloud Run" compute | 337 | Dockerfile + .gcloudignore | both present at repo root; root CLAUDE.md Commands section has gcloud run deploy | VERIFIED | NO (already in root CLAUDE.md) |
| 6 | "Current: Claude Sonnet 4.5" LLM | 396 | nikita/config/settings.py | `:47` default=`claude-sonnet-4-6` | STALE — Replaced by claude-sonnet-4-6 | NO |
| 7 | "Current: Custom 8-collector system" context engine | 456 | nikita/pipeline/stages/ | 12 stage modules (no "collector" abstraction); 0 grep hits for "ContextPackage" or "8 collector" framing | STALE — Replaced by 11-stage async pipeline (orchestrator.py) | NO |
| 8-19 | Vendor comparisons (RAG/Graphiti/LangGraph alternatives, Twilio/Vapi voice alts, PlanetScale/Neon DB alts, AWS Lambda/Fly compute alts, GPT-4o/Gemini LLM alts, Redis snapshots, etc.) | 36-551 | n/a (proposals + opinion) | — | UNVERIFIABLE | NO |

## Net Summary

- **Total claims**: 19 substantive (excluding self-disclaimer)
- **Verified**: 4 (rows 2-5: Pydantic AI, ElevenLabs, Supabase, Cloud Run — already in root CLAUDE.md)
- **Stale**: 5 (rows 1, 6, 7, 15, 17: Neo4j, 4.5 vs 4.6, 8-collector, Redis snapshots, Q2 hybrid)
- **Unverifiable**: 10 (vendor-comparison opinion content)

## Top facts MISSING from `memory/architecture.md` (per code, not per KT)

- `nikita/pipeline/orchestrator.py:47-59` — STAGE_DEFINITIONS list of 11 named stages: extraction, persistence, memory_update, life_sim, emotional, vice, game_state, conflict, touchpoint, summary, prompt_builder. 3 critical (extraction/memory_update). Driven by Spec 042 (unified pipeline) + Spec 114 (vice) + Spec 116 (persistence reorder).
- `nikita/memory/supabase_memory.py:51` (class `SupabaseMemory`) is the sole memory backend; embedding model `text-embedding-3-small`, dim 1536 (constants `:32-33`); dedup threshold `0.87` hardcoded at `:42` (history 0.95→0.92→0.87 per GH #199).
- `nikita/config/settings.py:47` — LLM model id `claude-sonnet-4-6` (KT says 4.5).
- `nikita/pipeline/stages/prompt_builder.py:36` — heaviest stage (24 ctx writes); central context-assembly responsibility (replaces KT's "8-collector" framing).
- `nikita/agents/voice/` — voice loop is **ElevenLabs Server Tools pattern** (not Pydantic AI Agent in live loop). Pydantic AI agents at `nikita/agents/voice/transcript.py:200,361` are post-call batch utilities only. Live voice = `nikita/agents/voice/server_tools.py` + `service.py`.
- Pipeline invocation sites (5 entry points): `admin.py:628`, `tasks.py:788`, `tasks.py:962`, `voice.py:727`, `onboarding/handoff.py:705`. **Telegram message_handler.py does NOT directly invoke the pipeline** — flows via cron path.
