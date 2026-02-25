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

7 active jobs configured via Supabase dashboard:

| Job | Schedule | Endpoint | Purpose |
|-----|----------|----------|---------|
| `decay-hourly` | Every hour | `/tasks/decay` | Score decay processing |
| `psyche-batch-daily` | 03:15 UTC | `/tasks/psyche-batch` | Daily psyche agent batch |
| `touchpoint-daily` | 08:00 UTC | `/tasks/touchpoints` | Daily touchpoint evaluation |
| `summary-daily` | 04:00 UTC | `/tasks/daily-summary` | Daily conversation summaries |
| `engagement-hourly` | Every hour | `/tasks/engagement` | Engagement state transitions |
| `cleanup-daily` | 02:00 UTC | `/tasks/cleanup` | Old data cleanup |
| `health-check` | Every 5 min | `/health` | Keep-alive ping |

## ElevenLabs (Voice)

Agent IDs are **per-environment** (dev vs prod). See `nikita/config/settings.py` for the current agent ID.

Dashboard: Configure server tools, knowledge base, and voice settings at `https://elevenlabs.io/app/conversational-ai`.

**Server Tools pattern**: ElevenLabs agent calls back to our API endpoints for game state, scoring, and memory operations.

## Environment Variables

All configuration is managed via Pydantic settings in `nikita/config/settings.py`. Required env vars are documented in `.env.example`.
