# Handover Brief — Walk A1 Batch Shipped (2026-05-06)

**Status**: Onboarding wizard FUNCTIONAL on prod. 5 of 7 Walk A1 issues shipped, 2 in flight. Ready for user dogfood.

## TL;DR

If picking up cold: the onboarding wizard is now live and usable. New users CAN sign up via Telegram-first OR portal-first paths, magic-link auto-binds Telegram, bare-token first answers extract correctly, mid-flow refresh resumes at the right screen, no em-dashes leak. PR #533 (phone E.164) is the only Walk A1 P2 fix still in flight.

## Test URL + Walk A3 Protocol

```
URL: https://nikita-mygirl.com/
Email pattern: simon.yang.ch+walkA3@gmail.com (admin Gmail MCP routes here)
Walk protocol: .claude/rules/live-testing-protocol.md (12 steps)
```

Verification sequence (Walk A3):
1. Cold-start landing → click CTA → /onboarding/auth lands
2. Submit email → magic link arrives at Gmail MCP
3. Click magic link → /auth/confirm → /auth/interstitial → /onboarding (NOT /dashboard)
4. Type bare token "Walker" at name slot → progress > 0 (closes #484 verification)
5. Refresh mid-wizard → resumes at next missing slot, NOT welcome screen (closes #485)
6. No "welcome back" copy on fresh signup screen (closes #488)
7. No em-dashes in any nikita_reply across 13 turns (closes #494)
8. Submit invalid phone "abc" → agent re-asks (closes #490, after PR #533 merges)
9. DB cleanup per FK-safe template at .claude/rules/live-testing-protocol.md

## What Shipped (Walk A1 + EM stack — chronological)

| PR | Issue | Title | Branch | Merged Commit |
|---|---|---|---|---|
| #515 | EM-1 | unify auth callback /auth/callback → /auth/confirm | fix/216-EM1-auth-callback-unify | e520493 |
| #517 | EM-3a | portal env hardening NODE_ENV guard + fail-fast | fix/216-EM3a-portal-env-hardening | 7470b3b |
| #518 | EM-4 | delete legacy WizardPersistence + WizardStateMachine | fix/216-EM4-state-unification | aa424cb |
| #519 | EM-3b | BE consolidation UserService + tuning constants | fix/216-EM3b-be-consolidation | c0d6bbf |
| #520 | EM-2 | autobind Telegram on /auth/confirm | fix/216-EM2-autobind-telegram | b3941c0 |
| #524 | hotfix | middleware /auth/confirm + /auth/interstitial passthrough | fix/216-walka2-hotfix-middleware-confirm-passthrough | 3a02bd1 |
| #527 | EM-3b vault | switch cron-bearer migration GUC → Supabase Vault | fix/em3b-vault-pattern-supersede | 73cc2bf |
| #528 | #484 P0 | bare-token first-answer extraction (Walk A1 C1) | fix/484-c1-bare-token-extraction | 1ea3c82 |
| #529 | #485 HIGH | wizard rehydration resumes at next missing slot | fix/485-h2-wizard-rehydration | (merged) |
| #530 | #495 LOW | em-dash in landing copy | fix/495-em-dash-landing | (merged) |
| #531 | #494 LOW | em-dash sanitizer in LLM nikita_reply | fix/494-em-dash-llm-sanitizer | (merged) |
| #532 | #488 MED | welcome-back copy gated on progress > 0 | fix/488-welcome-back-fresh-signup | (merged) |

Backend Cloud Run rev: **nikita-api-00299-587** (post-#484 deploy).
Vercel: auto-deploys on master push. Latest portal-affecting merge = #532.

## In Flight (NOT yet merged)

| PR | Issue | Title | Status |
|---|---|---|---|
| #533 | #490 MED | phone E.164 deterministic post-processor | open, CI in progress |

After #533 merges → backend redeploy needed (`gcloud run deploy nikita-api ...`).

## Open Walk A1 Issues — NOT Started

| GH | Severity | Title | Effort | Notes |
|---|---|---|---|---|
| #486 | ops | magic-link sender `onboarding@silent-agents.com` not Nikita-branded | Supabase Dashboard config | Not blocking |
| #487 | ops | magic-link template merges code + link (confusing) | Supabase template edit | Not blocking |
| #491 | MED | GET /state cid inconsistency top-level vs last_assistant_turn | BE 1-2h | Logging hygiene |
| #492 | MED | multiple cids share one users.onboarding_profile.conversation array | BE 1-2h | Logging hygiene |
| #525 | LOW | magic-link URL contains `//auth/confirm` (Site URL trailing slash) | Supabase Dashboard config | Cosmetic, browser normalizes |
| #449 | MED | Vercel insights MIME error console noise | Vercel project config | Console noise only |
| #509 | MED/infra | tighten SQL-write hook detector | Hook fix, separate PR | Orthogonal |

## Outstanding Carry-overs from Earlier (Pre-Walk-A1)

| GH | Status |
|---|---|
| #453 | CLOSED — N1 ordering invariant fixed in T-B3-12 |
| #454 | OPEN — N2 regression-guard regex too narrow |
| #455 | OPEN — N3 redaction templates not yet wired |
| #463 | OPEN — coarse PII strip on firecrawl response snippets |
| #465 | OPEN — automated TS↔Pydantic drift |
| #466 | OPEN — migrate Slider control to Radix |
| #467 | OPEN — rewrite onboarding-chat E2E for cinematic wizard |

## Stash State (Live)

```
git stash list
# stash@{0}: empty (em-dash WIP popped + shipped)
# stash@{1}: WIP before walkA1-H2 branch (older, may discard)
# stash@{2}: pre-216-resume-20260503-1318 (older, may discard)
```

## Critical Rules to Re-Read on Resume

| Rule | Why |
|---|---|
| `~/.claude/rules/operating-principles.md` | Auto-execute follow-through, AskUserQuestion-only, no DB fabrication |
| `.claude/rules/pr-workflow.md` | Pre-push test gate (full suite), grep-verify gate, /qa-review absolute-zero |
| `.claude/rules/agentic-design-patterns.md` | Hard Rule §5 (3-layer validation) drives #484 + #490 fix shape |
| `.claude/rules/live-testing-protocol.md` | 12-step Walk A3 protocol + anti-fabrication |
| `.claude/rules/parallel-agents.md` | Subagent dispatch caps (HARD CAP + scope + exit criterion) |
| `.claude/CLAUDE.md` | Pre-send banned-closer scan; auto-dispatch routine follow-through |

## Reference Plan

`/Users/yangsim/.claude/plans/docs-to-process-20260424-wizard-redesig-composed-micali.md` — 1500-line plan with EM-1..EM-4 + Walk A1 Phase 0..5. Original work is mostly closed; remaining open phases are Phase 4 Walk A2 verify (DONE 2026-05-05) + Phase 5 user testing handoff (THIS DOCUMENT).

## Auto-Memory Pointers (Most Relevant Today)

```
~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/
├── feedback_dont_offload_routine_followup.md
├── feedback_implementor_self_report_verification.md
├── feedback_no_db_fabrication_in_dogfood.md
├── feedback_subagent_dispatch_caps.md
├── feedback_agentic_systems_not_procedural.md
├── feedback_telegram_first_signup_pattern.md
├── feedback_compact_and_local_tests.md
└── project_users_table_schema.md (DB cleanup template)
```

## Resume Steps

1. Re-read `MEMORY.md` index for auto-memory recall
2. Check #533 status: `gh pr view 533 --json statusCheckRollup,mergeable`
3. If green: merge, close #490, deploy backend (`gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated`)
4. Run Walk A3 (live verification) per `.claude/rules/live-testing-protocol.md`
5. Surface remaining Walk A1 carry-overs (#491, #492, #525, ops #486/#487) — pick by user priority
6. Sync ROADMAP.md spec status

## What to Tell the User on Cold Start

> Walk A1 batch shipped. Onboarding functional on prod. Test at https://nikita-mygirl.com/. PR #533 (phone E.164) awaiting CI; remaining open issues are MEDIUM logging hygiene (#491/#492) + LOW cosmetics + ops config (#486/#487/#525). Ready to pick next priority.

---

**Last verified**: 2026-05-06 12:55 UTC
**Branch state**: detached or fresh on master post-#533 push
**Deploys live**: backend rev 00299 (commit 1ea3c82), Vercel auto on master
