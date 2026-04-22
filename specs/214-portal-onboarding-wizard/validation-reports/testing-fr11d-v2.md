## Testing Validation Report — FR-11d Amendment

**Spec:** `specs/214-portal-onboarding-wizard/spec.md` (FR-11d, lines 654-753)
**Branch:** `spec/214-fr11d-slot-filling-amendment` (commit b4180e1)
**Validator:** sdd-testing-validator
**Status:** PASS
**Timestamp:** 2026-04-22T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | E2E coverage | FR-11d defines a chat-first slot-filling agentic flow that fundamentally diverges from the legacy 11-step click-wizard, but `NFR-005` and the Playwright Test Inventory (lines 993-1001, 1086-1088) still enumerate ONLY the legacy step-based E2E specs (`onboarding-wizard.spec.ts`, `onboarding-resume.spec.ts`, `onboarding-phone-country.spec.ts`) targeting `data-testid="wizard-step-{N}"`. No FR-11d-specific E2E spec is named (e.g., `onboarding-converse.spec.ts`) and no "Walk W" or chat-first happy-path AC exists. Risk: the agentic flow could ship without a single live browser-side E2E. | spec.md:870, 993-1001, 1086-1088 | Add an explicit chat-first E2E to the inventory: e.g., `portal/e2e/onboarding-converse.spec.ts` covering (a) 3-turn conversation reaching `complete=true`, (b) deterministic regex-fallback path when typed phone is presented, (c) `progress_pct` monotonicity asserted across response payloads. Reference it in NFR-005 mandatory E2E list and add an AC-11d.7 "Walk W happy path" reflecting it. |
| MEDIUM | Coverage targets | NFR-005 enumerates coverage targets for `WizardStateMachine` (≥85% branch), step components (≥70% line), `useOnboardingPipelineReady` (≥80% branch) — all legacy artifacts. FR-11d introduces new modules (`WizardSlots`, `FinalForm`, `hydrate_message_history`, regex fallback path, dynamic-instructions callable, `ConverseDeps`) without explicit coverage targets. The overall Python NFR-005 hint (90% mentioned in task brief) is not present in the actual spec text. | spec.md:865-870 | Extend NFR-005 with FR-11d coverage targets: `WizardSlots` + `FinalForm` ≥ 95% line (small pure-data models, easy to hit), `/converse` handler in `nikita/api/routes/portal_onboarding.py` ≥ 85% branch (covers gate + fallback paths), regex phone fallback ≥ 100% branch (3 paths: phone present + match, present + no match, absent). |
| LOW | TDD readiness | AC-11d.5 has two acceptable shapes ((a) consolidated tool, (b) retained 6+1 + dynamic instructions). Test `test_dynamic_instructions_callable_invoked_with_missing_slots` only validates branch (b). If implementor chooses branch (a), a different falsifier is needed (assert single `output_type=[SlotDelta, str]` registration; assert `agent.tools` length == 1). | spec.md:738 | Add a parenthetical to AC-11d.5: "If branch (a) is chosen, replace `test_dynamic_instructions_callable_invoked_with_missing_slots` with `test_single_tool_discriminated_union_registered` asserting `len(agent._function_tools) <= 1` and `output_type` is a discriminated union including `SlotDelta` and `str`." |
| LOW | Test inventory completeness | The "Test Requirements" block (lines 741-752) names 5 tests but does not state which are unit vs integration vs E2E, nor co-locate them in a single inventory table with file paths + AC mapping. Reviewers must scroll up to ACs to reconstruct mapping. | spec.md:741-752 | Convert lines 741-752 into a 4-column table (Test name | Type | File path | Covers AC) so the auditor can grep-verify completeness in one pass. |
| LOW | AC-11d.1 testability nit | AC-11d.1 names `test_converse_cumulative_state_persists_across_turns` as an "integration test" but does not state whether it runs against a Postgres test container, an in-memory `AsyncMock` session, or the ASGI `tests/e2e/conftest.py` transport. Implementor ambiguity. | spec.md:734 | Specify: "uses `tests/e2e/conftest.py` ASGI transport with mocked `OnboardingProfileWriter`; no real Postgres required." |

### Testing Pyramid Analysis

```
         /\
        /E2E\           Target ~10%   Spec FR-11d ~10% (legacy specs only — FR-11d adds 0; see MEDIUM #1)
       /------\
      / Integ. \        Target ~20%   Spec FR-11d ~25% (AC-11d.1, AC-11d.6 + AC-11d.3 grep-gate)
     /----------\
    /   Unit     \      Target ~70%   Spec FR-11d ~65% (AC-11d.2, AC-11d.4, AC-11d.5 + 3 mandatory test classes)
   /--------------\
```

Pyramid balance is acceptable for the BACKEND scope of FR-11d (the 5 named tests skew slightly integration-heavy because the agent invocation contract is intrinsically integration-shaped). The E2E gap is the MEDIUM finding above — fix by adding `onboarding-converse.spec.ts`.

### AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| AC-11d.1 | Cumulative-state read | Yes | Integration (`/converse` 3-turn) | LOW: ambiguous transport choice (see findings) |
| AC-11d.2 | Monotonic progress (`progress_pct[t+1] >= progress_pct[t]`) | Yes | Unit (state model) | None — falsifier is concrete and bounded |
| AC-11d.3 | Pydantic completion gate (no boolean literals; grep-verifiable) | Yes | Unit + grep-gate | None — `rg "conversation_complete\s*=\s*(True\|False)"` is ideal CI guard |
| AC-11d.4 | Phone regex fallback for wrong-tool LLM | Yes | Unit (mock agent) | None — directly satisfies testing.md §3 mandatory |
| AC-11d.5 | Tool consolidation OR dynamic instructions | Yes | Unit | LOW: only one branch has a falsifier (see findings) |
| AC-11d.6 | `agent.run(message_history=, deps=)` contract | Yes | Integration | None — clear non-empty `message_history` assertion |

All 6 ACs are SMART (Specific, Measurable, Automated, Reproducible). No vague phrasing ("system performs well", "good UX"). RED-test-first feasible for every AC.

### Test Scenario Inventory

**Unit tests (BE):**
| Test | File path | Covers AC | Existing dir? |
|------|-----------|-----------|---------------|
| `test_progress_monotonicity` | `tests/agents/onboarding/test_wizard_slots_progress.py` (NEW) | AC-11d.2 | yes (`tests/agents/onboarding/`) |
| Completion-gate triplet (3 cases) | `tests/agents/onboarding/test_final_form_validation.py` (NEW) | AC-11d.3 | yes |
| `test_extract_phone_regex_fallback_when_llm_emits_wrong_tool` | `tests/agents/onboarding/test_conversation_agent.py` (extends existing) | AC-11d.4 | yes (existing 19.3K file) |
| `test_dynamic_instructions_callable_invoked_with_missing_slots` | `tests/agents/onboarding/test_conversation_agent.py` (extends) | AC-11d.5 | yes |

**Integration tests (BE):**
| Test | File path | Covers AC | Existing dir? |
|------|-----------|-----------|---------------|
| `test_converse_cumulative_state_persists_across_turns` | `tests/api/routes/test_converse_endpoint.py` (extend or NEW) | AC-11d.1 | scope brief named it but file existence not verified by validator |
| `test_agent_run_uses_message_history_primitive` | `tests/agents/onboarding/test_conversation_agent.py` (extends) OR `tests/api/routes/test_converse_endpoint.py` | AC-11d.6 | yes |

**E2E tests (FE):** none currently named for FR-11d (see MEDIUM #1).

**Path-mapping verification:** all 4 net-new test files target the existing `tests/agents/onboarding/` directory, which already hosts 6 sibling Python test files (`test_conversation_agent.py`, `test_extraction_schemas.py`, `test_handoff_greeting.py`, `test_message_history.py`, `test_validators.py`, `__init__.py`). Path mapping is clean. None of the named test functions currently exist (verified via `grep` across `tests/`) — RED-test-first state is genuine.

### TDD Readiness Checklist
- [x] All ACs are specific (no "system performs well")
- [x] All ACs are measurable (concrete predicates: `>=`, `==`, validation success/failure, grep-empty)
- [x] Test types clear per AC (table above)
- [x] Red-green-refactor path clear: every named test can be written FIRST against current master and observed to fail (cumulative-state read currently per-turn snapshot per anti-pattern at `nikita/api/routes/portal_onboarding.py:1086-1100`; completion-gate currently `progress_pct == 100` literal at L1025; regex fallback path absent; dynamic instructions absent)
- [x] No test currently exists for any named falsifier (RED state genuine)
- [x] Anti-pattern guards: AC-11d.4 directly satisfies `.claude/rules/testing.md` §3 "Mock-LLM-emits-wrong-tool recovery" mandatory test
- [x] Anti-pattern guards: AC-11d.2 directly satisfies §1 "Cumulative-state monotonicity" mandatory test
- [x] Anti-pattern guards: AC-11d.3 directly satisfies §2 "Completion-gate triplet" mandatory test (empty/partial/full)

### Coverage Requirements
- [x] Overall target specified for legacy artifacts (NFR-005)
- [ ] **Gap**: FR-11d-introduced modules (`WizardSlots`, `FinalForm`, `/converse` handler post-amendment, regex fallback) lack explicit coverage targets — see MEDIUM #2
- [x] Critical path coverage: completion-gate path is grep-enforced (AC-11d.3) which is stronger than coverage %
- [x] Branch coverage: AC-11d.4 implicitly covers all 3 fallback branches if tested per-branch
- [ ] **Gap**: Coverage exclusions not documented (e.g., are agent prompts excluded from coverage?)

### Anti-Pattern Guards (Verification vs `.claude/rules/testing.md` "Agentic-Flow Test Requirements")

| Required test class (testing.md) | FR-11d coverage | Status |
|---|---|---|
| §1 Cumulative-state monotonicity | AC-11d.2 + `test_progress_monotonicity` (≥3 turns) | SATISFIED |
| §2 Completion-gate triplet (empty/partial/full) | AC-11d.3 + `test_final_form_validation.py` "covering empty/partial/full state paths" | SATISFIED |
| §3 Mock-LLM-emits-wrong-tool recovery | AC-11d.4 + `test_extract_phone_regex_fallback_when_llm_emits_wrong_tool` | SATISFIED |
| §4 (rule-additional) Agent invocation contract | AC-11d.6 + `test_agent_run_uses_message_history_primitive` | SATISFIED |
| §5 (rule-additional) Dynamic-instructions invocation | AC-11d.5 + `test_dynamic_instructions_callable_invoked_with_missing_slots` | SATISFIED for branch (b); missing falsifier for branch (a) — LOW |

All 3 mandatory test classes from `.claude/rules/testing.md` Agentic-Flow Test Requirements are correctly enforced by the spec. Both rule-additional tests from `.claude/rules/agentic-design-patterns.md` are also enforced.

### Recommendations (Prioritized)

1. **MEDIUM** — Add a chat-first E2E spec to the Test Inventory (line 993-1001) and a corresponding AC-11d.7 "Walk W happy path" so the agentic flow has at least one live browser-side end-to-end test. Suggested file: `portal/e2e/onboarding-converse.spec.ts`. Walk W naming makes traceability to the Walk V incident explicit.
2. **MEDIUM** — Extend NFR-005 with explicit coverage targets for FR-11d-introduced modules (`WizardSlots` ≥ 95%, `FinalForm` ≥ 95%, `/converse` handler ≥ 85% branch, regex fallback ≥ 100% branch). The current NFR-005 enumerates only legacy artifacts.
3. **LOW** — Add a branch-(a) falsifier to AC-11d.5 so TDD works for either tool-architecture choice.
4. **LOW** — Convert lines 741-752 into a 4-column inventory table (Test | Type | Path | AC) for grep-verifiable completeness.
5. **LOW** — Specify the test-transport choice for AC-11d.1 (`tests/e2e/conftest.py` ASGI vs unit AsyncMock).

### PASS/FAIL Determination

**PASS.** 0 CRITICAL + 0 HIGH. The 2 MEDIUM findings are gaps in inventory enumeration (E2E spec naming, coverage-target enumeration), not failures of testability — TDD can proceed from the current spec. The 3 mandatory Agentic-Flow Test Requirements from `.claude/rules/testing.md` are correctly enforced by named tests with falsifiable assertions. All 6 ACs are SMART and red-test-first feasible against current master.

The MEDIUM findings should be addressed before opening the FR-11d implementation PR but do not block exiting GATE 2.
