# Pydantic AI Best Practices for Dynamic Info-Collection — Research Synthesis (2026-04-28)

**Audience**: Spec 216 implementer (Nikita onboarding wizard, Pydantic AI 1.25+, one-question-per-screen UI with agent-driven reactions).
**Method**: Pydantic AI official docs (ai.pydantic.dev, retrieved 2026-04-28), arXiv 2510.00307 (BiasBusters), Sierra/Decagon engineering blogs, UX best-practice surveys. Where a source could not be retrieved with sufficient depth (e.g., Decagon, Forethought, Maven AGI, Arini private blogs without engineering-detail posts), this is stated explicitly.

## TL;DR — Top 5 principles for the Nikita onboarding wizard

1. **One agent, discriminated-union `output_type`, Tool Output mode.** Use `output_type=[SlotDelta, ClarifyingQuestion]` (or similar) and let Pydantic AI's default Tool Output mode + `end_strategy='early'` handle dispatch. Refuse the Walk V `extract_*` fan-out anti-pattern.
2. **Cumulative state in `deps_type` + `WizardSlots(BaseModel)` with `@computed_field` `progress_pct`.** State is the union of extractions; each turn merges via `model_copy(update=...)`. Persist to JSONB on user row; rehydrate on every wizard load.
3. **Completion gate is `FinalForm.model_validate(state)` — never a literal.** A Pydantic model with all required slots non-optional + cross-field `@model_validator(mode='after')` IS the gate. No `complete = False` constants in handler code.
4. **Dynamic `instructions=callable`** that injects `state.missing` per turn, plus `@output_validator` raising `ModelRetry` on cross-field violations, plus deterministic regex fallback for high-stakes slots (phone, age). Three layers of validation, all required.
5. **Multi-turn via official `message_history=` + `result.new_messages()`.** Do not reinvent context in the request body. Persist `ModelMessagesTypeAdapter`-serialised messages to DB and rehydrate. Use `history_processors` for token budget pruning when the conversation runs long.

---

## 1. Structured-output extraction patterns

Pydantic AI 1.25 supports three output modes (`ai.pydantic.dev/output/`, retrieved 2026-04-28):

- **Tool Output (default)** — output schema rendered as a special tool. Works on virtually every model. Recommended for wizard slot extraction.
- **Native Output** — model's own structured-output JSON-schema feature. Fewer model integrations; Gemini cannot mix native output with regular tools.
- **Prompted Output** — JSON schema injected into instructions, plain-text response parsed. Lowest reliability; use only when no other option.

**Discriminated-union output**: `output_type=[Schema1, Schema2]` registers each as its own output tool. With `ToolOutput(Schema1, name='return_x')` you get explicit naming. A single union (`Schema | str`) gives the agent a structured-OR-free-text escape hatch — exactly what the Walk V remediation calls for. The "first matching output ends the run" semantics combined with `end_strategy='early'` (default) prevents the model from emitting multiple competing extractions.

**Per-slot mini-agents vs single agent**: comparable products (Sierra's "constellation of models", `sierra.ai/blog/constellation-of-models`) decompose by *capability* (retrieval, classification, policy), not by per-slot extraction. Per-slot agents multiply token cost N-fold and lose cross-slot context. **Recommendation for Spec 216: one agent, one cumulative-state Pydantic model, discriminated-union output.**

**Streaming**: `agent.run_stream()` + `result.stream_output()` yields partial structured output validated incrementally (Pydantic's `experimental_allow_partial`). Useful for showing typing/reaction UI while the slot fills, but the *gate* must be on the final, full state.

## 2. Output validators + `ModelRetry` self-healing

From `ai.pydantic.dev/agent#reflection-and-self-correction` and `api/exceptions#ModelRetry`:

- **`@agent.output_validator`** runs after structured output is parsed. Raise `ModelRetry("explanation")` to feed the validation error back to the model with a retry-message; the model re-emits.
- **Default retries: 1 per agent run; configurable per-agent, per-tool, per-output.**
- **Per-tool validation** is automatic — Pydantic-validates tool args; failure → `ModelRetry` to the model.

**Defense in depth (Walk V remediation)**: layer three checks for high-stakes slots like phone numbers, where LLM tool-selection bias is documented (BiasBusters arXiv:2510.00307):

1. Pre-tool: Pydantic field validators on the slot type.
2. Post-tool: `@output_validator` re-checking cross-field invariants (e.g., voice-requires-phone, age ≥ 18).
3. Deterministic fallback: regex/heuristic post-processor that can override or rescue when the LLM emits the wrong extraction kind.

This matches `.claude/rules/agentic-design-patterns.md` Hard Rule 5.

## 3. Dynamic instructions

`Agent(instructions=callable)` re-renders the system prompt every turn. The callable receives `RunContext[deps_type]`, so it has access to the current cumulative-state object.

```python
def render_instructions(ctx: RunContext[Deps]) -> str:
    state = ctx.deps.slots
    missing = state.missing
    return f"... You still need to collect: {', '.join(missing)} ..."
```

**Why dynamic, not static**: a static prompt with hardcoded routing rules ("if user mentions a city, call extract_location") is the PR #395 Walk V anti-pattern. Static prompts compound across N tools because the model has to remember which slot is filled. Dynamic injection of `state.missing` gives the LLM the live "what's left" view and dramatically reduces tool-selection bias. Sierra's docs describe a similar pattern — capabilities are composed at runtime, not baked into a monolithic prompt.

## 4. Multi-turn state management

**Canonical pattern (`ai.pydantic.dev` message-history docs, retrieved 2026-04-28)**:

```python
result1 = agent.run_sync('Hi')
result2 = agent.run_sync('More', message_history=result1.new_messages())
```

`message_history` carries `ModelRequest`/`ModelResponse` objects including system prompt, tool calls, tool returns. **If `message_history` is non-empty, a new system prompt is NOT generated** — Pydantic AI assumes the history already contains it. For frontends or DBs that strip system prompts, add the `ReinjectSystemPrompt` capability so the agent's configured prompt is re-prepended.

**Persistence**:

- `ModelMessagesTypeAdapter` from `pydantic_ai.messages` serialises the full message list to JSON-compatible Python objects (and back).
- Store the JSON blob (or `to_json(...)`) on the user row. On wizard reload, deserialise + pass as `message_history`.
- Cumulative `WizardSlots` state is *separate*: it lives in `deps_type` and is reconstructed by replaying extractions (or stored alongside).

**Long-conversation pruning**: `history_processors=[summarize_old_messages, keep_recent_5]` lets you cap token cost. The docs warn explicitly: when slicing, ensure tool-call/tool-return pairs stay together, else the model errors. For a wizard with ≤10 turns this is rarely needed, but worth knowing.

## 5. Tool patterns for live context

Tools are functions the LLM can invoke for side-effect-free reads (web fetch, DB lookup) or actions. Two registration styles:

- `@agent.tool` decorated function with `RunContext[Deps]` first param + Pydantic-typed kwargs. Pydantic auto-generates the JSON schema from type hints + docstring.
- Async tools work the same; just `async def`.

**Prepare functions**: `prepare_tools` and `prepare_output_tools` accept a `RunContext + list[ToolDefinition]` and return the filtered list. Per-step tool gating means you can hide irrelevant tools when a slot is already filled — the principal mitigation BiasBusters recommends (filtering candidate APIs to a smaller subset before the LLM picks).

**Tool fan-out vs consolidation**: BiasBusters (arXiv:2510.00307) shows tool selection bias persists across 7 LLMs — models fixate on a single provider or favour earlier-listed tools. Their lightweight mitigation (smaller LLM filters relevant APIs, then uniform sampling) cut API bias from 0.338 to 0.108 and combined bias from 0.380 to 0.094. **Practical implication for the wizard: 1 extraction tool with discriminated-union args, not 7 narrow `extract_*` tools.** When a tool fan-out IS needed, use `prepare_tools` to surface only the tools relevant to currently-missing slots.

**Cost guards**: track `RunContext.usage.total_tokens`; cap turns; circuit-break web-tool calls per session.

## 6. Live web/context-fetching for personalization

Pydantic AI 1.25 ships **built-in tools** that can be added to any agent:

- `WebSearchTool` (provider-backed search; Anthropic + OpenAI support per docs).
- `ToolReturn` for non-text payloads (images, structured blobs).

For Spec 216-style "fetch a cultural fact about the user's city" personalisation:

- **Custom tool wrapping Firecrawl/HTTPX** is straightforward — `async def` + `httpx.AsyncClient` injected via `deps`. Cache results in Redis or on the user row for at most the wizard session; re-fetching the same city across turns is wasteful and adds latency.
- **Failure modes to handle in the tool body**: timeout (return graceful "no fresh data" string the agent can ignore), web-source down (tool returns empty; agent falls back to its training prior), citation hallucination (validate URLs the model emits in narratives — see §7).

Citations: Sierra's reliability blog (`sierra.ai/blog/enterprise-grade-agents`, retrieved 2026-04-28) describes adaptive routing across model providers to maintain >99% uptime — a pattern relevant for the persona-narrative agent if it has a hard latency budget.

## 7. Backstory / persona generation patterns

(No first-party Pydantic AI doc on persona generation; principles from broader 2025 LLM literature + Pydantic v2 patterns.)

- **Few-shot vs free-form**: few-shot examples bias the model toward the example shape — but per `.claude/rules/review-findings.md` few-shot echo rule, hardcoded canonical strings get mirrored verbatim. For backstory, use *parameterised* examples (placeholders for city/age/vice) so the model imitates structure, not literal phrases.
- **Validation**: `BackstoryOutput(BaseModel)` with `length: int` (computed_field), `tone: Literal['warm', 'neutral']`, `mentions_pii: bool`. `@model_validator(mode='after')` enforces no raw email/phone leak.
- **Diversity (3-variants problem)**: ask the agent for 3 candidates in one structured-output call (`output_type=list[BackstoryOutput]` constrained to length 3), validator enforces lexical diversity (Jaccard overlap < 0.5 across variants). Cheaper and more diverse than 3 separate runs.

## 8. Comparable products — what the engineering blogs reveal

**Sierra** (`sierra.ai/blog/constellation-of-models`, `agent-os-2-0`, retrieved 2026-04-28):
- Decomposed agents by *capability* (retrieval, classification, tools, policies, tone), not by per-slot extraction.
- "Constellation" routes each subtask to the best-fit model from OpenAI/Anthropic/Meta via an adaptive routing client.
- Supervisors enforce guardrails on agency-rich tasks.
- Take-away for Spec 216: borrow the capability-decomposition idea (extraction agent vs persona-narrative agent are *separate* Pydantic AI agents sharing state via `deps`), but stay single-model unless latency demands routing.

**Decagon** (per `quiq.com/blog/sierra-ai-vs-decagon`, `cresta.com/guides/decagon-vs-sierra`, retrieved 2026-04-28):
- Public material is product-marketing; their "Agent Operating Procedures" (AOPs) let non-technical staff express logic in near-natural-language. No engineering detail accessible.
- Take-away: keep configuration declarative — slot definitions in YAML/Pydantic, not buried in prompt strings — so non-engineers can iterate on copy without touching the agent runtime.

**Forethought, Maven AGI, Arini.ai**: no public engineering blog with relevant detail at the depth needed (verified via search 2026-04-28). All three describe outcomes (deflection rates, integration breadth) without architectural specifics. **Failed citation; not relying on these.**

**UX (mindtheproduct, lollypop.design, parallelhq, retrieved 2026-04-28)**: progressive disclosure (one question at a time), context retention across turns, balanced input (open text + quick-reply buttons), graceful error recovery — all directly applicable to the wizard.

## 9. Anti-patterns

| Anti-pattern | Source | Why bad |
|---|---|---|
| Per-turn snapshot state (`progress_pct = compute(latest_extraction)`) | Walk V, ADR-009, `nikita/api/routes/portal_onboarding.py:1086-1100` | Loses monotonicity; model can "uncomplete" the wizard. |
| Tool fan-out (7 narrow `extract_*` tools + sentinel) | Walk V, `nikita/agents/onboarding/conversation_agent.py:106-229` | Tool-selection bias (BiasBusters) → wrong slot extracted. |
| LLM-judged completion gate (`agent decides done`) | Common LLM-app smell | Non-deterministic; model can over- or under-claim completion. |
| Static system prompt with hardcoded routing rules | Walk V PR #395, `conversation_prompts.py` `_WIZARD_FRAMING` | Doesn't reflect cumulative state; rules conflict as state evolves. |
| Mock-LLM tests that always emit the right tool | Common test smell | Hides tool-selection bias; PR passes; production fails. |
| Re-passing conversation in request body, ignoring `message_history=` | Common Pydantic AI mistake | Agent has no chat-history context; system prompt re-injection fights the model. |
| Few-shot canonical strings in persona prompts | GH #200 / PR #256, `.claude/rules/review-findings.md` | Model echoes the literal phrasing into output. |

## 10. Concrete recommendations for Spec 216

1. **Single agent** `wizard_agent = Agent('claude-sonnet-X', deps_type=Deps, output_type=[SlotDelta, ClarifyingQuestion], instructions=render_instructions)`. Refuse the per-slot-agent shape.
2. **`WizardSlots(BaseModel)`** with one optional field per slot + `@computed_field def missing()` + `@computed_field def progress_pct()`. All updates via `state = state.model_copy(update={...})`. File: new `nikita/agents/onboarding/state.py`.
3. **`FinalForm(BaseModel)`** with all slots non-optional + `@model_validator(mode='after')` for cross-field rules. The completion check is `try: FinalForm.model_validate(state.model_dump()); except ValidationError: not_complete`. Replace `nikita/api/routes/portal_onboarding.py:1025` literal.
4. **`render_instructions(ctx)` callable** that injects `ctx.deps.slots.missing` and the slot's prompt copy. Replace `_WIZARD_FRAMING` static prompt in `conversation_prompts.py`.
5. **`@wizard_agent.output_validator`** that re-runs cross-field rules and raises `ModelRetry("you missed slot X — ask again")` on regression. Configure `retries=2` at agent level.
6. **Deterministic regex post-processor** for phone, email, age. Run after the agent returns; merge into `SlotDelta` if the agent missed it. File: `nikita/agents/onboarding/heuristics.py`.
7. **`message_history` round-trip**: `ModelMessagesTypeAdapter.dump_json(result.new_messages())` on save; `validate_json` on load. Persist on user row alongside `WizardSlots` JSONB. Use `hydrate_message_history` (`nikita/agents/onboarding/message_history.py:44`).
8. **Live-context tool**: 1 async tool `fetch_city_context(city: str)` returning a structured `CityContext(BaseModel)`. Cache by city in-memory for the wizard session. Token-budget cap: ≤300 tokens of context per call.
9. **Backstory generator**: separate `narrative_agent = Agent(..., output_type=list[BackstoryVariant])` with a length-3 constraint and lexical-diversity validator. Run once after wizard completion, not per-turn.
10. **Tests**: per `.claude/rules/testing.md`, three mandatory classes — cumulative-state monotonicity (≥3 turns asserts `progress_pct[t+1] >= progress_pct[t]`), completion-gate triplet (empty/partial/full → False/False/True), mock-LLM-emits-wrong-tool recovery. Add a 4th: dynamic-instructions invocation count = turn count, with `state.missing` referenced.

## Sources

All retrieved 2026-04-28.

- Pydantic AI Output docs: https://ai.pydantic.dev/output/ (output modes, ToolOutput/NativeOutput/PromptedOutput, streaming structured output, StructuredDict)
- Pydantic AI Message History: https://github.com/pydantic/pydantic-ai/blob/main/docs/message-history.md (`message_history=`, `new_messages()`, `ModelMessagesTypeAdapter`, `ReinjectSystemPrompt`, `history_processors`)
- Pydantic AI Agent (reflection / ModelRetry): https://ai.pydantic.dev/agent#reflection-and-self-correction
- Pydantic AI Exceptions (ModelRetry): https://ai.pydantic.dev/api/exceptions#pydantic_ai.exceptions.ModelRetry
- Pydantic AI Tools / Dependencies: https://github.com/pydantic/pydantic-ai/blob/main/docs/dependencies.md
- BiasBusters (tool-selection bias): https://arxiv.org/abs/2510.00307 (also https://arxiv.org/html/2510.00307)
- Sierra constellation-of-models: https://sierra.ai/blog/constellation-of-models
- Sierra Agent OS 2.0: https://sierra.ai/blog/agent-os-2-0
- Sierra enterprise-grade agents: https://sierra.ai/blog/enterprise-grade-agents
- Decagon vs Sierra (third-party comparisons; product-marketing depth only): https://quiq.com/blog/sierra-ai-vs-decagon/, https://cresta.com/guides/decagon-vs-sierra
- Chatbot UX best practices 2025-2026: https://www.mindtheproduct.com/deep-dive-ux-best-practices-for-ai-chatbots/, https://www.parallelhq.com/blog/ux-ai-chatbots, https://lollypop.design/blog/2025/january/chatbot-ui-ux-design-best-practices-examples/

**Failed citations (acknowledged, not relied on)**: Forethought, Maven AGI, Arini.ai engineering blogs — public material is product-marketing only; no architectural detail accessible at search depth.

**Pydantic AI version cited**: docs at `ai.pydantic.dev` reflect Pydantic AI's main branch as of 2026-04-28; examples reference `gpt-5.2` and `gemini-3-flash-preview` model IDs, consistent with 1.25+. Verify the project's pinned version against the spec when implementing.
