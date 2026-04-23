# Live Testing Protocol — Canonical Dogfood Walk

**This rule fires** for any live dogfood / live-E2E walk that exercises the real user flow against deployed Cloud Run + Vercel + Supabase + Telegram. Encodes Walk Y (2026-04-23) anti-fabrication discipline as a durable gate. Per ADR-011.

**Authority**: Walk Y subagent fabricated `auth.users` row + minted JWT via `signInWithPassword`, producing 2 CRITICAL findings (#410, #411) the user could not trust. Anti-fabrication discipline was implicit prior to this rule; making it durable.

## Prerequisites

- **Env source**: walk subagents MUST source the real `.env` (or production-equivalent) — backend URL, Supabase URL, anon key, service-role key (read-only ops only). Playwright dummy `example.run.app` env only works for mocked specs.
- **Plus-alias inbox**: use `youwontgetmyname777+walkN@gmail.com` form for test accounts so Gmail MCP search (admin inbox) still surfaces magic-link mail.
- **Telegram MCP**: confirm session is alive via `mcp__telegram-mcp__get_me` before walk start. Re-mint via `../telegram-mcp/session_string_generator.py` if dead.
- **Walk identity**: pick one walk label (`walkY`, `walkZ`, ...) and use it consistently in user-facing inputs (display name, etc.) so DB cleanup is greppable.

## 12-Step Walk Protocol

Use abstract `<USER_INPUT>` placeholders for what the simulated user types and `<CODE>` for verification codes copied from email/Telegram.

1. **Cold-start landing** — `mcp__claude-in-chrome__navigate` to apex URL. Read console + network surfaces; assert no 4xx/5xx.
2. **CTA click** — click landing CTA via Chrome MCP `click`. Verify route lands on the intended next step (Telegram deep-link OR /onboarding/auth, depending on canonical direction per ADR-010).
3. **Telegram deep-link follow** — `mcp__telegram-mcp__send_message` to `@Nikita_my_bot` with `<USER_INPUT>` matching the deep-link payload. Wait for first bot reply.
4. **Conversational onboarding** — drive turn-by-turn via `mcp__telegram-mcp__send_message`; for each turn capture (a) user input, (b) bot reply, (c) extracted slots from logs (`gcloud logging read`).
5. **Email collection** — when bot asks for email, send `<USER_INPUT>` containing the plus-alias address. Do NOT skip; do NOT fabricate.
6. **Magic-link / OTP retrieval** — `mcp__claude_ai_Gmail__search_threads` with `newer_than:5m` (no complex filters per `feedback_gmail_mcp_search.md`). Extract `<CODE>` or magic-link URL.
7. **Verification submit** — paste `<CODE>` back into Telegram OR navigate the magic-link URL via Chrome MCP. Capture the verification response.
8. **Portal handoff** — once verified, expect a portal URL surfaced in Telegram or auto-redirect. Navigate via Chrome MCP. Read console for hydration/JS errors.
9. **Wizard completion** — drive remaining onboarding wizard steps via Chrome MCP `fill` / `click`. Capture progress_pct after every step (must be monotonic).
10. **Dashboard arrival** — assert final route matches expected dashboard. Capture screenshot for the run artifact.
11. **Persistence check** — read user state via Supabase MCP `execute_sql` (read-only): `SELECT * FROM user_profiles WHERE id = (SELECT id FROM auth.users WHERE email = '<plus-alias>')`. Verify slot values match what was typed.
12. **Cleanup** — apply DB cleanup SQL (template below) with exact-email match. Confirm row counts deleted.

If ANY step is unreachable due to a real bug → STOP, file a HIGH-severity GH issue (per `.claude/rules/issue-triage.md`) with reproduction, do NOT fabricate state to continue.

## Critical Anti-Patterns (PR-blockers)

1. **`INSERT INTO auth.users`** — fabricates user identity; bypasses the auth flow under test.
2. **`signInWithPassword({email, password:'...'})`** — uses password-grant when system is passwordless; mints session that doesn't reflect real magic-link or OTP path.
3. **`E2E_AUTH_BYPASS=true`** in walk env — bypasses auth gates entirely; defeats the purpose of live walks.
4. **Custom JWT minting from service-role key** — same shortcut, same trust failure.

Cross-reference: `~/.claude/rules/operating-principles.md` Core Behavior #9; `.claude/rules/agentic-design-patterns.md` for agent-flow concerns inside the walk.

## DB Cleanup SQL Template (FK-safe order, exact email match)

Per `project_users_table_schema.md` (auto-memory): `public.users` has no email column; join through `auth.users`.

```sql
-- Replace <EMAIL> with the exact plus-alias used in the walk
WITH target AS (
  SELECT id FROM auth.users WHERE email = '<EMAIL>'
)
DELETE FROM user_metrics                WHERE user_id IN (SELECT id FROM target);
DELETE FROM user_vice_preferences       WHERE user_id IN (SELECT id FROM target);
DELETE FROM scheduled_events            WHERE user_id IN (SELECT id FROM target);
DELETE FROM memories                    WHERE user_id IN (SELECT id FROM target);
DELETE FROM user_profiles               WHERE id     IN (SELECT id FROM target);
DELETE FROM users                       WHERE id     IN (SELECT id FROM target);
DELETE FROM auth.users                  WHERE id     IN (SELECT id FROM target);
```

Run via `mcp__supabase__execute_sql`. Verify each `DELETE` row count matches expectation; if a row count is unexpectedly zero, the walk did not actually create that artifact and the spec coverage has a gap — file a MEDIUM-severity GH issue (per `.claude/rules/issue-triage.md`).

## Reference

- ADR: `~/.claude/ecosystem-spec/decisions/ADR-011-live-testing-protocol-as-rule.md`
- Sister rules: `.claude/rules/agentic-design-patterns.md`, `.claude/rules/pr-workflow.md` step 8, `.claude/rules/testing.md` Live-Dogfood Anti-Patterns
- Memory: `~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/feedback_no_db_fabrication_in_dogfood.md`
- Walk Y precedent: subagent `a4324f078e9329b23` sanitiser audit (Plan v17.1 §18.8)
