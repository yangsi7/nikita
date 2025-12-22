---
description: Execute E2E tests for Nikita using Telegram MCP, Gmail MCP, Supabase MCP, Chrome DevTools MCP, and gcloud CLI (project)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Bash(gcloud:*), Bash(curl:*), MCPSearch, mcp__telegram-mcp__*, mcp__gmail__*, mcp__supabase__*, mcp__chrome-devtools__*
argument-hint: [full|telegram|portal|otp|conversation]
---

# E2E Test Command

You are now executing the `/e2e-test` command. This command runs end-to-end tests for Nikita using MCP tools and gcloud CLI via the **e2e-test-automation skill**.

## Your Task

Execute comprehensive E2E tests using the **e2e-test-automation skill** (@.claude/skills/e2e-test-automation/SKILL.md).

**Scope Argument:** `$ARGUMENTS`

If no scope provided, default to `telegram` for quick verification.

## Test Scopes

| Scope | What It Tests | Duration |
|-------|---------------|----------|
| `full` | All systems (Telegram, DB, OTP, logs, portal) | 5-10 min |
| `telegram` | Bot interactions, conversations, engagement | 2-3 min |
| `portal` | Web portal via Chrome DevTools | 2-3 min |
| `otp` | OTP/email flow via Gmail MCP | 1-2 min |
| `conversation` | Multi-turn conversation, memory, scoring | 3-5 min |

## Process Overview

### Phase 0: Prerequisites Check

Verify all MCP servers are available:

```
MCPSearch query="select:mcp__telegram-mcp__get_me"
MCPSearch query="select:mcp__gmail__search_emails"
MCPSearch query="select:mcp__supabase__execute_sql"
```

Verify Cloud Run deployment:
```bash
gcloud run services describe nikita-api --region us-central1 --format='value(status.url)'
```

### Phase 1: Execute Tests Based on Scope

**Scope: telegram**
1. Find bot chat via `mcp__telegram-mcp__list_chats`
2. Send test message via `mcp__telegram-mcp__send_message`
3. Wait 10-15 seconds for LLM processing
4. Get response via `mcp__telegram-mcp__get_messages`
5. Verify DB state via `mcp__supabase__execute_sql`

**Scope: otp**
1. Search for OTP emails via `mcp__gmail__search_emails`
2. Read latest OTP via `mcp__gmail__read_email`
3. Verify pending_registrations via Supabase

**Scope: portal**
1. Navigate via `mcp__chrome-devtools__navigate_page`
2. Take screenshot via `mcp__chrome-devtools__take_screenshot`
3. Check elements via `mcp__chrome-devtools__evaluate_script`

**Scope: full**
Run all of the above in sequence.

### Phase 2: Database Verification

Always verify database state after tests:

```sql
-- Check conversations logged
SELECT COUNT(*) FROM conversations WHERE created_at > NOW() - INTERVAL '1 hour';

-- Check engagement state updated
SELECT current_state, updated_at FROM engagement_state ORDER BY updated_at DESC LIMIT 1;

-- Check generated_prompts populated (Spec 012)
SELECT COUNT(*) FROM generated_prompts WHERE created_at > NOW() - INTERVAL '1 hour';
```

### Phase 3: Log Analysis

Check production logs for errors:

```bash
gcloud run services logs read nikita-api --region us-central1 --limit 100 2>&1 | grep -i "error\|exception"
```

### Phase 4: Generate Report

Use the report template from the skill:

```markdown
## E2E Test Report - [DATE]

### Scope: [scope]

### Test Results

| Test | Status | Evidence |
|------|--------|----------|
| [test name] | PASS/FAIL | [evidence] |

### Issues Found

- [List issues if any]

### Metrics

- Test duration: X min
- Bot response time: X ms
- Errors in logs: X
```

### Phase 5: Update Event Stream

Log test result:

```
[TIMESTAMP] E2E_TEST: [scope] - PASS/FAIL - [brief summary]
```

## Workflow References

Detailed instructions for each test type:

- @.claude/skills/e2e-test-automation/workflows/test-discovery.md
- @.claude/skills/e2e-test-automation/workflows/telegram-testing.md
- @.claude/skills/e2e-test-automation/workflows/portal-testing.md
- @.claude/skills/e2e-test-automation/workflows/database-verification.md
- @.claude/skills/e2e-test-automation/workflows/log-analysis.md

## Reference Documentation

- @.claude/skills/e2e-test-automation/references/mcp-tool-usage.md
- @.claude/skills/e2e-test-automation/references/test-patterns.md
- @.claude/skills/e2e-test-automation/references/failure-modes.md

## Example

See @.claude/skills/e2e-test-automation/examples/full-journey-test.md for a complete walkthrough.

## Success Criteria

Before completing the command, verify:

- [ ] All requested tests executed
- [ ] Database state verified
- [ ] No critical errors in logs
- [ ] Report generated
- [ ] Event stream updated

## Start Now

1. Parse scope from `$ARGUMENTS` (default: `telegram`)
2. Run prerequisites check
3. Execute tests for specified scope
4. Verify database state
5. Check logs for errors
6. Generate report
7. Update event-stream.md

Begin by loading the MCP tools needed for the specified scope.
