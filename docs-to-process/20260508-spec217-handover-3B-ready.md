---
title: Spec 217 orchestration handover — 217-3A complete, 217-3B ready to dispatch
lifecycle: living
date: 2026-05-08
session: post-217-3A.3 merge → 217-3B dispatch pending
type: handover
---

# Spec 217 Handover — 217-3B Dispatch (post-compact)

## TL;DR

Spec 217 onboarding wizard deterministic-track redesign. Master HEAD: `fc53436`. 4 of 5 sub-PRs merged (217-0, 217-1, 217-2, 217-2c, 217-3A.1, 217-3A.2, 217-3A.3 — all BE work shipped). Remaining: **217-3B FE wizard refactor** + Walk B4 final integration.

## Context one-liner

Spec 217 supersedes 216-B + 216-C. Original trigger: 5 catastrophic UX bugs from IMG_0431-0434 user dogfood (TG CTA missing /start prefill, "access portal" interstitial, "in development" loading flash, deterministic+agent overlay in wizard card, backstory hang at "preparing the three of us..."). Plan-rewrite Tier-3 brief: `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md`. Orchestration plan: `~/.claude/plans/immutable-wondering-gray.md`.

## Sub-PR Scoreboard

| Sub-PR | Status | Walk | User-bug-fixed | Master commit |
|---|---|---|---|---|
| 217-0 prereq cleanup | ✅ merged | n/a | (test plumbing) | `6b15668` |
| 217-1 cold-start CTA + interstitial + loading flash | ✅ merged | B1 PASS | bugs 1, 2, 3 ✅ | `9003a58` |
| 217-2 backstory FE fallback + BE asyncio.wait_for(20s) | ✅ merged | B2-resume PASS | bug 5 partial | `2edc781` |
| 217-2c ModelHTTPError retry + structured logs | ✅ merged | B2-resume2 BLOCKED Telegram MCP | (defensive layer) | `72bd18f` |
| **217-3A.1** emission union prereqs | ✅ merged 2026-05-08 03:30Z | n/a (BE) | — | `a69db24` (PR #560) |
| **217-3A.2** emission-union agent + sidecar + CompletionResponse | ✅ merged 2026-05-08 ~07:30Z | n/a (BE) | — | `34f9f44` (PR #562) |
| **217-3A.3** /answer route dispatch + IdentityPair BE + AnswerResponse rename | ✅ merged 2026-05-08 ~10:50Z | n/a (BE) | — | `fc53436` (PR #563) |
| **217-3B** FE wizard sibling-DOM refactor | 🟡 **NEXT — ready to dispatch** | B3 pending | bug 4 (overlay) | — |
| Walk B4 final integration | pending (post-217-3B merge) | — | — | — |

## What's Live

- **Master HEAD**: `fc53436 feat(217,3A.3): /answer route emission dispatch + IdentityPair BE + AnswerResponse rename (#563)`
- **Cloud Run**: `nikita-api-00301-5f8` (217-2 + 217-2c). 217-3A.1/3A.2/3A.3 NOT yet deployed — BE-only schema + route refactor; needs deploy after merge if FE will hit live BE during Walk B3.
- **Pytest**: 7044 passed on master (last run pre-217-3A.3, expect similar +50 new).

## 217-3A Recovery Highlights (post-compact context)

### 217-3A.1 (PR #560): 6 QA iterations, 7 commits squashed → 8 files, +809/-1
- Original implementor `a4c20c4710b40de30` killed by usage-limit at 00:30Z mid-flight.
- Orchestrator branched + recovered partial work + completed remaining 4 files manually.
- 6 QA iters: iter-1 (3 IMPORTANT + 1 NITPICK) → iter-6 CLEAN 0/0/0.

### 217-3A.2 (PR #562): 1 QA iter + spec amendment → 5 files, +760/-5
- Implementor `a6b55021e78fd1f26` self-split scope when realizing 217-3A would exceed 350 LOC.
- Shipped: agent factory `get_emission_agent`, sidecar persistence helpers (jsonb_set + #-), CompletionResponse 6th branch (resolves GH #561), 43 new tests covering AC-T-1..5.
- DEFERRED to 217-3A.3: route refactor + IdentityPair + 4 legacy-test rewrites.

### 217-3A.3 (PR #563): 3 QA iters → 14 files, +987/-2144
- Implementor `a5e8810562c2470ce`. Key changes:
  - Renamed legacy `AnswerResponse` → `LegacyAnswerResponse` in `nikita/agents/onboarding/answer_contracts.py`.
  - Refactored `/answer` route in `portal_onboarding.py` from 480-line legacy envelope to 6-branch discriminated dispatch.
  - Added `SlotKind.IDENTITY_PAIR` + IdentityPair partial-validation logic.
  - Re-wired `_run_emission_with_retry` (was unwired by initial refactor; QA iter-1 BLOCKING-1 fix in commit `90c4c8c`).
  - Deleted 4 legacy test files (1647 LOC) — covered by 2 new files (test_emission_dispatch.py + test_identity_pair.py, 562 LOC) + retry tests added in QA fix.
- QA iter-3 IMPORTANT-1 (completion-route-dispatch end-to-end test) deferred to GH #564 (LOW); triplet test at WizardSlots level already covered by `test_completion_gate.py`.

## 217-3B Scope (NEXT DISPATCH)

Spec: `specs/217-onboarding-wizard-deterministic-redesign/subspecs/217-3B-fe-wizard-refactor/spec.md` (93 lines).

Branch: `feat/217-3B-fe-wizard-refactor` (create from master `fc53436`).

LOC budget: 250-300 estimate; 600 cap authorized.

### Files to create/modify

| Action | File |
|---|---|
| NEW | `portal/src/app/onboarding/_components/DeterministicTrack.tsx` |
| NEW | `portal/src/app/onboarding/_components/AgentSubspace.tsx` |
| NEW | `portal/src/app/onboarding/_components/IdentityPair.tsx` |
| EDIT | `portal/src/app/onboarding/_components/WizardShell.tsx` (REMOVE overlay L467 reactionText, L542 NikitaReaction, L760-789 control rendering; mount sibling DOM) |
| EDIT | `portal/src/app/onboarding/_components/screen-config.ts` (add `IdentityPair` control type) |
| EDIT | `portal/src/app/onboarding/hooks/useConversationState.ts` (case "server_response" L175 — discriminated-union dispatch on 6 `kind` values) |
| EDIT | `portal/src/app/onboarding/types/answer.ts` (regen TS types from BE OpenAPI; should now have 6 kinds incl. `completion`) |
| NEW | `portal/src/app/onboarding/_components/__tests__/WizardShell.test.tsx` |
| NEW | `portal/src/app/onboarding/_components/__tests__/IdentityPair.test.tsx` |
| NEW | `portal/src/app/onboarding/hooks/__tests__/useConversationState.test.ts` |

### Critical AC summary

- **AC-11.3 CRITICAL**: `[data-testid="deterministic-card"]` + `[data-testid="agent-subspace"]` are SIBLING DOM nodes (assert `el.parentNode === other.parentNode`).
- **AC-12.1**: `state.kind === "reaction"` → DeterministicTrack STAYS ENABLED (typing fades reaction). NO setTimeout auto-advance.
- **AC-12.4**: at most ONE input focusable across both regions.
- **AC-13.2**: discriminated-union dispatch on `response.kind ∈ {deterministic_advance, reaction, followup, field_error, turn_failure, completion}` (6 kinds; `completion` per GH #561 amendment).
- **AC-13.3**: NO setTimeout on reaction state (vitest spy assertion).
- **AC-T-B.1/B.2/B.3 CRITICAL**: 3 new vitest files mandatory.

### BE contract (from 217-3A merged)

`AnswerResponse` discriminated union with 6 `kind` branches. Each FLATTENS payload (no `payload:` nesting per QA iter-1 ruling on PR #560):

```typescript
type ReactionResponse        = { kind: "reaction"; reaction_text: string };
type FollowUpResponse        = { kind: "followup"; question_text: string; target_slot: string | null };
type FieldErrorResponse      = { kind: "field_error"; errors: Record<string, string> }; // min 1 entry
type TurnFailureResponse     = { kind: "turn_failure"; explanation: string };
type DeterministicAdvanceResponse = { kind: "deterministic_advance"; next_slot_kind: string | null; progress_pct: number; archetype_cards: object[] | null };
type CompletionResponse      = { kind: "completion"; is_complete: true; link_code: string | null; conversation_id: string; progress_pct: 100 };
type AnswerResponse = ReactionResponse | FollowUpResponse | FieldErrorResponse | TurnFailureResponse | DeterministicAdvanceResponse | CompletionResponse;
```

### Spec 208 design tokens (mandatory)

bg-void `oklch(0.08 0 0)`, rose `oklch(0.75 0.15 350)`, Geist Sans/Mono, glass-card, AuroraOrbs, GlowButton, EASE_OUT_QUART. shadcn/ui Card+Skeleton+Alert via `mcp__shadcn__*` MCP.

### Vocab discipline (mandatory)

NO `FILE`, `dossier`, `clearance`, all-caps `FIELD` in user-facing wizard JSX strings. Per `nikita/agents/onboarding/CLAUDE.md`. Interstitial-level "cleared/portal" copy fine.

### Em-dash discipline (mandatory)

NO em-dashes in user-rendered JSX strings. Allowed in JSDoc/comments only.

## Open GH Issues

| # | Severity | Title |
|---|---|---|
| 564 | LOW | test(217,3A.3): add end-to-end completion-route-dispatch test |
| 561 | HIGH | (CLOSED via 217-3A.2 amendment + 217-3A.3 merge) DeterministicAdvanceResponse missing terminal-turn fields |
| 559 | MEDIUM | fix(ci): test-summary/action@v2 missing index.js (broken-infra, non-blocking) |
| 557 | MEDIUM | feat(observability,agents): codebase-wide retry helper for ModelHTTPError |
| 556 | MEDIUM | feat(observability): structured backstory_pipeline_timeout events |
| 554 | MEDIUM | chore(devx): Supabase MCP unauthorized in worktree subagent context |
| 549 | LOW | chore(portal): delete /onboarding/auth/route.ts 410 stub after 2026-06-06 |
| 547, 546, 545 | spec amendments tracked in spec.md |

## Active background tasks at compact time

- **Implementor `a5e8810562c2470ce`** completed (post-merge) — worktree at `.claude/worktrees/agent-a5e8810562c2470ce` may persist.
- 217-3B implementor dispatch was REJECTED by user just before this handover — pending re-dispatch on next session resume.

## Workflow conventions reminder (per ~/.claude/plans/immutable-wondering-gray.md step 5.x)

Per sub-PR cycle:
1. Implementor dispatch (worktree-isolated, HARD CAP, scope clause, anti-fab clause).
2. Orchestrator grep-verify gate after implementor reports complete.
3. Pre-push gate: full pytest + portal vitest+lint+build OR scoped (faster, trust CI for full).
4. PR open → fresh-context QA review subagent (HARD CAP 5).
5. Zero-tolerance loop until 0/0/0 across all severities.
6. CI green check.
7. Squash merge.
8. Commit-hash verify.
9. Post-merge smoke test (auto-dispatched).

## User preferences captured this session

- **Speed**: prefer scoped pytest + trust CI; full local 7000-test suite is 25min wall, often skippable when CI runs full.
- **Auto-mode**: minimize interruptions, dispatch follow-through autonomously.
- **AskUserQuestion**: use the tool for genuine clarifications; never inline-prose-options.
- **Em-dash hard rule**: forbidden in user-facing prose, allowed in dev docs/comments. Per `~/.claude/CLAUDE.md`.
- **600-LOC PR cap**: authorized for 217-3A.2+3A.3 path; 217-3B same authorization.

## Compact-safe resume

Read in order on next session:
1. This file (`docs-to-process/20260508-spec217-handover-3B-ready.md`)
2. `~/.claude/plans/immutable-wondering-gray.md` (orchestration plan, step 5.5)
3. `specs/217-onboarding-wizard-deterministic-redesign/subspecs/217-3B-fe-wizard-refactor/spec.md`
4. `.claude/rules/{agentic-design-patterns,live-testing-protocol,pr-workflow,subagent-safety,parallel-agents,testing}.md`

## Exact next action

User REJECTED the 217-3B implementor dispatch just before this compact. Either:
- (a) Re-dispatch with same prompt structure (handover doc enumerates everything needed).
- (b) Implement 217-3B manually given 600-LOC scope is reachable.
- (c) User-decide via AskUserQuestion if something else needed.

Cloud Run deploy of master `fc53436` may be desirable BEFORE Walk B3 (so FE hits 217-3A.x BE live). Telegram MCP session was EXPIRED at last check — re-mint via `! cd /Users/yangsim/Nanoleq/sideProjects/telegram-mcp && python session_string_generator.py` if Walk B3 follows immediately.
