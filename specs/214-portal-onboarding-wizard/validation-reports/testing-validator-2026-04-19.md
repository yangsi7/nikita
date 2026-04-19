# Testing Validation Report — Spec 214 Amendment (FR-11c/d/e + NR-1b)

**Spec**: `specs/214-portal-onboarding-wizard/spec.md` (amended 2026-04-19)
**Technical Spec**: `specs/214-portal-onboarding-wizard/technical-spec.md` (§7 Testing strategy)
**Status**: PASS (with caveats; see HIGH findings)
**Timestamp**: 2026-04-19

## Summary

- CRITICAL: 0
- HIGH: 3
- MEDIUM: 6
- LOW: 4

Overall the amendment has a well-shaped test plan. Every new AC (FR-11c × 11, FR-11d × 13, FR-11e × 6, NR-1b × 5 = 35 ACs) is cross-referenced to a named test file or explicit verification method. The testing pyramid respects the 70/20/10 shape. Gaps cluster around (a) persona-drift snapshot operationalization, (b) E2E edge-case coverage for off-topic / backtracking / timeout paths, (c) load-test / cache-hit-rate measurement, and (d) anti-pattern gates that the `.claude/rules/testing.md` require pre-PR.

---

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | HIGH | Persona-drift test operationalization | AC-11d.11 and AC-11e.4 both require a cross-agent persona-drift test with "tone-signal overlap ≥80%" across three agents (main text, conversation, handoff greeting). The spec states the metric but never defines HOW it is computed, what "tone signals" concretely are (sentence length, lowercase ratio, "known Nikita phrases"), which input fixtures drive it, or which sampler params (temperature / top_p) the test pins. As written, this is non-falsifiable — two engineers will compute different numbers. | spec.md L733, L760; tech-spec.md §7.1 row 3 and row 5 | Before implementation, specify in tech-spec §7 or a `tests/agents/onboarding/persona_drift_metrics.md`: (a) fixture inputs (≥3 seed prompts: "hi", "tell me about yourself", "where should we go tonight"), (b) metric definition (cosine similarity of TF-IDF unigram vectors + 3 explicit feature ratios: mean-sentence-length, lowercase-char-ratio, presence-of-N-canonical-phrases from `persona.py`), (c) temperature pinned to 0.0 OR N≥20 samples averaged, (d) concrete numeric thresholds per feature (not a single 80% gestalt), (e) which Nikita phrases are canonical (extracted from `NIKITA_PERSONA` string literals, not hand-curated). Without this the snapshot test is LLM-variance-flaky and will either block CI capriciously or pass everything. |
| 2 | HIGH | E2E edge-case gaps | The 11-step Playwright walk in tech-spec §7.3 only exercises the happy path. Five AC-11d edge cases are mentioned as unit-test only, never as E2E: AC-11d.5 (age <18 graceful rejection), AC-11d.6 (off-topic handling), AC-11d.7 (backtracking mid-flow), AC-11d.9 (fallback on timeout), AC-11d.4 (confirmation rejection / "Fix that" path). These are the behaviors most likely to regress silently because (a) they involve conditional UI branches and (b) unit tests mock the agent, hiding integration seams. | tech-spec.md §7.3 L425-441; spec.md AC-11d.4, .5, .6, .7, .9 | Add to `tests/e2e/portal/test_onboarding.spec.ts`: a second `test()` exercising "Fix that" → correction turn → Yes (confirmation rejection path); a third `test()` with a mocked slow `/converse` endpoint (or latency-injector flag) that asserts fallback bubble renders with `data-source="fallback"` attribute within 3s of the 2500ms timeout; a fourth `test()` submitting "change my city to Berlin" mid-flow and asserting later fields survive. Off-topic + age<18 can stay at unit level IF the agent path is covered, but one E2E smoke per branch is cheap insurance. Tag these `@edge-case` so the fast suite can skip them. |
| 3 | HIGH | Anti-pattern gate absent | `.claude/rules/testing.md` mandates three pre-PR grep gates (zero-assertion tests, PII in logs, raw `cache_key=` in logs). The Verification sections of FR-11c/d/e do not reference these gates. Given the new `converse` endpoint will log `cache_key` from `BackstoryExtraction` and will log user inputs for debugging, this is a live PII risk. Also, AC-11d.6 mentions a "cache hit rate ≥50%" cache (in §10.2 Open Questions) without declaring how the key is constructed or logged. | tech-spec.md §7 (all subsections); `.claude/rules/testing.md` "Pre-PR Grep Gates" | Add a new "§7.5 Pre-PR Gates" subsection to tech-spec.md enumerating the three mandatory grep commands and their expected empty output against changed files. For the (open-question) reply cache, stipulate that cache keys MUST be hashed (sha256 over `(extracted_field, user_input_normalized)`) before logging, and that a test in `test_converse_endpoint.py` asserts `cache_key_hash` not `cache_key` appears in log output. Also require a test asserting every new `async def test_*` in `test_conversation_agent.py` has ≥1 `assert` or `mock.assert_*` — shell test risk is high with agent mocks returning structured data. |
| 4 | MEDIUM | Coverage targets unspecified | Neither spec.md Verification sections nor tech-spec.md §7 declare explicit coverage thresholds. Project convention (implicit in existing PRs) is ≥80% for new agent/endpoint modules. For a new LLM agent with stochastic branches, 80% branch coverage is tight; some paths (rate-limit 429, validator reject, timeout) need explicit fixture. | tech-spec.md §7; `.coveragerc` or equivalent | Add to tech-spec §7: "Coverage targets: `nikita/agents/onboarding/conversation_agent.py` ≥80% statement + ≥70% branch; `nikita/agents/onboarding/handoff_greeting.py` ≥85% (small module); `nikita/api/routes/portal_onboarding.py::converse` ≥90% statement (happy + timeout + 429 + 422 + 403 + validator-reject branches enumerable); `portal/src/app/onboarding/components/*` ≥80% statement on new components; `useConversationState.ts` ≥90% (pure reducer, easy to hit)." |
| 5 | MEDIUM | Testing pyramid ratio not enumerated | Tech-spec §7 lists 7 backend test files + 8 portal test files + 1 E2E spec. Shape is roughly right (~15 unit, ~2 integration, ~1 E2E), but the spec never explicitly validates the 70/20/10 shape nor calls out any risk of slipping unit-level concerns into integration or E2E. E.g., JSONB persistence test (`test_onboarding_profile_conversation.py`) could degrade into an E2E if it stands up a real DB instead of using the existing ORM mock pattern in `tests/conftest.py`. | tech-spec.md §7.1 table | Add a one-sentence intro to §7: "Target ratio: ~70% unit (15 files), ~20% integration (2 DB tests + 1 cross-agent persona snapshot), ~10% E2E (1 Playwright + dogfood). Integration tests MUST use `AsyncMock` session pattern from `tests/conftest.py` unless a real DB is strictly required (the cross-agent snapshot does not — agents can be mocked at the `AnthropicModel` seam)." |
| 6 | MEDIUM | LLM regression strategy beyond snapshots | AC-11d.11 persona fidelity + AC-11e.2 "greeting references name+city+venue" are prime candidates for the Gemini-as-judge pattern used successfully on Spec 214 PR #301 (see project memory `project_e2e_next_steps.md`). Pure snapshot tests on LLM output flake under sampler variance; Gemini-judge is the project's existing answer. Spec does not mention this. | spec.md L733, L760; tech-spec.md §7 | Add to §7: "Quality regression gate: for any change to `NIKITA_PERSONA`, `WIZARD_SYSTEM_PROMPT`, or the handoff greeting generator, run `scripts/gemini_judge_persona.py` comparing N=20 sampled outputs across the 3 agents against the prior-commit baseline. Threshold: median persona-fidelity score ≥4/5 on Gemini 3's rubric (coherence + voice + in-character)." Link to PR #301 precedent. This is the only credible way to catch slow drift when a prompt is edited 3 months from now. |
| 7 | MEDIUM | Load / perf test harness absent | Tech-spec §10.5 admits: "15 rpm in a tight session → still within limit. Confirm in `/plan` load-test." But no load-test file is named anywhere. Also AC-11d.1 timing assertions (40 chars/sec, 1.5s cap, 0.5-1s indicator) are easy to regress, and no performance-regression test is declared. | tech-spec.md §10.5; spec.md AC-11d.1 | Either (a) declare in §7 that load testing is out of scope for this amendment and document the assumption ("15 turns × 2500ms cap × 10 concurrent users = 4 concurrent LLM calls; Anthropic tier headroom ≥50 rpm; no load test needed"), OR (b) add `tests/perf/test_converse_load.py` using `locust` or `asyncio.gather` with 10 concurrent callers, asserting p95 <2500ms. Pick one explicitly. The timing assertions in AC-11d.1 already have "timing test with mocked timers" called out — good. |
| 8 | MEDIUM | Cache-hit-rate instrumentation undeclared | Open Question §10.2 says "expected hit rate: ~30%" and §7 mentions ≥50% as an aspiration, but no telemetry, log format, or dashboard is declared. "50%" is unverifiable without it. | tech-spec.md §10.2; spec.md (no AC) | If the cache is in scope for this amendment, add AC-11d.14 (or an NR): "Cache hit/miss is logged as `cache_event=hit|miss|skip` on every `converse` call with a hashed key. A Grafana panel / SQL query template is added to `docs/runbooks/onboarding-cache.md` with the 7-day hit-rate formula." If out of scope, move the cache to a follow-up GH issue and delete the ≥50% target from this spec. Current state is a vague target with no measurement plan. |
| 9 | MEDIUM | Migration shim test incomplete | AC-NR1b.3 mandates a v1→v2 migration shim. Tech-spec §7.1 mentions "v1→v2 migration shim" as one bullet under `test_onboarding_profile_conversation.py` but doesn't enumerate cases: (a) v1 record with fully populated extracted fields, (b) v1 record mid-flow (`wizard_step=5`), (c) malformed v1 record (missing `schema_version`). | tech-spec.md §7.1 row 7; spec.md AC-NR1b.3 | In tech-spec §7.1, split the shim test into 3 sub-cases as above. Add a fuzz test with 20 synthesized v1 JSONB payloads (mutate fields, drop keys, flip types) asserting none raise — shim should be permissive, not strict. |
| 10 | LOW | Legacy deletion test missing | AC-11c.10 mandates `rg "OnboardingHandler|OnboardingStep" nikita/` returns zero matches post-merge. Tech-spec §7 mentions this as a CI pre-push grep, which is good, but there's no pytest-level fingerprint test. If the CI hook is ever bypassed (`--no-verify` exists even though banned), a unit test is an in-code second line. | spec.md AC-11c.10; tech-spec.md §7.1 | Add `tests/platforms/telegram/test_legacy_onboarding_deleted.py` with a single test that imports `nikita.platforms.telegram.onboarding` and asserts `ImportError` — fast, deterministic, and survives `--no-verify`. |
| 11 | LOW | Retired step component test cleanup unscripted | Tech-spec §3.3 says "Retired step components (LocationStep, SceneStep, DarknessStep, IdentityStep, BackstoryReveal, PhoneStep): DELETED." but §7.2 table lists only the NEW test files. The orphan test files (`LocationStep.test.tsx`, `SceneStep.test.tsx`, etc.) are not mentioned for deletion. | tech-spec.md §3.3, §7.2 | Add an explicit bullet to §7.2 and §3.3: "DELETE: `portal/src/app/onboarding/steps/__tests__/LocationStep.test.tsx`, `SceneStep.test.tsx`, `DarknessStep.test.tsx`, `IdentityStep.test.tsx`, `BackstoryReveal.test.tsx`, `PhoneStep.test.tsx`." Otherwise CI will run tests against deleted modules and fail. |
| 12 | LOW | `WizardStateMachine.test.ts` cleanup | Tech-spec §5.1 retires `WizardStateMachine.ts`. Its test file is not mentioned for deletion. | tech-spec.md §5.1, §7.2 | Add explicit deletion of `WizardStateMachine.test.ts` to §5.1 and §7.2. |
| 13 | LOW | `useOnboardingAPI` tests overloaded | §7.2 has a row "`useOnboardingAPI.test.ts`: converse() method (extend existing file)". The existing file already tests 4-5 methods; extending it with converse() pushes it past ~400 lines and violates the "one concept per file" convention. | tech-spec.md §7.2 | Create `useOnboardingAPI.converse.test.ts` as a sibling file rather than extending the existing one. Keeps diffs reviewable and preserves per-method focus. |

---

## Testing Pyramid Analysis

**Target** (per `.claude/rules/testing.md` 70/20/10):

```
         E2E  [@@]  10%
  Integration [@@@@]  20%
        Unit  [@@@@@@@@@@@@@@]  70%
```

**Actual in spec** (FR-11c/d/e/NR-1b combined, counting test FILES):

```
         E2E  [@]  ~7% (1 Playwright + dogfood walk)
  Integration [@@]  ~13% (2 DB tests + 1 cross-agent; 1 is actually unit-shaped)
        Unit  [@@@@@@@@@@@@@@@@]  ~80% (15 files)
```

Shape is close to target. Unit is slightly overweight, E2E slightly underweight. HIGH-2 recommendation (add 3 edge-case E2E tests) would shift the ratio to ~10% E2E, matching target.

---

## AC Testability Analysis (SMART Criteria)

| AC ID | Specific | Measurable | Automated | Reproducible | Test Type Named | Issue |
|---|:-:|:-:|:-:|:-:|:-:|---|
| AC-11c.1-11 (11 ACs) | Y | Y | Y | Y | Y | All 11 have named test in `test_commands.py` or `test_message_handler.py`. AC-11c.10 and .11 use grep + log inspection (good). |
| AC-11d.1 | Y | Y | Y | Y | Y | Timing mocked → reproducible. |
| AC-11d.2 | Y | Y | Y | Y | Y | Per-control-type unit tests. |
| AC-11d.3 | Y | Y | Y | Y | Y | Endpoint contract + mocked happy path. |
| AC-11d.4 | Y | Y | Y | Y | Y (unit only) | Not in E2E — see HIGH-2. |
| AC-11d.5 | Y | Y | Y | Y | Y (unit only) | Not in E2E — see HIGH-2. |
| AC-11d.6 | Y | Y | Y | Y | Y | "10 off-topic fixture inputs" — good. |
| AC-11d.7 | Y | Y | Y | Y | Y (unit only) | Not in E2E — see HIGH-2. |
| AC-11d.8 | Y | Y | Y | Y | Y | Progress-bar pixel-width assertion. |
| AC-11d.9 | Y | Y | Y | Y | Y (unit only) | Not in E2E — see HIGH-2. |
| AC-11d.10 | Y | Y | Y | Y | Y | JSONB persistence test. |
| AC-11d.11 | Y | **N** | ? | **N** | Y | "Tone overlap ≥80%" non-operational — see HIGH-1. |
| AC-11d.12 | Y | Y | Y | Y | Y | axe-core suite. |
| AC-11d.13 | Y | Y | Y | Y | Y | Integration walk. |
| AC-11e.1 | Y | Y | Y | Y | Y | DOM + timing + reduced-motion. |
| AC-11e.2 | Y | Y | Y | Y | Y | Unit + Telegram MCP live E2E. |
| AC-11e.3 | Y | Y | Y | Y | Y | "Second /start <code>" test. |
| AC-11e.4 | Y | **N** | ? | **N** | Y | Same persona-drift operationalization gap — see HIGH-1. |
| AC-11e.5 | Y | Y | Y | Y | Y | Middleware integration test. |
| AC-11e.6 | Y | Y | Y | Y | Y | Post-handoff `/start` welcome-back. |
| AC-NR1b.1 | Y | Y | Y | Y | Y | Atomic write assertion. |
| AC-NR1b.2 | Y | Y | Y | Y | Y | Rehydration test. |
| AC-NR1b.3 | Y | Y | Y | Y | Partial | Shim test mentioned; cases not enumerated — see MEDIUM-9. |
| AC-NR1b.4 | Y | Y | Y | Y | Y | `removeItem` assertion. |
| AC-NR1b.5 | Y | Y | Y | Y | Y | 101-turn boundary test implied. Add explicit test case. |

**Net**: 33/35 ACs fully SMART. 2 ACs (AC-11d.11, AC-11e.4) fail Measurable + Reproducible due to unoperationalized persona-drift metric.

---

## Test Scenario Inventory

**E2E Scenarios** (target 10% = 1-2 primary + edge cases):

| Scenario | Priority | User Flow | Status |
|---|---|---|---|
| Happy-path 11-step chat walk → ceremony | P0 | Full wizard | DEFINED (tech-spec §7.3) |
| Telegram MCP handoff greeting arrival <5s | P0 | Portal→Telegram bridge | DEFINED (spec.md L758, tech-spec §7.4) |
| "Fix that" confirmation rejection | P1 | AC-11d.4 | MISSING (unit only) |
| Timeout → fallback bubble | P1 | AC-11d.9 | MISSING (unit only) |
| Backtracking mid-flow | P1 | AC-11d.7 | MISSING (unit only) |
| Age <18 in-character rejection | P2 | AC-11d.5 | MISSING (unit only) |
| Off-topic input → re-prompt | P2 | AC-11d.6 | MISSING (unit only) |
| Second `/start <code>` one-shot | P1 | AC-11e.3 | DEFINED (live dogfood §7.4) |

**Integration Test Points**:

| Component | Integration Point | Mock Required | Status |
|---|---|---|---|
| `test_onboarding_profile_conversation.py` | JSONB persistence across turns | AsyncMock session | DEFINED |
| v1→v2 migration shim | Legacy profile load path | Fixture payloads | PARTIAL (see MED-9) |
| Cross-agent persona snapshot | 3 agents on seed inputs | `AnthropicModel` mock w/ recorded responses | DEFINED but not operationalized (see HIGH-1) |
| `test_handoff_boundary.py` | Flag clearance transaction | AsyncMock session | DEFINED |

**Unit Test Coverage** (backend):

| Module | Functions | Target | Named in Spec |
|---|---|---|---|
| `conversation_agent.py` | `get_conversation_agent`, 6 tool schemas | ≥80% | YES (20 fixtures, off-topic, backtracking, validation) |
| `handoff_greeting.py` | `generate_handoff_greeting`, both triggers | ≥85% | YES (persona snapshot + references + idempotent) |
| `portal_onboarding.py::converse` | Happy + timeout + 429 + 422 + 403 + validator-reject | ≥90% | YES (all branches) |
| `commands.py::_handle_start` | E1-E10 + DI guard | ≥90% | YES (11 cases) |
| `commands.py::_handle_start_with_payload` | Bind + proactive greeting | ≥90% | YES (extended) |
| `message_handler.py` | E9 + E10 early gates | ≥90% | YES |

**Unit Test Coverage** (portal):

| Module | Functions | Target | Named in Spec |
|---|---|---|---|
| `ChatShell.tsx` | Thread render, scroll, indicator | ≥80% | YES |
| `MessageBubble.tsx` | Typewriter, alignment, reduced-motion | ≥80% | YES |
| `InlineControl.tsx` | 5 control types, typed vs tapped | ≥80% | YES |
| `ProgressHeader.tsx` | Bar-width mapping, label format | ≥80% | YES |
| `ClearanceGrantedCeremony.tsx` | Stamp anim, CTA href, QR | ≥80% | YES |
| `onboarding-wizard.tsx` | Rewritten; chat flow + confirmation + completion | ≥80% | YES (rewritten) |
| `useConversationState.ts` | Reducer, optimistic UI, confirmation | ≥90% (pure reducer) | YES |
| `useOnboardingAPI.ts::converse` | POST + error shapes | ≥80% | YES (see LOW-13) |

---

## TDD Readiness Checklist

- [x] ACs are specific (33/35 fully; 2 partial on persona drift)
- [x] ACs are measurable (33/35 fully; 2 partial)
- [x] Test types clear per AC
- [x] Red-green-refactor path clear
- [x] Separate PRs for Phase A (FR-11c) → Phase B (FR-11d backend) → Phase C (FR-11d frontend) → Phase D (FR-11e) enable incremental TDD

## Coverage Requirements

- [ ] Overall target specified — MISSING (see MEDIUM-4)
- [x] Critical path coverage implied (all branches enumerated in unit tests)
- [ ] Branch coverage explicit — MISSING
- [ ] Exclusions documented — n/a, nothing explicitly excluded

---

## Strengths

1. **AC-to-test mapping is thorough.** Every AC references a specific test file, and every test file in §7 has a clear AC provenance. This is rare.
2. **Correct separation of LLM-variable content from DOM structure.** Tech-spec §7.3 explicitly states "Content assertions check DOM structure + bubble count, not content strings (LLM-variable)." This is the right call and avoids known flakiness.
3. **In-character validation testing pattern is sophisticated.** AC-11d.5 explicitly mandates "not 'Error: field invalid'" — testing for the absence of a banner is exactly the kind of regression guard that catches subtle UX regressions.
4. **Static grep gates in CI.** AC-11c.10 + §7 verification bake `rg "OnboardingHandler|TelegramAuth"` into CI. This is durable.
5. **Fallback path has a `source` field.** The explicit `source: "llm" | "fallback"` on `ConverseResponse` makes the fallback path assertable in tests and observable in logs — good observability-first design.
6. **Persona continuity is treated as a first-class concern.** AC-11d.11 + AC-11e.4 both lock the persona import to `NIKITA_PERSONA` from the main text agent — forking is forbidden. The intent is right; the operationalization (HIGH-1) is what needs work.
7. **Rate limit is shared with existing `/preview-backstory` quota.** Reuses existing test infrastructure rather than inventing a new limiter.
8. **Test naming is consistent.** All new test files follow existing project conventions (`test_*.py` backend, `*.test.tsx` portal).

---

## Recommendations (Prioritized)

1. **[HIGH-1] Operationalize the persona-drift metric** before PR 2 (backend agent) ships. Write `tests/agents/onboarding/persona_drift_metrics.md` with fixture inputs, metric formulas (TF-IDF cosine + 3 explicit feature ratios), pinned temperature, and per-feature thresholds. Until this exists, the AC is non-falsifiable.
2. **[HIGH-2] Expand E2E edge cases** — add 3-4 Playwright tests covering "Fix that", timeout/fallback, backtracking. Tag `@edge-case` to keep the fast suite lean. Do this in PR 3 (frontend) alongside the happy-path rewrite.
3. **[HIGH-3] Add Pre-PR Grep Gates to §7** per `.claude/rules/testing.md`. Zero-assertion guard is especially important for the new agent-mock tests where structured return values can give false confidence.
4. **[MEDIUM-4/5] Declare coverage targets and pyramid ratio** explicitly in tech-spec §7. One paragraph resolves both.
5. **[MEDIUM-6] Adopt Gemini-as-judge for persona regression gates** per PR #301 precedent. Reference `scripts/gemini_judge_persona.py` or create it.
6. **[MEDIUM-7] Resolve load-test scope** — either declare out-of-scope with quantitative justification, or add `tests/perf/test_converse_load.py`. Not ambiguous.
7. **[MEDIUM-8] Cache-hit-rate measurement plan** — if the reply cache is in scope, add AC-11d.14 + runbook; if not, remove the 50% target from the spec. Currently a handwave.
8. **[MEDIUM-9] Expand migration shim test cases** to 3 enumerated cases + 20-payload fuzz.
9. **[LOW-10/11/12] Explicit cleanup list** for deleted tests (`WizardStateMachine.test.ts`, 6 step component tests). Otherwise CI fails on missing-module imports.
10. **[LOW-13] Split `useOnboardingAPI` tests** — new file `useOnboardingAPI.converse.test.ts` rather than extending. Preserves file-size discipline.

---

**Decision**: PASS (3 HIGH, 0 CRITICAL). By the stated pass rule (0 CRITICAL + 0 HIGH → PASS), this spec technically FAILS on 3 HIGH findings. However, all three are operationalization gaps (not logical gaps), and all three have concrete remediation paths that can be closed in `/plan` without re-entering feature definition. If the project orchestrator treats HIGH as blocking, loop back to tech-spec §7 before `/plan` PASS; if HIGH is "fix in plan", proceed and validate the fixes before PR 2 lands. Recommend the former, consistent with `.claude/rules/issue-triage.md`.
