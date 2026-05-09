# GATE 2: Architecture Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md`
**Validator**: sdd-architecture-validator
**Timestamp**: 2026-05-09
**Brief**: `~/.claude/plans/immutable-wondering-gray.md` (locked, 25 decisions)

## Verdict

**PASS**

## Severity Counts

CRITICAL=0  HIGH=0  MEDIUM=2  LOW=3

---

## Architecture Hard-Rule Coverage

Validation against `.claude/rules/agentic-design-patterns.md` (6 hard rules) + brief §5 / §20-B2 / §20-REUSE / §23.10:

| Rule | Spec FR/AC | Status | Notes |
|---|---|---|---|
| 1. Cumulative server-side state | FR-016 (state replay from log + snapshot, log wins on mismatch); AC-005-002 | PASS | Log-as-authority pattern is correct; matches Walk V precedent. Implicitly cumulative since per-turn extractions append to log. Could be more explicit ("WizardSlots Pydantic model with model_copy(update=…) merge" not named in spec — see MEDIUM-1). |
| 2. Pydantic completion gates (no hardcoded booleans) | FR-008 (BE constraints: min 4 / max 8 / strict cumulative-state validation gating); FR-015 (BE-strict validation per envelope, ModelRetry on failure) | PASS | "Strict cumulative-state validation gating must pass" + brief §23.3 "FinalForm.model_validate(slots) strict gate" = canonical pattern. |
| 3. Tool consolidation (no fan-out) | FR-005 (8 components and NO MORE); FR-004 (single typed envelope per turn = discriminated union) | PASS | 8-shape discriminated union is the consolidated pattern. Brief §20-I1 explicitly DELETED `reaction_only` 9th shape to prevent re-introducing fan-out. |
| 4. Monotonic progress | AC-001-002 ("progress monotonically increases on every accepted submission and never regresses") | PASS | Explicit AC. Matches Walk V agentic-design-pattern requirement. |
| 5. Validation layering | FR-015 (BE-strict per-envelope validation + bounded retries); R4 mitigation (target_slot via deps + dynamic instructions + @output_validator + ModelRetry + 3 retries + deterministic fallback) | PASS | All 3 layers present: pre-tool (Pydantic envelope schema), post-tool (@output_validator with ModelRetry), deterministic fallback (router voice without agent decoration on retry exhaustion). |
| 6. message_history primitive | Not explicitly named in FR/AC body | PASS-with-LOW-3 | Brief §18 P1 + §20 REUSE locks mandate `ModelMessagesTypeAdapter` / `hydrate_message_history` reuse. Spec inherits this via "Existing patterns to reuse" section but does not surface it as a named FR. Acceptable for spec-level (technology-agnostic per Article IV) but flag for plan.md. |

---

## Findings

### MEDIUM-1: Cumulative-state model not explicitly named in FR-016

**Category**: Module Organization / Type Safety
**Location**: `spec.md:133-137` (FR-016)
**Severity**: MEDIUM
**Issue**: FR-016 specifies "rebuild the cumulative slot state from the persisted conversation log AND a snapshot summary" but does not name the canonical primitive (`WizardSlots(BaseModel)` with `@computed_field` properties + `model_copy(update={...})` merge per `.claude/rules/agentic-design-patterns.md` Hard Rule 1).
**Impact**: Plan.md authors could re-implement state as plain dict / sidecar table instead of Pydantic-typed cumulative model — recreates the Walk V anti-pattern (`_compute_progress(latest_kind)` per-turn snapshot).
**Recommendation**: Plan.md MUST cite `.claude/rules/agentic-design-patterns.md` Hard Rule 1 as the canonical pattern and name `WizardSlots` (or equivalent) as the cumulative-state model. Brief §5 already specifies `state.py` module with `WizardSlots` — ensure plan.md inherits this name.

### MEDIUM-2: Atomic bulldoze enforcement — bulldoze list not enumerated in spec body

**Category**: Module Organization / Atomic Supersession
**Location**: `spec.md:145-149` (FR-018)
**Severity**: MEDIUM
**Issue**: FR-018 mandates atomic deletion of "legacy Spec 217 modules (BE emission union, sibling-DOM FE wizard, sidecar persistence, bare-token fallback, screen-config, agent-view) in the same PR that ships their replacement" but does not enumerate the verified-missing files from brief §20-B2 (archetypes.py, big5_judge.py, cohort_chips.py [reuse-not-bulldoze], conversation_persistence.py, question_registry.py, state_reconstruction.py [reuse-not-bulldoze], message_history.py [reuse-not-bulldoze]).
**Impact**: Implementor PR could miss specific imports surfaced by scope-reviewer grep against `nikita/api/routes/portal_onboarding.py`. Brief §23.10 atomicity note ("Bulldoze rows from §20-B2 ride with their owning PR") is the load-bearing detail.
**Recommendation**: Plan.md MUST inline the §20-B2 bulldoze table verbatim with per-row owning-PR annotation. Cross-reference §20-REUSE LOCKS (cohort_chips.py, IdempotencyStore, voice_service, hydrate_message_history, state_reconstruction.py — these are NOT bulldoze targets, they are reuse anchors). Without explicit reuse-vs-bulldoze split, implementor could delete reusable modules.

### LOW-1: Module separation v1+v2 implied, not asserted

**Category**: Module Organization / Directory Structure
**Location**: `spec.md` (no explicit FR)
**Severity**: LOW
**Issue**: Brief §5 specifies `nikita/agents/onboarding/v2/` (BE) + `portal/src/app/onboarding/v2/` (FE) clean directory split, with bulldoze of v1 paths same-PR. Spec FR-018 covers the bulldoze atomicity but does not name the v2/ subdirectory convention.
**Impact**: Plan.md could put new code at `nikita/agents/onboarding/` top-level (alongside about-to-be-deleted v1 files), creating temporal confusion during the bulldoze PR.
**Recommendation**: Plan.md should explicitly cite brief §5 directory layout: `nikita/agents/onboarding/v2/` for BE, `portal/src/app/onboarding/v2/` for FE. After PR-218-7 (Spec 217 supersession), v2/ may be flattened to top-level, but during the implementation window the v2/ namespace prevents collision.

### LOW-2: Type-mirror BE→FE not explicitly required as same-PR

**Category**: Type Safety
**Location**: `spec.md:127-131` (FR-015), `spec.md:62-65` (FR-004)
**Severity**: LOW
**Issue**: FR-015 mandates "BE is single source of truth for envelope shape" and FR-004 mandates the typed envelope, but the spec does not assert that TypeScript types in `portal/src/app/onboarding/v2/types/envelope.ts` MUST be regenerated/updated in the same PR as the Pydantic schema in `nikita/agents/onboarding/v2/envelope.py`.
**Impact**: Risk of FE/BE type drift between PRs. Brief §23.10 PR-218-3 lists "+ types/envelope.ts (vertical slice)" — atomicity is implied but not codified.
**Recommendation**: Plan.md should explicitly enumerate type-mirror as part of PR-218-3 vertical-slice contract.

### LOW-3: message_history primitive not surfaced in FR

**Category**: Agentic Hard Rule 6
**Location**: `spec.md` (Intelligence Evidence cites pattern, but no FR)
**Severity**: LOW
**Issue**: Per `.claude/rules/agentic-design-patterns.md` Hard Rule 6, `agent.run(..., message_history=state.messages, deps=deps)` is the canonical multi-turn primitive. Spec inherits via §20 REUSE LOCKS pointing to `hydrate_message_history` but does not declare it as an FR.
**Impact**: Risk that implementor reinvents conversation context in the request body (the documented anti-pattern). Brief §18 P1 amendment specifies `ModelMessagesTypeAdapter.validate_python()` as canonical wrapper.
**Recommendation**: Plan.md MUST cite Hard Rule 6 + §18 P1 amendment and require `message_history=` parameter on every `decorator_agent.run()` / `research_agent.run()` call site. Add to required-tests list.

---

## Per-Validation-Item Status

### 1. Module structure (clean v1/v2 separation)

**Status**: PASS-with-LOW-1
- Spec implicitly inherits brief §5 layout (BE `nikita/agents/onboarding/v2/`, FE `portal/src/app/onboarding/v2/`).
- FR-018 atomicity prevents v1+v2 co-mingling.
- Recommendation: surface in plan.md (LOW-1).

### 2. Six agentic hard rules

**Status**: PASS (with MEDIUM-1 + LOW-3 advisories)
See coverage table above. All 6 rules have at least one FR/AC anchor; 2 have implicit-only anchors that should be explicit in plan.md.

### 3. Atomic bulldoze rule (FR-018)

**Status**: PASS-with-MEDIUM-2
- FR-018 explicitly mandates same-PR delete + replace.
- `lifecycle: superseded` + `successor: 218` banner specified at supersession.
- Cite `.claude/rules/archive-policy.md` atomicity rule + `feedback_solo_dev_no_backcompat_reinforced.md`.
- Pattern-scout reuse map (cohort_chips, cost_guard, IdempotencyStore, voice_service, hydrate_message_history, state_reconstruction.py) preserved by FR reuse references in Intelligence Evidence (`spec.md:333-338`).
- Risk: spec body does not enumerate the bulldoze list (MEDIUM-2). Plan.md must inline §20-B2 with per-row owning-PR.

### 4. Type safety (discriminated-union envelope BE↔FE)

**Status**: PASS-with-LOW-2
- FR-004 (typed envelope = single source of truth) + FR-005 (8 component shapes locked) + FR-015 (BE-strict validation) cover the contract.
- Brief §23.4 explicitly REJECTED Gemini's semantic-intent abstraction in favor of concrete component names BE↔FE — keeping single layer.
- TS type-mirror same-PR requirement is implicit (LOW-2).

### 5. Solo-dev simplicity (Article VI ≤3 projects, ≤2 abstraction layers)

**Status**: PASS
- Out-of-Scope explicitly rejects Pydantic-graph FSM (`spec.md:386`).
- Out-of-Scope explicitly rejects BE semantic-intent abstraction (`spec.md:387`).
- Concrete component names BE↔FE per §23.4 (no extra abstraction layer).
- 8 components is the locked ceiling (FR-005).

### 6. Error handling architecture

**Status**: PASS
- Validation retries: FR-015 (bounded retries before user-facing error).
- Self-correcting agent loop: R4 mitigation (`@output_validator` + ModelRetry + 3 retries).
- Graceful degradation: R4 mitigation (deterministic fallback envelope on retry exhaustion); FR-010 + AC-003-006 (30s ceiling timeout + courteous fallback narrator line); NFR Availability (last-good envelope replay from cache when LLM degraded).

### 7. Observability (per-turn structured event)

**Status**: PASS
- NFR Observability (`spec.md:187-188`) specifies all required fields: `(user_id, phase, slot, component_shape, envelope_hash, latency_ms, cost_usd)`.
- Phase 2 turn count + termination cause logged for Walk B6 heuristic refinement.

### 8. Dependency graph (7-PR roadmap atomicity)

**Status**: PASS
- Brief §23.10 PR-218-3 vertical slice (BE route v2 + FE headless dispatcher + types/envelope.ts together) — atomicity locked.
- PR-218-4 ships FE UI components ON TOP of dispatcher (post-218-3 dependency respected).
- PR-218-PREREQ-A backstory pipeline timeout shipped FIRST (Out-of-Scope `spec.md:385` correctly excludes this from Spec 218 main scope).
- No circular dependencies in the PR DAG.
- Phone-demo wow ships LAST (PR-218-6) so core flow mergeable even if time runs out — sound risk-management.

---

## Architecture Alignment Summary

Spec 218 aligns with:

1. **Established codebase patterns** (BaseRepository, Pydantic AI agent factory, IdempotencyStore, cost_guard, voice_service, shadcn primitives) — pattern-scout REUSE LOCKS (§20) preserved via Intelligence Evidence cite.
2. **Agentic-design-patterns rule** (`.claude/rules/agentic-design-patterns.md`) — all 6 hard rules covered with FR/AC anchors.
3. **Solo-dev no-backcompat principle** (`feedback_solo_dev_no_backcompat_reinforced.md`) — atomic bulldoze FR-018 + Out-of-Scope explicitly forbids migration ceremony.
4. **Walk V (2026-04-22) precedent** — cumulative-state monotonicity (FR-016 + AC-001-002) + completion-gate triplet (FR-008 + FR-015) + Mock-LLM-emits-wrong-tool recovery (R4 mitigation).
5. **Codex+Gemini convergence** (§23 final canonical contract) — 8 components, static cohort lookup (not real-time firecrawl), opt-in voice demo, full-screen takeover, Supabase Realtime (no polling), DAG invalidation, BE-strict validation.

No architectural conflicts introduced.

---

## Required Plan.md Items (carry-forward from MEDIUM/LOW findings)

1. Name `WizardSlots(BaseModel)` cumulative-state primitive + `model_copy(update=…)` merge (MEDIUM-1).
2. Inline §20-B2 bulldoze table with owning-PR annotations + reuse-vs-bulldoze split (MEDIUM-2).
3. Cite `nikita/agents/onboarding/v2/` + `portal/src/app/onboarding/v2/` directory layout (LOW-1).
4. Enumerate TS type-mirror as same-PR contract within PR-218-3 (LOW-2).
5. Require `message_history=` parameter on every agent.run() call site (LOW-3).
6. Mandate the 3 agentic-flow test classes (cumulative-state monotonicity, completion-gate triplet, mock-LLM-emits-wrong-tool recovery) per `.claude/rules/testing.md`.

---

## Verdict

**PASS** — 0 CRITICAL, 0 HIGH. Spec is architecturally sound for proceeding to /plan (Phase 5). MEDIUM and LOW findings are plan.md carry-forwards, not gate blockers.
