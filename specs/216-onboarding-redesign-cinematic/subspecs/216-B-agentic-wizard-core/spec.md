# Subspec 216-B — Agentic Wizard Core

**Parent**: `specs/216-onboarding-redesign-cinematic/spec.md` FR-03, FR-04, FR-05, NR-01, NR-02, NR-06
**PR boundary**: 216-B (depends on 216-A merged)
**Estimated**: ~350 LOC (agent + prompts + state extension + API endpoint) + ~250 LOC tests
**Status**: Draft (GATE 1)

---

## Scope

The conversation agent at the heart of the wizard. Implements:
1. Extended `WizardSlots` (12 fixed roots) + `FinalForm` cross-field validation gate.
2. Pydantic AI 1.71.0 agent with `output_type=[TurnOutput, TurnFailure]` discriminated union, `instructions=callable` per-turn injection, `@output_validator + ModelRetry`, `message_history`, `capture_run_messages`.
3. M1-M4 meta-prompt set: `GenerateFollowUpFromAnswer`, `ClassifyAnswerCluster`, `RefineSummary`, `DetectSaturation`.
4. Static fallback registry (`follow_up_registry.yaml`) with paired `static_fallback_question` per dynamic node.
5. New API endpoint `POST /api/v1/onboarding/answer` replacing legacy `POST /converse`.
6. Anthropic prompt caching on FIXED skeletons (NR-02).

Replaces / deletes:
- `nikita/agents/onboarding/conversation_prompts.py:33-115,128` `_WIZARD_FRAMING` static framing block.
- `nikita/agents/onboarding/regex_fallback.py:47` `regex_phone_fallback` (FE controls phone format now).
- `nikita/api/routes/portal_onboarding.py:799-1231` legacy `/converse` route.

Closes W3 GH #441 (completion gate) + #443 (mirror echo) + #444 (converse_reply_reject) + #442 (identity ambiguous).

## Acceptance Criteria

| AC | Description | Severity |
|----|-------------|----------|
| **B1.1** | `WizardSlots` extended to 12 fixed-root slots: split identity → `display_name`, `age`, `occupation`; add `primary_hobbies`, `saturday_morning`, `geek_out_on`, `together_we_could`, `same_weird_if`, `voice_tone_pref`, `backstory_pick`. Existing `city`, `darkness_level`, `phone` retained. | CRIT |
| **B1.2** | `FinalForm.model_validate(state.slots_dict)` is the ONLY completion gate. NO `is_complete = True/False` boolean literal anywhere in `/onboarding/answer` handler or `WizardState` derivation. | CRIT |
| **B1.3** | Conversation agent uses `output_type=[TurnOutput, TurnFailure]` discriminated union (Tool Output mode default). NativeOutput / PromptedOutput NOT used. | CRIT |
| **B1.4** | `instructions=callable` (`inject_per_turn_context`) injects per-turn `state.missing` + `next_slot_hint` + cumulative state summary + `last_slot_kind` + `last_value`. Static `system_prompt` is NOT used for routing rules. | HIGH |
| **B1.5** | `@agent.output_validator` rejects (a) mirror-echo `name * 2 in reaction.lower()` when `last_slot=="name"` (closes #443), (b) `len(reaction) > 140`, (c) M2 cluster confidence <0.6 AND `cluster != "ambiguous"`. Each `raise ModelRetry(...)` with specific guidance. `Agent(retries=2)`. | HIGH |
| **B1.6** | M1 `GenerateFollowUpFromAnswer` fires depth-1 after each Hinge prose root (saturday_morning, geek_out_on, together_we_could, same_weird_if) AND after hobbies. Depth-2 ONLY when `cluster == "ambiguous"` AND `turn_count_for_topic < 3`. | HIGH |
| **B1.7** | M2 `ClassifyAnswerCluster` runs after every prose answer; result has confidence ≥0.6 OR triggers depth-2 follow-up via cluster=ambiguous path. | HIGH |
| **B1.8** | Total dynamic follow-ups capped at **6 across the wizard**. Cost circuit fires at $0.05 budget remaining (CostGuard sets `force_static_fallback=True`). | HIGH |
| **B1.9** | Static fallback registry (`nikita/agents/onboarding/follow_up_registry.yaml`) is consulted when (a) M1 generation final retry exhausted, (b) cost circuit active, OR (c) firecrawl tool times out. Lint test enforces every dynamic node has a paired `static_fallback_question`. | HIGH |
| **B1.10** | `agent.run(..., message_history=hydrate_message_history(state.messages), deps=deps)` — official multi-turn primitive. Request body does NOT re-pass conversation context. `result.new_messages()` appended to `nikita.conversation_jsonb` between turns. | CRIT |
| **B1.11** | `capture_run_messages` wraps every `agent.run`; on `UnexpectedModelBehavior`, log Cloud Run traceparent + messages + fall back to static fallback question. NEVER 500 to FE. (Closes #444.) | HIGH |
| **B1.12** | `progress_pct` is `@computed_field @property` on `WizardSlots`; monotonic non-decreasing across all turns. `min(100, int((TOTAL - len(self.missing)) * 100 / TOTAL))`. | CRIT |

## Critical Files

### Backend extensions
- `nikita/agents/onboarding/state.py:88-328` — extend `WizardSlots` from current shape to 12 fields. Add `@computed_field` `progress_pct`, `missing`, `slots_dict`. Add `FinalForm(BaseModel)` with non-optional fields + `@model_validator(mode="after")` for cross-field rules (age ≥18, voice_tone_pref + phone consistency).
- `nikita/agents/onboarding/conversation_agent.py:127-197` — REWRITE the agent definition block. Keep `TurnOutput` / `ConverseDeps` types at L69-126 (extend with new fields). Remove the 7 narrow `extract_*` tools.

### NEW files
- `nikita/agents/onboarding/follow_up_registry.yaml` (NEW) — keyed by `(slot_kind, cluster)`, value is `{static_fallback_question: str, why_we_ask: str, control_type: str}`.
- `nikita/agents/onboarding/cost_guard.py` (NEW or extend existing) — `CostGuard.check_budget(deps) -> bool`, fires at $0.05 remaining; integrated into `inject_per_turn_context` callable.

### REPLACED files
- `nikita/agents/onboarding/conversation_prompts.py` — replace `_WIZARD_FRAMING` block (L33-115) + `WIZARD_SYSTEM_PROMPT` assignment (L118) + `render_dynamic_instructions` (L128) with M1-M4 templates and a new `inject_per_turn_context(ctx: RunContext[ConverseDeps]) -> str` callable.
- `nikita/agents/onboarding/question_registry.py:42-79` — extend `ORDERED_QUESTIONS` from current 6 entries to 12 (one per fixed root).

### NEW endpoint
- `nikita/api/routes/portal_onboarding.py` — new `POST /api/v1/onboarding/answer` route. Request: `{slot_kind, value, turn_id?, conversation_id?}`. Response: `TurnOutput` + `progress_pct` + `is_complete` + `link_code?` (when complete).
- DELETE legacy `/converse` route at `:799-1231`.

### DELETED files
- `nikita/agents/onboarding/regex_fallback.py:47` — `regex_phone_fallback` removed (FE now sends E.164-formatted strings).

## M1-M4 Meta-Prompt Templates

All templates use `[FIXED]` skeleton + `[DYNAMIC]` `{{var}}` substitution markers; the `[FIXED]` block is wrapped in Anthropic prompt-cache markers.

### M1 — GenerateFollowUpFromAnswer

```
[FIXED]
Role: Generate ONE non-leading follow-up question for an AI-companion onboarding chat.
Voice: dark luxe, slightly menacing, ≤140 chars, no emoji, no markdown.
Output schema: DynamicFollowUp(question, why_we_ask, references_state)
Rules:
- Reference at least ONE detail from the user's last answer (paraphrase, never echo verbatim).
- NEVER use "don't you" / "wouldn't you" / leading phrases.
- Use "What" or "How" — never "Why".
- The question MUST advance signal on the cluster, not the same axis the user already covered.

[DYNAMIC]
Last topic: {{slot_kind}}
Last answer (redacted): {{slot_value_redacted}}
Detected cluster: {{cluster}} (confidence {{confidence}})
Cumulative state summary: {{state_summary}}
Forbidden topics this turn: {{forbidden_list}}
```

### M2 — ClassifyAnswerCluster

```
[FIXED]
Role: Classify a user's prose answer into one of {{slot_kind}}'s 4-6 cluster taxonomy.
Output: AnswerCluster(cluster: Literal[...], confidence: float ∈ [0,1])
If you cannot classify with confidence ≥0.6, return cluster="ambiguous", confidence=<actual>.

[DYNAMIC]
Slot: {{slot_kind}}
Allowed clusters: {{cluster_enum}}
User answer (redacted): {{user_answer_redacted}}
```

Per-slot cluster taxonomies (locked in question_registry.py):
- **hobbies** (6): aesthete / kinetic / digital_nomad / homemaker / nightlife / outdoorsy / ambiguous
- **saturday_morning** (4): movement / quiet / social / chaos / ambiguous
- **geek_out_on** (4): hands-on / system / culture / human / ambiguous
- **together_we_could** (5): risk / refuge / craft / discovery / ritual / ambiguous

### M3 — RefineSummary

```
[FIXED]
Role: Compress conversation_jsonb history into ≤2 sentences for system-prompt injection.
Voice: third-person, factual, no editorializing.
Output: PromptSummary(text: str)

[DYNAMIC]
Conversation turns: {{turn_count}}
Slots filled: {{slots_summary}}
Latest 3 user messages: {{recent_messages}}
```

Fires when cumulative state summary >300 tokens (rough heuristic).

### M4 — DetectSaturation

```
[FIXED]
Role: Decide continue-or-stop on dynamic follow-up depth for the current topic.
Output: SaturationSignal(decision: Literal["probe","move_on"], reason: str)
HARD OVERRIDES:
- If turn_count_for_topic >= 2 → "move_on"
- If cluster == "ambiguous" AND turn_count_for_topic < 3 → "probe"
- If any Big5 dimension confidence ≥0.7 for an axis the topic could probe → "move_on"

[DYNAMIC]
Topic: {{slot_kind}}
Turn count for topic: {{turn_count}}
Cluster: {{cluster}}
Big5 confidence vector: {{big5_confidence}}
Cost budget remaining: {{cost_budget}}
```

## Tests to Write

| Test File | Focus | AC |
|-----------|-------|-----|
| `tests/agents/onboarding/test_cumulative_state.py` | Rule #1 monotonicity (12 turns), `model_copy(update={...})` immutability, slots accumulate not replace | B1.1, B1.12 |
| `tests/agents/onboarding/test_completion_gate.py` | empty/partial/full FinalForm.model_validate triplet | B1.2 |
| `tests/agents/onboarding/test_tool_recovery.py` | mock LLM emits wrong-tool-args, `@output_validator` raises ModelRetry, agent retries succeed | B1.5 |
| `tests/agents/onboarding/test_meta_prompts.py` | M1-M4 golden snapshot outputs (LLM-stub fixtures) | B1.6, B1.7 |
| `tests/agents/onboarding/test_cluster_enum_completeness.py` | every Literal cluster value across all slots has paired template entry | B1.7 |
| `tests/agents/onboarding/test_follow_up_registry_completeness.py` | every dynamic node has a `static_fallback_question` | B1.9 |
| `tests/agents/onboarding/test_cost_circuit.py` | over-budget mock LLM falls back to static registry | B1.8, B1.9 |
| `tests/api/routes/test_onboarding_answer.py` | POST /onboarding/answer end-to-end with mocked agent | B1.10, B1.11 |
| `tests/agents/onboarding/test_message_history_wiring.py` | `agent.run` receives `message_history`, `result.new_messages()` appended | B1.10 |
| `tests/agents/onboarding/test_capture_run_messages.py` | `UnexpectedModelBehavior` triggers fallback, no 500 | B1.11 |
| `tests/agents/onboarding/test_progress_monotonic.py` | 12-turn fixture, `progress_pct[t+1] >= progress_pct[t]` for all t | B1.12 |
| `tests/agents/onboarding/test_dynamic_instructions_invocation.py` | callable invoked per turn, references `state.missing` (anti-static-prompt) | B1.4 |

## Implementation Notes

- **Discriminated union output**: `output_type=[TurnOutput, TurnFailure]`. The agent emits `TurnFailure(explanation=str)` in-character when the user-submitted slot value cannot be processed (underage, abusive, etc.) — no exceptions thrown, FE treats as "graceful re-ask".
- **Anthropic prompt cache markers**: ensure the `[FIXED]` block of M1-M4 + base `inject_per_turn_context` skeleton is emitted as a single contiguous block at the start of the system message, with cache_control breakpoint after. Verify ≥60% cache hit rate in Cloud Run logs (NR-02).
- **`hydrate_message_history`**: existing helper at `nikita/agents/onboarding/message_history.py:44` (REUSE; no rewrite needed).

## Open Questions

- **Q1**: Should `TurnFailure` be persisted to `conversation_jsonb` like `TurnOutput`, or only logged?
- **Q2**: Cluster confidence threshold — use 0.6 (M2 acceptance) and 0.7 (M4 short-circuit), OR unify? Default: separate; review post-50-flow telemetry.
- **Q3**: M3 RefineSummary firing threshold — 300 tokens is a guess; instrument and recalibrate.

## References

- Master spec FR-03, FR-04, FR-05, NR-01, NR-02, NR-06
- `.claude/rules/agentic-design-patterns.md` — 6 hard rules (cumulative state, Pydantic gate, tool consolidation, monotonic progress, validation layering, message_history)
- Pydantic AI doc: https://ai.pydantic.dev/output/, https://ai.pydantic.dev/agents/, https://ai.pydantic.dev/message-history/
- BiasBusters arXiv:2510.00307 — quantified tool-selection bias (motivates B1.3 single-tool consolidation)
- W3 walk findings #441, #442, #443, #444
