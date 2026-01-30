# Log Monitoring Workflow

## Overview

Cloud Run logs provide critical visibility into production issues. This workflow covers common log queries and error detection patterns.

---

## Log Query Basics

### Project Configuration

```bash
# Set default project
gcloud config set project gcp-transcribe-test

# Verify configuration
gcloud config list project
```

### Basic Queries

```bash
# Recent logs (all severities)
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=20 \
  --format="table(timestamp,severity,textPayload)"

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=10 \
  --project gcp-transcribe-test

# Filter by time
gcloud logging read "resource.type=cloud_run_revision AND timestamp>=\"2026-01-30T00:00:00Z\"" \
  --limit=20 \
  --project gcp-transcribe-test
```

---

## Common Error Patterns

### 1. AttributeError (Missing Attribute)

```bash
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"AttributeError\"" \
  --limit=10 \
  --project gcp-transcribe-test \
  --format="table(timestamp,textPayload)"
```

**Common causes:**
- Wrong attribute name on model
- Accessing attribute on None
- API response structure changed

### 2. TypeError (Wrong Type)

```bash
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TypeError\"" \
  --limit=10 \
  --project gcp-transcribe-test
```

**Common causes:**
- Decimal vs float arithmetic
- None passed to function expecting value
- Missing await on async function

### 3. Database Errors

```bash
gcloud logging read "resource.type=cloud_run_revision AND (textPayload:\"IntegrityError\" OR textPayload:\"OperationalError\" OR textPayload:\"asyncpg\")" \
  --limit=10 \
  --project gcp-transcribe-test
```

**Common causes:**
- Foreign key constraint violation
- Connection pool exhausted
- Session in bad state

### 4. External API Errors

```bash
gcloud logging read "resource.type=cloud_run_revision AND (textPayload:\"httpx\" OR textPayload:\"timeout\" OR textPayload:\"ConnectionError\")" \
  --limit=10 \
  --project gcp-transcribe-test
```

**Common causes:**
- Neo4j cold start timeout
- ElevenLabs API rate limit
- Claude API timeout

---

## Time-Based Queries

```bash
# Last hour
TIMESTAMP=$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$TIMESTAMP\"" \
  --limit=20 \
  --project gcp-transcribe-test

# Last 15 minutes
TIMESTAMP=$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$TIMESTAMP\"" \
  --limit=10 \
  --project gcp-transcribe-test

# Specific time range
gcloud logging read "resource.type=cloud_run_revision AND timestamp>=\"2026-01-30T10:00:00Z\" AND timestamp<=\"2026-01-30T11:00:00Z\"" \
  --limit=50 \
  --project gcp-transcribe-test
```

---

## Request Tracing

### Trace a Specific Request

```bash
# By URL path
gcloud logging read "resource.type=cloud_run_revision AND httpRequest.requestUrl:\"/api/v1/telegram/webhook\"" \
  --limit=10 \
  --project gcp-transcribe-test \
  --format=json

# By trace ID (from error log)
gcloud logging read "resource.type=cloud_run_revision AND trace=\"projects/gcp-transcribe-test/traces/TRACE_ID\"" \
  --limit=20 \
  --project gcp-transcribe-test
```

### Check Request Latency

```bash
gcloud logging read "resource.type=cloud_run_revision AND httpRequest.latency>\"5s\"" \
  --limit=10 \
  --project gcp-transcribe-test \
  --format="table(timestamp,httpRequest.requestUrl,httpRequest.latency)"
```

---

## Revision-Specific Logs

```bash
# Get current revision
REVISION=$(gcloud run services describe nikita-api --region us-central1 --format="value(status.traffic[0].revisionName)")

# Logs for specific revision
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.revision_name=\"$REVISION\"" \
  --limit=20 \
  --project gcp-transcribe-test
```

---

## Error Aggregation

### Count Errors by Type

```bash
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=100 \
  --project gcp-transcribe-test \
  --format=json | jq -r '.[].textPayload' | grep -oE "^\w+Error" | sort | uniq -c | sort -rn
```

### Errors by Hour

```bash
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)\"" \
  --limit=500 \
  --project gcp-transcribe-test \
  --format=json | jq -r '.[].timestamp[:13]' | sort | uniq -c
```

---

## Alerting Queries (for monitoring)

### Critical Errors (last 5 min)

```bash
# Run this periodically
COUNT=$(gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ)\"" \
  --project gcp-transcribe-test \
  --format=json | jq length)

if [ "$COUNT" -gt 0 ]; then
  echo "ALERT: $COUNT errors in last 5 minutes"
fi
```

### Specific Error Pattern

```bash
# Check for stuck conversations
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"stuck conversation\"" \
  --limit=5 \
  --project gcp-transcribe-test
```

---

## Output Formats

```bash
# Table (human readable)
--format="table(timestamp,severity,textPayload)"

# JSON (for processing)
--format=json

# Just the payload
--format="value(textPayload)"

# Custom format
--format="table[box](timestamp.date('%Y-%m-%d %H:%M'),severity,textPayload:label=Message)"
```

---

## Quick Reference

| Query Type | Command Suffix |
|------------|----------------|
| All errors | `severity>=ERROR` |
| Warnings+ | `severity>=WARNING` |
| Last hour | `timestamp>="$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)"` |
| Last 24h | `timestamp>="$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)"` |
| By text | `textPayload:"search term"` |
| By URL | `httpRequest.requestUrl:"/path"` |
| Slow requests | `httpRequest.latency>"5s"` |

---

## Troubleshooting Checklist

When investigating production issues:

1. [ ] Check ERROR logs in last 15 minutes
2. [ ] Check WARNING logs for patterns
3. [ ] Trace specific request if available
4. [ ] Compare with previous revision logs
5. [ ] Check for timeout patterns
6. [ ] Verify database connectivity
7. [ ] Check external API responses
