# Architecture Validation Report — Spec 214 (GATE 2 iter-2)

**Validator**: sdd-architecture-validator
**Spec**: `specs/214-portal-onboarding-wizard/spec.md` (amended 2026-04-19)
**Tech spec**: `specs/214-portal-onboarding-wizard/technical-spec.md`
**Iteration**: GATE 2 iter-2 (post-amendment regression check)
**Timestamp**: 2026-04-19
**Verdict**: **PASS**

## Scoreboard

| Severity | iter-1 | iter-2 | Δ |
|----------|--------|--------|---|
| CRITICAL | 0 | 0 | ±0 |
| HIGH     | 0 | 0 | ±0 |
| MEDIUM   | 5 | 1 | -4 (M1, M2, M3, M5 resolved; M4 still open; T-additions introduced **0** new MEDIUM) |
| LOW      | 6 | 5 | -1 (L3 explicitly resolved by `controls/` registry per tech-spec §3.1) |

**Pass bar**: 0 CRITICAL + 0 HIGH. Amendment **PASSES**.

## Summary

The amendment (T1-T7 additions resolving #350-#356, B1, B5, B6, M1-M7, S1-S9) preserves Clean Architecture boundaries and resolves 4 of 5 iter-1 MEDIUMs. The new `nikita/agents/onboarding/` package, the extension of `_handle_start_with_payload` with `BackgroundTasks`, the new `pg_cron nikita_handoff_greeting_backstop` job + task endpoint, and the two new tables (`llm_spend_ledger`, `llm_idempotency_cache`) all sit cleanly inside existing module homes with no backward dependencies. Tuning constants are correctly centralized in `nikita/onboarding/tuning.py` per `.claude/rules/tuning-constants.md` (M7 explicitly resolves with a 19-row constants table at §10). One MEDIUM (`ControlSelection` shape parity, M4 from iter-1) remains under-specified and should be pinned in `/plan`. No CRITICAL or HIGH regressions introduced by the amendment.

---

## iter-1 MEDIUM regression check

| iter-1 MEDIUM | Resolution status | Evidence in amended spec / tech-spec |
|---|---|---|
| **M1** — `__init__.py` export contract for `nikita/agents/onboarding/` | **PARTIALLY RESOLVED** | Tech-spec §2.1 line 52 shows `from nikita.agents.onboarding.conversation_agent import ConverseDeps` and §2.1 imports schemas via fully-qualified paths (no barrel re-exports). De facto the convention matches `nikita/agents/text/`. Recommend `/plan` codify this with a one-line note in the package CLAUDE.md. **Not blocking.** |
| **M2** — Confidence threshold 0.85 declarative | **RESOLVED** | Tech-spec §10 tuning constants table row `CONFIDENCE_CONFIRMATION_THRESHOLD = 0.85` in `nikita/onboarding/tuning.py`. Validation table §2.3 references it by name, not by literal. Spec also names `MIN_USER_AGE = 18`, `ONBOARDING_INPUT_MAX_CHARS = 500`, `NIKITA_REPLY_MAX_CHARS = 140`, `STRICTMODE_GUARD_MS = 50`, persona-drift constants. M7 explicitly addresses this. |
| **M3** — Handoff-greeting dispatch failure semantics | **RESOLVED** | AC-11e.3 (resolves #352, B1, B5) defines a 3-step durable dispatch: (1) atomic claim of `handoff_greeting_dispatched_at`, (2) `BackgroundTasks` send with [0.5s, 1s, 2s] retry, (3) clear `pending_handoff` only on confirmed send. Step 4 adds pg_cron backstop `nikita_handoff_greeting_backstop` every 60s. Step 5 (§2.5) defines stranded-user one-shot migration. Open question §10.4 still flags fallback copy choice but bind atomicity is **decided**. |
| **M4** — `ControlSelection` shape | **STILL OPEN** | Tech-spec §2.3 still references `Union[str, ControlSelection]` and §5.2 references `string \| ControlSelection` without defining the shape. Re-recorded as M4-iter2 below. **Not blocking** (one-line Pydantic model in `/plan`). |
| **M5** — Missing reducer actions | **RESOLVED** | Tech-spec §5.2 action union now lists 9 actions including `hydrate` (with `STRICTMODE_GUARD_MS` 50ms guard per AC-NR1b.2 + M3 mention), `timeout` (renders `source="fallback"` per AC-11d.9), `retry` (429 / transient path), `truncate_oldest` (NR-1b 100-turn cap), `clearPendingControl` (M2 / AC-11d.4b ghost-turn). Comments in the union explicitly cite resolved issues #355, M2, M3. |

**Net regression**: 0 MEDIUMs regressed; 4 of 5 resolved by amendment.

---

## New-additions architecture review (T1-T7)

### T1 — `nikita/agents/onboarding/` package (conversation_agent.py, extraction_schemas.py, conversation_prompts.py, handoff_greeting.py)

**Verdict**: CLEAN
- **Module home**: correct sibling of `nikita/agents/text/` and `nikita/agents/voice/`. Mirrors existing pattern from CLAUDE.md package overview.
- **Import direction**: tech-spec §2.1 imports `from nikita.agents.text.persona import NIKITA_PERSONA` (sideways within `agents/`, allowed) and `from nikita.config.settings import get_settings` (downward). No backward `agents → platforms` imports introduced. The legacy line in `nikita/agents/voice/scheduling.py:353` (`from nikita.platforms.telegram.bot import TelegramBot`) is pre-existing technical debt, NOT introduced or aggravated by this amendment.
- **Pydantic AI agent factory**: `get_conversation_agent() -> Agent[ConverseDeps, ConverseResult]` returns a typed agent with tool_plain registrations per topic. Stateless per call. Pattern matches `nikita/agents/text/agent.py`.
- **Persona reuse**: verbatim import of `NIKITA_PERSONA`. Spec §10 cross-references with persona-drift gates (TF-IDF cosine ≥ 0.70 + 3 feature ratios within ±15%) baked in across (text, conversation, handoff) per AC-11d.11 + AC-11e.4. Architectural protection against drift is in place.

### T2 — Extension of `nikita/api/routes/portal_onboarding.py` with `POST /onboarding/converse`

**Verdict**: CLEAN
- **Module home**: extension of existing route module (already houses `/preview-backstory`, `/profile`, `/profile/chosen-option`, `/pipeline-ready`). Co-locates with related portal-onboarding routes.
- **Dependency injection**: 6 DI providers via FastAPI `Depends(...)` — `get_authenticated_user`, `get_conversation_agent`, `get_converse_rate_limiter`, `get_converse_ip_rate_limiter`, `get_llm_spend_ledger`, `get_idempotency_store`. Each is a separate concern; no god-dependency.
- **Identity from JWT, not body**: `ConverseRequest` enforces `extra="forbid"` (AC-11d.3 + #350). `current_user.id` derived from `Depends(get_authenticated_user)`. Auth boundary is correctly drawn.
- **Authz on JSONB-path tool args**: AC-11d.3b adds 403 + `converse_authz_mismatch` event on cross-user tool argument tampering. New defensive layer; correctly scoped to the route handler.

### T3 — Extension of `nikita/onboarding/handoff.py::FirstMessageGenerator`

**Verdict**: CLEAN
- **Module home**: tech-spec §2.4 puts the new entrypoint at `nikita/agents/onboarding/handoff_greeting.py` (NEW), reusing/extending `FirstMessageGenerator` from `nikita/onboarding/handoff.py:133` with a `trigger="handoff_bind" | "first_user_message"` parameter. Pre-existing `FirstMessageGenerator` lives in `nikita/onboarding/` (Spec 213 PR 213-5); the new agent-side wrapper lives in `nikita/agents/onboarding/`. **Two homes raises a minor question** (resolvable in `/plan`): why does `handoff_greeting.py` go under `agents/onboarding/` when `handoff.py` already lives in `nikita/onboarding/`? Defensible — the agent-side wrapper does prompt construction + LLM dispatch (agent concern), while `handoff.py` is the orchestration layer. Worth a one-line CLAUDE.md note disambiguating.

### T4 — Extension of `nikita/platforms/telegram/commands.py::_handle_start_with_payload`

**Verdict**: CLEAN
- **Module home**: extension of existing handler. No new module; in-place change.
- **Background dispatch convention**: tech-spec §2.5 explicitly resolves B5 (background dispatch convention): use `BackgroundTasks` (not `asyncio.create_task`) for FastAPI route paths. Plumbs `background_tasks: BackgroundTasks` from the telegram webhook route at `nikita/api/routes/telegram.py:508`. Convention codified for future extensions.
- **Atomic one-shot semantics**: `UPDATE ... WHERE handoff_greeting_dispatched_at IS NULL AND pending_handoff = TRUE RETURNING id` claim pattern. Concurrent `/start <code>` produces rowcount==1 in one race winner only. AC-11e.3 + AC-11e.6 protect against double-dispatch and Q&A re-entry.

### T5 — pg_cron `nikita_handoff_greeting_backstop` + `POST /api/v1/tasks/retry-handoff-greetings`

**Verdict**: CLEAN
- **Module home**: tech-spec §2.5 step 5 places the new endpoint in `nikita/api/routes/tasks.py` (existing pg_cron task endpoints module). Bearer auth via `TASK_AUTH_SECRET` matches the 6 existing cron-job authentication pattern (per CLAUDE.md gotcha: hardcoded Bearer token in `net.http_post`).
- **Cadence + recovery semantics**: every 60s, looks for stranded rows `WHERE pending_handoff = TRUE AND telegram_id IS NOT NULL AND (handoff_greeting_dispatched_at IS NULL OR handoff_greeting_dispatched_at < now() - interval '30 seconds')`. Tuning constants `HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC = 60` and `HANDOFF_GREETING_STALE_AFTER_SEC = 30` named per `.claude/rules/tuning-constants.md`. Properly architected as a separate concern from the request-path dispatch.
- **One-shot migration**: `scripts/handoff_stranded_migration.py` for legacy stranded users at deploy cutover. Standalone script; doesn't pollute the runtime path.

### T6 — `llm_spend_ledger` + `llm_idempotency_cache` tables

**Verdict**: CLEAN
- **DDL hygiene**: both tables (tech-spec §4.3a / §4.3b) include `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY admin_and_service_role_only` (consistent with `.claude/rules/testing.md` "DB Migration Checklist" — RLS completeness on every new table). `WITH CHECK` clauses present on both UPDATE-capable policies.
- **Indexes**: appropriate (`idx_llm_idempotency_cache_created` for prune-by-age, `idx_llm_spend_ledger_day` for daily rollover).
- **TTL via pg_cron**: `llm_idempotency_cache_prune` hourly (5-min TTL) + `llm_spend_ledger_rollover` daily (30-day window). Both follow the existing pg_cron task pattern.
- **CASCADE on user delete**: both have `ON DELETE CASCADE` from `users(id)`. Correct GDPR coupling per AC-NR1b.4b.

### T7 — Tuning constants in `nikita/onboarding/tuning.py`

**Verdict**: CLEAN
- Tech-spec §10 lists 19 named `Final[int|float]` constants with rationale comments per `.claude/rules/tuning-constants.md`. Examples: `CONVERSE_TIMEOUT_MS = 2500`, `CONVERSE_PER_USER_RPM = 20`, `CONVERSE_DAILY_LLM_CAP_USD = 2.00`, `CONFIDENCE_CONFIRMATION_THRESHOLD = 0.85`, `STRICTMODE_GUARD_MS = 50`, `HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC = 60`, `PERSONA_DRIFT_COSINE_MIN = 0.70`. All in one home; no scattered literals.
- M7 explicitly resolved.

---

## Findings (iter-2)

### MEDIUM (1 carried over from iter-1, not regressed)

#### M4-iter2 — `ControlSelection` shape still undefined (carried from iter-1 M4)
**Location**: tech-spec §2.3 `user_input: Union[str, ControlSelection]`; §5.2 TS action `user_input: string | ControlSelection`
**Issue**: `ControlSelection` referenced on both Python and TypeScript sides but shape undefined in either spec. The dispatcher in `controls/InlineControl.tsx` and the agent-input builder in `converse` will drift without a pinned type.
**Recommendation**: in `/plan`, define a shared shape:
```python
class ControlSelection(BaseModel):
    control_type: Literal["chips","slider","toggle","cards","text"]
    value: str | int           # slider=int 1-5, others=str
    field: str                 # e.g. "location_city", "social_scene"
```
Plus its TS mirror. Add a parity test that round-trips a Python `ControlSelection` through JSON to TS and back. Not blocking — same status as iter-1.

### LOW (5 of 6 carried; L3 explicitly resolved)

L3 from iter-1 ("Portal chat dispatcher risk") is explicitly resolved by tech-spec §3.1: `InlineControl.tsx` is now a "slim dispatcher (~30 LOC, resolves #355)" that "reads `next_prompt_type` from a `controls/` registry" — exactly the registry-lookup pattern recommended in iter-1.

L1 (PII concat regex), L2 (persona-drift edit guardrail), L4 (PR 3 without PR 4 ceremony), L5 (`TelegramAuth` caller audit list — partially addressed by AC-11c.10b which now requires the audit in the PR description), L6 (localStorage PII acknowledgement) all carry over without amendment regression.

### NEW MEDIUM/HIGH/CRITICAL from amendment

**None.** The amendment introduces no new architectural blockers. Two minor watchpoints that should be confirmed in `/plan` (not findings, just observations):

1. **Two homes for handoff-greeting code** (`nikita/onboarding/handoff.py` legacy + `nikita/agents/onboarding/handoff_greeting.py` new) — defensible split (orchestration vs LLM dispatch) but should get a one-line CLAUDE.md note.
2. **Tuning constants location split** — most live in `nikita/onboarding/tuning.py`; iter-1 M2 recommended `nikita/agents/onboarding/constants.py` for the confidence threshold. Tech-spec §10 puts them all in `nikita/onboarding/tuning.py` instead, which is a defensible choice (one home for all onboarding constants) and aligns with M7 resolution. **No conflict; the iter-1 recommendation is one of two valid placements.**

---

## Architectural strengths confirmed by amendment

1. **Backward-dep audit clean**: no `nikita/agents/onboarding/` imports from `nikita/platforms/`. The only `agents → platforms` import in the codebase is the pre-existing `nikita/agents/voice/scheduling.py:353` line; not affected.
2. **Type safety end-to-end**: `ConverseRequest` (Pydantic, `extra="forbid"`), `ConverseResponse` (Pydantic, validated), 6 extraction schemas (Pydantic with `Field(ge=…, le=…, pattern=…)`), TS mirrors via `OnboardingProfile` types. No raw dicts on contract surfaces.
3. **Error handling architecture sound**: timeout → fallback (AC-11d.9, `source="fallback"`); validator reject → fallback; injection attempts → fallback + structured event (`converse_input_reject`, `converse_output_leak`, `converse_authz_mismatch`, `converse_tone_reject`). Never raises 500 to client per spec.
4. **Tuning constants per project rule**: 19 named `Final` constants with rationale, in one module. Regression-guard tests implied by §10 table.
5. **Independent revertability per PR**: PRs 1-5 each independently revertable per tech-spec §8.2. Feature flag `USE_LEGACY_FORM_WIZARD` gates the chat wizard rollout per S1.
6. **DB hygiene**: both new tables have RLS + WITH CHECK + indexes + TTL pg_cron + CASCADE on user delete.

---

## Verdict

**PASS** (0 CRITICAL + 0 HIGH).

The Spec 214 amendment (FR-11c, FR-11d, FR-11e, NR-1b) is architecturally sound. T1-T7 additions preserve Clean Architecture boundaries, resolve 4 of 5 iter-1 MEDIUMs (M1 partial, M2/M3/M5 fully), and introduce zero new MEDIUM/HIGH/CRITICAL findings. The remaining iter-1 MEDIUM (M4 — `ControlSelection` shape) is non-blocking and pins in `/plan`. Recommend proceeding to Phase 5 (planning) with M4-iter2 flagged as a plan-phase input.
