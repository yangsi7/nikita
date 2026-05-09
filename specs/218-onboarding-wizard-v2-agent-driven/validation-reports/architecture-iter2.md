# GATE 2 ITER 2: Architecture Re-Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (1008 lines, post-iter-1 amendment from 553)
**Validator**: sdd-architecture-validator
**Timestamp**: 2026-05-09
**Iter-1 verdict**: PASS (0 CRITICAL, 0 HIGH, 2 MEDIUM, 3 LOW)
**Brief**: `~/.claude/plans/immutable-wondering-gray.md`

## Verdict

**PASS**

## Severity Counts

CRITICAL=0  HIGH=0  MEDIUM=2 (carried forward, both partially mitigated)  LOW=3 (carried forward, LOW-2 + LOW-3 fully resolved)

---

## Iter-2 Amendment Scope

Three new sections added between iter-1 PASS and iter-2:

1. **Data Entities** (lines 585-682) — names persistence surfaces: `onboarding_profile` (JSONB extension), `phone_demo_calls` (NEW table with full RLS), `cohort_chips_table` (static file, NOT a DB entity).
2. **HTTP Route Contract** (lines 685-866) — concrete envelope discriminated union (8 shapes), 3 routes (POST /answer, GET /state, POST /phone-demo/consent), Realtime channel subscription, error envelope wire shape.
3. **Testing Strategy** (lines 870-935) — agentic-flow test triplet, agent-invocation contract tests, prompt-injection resistance test, live-walk discipline (B6/B7/B8), pre-PR grep gates, coverage targets.

Each is verified below against the iter-1 PASS criteria.

---

## Re-Check Against Iter-1 PASS Criteria

### 1. No new CRITICAL/HIGH introduced — verified

| Check | Iter-2 status | Notes |
|---|---|---|
| Solo-dev simplicity (no new abstraction layer) | PASS | Data Entities adds 1 new table (`phone_demo_calls`); reuses existing `onboarding_profile` JSONB column. No ORM-magic, no new repository tier, no new service abstraction. HTTP Route Contract uses 3 concrete routes (no abstract handler hierarchy). |
| Atomic bulldoze (FR-018) | PASS | Iter-2 amendment did NOT introduce v1+v2 split. Line 631 explicitly: "v1 keys (if any) bulldozed atomically per FR-018". Realtime subscription replaces polling outright (line 698: "NO polling endpoint exists"). |
| Type safety (envelope union schema concrete) | PASS | Lines 700-775 enumerate all 8 shapes with concrete fields. NO semantic-intent layer reintroduced. Discriminator field `component` is concrete string literal. |
| Tool consolidation (still 8 shapes, no 9th) | PASS | Lines 705 ("Shape 1: text_short") through 770 ("Shape 8: complete") = exactly 8 shapes. Brief §20-I1 deletion of `reaction_only` 9th shape is preserved. |
| 6 agentic hard rules preserved | PASS | Testing Strategy section (lines 874-892) explicitly mandates: cumulative-state monotonicity (Rule 1), completion-gate triplet (Rule 2), mock-LLM-emits-wrong-component recovery (Rule 5), agent-invocation contract test with `message_history=` AND `deps=` (Rule 6 — promotes LOW-3 from advisory to PR-blocker test), dynamic-instructions invocation test (Rule 3 anti-fan-out via dynamic prompts). |

### 2. Spot-check FR-019 (route auth) + FR-020 (named shells) — clean integration

- **FR-019 (JWT auth)**: Route Inventory table (line 691-696) anchors JWT requirement on all 3 HTTP routes + Realtime channel. Concrete and consistent with brief §5 (no contradiction).
- **FR-020 (named shells)**: Component shapes have explicit names (`text_short`, `text_long`, `single_select`, `chip_multi`, `slider`, `calendar`, `phone`, `complete`). Discriminated union matches brief §23.4 (concrete component names BE↔FE — no semantic-intent abstraction).
- **No contradictions** with brief §5 module structure (`nikita/agents/onboarding/v2/` + `portal/src/app/onboarding/v2/`).

### 3. Spot-check Data Entities — single-source-of-truth + no scope creep

- **`onboarding_profile` JSONB extension**: lines 589-631. PRESERVES single source of truth — uses existing `users` row, existing per-user RLS policy. Replay rule (line 629) explicitly: "On mismatch, conversation log wins (audit-trail authority per FR-016)". Walk V cumulative-state pattern intact.
- **`phone_demo_calls` is the ONLY new table**: lines 633-671. Schema is justified by FR-009/FR-010/FR-011 (consent + lifecycle + lifetime cap via UNIQUE on user_id). RLS is COMPLETE per `.claude/rules/testing.md` DB Migration Checklist:
  - `ENABLE ROW LEVEL SECURITY` (line 657) ✓
  - SELECT policy with subquery form `user_id = (SELECT auth.uid())` (line 660) ✓
  - INSERT policy with `WITH CHECK` (line 663) ✓
  - UPDATE/DELETE explicitly NOT user-policied — comment on line 665-666 documents service-role-only path for webhook updates ✓
- **`cohort_chips_table` is STATIC FILE, NOT a DB entity** (lines 673-682) — preserves brief §20-REUSE LOCK on `nikita/agents/onboarding/cohort_chips.py`. Zero scope creep into DB-backed table.

---

## Iter-1 MEDIUM/LOW Findings — Status Update

| Finding | Iter-1 severity | Iter-2 status |
|---|---|---|
| MEDIUM-1: WizardSlots cumulative-state model not explicitly named | MEDIUM | PARTIALLY RESOLVED — line 602 names "WizardSlots dict" in JSONB shape; Testing Strategy line 878 references state model. Still NOT named in FR-016 body. Plan.md carry-forward unchanged. |
| MEDIUM-2: Bulldoze list not enumerated in spec body | MEDIUM | UNCHANGED — FR-018 atomicity preserved; iter-2 did not inline §20-B2 table. Plan.md carry-forward unchanged. |
| LOW-1: v2/ directory convention implied | LOW | UNCHANGED — Testing Strategy line 876 references `nikita/agents/onboarding/v2/`; FE side `portal/src/app/onboarding/v2/` referenced line 932. Plan.md carry-forward retained. |
| LOW-2: Type-mirror BE→FE same-PR not explicit | LOW | RESOLVED — HTTP Route Contract section codifies wire shape (lines 700-775) which IS the contract. Brief §23.10 PR-218-3 vertical-slice atomicity is the operational counterpart. |
| LOW-3: message_history primitive not surfaced in FR | LOW | RESOLVED — Testing Strategy line 888 PROMOTES this to mandatory test #4: "Agent-invocation contract test: assert `agent.run(...)` is called with `message_history=` AND `deps=` containing cumulative state. Walk V (2026-04-22) precedent". Now PR-blocker, not advisory. |

---

## New Defects Introduced by Iter-2 Amendment

**None.** Each new section reinforces existing FR/AC anchors and provides concrete contract surface for plan.md to inherit. No architectural defects.

Specifically verified absent:

- ❌ No new abstraction layer (Article VI ≤2 layers preserved).
- ❌ No semantic-intent envelope layer (brief §23.4 rejection holds).
- ❌ No 9th component shape (brief §20-I1 deletion holds).
- ❌ No polling endpoint for phone-demo (line 698 forbids it; Realtime subscription is canonical).
- ❌ No new DB tables beyond `phone_demo_calls` (cohort_chips stays static; onboarding_profile stays JSONB extension).
- ❌ No RLS gaps (every new entity has full RLS posture per `.claude/rules/testing.md`).
- ❌ No back-compat ceremony (no v1+v2 co-existence; FR-018 atomic bulldoze preserved).

---

## Architecture Hard-Rule Coverage (Iter-2 strengthened)

| Rule | Iter-1 | Iter-2 | Change |
|---|---|---|---|
| 1. Cumulative server-side state | PASS | PASS | Lines 589-631 codify JSONB shape; Testing Strategy line 878 mandates monotonicity test. |
| 2. Pydantic completion gates | PASS | PASS | Testing Strategy line 880 mandates triplet test (empty/partial/full). |
| 3. Tool consolidation | PASS | PASS | Lines 700-775 enumerate exactly 8 shapes with concrete fields. |
| 4. Monotonic progress | PASS | PASS | Testing Strategy line 878 codifies falsifier ("per-turn snapshot read instead of cumulative state"). |
| 5. Validation layering | PASS | PASS | HTTP Route Contract line 798 (`422 Unprocessable Entity`) + line 799 (`recovery_envelope` deterministic fallback) operationalize the 3 layers. |
| 6. message_history primitive | PASS-with-LOW-3 | **PASS (LOW-3 resolved)** | Testing Strategy line 888 promotes this to mandatory PR-blocker test. |

---

## Verdict (Final)

**PASS** — 0 CRITICAL, 0 HIGH. Iter-2 amendment introduced NO new architectural defects. Two of three iter-1 LOWs are now fully resolved (LOW-2, LOW-3); LOW-1 remains as plan.md carry-forward. Both iter-1 MEDIUMs remain as plan.md carry-forwards (unchanged from iter-1).

Spec is architecturally sound to proceed to /plan (Phase 5).

### Plan.md Carry-Forwards (unchanged from iter-1, plus iter-2 affirmations)

1. Name `WizardSlots(BaseModel)` cumulative-state primitive + `model_copy(update=…)` merge (MEDIUM-1).
2. Inline §20-B2 bulldoze table with owning-PR annotations + reuse-vs-bulldoze split (MEDIUM-2).
3. Cite `nikita/agents/onboarding/v2/` + `portal/src/app/onboarding/v2/` directory layout (LOW-1).
4. Iter-2 affirmations (now spec-mandated, plan.md must implement):
   - 6 mandatory test classes per Testing Strategy section (lines 874-906).
   - Pre-PR grep gates per lines 912-918.
   - Coverage targets per lines 929-934.
   - Live-walk discipline per `.claude/rules/live-testing-protocol.md` (B6/B7/B8).

---

**VERDICT: PASS — CRITICAL=0 HIGH=0 MEDIUM=2 LOW=3 (LOW-2 + LOW-3 fully resolved by iter-2 amendment)**
