# Plan — 048: Full-Lifecycle E2E Test

**Spec**: [spec.md](spec.md) | **Tasks**: [tasks.md](tasks.md)

---

## Execution Strategy

### Team Structure (5 agents)

| Agent | Type | Role | Tools |
|-------|------|------|-------|
| orchestrator | general-purpose | Sequence control, state tracking | Task tools, SendMessage |
| telegram-agent | general-purpose | Telegram + Gmail interactions | Telegram MCP, Gmail MCP |
| verifier | general-purpose | DB queries, API checks | Supabase MCP, Bash (curl) |
| portal-agent | general-purpose | Portal navigation, screenshots | Chrome DevTools MCP |
| devils-advocate | Explore | Challenge results, find gaps | Read, Grep, Glob |

### Phase Execution Order

| Phase | Duration | Tasks | Description |
|-------|----------|-------|-------------|
| 0 | 5 min | T1.1 | Cleanup existing user data |
| 1 | 10 min | T1.2 | Registration via Telegram OTP |
| 2 | 10 min | T1.3 | Text onboarding completion |
| 3 | 15 min | T2.1 | Chapter 1 gameplay + scoring |
| 4 | 10 min | T2.2 | Boss 1 encounter (ch1→ch2) |
| 5-6 | 20 min | T2.3 | Chapter 2 + Boss 2 (ch2→ch3) |
| 7-8 | 20 min | T2.4 | Chapter 3 + Boss 3 (ch3→ch4) |
| 9-10 | 20 min | T2.5 | Chapter 4 + Boss 4 (ch4→ch5) |
| 11-12 | 20 min | T2.6 | Chapter 5 + Final Boss → Victory |
| 13 | 10 min | T3.1-T3.3 | Backend verification + background jobs |
| 14 | 15 min | T4.1-T4.2 | Portal dashboard |
| 15 | 10 min | T5.1-T5.3 | Edge cases |
| 16 | 10 min | T5.2 | Game-over path |
| 17 | 10 min | T6.1-T6.2 | Report + sync |

**Total: ~3.2 hours** (+ 50% buffer = 5 hours max)

### Score Acceleration Strategy

Natural scoring yields +1 to +3 per message. Boss thresholds:
- Ch1→Ch2: 55% (set score to 54.5 via SQL)
- Ch2→Ch3: 60% (set to 59.5)
- Ch3→Ch4: 65% (set to 64.5)
- Ch4→Ch5: 70% (set to 69.5)
- Ch5 Victory: 75% (set to 74.5)

Send 3-5 natural messages per chapter, verify real scoring, then SQL accelerate.

### Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| OTP email delayed | Poll 3s intervals for 120s. Fallback: check auth.users |
| Neo4j cold start | Wait 180s max. pgVector primary (Spec 042) |
| Pipeline stuck | Manual trigger via curl. Check status + processing_attempts |
| Boss judgment fails | Retry with different response (max 2). Fallback: SQL reset |
| Portal auth fails | Use Supabase for auth token, test API directly |

### Orchestration Pattern

```
orchestrator → telegram-agent: "Execute Phase N action"
telegram-agent → orchestrator: "Response: {content}"
orchestrator → verifier: "Run verification checkpoint"
verifier → orchestrator: "VC-N: PASS/FAIL (details)"
orchestrator → devils-advocate: "Review VC-N results"
devils-advocate → orchestrator: "Concerns: {list}"
orchestrator → [resolve concerns or proceed]
```
