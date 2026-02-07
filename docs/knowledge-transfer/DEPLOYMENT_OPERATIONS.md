# Deployment & Operations

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - PROJECT_OVERVIEW.md
  - INTEGRATIONS.md
  - ANTI_PATTERNS.md
```

## Overview

Nikita runs on Google Cloud Run with supporting services:
- **Cloud Run** - Serverless compute
- **Supabase** - PostgreSQL database + Auth
- **Neo4j Aura** - Knowledge graphs
- **Vercel** - Portal frontend

---

## Cloud Run Configuration

### Service Details

| Setting | Value |
|---------|-------|
| **Service Name** | `nikita-api` |
| **Project** | `gcp-transcribe-test` |
| **Region** | `us-central1` |
| **URL** | `https://nikita-api-1040094048579.us-central1.run.app` |

### Resource Limits

| Setting | Value | Notes |
|---------|-------|-------|
| Memory | 2GB | Required for LLM context |
| CPU | 1 | Sufficient for current load |
| Min Instances | 0 | Scales to zero |
| Max Instances | 10 | Cost control |
| Request Timeout | 300s | For long LLM calls |
| Concurrency | 80 | Requests per instance |

### Deployment Command

```bash
# Ensure correct project
gcloud config set project gcp-transcribe-test
gcloud config set account simon.yang.ch@gmail.com

# Deploy
gcloud run deploy nikita-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10
```

### Revision Naming

Format: `nikita-api-XXXXX-YYY`
- `XXXXX` - Revision number (auto-incremented)
- `YYY` - Random suffix

Example: `nikita-api-00186-bc7`

---

## Environment Variables

### Required Variables

**File**: `nikita/config/settings.py:1-200`

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Supabase PostgreSQL | `postgresql://postgres:...@db.xxx.supabase.co:5432/postgres` |
| `NEO4J_URI` | Neo4j Aura connection | `neo4j+s://xxx.databases.neo4j.io` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `***` |
| `ANTHROPIC_API_KEY` | Claude API key | `sk-ant-api03-...` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | `***` |
| `ELEVENLABS_AGENT_ID` | Main Nikita agent | `agent_xxx` |
| `ELEVENLABS_AGENT_META_NIKITA` | Onboarding agent | `agent_yyy` |
| `TELEGRAM_BOT_TOKEN` | Bot token | `123456:ABC...` |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook HMAC secret | `***` |
| `SUPABASE_JWT_SECRET` | JWT signing key | `***` |
| `VOICE_TOKEN_SECRET` | Voice session tokens | `***` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `CONTEXT_ENGINE_FLAG` | `disabled` | Feature flag for v2 |
| `ENVIRONMENT` | `production` | Environment name |

### Setting Variables

```bash
# Via gcloud CLI
gcloud run services update nikita-api \
  --region us-central1 \
  --update-env-vars "DATABASE_URL=postgresql://..."

# Multiple variables
gcloud run services update nikita-api \
  --region us-central1 \
  --update-env-vars "VAR1=value1,VAR2=value2"
```

### Secrets Management

Secrets are stored in Google Secret Manager:

```bash
# Create secret
echo -n "secret-value" | gcloud secrets create SECRET_NAME --data-file=-

# Reference in Cloud Run
gcloud run services update nikita-api \
  --region us-central1 \
  --update-secrets "NEO4J_PASSWORD=neo4j-password:latest"
```

---

## Database Migrations

### Alembic Setup

**File**: `alembic.ini`, `alembic/env.py`

```bash
# Run migrations locally
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Show current version
alembic current

# Show history
alembic history
```

### Production Migrations

Migrations run automatically on deployment via:

**File**: `Dockerfile`

```dockerfile
# ... build steps ...

# Run migrations on startup
CMD alembic upgrade head && uvicorn nikita.api.main:app --host 0.0.0.0 --port $PORT
```

### Rollback

```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123
```

---

## Scheduled Jobs (pg_cron)

### Active Jobs

| Job | Schedule | Endpoint | Purpose |
|-----|----------|----------|---------|
| `decay` | `0 * * * *` (hourly) | `POST /tasks/decay` | Apply relationship decay |
| `deliver` | `*/30 * * * *` (30 min) | `POST /tasks/deliver` | Send scheduled messages |
| `summary` | `0 6 * * *` (6 AM) | `POST /tasks/summary` | Generate daily summaries |
| `cleanup` | `0 3 * * *` (3 AM) | `POST /tasks/cleanup` | Clean expired data |
| `process` | `*/5 * * * *` (5 min) | `POST /tasks/process-conversations` | Recover stuck convos |

### Managing Jobs

Jobs are configured in Supabase Dashboard → SQL Editor:

```sql
-- List all cron jobs
SELECT * FROM cron.job;

-- Create new job
SELECT cron.schedule(
  'decay-job',
  '0 * * * *',
  $$SELECT net.http_post(
    url := 'https://nikita-api-xxx.run.app/tasks/decay',
    headers := '{"Content-Type": "application/json"}'::jsonb,
    body := '{}'::jsonb
  )$$
);

-- Delete job
SELECT cron.unschedule('decay-job');
```

### Job Monitoring

```sql
-- Check recent job runs
SELECT * FROM cron.job_run_details
ORDER BY start_time DESC
LIMIT 20;

-- Check failed jobs
SELECT * FROM cron.job_run_details
WHERE status = 'failed'
ORDER BY start_time DESC;
```

---

## Monitoring

### Cloud Run Metrics

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=nikita-api" \
  --limit 100 \
  --format "table(timestamp,textPayload)"

# View errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=nikita-api AND severity>=ERROR" \
  --limit 50

# View metrics
gcloud monitoring dashboards list
```

### Application Metrics

**Endpoint**: `GET /health`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "neo4j": "connected",
  "timestamp": "2026-02-03T12:00:00Z"
}
```

**Endpoint**: `GET /admin/pipeline-health`

```json
{
  "total_jobs": 2954,
  "completed": 2952,
  "failed": 2,
  "success_rate": 0.999,
  "stuck_conversations": 0,
  "avg_processing_time_ms": 3500
}
```

### Error Tracking

Errors are logged to `error_logs` table:

```sql
SELECT
  error_type,
  error_message,
  context->'endpoint' as endpoint,
  created_at
FROM error_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

---

## Troubleshooting

### Common Issues

#### Neo4j Cold Start (30-60s)

**Symptom**: First request after inactivity times out.

**Cause**: Neo4j Aura free tier pauses after inactivity.

**Solution**:
1. Health check endpoint warms up connection
2. Generous timeouts (30s for Graphiti)
3. Fallback data for timeout scenarios

#### Cloud Run Timeout

**Symptom**: Request fails with 504 Gateway Timeout.

**Cause**: Request exceeds 300s timeout.

**Solution**:
1. Check if LLM call is taking too long
2. Add timeout to individual operations
3. Consider breaking into async job

#### Database Connection Pool

**Symptom**: "too many connections" error.

**Cause**: Connections not being released.

**Solution**:
1. Ensure sessions are properly closed
2. Check for missing `await session.close()`
3. Verify connection pool settings

### Debug Commands

```bash
# Check Cloud Run status
gcloud run services describe nikita-api --region us-central1

# Check revisions
gcloud run revisions list --service nikita-api --region us-central1

# View real-time logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=nikita-api"

# Check instance count
gcloud monitoring metrics list --filter="metric.type=run.googleapis.com/container/instance_count"
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`pytest tests/ -v`)
- [ ] No failing type checks (`mypy nikita/`)
- [ ] Database migrations created
- [ ] Environment variables documented
- [ ] CHANGELOG updated

### Deployment Steps

1. **Commit changes**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   git push origin main
   ```

2. **Run tests**
   ```bash
   pytest tests/ -v -x
   ```

3. **Deploy**
   ```bash
   gcloud run deploy nikita-api --source . --region us-central1
   ```

4. **Verify**
   ```bash
   curl https://nikita-api-xxx.run.app/health
   ```

5. **Monitor logs**
   ```bash
   gcloud logging tail "resource.labels.service_name=nikita-api"
   ```

### Post-Deployment

- [ ] Health check passing
- [ ] Logs show no errors
- [ ] Test key endpoints manually
- [ ] Verify scheduled jobs running
- [ ] Check database migrations applied

---

## Rollback

### Quick Rollback

```bash
# List revisions
gcloud run revisions list --service nikita-api --region us-central1

# Route traffic to previous revision
gcloud run services update-traffic nikita-api \
  --region us-central1 \
  --to-revisions nikita-api-XXXXX-YYY=100
```

### Full Rollback

```bash
# Checkout previous commit
git checkout HEAD~1

# Deploy previous version
gcloud run deploy nikita-api --source . --region us-central1

# If database migration needed
alembic downgrade -1
```

---

## Cost Optimization

### Current Monthly Costs

| Service | Est. Cost | Notes |
|---------|-----------|-------|
| Cloud Run | $5-15 | Pay per request |
| Supabase | $0 | Free tier |
| Neo4j Aura | $0 | Free tier |
| Claude API | $20-40 | Per token |
| ElevenLabs | $5-10 | Voice minutes |
| **Total** | **$35-65** | |

### Optimization Tips

1. **Scale to Zero** - Set min instances to 0
2. **Request Timeout** - Don't hold connections unnecessarily
3. **Caching** - Cache frequently accessed data
4. **Batch Operations** - Combine related API calls
5. **Prompt Optimization** - Reduce token usage

---

## Security

### Network Security

- All endpoints behind HTTPS
- Webhook signature validation
- Rate limiting on public endpoints
- Admin endpoints require JWT

### Secret Rotation

```bash
# Rotate Neo4j password
gcloud secrets versions add neo4j-password --data-file=-

# Update Cloud Run
gcloud run services update nikita-api \
  --update-secrets "NEO4J_PASSWORD=neo4j-password:latest"
```

### Access Control

- Admin access: `@silent-agents.com` domain only
- User data isolation via RLS
- Service role for backend operations

---

## Key File References

| File | Purpose |
|------|---------|
| `Dockerfile` | Container build |
| `cloudbuild.yaml` | CI/CD config |
| `alembic.ini` | Migration config |
| `nikita/config/settings.py` | Environment settings |
| `nikita/api/main.py` | FastAPI app |

---

## Related Documentation

- **Project Overview**: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- **Integrations**: [INTEGRATIONS.md](INTEGRATIONS.md)
- **Anti-Patterns**: [ANTI_PATTERNS.md](ANTI_PATTERNS.md)
