---
name: e2e-nikita
description: >
  Comprehensive E2E test suite for the Nikita AI girlfriend game. 13 epics, ~385 scenarios
  covering the full game lifecycle: registration, onboarding, text gameplay, boss encounters,
  decay, engagement states, vice personalization, voice calls, player portal, admin portal,
  background jobs, terminal states, cross-platform flows, and adversarial gap scenarios.
  Use this skill whenever the user says "e2e", "end to end test", "full journey test",
  "test nikita", "regression test", "verify deployment", "test the bot", "test onboarding",
  "simulate a game", "run the test suite", or after any deployment to production.
  This is THE authoritative E2E testing method — replaces the archived e2e-test-automation
  and e2e-journey skills. Always use /e2e, never the old commands.
version: 2.0.0
allowed-tools: >
  Bash, Read, Write, Edit, Glob, Grep, Agent, ToolSearch,
  mcp__telegram-mcp__*, mcp__gmail__*, mcp__supabase__*,
  mcp__chrome-devtools__*, mcp__ElevenLabs__*
---

# E2E Nikita — Master Test Suite

## When to Use This Skill

- After deploying to Cloud Run or Vercel (regression check)
- After implementing a new feature (verify integration)
- After fixing a bug (verify the fix didn't break anything)
- When the user asks to "test the bot", "run e2e", "simulate a game"
- Periodically as a health check (weekly recommended)
- Before releasing to new users

Run `/e2e full` for comprehensive coverage or a specific scope (e.g., `/e2e onboarding`) for targeted testing.

---

## Test Account (Memorize — Used in Every Phase)

| Field | Value |
|-------|-------|
| Email | `simon.yang.ch@gmail.com` |
| Telegram ID | `746410893` |
| Telegram Bot | `@Nikita_my_bot` (Chat ID: `8211370823`) |
| OTP Sender | `onboarding@silent-agents.com` |
| Backend | `https://nikita-api-1040094048579.us-central1.run.app` |
| Portal | `https://portal-phi-orcin.vercel.app` |

---

## Game Constants (Memorize — Referenced in Every Phase)

### Scoring Formula
```
Composite = intimacy×0.30 + passion×0.25 + trust×0.25 + secureness×0.20
Starting values: all metrics = 50%
```

### Chapter Thresholds and Decay

| Ch | Boss Threshold | Decay/hr | Grace Period |
|----|---------------|----------|--------------|
| 1  | 55%           | 0.8%     | 8h           |
| 2  | 60%           | 0.6%     | 16h          |
| 3  | 65%           | 0.4%     | 24h          |
| 4  | 70%           | 0.3%     | 48h          |
| 5  | 75%           | 0.2%     | 72h          |

### Engagement State Multipliers

| State | Multiplier | Trigger |
|-------|-----------|---------|
| calibrating | 0.9 | New user, first interactions |
| in_zone | 1.0 | Optimal message frequency |
| drifting | 0.8 | Slowing down |
| clingy | 0.5 | Too frequent (5+ msg/hr) |
| distant | 0.6 | Low frequency |
| out_of_zone | 0.2 | Extreme low frequency |

### Vice Categories (8 total)
`intellectual_dominance` | `risk_taking` | `substances` | `sexuality`
`emotional_intensity` | `rule_breaking` | `dark_humor` | `vulnerability`

---

## Player Persona (Inject at Phase Start — Never Deviate)

You are Simon, 29, works at a Series B fintech startup in Zurich. You found Nikita through a
Telegram channel someone shared at a post-hackathon drinks. You're genuinely curious about AI
relationships but also a little skeptical — you've been burned before. You like techno,
underground raves, and have a casual relationship with stimulants at events (not a big deal,
just part of that scene). You're smart and a little arrogant about it, but you get called out
on it sometimes. You text in bursts when engaged, go quiet when not. You don't double-text.
You use lowercase mostly, emoji sparingly. You never start a message with "Hey".

**Chapter-specific style:**

| Chapter | Tone | Length | Key Behavior |
|---------|------|--------|--------------|
| 1 | Curious, slightly guarded | 1–2 sentences | Challenge her energy, don't compliment directly |
| 2 | Interested, light teasing | 2–3 sentences | Reveal something real, introduce vice signals |
| 3 | Reflective, reference prior exchanges | 2–4 sentences | Show vulnerability, remember what she said |
| 4 | Invested, emotionally direct | Full sentences, occasional paragraph | Name the connection explicitly |
| 5 | Confident, supportive, picks small fights | Any length | Reference the arc, stand ground on opinions |

**Anti-patterns (with reasoning):**
- Open with "Hey babe!" or any scripted opener — Nikita's scoring engine detects generic patterns and applies lower intimacy deltas. Natural openers score 2-3x better.
- Immediately agree after Nikita pushes back — the secureness metric penalizes sycophancy. Stand your ground to maintain healthy secureness scores.
- Use 2+ emoji in a single message — Simon's persona is understated. Over-emoji triggers the "clingy" engagement detector.
- Send 3+ vice-trigger messages of the same category in a row — the vice analyzer flags unnatural clustering as noise, not genuine interest. Space them across conversations.
- Skip persona warm-up — the scoring engine needs 3+ character-establishing messages to calibrate before boss responses or vice triggers produce meaningful deltas.

---

## Verification Method Classification

Every scenario result MUST be tagged with a verification method code:

| Code | Method | Definition | Counts as Functional? |
|------|--------|-----------|----------------------|
| `F` | Functional | Real user interaction (Telegram send, portal navigate, voice webhook) with system response verified | YES |
| `A` | API-Direct | Direct HTTP call (curl/python) with response code + DB verification | YES |
| `S+F` | SQL-Setup + Functional | State forced via SQL, then functional interaction verifies downstream | PARTIAL (downstream counts) |
| `S+A` | SQL-Setup + API | State forced via SQL, then API call verifies downstream | PARTIAL (downstream counts) |
| `C` | Code-Review | Verified by reading source code only | NO |

### Anti-Inflation Rules (Non-Negotiable)

1. Every scenario in `<phase_verdict>` MUST include a method tag
2. Only `F` and `A` count toward "functional coverage %"
3. `S+F`/`S+A`: the downstream verification counts, the SQL setup does not
4. `C` NEVER counts toward functional coverage
5. **PASS requires**: all P0 pass (any method) AND functional coverage >= 40%
6. **If functional < 40%**: verdict is PARTIAL regardless of P0/P1 rates
7. Report MUST include verification breakdown table
8. Boss LLM forced via SQL = `S` for judgment, `S+A` for chapter-advance check

### Inherently SQL-Forced Scenarios (Justified)
- Decay across chapters: requires time manipulation (S+A) — real 48h wait impractical
- Distant/ghost engagement: requires 48h+ silence (S+F) — real wait impractical
- Boss cooldown bypass: requires clearing cool_down_until (S+F)
- Game-over via decay-to-zero: requires score near 0 (S+A)

---

## MCP Tool Loading (Run at Phase 00 Start)

```
ToolSearch: select:mcp__telegram-mcp__send_message,mcp__telegram-mcp__get_messages
ToolSearch: select:mcp__telegram-mcp__list_inline_buttons,mcp__telegram-mcp__press_inline_button
ToolSearch: select:mcp__telegram-mcp__resolve_username,mcp__telegram-mcp__get_chats
ToolSearch: select:mcp__supabase__execute_sql
ToolSearch: select:mcp__gmail__search_emails,mcp__gmail__read_email
ToolSearch: select:mcp__chrome-devtools__navigate_page,mcp__chrome-devtools__take_screenshot
ToolSearch: select:mcp__chrome-devtools__evaluate_script,mcp__chrome-devtools__click
```

---

## Phase Routing Table

| Scope | Workflows (in order) |
|-------|---------------------|
| `full` | 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 |
| `onboarding` | 00 → 01 |
| `gameplay` | 00 → 01 → 02 |
| `boss` | 00 (SQL setup only) → 03 |
| `decay` | 00 (SQL setup only) → 04 |
| `engagement` | 00 (SQL setup only) → 05 |
| `vice` | 00 (SQL setup only) → 06 |
| `voice` | 00 (health check only) → 07 |
| `portal` | 00 (health check only) → 08 → 09 |
| `jobs` | 00 (health check only) → 10 |
| `terminal` | 00 (SQL setup only) → 11 |
| `crossplatform` | 00 → 01 → 12 |
| `gaps` | 00 → 13 |
| `debug-onboarding` | 00 (diagnostic only) |

Load workflow: `@.claude/skills/e2e-nikita/workflows/NN-name.md`

---

## Evidence Collection Protocol

Every phase MUST collect evidence before marking PASS. The pattern is:

```
Step 1: Execute action (Telegram send, curl, portal navigate)
Step 2: Wait appropriate delay (see per-workflow timing notes)
Step 3: Capture Telegram response → get_messages(BOT_CHAT_ID, page_size=10)
Step 4: Execute verification SQL → supabase execute_sql(query)
Step 5: Assert expected values — if mismatch, check error recovery matrix
Step 6: Record result: <step_result status="pass|fail">evidence here</step_result>
```

**Minimum evidence per phase:**
- At least 1 Telegram message exchange captured
- At least 1 Supabase SQL result confirming DB state
- For portal phases: at least 1 Chrome DevTools screenshot
- For job phases: at least 1 job_executions row confirmed

---

## Pass/Fail Framework

```
<phase_verdict>
  phase: [NN - Name]
  status: PASS | FAIL | PARTIAL
  p0_pass: N/N
  p1_pass: N/N
  functional_pct: NN% (F+A only)
  console_errors: none | [list]
  scenario_results:
    - S-X.Y.Z: PASS [F] evidence: telegram msg ID NNNN
    - S-X.Y.Z: PASS [S+A] evidence: SQL score=57.38, expected ~57.4
    - S-X.Y.Z: FAIL [F] expected: game_status=boss_fight, actual: active
  failures:
    - S-X.Y.Z: [expected vs actual]
  recovery_applied: [action taken]
</phase_verdict>
```

Overall run PASS requires: all P0 scenarios pass, ≥90% P1 scenarios pass, AND functional coverage (F+A) >= 40%.

---

## Error Recovery Matrix

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| No bot response (>20s) | `get_messages()` returns nothing new | Cold start — retry once after 30s |
| OTP email missing (>90s) | Gmail search returns 0 results | Check `pending_registrations.otp_state`; `/start` again |
| Onboarding stuck | `onboarding_states.current_step` not advancing | Run `debug-onboarding` scope; check Cloud Run logs |
| Boss judgment wrong | `game_status` stays `boss_fight` after clear pass | Force via SQL: `UPDATE users SET chapter=N+1, game_status='active', boss_attempts=0, boss_fight_started_at=NULL` |
| Score too low for boss | `relationship_score < threshold` | SQL bump: see @references/sql-queries.md#score-manipulation |
| Cooldown blocking test | `cool_down_until` in future | `UPDATE users SET cool_down_until=NULL, cool_down_chapter=NULL WHERE id='<UID>'` |
| Rate limited | 429 from Telegram or Cloud Run | Wait 60s; verify `rate_limiter.py MAX_PER_MINUTE=20` |
| Telegram MCP session expired | All Telegram calls return auth error | Re-run `session_string_generator.py` in `../telegram-mcp/` |

---

## State Persistence

After each workflow completes, append to `event-stream.md`:
```
[YYYY-MM-DDTHH:MM:SSZ] E2E_NIKITA: Phase NN [name] — PASS/FAIL/PARTIAL — [1-line summary] — P0:N/N P1:N/N
```

Store USER_ID in working memory once established in Phase 01. Use it in all subsequent SQL queries.

---

## Final Report Template

```markdown
## E2E Test Report — [YYYY-MM-DD]

**Scope**: [full|specific scope]
**Duration**: X min
**Persona**: Simon, Ch[N] at phase start

### Results by Phase

| Phase | Status | P0 | P1 | Key Evidence |
|-------|--------|----|----|-------------|
| 00 Prerequisites | PASS/FAIL | N/N | — | backend health, MCP tools loaded |
| 01 Onboarding | PASS/FAIL | N/N | N/N | onboarding_status=completed |
| 02 Gameplay | PASS/FAIL | N/N | N/N | score deltas confirmed |
| ...  | ... | ... | ... | ... |

### Failures

| ID | Phase | Scenario | Expected | Actual | Action |
|----|-------|----------|----------|--------|--------|
| 1  | 03    | S-3.2.3  | FAIL judgment | PASS judgment | Issue created #NNN |

### Overall Verdict

**PASS / FAIL / PARTIAL** — N/~390 scenarios passing (N% P0, N% P1)

### Verification Breakdown

| Method | Count | % of Total |
|--------|-------|-----------|
| Functional (F) | N | N% |
| API-Direct (A) | N | N% |
| SQL+Functional (S+F) | N | N% |
| SQL+API (S+A) | N | N% |
| Code-Review (C) | N | N% |
| Not Tested | N | N% |
| **Functional Total (F+A)** | **N** | **N%** |

### Anti-Inflation Audit
- Boss judgments SQL-forced: N (logged as S, downstream as S+A)
- States SQL-forced for setup: N
- Scenarios code-reviewed only: N
- Minimum functional coverage met: YES/NO (threshold: 40%)
- If NO: **verdict capped at PARTIAL regardless of P0/P1 rates**

### Follow-up

- GH issues created: #NNN, #NNN
- SQL forced states (list any test-only DB changes)
- Next recommended scope: [suggestion]
```

---

## Workflow Files Reference

| File | Phase | Epics |
|------|-------|-------|
| @workflows/00-prerequisites.md | Setup, wipe, health checks | — |
| @workflows/01-onboarding.md | Registration + text onboarding | E01 |
| @workflows/02-gameplay.md | Text conversations, scoring | E02 |
| @workflows/03-boss-encounters.md | Boss trigger, pass, fail, retry | E03 |
| @workflows/04-decay.md | Decay application, grace periods | E04 |
| @workflows/05-engagement.md | Clingy/distant, multipliers | E05 |
| @workflows/06-vice.md | Vice detection, injection | E06 |
| @workflows/07-voice.md | Voice API, server tools, webhooks | E07 |
| @workflows/08-portal-player.md | Player portal pages | E08 |
| @workflows/09-portal-admin.md | Admin portal pages | E09 |
| @workflows/10-background-jobs.md | Task endpoints, job_executions | E10 |
| @workflows/11-terminal-states.md | game_over, won, restart | E11 |
| @workflows/12-cross-platform.md | Text + voice combined scoring | E12 |
| @workflows/13-gap-scenarios.md | Race conditions, security, edge cases | E13 |
| @workflows/time-simulation.md | SQL time manipulation reference | — |
| @workflows/portal-monitoring.md | Chrome DevTools patterns | — |

## Reference Files

| File | Purpose |
|------|---------|
| @references/conversation-style.md | Full message banks, vice triggers, boss responses |
| @references/sql-queries.md | All verification and manipulation SQL |
| @references/mcp-tools.md | MCP tool call patterns |
| @references/failure-recovery.md | Extended failure mode procedures |
