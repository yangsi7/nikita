# Implementation Plan — Spec 217 Onboarding Wizard Deterministic-Track Redesign

**Spec ID**: 217-onboarding-wizard-deterministic-redesign
**Plan Status**: Draft (Phase 5)
**Date**: 2026-05-07
**Predecessor artifacts**: `spec.md`, 5 subspec spec.md files, `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md` (with ERRATA), `docs-to-process/20260507-spec217-2-backstory-diagnosis.md`.

---

## 1. Plan Scope

This is a **coordination plan** for the 5-subspec decomposition. Per-sub-PR architecture, file paths, and task lists live in subspec `plan.md` + `tasks.md`. Master plan owns:

- Cross-PR sequencing + dependency graph.
- Cross-cutting type system + interface contracts (BE → FE emission contract).
- PR plan with size estimates + ship gates.
- Reuse map (existing files extended vs. new files).
- Risk register with mitigations.
- Verification strategy (Walk B1-B4 ladder).

It does NOT duplicate subspec content. When in doubt, the subspec is authoritative.

---

## 2. Sub-PR Sequencing

```
217-0 (prereq cleanup, ~150 LOC)
    └─→ 217-1 (cold-start CTA + interstitial, ~150 LOC)
            └─→ 217-2 (backstory FE fallback + BE timeout, 80-150 LOC)
                    └─→ 217-3A (BE emission union, ~250-300 LOC)
                            └─→ 217-3B (FE wizard refactor, ~250-300 LOC)
                                    └─→ Walk B4 (post-final-merge integration)
```

Each `→` is a HARD ordering: previous sub-PR must be **merged + post-merge smoke verified** before the next branches off master. Live-walks (B1-B3) interleave between merges per planning brief Step 5.

---

## 3. Cross-cutting Type Contract (BE → FE)

### 3.1 Emission union (sub-PR 217-3A defines, 217-3B consumes)

```python
# nikita/agents/onboarding/converse_contracts.py (or new agent_emission.py)
class ReactionOnly(BaseModel):
    reaction_text: str = Field(max_length=140)

class FollowUpQuestion(BaseModel):
    reaction_text: str | None = Field(default=None, max_length=140)
    question_text: str = Field(max_length=240)
    control_type: Literal["text", "chips", "slider", "scenarios", "radio", "tel"]
    control_options: list[str] | None = None
    slot_to_fill: str  # ad-hoc follow-up slot key, NOT a deterministic SlotKind

class TurnFailure(BaseModel):
    explanation: str
```

### 3.2 `/answer` response envelope (217-3A defines)

```ts
// portal/src/app/onboarding/types/answer.ts (FE-side mirror)
type AnswerResponse =
  | { kind: "deterministic_advance"; output: { ... } }
  | { kind: "reaction"; reaction_text: string }
  | { kind: "followup"; payload: FollowUpQuestion }
  | { kind: "field_error"; errors: Record<string, string> }
  | { kind: "turn_failure"; explanation: string };
```

### 3.3 Sidecar persistence (217-3A)

- `users.onboarding_profile` JSONB column: add field `pending_followup: FollowUpQuestion | null` (separate from `slots`).
- Cleared by setting `null` on followup resolution.
- `WizardSlots` remains monotonic (Hard Rule #1).

### 3.4 IdentityPair contract (FR-10a/b)

```ts
// FE → BE
POST /api/v1/onboarding/answer
{ slot: "identity_pair", value: { name: string, age: number } }

// BE → FE on partial valid
{ kind: "field_error", errors: { age: "must be ≥ 18" } }
```

### 3.5 Cold-start CTA payload (FR-1)

`?start=welcome` static query param. BE behavior (216-A AC A1.1+A1.2): bare `/start` and `/start welcome` enter the SAME `SignupHandler.handle_welcome` handler — no organic-vs-CTA branching.

---

## 4. Reuse Map

| File | Action | Sub-PR |
|---|---|---|
| `nikita/agents/onboarding/conversation_agent.py` | Extend `output_type` + `instructions=callable` | 217-3A |
| `nikita/agents/onboarding/state.py` | Unchanged (`WizardSlots` monotonic invariant preserved) | — |
| `nikita/agents/onboarding/converse_contracts.py` | Add `ReactionOnly`, `FollowUpQuestion`, refactor `TurnFailure` | 217-3A |
| `nikita/agents/onboarding/agent_emission_state.py` | NEW (sidecar) | 217-3A |
| `nikita/agents/onboarding/validators.py` | Add mirror-of-next + mirror-echo `@output_validator` | 217-3A |
| `nikita/api/routes/portal_onboarding.py` | Refactor `/answer` dispatch on emission type; FR-4b 5-LOC `wait_for` | 217-3A, 217-2 |
| `portal/src/app/onboarding/_components/WizardShell.tsx` | Remove overlay; add archetype fallback; sibling DOM; interaction-locking | 217-2, 217-3B |
| `portal/src/app/onboarding/_components/AgentSubspace.tsx` | NEW | 217-3B |
| `portal/src/app/onboarding/_components/DeterministicTrack.tsx` | NEW | 217-3B |
| `portal/src/app/onboarding/_components/IdentityPair.tsx` | NEW | 217-3B |
| `portal/src/app/onboarding/_components/screen-config.ts` | Add `IdentityPair` control type | 217-3B |
| `portal/src/app/onboarding/hooks/useConversationState.ts` | Discriminated-union dispatch on `response.kind` | 217-3B |
| `portal/src/app/onboarding/types/{ControlSelection,answer,contracts,converse,wizard}.ts` | Type updates to mirror BE contract | 217-3B |
| `portal/src/components/landing/{hero-section,cta-section}.tsx` | Append `?start=welcome` via `URLSearchParams` | 217-1 |
| `portal/src/app/login/page-client.tsx` | Same (unauth branch only) | 217-1 |
| `portal/src/app/auth/interstitial/InterstitialClient.tsx` | Reskin per FR-2 | 217-1 |
| `portal/e2e/onboarding.spec.ts` | Replace 13 `networkidle` with `domcontentloaded` | 217-0 |
| `portal/e2e/onboarding-wizard.spec.ts:24-26` | DELETE test.describe.skip block | 217-0 |
| `ROADMAP.md` | Backfill #537/#538/#539 | 217-0 |

---

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 217-3A LOC overflows 350 cap | Medium | High (PR-cap violation) | Pre-flight `git diff --stat origin/master...HEAD` mid-implementation; split `@output_validator` + sidecar into 217-3A.1 if >350 |
| `difflib.SequenceMatcher` threshold 0.85 mis-calibrated | Medium | Medium (false-positive ModelRetry storms) | 5 hand-crafted near-duplicate + 5 distinct calibration fixture at `tests/agents/onboarding/fixtures/similarity_calibration.py`; tune BEFORE locking |
| Spike's mechanism-1 wrong (BE conditional skip is real culprit) | Low (HIGH confidence per spike) | Medium | FR-4b 5-LOC `wait_for` + existing `default_archetype_cards` fallback covers mechanism-2; FR-4a covers both mechanism-1 sub-mechanisms |
| Walk B4 surfaces emergent integration bug post-final-merge | Medium | Medium | TDD per sub-PR + zero-tolerance `/qa-review` per merge minimizes; B4 runs on full merged stack |
| Pydantic AI `ToolOutput` syntax flagged false-positive by reviewer | Medium | Low | Phase-2 primary-source verification rejected the false-positive; planning brief Planning Notes documents resolution |
| iOS PWA gesture regression on interstitial reskin | Low (FR-2 preserves real touch handler) | High (Spec 215 FR-6 violation) | UA-default-safe inversion; e2e fixture covers Chrome desktop + iOS Safari standalone + Telegram IAB UA cases |

---

## 6. Verification Strategy

Inherited R1-R13 from planning brief; per-sub-PR coverage in subspec tasks.md. Master gates:

- **GATE 2 (validators)**: 6 parallel `Task(subagent_type=sdd-*-validator)` invocations. **Status**: deferred to orchestrator main thread per worktree-subagent dispatch-cap budget. See `validation-findings.md`.
- **Pre-merge per sub-PR**: TDD coverage + pre-push HARD GATE (full test suite for touched area) + `/qa-review` zero-tolerance fresh-context loop.
- **Live walks**: B1 (217-1), B2 (217-2 — already informed by spike artifact), B3 (217-3 final), B4 (post-final-merge).

---

## 7. Constitutional Compliance

- **Article I (Intelligence-First)**: planning brief consumed Phase-1 codebase verification; spike artifact frozen for 217-2.
- **Article III (Test-First)**: every sub-PR ships with TDD-first commits (failing test → minimal impl → green).
- **Article IV (Spec-First)**: spec → plan → tasks → audit → implement sequence; this plan is Phase 5.

---

## 8. Open Coordination Items

1. **GATE 2 validators**: deferred. Orchestrator dispatches 6 parallel `sdd-*-validator` agents from main thread (see `validation-findings.md`).
2. **Slot grouping depth**: default = name+age only. Re-confirm via `AskUserQuestion` if walk-fatigue evidence emerges.
3. **Mirror-similarity calibration fixture**: write `tests/agents/onboarding/fixtures/similarity_calibration.py` BEFORE locking the 0.85 threshold in 217-3A.
