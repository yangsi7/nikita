# Architecture Validation Report — Spec 216 Onboarding Redesign

**Spec**: `specs/216-onboarding-redesign-cinematic/spec.md` (master) + `subspecs/216-B-agentic-wizard-core/spec.md`
**Validator**: sdd-architecture-validator
**Status**: **PASS** (NEEDS_FIXES on 2 MEDIUM, 3 LOW — none blocking GATE 2)
**Timestamp**: 2026-04-29
**Reference**: `.claude/rules/agentic-design-patterns.md` (6 hard rules + 5 anti-patterns)

---

## Summary Verdict

The architecture is **structurally sound and properly aligned with all 6 hard rules** in `agentic-design-patterns.md`. Spec 216 explicitly inverts every documented anti-pattern from Walk V (2026-04-22). 216-B's AC table maps 1:1 to the rule file's six hard rules with no gaps. Pydantic AI 1.71.0 primitives are correctly applied: discriminated-union `output_type`, `instructions=callable`, `@output_validator + ModelRetry`, `message_history`, `capture_run_messages`, `@computed_field`, `@model_validator`.

- **CRITICAL**: 0
- **HIGH**: 0
- **MEDIUM**: 2
- **LOW**: 3

GATE 2 **may proceed**. Two MEDIUM items should be patched in spec text before /plan; three LOW items can be deferred to /clarify or /implement.

---

## Hard-Rule Conformance Matrix

| Rule | agentic-design-patterns.md requirement | Spec 216 location | Status |
|------|----------------------------------------|-------------------|--------|
| #1 Cumulative state | `WizardSlots` model with `model_copy(update={...})`, `@computed_field` for `missing` / `progress_pct` | FR-03 (master); B1.1, B1.12 (216-B) | PASS |
| #2 Pydantic completion gate | `FinalForm.model_validate(state.slots_dict)` triplet, NO boolean literal | FR-03 (master); B1.2 (216-B, CRIT) | PASS |
| #3 Tool consolidation | Single agent, `output_type=[TurnOutput, TurnFailure]` discriminated union; explicit "Remove the 7 narrow `extract_*` tools" | FR-04 (master); B1.3 (216-B, CRIT); Critical Files L48 | PASS |
| #4 Monotonic progress | `progress_pct` = `@computed_field` of cumulative slots; 12-turn monotonicity test | NR-01; B1.12 (CRIT); test `test_progress_monotonic.py` | PASS |
| #5 Validation layering | (a) Pre-tool Pydantic on `TurnOutput` schema, (b) `@output_validator` with `raise ModelRetry`, (c) deterministic post-processing for cluster confidence + mirror echo | FR-04 (master); B1.5 (216-B, HIGH) | PASS |
| #6 Official `message_history=` | `agent.run(..., message_history=hydrate_message_history(state.messages), deps=deps)`; "Request body does NOT re-pass conversation context"; `result.new_messages()` appended to JSONB | FR-04 (master); B1.10 (216-B, CRIT) | PASS |

All six hard rules have explicit, testable AC coverage. The rule's "Anti-Patterns" table at lines 36-44 is inverted point-for-point in the spec.

---

## Pydantic AI Primitives Conformance

| Primitive | rule-file requirement | Spec 216 evidence | Status |
|-----------|----------------------|-------------------|--------|
| `Agent(output_type=[X, str\|Y])` | Mixed mode | `Agent[ConverseDeps, TurnOutput \| TurnFailure]` w/ `output_type=[TurnOutput, TurnFailure]` (master FR-04 code block, L96-103) | PASS — uses `TurnFailure` (in-character graceful failure) instead of `str`. Stronger than `str`; correct. |
| `Agent(instructions=callable)` | Dynamic per-turn | `instructions=inject_per_turn_context` with explicit comment "ALWAYS reevaluated even with message_history" (master FR-04 L99); B1.4 enforces it (HIGH); test `test_dynamic_instructions_invocation.py` | PASS |
| `agent.run(..., message_history=)` | Multi-turn primitive | B1.10 explicit; `hydrate_message_history` reused from existing `nikita/agents/onboarding/message_history.py:44` | PASS |
| `Agent(deps_type=X)` + `RunContext[X]` | Sidecar state DI | `ConverseDeps` deps_type cited (FR-04, L101); RunContext referenced in firecrawl tool budget plumbing (FR-07) | PASS |
| `@agent.output_validator` + `raise ModelRetry` | Self-correcting loop | B1.5 (HIGH): mirror-echo, length, cluster-confidence each `raise ModelRetry(...)`; `Agent(retries=2)` | PASS |
| `@model_validator(mode="after")` | Cross-field | FR-03: `FinalForm` has `@model_validator(mode="after")` for age ≥18 + voice-requires-phone | PASS |
| `@computed_field @property` | Derived state | FR-03: `progress_pct`, `missing`, `slots_dict` on `WizardSlots`; B1.12 (CRIT) | PASS |
| `capture_run_messages` | Production debug | FR-04 + B1.11 (HIGH): wraps every `agent.run`; `UnexpectedModelBehavior` → log traceparent + fallback | PASS |
| Forbidden: `system_prompt` for routing | NOT REUSED with message_history | NR-01 explicit forbiddance; B1.4 explicit "Static `system_prompt` is NOT used for routing rules" | PASS |
| Forbidden: 7 narrow `extract_*` tools | tool-selection bias | NR-01 + 216-B Critical Files L48 "Remove the 7 narrow `extract_*` tools" | PASS |
| Forbidden: `pydantic-graph` FSM | overkill for linear flow | NR-01 explicit | PASS |

---

## Anti-Pattern Sweep (rule file lines 38-44)

| Anti-pattern (with file:line precedent) | Spec 216 inversion | Status |
|----------------------------------------|--------------------|--------|
| `_compute_progress(latest_kind)` per-turn snapshot at `portal_onboarding.py:1086-1100` | `progress_pct = @computed_field` of cumulative `WizardSlots`; 12-turn monotonicity test mandatory | PASS |
| 7 single-purpose `extract_*` tools at `conversation_agent.py:106..229` | Single agent, discriminated-union output, `extract_*` tools explicitly removed | PASS |
| Hardcoded slot-routing in static `_WIZARD_FRAMING` system prompt | M1-M4 templates + `inject_per_turn_context` callable; replaces `_WIZARD_FRAMING:33-115` | PASS |
| `progress = response.progress_pct` overwrite in FE reducer | BE = single source of truth (master Success Criteria + FR-03); FR-11 auto-redirect on BE-side `is_complete` | PASS |
| Boolean `complete = False` literal in route handler | B1.2 (CRIT) explicit "NO `is_complete = True/False` boolean literal anywhere in `/onboarding/answer` handler" | PASS |

No anti-patterns survive. Spec 216 is a deliberate inversion of the Walk V regression set.

---

## Module Organization & Boundaries

| Module | Role | Coupling | Status |
|--------|------|----------|--------|
| `nikita/agents/onboarding/state.py` | `WizardSlots` model + `FinalForm` cross-field validator + computed fields | Pure Pydantic; no I/O | CLEAN |
| `nikita/agents/onboarding/conversation_agent.py` | Agent definition (`output_type`, `instructions=`, `@output_validator`, `retries=2`) | Imports state + prompts; no DB | CLEAN |
| `nikita/agents/onboarding/conversation_prompts.py` | M1-M4 templates + `inject_per_turn_context` callable | Pure string-rendering; receives `RunContext` | CLEAN |
| `nikita/agents/onboarding/question_registry.py` | `ORDERED_QUESTIONS` (12 entries) + per-slot cluster taxonomies | Pure data; no logic | CLEAN |
| `nikita/agents/onboarding/follow_up_registry.yaml` (NEW) | Static fallback registry, keyed by `(slot_kind, cluster)` | YAML data; lint test enforces completeness | CLEAN |
| `nikita/agents/onboarding/cost_guard.py` (NEW) | `CostGuard.check_budget(deps)` → bool | Reads `RunContext.deps`; no LLM call | CLEAN |
| `nikita/agents/onboarding/message_history.py:44` | `hydrate_message_history` (REUSED, not rewritten) | Pre-existing, validated | CLEAN |

Boundaries are clean. State / agent-config / prompts / data-registry / cost-guard each have a single concern. No module imports another's internals (only public schemas + helpers).

---

## Type-Safety Conformance

`WizardSlots` (12 optional fields) → `FinalForm` (12 required + cross-field validator) → `slots_dict` is the canonical input/output transition. `TurnOutput` covers the success path; `TurnFailure(explanation: str)` covers in-character graceful failure. `SlotDelta` referenced in agentic-design-patterns.md as one variant of consolidated tool args; here the equivalent is the typed `TurnOutput` itself (the agent emits the next-question structure rather than per-slot deltas — the value is captured by control_type + control_options rather than re-typed). This is acceptable because slot-fill happens FE-side via the typed control, not via a structured tool call.

`ConverseDeps` is mentioned in FR-04 (`deps_type=ConverseDeps`) and 216-B Critical Files (extension at L69-126). Schema not enumerated in either spec — see MEDIUM finding M-1.

---

## Error Handling Architecture

| Layer | Mechanism | Location | Status |
|-------|-----------|----------|--------|
| Agent self-correction | `@output_validator` + `raise ModelRetry(...)` | B1.5 | PASS |
| Agent total failure | `capture_run_messages` + `UnexpectedModelBehavior` catch + traceparent log + static fallback | B1.11; FR-04 | PASS |
| Cost circuit | `CostGuard.check_budget` aborts at $0.05 remaining | B1.8; FR-12 | PASS |
| firecrawl tool timeout | 3s per call → cached fallback or static fallback (NEVER block) | FR-07; Edge-case 8 | PASS |
| M1 generation failure | `static_fallback_question` from registry | NR-06; B1.9 | PASS |
| FE-side validation edge case | "We hit a snag" + retry once + escalate to GH issue auto-create | Edge-case 12 | PASS |

Defense in depth across 3 layers (validator / capture / circuit) plus tool-level fallback. Per Rule #5.

---

## AC Traceability — Master FRs to 216-B Sub-ACs

The validator is scoped to architecture coverage in 216-B; other FRs route to 216-A/C/D/E/F.

| Master FR | Domain | 216-B sub-AC coverage | Notes |
|-----------|--------|------------------------|-------|
| FR-01 | Telegram routing | n/a (routes to 216-A) | OK |
| FR-02 | Wizard 12 slots | n/a (routes to 216-C; B1.1 extends `WizardSlots` to match) | OK |
| FR-03 | Cumulative state + FinalForm gate | **B1.1, B1.2, B1.12** | Full coverage |
| FR-04 | Agentic agent (`output_type`, `instructions`, `output_validator`, `message_history`, `capture_run_messages`) | **B1.3, B1.4, B1.5, B1.10, B1.11** | Full coverage |
| FR-05 | M1-M4 meta-prompt set | **B1.6, B1.7, B1.8, B1.9** | Full coverage |
| FR-06 | Big5 hidden inference | n/a (routes to 216-D) | OK |
| FR-07 | 4 firecrawl tools | n/a (routes to 216-E) | OK |
| FR-08 | Hobby chip multi-select | n/a (routes to 216-C) | OK |
| FR-09 | 3-card backstory selector | n/a (routes to 216-C/D) | OK |
| FR-10 | Visual identity | n/a (routes to 216-C) | OK |
| FR-11 | Idempotent magic-link + auto-redirect | n/a (routes to 216-A/C) | OK |
| FR-12 | Cost circuit + latency | partially in B1.8 (cost circuit fires at $0.05); latency p99 routes to 216-E | OK — see LOW L-2 |
| NR-01 | Pydantic AI primitives only | **B1.3, B1.4, B1.5, B1.10, B1.11** + forbidden list | Full coverage |
| NR-02 | Anthropic prompt caching | 216-B Implementation Notes mentions it; no explicit AC | LOW L-1 |
| NR-06 | Static fallback registry | **B1.9** | Full coverage |

No master-spec FR architectural concern is orphaned without 216-B coverage. Each FR routes correctly.

---

## Findings

### MEDIUM

**M-1**: `ConverseDeps` schema not enumerated.
- **Location**: master FR-04 (L101); 216-B Critical Files L48 ("extend with new fields") + Implementation Notes
- **Issue**: `Agent(deps_type=ConverseDeps)` is mentioned but the field set is not declared in either spec. Cost-guard plumbing (`RunContext.deps`), cohort cache key, traceparent, current `state.missing`, firecrawl budget, and per-turn `last_value` all flow through this type. Without an enumerated schema, /plan downstream may diverge across PRs (216-B vs 216-E vs 216-D).
- **Suggested fix**: Add a code block to 216-B Implementation Notes (or a new Critical Schema section) listing the 8-12 fields of `ConverseDeps` (e.g., `state: WizardSlots`, `state_summary: str`, `cost_budget_remaining_usd: float`, `last_slot_kind: SlotKind | None`, `last_value: str | None`, `traceparent: str`, `cohort_cache: dict`, `firecrawl_calls_this_turn: int`, `big5_confidence: dict[str, float]`).

**M-2**: `TurnOutput` `next_slot_kind: Literal[...] | None` literal members not enumerated.
- **Location**: master FR-04 L88
- **Issue**: The 12 fixed roots (display_name → backstory_pick) live in `question_registry.py:ORDERED_QUESTIONS` per 216-B Critical Files L56, but the `Literal[...]` membership in `TurnOutput.next_slot_kind` is not pinned to that enum. If they drift (e.g., 216-C renames `same_weird_if` → something else), the type system won't catch it — the agent could emit a slot kind that isn't in the registry.
- **Suggested fix**: Add an AC (B1.13) requiring `TurnOutput.next_slot_kind` to be `Literal[*ORDERED_QUESTIONS.keys()]` or an exported `SlotKind` `StrEnum` consumed by both the registry and the model. Add lint test `test_slot_kind_enum_completeness.py`.

### LOW

**L-1**: Anthropic prompt caching (NR-02) lacks an explicit AC in 216-B.
- **Location**: NR-02 master + 216-B Implementation Notes
- **Issue**: NR-02 demands ≥60% cache hit rate, but no AC enforces "FIXED block + cache_control breakpoint after". Implementation Notes mention it descriptively. Without an AC, /qa-review may not flag absence.
- **Suggested fix**: Add B1.13 (or B1.14 if M-2 takes 1.13): "M1-M4 FIXED skeleton + `inject_per_turn_context` base instructions are emitted as a contiguous prefix with Anthropic `cache_control` breakpoint after the FIXED block. Cloud Run logs show `cache_read_input_tokens / total_input_tokens >= 0.6` averaged over 10+ flows."

**L-2**: p99 latency budget per turn (8s, FR-12) lacks a 216-B test.
- **Location**: FR-12 master
- **Issue**: Latency-budget test belongs to 216-E or 216-F, but 216-B doesn't add a per-turn timing assertion (e.g., `agent.run` mock with delays simulates worst case).
- **Suggested fix**: Note in 216-B Implementation Notes that timing belongs to 216-F W4 walk + 216-E firecrawl 3s timeout test. Acceptable to defer.

**L-3**: `result.new_messages()` JSONB serialization shape not pinned.
- **Location**: B1.10
- **Issue**: "Append `result.new_messages()` to `nikita.conversation_jsonb`" — the wire shape (model_dump? dict? str?) is not specified. Agentic-design-patterns.md references `hydrate_message_history` for wire→ModelMessage; the spec reuses it (good). But the inverse (ModelMessage→wire on append) is not pinned. Drift here breaks resume mid-wizard (NR-07).
- **Suggested fix**: B1.10 implementation note: "Append messages via `[m.model_dump(mode='json') for m in result.new_messages()]` to maintain wire compatibility with `hydrate_message_history`. Test fixture: round-trip JSONB → hydrate → run → new_messages → JSONB without semantic loss."

---

## Validation Layering Coverage (Rule #5)

| Layer | Spec evidence | Test |
|-------|---------------|------|
| Pre-tool Pydantic on schema | `output_type=[TurnOutput, TurnFailure]` Tool Output mode → Pydantic enforces shape pre-emit | `test_completion_gate.py` covers FinalForm |
| Post-tool `@output_validator + ModelRetry` | B1.5 mirror-echo + length + cluster-confidence triplet | `test_tool_recovery.py` |
| Deterministic post-processing fallback | Cluster validator deterministic check + mirror-echo regex check (`name * 2 in reaction.lower()`) | `test_tool_recovery.py` covers wrong-tool-args recovery |

All three layers present. Note: regex_phone_fallback is being **deleted** (216-B replaced files L65) because FE controls phone E.164 format now — this is a layer-3 simplification, not a regression. FE-side validation IS the deterministic post-processing for phone.

---

## Recommendations (priority order)

1. **Patch M-1 in 216-B before /plan**: Enumerate `ConverseDeps` fields in a Critical Schema block. Affects 3+ PRs (B/D/E) coordination. ~10 min.
2. **Patch M-2 in 216-B before /plan**: Pin `TurnOutput.next_slot_kind` to a single enum source (`SlotKind` exported from `question_registry.py`). Affects type-safety across BE↔FE. ~15 min.
3. **Patch L-1 + L-3 during /clarify**: Add explicit ACs for Anthropic cache_control breakpoint placement (NR-02) and `result.new_messages()` JSONB serialization shape. ~20 min combined.
4. **Defer L-2 to /implement-216-F**: Latency budget test belongs to W4 walk + 216-E firecrawl tool tests; acceptable to leave 216-B silent.

---

## Verdict

**PASS for GATE 2 architecture criteria.** Zero CRITICAL, zero HIGH. Spec 216 architecture is the textbook inversion of Walk V's anti-pattern set and conforms to all 6 hard rules + all 8 Pydantic AI primitives + all forbidden-pattern checks in `agentic-design-patterns.md`. The 2 MEDIUM and 3 LOW findings are nail-down items that can be patched in spec text before /plan or absorbed into /clarify; none block GATE 2 progression.
