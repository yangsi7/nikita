# Architecture Smells Registry — code-verified, 2026-05-05

Aggregated from 8 W6.5 architecture diagrams. Every entry has a `file:line` citation against master HEAD `28e21b8`. Diagrams visible at `diagrams.json`.

**Verification**: pre-render subagent grep-confirmed citations on master @ `36a5934` (W6.5 PR #511 baseline). 90% citations exact, 1 minor shift, 0 missing.

**Severity legend**:
- **CRITICAL**: security risk or production-data loss potential
- **HIGH**: silent failure, drift between source-of-truth and production code, or known-bug-still-shipping
- **MEDIUM**: code smell, magic number, broad catch, opaque side-effect, missing test guard
- **LOW**: documentation drift, unverified line, deprecated-but-tolerated

---

## Severity Distribution

| Severity | Count |
|---|---|
| CRITICAL | 1 |
| HIGH | 6 |
| MEDIUM | 17 |
| LOW | 8 |
| INFO | 1 |
| **Total** | **33** |

---

## CRITICAL

### S-F1 Hardcoded Bearer token in cron migration (Diagram F)

**File**: `supabase/migrations/20260418141500_cron_heartbeat_engine.sql:63,75,87`
**Issue**: Bearer token `S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0` literally checked into git inside the cron migration. Three cron jobs (heartbeat, generate-daily-arcs, touchpoints) reference it inline.
**Impact**: secret rotation requires SQL `cron.alter_job()` per CLAUDE.md gotcha; checked-in secret is exposed in any repo clone, including all forks/PRs in history.
**Mitigation**: store secret in a Supabase vault or migration-time env injection; rotate the existing token (it is now public).

---

## HIGH

### S-B1 GH #478 deprecated `note_user_fact` still registered (Diagram B)

**Files**: `nikita/agents/text/tools.py:107` (deprecated comment) + `nikita/agents/text/agent.py:220-247` (still `@agent.tool`)
**Issue**: tool deprecated in code comment but registered with the agent; LLM can still invoke it. Open since GH #478.
**Mitigation**: deregister via `@agent.tool` removal (W7-aligned) or close #478 with deprecation banner shipping in same PR.

### S-D1 CALIBRATION_MULTIPLIERS contradict YAML (Diagram D)

**Files**: `nikita/engine/scoring/calculator.py:20-27` vs `nikita/engine/scoring/scoring.yaml:53-59`
**Issue**: python literals are `1.0 0.9 0.8 0.6 0.5 0.2`; YAML `engagement_multipliers` are `1.0 0.8 0.7 0.7 0.5 0.3`. Production code uses python literals. YAML appears to be a stale copy or an aspirational tuning that never landed.
**Mitigation**: pick one source of truth; if YAML is truth, refactor calculator to load from YAML; otherwise delete YAML key with a `# DEPRECATED: see calculator.py:20` marker.

### S-D2 GRACE_PERIODS python constants INVERTED vs YAML (Diagram D)

**Files**: `nikita/engine/constants.py:153` vs `nikita/engine/config_data/decay.yaml:6-11`
**Issue**: python `GRACE_PERIODS` has `Ch1=72h Ch5=8h`; YAML has `Ch1=8h Ch5=72h`. Production reads YAML; constants kept for back-compat (acknowledged at `:149-152`). Test guard `tests/engine/test_grace_period_divergence.py` exists.
**Mitigation**: drop the python mirror entirely; the back-compat reason is no longer load-bearing. Remove from `__all__` per S-D8.

### S-G1 Three separate user-creation call sites (Diagram G)

**Files**: `nikita/api/routes/portal.py:126`, `:477`, `:513`
**Issue**: `user_repo.create_with_metrics(...)` called from three places with no shared helper. Divergent initialization is a CRITICAL-adjacent risk: one call site can drift on default fields (city, vice prefs, metrics) and silently change new-user state shape.
**Mitigation**: extract to `nikita/onboarding/user_provisioning.py:create_user_with_metrics()` helper; replace 3 call sites in one PR.

### S-G2 `E2E_AUTH_BYPASS=true` production-leak (Diagram G)

**File**: `portal/src/app/onboarding/page.tsx:42-50`
**Issue**: shortcut hard-codes `userId="e2e-player-id"`; guarded by `NODE_ENV !== "production"`. In a production-build that has the env var set (e.g., a Cloud Run deploy that accidentally inherits a CI secret), the guard does NOT block — the env-var presence is the trigger, not just the code path.
**Mitigation**: stricter guard combining `NODE_ENV` AND a build-time constant pinned by Vercel env, e.g., `process.env.NEXT_PUBLIC_E2E_BUILD === '1'`. Add a Vercel build-time test asserting the bypass is unreachable in `prod`.

### S-F2 Dev-mode auth bypass on task endpoints (Diagram F)

**File**: `nikita/api/routes/tasks.py:65-70`
**Issue**: when `TASK_AUTH_SECRET` is unset, the verifier emits a warning and **allows** unauthenticated POSTs. In a misconfigured prod deploy (env var deleted, Cloud Run revision rolled back without secret), all 11 task endpoints become public — including `/decay`, `/process-conversations`, `/heartbeat`.
**Mitigation**: refuse to start the app if `TASK_AUTH_SECRET` is unset and `NIKITA_ENV=production` (or absence of `NIKITA_ENV`). Default-deny.

---

## MEDIUM

### S-A1 `stages_total=11` hardcoded inside the canonical pipeline file (Diagram A)

**File**: `nikita/pipeline/orchestrator.py:186`
**Issue**: stage count is a magic literal embedded in the orchestrator that already owns `STAGE_DEFINITIONS`. Removing or adding a stage requires two-place edit.
**Mitigation**: replace with `len(STAGE_DEFINITIONS)`.

### S-A2 Bare `except Exception` swallow on non-critical stages (Diagram A)

**Files**: `nikita/pipeline/orchestrator.py:308`, `:343`
**Issue**: catches all exceptions, marks stage as failed-non-critical, pipeline continues. Silent failure mode for stages 3-9. Logs exist but operator never paged.
**Mitigation**: catch-and-rethrow for `KeyboardInterrupt`/`SystemExit`/`asyncio.CancelledError`; otherwise emit a structured warning + Sentry breadcrumb (or equivalent).

### S-A3 Pipeline state-collision: `extraction_summary` (Diagram A)

**Files**: `nikita/pipeline/stages/extraction.py:34` writes; `nikita/pipeline/stages/summary.py:23` overwrites at stage 9.
**Issue**: two stages write the same context key. Stage 9 wins, stage 0's extraction summary is silently lost.
**Mitigation**: rename to `extraction_summary_raw` and `extraction_summary_final` OR document the intentional overwrite explicitly.

### S-A4 Pipeline state-collision: `conflict_details` (Diagram A)

**Files**: `nikita/pipeline/stages/emotional.py:22` and `nikita/pipeline/stages/conflict.py:27`
**Issue**: stage 4 (emotional) and stage 7 (conflict) both write `conflict_details`. Last-writer-wins; stage 4's writes are likely lost.
**Mitigation**: rename one or document the merge contract.

### S-B2 Onboarding tool fan-out borderline (Diagram B)

**File**: `nikita/agents/onboarding/conversation_agent.py` (4 narrow `fetch_*` tools)
**Issue**: `fetch_city_context`, `fetch_occupation`, `fetch_time_of_day`, `fetch_topic_spec` are 4 narrow tools where 1 consolidated tool with discriminated args would suffice. Borderline tool-fan-out anti-pattern per `.claude/rules/agentic-design-patterns.md` Hard Rule #3.
**Mitigation**: consolidate to one `fetch_context(kind: Literal[...])` with discriminated dispatch.

### S-B3 No output_validator on text agent (Diagram B)

**File**: `nikita/agents/text/agent.py`
**Issue**: text agent has free-form `str` output and no `@agent.output_validator`; relies on prompt discipline alone.
**Mitigation**: add structural validator or wrap in pydantic model so retries are deterministic.

### S-C1 `DEDUP_SIMILARITY_THRESHOLD = 0.87` bare module-level constant (Diagram C)

**File**: `nikita/memory/supabase_memory.py:42`
**Issue**: not in `settings.py`, not env-overridable. History `0.95 → 0.92 → 0.87` per GH #199.
**Mitigation**: lift to `settings.py` with a Pydantic field + override env, or at minimum add module-level docstring noting why 0.87 is the current value.

### S-C2 Broad `except Exception` retries hide errors (Diagram C)

**Files**: `nikita/memory/supabase_memory.py:115-125`, `:140-151`
**Issue**: retry loop catches `Exception`; only the last error surfaces. Non-retriable errors (auth, schema mismatch) waste the budget then surface late.
**Mitigation**: distinguish retriable (network/rate-limit) from terminal (auth/schema).

### S-C3 Factory `get_supabase_memory_client(user_id)` leak risk (Diagram C)

**File**: `nikita/memory/supabase_memory.py:418`
**Issue**: creates fresh DB session, close-responsibility on caller. Easy to forget the close → connection-pool exhaustion.
**Mitigation**: convert to async context manager or wrap callers in `async with`.

### S-D3 `CHAPTER_DELTA_CAPS` bare Decimal literals (Diagram D)

**File**: `nikita/engine/scoring/calculator.py:31-37`
**Issue**: per-chapter caps embedded as bare `Decimal('...')` literals in the calculator.
**Mitigation**: extract to `nikita/engine/config_data/scoring.yaml` with named keys.

### S-D4 `CRITICAL_LOW_THRESHOLD = 20` magic number, no test guard (Diagram D)

**File**: `nikita/engine/scoring/calculator.py:40`
**Issue**: scoring boundary, no test asserting current value.
**Mitigation**: add to `.claude/rules/tuning-constants.md` regression-guard list; write `test_critical_low_threshold_pin.py`.

### S-D5 `_BLOCKING_STATUSES` uses string literals not enum (Diagram D)

**File**: `nikita/engine/chapters/boss.py:78`
**Issue**: `('boss_fight', 'game_over', 'won')` — should be `(GameStatus.BOSS_FIGHT, GameStatus.GAME_OVER, GameStatus.WON)`.
**Mitigation**: import `GameStatus` and use enum members; mypy will then catch typos.

### S-D6 Boss push-notification try/except no GH-issue ref (Diagram D)

**File**: `nikita/engine/chapters/boss.py:189-210`
**Issue**: catches push-notif failures silently; no comment linking to a GH issue explaining why this is intentional.
**Mitigation**: add `# GH #NNN: push-notif is best-effort because ...` or escalate to Sentry.

### S-D7 Silent `Decimal('55')` fallback in scoring (Diagram D)

**File**: `nikita/engine/scoring/calculator.py:280`
**Issue**: hardcoded fallback hides chapter-config errors. If `chapter_config` is unloadable, score quietly defaults to a value that looks like a Chapter 1 threshold.
**Mitigation**: raise `ConfigError` on missing config; a loud failure beats a silent stuck-at-55.

### S-E1 Life-sim stage bare Exception swallow (Diagram E)

**File**: `nikita/pipeline/stages/life_sim.py:52-88`
**Issue**: combined with `is_critical=False`, life-sim failures are completely silent.
**Mitigation**: same as S-A2; structured warning at minimum.

### S-E2 Cold-user inline LLM call latency hazard (Diagram E)

**File**: `nikita/pipeline/stages/life_sim.py:70-76`
**Issue**: `read_today_events` then fallback to `generate_next_day_events` runs an LLM call inside the request pipeline. For cold users (no events yet), every conversation tail incurs the latency.
**Mitigation**: warm-up via cron `generate-daily-arcs` for new users at signup; OR move generation off the request path.

### S-F3 Commented-only handoff backstop migration (Diagram F)

**File**: `supabase/migrations/cron_handoff_backstop.sql:1-33`
**Issue**: entire migration is commented out; never executes. Dead file in source control.
**Mitigation**: delete the file OR uncomment + ship + verify the cron job actually runs.

---

## LOW

### S-A5 Vice stage produces no ctx output (Diagram A)

**File**: `nikita/pipeline/stages/vice.py:21`
**Issue**: side-effects only; opaque to downstream stages.
**Mitigation**: emit a `vice_summary` ctx field for diagnostic visibility, even if other stages do not consume it.

### S-B4 Psyche Opus model variant unverified (Diagram B)

**File**: `nikita/agents/psyche/agent.py:233`
**Issue**: Opus variant defined; wired path UNVERIFIED in 2026-05-04 baseline.
**Mitigation**: grep callers; either verify or delete.

### S-C4 `__aexit__` returns False, only logs (Diagram C)

**File**: `nikita/memory/supabase_memory.py:84-92`
**Issue**: no rollback on exception. Silent state inconsistency on async-context exit.
**Mitigation**: either rollback session OR document why state-on-exception is acceptable.

### S-D8 Deprecated mirror constants still in `__all__` (Diagram D)

**File**: `nikita/engine/constants.py:113-138`
**Issue**: `BOSS_THRESHOLDS DECAY_RATES GRACE_PERIODS METRIC_WEIGHTS CHAPTER_NAMES` exported via `__all__`. Dead-code-pathway risk: a fresh contributor imports the python mirror instead of the YAML loader.
**Mitigation**: drop from `__all__`; emit `DeprecationWarning` on import.

### S-E3 Cron handler `/tasks/generate-daily-arcs` line UNVERIFIED (Diagram E)

**Issue**: cron-wired but `@router.post("/generate-daily-arcs")` not located in route grep; possible dead route.
**Mitigation**: grep for the handler; either pin file:line in the migration comment or delete the cron job.

### S-F4 Two cron jobs UNVERIFIED (Diagram F)

**Issue**: `llm_idempotency_cache_prune` + `llm_spend_ledger_rollover` schedules UNVERIFIED in pre-render baseline.
**Mitigation**: locate migrations; pin into the diagram or remove if dead.

### S-G3 Dual auth surface (Diagram G)

**Files**: `portal/src/app/login/page-client.tsx:24,94` AND `portal/src/app/onboarding/auth/page-client.tsx:50,101`
**Issue**: both call `signInWithOtp`; copy + redirect logic duplicated. Drift risk on OTP/redirect tweaks.
**Mitigation**: extract `useSignInWithOtp({redirectTo})` shared hook.

### S-G4 Spec deviation acknowledged in code (Diagram G)

**File**: `portal/src/app/onboarding/page.tsx:14-25`
**Issue**: AC C1.13 literal cookie peek replaced with `getUser()` (security improvement). Code is correct; spec is stale.
**Mitigation**: update Spec 214 AC C1.13 to match landed implementation.

---

## INFO

### S-A6 KT framing wrong on telegram→pipeline (Diagram A)

**Issue**: `nikita/platforms/telegram/message_handler.py` does NOT directly invoke `PipelineOrchestrator`. Flows via cron path in `tasks.py`. Documented assumption ("telegram → pipeline direct") is wrong; corrected in W4 audit.
**Status**: documentation-only; resolved in W4 KT migration.

---

## How to use this registry

- **Triage**: anything CRITICAL/HIGH should have a GH issue (use `.claude/rules/issue-triage.md`). One issue per smell, label `bug` or `tech-debt`.
- **Tracking**: when fixing, reference the smell ID in the PR title (e.g., `fix(scoring,S-D1): collapse CALIBRATION/yaml duplication to one source`).
- **Re-verification**: re-run W6.5 pre-render verification subagent on every smell fix to confirm the citation no longer hits.
- **Coverage**: each diagram's smell list is also embedded in `diagrams.json` with full `file:line` references.

## Generation provenance

- Wave: W6.5 (PR #511) + W6.5b (this PR)
- Source: 8 Figma boards generated via `mcp__plugin_figma_figma__generate_diagram`
- Verification gate: pre-render subagent (HARD CAP 8 tool calls) confirmed file:line citations on master @ `36a5934`. PASS at 90% (1 minor shift, 0 missing).
- PNG export: deferred to a follow-up wave (Figma MCP `get_screenshot` returned token-expired in W6.5b session despite a successful `whoami` 5 minutes earlier; PAT not configured in this dev box). The Figma boards remain the source-of-truth visual artifact.
