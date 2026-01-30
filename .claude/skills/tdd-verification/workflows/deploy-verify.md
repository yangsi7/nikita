# Deployment Verification Workflow

## Overview

Every deployment must be verified through health checks, smoke tests, and log monitoring before considering a fix complete.

---

## Pre-Deployment Checklist

- [ ] All local tests pass (`pytest tests/ -v`)
- [ ] No uncommitted changes (`git status`)
- [ ] Code committed with proper message
- [ ] Branch is up to date with main

---

## Deployment Steps

### 1. Deploy to Cloud Run

```bash
# Deploy from source
gcloud run deploy nikita-api \
  --source . \
  --region us-central1 \
  --project gcp-transcribe-test \
  --allow-unauthenticated

# Note the revision name (e.g., nikita-api-00177-xxx)
```

### 2. Verify Deployment Status

```bash
# Check service status
gcloud run services describe nikita-api \
  --region us-central1 \
  --project gcp-transcribe-test \
  --format="yaml(status)"

# Verify 100% traffic on new revision
gcloud run services describe nikita-api \
  --region us-central1 \
  --format="value(status.traffic[0].revisionName,status.traffic[0].percent)"
```

---

## Post-Deployment Verification

### 3. Health Endpoint Check

```bash
# Basic health
curl -s https://nikita-api-1040094048579.us-central1.run.app/health | jq .
# Expected: {"status": "healthy", "service": "nikita-api"}

# Deep health (with database)
curl -s https://nikita-api-1040094048579.us-central1.run.app/health/deep | jq .
# Expected: {"status": "healthy", "database": "connected"}
```

### 4. Log Monitoring

```bash
# Check for errors in last 15 minutes
TIMESTAMP=$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)
gcloud logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$TIMESTAMP\"" \
  --limit=10 \
  --project gcp-transcribe-test \
  --format="table(timestamp,textPayload)"

# Check for warnings
gcloud logging read \
  "resource.type=cloud_run_revision AND severity=WARNING AND timestamp>=\"$TIMESTAMP\"" \
  --limit=10 \
  --project gcp-transcribe-test
```

### 5. Smoke Tests

```bash
# Run pytest smoke tests
pytest tests/smoke/ -v -m smoke

# Or manual API tests
curl -s https://nikita-api-1040094048579.us-central1.run.app/api/v1/users/me \
  -H "Authorization: Bearer test" | jq .status_code
# Expected: 401 (unauthorized) - proves endpoint is responding
```

---

## E2E Verification (Optional but Recommended)

### Via Telegram MCP

```bash
# If Telegram MCP is available
# 1. Get chat with test user
mcp__telegram-mcp__get_direct_chat_by_contact(name="Test User")

# 2. Send test message
mcp__telegram-mcp__send_message(chat_id=<id>, message="test message")

# 3. Wait for response
mcp__telegram-mcp__get_history(chat_id=<id>, limit=2)
```

### Via Live Testing

1. Open Telegram app
2. Send message to @Nikita_my_bot
3. Verify response received
4. Check logs for errors

---

## Rollback Procedure

If verification fails:

```bash
# 1. Get previous revision
gcloud run revisions list \
  --service nikita-api \
  --region us-central1 \
  --format="table(name,status.conditions[0].status)" \
  --limit=5

# 2. Route traffic to previous revision
gcloud run services update-traffic nikita-api \
  --region us-central1 \
  --to-revisions=nikita-api-00XXX-xxx=100
```

---

## Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Deploy success | `gcloud run deploy` | "Service deployed" |
| Health endpoint | `curl /health` | `{"status": "healthy"}` |
| Deep health | `curl /health/deep` | `{"database": "connected"}` |
| No errors (15m) | `gcloud logging read` | 0 ERROR entries |
| Smoke tests | `pytest tests/smoke/` | All PASS |
| E2E (if needed) | Telegram message | Response received |

---

## Completion Criteria

Deployment is verified when:
- [ ] Health endpoint returns 200
- [ ] Deep health shows database connected
- [ ] No new ERROR logs in last 15 minutes
- [ ] Smoke tests pass
- [ ] E2E test passes (for user-facing changes)

---

## Troubleshooting

### Health Endpoint 404
- Router not registered → Check `main.py` includes health router

### Database Connection Failed
- Connection string wrong → Check `SUPABASE_URL` env var
- Pool exhausted → Check connection limits

### Deployment Timeout
- Container start slow → Check Dockerfile, reduce dependencies
- Cold start → Expected first request takes 60-90s

### E2E Test Fails
- Bot not responding → Check webhook URL configuration
- Wrong response → Check logs for actual error
