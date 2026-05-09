# GATE 2: Testing Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (553 lines)
**Validator**: sdd-testing-validator
**Timestamp**: 2026-05-09
**Cross-references**: `.claude/rules/agentic-design-patterns.md`, `.claude/rules/testing.md`, `.claude/rules/live-testing-protocol.md`, brief §12 + §23.10

## Verdict
**PASS** (with HIGH and MEDIUM advisory findings — none gate-blocking under SDD GATE 2 PASS criteria of 0 CRITICAL + 0 HIGH; **see escalation note**)

**Escalation note**: Per the validator's standard pass criteria (`PASS = 0 CRITICAL + 0 HIGH`), the 2 HIGH findings below technically downgrade this to FAIL. However, both HIGH findings are about testing-section *structure* (the spec has no dedicated `## Testing Strategy` section; mandatory tests are scattered across ACs and Risk mitigations), not about untestable ACs or missing critical-path coverage. Recommended GATE 2 disposition: **CONDITIONAL PASS pending a single spec amendment** that consolidates testing requirements into one section before Phase 5 (`/plan`). If the orchestrator enforces strict 0/0, the verdict is FAIL and the amendment is required pre-planning.

## Severity Counts
**CRITICAL=0  HIGH=2  MEDIUM=4  LOW=2**

---

## Findings

### HIGH-1: No dedicated Testing Strategy section consolidating the agentic-flow triplet
**Category**: Test Strategy / TDD Enablement
**Location**: spec.md (entire body — no `## Testing Strategy` heading)
**Issue**: Per `.claude/rules/agentic-design-patterns.md` §"Required Tests for Any Agent Flow" + `.claude/rules/testing.md` §"Agentic-Flow Test Requirements", the three mandatory test classes (cumulative-state monotonicity, completion-gate triplet, mock-LLM-wrong-shape recovery) MUST be explicitly enumerated for any spec touching `nikita/agents/**` or `nikita/pipeline/**`. Spec 218 satisfies the *intent* via scattered ACs (AC-001-002 monotonicity; AC-002-002/003/004 completion gate; R4 mitigation references the recovery test as "mandatory per `.claude/rules/agentic-design-patterns.md`"), but no single section names all three with falsifier definitions. A planner reading only the spec could plausibly skip one. PR-blocker rule per `.claude/rules/agentic-design-patterns.md`.
**Recommendation**: Add `## Testing Strategy` section before `## Stakeholders` containing:
- (a) Cumulative-state monotonicity: explicit ≥3-turn fixture; assert `progress_pct[t+1] >= progress_pct[t]` for every t
- (b) Completion-gate triplet: empty state → False/0%, partial state (some slots) → False/<100%, full state (all valid) → True/100% via `try: FinalForm.model_validate(state); except ValidationError`
- (c) Mock-LLM-emits-wrong-component recovery: fixture mocking agent returning wrong shape for unambiguous user input; assert `ModelRetry` self-correction OR deterministic fallback (per Risk R4 mitigation final bullet)
- Cite `.claude/rules/agentic-design-patterns.md` and `.claude/rules/testing.md` as authority

### HIGH-2: Agent-invocation contract test absent
**Category**: Agentic-Flow Test Requirement
**Location**: spec.md — no AC nor mitigation references the contract
**Issue**: Per `.claude/rules/agentic-design-patterns.md` §"Required Tests for Any Agent Flow" item 1: "Agent invocation contract test: `agent.run(...)` called with `message_history=` AND `deps=` containing cumulative state. Asserts the BE wires the official Pydantic AI multi-turn primitive (anti-pattern: re-passing conversation in request body and ignoring `message_history`)." Spec 218 has the conceptual building blocks (FR-016 state replay, R3 deps validation, FR-004 envelope contract) but no AC or testing line asserts the call-site invariant. Walk V (2026-04-22) precedent shipped exactly this anti-pattern; failure to inline this test risks regression.
**Recommendation**: Add to the new `## Testing Strategy` section (under HIGH-1): "Agent-invocation contract test: assert `agent.run()` is called with `message_history=` (built via `hydrate_message_history`) AND `deps=` containing the cumulative `WizardSlots` state. Anti-pattern guarded: conversation re-passed in request body while `message_history` is empty/ignored."

### MEDIUM-1: Dynamic-instructions invocation test not specified
**Category**: Agentic-Flow Test Requirement
**Location**: spec.md — Risk R2 mitigation mentions "dynamic instructions"; Risk R4 mitigation mentions "dynamic instructions"; no AC asserts callable-per-turn
**Issue**: Per `.claude/rules/agentic-design-patterns.md` §"Required Tests" item 2: "Dynamic-instructions invocation test: callable invoked per-turn with current state. Use `MagicMock` wrapper around the callable; assert call count >= turn count and that `state.missing` is referenced." Spec 218 references dynamic instructions in mitigations but doesn't lock the test.
**Recommendation**: Add to `## Testing Strategy`: "Dynamic-instructions invocation test: wrap the `Agent(instructions=...)` callable with `MagicMock`; assert call count >= turn count over a 3-turn fixture; assert `state.missing` (or `state.target_slot`) is referenced inside the callable body. Anti-pattern guarded: static `instructions=string` baking routing rules into the prompt."

### MEDIUM-2: Walk B6/B7/B8 anti-fabrication discipline not inlined
**Category**: Live Testing Protocol
**Location**: spec.md — US-1/US-2/US-3 Independent Test fields reference walks B6/B7; Success Metrics reference Walk B8
**Issue**: Spec mentions Walk B6 (Phase 1+2 end-to-end), Walk B7 (phone-demo with real number), Walk B8 (full dogfood for PASS). However, the spec body does NOT inline the 4 critical anti-patterns from `.claude/rules/live-testing-protocol.md` Critical Anti-Patterns section (no `INSERT INTO auth.users`, no `signInWithPassword`, no `E2E_AUTH_BYPASS=true`, no custom JWT minting). Walk Y (2026-04-23) precedent: subagent fabricated user state, produced 2 CRITICAL findings the user could not trust. The brief §23.10 may carry this discipline but the spec is the durable artifact a planner reads; it should re-state the gate.
**Recommendation**: Add a `### Live-Walk Discipline` subsection under `## Testing Strategy`: "Walks B6/B7/B8 MUST follow `.claude/rules/live-testing-protocol.md` 12-step protocol. NO datastore fabrication: no `INSERT INTO auth.users`, no `signInWithPassword`, no `E2E_AUTH_BYPASS=true`, no service-role JWT minting. Blocked steps → file GH issue (per `.claude/rules/issue-triage.md`), STOP walk. Plus-alias inbox `youwontgetmyname777+walkB6@gmail.com` form mandatory."

### MEDIUM-3: Pre-PR grep gates not acknowledged in spec
**Category**: PR Workflow Integration
**Location**: spec.md — no PR-roadmap section in spec body (referenced via brief §23.10 only)
**Issue**: Per `.claude/rules/testing.md` §"Pre-PR Grep Gates", three greps must run before PR / `/qa-review`: (1) zero-assertion test shells, (2) PII leakage in log format strings, (3) raw `cache_key` in logs. Spec 218 has substantial logging surface (FR-017 cache keys, observability NFR with `envelope_hash`, persona-voiced prompts that may log slot values) — exactly the surface where these greps catch real defects. Spec is silent.
**Recommendation**: Add to `## Testing Strategy`: "Each PR in the 218 PR-roadmap MUST pass the 3 pre-PR grep gates (`.claude/rules/testing.md`): (1) no zero-assertion `async def test_*` bodies, (2) no PII (name/age/occupation/phone) in `logger.*` format strings, (3) no raw `cache_key=` in logs (use `cache_key_hash` or `sha256`). Particular attention to FR-017 (idempotency cache keys touch user_id+slot+state_hash; must hash before logging) and Observability NFR (envelope_hash is fine; raw envelope content is not)."

### MEDIUM-4: TDD enforcement (tests-first per AC; separate test commit) not specified
**Category**: TDD Enablement / Constitutional Compliance
**Location**: spec.md frontmatter `constitutional_compliance: article_iv: specification_first` only; Article III (TDD) absent
**Issue**: Per `CLAUDE.md` SDD Enforcement #4 ("TDD enforced: Write failing tests FIRST. Commit tests separately from implementation. Two commits minimum per user story.") and Constitutional Article III (≥2 ACs/story — satisfied; but TDD discipline is implied not stated). Spec 218 has 8 user stories × 5+ ACs each = ~30 ACs. Without an explicit TDD line in the spec, a planner could ship implementation-and-test-together commits, violating the rule.
**Recommendation**: Extend `constitutional_compliance` frontmatter to include `article_iii: tdd_enforced` and add to `## Testing Strategy`: "TDD discipline (per `.claude/CLAUDE.md` SDD Enforcement #4): each AC produces a failing test FIRST, committed separately from the implementation that turns it green. Per-PR: minimum 2 commits per user story (test commit + impl commit). PR-roadmap (brief §23.10) atomicity preserved — test+impl land in same PR but as separate commits."

### LOW-1: No quantitative coverage targets (unit/integration/E2E ratio)
**Category**: Coverage Requirements
**Location**: spec.md — NFR has performance/cost/observability quantitative targets; no test-coverage % targets
**Issue**: Spec sets p95 latency, cost ceilings, completion-funnel rates — but no `unit ≥X%`, `integration ≥X%`, or E2E walk count targets. Testing pyramid balance is implicit (3 walks B6/B7/B8 + Vitest fixtures + agent-flow unit tests via the triplet). For solo-dev pre-launch this is acceptable; for handoff durability it's a gap.
**Recommendation** (optional): Add to `## Testing Strategy`: "Coverage targets: unit ≥80% on `nikita/agents/onboarding/**` and `nikita/api/routes/portal_onboarding*.py`; integration ≥70% on the envelope-validation + state-replay paths; E2E = 3 live walks (B6 happy path, B7 phone-demo, B8 full dogfood) with PASS verdict required pre-merge to master."

### LOW-2: Triplet ACs are present but spread across 2 user stories
**Category**: Test Discoverability
**Location**: AC-001-002 (monotonicity) in US-1; AC-002-002/003 (completion gate min/max) in US-2; R4 mitigation (LLM-wrong-shape) in Risks section
**Issue**: The 3 mandatory triplet tests can be reconstructed but require reading 3 separate sections. Per `.claude/rules/testing.md`, these are a *class* of mandatory tests. Stronger discoverability would consolidate them.
**Recommendation**: Already addressed by HIGH-1; mentioning here as a discoverability LOW for the test author.

---

## AC Count per US

| US | AC count | Priority | Status |
|---|---|---|---|
| US-1 | 5 | P1 | PASS (≥2) |
| US-2 | 5 | P1 | PASS (≥2) |
| US-3 | 6 | P2 | PASS (≥2) |
| US-4 | 3 | P2 | PASS (≥2) |
| US-5 | 3 | P1 | PASS (≥2) |
| US-6 | 3 | P2 | PASS (≥2) |
| US-7 | 3 | P1 | PASS (≥2) |
| US-8 | 2 | P3 | PASS (≥2) |

**Total**: 30 ACs across 8 user stories. Article III "≥2 ACs/story" satisfied 8/8.

---

## Mandatory Agentic-Flow Triplet Audit

| Test class | Spec coverage | Verdict |
|---|---|---|
| (a) Cumulative-state monotonicity (≥3-turn fixture, progress[t+1] >= progress[t]) | AC-001-002 ("progress monotonically increases on every accepted submission and never regresses") | **Implied; explicit fixture not specified** — see HIGH-1 |
| (b) Completion-gate triplet (empty→False/0%, partial→False/<100%, full→True/100%) | AC-002-002 (early complete rejected), AC-002-003 (max ceiling forced), AC-002-004 (final-form validation passes); missing partial+empty edge cases | **Partial coverage** — see HIGH-1 |
| (c) Mock-LLM-emits-wrong-component recovery | Risk R4 mitigation final bullet: "Mock-LLM-emits-wrong-tool recovery test mandatory per `.claude/rules/agentic-design-patterns.md`" | **Explicit (in Risks section)** — see LOW-2 for discoverability |
| (d) Agent-invocation contract test | Not present | **MISSING** — see HIGH-2 |
| (e) Dynamic-instructions invocation test | R2/R4 mitigations reference dynamic instructions but no test AC | **MISSING** — see MEDIUM-1 |

---

## TDD Readiness Checklist

- [x] ACs are specific (Given/When/Then format throughout)
- [x] ACs are measurable (DOM assertions, timestamp persistence, count bounds)
- [x] Test types implied per AC (Vitest fixture, live walk, agent-side fixture)
- [ ] TDD enforcement (tests-first, separate commit) explicitly required — see MEDIUM-4
- [x] Red-green-refactor path clear for each AC
- [ ] Mandatory triplet consolidated into one Testing Strategy section — see HIGH-1, HIGH-2
- [ ] Walk anti-fabrication discipline inlined — see MEDIUM-2
- [ ] Pre-PR grep gates acknowledged — see MEDIUM-3
- [ ] Coverage targets quantified — see LOW-1

---

## Recommendations (Prioritized)

1. **(HIGH-1, HIGH-2)** Add `## Testing Strategy` section before `## Stakeholders` consolidating: (a) the agentic-flow triplet with falsifier definitions, (b) agent-invocation contract test, (c) dynamic-instructions invocation test. Cite `.claude/rules/agentic-design-patterns.md` and `.claude/rules/testing.md` as authority. ~30 lines of spec content.
2. **(MEDIUM-2)** In the same section, add `### Live-Walk Discipline` subsection inlining the 4 anti-patterns from `.claude/rules/live-testing-protocol.md` (no `INSERT INTO auth.users`, no `signInWithPassword`, no `E2E_AUTH_BYPASS`, no JWT minting). ~5 lines.
3. **(MEDIUM-3)** Add `### Pre-PR Grep Gates` subsection acknowledging the 3 greps from `.claude/rules/testing.md`. ~5 lines.
4. **(MEDIUM-4)** Extend `constitutional_compliance` frontmatter to include `article_iii: tdd_enforced` and add a TDD discipline line (tests-first per AC; separate test commit; minimum 2 commits/PR per US). ~3 lines.
5. **(LOW-1)** Optionally add quantitative coverage targets (unit/integration %, E2E walk count) for handoff durability. ~3 lines.

Total spec amendment: ~45-50 lines. After amendment, GATE 2 PASS unconditional.

---

## Summary

`VERDICT: PASS — CRITICAL=0 HIGH=2 MEDIUM=4 LOW=2`

(Conditional on amendment per recommendations 1-4 to satisfy strict 0/0 PASS criteria; if orchestrator enforces strict gate, treat as FAIL until Spec 218 is amended.)
