# CLAUDE.md — Nikita: Don't Get Dumped

## Project

AI girlfriend simulation game. Players interact with Nikita via text (Telegram) and voice (ElevenLabs). A scoring engine tracks 4 relationship metrics, driving chapter progression (1-5), boss encounters, decay, and vice personalization. Win by reaching Chapter 5; lose by failing 3 boss encounters.

**Status**: All specs implemented, audited, and E2E verified.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Google Cloud Run (serverless, scales to zero)
- **Frontend**: Next.js 16, shadcn/ui, Tailwind CSS, Vercel
- **Database**: Supabase (PostgreSQL + pgVector + RLS)
- **AI Text**: Pydantic AI + Claude (see `nikita/config/settings.py` for model ID)
- **AI Voice**: ElevenLabs Conversational AI 2.0 (Server Tools pattern)
- **Memory**: SupabaseMemory (pgVector) — replaced Graphiti/Neo4j in Spec 042
- **Scheduling**: pg_cron + Cloud Run task endpoints (no Celery/Redis)
- **Platforms**: Telegram (`@Nikita_my_bot`), Voice (ElevenLabs), Portal (Next.js)

## Commands

```bash
pytest tests/ -x -q                          # Run all tests
pytest tests/{module}/ -v                    # Run module tests
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated
cd portal && npm run build && vercel --prod  # Deploy portal
```

## Deployment

See `docs/deployment.md` for full deployment reference (URLs, project IDs, commands).

**NEVER** set `--min-instances=1` on Cloud Run. Must scale to zero. Enforced by `guard-deploy.sh` hook.

## Git Conventions

- **Commits**: `type(scope): description` — types: feat, fix, docs, refactor, test, chore — scopes: api, portal, engine, db, auth, telegram, voice, memory, pipeline, config
- **Branches**: `{type}/{spec-number}-{description}` (e.g., `feature/042-unified-pipeline`)
- **Merge**: Squash merge to master. Max 400 lines per PR.

## Critical Rules

1. **Verify before implementing**: Use MCP Ref tool to check official docs for ANY external library/API before writing code. Training data is outdated.
2. **Search before writing**: `rg "class.*Client" --type py` — if it exists, use it. One source of truth per utility.
3. **Zero failing tests**: Fix, track (GitHub issue), or delete — never ignore. Run tests before ending any task.
4. **External service config**: Document BOTH code-side AND dashboard-side settings (ElevenLabs, Supabase, etc.).
5. **No over-engineering**: Implement ONLY what was requested. No invented features.
6. **Event logging**: Log all significant actions in `event-stream.md` — format: `[TIMESTAMP] TYPE: description`

## State Files

| File | Max Lines | Purpose |
|------|-----------|---------|
| `event-stream.md` | 100 | Session event log |
| `workbook.md` | 300 | Active session context |
| `plans/master-plan.md` | 1000 | Technical architecture |
| `ROADMAP.md` | 400 | Strategic roadmap & spec tracking |

## Key Files

| File | Purpose |
|------|---------|
| `ROADMAP.md` | Project roadmap, spec status, feature tracking |
| `nikita/config/settings.py` | All environment settings (Pydantic) |
| `nikita/engine/constants.py` | Game constants: chapters, thresholds (55-75%), decay (0.8-0.2/hr) |
| `nikita/pipeline/orchestrator.py` | 9-stage async pipeline |
| `nikita/memory/supabase_memory.py` | SupabaseMemory (pgVector + dedup) |
| `nikita/db/models/user.py` | User, UserMetrics, UserVicePreference |
| `nikita/agents/text/agent.py` | Pydantic AI text agent |
| `nikita/platforms/telegram/message_handler.py` | Main message processing |
| `nikita/api/main.py` | FastAPI app entry point |
| `portal/src/app/` | Next.js App Router pages |

## Navigation

| Topic | Location |
|-------|----------|
| Project roadmap & spec tracking | `ROADMAP.md` |
| System architecture | `memory/architecture.md` |
| Backend & API patterns | `memory/backend.md` |
| Game mechanics (scoring, chapters, decay, vices) | `memory/game-mechanics.md` |
| User journeys | `memory/user-journeys.md` |
| Integration guides | `memory/integrations.md` |
| Technical architecture | `plans/master-plan.md` |
| Feature specs | `specs/NNN-feature/` (each has spec.md, plan.md, tasks.md) |
| Module reference | Each module has its own `CLAUDE.md` (lazy-loaded on file access) |
| Claude Code toolkit | `.claude/CLAUDE.md` (skills, commands, agents, workflows) |
