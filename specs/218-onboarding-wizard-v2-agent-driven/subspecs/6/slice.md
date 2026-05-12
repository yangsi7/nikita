---
title: "Spec 218 Slice 218-6 — Phase-2 open-bounce + research agent + completion gate + backstory commit"
lifecycle: frozen
spec: 218
slice: 6
status: IMPLEMENTED
branch: feat/218-6-phase2-research-completion
---

# Slice 218-6 — Phase-2 Research Agent + Completion Gate + Backstory Commit

## Scope

Implements the Phase-2 open-bounce conversation layer for the v2 onboarding wizard.
Phase-1 collects structured slots via the decorator agent. Phase-2 is a free-form
follow-up conversation (4–8 turns) that gathers depth for backstory generation.

## Deliverables

| File | Type | Description |
|------|------|-------------|
| `nikita/agents/onboarding/v2/research_agent.py` | New | Phase-2 research agent, phase_2_gate, V2ResearchDeps, inject_phase2_context |
| `nikita/agents/onboarding/v2/backstory_commit.py` | New | generate_v2_backstory, BackstoryGenerationError, _run_backstory_agent |
| `nikita/api/routes/portal_onboarding_v2.py` | Modified | Phase-2 orchestration in handle_v2_answer (~150 LOC) |
| `tests/agents/onboarding/v2/test_research_agent.py` | New | Triplet: monotonicity + gate + wrong-output recovery |
| `tests/agents/onboarding/v2/test_completion_gate.py` | New | FR-008 boundary parametrization |
| `tests/agents/onboarding/v2/test_phase2_orchestrator.py` | New | handle_v2_answer Phase-2 entry + forced complete at MAX_TURNS |
| `tests/agents/onboarding/v2/test_backstory_commit.py` | New | BackstoryGenerationError isolation, truncation, empty messages |

## Design Decisions

### FR-008 Completion Gate

`phase_2_gate(state, agent_signals_done) -> (complete, forced)`:

- `count < MIN_TURNS (4)`: `(False, True)` — min-floor, blocks early CompleteAsk via ModelRetry
- `MIN_TURNS <= count < MAX_TURNS (8)`: `(agent_signals_done, False)` — LLM decides freely
- `count >= MAX_TURNS (8)`: `(True, True)` — max-ceiling forced complete

The `forced` bool enables observability (FR spec §Observability: termination cause must be recorded).

### Output Union Pattern

Agent emits `CompleteAsk | str` via `output_type=[ToolOutput(CompleteAsk, name="phase2_complete"), str]`.
`str` = follow-up question (user responds). `CompleteAsk` = terminal turn (triggers backstory + persist).

### Backstory Non-Fatal

`_run_phase2_complete` catches `BackstoryGenerationError` and completes with `backstory_preview=None`.
LLM failures must not block wizard completion.

### computed_field Serialization Pitfall

`WizardSlotsV2.model_dump(exclude_none=True)` includes `@computed_field` properties (`missing`,
`progress_pct`, `is_phase_1_complete`) that fail `model_validate` with `extra="forbid"`.
All profile JSONB operations use `state.slots.slots_dict()` (raw slot fields only).

### V2ResearchDeps Isolation

New dataclass (NOT extending V2Deps) carries exactly what firecrawl_tools needs:
`traceparent`, `fetch_invocations_this_turn`, `fetch_cost_cumulative`. Avoids blast-radius
drift on the frozen Phase-1 V2Deps.

## Test Results

```
37 slice-218-6 tests: PASS
153 v2 suite tests: PASS
Full suite: 7248 passed, 2 failed (pre-existing, confirmed via git-stash)
```

Pre-existing failures (not introduced by this slice):
- `tests/agents/text/test_agent.py::test_ac_1_3_1_model_name_constant`
- `tests/api/routes/test_portal_onboarding_v2_slice5.py::test_geek_out_on_persists_via_handler`

## Red Commit

`9f97e77 test(218,6): RED — Phase-2 research agent + completion gate + backstory commit + orchestrator`

## Green Commit

`e049081 feat(218,6): Phase-2 open-bounce + research agent + completion gate + backstory commit`
