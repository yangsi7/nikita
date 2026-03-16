# Deployment Reference

## Cloud Run (Backend)

| Resource | Value |
|----------|-------|
| GCP Project | `gcp-transcribe-test` |
| GCP Account | `simon.yang.ch@gmail.com` |
| Cloud Run Service | `nikita-api` (region: `us-central1`) |
| Backend URL | `https://nikita-api-1040094048579.us-central1.run.app` |

**Deploy command:**
```bash
gcloud config set account simon.yang.ch@gmail.com && gcloud config set project gcp-transcribe-test
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated
```

**NEVER** set `--min-instances=1`. Must scale to zero. Cold starts (5-15s) are acceptable.
A PreToolUse hook (`guard-deploy.sh`) blocks `--min-instances` automatically.

## Vercel (Portal)

| Resource | Value |
|----------|-------|
| Portal URL | `https://portal-phi-orcin.vercel.app` |

**Deploy command:**
```bash
source ~/.nvm/nvm.sh && nvm use 22 && cd portal && npm run build && vercel --prod
```

**Env vars** (already configured on Vercel):
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`

`vercel.json` includes API rewrites that proxy `/api/v1/*` to the Cloud Run backend + security headers.

## Supabase (Database)

| Resource | Value |
|----------|-------|
| Project | `vlvlwmolfdpzdfmtipji` |
| Dashboard | `https://supabase.com/dashboard/project/vlvlwmolfdpzdfmtipji` |

### Migration Pattern (CRITICAL)

90 comment-only stubs in `supabase/migrations/` — **NO real DDL in migration files**.

Full DDL reference: `supabase/reference/00000000000001_baseline_schema.sql`

**Why stubs**: Supabase Preview branches execute ALL migrations from scratch. If stubs contain real DDL, Preview creates duplicate tables/policies.

**Adding new migrations**:
1. Apply DDL via Supabase MCP `apply_migration` or `execute_sql`
2. Create a 2-line comment stub locally: `-- Migration: description` + `-- Applied via Supabase MCP on YYYY-MM-DD`
3. Commit the stub to git

**Anti-patterns**:
- NEVER put real DDL in stub files
- NEVER remove a committed migration file (Preview tracks applied versions)

## pg_cron Jobs

**Authoritative registry** — 8 active jobs configured via Supabase dashboard (verified 2026-03-15).
Source of truth: this file. `nikita/config_data/schedule.yaml` defers here (IT-004/DC-013 fix).

| Job name | Schedule | Endpoint | Purpose |
|----------|----------|----------|---------|
| `process-conversations` | Every minute | `POST /tasks/process-conversations` | 10-stage pipeline processing |
| `deliver-messages` | Every minute | `POST /tasks/deliver` | Scheduled message delivery |
| `decay-hourly` | `0 * * * *` (every hour) | `POST /tasks/decay` | Score decay processing |
| `cleanup-hourly` | `0 * * * *` (every hour) | `POST /tasks/cleanup` | Old data cleanup (pipeline_events, etc.) |
| `touchpoints-5min` | `*/5 * * * *` | `POST /tasks/touchpoints` | Proactive touchpoint evaluation (not yet created) |
| `boss-timeout-6h` | `0 */6 * * *` | `POST /tasks/boss-timeout` | Resolve AFK boss encounters (not yet created) |
| `summary-daily` | `59 23 * * *` | `POST /tasks/summary` | Daily conversation summaries |
| `psyche-batch-daily` | `0 5 * * *` | `POST /tasks/psyche-batch` | Daily psyche agent batch |
| `health-check` | `*/5 * * * *` | `GET /health` | Keep-alive warm-instance ping (deliberate — IT-009) |
| `engagement-hourly` | `30 * * * *` | `POST /tasks/engagement` | Engagement state transitions |

**Deprecated jobs** (return HTTP 410, safe to remove from pg_cron dashboard):
- `detect-stuck` (`POST /tasks/detect-stuck`) — replaced by `process-conversations`
- `recover-stuck` (`POST /tasks/recover-stuck`) — replaced by `process-conversations`

## ElevenLabs (Voice)

Agent IDs are **per-environment** (dev vs prod). See `nikita/config/settings.py` for the current agent ID.

Dashboard: Configure server tools, knowledge base, and voice settings at `https://elevenlabs.io/app/conversational-ai`.

**Server Tools pattern**: ElevenLabs agent calls back to our API endpoints for game state, scoring, and memory operations.

## Cloud Run Secrets (GCP Secret Manager)

| Env Var | Secret Name | Purpose |
|---------|-------------|---------|
| `DATABASE_URL` | `nikita-database-url` | PostgreSQL connection string |
| `SUPABASE_URL` | `nikita-supabase-url` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | `nikita-supabase-service-key` | Supabase service role key |
| `ANTHROPIC_API_KEY` | `nikita-anthropic-api-key` | Claude API key |
| `ELEVENLABS_API_KEY` | `nikita-elevenlabs-api-key` | ElevenLabs voice API key |
| `TELEGRAM_BOT_TOKEN` | `nikita-telegram-bot-token` | Telegram bot authentication |
| `TELEGRAM_WEBHOOK_SECRET` | `nikita-telegram-webhook-secret` | Webhook signature validation |
| `TASK_AUTH_SECRET` | `nikita-task-auth-secret` | pg_cron task endpoint auth (PR #127) |

**TASK_AUTH_SECRET**: Required in non-debug mode. Startup raises `RuntimeError` if missing (`nikita/api/main.py:78-85`). Created 2026-03-15 during audit remediation deployment.

## Environment Variables

All configuration is managed via Pydantic settings in `nikita/config/settings.py`. Required env vars are documented in `.env.example`.
