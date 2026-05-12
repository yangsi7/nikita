---
title: Handover — Spec 218 PR-218-7 shipped, PR-218-8 final
date: 2026-05-13
lifecycle: frozen
type: handover
---

# Handover Brief — Spec 218 Slice 218-7 shipped + smoke green

Compaction-safe resume doc. Final slice 218-8 is the only remaining PR.

---

## §0 High-level Goals

1. **Spec 218 — onboarding wizard v2** (agent-driven dynamic UI): vertical-slice rollout per `~/.claude/plans/immutable-wondering-gray.md`. 8 PRs total (218-2..218-8), now 7 of 8 shipped.
2. PR-218-2..218-6 + precursor — see prior handovers.
3. **PR-218-7** (phone-demo wow + Supabase Realtime + opt-in modal + phone_demo_calls migration) — shipped `d2c6a54` (PR #590) THIS SESSION.
4. **PR-218-8** (atomic bulldoze + flag flip + Spec 217 supersession + ROADMAP sync) — FINAL.

## §1 Status Summary

| Item | State |
|---|---|
| Master tip | `d2c6a54` feat(218,7): phone-demo wow + Supabase Realtime + opt-in modal (#590) |
| Cloud Run | rev `nikita-api-00313-cjt` serving 100%, smoke green |
| PR-218-7 | merged `d2c6a54` after 2 QA-iter (incl. implementor self-review iter-0 + 2 fresh-context reviewer iters) + CI test mock fixes |
| Phase-1 + Phase-2 + phone-demo | all live behind `wizard_v2_enabled=False` flag |
| GH #581/#583/#584 | open — slice-218-2 R15 retry-budget deferred (block before launch) |
| GH #582 | CLOSED (PR #588) |
| Spec 217 | not yet superseded (PR-218-8 task) |
| Combined live walk | PENDING — final acceptance 12-step walk @218-8 per plan R8 |

## §2 What PR-218-7 shipped

10 commits + 1 force-push cleanup (RED + GREEN + implementor self-iter + 2 QA-iter fixes + CI mock fixes). ~1500 LOC additions:

**New BE modules**
- `nikita/agents/onboarding/v2/phone_demo.py` — dispatch_phone_demo_call (consent INSERT + ElevenLabs outbound in same txn), handle_webhook_update (call.ended → status update), STATUS_ENDED_* constants, UNIQUE-violation accepted-forfeit per AC-003-005.
- `supabase/migrations/<NEW_TS>_phone_demo_calls.sql` — table + RLS (user SELECT own, service INSERT/UPDATE) + UNIQUE(user_id) lifetime cap + Realtime publication.

**Modified**
- `nikita/api/routes/voice.py` — Phase-7 piggyback: post_call_transcription webhook checks if conversation_id belongs to phone_demo_calls row first; updates row + cost_usd + status if so, then early-returns "processed" + phone_demo envelope. `_map_elevenlabs_termination` maps payload outcome to STATUS_ENDED_* (busy/no_answer/error/success).
- `nikita/api/routes/portal_onboarding_v2.py` — phone-demo opt-in endpoint wired to phone slot submission.

**New FE**
- `portal/src/app/onboarding/v2/phone_demo_modal.tsx` — shadcn AlertDialog "Want Nikita to call you for ~10s? [yes / skip]" default-focused skip.
- `portal/src/app/onboarding/v2/phone_demo_takeover.tsx` — full-screen "Nikita's calling…" + waveform. Supabase Realtime channel `phone_demo_calls:${userId}` (per-user scoped); 30-sec ceiling timeout; advance on call.ended/timeout.
- `portal/src/app/onboarding/v2/DynamicQuestion.tsx` — phone slot submission triggers opt-in modal post-persist.

**Tests** (~50 new tests)
- `tests/agents/onboarding/v2/test_phone_demo.py` — consent + idempotency + UNIQUE-violation tests.
- `tests/api/routes/test_phone_demo_endpoint.py` — endpoint behavior + parametrized webhook outcome mapping.
- `portal/src/__tests__/app/onboarding/v2/phone_demo_modal.test.tsx` + `phone_demo_takeover.test.tsx` — modal default-focus skip + Realtime dispatch + ceiling timer + End-early.

**Tests fix** (`tests/api/routes/test_voice_post_score.py`): autouse fixture stubs `phone_demo.handle_webhook_update → False` so existing boss/crisis tests fall through to scoring path.

**Scaffold**
- `specs/218-onboarding-wizard-v2-agent-driven/subspecs/7/slice.md` — lifecycle: living, cost-ceiling section noting $0.10/user enforcement via ElevenLabs prompt + DB UNIQUE constraint; hard call-duration cutoff deferred to ops monitoring.

**QA loop summary** (2 fresh-context iterations on PR #590 + 2 CI mock fixes):
- implementor self-iter-0 + iter-1: 6 findings, 5 fixed + 1 accepted (call_status hardcoded reasoning kept).
- fresh-context iter-1: 1 BUG (hardcoded ended_success) + 5 RISK + 1 CI Pytest fail (test_webhook_handles_unknown_user phone_demo MagicMock row truthy) → all fixed.
- fresh-context iter-2: 2 RISK (_call_data redundant alias + collapsed misleading warning) → fixed.
- CI mock follow-up: test_voice_post_score.py autouse fixture for phone_demo.handle_webhook_update.
- fresh-context iter-3: CLEAN 0 findings.

**CI**: Backend Pytest + E2E Tests + Lint+Type + Playwright E2E + Vercel all GREEN at final commit `595b7d1`.

## §3 Next Step: PR-218-8 (FINAL — atomic bulldoze + flag flip + supersession)

**Scope per plan §Slice sequencing PR-218-8 row** (~750 LOC, 1 session, atomicity required):

- Delete v1 wizard modules: `conversation_agent.py`, `converse_contracts.py`, `answer_contracts.py`, `agent_emission_state.py`, `sidecar_persistence.py` + 120 inbound refs across `nikita/`, `portal/src/`, `tests/`.
- Delete legacy FE: `portal/src/app/onboarding/onboarding-wizard-legacy.tsx` + `_components/{WizardShell, AgentSubspace, DeterministicTrack, NikitaReaction, IdentityPair, screen-config.ts, agent-view.ts}.tsx`.
- Delete HandlerHandoffAsk from `nikita/agents/onboarding/v2/envelope.py` + remove `case "handler_handoff"` from FE `DynamicQuestion.tsx`.
- Flip `wizard_v2_enabled` default `False → True` in `nikita/config/settings.py`.
- Mark Spec 217 superseded: `specs/217-onboarding-wizard-deterministic-redesign/spec.md` frontmatter `lifecycle: superseded` + `successor: 218`.
- Run `/roadmap sync` to update ROADMAP.md spec status.
- 14 v1 test files in `tests/onboarding/`, `tests/services/test_portal_onboarding.py`, etc. — deleted in this PR.

**Pre-merge verification gates**:
- `python3 -c "from nikita.api.routes.portal_onboarding import router"` succeeds in CI (import-integrity).
- `rg "conversation_agent|converse_contracts|answer_contracts|agent_emission_state|sidecar_persistence" nikita/ portal/src/ tests/` returns empty.
- Full `uv run pytest -q` green.

**Post-merge gate (R8 FINAL)**: FINAL ACCEPTANCE 12-step LIVE WALK per `.claude/rules/live-testing-protocol.md`. Plus-alias `youwontgetmyname777+walkFinal@gmail.com`. Pre-walk verify `wizard_v2_enabled=True` default applied + Cloud Run env synced.

**Split fallback**: If LOC > 750, split into 218-8a (production + tests deletion) + 218-8b (flag flip + supersession + ROADMAP) merged same-day to preserve atomicity.

## §4 Compaction-Safe Context Retrieval

```bash
# 1. Planning brief (locked)
cat ~/.claude/plans/immutable-wondering-gray.md

# 2. This handover
cat docs-to-process/20260513-handover-spec-218-PR7-shipped.md

# 3. Prior handovers
cat docs-to-process/20260512-handover-spec-218-PR6-shipped.md
cat docs-to-process/20260512-handover-spec-218-PR5-shipped.md

# 4. Slice scope docs
cat specs/218-onboarding-wizard-v2-agent-driven/subspecs/7/slice.md
ls specs/218-onboarding-wizard-v2-agent-driven/subspecs/

# 5. Bulldoze grep targets
rg -l "conversation_agent|converse_contracts|answer_contracts|agent_emission_state|sidecar_persistence" nikita/ portal/src/ tests/ | head -30

# 6. Current master state
git fetch origin && git log origin/master --oneline -10

# 7. Open PRs / issues
gh pr list --state open --limit 10
gh issue list --state open --limit 10
```

## §5 Operational Notes

- **Cloud Run rev**: `nikita-api-00313-cjt` serving 100%. Smoke: /health 200, /api/v1/health 200, /api/v1/converse/onboarding/retry 401, /api/v1/voice/webhook 401.
- **`wizard_v2_enabled` default still `False`** — production user traffic still on v1. PR-218-8 flips this default + bulldozes v1.
- **GH #581/#583/#584** — slice-218-2 R15 deferred risks. Address before launch.
- **/tmp/nikita-deploy-master was wiped between sessions** — re-cloned for this deploy. Going forward, deploy directly from main checkout via `rtk proxy bash -c 'gcloud run deploy nikita-api --source .'` works (avoids /tmp churn).

## §6 Outstanding Hygiene Items

| Item | Severity | Action |
|---|---|---|
| Task #41 — final live walk | LOW | Final acceptance walk post-218-8 |
| GH #578 — model_name test drift | MEDIUM | Standalone fix PR (pre-existing) |
| GH #581/#583/#584 — R15 retry budget | MEDIUM | Address before launch (not blocking 218-8) |
| Stale 217-* origin branches | LOW | Sweep post-PR-218-8 |
| Worktree orphans | LOW | `git worktree remove --force` sweep |
| 75+ untracked session artifacts | LOW | Hygiene PR per archive-policy.md |
| Spec 217 supersession marker | done@PR-218-8 | Bulldoze PR |

## §7 What Could Block Next Session

| Risk | Mitigation |
|---|---|
| RTK rewrites compound `cd` commands | `rtk proxy bash -c '...'` |
| GitHub SSH:22 blocked | `git -c "url.ssh://git@ssh.github.com:443/.insteadOf=git@github.com:" push` |
| Builder agents lack Bash | Drive verification + commit + push from orchestrator |
| Worktree already-checked-out | `git worktree remove -f -f <path>` |
| `git add -A` sweeps untracked | Always enumerate intended files in `git add <list>` |
| Bulldoze atomicity (PR-218-8) | All deletes + flag flip + supersession in ONE commit; if LOC overruns split 218-8a/8b same-day |
| Compaction loses Spec 218 context | This handover + §4 retrieval order |

## §8 Subagent Dispatch Manifest (slice 218-7)

| # | Agent | Phase | Outcome |
|---|---|---|---|
| 1 | executor-implement-verify (worktree) | RED+GREEN impl + self-review iter-0/1 | PR #590 opened, 1421/-1 LOC |
| 2 | caveman:cavecrew-reviewer | fresh-context iter-1 | 1 BUG + 5 RISK + 1 CI fail → fixed via builder agent |
| 3 | caveman:cavecrew-builder | iter-1 fix bundle | 6 fixes applied; orchestrator drove pytest/commit/push |
| 4 | (orchestrator-driven) | CI mock follow-up | test_voice_post_score autouse fixture |
| 5 | caveman:cavecrew-reviewer | fresh-context iter-2 | 2 RISK (alias + warning collapse) → fixed |
| 6 | caveman:cavecrew-reviewer | fresh-context iter-3 | CLEAN 0 findings |

Total: 6 dispatches.

## §9 Plan-rewrite Validity Check

LOC actual ~1500 vs plan estimate ~800. Drivers of overage:
- Phone-demo modal + takeover + Realtime subscription (~400 LOC FE).
- phone_demo.py dispatch + handle_webhook_update + idempotency (~250 LOC BE).
- Migration + RLS policies (~100 LOC).
- voice.py piggyback + `_map_elevenlabs_termination` helper (~150 LOC).
- Tests (~600 LOC).

LOC trend: 218-2 ~650, 218-3 ~600, 218-4 ~1600, 218-5 ~1100, precursor ~250, 218-6 ~1500, 218-7 ~1500. Cumulative ~7200. Slice 218-8 estimated ~750 deletes + atomic flag/supersession.

---

**Resume command for next session**: `cat ~/.claude/plans/immutable-wondering-gray.md && cat docs-to-process/20260513-handover-spec-218-PR7-shipped.md` → start FINAL slice 218-8 (atomic bulldoze) per §3.
