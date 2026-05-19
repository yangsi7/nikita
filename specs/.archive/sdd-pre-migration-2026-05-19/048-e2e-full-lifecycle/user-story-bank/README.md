# E2E User Story Bank — Nikita: Don't Get Dumped

> Generated: 2026-02-14 | Scenarios: 313 base + 50 gap = 363 total
> Structure: Per-Epic (13 files) | Token budget: ~45K tokens (22% of 200K context)
> Sources: Deep audit analysis, codebase evidence, Devil's Advocate gap analysis

---

## Epic Index

| File | Epic | Scenarios | P0 | P1 | P2 | P3 | ~Tokens |
|------|------|:---------:|:--:|:--:|:--:|:--:|--------:|
| [E01-registration-onboarding.md](E01-registration-onboarding.md) | Registration & Onboarding | 28 | 8 | 12 | 6 | 2 | 3,000 |
| [E02-gameplay-loop-text.md](E02-gameplay-loop-text.md) | Gameplay Loop (Text) | 24 | 6 | 10 | 6 | 2 | 2,600 |
| [E03-boss-encounters.md](E03-boss-encounters.md) | Boss Encounters | 30 | 10 | 12 | 6 | 2 | 3,100 |
| [E04-decay-system.md](E04-decay-system.md) | Decay System | 18 | 5 | 7 | 4 | 2 | 1,500 |
| [E05-engagement-model.md](E05-engagement-model.md) | Engagement Model | 22 | 5 | 11 | 5 | 1 | 1,900 |
| [E06-vice-personalization.md](E06-vice-personalization.md) | Vice Personalization | 12 | 1 | 5 | 4 | 2 | 1,200 |
| [E07-voice-interactions.md](E07-voice-interactions.md) | Voice Interactions | 24 | 10 | 8 | 4 | 0 | 3,200 |
| [E08-portal-player.md](E08-portal-player.md) | Portal — Player | 22 | 4 | 8 | 6 | 0 | 2,800 |
| [E09-portal-admin.md](E09-portal-admin.md) | Portal — Admin | 18 | 3 | 9 | 4 | 0 | 2,400 |
| [E10-background-jobs.md](E10-background-jobs.md) | Background Jobs & Pipeline | 39 | 10 | 15 | 8 | 0 | 7,700 |
| [E11-terminal-states.md](E11-terminal-states.md) | Terminal States | 14 | 6 | 4 | 2 | 0 | 1,500 |
| [E12-cross-platform.md](E12-cross-platform.md) | Cross-Platform | 12 | 4 | 4 | 2 | 0 | 1,800 |
| [E13-gap-scenarios.md](E13-gap-scenarios.md) | Gap Scenarios (Devil's Advocate) | 50 | 17 | 23 | 10 | 0 | 12,400 |
| **TOTAL** | | **313+50** | **89** | **128** | **67** | **9** | **~45K** |

---

## Priority Distribution

| Priority | Count | % | Focus |
|----------|------:|--:|-------|
| P0-Critical | 89 | 25% | Must-pass for production readiness |
| P1-High | 128 | 35% | Required for quality release |
| P2-Medium | 67 | 18% | Edge cases, nice-to-have |
| P3-Low | 9 | 2% | Future consideration |
| **Gap (E13)** | **50** | **14%** | Race conditions, security, resilience |

---

## Game State Machine Coverage

```
                    ┌─────────────┐
     /start ───────→│  REGISTERED │
                    └──────┬──────┘
                    Onboarding (E01)
                    ┌──────▼──────┐
                    │   ACTIVE    │◄──── Recovery (E05 US-5.3)
                    └──┬───┬───┬──┘
          Score ≥ T    │   │   │   Score = 0 via decay
     ┌─────────────────┘   │   └────────────────┐
     │                     │                    │
┌────▼─────┐    Decay/Engagement         ┌──────▼──────┐
│ BOSS_FIGHT│    (E04, E05)              │  GAME_OVER  │
└──┬────┬──┘                             └─────────────┘
   │    │                                      ▲
 PASS  FAIL×3                                  │
   │    └──────────────────────────────────────┘
   │
   │  old_chapter < 5
   ├──────────────────→ ACTIVE (next chapter)
   │
   │  old_chapter ≥ 5
   └──────────────────→ WON (E11 US-11.2)
```

### State × Epic Coverage

| State | Epics Covering | Key Scenarios |
|-------|---------------|---------------|
| registered → active | E01 | S-1.1.1, S-1.2.1, S-1.3.1 |
| active (gameplay) | E02, E04, E05, E06 | S-2.1.1, S-4.1.1, S-5.1.1, S-6.1.1 |
| active → boss_fight | E03 | S-3.1.1 through S-3.1.5 |
| boss_fight → active | E03, E10 | S-3.3.1, S-10.7.1 |
| boss_fight → game_over | E03, E10 | S-3.4.3, S-10.7.2 |
| boss_fight → won | E03, E11 | S-3.3.4, S-11.2.1 |
| active → game_over (decay) | E04, E10, E11 | S-4.2.3, S-10.1.3, S-11.1.1 |
| game_over (canned response) | E11 | S-11.1.3 |
| won (variant messages) | E11 | S-11.2.2 |
| game_over → active (restart) | E11 | S-11.3.1 |

---

## MCP Tool Coverage

| MCP Tool | Epics Using | Primary Purpose |
|----------|-------------|-----------------|
| Supabase MCP | E01-E13 | DB state verification (users, conversations, score_history) |
| Telegram MCP | E01, E02, E03, E06, E10, E11 | Message sending/receiving, webhook simulation |
| Chrome DevTools MCP | E08, E09, E12 | Portal UI verification, screenshots |
| gcloud CLI | E07, E09, E10 | Cloud Run curl, deployment verification |
| Gmail MCP | E01 | OTP email retrieval |

---

## Key Source Files

| File | Epics | Purpose |
|------|-------|---------|
| `nikita/platforms/telegram/message_handler.py` | E02, E03, E11 | Message routing, boss responses, terminal states |
| `nikita/engine/chapters/boss.py` | E03, E10, E11 | Boss judgment, pass/fail, timeout |
| `nikita/engine/decay/processor.py` | E04, E10 | Decay application, game_over trigger |
| `nikita/engine/decay/calculator.py` | E04, E10 | Grace periods, decay rates |
| `nikita/engine/engagement/state_machine.py` | E05 | 6-state engagement transitions |
| `nikita/pipeline/orchestrator.py` | E10 | 9-stage unified pipeline |
| `nikita/api/routes/tasks.py` | E10 | All background job endpoints |
| `nikita/agents/voice/voice.py` | E07 | Voice initiation, webhooks, scoring |
| `nikita/api/routes/portal.py` | E08, E09 | Portal + admin API endpoints |
| `nikita/api/auth.py` | E08, E09 | JWT auth, admin email check |
| `nikita/engine/constants.py` | E03, E04, E05 | Thresholds, rates, chapter config |

---

## Verification Strategy

### For Agent Consumption

1. **Read epic file**: `Glob("E??-*.md")` → `Read(target_epic.md)`
2. **Execute scenarios by priority**: P0 first, then P1, then P2
3. **Verify via MCP tools**: Each scenario has `# Verify:` annotations with exact queries
4. **Cross-reference gaps**: After epic testing, read E13 for relevant gap scenarios

### Agent Workflow

```
1. Read README.md (this file) — understand scope
2. For each epic in priority order:
   a. Read E{NN}-{name}.md
   b. Execute P0-Critical scenarios first
   c. Log results per scenario (PASS/FAIL/SKIP)
   d. Continue to P1/P2 if time permits
3. Read E13-gap-scenarios.md for adversarial testing
4. Generate test report with pass/fail counts per epic
```

### Priority Execution Order

| Phase | Epics | Focus | Scenarios |
|-------|-------|-------|-----------|
| 1 (Critical Path) | E01, E02, E03, E04 | Registration → Gameplay → Boss → Decay | ~100 |
| 2 (Systems) | E05, E06, E10 | Engagement, Vice, Background Jobs | ~73 |
| 3 (Platforms) | E07, E08, E09, E12 | Voice, Portal, Cross-Platform | ~76 |
| 4 (Edge Cases) | E11, E13 | Terminal States, Gap Analysis | ~64 |

---

## Cross-References

- **Spec 048**: [../spec.md](../spec.md) — E2E Full Lifecycle specification
- **Deep Audit**: [../../docs-to-process/20260214-deep-audit-report.md](../../docs-to-process/20260214-deep-audit-report.md)
- **System Map**: [../../docs-to-process/20260214-system-map.md](../../docs-to-process/20260214-system-map.md)
- **Remediation Specs**: 049 (game mechanics), 050 (portal fixes), 051 (voice polish), 052 (infra cleanup)
