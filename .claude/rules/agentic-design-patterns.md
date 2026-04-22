# Agentic Design Patterns — How to Build LLM Conversation Flows

**This rule fires** for any task touching `nikita/agents/**`, `nikita/pipeline/**`, voice/text agent prompts, conversational onboarding/handoff flows, or any code that calls `Agent(...).run(...)`. Consult BEFORE planning.

**Authority**: Walk V (2026-04-22) shipped 4 coupled anti-patterns through 5 walks + 4 patchwork PRs (#392-396) before redesign was forced. The pattern is encoded here so future agent work doesn't redo it. ADR-009.

## Hard Rules

### 1. Cumulative server-side state — NEVER per-turn snapshot

State is the union of all extractions across the conversation, held in a Pydantic model. Per-turn `extracted_fields` is an INPUT to a merge, not the source of truth.

- Use a `WizardSlots(BaseModel)` or equivalent with one optional field per slot
- Use `@computed_field @property` for derived state (`missing`, `progress_pct`, etc.)
- Use `model_copy(update={...})` to merge — immutable update; reassign caller's reference
- Persist the full state as JSONB on the user row OR reconstruct from `conversation[*].extracted ∪ elided_extracted` on load

### 2. Completion gates via Pydantic — NEVER hardcoded booleans, NEVER LLM-judged

```python
try:
    form = FinalForm.model_validate(state.slots_dict)
    complete = True
except ValidationError:
    complete = False
```

`FinalForm` declares all required slots as non-optional + cross-field `@model_validator(mode="after")` for business rules (age ≥ 18, voice-requires-phone, etc.). The validator IS the gate. Refuse `complete = True` / `complete = False` literals in handler code.

### 3. Tool selection — consolidate; if N tools, inject missing-slot guidance

Default: 1 tool with discriminated-union args:

```python
output_type=[SlotDelta, str]   # mixed: structured delta OR clarifying free-text
```

If N narrow tools are unavoidable, use **dynamic `instructions=callable`** to re-render the system prompt every turn with current `state.missing` injected — gives the LLM "what's left to collect" instead of relying on static prompt rules. Tool-selection bias is the documented failure mode of N-tool fan-out (Pydantic AI `output.py` doc + Indium March 2026 reliability study).

### 4. Progress is a `@computed_field` of cumulative state — NEVER of latest extraction

```python
@computed_field
@property
def progress_pct(self) -> int:
    return min(100, int((TOTAL - len(self.missing)) * 100 / TOTAL))
```

Monotonicity is by construction — slots only added, never removed. CI test required: turn-by-turn fixture asserts `progress_pct[t+1] >= progress_pct[t]`.

### 5. Validation layering — three layers, all required

- **Pre-tool** (Pydantic on tool args / structured output schema)
- **Post-tool** (`@agent.output_validator` with `raise ModelRetry(...)` on validation failure for self-correcting loop)
- **Deterministic post-processing** (regex/heuristic fallback for high-stakes slots like phone — defense in depth against LLM tool-selection bias)

### 6. Conversation context — official `message_history=` primitive

```python
agent.run(user_input, message_history=state.messages, deps=deps)
```

Use `result.new_messages()` between turns. Do NOT reinvent conversation context in the request body or system prompt. Use `hydrate_message_history` (`nikita/agents/onboarding/message_history.py:44`) for wire→`ModelMessage` conversion.

## Anti-Patterns (with file:line precedents)

| Anti-pattern | Walk V precedent | Fix |
|---|---|---|
| `conversation_complete=False` hardcode | `nikita/api/routes/portal_onboarding.py:1020` | Pydantic `FinalForm.model_validate()` gate |
| 7 single-purpose `extract_*` tools | `nikita/agents/onboarding/conversation_agent.py` (L106-244) | 1 agent, `output_type=[SlotDelta, str]` |
| `_compute_progress(latest_kind)` per-turn snapshot | `portal_onboarding.py:1073-1088` | `WizardSlots.progress_pct` computed_field |
| Hardcoded routing rules in static system prompt | `conversation_prompts.py` post-PR #395 | `Agent(instructions=callable)` dynamic |
| `progress = response.progress_pct` overwrite in FE reducer | (now correct iff BE serves cumulative — but document this contract) | BE = single source of truth |

## Required Tests for Any Agent Flow

1. **Cumulative-state monotonicity**: turn-by-turn fixture, asserts progress never regresses
2. **Completion-gate triplet**: empty state → False/0%, partial → False/<100%, full → True/100%
3. **Mock-LLM emits wrong tool**: prove recovery path (regex fallback OR `ModelRetry` self-correction)
4. **Agent invocation contract**: `agent.run(...)` called with `message_history=` and `deps=` containing cumulative state
5. **Dynamic-instructions invocation**: callable invoked per-turn with current state (snapshot ≠ snapshot pin; assert callable was called)

## Pydantic AI Primitives Reference

| Primitive | Use | Doc |
|---|---|---|
| `Agent(output_type=[X, str])` | Mixed mode — structured OR free text | https://ai.pydantic.dev/output/ |
| `Agent(instructions=callable)` | Dynamic per-turn system prompt | same |
| `agent.run(..., message_history=)` | Multi-turn conversation context | https://ai.pydantic.dev/message-history/ |
| `Agent(deps_type=X)` + `RunContext[X]` | Sidecar state DI | https://ai.pydantic.dev/dependencies/ |
| `@agent.output_validator` + `raise ModelRetry` | Self-correcting agent loop | https://ai.pydantic.dev/output/#output-validator-functions |
| `@model_validator(mode="after")` | Cross-field Pydantic v2 validation | https://docs.pydantic.dev/latest/concepts/validators/ |
| `@computed_field @property` | Derived state, serialized | https://docs.pydantic.dev/latest/concepts/fields/#the-computed_field-decorator |
| `pydantic-graph` (FSM) | NOT for linear flows. "Don't use a nail gun unless you need a nail gun." Reach for it only when branching emerges (e.g., voice-vs-text divergence with rejoin). | https://ai.pydantic.dev/graph/ |

## References

- Spec: `specs/214-portal-onboarding-wizard/spec.md` FR-11d (post-amendment)
- ADR: `~/.claude/ecosystem-spec/decisions/ADR-009-agentic-design-patterns.md`
- Memory: `~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/feedback_agentic_systems_not_procedural.md`
- Sister rules: `.claude/rules/{testing.md, pr-workflow.md, review-findings.md, tuning-constants.md}`
- Walk V evidence: Cloud Run rev `nikita-api-00280-q5w`, user `walkv`, JSONB conversation kinds=[location, scene, darkness, identity, backstory, **identity**] (wrong terminal extraction)
