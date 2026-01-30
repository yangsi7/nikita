---
name: tdd-verification
description: Rigorous TDD workflow enforcement with Red-Green-Refactor cycle, deployment verification, and log monitoring. Use when fixing bugs, implementing features, or verifying deployments.
parameters:
  mode:
    type: string
    enum: [fix, deploy-verify, log-check]
    default: fix
    description: "Mode: fix (full TDD cycle), deploy-verify (post-deployment smoke tests), log-check (Cloud Run log monitoring)"
  issue:
    type: string
    optional: true
    description: "GitHub issue number to fix (e.g., '25')"
  target:
    type: string
    optional: true
    description: "Target file or module for the fix"
---

# TDD Verification Skill

## Overview

This skill enforces **rigorous TDD practices** - no fix is complete until it's verified through the full Red-Green-Refactor cycle AND deployed with smoke tests.

**Core principle:** Red → Green → Verify → Deploy → Smoke Test → E2E → Close

**Announce at start:** "I'm using the tdd-verification skill to ensure this fix is properly tested."

---

## Quick Reference

| Phase | Key Activities | Verification |
|-------|---------------|--------------|
| **1. RED** | Write failing test for the fix | `pytest -v -x` → MUST FAIL |
| **2. GREEN** | Implement minimal fix | `pytest -v -x` → MUST PASS |
| **3. VERIFY** | Run all related tests | `pytest tests/affected/` → ALL PASS |
| **4. DEPLOY** | Push to Cloud Run | `gcloud run deploy` → Health check PASS |
| **5. SMOKE** | Post-deployment verification | `/health` + `/health/deep` → 200 OK |
| **6. E2E** | End-to-end verification | Telegram MCP or live test → Response received |
| **7. CLOSE** | Close issue with evidence | `gh issue close` → Done |

---

## Mode 1: Fix (Full TDD Cycle)

**Trigger:** `/tdd-fix <issue_number>` or when fixing any bug

### Mandatory Steps

```
1. READ ISSUE
   └── gh issue view <number>
   └── Understand the bug and expected behavior

2. RED: Write Failing Test
   └── Create test in tests/pipeline_fixes/test_issue_<number>_*.py
   └── pytest tests/pipeline_fixes/test_issue_<number>_*.py -v -x
   └── VERIFY: Test MUST FAIL (if it passes, test is wrong)

3. GREEN: Implement Fix
   └── Make minimal code change to fix the issue
   └── pytest tests/pipeline_fixes/test_issue_<number>_*.py -v -x
   └── VERIFY: Test MUST PASS

4. VERIFY: Full Test Suite
   └── pytest tests/affected_module/ -v
   └── VERIFY: ALL tests pass, no regressions

5. DEPLOY: Cloud Run
   └── gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test
   └── VERIFY: Deployment successful, health check PASS

6. SMOKE: Post-Deployment
   └── curl https://nikita-api-1040094048579.us-central1.run.app/health
   └── curl https://nikita-api-1040094048579.us-central1.run.app/health/deep
   └── VERIFY: Both return 200 OK

7. LOGS: Check for Errors
   └── gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10 --project gcp-transcribe-test
   └── VERIFY: No new errors related to the fix

8. E2E: End-to-End Test (if applicable)
   └── Use Telegram MCP to send test message
   └── VERIFY: Response received, no errors in logs

9. CLOSE: Issue with Evidence
   └── gh issue close <number> --comment "Verified via TDD: [test file], [deployment], [E2E]"
```

### Evidence Requirements

Every fix MUST include:
- **Test file location**: `tests/pipeline_fixes/test_issue_XXX_*.py`
- **Test count**: Number of tests added
- **Code change**: File and line number of the fix
- **Deployment revision**: `nikita-api-00XXX-xxx`
- **E2E verification**: Screenshot or log excerpt

---

## Mode 2: Deploy-Verify (Post-Deployment)

**Trigger:** `/verify-deploy` or after any deployment

### Verification Steps

```bash
# 1. Health check
curl -s https://nikita-api-1040094048579.us-central1.run.app/health | jq .
# Expected: {"status": "healthy", "service": "nikita-api"}

# 2. Deep health (database)
curl -s https://nikita-api-1040094048579.us-central1.run.app/health/deep | jq .
# Expected: {"status": "healthy", "database": "connected"}

# 3. Check recent errors
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)\"" --limit=5 --project gcp-transcribe-test --format=json | jq '.[].textPayload'

# 4. Run smoke tests
pytest tests/smoke/ -v -m smoke
```

---

## Mode 3: Log-Check (Error Monitoring)

**Trigger:** `/check-logs` or when investigating production issues

### Log Queries

```bash
# Recent errors (last hour)
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20 --project gcp-transcribe-test --format="table(timestamp,textPayload)"

# Specific error pattern
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"AttributeError\"" --limit=10 --project gcp-transcribe-test

# Request tracing
gcloud logging read "resource.type=cloud_run_revision AND httpRequest.requestUrl:\"/api/v1/telegram/webhook\"" --limit=5 --project gcp-transcribe-test --format=json

# Warning + Error logs
gcloud logging read "resource.type=cloud_run_revision AND severity>=WARNING" --limit=20 --project gcp-transcribe-test
```

---

## Test File Conventions

### Location
- Bug fixes: `tests/pipeline_fixes/test_issue_<number>_<description>.py`
- Feature tests: `tests/<module>/test_<feature>.py`
- Smoke tests: `tests/smoke/test_deployment.py`

### Naming
```python
# tests/pipeline_fixes/test_issue_025_session_factory.py
"""Tests for Issue #25: async_generator context manager fix."""

def test_summary_generator_uses_session_maker():
    """Verify SummaryGenerator uses get_session_maker() not async with."""
    ...

def test_layer_composer_session_factory():
    """Verify LayerComposer uses get_session_maker()."""
    ...
```

---

## Issue Closure Template

```bash
gh issue close <number> --comment "$(cat <<'EOF'
## Verified FIXED via TDD

**Test Evidence:**
- Tests: `tests/pipeline_fixes/test_issue_<number>_*.py` (N tests)
- All tests passing: `pytest tests/pipeline_fixes/test_issue_<number>_*.py -v`

**Code Fix:**
- File: `module/file.py:LINE`
- Change: [description]

**Deployment:**
- Revision: `nikita-api-00XXX-xxx`
- Health check: PASS
- Smoke tests: PASS

**E2E Verification:**
- [Test description and result]
EOF
)"
```

---

## Anti-Patterns (DO NOT)

1. **Claiming "fixed" without tests** - Every fix needs a test
2. **Skipping RED phase** - If test passes immediately, it's not testing the bug
3. **Deploying without local verification** - Run full test suite first
4. **Closing issues without E2E** - Production verification is mandatory
5. **Ignoring log errors** - Check logs after every deployment

---

## Integration with SDD

When working within SDD workflow (Spec implementation):
1. Use `/tdd-fix` for any bugs discovered during implementation
2. Create tests in the spec's test directory first
3. Reference issue number in commit message
4. Update tasks.md with fix details

---

## Workflow Files

- `workflows/red-green.md` - Detailed Red-Green-Refactor process
- `workflows/deploy-verify.md` - Deployment verification checklist
- `workflows/log-monitor.md` - Log monitoring and error detection
- `templates/smoke-test.py` - Smoke test template
- `templates/verify-script.sh` - Deployment verification script
