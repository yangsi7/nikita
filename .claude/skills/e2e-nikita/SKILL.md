---
name: e2e-nikita
description: >
  Complete user journey simulation for the Nikita AI girlfriend game. Simulates a real player
  (Simon) playing through all 5 chapters — registration, onboarding, text gameplay, boss encounters,
  decay, engagement states, vice personalization, voice calls, portal monitoring, terminal states,
  and adversarial scenarios. Assesses behavioral realism (does Nikita feel human?), game balance
  (are thresholds achievable?), and classifies all findings by severity and category.
  Use this skill whenever the user says "e2e", "end to end test", "full journey test",
  "test nikita", "regression test", "verify deployment", "test the bot", "test onboarding",
  "simulate a game", "run the test suite", "play through the game", "test the experience",
  "check if nikita feels real", "behavioral test", "game balance check", or after any
  deployment to production. This is THE authoritative E2E testing method — replaces the
  archived e2e-test-automation and e2e-journey skills. Always use /e2e, never the old commands.
version: 3.0.0
allowed-tools: >
  Bash, Read, Write, Edit, Glob, Grep, Agent, ToolSearch,
  mcp__telegram-mcp__*, mcp__gmail__*, mcp__supabase__*,
  mcp__gemini__*, mcp__ElevenLabs__*
---

# E2E Nikita — Complete Journey Simulation v3

## When to Use This Skill

- After deploying to Cloud Run or Vercel (regression check)
- After implementing a new feature (verify integration)
- After fixing a bug (verify the fix didn't break anything)
- When the user asks to "test the bot", "run e2e", "simulate a game"
- Periodically as a health check (weekly recommended)
- Before releasing to new users
- When assessing behavioral quality or game balance

---

## Test Account (Memorize)

| Field | Value |
|-------|-------|
| Email | `simon.yang.ch@gmail.com` |
| Telegram ID | `746410893` |
| Telegram Bot | `@Nikita_my_bot` (Chat ID: `8211370823`) |
| Backend | `https://nikita-api-1040094048579.us-central1.run.app` |
| Portal | `https://portal-phi-orcin.vercel.app` |

---

## Game Constants (Reference — do not hardcode, check `nikita/engine/constants.py`)

| Chapter | Name | Boss Threshold | Decay/hr | Grace |
|---------|------|---------------|----------|-------|
| 1 | Curiosity | 55% | 0.8% | 8h |
| 2 | Intrigue | 60% | 0.6% | 16h |
| 3 | Investment | 65% | 0.4% | 24h |
| 4 | Intimacy | 70% | 0.3% | 48h |
| 5 | Established | 75% | 0.2% | 72h |

**Composite**: `intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20`
**Engagement multipliers** (positive deltas only): in_zone=1.0, calibrating=0.9, drifting=0.8, distant=0.6, clingy=0.5, out_of_zone=0.2

---

## Execution Modes

| Mode | Duration | Coverage | Use When |
|------|----------|----------|----------|
| `smoke` | ~30 min | Prerequisites + Onboarding + Ch1 (abbreviated) | Quick confidence check after deploy |
| `standard` | 2-3h | Full journey Ch1-Ch5 + terminal states | Regular regression testing |
| `full` | 5h+ | All chapters + system jobs + adversarial + full behavioral assessment | Pre-release, weekly deep check |

---

## Scope Routing

| Scope | Workflows |
|-------|-----------|
| `full` | 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 |
| `standard` | 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 |
| `smoke` | 00 → 01 → 02 (abbreviated: 3 exchanges, skip decay/boss) |
| `onboarding` | 00 → 01 |
| `ch1` | 00 → 02 |
| `ch2` | 00 (SQL→ch2) → 03 |
| `ch3` | 00 (SQL→ch3) → 04 |
| `ch4` | 00 (SQL→ch4) → 05 |
| `ch5` | 00 (SQL→ch5) → 06 |
| `boss` | 00 → 02(D) → 03(D) → 04(D) → 05(D) → 06(D) |
| `decay` | 00 → each chapter's Phase E |
| `portal` | 00 → each chapter's Phase B |
| `terminal` | 00 (SQL setup) → 07 |
| `jobs` | 00 → 08 |
| `adversarial` | 00 → 09 |
| `behavioral` | 00 → 01 → 02 → 10 (assessment only) |

**SQL shortcut for scoped runs** (skip to chapter N):
```sql
UPDATE users SET chapter = N, game_status = 'active', relationship_score = [threshold-5]
WHERE email = 'simon.yang.ch@gmail.com';
UPDATE user_metrics SET intimacy = X, passion = Y, trust = Z, secureness = W
WHERE user_id = (SELECT id FROM users WHERE email = 'simon.yang.ch@gmail.com');
```

---

## Simon Persona (Injected at Every Chapter)

**Profile**: 29, Series B fintech founder, Zurich. Found Nikita via Telegram channel.
**Style**: Lowercase, minimal emoji, never opens with "Hey", texts in bursts, no double-texts.
**Arc**: Guarded skeptic (Ch1) → disclosing risk-taker (Ch2) → vulnerable (Ch3) → emotionally direct (Ch4) → settled partner (Ch5).

See `references/conversation-style.md` for chapter-specific message banks and anti-patterns.

---

## Behavioral Assessment

Every chapter includes behavioral assessment at two levels:

1. **Per-response deterministic checks** (instant, no LLM): response length, repetition, memory refs, tone, emoji density, sycophancy detection.
2. **Per-chapter LLM assessment** (batched, via Gemini MCP): 6-dimension rubric scoring (1-5 scale).

See `references/behavioral-rubric.md` for the full rubric, scoring anchors, and Gemini prompt template.

**Why Gemini for assessment**: Avoids Claude-evaluating-Claude circularity. The game uses Claude for response generation — using a different model family for evaluation provides genuine diversity of judgment.

---

## Findings Classification

Every issue found during simulation is classified:
- **Severity**: CRITICAL, HIGH, MEDIUM, LOW, OBSERVATION
- **Category**: 10 bug types + 5 improvement types
- **Action**: GH issue (for bugs) or logged (for observations)

See `references/classification-system.md` for the full taxonomy.

---

## Portal Monitoring

Portal testing is embedded in EVERY chapter via Vercel browser agent — not a separate phase. The player checks their dashboard between messages. This IS the user journey.

**Player routes** (every chapter): /dashboard, /engagement, /vices, /conversations, /diary, /settings
**Admin routes** (Ch1 + Ch5): /admin/users, /admin/pipeline, /admin/conversations/[id]

See `references/monitoring-checkpoints.md` for DB snapshot queries and portal accuracy recording format.

---

## Multi-Session Checkpoints

If context compacts during a long simulation:
1. Check `event-stream.md` for last CHECKPOINT entry
2. Read the checkpoint data (chapter, score, metrics, engagement, vices)
3. Verify DB state matches checkpoint
4. Resume from the next chapter workflow

---

## Phase Execution Order

### Phase 00: Prerequisites (`workflows/00-prerequisites.md`)
- Telegram MCP session health check
- Backend health check (GET /health)
- DB wipe (FK-safe order from `references/sql-queries.md`)
- Schema validation
- Load MCP tools: `ToolSearch: select:mcp__telegram-mcp__send_message,...`
- Portal health check via browser agent

### Phase 01: Onboarding (`workflows/01-onboarding.md`)
- /start → email → OTP → verify
- 5 onboarding questions (scene, vibe, obsession, edge level, scenario)
- Profile creation verified: score=50, chapter=1, game_status=active
- First in-character Nikita message → behavioral check
- Portal check: /dashboard shows initial state

### Phase 02-06: Chapters 1-5 (`workflows/02-chapter-1-curiosity.md` through `06-chapter-5-established.md`)
Each chapter is a self-contained simulation segment containing:
- **Phase A**: 5-8 gameplay exchanges (persona-driven, with per-response checks)
- **Phase B**: Portal monitoring (browser agent, data accuracy verification)
- **Phase C**: Engagement & vice verification (DB queries)
- **Phase D**: Boss encounter (natural play → SQL guardrail → mechanics assertion)
- **Phase E**: Decay awareness (time simulation, rate verification)
- **Assessment checkpoint**: DB snapshot + behavioral scoring

### Phase 07: Terminal States (`workflows/07-terminal-and-restart.md`)
- game_over via 3 boss fails
- game_over via decay to 0
- Won state verification
- Restart flow: /start after game_over
- Account deletion

### Phase 08: System Jobs (`workflows/08-system-jobs.md`)
- Background task endpoints (decay, process, deliver, summary, boss-timeout, psyche-batch)
- Auth verification (invalid secret → 401)
- Not player-facing — no portal monitoring

### Phase 09: Adversarial (`workflows/09-adversarial.md`)
- Race conditions, security gaps, data integrity
- Timing edge cases, missing user journeys

### Phase 10: Assessment Checkpoint (`workflows/10-assessment-checkpoint.md`)
- Between-chapter assessment protocol
- Gemini behavioral rubric scoring
- Findings classification
- Decision gate

---

## Final Report

After simulation completes, generate report from `references/final-report-template.md`:
- Behavioral assessment (6 rubric dimensions, overall grade A-F)
- Game balance analysis (score trajectory, boss reachability, decay fairness)
- Classified findings (bugs by severity + improvements by category)
- Portal accuracy (routes checked, data mismatches)
- Chapter verdicts (per-chapter PASS/PARTIAL/FAIL)
- Simulation verdict (PASS/PARTIAL/FAIL)

**Pass criteria**: 0 CRITICAL, ≤2 HIGH, behavioral grade ≥ C, portal accuracy ≥ 80%

---

## Reference Files

| File | When to Read |
|------|-------------|
| `references/behavioral-rubric.md` | Before any behavioral assessment |
| `references/classification-system.md` | When classifying a finding |
| `references/monitoring-checkpoints.md` | At every checkpoint (DB snapshot, portal, time sim) |
| `references/final-report-template.md` | At simulation end |
| `references/conversation-style.md` | At chapter start (Simon persona + message banks) |
| `references/sql-queries.md` | For any DB operation |
| `references/failure-recovery.md` | When something goes wrong |
| `references/mcp-tools.md` | For MCP tool call patterns |

---

## Failure Recovery

If something goes wrong during simulation:
1. Check `references/failure-recovery.md` for the failure mode
2. Apply the documented recovery (retry, SQL fix, session refresh)
3. Log the recovery action
4. If CRITICAL: stop simulation, create GH issue
5. If recoverable: continue from current chapter

**Common failures**: No bot response (cold start, retry 30s), OTP missing (check DB), Telegram MCP expired (manual session refresh), portal blank (wait 5s, retry).
