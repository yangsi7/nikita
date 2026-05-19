# Specification Audit Report

**Feature**: 216-onboarding-redesign-cinematic
**Date**: 2026-04-30
**Auditor**: fresh-context general-purpose subagent
**Result**: FAIL (4 CRITICAL, 8 HIGH, 5 MEDIUM)

## Executive Summary
- Total Findings: 17
- Critical: 4 | High: 8 | Medium: 5 | Low: 0

## Findings Table

| ID | Category | Severity | Location | Summary | Fix |
|----|----------|----------|----------|---------|-----|
| F-1 | coverage | CRITICAL | tasks.md T-A-1..T-A-4 vs subspec 216-A AC table | A1.11, A1.12, A1.13, A1.14 (4 ACs added in iter-2) have NO mapped task. Concurrent magic-link race (CRIT path), resume mid-wizard empty-jsonb edge, disable_web_page_preview enforcement, wrong-OTP destructive-purge guard are unimplementable without tasks. | Add T-A-5..T-A-8 covering A1.11–A1.14 with explicit AC binding + test references. |
| F-2 | coverage | CRITICAL | tasks.md T-B section vs subspec 216-B AC table | B1.13–B1.22 (10 ACs added in iter-2 to close validator findings) have NO direct task AC binding. T-B-11 mentions "HTTP API contract" but lists no AC IDs. B1.18 (SlotKind StrEnum lint), B1.19 (ConverseDeps schema), B1.20 (prompt-cache breakpoint), B1.21 (JSONB round-trip), B1.22 (rate limit 429) are unmapped. | Bind B1.13–B1.17 to T-B-11; add T-B-13 (B1.18 lint test), T-B-14 (B1.19 schema), T-B-15 (B1.20 cache breakpoint), T-B-16 (B1.21 round-trip test), T-B-17 (B1.22 rate limit). |
| F-3 | coverage | CRITICAL | tasks.md T-C section vs subspec 216-C AC table | C1.12 (a11y ARIA contracts — HIGH), C1.13 (Server Component cookie auth guard — HIGH), C1.14 (pending/error UI states — MED), C1.16 (AnimatePresence key=turn_id — MED), C1.17 (ProgressRail reduced-motion — MED) have NO mapped task. C1.12 is an extensive HIGH-severity AC that closes frontend-validator HIGH-1. | Add T-C-12 (a11y per C1.12), T-C-13 (Server Component auth guard per C1.13), T-C-14 (pending/error UI per C1.14), T-C-15 (AnimatePresence key per C1.16), T-C-16 (reduced-motion per C1.17). |
| F-4 | coverage | CRITICAL | tasks.md T-D section vs subspec 216-D AC table | D1.10 (top-level columns vs JSONB embedding — closes data-layer-validator MED-1), D1.11 (CHECK IF NOT EXISTS DO-block pattern — closes MED-2), D1.12 (archetype_candidates JSONB — closes testing-validator LOW-2) have NO mapped task. Migration cannot be authored correctly without these. Note: subspec D AC ordering is irregular (D1.9 listed AFTER D1.12 in subspec spec.md). | Add T-D-9 (D1.10 column placement), T-D-10 (D1.11 idempotent CHECK pattern), T-D-11 (D1.12 archetype_candidates column). Reorder subspec ACs sequentially. |
| F-5 | inconsistency | HIGH | tasks.md T-B-1 AC-1 vs AC-2 + spec.md L360-374 + subspec B B1.1 | T-B-1 AC-1 says "12 optional fields" then enumerates 13 names (display_name, age, city, occupation, darkness_level, primary_hobbies, saturday_morning, geek_out_on, together_we_could, same_weird_if, phone, voice_tone_pref, backstory_pick). AC-2 says "13 members" in SlotKind StrEnum. Spec.md FR-02 says "12 fixed roots" and combines `phone + voice_tone_pref` as one screen-row but spec.md SlotKind enum L360-374 lists 13 distinct members. Subspec C C1.18 affirms "Slot count remains 12 (B1.1 unchanged)". Reality: 13 SlotKind enum members → 13 WizardSlots fields, but the conceptual "12 roots" framing collides with the 13-member enum. | Reconcile: either (a) update spec.md FR-02 to say "13 slot kinds across 12 fixed visual roots" matching SlotKind enum, OR (b) collapse `voice_tone_pref` and `phone` into a single SlotKind member. Update T-B-1 AC-1 to "13 optional fields" matching AC-2 and SlotKind enum. |
| F-6 | inconsistency | HIGH | tasks.md vs plan.md §5 | Plan.md §5 says "T-B1..T-B14" and "T-C1..T-C16" but tasks.md only has T-B-1..T-B-12 and T-C-1..T-C-11. Plan §5 also says "T-D1..T-D8" but tasks.md has T-D-1..T-D-8 (matches). Plan §5 says "T-E1..T-E7" matches; "T-F1..T-F12" but tasks.md has T-F-1..T-F-9. Total task count summary in tasks.md L573 says "51 tasks" but plan §5 implies ~58. | Either (a) add the missing tasks per F-1..F-4 above, which closes the gap, OR (b) reconcile plan §5 task ID ranges with actual tasks.md. Update task count summary. |
| F-7 | inconsistency | HIGH | tasks.md T-A-3 AC-3 vs subspec A A1.11 | A1.11 (concurrent click race, HIGH) explicitly requires `asyncio.gather` integration test asserting exactly-one-200 + exactly-one-400 with NO partial DB state. T-A-3 AC-3 mentions "302 to /dashboard if session live" but NEITHER T-A-3 nor any T-A task tests the concurrent race. F-1 already flags missing tasks, but A1.11 in particular is a CRIT-impact race and the test gap is itself a HIGH issue. | Add a dedicated task with `asyncio.gather` race test or explicitly bind A1.11 to T-A-3 with AC-N: "concurrent /auth/confirm with same token_hash → exactly one 200, one 400, no partial DB state". |
| F-8 | inconsistency | HIGH | tasks.md T-F-1 + plan.md §7.1 vs `.claude/rules/testing.md` | Three mandatory test classes are bound to T-F-1 (in 216-F, depends on all A-E merged). Per `.claude/rules/testing.md`, these are MANDATORY for any agent-flow PR — meaning 216-B itself is a PR-blocker without these tests. T-F-1 placement in 216-F means 216-B can merge without the mandatory test classes existing. | Move T-F-1 (or equivalent) into 216-B as a precondition for 216-B merge. Plan.md §3 ship gate already says "B1.1-B1.12 + 3 mandatory test classes" — tasks.md must reflect this by binding the 3 test files to a T-B task, not deferring to T-F-1. |
| F-9 | implementation-readiness | HIGH | plan.md §3 ship gate for 216-C ("C1.1-C1.20") + LOC estimate ~400 + pr-workflow.md 400-line cap | Plan §3 explicitly notes "216-C is borderline; if exceeded, split frontend into 216-C1 components + 216-C2 screens". 216-C scope: 15 base screens, 6 control primitives, HobbyChips with 100 chips × 10 categories, BackstoryArchetypeCards, CombinedDualTextarea, MidpointNudge, ProgressRail, NikitaReaction/WhyWeAsk, a11y per C1.12 (10+ sub-bullets), Server Component auth guard, pending/error UI, resume hydration, auto-redirect. ~400 LOC is implausibly low for this surface; realistic estimate is 800-1500 LOC. PR will exceed 400-LOC cap. | Pre-emptively split 216-C into 216-C1 (shell + chrome + auth guard + ProgressRail + animations) and 216-C2 (HobbyChips + BackstoryCards + CombinedDualTextarea + MidpointNudge + per-control primitives). Update plan.md §3 dependency graph + tasks.md T-C splits. |
| F-10 | implementation-readiness | HIGH | plan.md §5 task ID ranges vs tasks.md actual count | Plan §5 task index promises ranges (T-B1..T-B14, T-C1..T-C16, T-F1..T-F12) inconsistent with actual tasks.md content. Implementation cannot proceed against an unstable task index — implementor agent receives "T-C-12" prompt that doesn't exist. | Reconcile per F-6 fix; verify range labels match exact tasks present. |
| F-11 | inconsistency | HIGH | spec.md FR-02 ordering vs spec.md SlotKind L360-374 vs subspec C C1.18 | FR-02 lists order: ...phone+voice_tone_pref → backstory_pick. SlotKind enum order: ...PHONE → VOICE_TONE_PREF → BACKSTORY_PICK. Subspec C C1.18 says "welcome + 11 visual slot screens + backstory pick + phone + completion" — placing backstory BEFORE phone, contradicting FR-02 narrative ("after wizard turn 11 (phone), the system runs ... 3 archetype label picks"). FR-09 says backstory follows phone; C1.18 visually places backstory before phone. | Pick one ordering: spec.md FR-09 (backstory after phone, climax) and align C1.18 visual order to match, OR update FR-09 if backstory must precede phone for cinematic reasons. |
| F-12 | constitution | MEDIUM | tasks.md T-B-3 (progress_pct) + plan.md §7.1 + Rule #4 | Plan §7.1 says cumulative-state monotonicity test is in T-F-1. T-B-3 acceptance includes "Cumulative-state monotonicity test green (12-turn fixture)". This is a duplicate / split: T-B-3 expects the test to exist for 216-B merge, but T-F-1 places its authoring in 216-F. Without resolution, 216-B merges with T-B-3 AC-2 unmet. | Move test authoring to a T-B task; T-F-1 becomes a "verify all 3 classes green in CI" task. |
| F-13 | inconsistency | MEDIUM | plan.md §5 "Total: ~58 tasks" vs tasks.md L584 "Total: 51 tasks" | Discrepancy between plan and tasks. | Reconcile after F-1..F-4 task additions. |
| F-14 | duplication | MEDIUM | spec.md FR-12 vs subspec E E1.7 vs subspec E E1.3 | FR-12 says hard cost ceiling $0.50/flow. E1.7 says <$0.50/flow hard ceiling. E1.3 says fetch-only sub-budget hard ceiling $0.15/flow. These are non-contradictory (E1.3 is a sub-budget) but the relationship is implicit. Risk of misread during implementation. | Add a single sentence to FR-12 or E1.7: "fetch_cost_cumulative ≤$0.15 is a sub-budget within the $0.50 total". |
| F-15 | inconsistency | MEDIUM | tasks.md T-D-1 AC-1 + spec.md NR-03 vs subspec D D1.10 | Tasks T-D-1 AC-1 says columns added at "users.onboarding_profile.{big5_vector, backstory_seed, brand_resonance_signal}" implying JSONB-embedded. Spec.md NR-03 says "JSONB embedding". Subspec D D1.10 explicitly REVERSES this: "added as top-level columns on public.users (alongside onboarding_profile JSONB)". The data-layer-validator MED-1 fix per validation-findings.md set the canonical position to top-level columns. Tasks.md T-D-1 wasn't updated and contradicts D1.10. | Update T-D-1 AC-1 to "top-level columns on public.users". Update spec.md NR-03 to match D1.10. Update T-D-6 to extend `User` (not `UserProfile`). |
| F-16 | ambiguity | MEDIUM | spec.md §2 Open Questions L592-598 (5 questions) | Open Questions are explicitly flagged as accepted per audit instructions, so non-blocking. Documented for traceability only. | None — accepted. |
| F-17 | implementation-readiness | MEDIUM | plan.md §3 dependency graph: 216-D depends on 216-A; 216-B depends on 216-A; B parallel D | DAG is acyclic. ✓ Verified: A → (B ∥ D) → (C ∥ E) → F. No circular dependencies. | None. |

## Coverage Analysis

- **FRs covered**: 12/12 (FR-01..FR-12 all map to ≥1 subspec AC, traced via spec.md Appendix B)
- **NRs covered**: 8/8 (NR-01..NR-08 all map; NR-01 → 216-B, NR-02 → 216-B B1.20 + 216-E E1.8, NR-03 → 216-D, NR-04 → 216-C C1.11, NR-05 → 216-D D1.9, NR-06 → 216-B B1.9, NR-07 → 216-A A1.12 + 216-C C1.15, NR-08 → 216-C C1.4/C1.17)
- **Subspec ACs covered by tasks**:
  - 216-A: 10/14 (A1.1–A1.10 covered; A1.11, A1.12, A1.13, A1.14 ORPHAN — see F-1)
  - 216-B: 12/22 (B1.1–B1.12 covered; B1.13–B1.22 ORPHAN — see F-2; T-B-11 mentions HTTP contract but lacks AC IDs)
  - 216-C: 14/20 (C1.1, C1.2, C1.3, C1.4, C1.6, C1.7, C1.8, C1.9, C1.10, C1.11, C1.15, C1.18, C1.19, C1.20 covered; C1.5, C1.12, C1.13, C1.14, C1.16, C1.17 ORPHAN — see F-3)
  - 216-D: 8/12 (D1.1–D1.9 covered; D1.10, D1.11, D1.12 ORPHAN — see F-4)
  - 216-E: 8/12 (E1.1–E1.8 covered; E1.9 partly covered by T-E-7; E1.10 covered by T-E-7 AC-2; E1.11, E1.12 ORPHAN)
  - 216-F: 9/9 (F1.1–F1.9 covered)
  - **Total**: 61/89 ACs covered (69%)
- **Orphan tasks** (tasks without explicit AC ref): 0 found — every task has subspec AC binding (though some are vague: T-A-4 "code hygiene", T-D-6 "D1.x", T-F-9 "F1.x")

## Constitution Compliance

- **Rule #1 (cumulative server-side state)**: PASS. Spec.md FR-03 + plan.md §2 + subspec B B1.1 mandate `WizardSlots(BaseModel)` cumulative + `model_copy(update={...})`. T-B-1 binds.
- **Rule #2 (Pydantic completion gate)**: PASS. FR-03 + B1.2 mandate `FinalForm.model_validate(state.slots_dict)`; spec L67-74 explicitly forbids boolean literal. T-B-2 binds + grep verification in AC-3.
- **Rule #3 (tool consolidation)**: PASS. FR-04 single `Agent(output_type=[TurnOutput, TurnFailure])` discriminated union. NR-01 explicitly forbids "7 narrow extract_* tools (Walk V incident)". T-B-5 binds.
- **Rule #4 (monotonic progress)**: PASS structurally. B1.12 + spec L460-466 require `@computed_field @property`. T-B-3 binds. CAVEAT: F-12 — test placement split between T-B-3 and T-F-1 risks 216-B merging without monotonicity test.
- **Rule #5 (validation layering)**: PASS. B1.5 covers `@output_validator` + `ModelRetry` (mirror-echo, length, cluster confidence). E1.6 covers per-tool 3s timeout fallback. Tasks T-B-6 + T-E-5 bind.
- **Rule #6 (message_history)**: PASS. B1.10 mandates `agent.run(..., message_history=hydrate_message_history(state.messages))`. NR-01 explicitly approves. T-B-9 binds + grep verifies request body does NOT re-pass conversation context.
- **3 mandatory test classes** (`.claude/rules/testing.md` "Agentic-Flow Test Requirements"): STRUCTURALLY PASS (T-F-1 lists all 3) BUT see F-8 + F-12: tests must exist before 216-B merge, not deferred to 216-F.

## Implementation Readiness

- **All PRs within 400-LOC cap**: NO. 216-C estimated ~400 LOC for 15 screens + 6 controls + a11y (C1.12 alone is ~150 LOC of ARIA wiring) + auth guard + animations + resume hydration + auto-redirect. Realistic estimate 800-1500 LOC. See F-9. Plan.md §3 acknowledges borderline + suggests pre-emptive split.
- **Dependency graph acyclic**: YES. A → (B ∥ D) → (C ∥ E) → F is a DAG.
- **Ship gates binary/falsifiable**: PARTIAL. 216-A "A1.1-A1.10 + golden test green" is binary but EXCLUDES A1.11–A1.14. 216-B "B1.1-B1.12 + 3 mandatory test classes" excludes B1.13–B1.22. 216-C "C1.1-C1.20" includes everything but tasks don't cover C1.12, C1.13, C1.14, C1.16, C1.17 (F-3) so the gate is unverifiable. 216-D ship gate "D1.1-D1.9 + RLS verified" excludes D1.10, D1.11, D1.12. 216-E "E1.1-E1.8 + cost guard test green" excludes E1.9–E1.12.
- **Reuse-map line ranges accurate**: PARTIAL. Plan §4 cites `state.py:88-328` (extend), `conversation_agent.py:127-197` (rewrite), `conversation_prompts.py:33-115,128` (replace), `question_registry.py:42-79`, `regex_fallback.py:47` (delete), `telegram.py:635-666` (reroute), `commands.py:343-348` (refactor), `portal_onboarding.py:799-1231` (delete). These ranges were "verified at GATE 2" per plan §4 header but not re-verified in this audit (read-only scope; out of audit scope per "fresh-context" mandate to trust GATE 2 verdict).

## Verdict

**FAIL** — 4 CRITICAL findings (F-1, F-2, F-3, F-4) on coverage gaps: 28 of 89 subspec ACs (31%) have no mapped task. /implement cannot proceed without binding tasks to A1.11–A1.14, B1.13–B1.22, C1.12-C1.14/C1.16-C1.17, D1.10–D1.12, and E1.11–E1.12. Additional HIGH issues (F-5..F-11) on inconsistency between spec/plan/tasks (slot count 12 vs 13, plan §5 task ID ranges vs actual, ordering of phone-before-backstory, 216-C size cap, 3 mandatory test placement).

Fix CRITICAL findings then re-run /audit. Recommend addressing in this order:
1. F-15 + F-5 (single-source-of-truth: column placement + slot count)
2. F-1..F-4 (add ~28 tasks for orphan ACs)
3. F-9 (split 216-C pre-emptively into C1+C2)
4. F-8 + F-12 (move 3 mandatory test classes into 216-B as ship-gate)
5. F-6 + F-10 + F-13 (reconcile plan §5 ranges with tasks.md)
6. F-7 (concurrent click race test for A1.11)
7. F-11 (resolve phone vs backstory ordering)
8. F-14 (clarify $0.15 fetch sub-budget vs $0.50 total)

---

## Iter-2 Re-Audit (2026-04-30)

**Result**: PASS
**Auditor**: fresh-context general-purpose subagent (iter-2)

### Verification of iter-1 findings

| iter-1 ID | Status | Evidence |
|-----------|--------|----------|
| F-1 CRIT (A1.11–A1.14 orphan) | FIXED | tasks.md:61 T-A-4 (A1.11 race), :71 T-A-5 (A1.12 resume), :81 T-A-6 (A1.14 wrong-OTP purge), :90 T-A-7, :100 T-A-8 added; A1.13 ACK via T-A-3. |
| F-2 CRIT (B1.13–B1.22 orphan) | FIXED | tasks.md:237 T-B-13 (B1.13/14/15), :249 T-B-14, :258 T-B-15 (B1.16), :268 T-B-16 (B1.22), :278 T-B-17 + B1.18→T-B-1 AC-3, B1.19→T-B-5, B1.20→T-B-9, B1.21→T-B-11. |
| F-3 CRIT (C1.5/C1.12-14/16-17 orphan) | FIXED | 216-C split into C1+C2 (plan.md:100-101); T-C1-2 (C1.13 auth guard, tasks.md:412), T-C1-3 (C1.17 reduced-motion :422), T-C1-6 (C1.14 pending/error :454), T-C1-8 (C1.16 AnimatePresence key :474), T-C1-10 (C1.5 responsive :492), T-C1-12 (C1.12 a11y :511) all present. |
| F-4 CRIT (D1.10–D1.12 orphan) | FIXED | tasks.md:303 T-D-1 ACs cover D1.10 (top-level columns) + D1.11 (idempotent CHECK DO-block); :313 T-D-2 covers D1.12 (archetype_candidates JSONB). |
| F-5 HIGH (12 vs 13 SlotKind) | FIXED | spec.md:56 FR-02 reconciled: "13 SlotKind members across 12 visual roots"; L60 explicitly states "13 SlotKind enum members" is BE SoT. tasks.md:119 T-B-1 AC-1 reads "13 optional fields". |
| F-6/F-10/F-13 HIGH (plan §5 task ID range) | FIXED | plan.md:154-160 ranges T-A-1..8, T-B-1..18, T-D-1..9, T-C1-1..12, T-C2-1..6, T-E-1..9, T-F-1..7; "Total: 69 tasks" (plan.md:162) consistent with tasks.md task headers. |
| F-7 HIGH (concurrent click race) | FIXED | tasks.md:67 T-A-4 AC-1 explicitly uses `asyncio.gather`; AC-2/AC-3 assert exactly-one-200/one-400 + no partial DB state. |
| F-8/F-12 HIGH/MED (3 mandatory tests deferred) | FIXED | T-B-3 (tasks.md:141 monotonicity, "ship-gate for 216-B"), T-B-7 (tasks.md:182 wrong-tool recovery, "ship-gate for 216-B"), T-B-17 (tasks.md:278 completion-gate triplet, "mandatory test class #2") all in 216-B; plan.md:98 ship gate "B1.1-B1.22 + 3 mandatory test classes (T-B-3, T-B-7, T-B-17)". |
| F-9 HIGH (216-C 400-LOC overflow) | FIXED | plan.md:68-77 dependency graph splits 216-C → 216-C1 + 216-C2; plan.md:100-101 sized as ~350 + ~400 LOC; tasks.md:401-590 contains both T-C1-* and T-C2-* sections. |
| F-11 HIGH (phone-vs-backstory ordering) | FIXED | subspecs/216-C C1.1 (line 20) explicit ordering "...phone → voice_tone_pref → backstory_pick"; "Backstory pick is the cinematic climax AFTER phone + voice_tone_pref (per FR-09)". C1.18 (line 37) confirms "Screen ordering fixed by C1.1". spec.md:58 FR-02 same canonical order. |
| F-15 MED (T-D-1 column placement) | FIXED | tasks.md:308 T-D-1 AC-1 says "top-level columns (NOT JSONB-embedded) on public.users"; spec.md:484 NR-03 says "top-level columns on public.users (NOT JSONB-embedded inside onboarding_profile; canonicalized 2026-04-30 per data-layer-validator MED-1 / 216-D D1.10)". |
| F-14 MED (sub-budget clarification) | PARTIAL | E1.3 hard $0.15 vs E1.7 hard $0.50 are both stated but no single sentence calls out subset relationship. Non-blocking (MED). Accept as documented. |
| F-16 MED (Open Questions) | N/A | Accepted iter-1; no change required. |
| F-17 MED (DAG verification) | N/A | Iter-1 verified. |

### NEW findings (iter-2)

None. Spot-check of changed regions confirmed no new orphan ACs introduced; total task count 69 matches plan §5 expected.

### Verdict

**PASS** — proceed to /implement (Phase 8) starting with 216-A.

All 4 CRIT findings (F-1..F-4) and all 8 HIGH findings (F-5..F-11) verified fixed at file:line citations above. F-14 remains as documented MED non-blocker. 89/89 subspec ACs (100%) bound to ≥1 task per plan.md:162.
