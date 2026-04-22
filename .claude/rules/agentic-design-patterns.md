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

| Anti-pattern | Precedent | Fix |
|---|---|---|
| Completion gate computed per-turn from `_compute_progress` instead of cumulative-state Pydantic validation. Originally `conversation_complete=False` literal (Walk V baseline, pre-PR #392, master commit 6339c78~). Currently `conversation_complete = progress_pct == 100` (post-PR #392). Both fail because `progress_pct` is per-turn snapshot. | `nikita/api/routes/portal_onboarding.py:1025` (current, post-#392); pre-#392 was hardcoded `False` literal at the same call-site. | Pydantic `FinalForm.model_validate(state)` gate over cumulative slots |
| 6 single-purpose `extract_*` tools + 1 `no_extraction` sentinel = 7 tool registrations | `nikita/agents/onboarding/conversation_agent.py` tools at L106, 116, 145, 170, 189, 206, 229 | 1 agent, `output_type=[SlotDelta, str]` discriminated-union |
| `_compute_progress(latest_kind)` per-turn snapshot | `nikita/api/routes/portal_onboarding.py:1086-1100` (function body) | `WizardSlots.progress_pct` `@computed_field` |
| Hardcoded slot-routing rules in static system prompt (PR #395 patchwork) | `nikita/agents/onboarding/conversation_prompts.py` `_WIZARD_FRAMING` | `Agent(instructions=callable)` dynamic, injects `state.missing` per-turn |
| `progress = response.progress_pct` overwrite in FE reducer | `portal/src/app/onboarding/hooks/useConversationState.ts:169-173` (now correct IFF BE serves cumulative — contract documented in FR-11d) | BE = single source of truth; FE simply reflects |

## Required Tests for Any Agent Flow

The canonical home for the 3 mandatory test classes (cumulative-state monotonicity, completion-gate triplet, mock-LLM-emits-wrong-tool recovery) is **`.claude/rules/testing.md` "Agentic-Flow Test Requirements" section** — refer there for falsifier definitions and to keep both files in sync.

This rule file additionally requires:

1. **Agent invocation contract** test: `agent.run(...)` called with `message_history=` AND `deps=` containing cumulative state. Asserts the BE wires the official Pydantic AI multi-turn primitive (anti-pattern: re-passing conversation in request body and ignoring `message_history`).

2. **Dynamic-instructions invocation** test: callable invoked per-turn with current state. Use `MagicMock` wrapper around the callable; assert call count >= turn count and that `state.missing` is referenced. Anti-pattern: static `instructions=string` that bakes routing rules into the prompt.

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
