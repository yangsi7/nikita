# Testing Validation Report — Spec 214 GATE 2 iter-2

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/214-portal-onboarding-wizard/spec.md` + `technical-spec.md`
**Iteration:** GATE 2 iter-2 (post-T7 amendments)
**Status:** **PASS**
**Timestamp:** 2026-04-19T14:30:00Z
**Validator:** sdd-testing-validator
**Prior iteration:** iter-1 found 0 CRIT + 3 HIGH (H16/H17/H18). All three resolutions verified below.

---

## Summary Scoreboard

| Severity | Count | Verdict |
|----------|-------|---------|
| CRITICAL | 0 | PASS |
| HIGH     | 0 | PASS |
| MEDIUM   | 2 | accept/defer (non-blocking) |
| LOW      | 3 | logged (non-blocking) |

**Pass criteria:** 0 CRITICAL + 0 HIGH → **PASS**.

---

## iter-1 Resolution Verification

| iter-1 Finding | Resolution Claim | Verification | Status |
|----------------|------------------|--------------|--------|
| **H16** persona-drift ≥80% non-falsifiable | TF-IDF cosine ≥0.70 + 3 feature ratios ±15%, temp 0.0, N=20 averaged | spec.md:751 (AC-11d.11) defines TWO conjunctive gates: (a) cosine ≥`PERSONA_DRIFT_COSINE_MIN`(0.70); (b) three feature ratios — mean-sentence-length, lowercase-character-ratio, canonical-phrase-count — each within ±0.15. Temperature 0.0, N=20 samples per seed, baseline CSV at `tests/fixtures/persona_baseline_v1.csv` PINNED. ADR `decisions/ADR-001-persona-drift-baseline.md` documents regen process. AC-11e.4 extends to pairwise (main-text↔conversation↔handoff). Test "fails loudly with the specific feature + measured delta." | **RESOLVED** |
| **H17** 5 edge-case ACs unit-only | 4 `@edge-case` Playwright scenarios added | spec.md:755 (AC-11d.13b) defines 4 walks: (a) Fix-that ghost-turn opacity assertion; (b) 2500ms timeout asserts `data-source="fallback"` DOM attr; (c) backtracking "change my city to Berlin" with later-fields-survive assertion; (d) age<18 in-character (NO red banner, control re-renders pre-filled, wizard does not advance). Tagged `@edge-case`, isolatable via `playwright test --grep @edge-case`. | **RESOLVED** |
| **H18** pre-PR grep gates absent | New Pre-PR Gates subsection references 3 grep commands from `.claude/rules/testing.md` | spec.md:798-806 (Pre-PR Gates section) + technical-spec.md:625-630 (§7.5 Pre-PR Gates) BOTH reference the 3 gates from `.claude/rules/testing.md`: zero-assertion shells, PII leakage in logs (`name|age|occupation|phone`), raw `cache_key` in logs (require `cache_key_hash`/`sha256`). Enforced locally (pre-push hook) AND CI. Non-empty output blocks merge. | **RESOLVED** |

All three iter-1 HIGH findings are **RESOLVED**. No regression in adjacent surface area.

---

## Coverage Inventory of Required Additions

| Requirement (from validation directives) | AC Reference | Status |
|------------------------------------------|--------------|--------|
| Test pyramid 70-20-10 compliance | spec §Verification per FR + technical-spec §7.1-7.4 | PASS — backend unit (~70%), portal unit + integration (~20%), Playwright @edge-case + happy-path (~10%) |
| TDD enablement: every AC has falsifiable test | All AC-11c/d/e + AC-NR1b have explicit `Test:` clauses | PASS — spot-checked AC-11c.1-12, AC-11d.1-13c, AC-11e.1-6, AC-NR1b.1-5 |
| Coverage targets ≥80% on new agent + endpoint + UI | spec §NFR-005 | PARTIAL — pre-existing NFR-005 covers WizardStateMachine (≥85%), step components (≥70%), `useOnboardingPipelineReady` (≥80%). New Conversation Agent / `/converse` endpoint / ChatShell coverage thresholds NOT explicitly stated. → **MEDIUM finding M-T1** |
| Onboarding-appropriate tone fixtures (20, Gemini-judged) per S3 | AC-11d.5e (spec.md:742) | PASS — `tests/fixtures/onboarding_tone_fixtures.yaml`, 20 fixtures, Gemini-judged via `mcp__gemini__gemini-structured`, CI gate ≥18/20 pass |
| Tool-use edge-case fixtures (0 calls, ≥2 calls, None field, invalid format) per S5 | technical-spec.md:179, §2.3 Validation rules table (lines 210-213) | PASS — table enumerates: (a) 0 tool calls → off-topic reprompt; (b) ≥2 → priority-order first only + `converse_multi_toolcall_warn`; (c) required field None → reject + `confirmation_required=true`; (d) format violation (age non-int / location_cache_key regex fail) → reject + fallback. Test surface enumerated in `tests/api/routes/test_converse_endpoint.py` (technical-spec.md:580). |
| OWASP LLM01 jailbreak fixtures (≥20) per T2 | AC-11d.5b + AC-11d.5d (spec.md:739, 741) | PASS — `tests/fixtures/jailbreak_patterns.yaml` with ≥20 fixtures: prompt-reveal, role-override, delimiter-injection (`<\|im_start\|>`, `[INST]`), base64, multilingual (DE/FR/CN), tool-misuse, PII-exfiltration. Each fixture asserts fallback, never raw LLM-compliant answer. |
| E2E conversation-coherence Gemini-judge per devil #15 | NOT FOUND | NOT ADDRESSED — only TONE Gemini-judge (AC-11d.5e) exists. No multi-turn coherence judge in Playwright suite. → **MEDIUM finding M-T2** (defer-acceptable: tone + persona-drift + extraction-fidelity are 3 lenses already; coherence is incremental polish) |
| Persona-drift baseline CSV pinning + ADR for regen per M1 | AC-11d.11 (spec.md:751) | PASS — `tests/fixtures/persona_baseline_v1.csv` pinned; `decisions/ADR-001-persona-drift-baseline.md` documents bump trigger ("whenever persona.py changes meaningfully") |
| llm_spend_ledger pg_cron daily reset test | AC-11d.3d (spec.md:734) + technical-spec.md:472-476 | PASS — pg_cron `llm_spend_ledger_rollover` at 00:05 UTC documented; tests assert: (a) 200th high-token turn returns 429 BEFORE agent invocation; (b) end-of-day query returns per-user row with non-zero spend. NOTE: explicit cron-job re-trigger smoke test is implicit; see L-T2. |

---

## Testing Pyramid Analysis

| Layer | Target | Spec Coverage |
|-------|--------|---------------|
| **Unit** (~70%) | Conversation agent, extraction schemas, validators, reducers, control components | technical-spec.md:577-596 enumerates 8 backend unit files + 8 portal unit files. Confidence threshold, off-topic, backtracking, in-character validation, persona-drift, tone-filter, jailbreak fixtures all unit-tested. **PASS** |
| **Integration** (~20%) | DB JSONB persistence, RLS, idempotency cache, ledger, handoff boundary | tech-spec.md:584 (`test_onboarding_profile_conversation.py`) + 595 (`test_handoff_boundary.py`) + AC-11d.10 / AC-11d.3c / AC-11d.3d / AC-11e.3 mandate integration tests. **PASS** |
| **E2E** (~10%) | Full chat walk + 4 @edge-case scenarios + 2 live dogfood walks | tech-spec.md:600-616 enumerates 11-step happy walk + 4 @edge-case suite. AC-11d.13b carves @edge-case grep-isolatable. **PASS** |

Pyramid balance is appropriate for an LLM-driven feature. E2E weight is intentionally larger than typical because LLM determinism cannot be unit-asserted.

---

## AC Testability Analysis (SMART)

Spot-checked 12 ACs across FR-11c / FR-11d / FR-11e and NR-1b. ALL contain explicit `Test:` clauses with falsifiable assertions:

| AC | S | M | A | R | Notes |
|----|---|---|---|---|-------|
| AC-11d.3 | Y | Y | Y | Y | 422 on rogue body user_id; mocked-agent happy path |
| AC-11d.3b | Y | Y | Y | Y | Seeded prompt-injection → 403 + generic body + 1 security event |
| AC-11d.3c | Y | Y | Y | Y | Replay within 5min → cached body + agent-call-count == 1 |
| AC-11d.3d | Y | Y | Y | Y | 199 high-token turns → 200th 429 BEFORE agent |
| AC-11d.5 | Y | Y | Y | Y | Two-layer: agent text + server-side hard-block |
| AC-11d.5b | Y | Y | Y | Y | 20 jailbreak fixtures, each asserts fallback |
| AC-11d.5e | Y | Y | Y | Y | Gemini-judge ≥18/20 + ONBOARDING_FORBIDDEN_PHRASES list |
| AC-11d.10b | Y | Y | Y | Y | 100 fixture turns → ≤30 MessageBubble nodes at any offset |
| AC-11d.11 | Y | Y | Y | Y | TF-IDF cosine ≥0.70 + 3 feature ratios ±15% — fails loudly with delta |
| AC-11d.12b | Y | Y | Y | Y | aria-live scoped to ChatShell only; sr-only sibling carries final text |
| AC-11d.13b | Y | Y | Y | Y | 4 @edge-case Playwright walks, grep-isolatable |
| AC-11e.3 | Y | Y | Y | Y | Concurrent /start <code> → rowcount==1/0 split; instance-crash injection → backstop fires within 90s |

All passed SMART. **PASS**.

---

## TDD Readiness Checklist

- [x] ACs are specific (named files, named patterns, named tolerances)
- [x] ACs are measurable (numeric thresholds: 0.70, 0.85, 0.15, 2500ms, 5min, 90s, ≥18/20, ≥20 fixtures)
- [x] Test types clear per AC (unit / integration / E2E / live dogfood explicitly tagged)
- [x] Red-green-refactor path clear (failing test pre-implementation → minimal code → passing → refactor)
- [x] Pre-PR Gates enforced both locally + CI (zero-assertion shells, PII-in-logs, raw cache_key) — spec.md:798-806

---

## Findings

### MEDIUM (non-blocking, accept/defer)

| ID | Category | Issue | Location | Recommendation |
|----|----------|-------|----------|----------------|
| **M-T1** | Coverage targets | NFR-005 lists portal step-component coverage thresholds but does NOT specify thresholds for the NEW backend Conversation Agent (`nikita/agents/onboarding/conversation_agent.py`), `/converse` endpoint route, or new portal components (`ChatShell`, `MessageBubble`, `InlineControl`, `ClearanceGrantedCeremony`). | spec.md:934-939 (NFR-005) | Append to NFR-005: "ConversationAgent + extraction_schemas: ≥85% line coverage (mocked LLM); /converse route: ≥85% branch coverage; ChatShell + MessageBubble + InlineControl + ClearanceGrantedCeremony: ≥75% line coverage." Accept-or-defer: GH issue + accept for iter-2 (coverage gap surfaces in PR review, non-blocking). |
| **M-T2** | E2E coherence | Devil #15 requested an E2E conversation-coherence Gemini-judge ("does the chat make sense end-to-end?"); spec includes per-message tone judge (AC-11d.5e) and persona-drift (AC-11d.11) but no multi-turn coherence judge. | spec.md gap | Defer-acceptable. Tone + persona-drift + extraction-fidelity (20 fixtures via tool-use) already triangulate quality from 3 angles. Recommend GH issue tagged `enhancement` for post-PR-3 measurement: 10 simulated full-walk transcripts → Gemini-judged on "does conversation flow coherently" with rubric. Add to Phase B measurement script (technical-spec.md:640). |

### LOW (logged, non-blocking)

| ID | Category | Issue | Location | Recommendation |
|----|----------|-------|----------|----------------|
| **L-T1** | Test fixture seeding | Persona-drift baseline (`persona_baseline_v1.csv`) is generated from main-text-agent samples. Spec does not explicitly state WHO generates the initial CSV (CI auto-seed vs. local one-shot script vs. manual paste). Implicit risk: first PR cannot run AC-11d.11 if baseline missing. | AC-11d.11 + ADR-001 | Add to ADR-001: "Initial baseline generated via `scripts/persona_baseline_seed.py` against main-text-agent at PR-2 implementation time; committed to repo before PR-2 opens." |
| **L-T2** | pg_cron smoke test | `llm_spend_ledger_rollover` (00:05 UTC) and `llm_idempotency_cache_prune` (hourly) and `nikita_handoff_greeting_backstop` (60s) are all pg_cron jobs. AC-11d.3d tests the LEDGER write but not the cron trigger itself. Spec 213 PR 213-2 precedent: pg_cron jobs use hardcoded Bearer tokens that drift with `TASK_AUTH_SECRET` rotation. | technical-spec.md:472-476 + 449-452 | Add post-deploy smoke: `mcp__supabase__execute_sql` query `SELECT * FROM cron.job WHERE jobname IN ('llm_spend_ledger_rollover', 'llm_idempotency_cache_prune', 'nikita_handoff_greeting_backstop')` to confirm schedule + last_run + last_status. Document in PR-2 / PR-3 deploy checklist. |
| **L-T3** | Test naming consistency | `tests/fixtures/onboarding_tone_fixtures.yaml` (20 fixtures, ≥18/20 pass) and `tests/fixtures/jailbreak_patterns.yaml` (20 fixtures, all-pass) use different pass-rate thresholds (90% vs 100%). Tone-filter relies on subjective Gemini scoring (some variance OK); jailbreak relies on hard-rule rejection (no variance OK). Difference is intentional; document briefly. | spec.md:739, 742 | Add 1-line comment to each YAML header explaining pass-rate rationale. |

---

## Test Scenario Inventory

### E2E Scenarios

| Scenario | Priority | Source | Status |
|----------|----------|--------|--------|
| Happy path: incognito → chat → ceremony → CTA | P1 | technical-spec.md:600-614 | Defined |
| @edge-case: Fix-that ghost-turn | P1 | AC-11d.13b (a) | Defined |
| @edge-case: 2500ms timeout fallback | P1 | AC-11d.13b (b) | Defined |
| @edge-case: Backtracking city change | P1 | AC-11d.13b (c) | Defined |
| @edge-case: Age <18 in-character | P1 | AC-11d.13b (d) | Defined |
| Live preview-env dogfood (PR 1-4) | P1 | technical-spec.md:619-621 | Defined |
| Telegram MCP greeting timing E2E | P1 | AC-11e.2 + technical-spec.md:621 | Defined |

### Integration Test Points

| Component | Integration Point | Mock Required |
|-----------|-------------------|---------------|
| ConversationAgent ↔ Anthropic | LLM call | Yes (mocked AnthropicModel) |
| `/converse` route ↔ ConversationAgent | Endpoint flow | Yes (DI-mocked agent) |
| `/converse` ↔ idempotency_cache | Replay dedupe | No (real DB) |
| `/converse` ↔ llm_spend_ledger | Daily cap | Partial (mocked cost counter + real ledger row) |
| `/converse` ↔ users.onboarding_profile | JSONB write | No (real DB + ORM) |
| handoff_greeting ↔ Telegram bot | send_message | Yes (mocked bot) |
| handoff_greeting ↔ pg_cron backstop | Stranded retry | Partial (call task endpoint directly) |

### Unit Test Coverage (new files only)

| Module | Test File | Required Coverage |
|--------|-----------|-------------------|
| `nikita/agents/onboarding/conversation_agent.py` | `tests/agents/onboarding/test_conversation_agent.py` | Per spec; threshold not stated → see M-T1 |
| `nikita/agents/onboarding/extraction_schemas.py` | embedded in above | Per spec; threshold not stated → see M-T1 |
| `nikita/api/routes/portal_onboarding.py` (extension) | `tests/api/routes/test_converse_endpoint.py` | Per spec; threshold not stated → see M-T1 |
| `nikita/agents/onboarding/handoff_greeting.py` | `tests/agents/onboarding/test_handoff_greeting.py` | Per spec |
| Portal `ChatShell.tsx`, `MessageBubble.tsx`, etc. | per technical-spec.md:587-596 | Per spec; threshold not stated → see M-T1 |

---

## Recommendations (Prioritized)

1. **Accept M-T1** for iter-2 (coverage threshold gap is non-blocking; surfaces during PR review). Open GH issue `enhancement: NFR-005 add coverage targets for FR-11d new modules`. Add to PR-2 checklist.
2. **Defer M-T2** (E2E coherence Gemini-judge). Triangulation via tone + persona-drift + extraction-fidelity is sufficient for ship; coherence judge is post-Phase-B polish. Open GH issue tagged `enhancement`.
3. **Address L-T1** (baseline seed ownership) inline during PR-2 by adding the seed script + ADR clarification. Cheap fix.
4. **Add L-T2** (pg_cron smoke) to PR-2 / PR-3 deploy checklist as a post-deploy verification step. Use Supabase MCP `execute_sql`.
5. **Address L-T3** (YAML pass-rate documentation) inline during PR-2 fixture creation. One-line comment per file.

---

## Verdict

**PASS — 0 CRITICAL + 0 HIGH.**

All three iter-1 HIGH findings (H16/H17/H18) are RESOLVED with falsifiable test scaffolding. The amended spec adds:
- Conjunctive 2-gate persona-drift metric with pinned baseline + ADR-governed regen.
- 4 @edge-case Playwright walks tagged for grep-isolation.
- Pre-PR grep gate trio enforced both locally + CI.
- 20-fixture jailbreak suite (OWASP LLM01) + 20-fixture tone-filter suite (Gemini-judged ≥18/20).
- pg_cron-backed `llm_spend_ledger` with end-of-day write assertion.
- pg_cron-backed handoff backstop with crash-injection test (90s SLA).

Two MEDIUM and three LOW findings are non-blocking; all have concrete actionable recommendations and can be addressed inline during PR-2/PR-3 implementation OR deferred to post-ship enhancement issues.

**Approval to proceed to Phase 5 (planning) — PASS.**
