---
title: Spec 217 orchestration handover — complete (post-Walk-B4)
lifecycle: living
date: 2026-05-08
session: post-Walk-B4 close-out
type: handover
supersedes: docs-to-process/20260508-spec217-handover-3B-ready.md
---

# Spec 217 Handover — Orchestration Complete

## TL;DR

Spec 217 (onboarding wizard deterministic-track redesign) — all 5 sub-PRs merged, Walk B1/B2/B3v2/B4 executed live on production, 4 of 5 original user-reported bugs verified fixed, end-to-end completion gated on follow-up GH #568. Master HEAD `d58c321`. BE rev `nikita-api-00303-xsx`. FE on Vercel from master.

## High-level goal

Replace 216-B + 216-C onboarding wizard with sibling-DOM deterministic-track + agent-subspace separation, fix backstory hang, fix cold-start CTA + interstitial reskin + loading-flash. Triggered by user dogfood evidence (IMG_0431-0434.PNG) showing 5 catastrophic UX failures.

## Status snapshot

| Layer | State |
|---|---|
| master HEAD | `d58c321 docs(217): walk B4 final integration audit + screenshots (#569)` |
| Cloud Run BE | `nikita-api-00303-xsx` — 100% traffic — verified `/answer` returns 6-branch `oneOf` `kind` discriminator |
| Vercel FE | master `2e41491` (217-3B sibling-DOM + IdentityPair + reducer dispatch live) |
| Telegram MCP | alive (`@to5meo` user `V.` id 746410893) |
| Supabase MCP | UNAUTH in subagent context (DB cleanup blocked; root session not yet tested) |

## Original user bugs (resolution matrix)

| # | Bug from IMG_0431-0434 | Sub-PR | Walk verification |
|---|---|---|---|
| 1 | TG CTA missing /start prefill | 217-1 | Walk B1 PASS, Walk B4 PASS (`?start=welcome` confirmed in href) |
| 2 | "access portal" interstitial | 217-1 | Walk B1 PASS, Walk B4 PASS |
| 3 | "in development" loading flash | 217-1 | Walk B4 PASS (`document.body.innerText` does NOT match `/in development|in progress/i`) |
| 4 | deterministic+agent overlay | 217-3B | Walk B3v2 PASS, Walk B4 PASS (`det.parentNode === agent.parentNode` confirmed via Chrome MCP `evaluate_script`) |
| 5 | backstory hang | 217-2 + 217-2c | Walk B2 PASS, Walk B2-resume PASS |

## Sub-PR scoreboard (final)

| PR | Title | Master commit |
|---|---|---|
| #560 | feat(217,3A.1): emission union prereqs | `a69db24` |
| #562 | feat(217,3A.2): emission-union agent + sidecar + CompletionResponse | `34f9f44` |
| #563 | feat(217,3A.3): /answer route emission dispatch + IdentityPair BE | `fc53436` |
| #565 | feat(217,3B): FE wizard sibling-DOM refactor + IdentityPair | `2e41491` |
| #567 | docs(217,3B): walk B3 + B3v2 audit reports | `c17b6d8` |
| #569 | docs(217): walk B4 final integration audit + screenshots | `d58c321` |

(217-0/1/2/2c shipped earlier in same session chain; see `docs-to-process/20260508-spec217-handover-3B-ready.md` for those commits.)

## Walk results

| Walk | Verdict | Plus-alias | Notes |
|---|---|---|---|
| B1 | PASS | `simon.yang.ch+walkB1@gmail.com` | 217-1 cold-start CTA + interstitial reskin + loading-flash |
| B2 | PASS | `simon.yang.ch+walkB2@gmail.com` | 217-2 backstory FE fallback + BE 20s timeout |
| B2-resume | PASS | (same) | Verification re-run after 217-2c retry helper merged |
| B2-resume2 | BLOCKED Telegram MCP | (same) | (Walk completed in next session via 217-2c QA only) |
| B3 | BLOCKED | `simon.yang.ch+walkB3@gmail.com` | Deploy infra regression (GH #566 closed); Walk B3v2 supersedes |
| B3v2 | PARTIAL PASS | `simon.yang.ch+walkB3v2@gmail.com` | 15/18 ACs verified live + 3 code-verified after redeploy on rev 00303 |
| B4 | PARTIAL | `simon.yang.ch+walkB4@gmail.com` | (a)(b)(c)(d) PASS; (e)(f) BLOCKED-BY-#568 |

## Plan-Step-6 final exit-criteria matrix

| # | Assertion | Status |
|---|---|---|
| (a) | cold-start TG CTA prefills `/start welcome` | PASS |
| (b) | interstitial reskin renders Spec 208 brand veil | PASS |
| (c) | no loading flash | PASS |
| (d) | wizard renders sibling DOM (`deterministic-card` ↔ `agent-subspace` siblings) | PASS |
| (e) | backstory completes p99 ≤30s OR retry CTA renders | BLOCKED-BY-#568 |
| (f) | FinalForm fires + redirect to /dashboard | BLOCKED-BY-#568 |

## Open follow-ups

| GH # | Severity | Title | Owner spec |
|---|---|---|---|
| 568 | MEDIUM (open) | emission agent over-emits ReactionOnly, deterministic-card never advances | 217-3A.3 territory |
| 570 | LOW (open) | /auth/confirm ignores next= param, redirects to /dashboard | 217-1 territory (or new spec) |
| 564 | LOW (open) | end-to-end completion-route-dispatch test | 217-3A.3 territory |
| 566 | CLOSED | deploy infra regression (Cloud Run rev served stale image) | resolved by redeploy from /tmp |

## Critical learnings filed in user-global memory

1. **`feedback_gcloud_deploy_outside_claude_dir.md`** (NEW, this session) — NEVER `gcloud run deploy --source .` from cwd inside `.claude/`. The `.gcloudignore` excludes `.claude/`; deploy from a sub-path produces silent stale-image regression. Always deploy from main repo root OR `/tmp/...` detached worktree. Verify openapi.json schema/summary post-deploy. Walk B3 GH #566 precedent.

## DB cleanup pending (manual run when Supabase MCP env restored)

Walk users still in DB (Supabase MCP returned `Unauthorized` in subagent context for all 3 walks):

```sql
-- Run for each plus-alias: walkb3, walkb3v2, walkb4 (lowercased per Supabase normalisation)
WITH target AS (
  SELECT id FROM auth.users WHERE email = 'simon.yang.ch+walkb3@gmail.com'
)
DELETE FROM user_metrics                WHERE user_id IN (SELECT id FROM target);
DELETE FROM user_vice_preferences       WHERE user_id IN (SELECT id FROM target);
DELETE FROM scheduled_events            WHERE user_id IN (SELECT id FROM target);
DELETE FROM memories                    WHERE user_id IN (SELECT id FROM target);
DELETE FROM user_profiles               WHERE id     IN (SELECT id FROM target);
DELETE FROM users                       WHERE id     IN (SELECT id FROM target);
DELETE FROM auth.users                  WHERE id     IN (SELECT id FROM target);
```

Repeat for `+walkb3v2@gmail.com` and `+walkb4@gmail.com`. UUIDs captured in walk reports for traceability.

GH #554 tracks the underlying `Supabase MCP unauthorized in worktree subagent context` issue.

## Compact-safe resume read order (next session)

1. **This file** (`docs-to-process/20260508-spec217-handover-complete.md`)
2. `docs-to-process/20260508-spec217-handover-3B-ready.md` (prior handover; supersedes by this doc)
3. `audits/2026/20260508-walk-B4-spec217-final.md` (final integration walk evidence)
4. `audits/2026/20260508-walk-B3v2-spec217-3B.md` (217-3B substance verification)
5. `~/.claude/plans/immutable-wondering-gray.md` (orchestration plan; Steps 1-6 all complete)
6. GH issue #568 (the only open MEDIUM follow-up)

## Recommended next-session next actions (in priority order)

1. **GH #568 fix** (MEDIUM, blocks end-to-end completion)
   - Investigate `nikita/agents/onboarding/conversation_agent.py` `get_emission_agent` factory
   - Add unit test: clean inputs (no clarification needed) → emission output_type asserts `SlotDelta` (deterministic) NOT `ReactionOnly`
   - Audit instructions for "advance unless ambiguity" rule
   - Likely a prompt-tuning + test-coverage fix, not a structural change
   - Once fixed → re-run Walk B4 to verify (e)+(f) BLOCKED-BY-#568 → PASS

2. **GH #570 fix** (LOW, cosmetic)
   - `portal/src/app/auth/confirm/route.ts` — read + honor `next=` param after `supabase.auth.verifyOtp`
   - Check Spec 216-A magic-link flow (autobind) for cross-impact
   - Small change, single file

3. **Manual DB cleanup** (3 walk users) once Supabase MCP env restored. SQL above.

4. **GH #554 root cause fix** for Supabase MCP unauth in worktree subagent context (so future walks can self-cleanup).

5. **Spec 217 closeout** once #568 fixed:
   - Add `lifecycle: frozen` to all 217 spec.md files
   - File CL-VERIFY checks per `~/.claude/plans/immutable-wondering-gray.md` "CL-VERIFY" section (cleanup audit)
   - ROADMAP sync via `/roadmap sync`
   - Archive planning brief `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md` to `docs/.archive/`

## State files / housekeeping

- 5+ orphan worktrees in `.claude/worktrees/` from this session's subagents (a3e62c6261cc24f76, ab5b16369a3b39c8d, a851065262550655d, ad4e9f48d973fe659). Clean via `git worktree remove --force <path>` once branches merged or abandoned.
- `feat/217-3B-fe-wizard-refactor`, `docs/217-walk-B3-audit-reports`, `docs/217-walk-B4-final` branches still exist on origin (not deleted via `--delete-branch` flag). Safe to delete via `gh api -X DELETE repos/yangsi7/nikita/git/refs/heads/<branch>`.

## Operational notes

- Cloud Run rev `nikita-api-00303-xsx` (correctly serving 217-3A.x). DO NOT redeploy from worktree paths inside `.claude/`. Use `/tmp/nikita-deploy-master` (created via `git worktree add --detach /tmp/nikita-deploy-master <commit>`).
- Vercel auto-deploys FE on master push. No manual step needed.
- Telegram MCP session was alive at session end. Re-mint via `! cd /Users/yangsim/Nanoleq/sideProjects/telegram-mcp && python session_string_generator.py` if `mcp__telegram-mcp__get_me` returns auth error in next session.
- Gmail MCP bound to `simon.yang.ch` admin inbox. Plus-alias `simon.yang.ch+walkBN@gmail.com` is the canonical pattern (memory `feedback_dogfood_gmail_mcp_mismatch.md`); the protocol-doc `youwontgetmyname777+...` example is stale.

## Spec ownership matrix (post-217 canonical)

Per `~/.claude/plans/immutable-wondering-gray.md` "Spec ownership matrix":

| Concern | Authoritative Spec |
|---|---|
| Telegram canonical routing (`/start` parser) | 216-A |
| Magic-link auth + autobind | 216-A + 216-H |
| Big5 + 12-archetype scoring | 216-D |
| Firecrawl + cost guard | 216-E |
| TG-first landing CTA | 216-G (217-1 amends with `?start=welcome`) |
| Wizard interaction model (deterministic + agent emission) | **217** |
| Backstory pipeline | **217-2** + 216-D consumption |
| Interstitial + iOS PWA gesture | 215 FR-6 + **217-1** reskin |

## What worked well this session

- Worktree-isolated implementor + zero-tolerance fresh-context QA loop converged in 1-2 iters per PR.
- Grep-verify gate caught both the implementor's "fix complete" SSH-signing-failed silent push AND the deploy-infra stale-image regression that would otherwise have wasted hours.
- Plan-Step-6 explicit exit-criteria matrix gave Walk B4 unambiguous reporting structure even under partial-PASS.
- AskUserQuestion (vs inline-prose options) at the 217-3B re-dispatch decision point preserved user agency.

## What didn't go well

- Cloud Run deploy from `.claude/`-cwd silently shipped stale image (GH #566). Fixed + memory entry filed; future deploys must verify openapi.json shape.
- Supabase MCP unauth in subagent context blocked DB cleanup across 3 walks. Filed GH #554 (existing); cleanup deferred to manual.
- Implementor's `git push` in subagent failed silently due to SSH agent signing error; orchestrator caught it via grep-verify gate but subagent self-report was misleading. Memory entry already exists: `feedback_implementor_self_report_verification.md`.
