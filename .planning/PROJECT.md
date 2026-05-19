---
title: Nikita — Don't Get Dumped
lifecycle: living
last_updated: 2026-05-19
---

# PROJECT.md — Nikita: Don't Get Dumped

## Identity

AI girlfriend simulation game. Players interact with Nikita via text (Telegram) and voice (ElevenLabs). A scoring engine tracks 4 relationship metrics driving chapter progression (1-5), boss encounters, decay, and vice personalization. Win by reaching Chapter 5; lose by failing 3 boss encounters.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Google Cloud Run (serverless, scales to zero) |
| Frontend | Next.js 16, shadcn/ui, Tailwind CSS, Vercel |
| Database | Supabase (PostgreSQL + pgVector + RLS) |
| AI Text | Pydantic AI + Claude Sonnet (see `nikita/config/settings.py` for model ID) |
| AI Voice | ElevenLabs Conversational AI 2.0 (Server Tools pattern) |
| Memory | SupabaseMemory (pgVector + dedup, replaces Graphiti/Neo4j) |
| Scheduling | pg_cron + Cloud Run task endpoints (no Celery/Redis) |
| Platforms | Telegram (`@Nikita_my_bot`), Voice (ElevenLabs), Portal (Next.js) |

## Key Files

| File | Purpose |
|---|---|
| `nikita/config/settings.py` | All environment settings (Pydantic) |
| `nikita/engine/constants.py` | Game constants: chapters, thresholds (55-75%), decay (0.8-0.2/hr) |
| `nikita/pipeline/orchestrator.py` | 11-stage async pipeline |
| `nikita/memory/supabase_memory.py` | SupabaseMemory (pgVector + dedup) |
| `nikita/db/models/user.py` | User, UserMetrics, UserVicePreference |
| `nikita/agents/text/agent.py` | Pydantic AI text agent |
| `nikita/platforms/telegram/message_handler.py` | Main message processing entry point |
| `nikita/api/main.py` | FastAPI app entry point |
| `portal/src/app/` | Next.js App Router pages |

## Game Constants

| Constant | Value |
|---|---|
| Relationship metrics | 4 (warmth, trust, passion, respect) |
| Chapters | 5 — win condition is reaching Chapter 5 |
| Lose condition | 3 failed boss encounters |
| Boss thresholds | 55/60/65/70/75% |
| Decay rates | 0.8/0.6/0.4/0.3/0.2 per hour |
| Grace periods | 8/16/24/48/72 hours |

## Deployments

| Service | URL |
|---|---|
| Backend | Cloud Run `nikita-api-*` (us-central1) |
| Portal | `nikita-mygirl.com` (apex canonical; www → apex 308) |

## Commands

```bash
uv run pytest -q                              # Full backend suite (~90 s pre-push gate)
(cd portal && npm run test -- --run)          # Portal vitest pre-push gate
(cd portal && npm run lint && npm run build)  # Portal lint + build gate
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated
cd portal && npm run build && vercel --prod   # Deploy portal
```

## Full Architecture Reference

See `plans/master-plan.md` for complete system architecture diagrams, agent wiring, and historical implementation notes.
