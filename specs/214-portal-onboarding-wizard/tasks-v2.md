# Spec 214 — Tasks v2 (FR-11d Slot-Filling)

**Source:** `plan-v2.md`. TDD-ordered. Owner: `executor-agent` (via `/implement` skill).

## PR-A — State + Cumulative Completion + Regex (T1-T9)

| ID | Task | Files | TDD | Driver AC |
|---|---|---|---|---|
| T1 | RED: `test_wizard_state.py` failing tests for WizardSlots / FinalForm / SlotDelta | `tests/agents/onboarding/test_wizard_state.py` (NEW) | RED | AC-11d.1, AC-11d.3 |
| T2 | GREEN: implement state models | `nikita/agents/onboarding/state.py` (NEW) | GREEN | AC-11d.1, AC-11d.3 |
| T3 | RED: `TestConverseCumulativeCompletion` triplet (empty/partial/full) + `TestConverseMonotonicProgress` (turn-by-turn `progress_pct` never regresses, ≥3-turn fixture) + `test_converse_terminal_turn_includes_link_code` + `test_converse_non_terminal_turn_omits_link_code` + `test_get_conversation_returns_link_after_completion` + `test_get_conversation_signals_link_expired_after_ttl` + `test_get_conversation_never_mints_code` | `tests/api/routes/test_converse_endpoint.py` (extend) | RED | AC-11d.2, AC-11d.3, AC-11d.7, AC-11d.8 |
| T4 | GREEN: wire cumulative state + FinalForm gate + link_code mint into `/converse`; DELETE `_compute_progress`; EXTEND `ConverseResponse` + `ConversationProfileResponse` with new fields | `nikita/api/routes/portal_onboarding.py` + `converse_contracts.py` | GREEN | AC-11d.3, AC-11d.7, AC-11d.8 |
| T5 | RED: `test_regex_fallback.py` for E.164 happy / age-substring reject / state-already-filled | `tests/agents/onboarding/test_regex_fallback.py` (NEW) | RED | AC-11d.4 |
| T6 | GREEN: implement `regex_phone_fallback` reusing `PhoneExtraction._phone_format` | `nikita/agents/onboarding/regex_fallback.py` (NEW) | GREEN | AC-11d.4 |
| T7 | RED: `test_state_reconstruction.py` for cumulative + elision-boundary + repeated-slot | `tests/agents/onboarding/test_state_reconstruction.py` (NEW) | RED | AC-11d.1, AC-11d.10 |
| T8 | GREEN: implement `build_state_from_conversation` (elided FIRST, live overrides) | `nikita/agents/onboarding/state_reconstruction.py` (NEW) | GREEN | AC-11d.1, AC-11d.10 |
| T9 | RED+GREEN: micro-bench `test_reconstruct_wizardslots_under_budget` | `tests/agents/onboarding/test_state_reconstruction_perf.py` (NEW) | GREEN | AC-11d.9 |
| T-A-Push | Pre-push HARD GATE: `uv run pytest -q` PASS | — | — | — |

## PR-B — Agent Refactor + Dynamic Instructions + FE Wire-Up (T10-T12)

| ID | Task | Files | TDD | Driver AC |
|---|---|---|---|---|
| T10 | RED: `test_dynamic_instructions.py` + `TestConsolidatedAgent` + `TestToolSelectionBiasRecovery` + `test_agent_run_uses_message_history_primitive` | `tests/agents/onboarding/test_{dynamic_instructions,conversation_agent}.py` | RED | AC-11d.4, AC-11d.5, AC-11d.6 |
| T11 | GREEN: refactor agent + dynamic instructions + output_validator + ModelRetry; wire regex fallback into /converse step 3 | `conversation_agent.py`, `conversation_prompts.py`, `portal_onboarding.py` | GREEN | AC-11d.4, AC-11d.5, AC-11d.6 |
| T12 | FE wire-up: TS type extension; remove `api.linkTelegram()` post-completion call; add `link_code_expired` re-mint branch; fix 429 fallback isComplete preservation | `portal/src/app/onboarding/types/converse.ts`, `onboarding-wizard.tsx` | GREEN | AC-11d.7, AC-11d.8 + Phase 3 Notes |
| T-B-Push | Pre-push HARD GATE: `uv run pytest -q` AND `(cd portal && npm run test -- --run && npm run lint && npm run build)` PASS | — | — | — |

## Order of Execution

PR-A T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T-A-Push → PR open → /qa-review CLEAN → squash merge → smoke probe
PR-B T10 → T11 → T12 → T-B-Push → PR open → /qa-review CLEAN → squash merge → smoke probe → Phase 4 Walk W

## Pre-PR Grep Gates (mandatory before /qa-review)

```bash
# AC-11d.3 grep gate
rg "conversation_complete\s*=\s*(True|False)\b" nikita/api/routes/portal_onboarding.py   # → empty
rg "_compute_progress\(extracted_fields" nikita/api/routes/portal_onboarding.py            # → empty

# AC-11d.8 grep gate
rg "TelegramLinkRepository|create_code" nikita/api/routes/portal_onboarding.py             # → matches only inside POST /converse handler

# Pre-PR generic gates per .claude/rules/testing.md
rg -U "async def test_[^(]+\([^)]*\):[\s\S]*?(?=\nasync def|\nclass |\Z)" tests/ | rg -L "assert|pytest\.raises"  # → empty (no zero-assertion shells)
grep -nE "logger\.(info|warning|error|exception|debug).*%s.*(name|age|occupation|phone)" <changed .py>  # → empty
```

## Agentic-Flow Test Class Mapping (per `.claude/rules/testing.md`)

The 3 mandatory test classes for any change touching `nikita/agents/**` are PR-blockers. Coverage in tasks-v2:

| Mandatory class | Task(s) |
|---|---|
| Cumulative-state monotonicity | T3 (`TestConverseMonotonicProgress`) + T7 (`test_repeated_slot_extraction_uses_live_conversation`) |
| Completion-gate triplet (empty/partial/full → False/False/True) | T1 (`test_final_form_*`) + T3 (`TestConverseCumulativeCompletion`) |
| Mock-LLM-emits-wrong-tool recovery (regex fallback OR ModelRetry) | T10 (`TestToolSelectionBiasRecovery`) |

## References

- Plan: `plan-v2.md`
- Spec: `spec.md` (FR-11d, AC-11d.1-10)
- Validation: `validation-findings.md`
- Audit: `audit-report-v2.md` (PASS with 2 MEDIUM remediations addressed in this file)
