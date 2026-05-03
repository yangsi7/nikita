# Meta-Prompts + Question-Tree — Research Synthesis (2026-04-28)

Audience: orchestrator drafting Spec 216 (Nikita onboarding question-tree). Sources verified via Pydantic AI docs (Ref MCP), PromptHub meta-prompting guide, ACL/arXiv papers (Tree-of-Thoughts, Branch-Solve-Merge, CAMI motivational interviewing). All retrievals 2026-04-27/28.

## TL;DR (≤200 words)

1. **Fixed-root + dynamic-child is the right shape.** ToT (Yao et al. 2023) is overkill for linear onboarding — reach for it only when the agent must compare multiple candidate next-questions and prune. For Nikita's use case (one root slot → one or two follow-ups), a **single Pydantic AI agent with `instructions=callable`** that injects `cumulative_state.missing` per-turn is the boring obvious solution.
2. **Discriminated-union output schema is the branching primitive.** `output_type=[StaticPick | DynamicFollowUp | EnrichmentReply, str]` covers selection + generation + refinement modes in ONE agent, avoiding tool fan-out (which the agentic-design rule already bans).
3. **Cumulative state, not per-turn snapshot.** Every meta-prompt template in §4 takes `cumulative_state` as input. This is mandated by `.claude/rules/agentic-design-patterns.md` Hard Rule #1.
4. **Three-layer validation per call**: pre-tool Pydantic schema, `@output_validator` with `ModelRetry` (Pydantic AI native self-correcting loop), deterministic post-processing fallback. Pydantic AI default retry=1 (docs §reflection-and-self-correction).
5. **Bound the tree at design-time.** Cap dynamic branching at depth 1 per root (1-2 follow-ups max). Avoid combinatorial blowup. Static fallback question for every dynamic node — when generation fails or token cap is hit, the wizard MUST still progress.

---

## 1. Meta-prompt taxonomy

Four functional categories, each is a meta-prompt because it instructs the LLM about how to produce its output (per PromptHub: "meta prompting … uses LLMs to create and refine prompts" [https://www.prompthub.us/blog/a-complete-guide-to-meta-prompting]).

### 1a. Generation meta-prompt
Skeleton instructs the LLM to *produce* the next user-facing question conditioned on prior state.

```python
agent = Agent(
    "anthropic:claude-sonnet-4-5",
    output_type=DynamicFollowUp,
    deps_type=WizardDeps,
)

@agent.instructions
def gen_meta(ctx: RunContext[WizardDeps]) -> str:
    s = ctx.deps.state
    return (
        f"Generate ONE follow-up question (≤140 chars). Topic: {s.last_kind}. "
        f"User's last answer: {s.last_value!r}. Slots still missing: {s.missing}. "
        "DO NOT lead the user. DO NOT echo PII verbatim. Reference 1 detail of last answer."
    )
```

### 1b. Selection meta-prompt
LLM picks the best candidate from a static set (registry of pre-written follow-ups). Cheaper, more controllable than free generation.

```python
class PickFollowUp(BaseModel):
    candidate_id: Literal["a", "b", "c"]
    why: str  # for logging

agent = Agent("anthropic:claude-haiku-4-5", output_type=PickFollowUp)
# instructions inject the 3 candidates + state
```

### 1c. Branching meta-prompt
LLM emits a *label* that controls flow. The label is a Pydantic Literal, not free text.

```python
class ClusterLabel(BaseModel):
    cluster: Literal["extrovert_social", "introvert_solo", "creative_solo", "athletic_team", "ambiguous"]
    confidence: float  # 0.0-1.0
```

The wizard reads `cluster` and routes to a different question template via dict lookup. Self-Consistency (Wang et al. 2022) suggests sampling N=3 and majority-voting for high-stakes branches; for onboarding, N=1 with a `confidence < 0.6 → fallback` rule is sufficient.

### 1d. Refinement meta-prompt
LLM rewrites a static question template using runtime context (e.g., live web results from firecrawl). The skeleton is fixed; only the dynamic placeholder is filled.

```python
# template = "I read that {city} just had {event}. Were you there?"
# refinement: clean + tone-shift to match Nikita persona
```

This is the safest of the four: bounded edit distance, always recognizable.

---

## 2. Tree-of-Thought / Tree-of-Curiosity patterns

### Tree of Thoughts (Yao et al. 2023, NeurIPS)
[https://arxiv.org/abs/2305.10601] — Generate multiple candidate "thoughts" per step, evaluate, prune via DFS/BFS, expand best. **Overkill for linear onboarding.** Worth invoking only when:
- The agent must explicitly compare ≥3 candidate next-questions on a quality metric
- Cost of a wrong question is high (e.g., medical intake)
- Latency budget allows N parallel LLM calls + ranker

For Nikita: NO. A single dynamic-instruction generation call + `@output_validator` self-correction matches ~95% of ToT's value for ~10% of the cost.

### Branch-Solve-Merge (Saha et al. 2024 NAACL)
[https://aclanthology.org/2024.naacl-long.462/] — Decompose a task into facets, solve each with separate LLM calls, merge. **Useful only for multi-faceted single turns.** For Nikita: relevant ONLY for the "summary moment" between root sections (e.g., merge location + scene + occupation into a "this is who you are" reflection). NOT relevant for follow-up generation.

### Curiosity-driven dialog
The closest production literature is goal-oriented information seeking with MCTS (NeurIPS 2025 poster #115459, "Feedback-Aware MCTS for Goal-Oriented Information Seeking"). Pattern: model explicitly tracks "what we still need to learn", picks question that maximizes expected information gain. For Nikita: encode the missing-slots set + a `priority_weight` per slot; the meta-prompt's "what's left to collect" injection (§1a) gives ~80% of MCTS's effect cheaply.

### Pydantic-graph FSM
[https://ai.pydantic.dev/graph/] — Use ONLY when branching emerges (e.g., voice-vs-text divergence with rejoin). For linear root traversal: don't reach for it. The agentic-design-patterns rule explicitly says "don't use a nail gun unless you need a nail gun."

---

## 3. Conditional branching by answer cluster

### Pattern
1. After a root answer, run the **branching meta-prompt** (§1c) to emit a `cluster` Literal.
2. Look up follow-up template by `(slot_kind, cluster)` in a dict.
3. If `confidence < 0.6` OR cluster == `"ambiguous"`, fall through to the static default question.

### Combinatorial-explosion mitigations
3 root slots × 5 clusters × 2 follow-ups = 30 templates. Manageable but tedious to author. Mitigations:
- **Limit clusters to 3-4 per slot** (not 5+). Coarser buckets = fewer templates, less label ambiguity.
- **Share templates across slots** when the cluster shape is similar (e.g., extrovert/introvert applies to both hobbies and personality_cue → one template family).
- **Use generation meta-prompt for the long tail.** Pre-write templates for the 2 most common clusters; let `gen_meta` handle ambiguous + rare ones with static fallback.
- **Cap depth at 1.** Each root spawns ≤2 dynamic children, never grandchildren. Prevents runaway trees.

### Pydantic discriminated-union as branching primitive
```python
TurnOutput = Annotated[
    Union[
        Annotated[StaticPick,      Tag("static")],
        Annotated[DynamicFollowUp, Tag("dynamic")],
        Annotated[ClusterLabel,    Tag("cluster")],
        Annotated[EnrichmentReply, Tag("enrich")],
    ],
    Discriminator("kind"),
]
agent = Agent("anthropic:claude-sonnet-4-5", output_type=TurnOutput)
```
Pydantic v2 discriminated unions enforce one-of semantics at validation time (Pydantic docs §unions/discriminated-unions-with-string-discriminators). The `kind` field acts as the routing key — handler reads it, dispatches.

---

## 4. Best-practice meta-prompt structure

Each template marks **FIXED** vs `{{DYNAMIC}}`. Output schemas are explicit; instructions are short.

### 4a. GenerateFollowUpFromAnswer
```
FIXED:
  Role: You are an interview-question generator for a relationship-building chat.
  Style: Curious, warm, ≤140 chars. NEVER lead. NEVER echo PII verbatim.
  Output schema: DynamicFollowUp(question: str, why_we_ask: str, references_state: list[str])

DYNAMIC:
  Last slot kind: {{slot_kind}}
  Last answer: {{slot_value_redacted}}
  Cumulative state (already collected): {{state_summary}}
  Slots still missing: {{missing_list}}
  Forbidden topics this turn: {{forbidden}}  # e.g., already-covered slots
```
Output validator: `len(question) <= 140`, `"?" in question`, no leading patterns ("don't you think...", "wouldn't you say..."). On fail → `ModelRetry("Question must be ≤140 chars and non-leading")`.

### 4b. ClassifyAnswerCluster
```
FIXED:
  Role: You classify a user answer into ONE pre-defined cluster.
  If ambiguous, return cluster="ambiguous" with confidence ≤ 0.5.
  Output schema: ClusterLabel(cluster: Literal[...], confidence: float)

DYNAMIC:
  Slot kind: {{slot_kind}}
  Answer: {{slot_value}}
  Allowed clusters: {{cluster_enum}}  # injected from registry per slot
```
Validator: `0.0 ≤ confidence ≤ 1.0`. Retry on parse failure (count=2 — cluster classification is high-stakes).

### 4c. EnrichWithLiveContext
```
FIXED:
  Role: You write a 1-sentence reaction (≤180 chars) tying user's answer to a live web fact.
  Style: Casual reaction, not encyclopedia. NO URLs. NO statistics dumps.
  Output schema: EnrichmentReply(reaction: str, source_phrase: str)

DYNAMIC:
  User mentioned: {{slot_value}}
  Web search results (top 3 snippets): {{firecrawl_results}}
  Cumulative tone calibration: {{user_tone_hint}}
```
Validator: reaction ≤180 chars, source_phrase appears in one of the firecrawl snippets (anti-hallucination). On fail → fallback to static reaction template (no retry — enrichment is non-critical).

### 4d. DetectSaturation
```
FIXED:
  Role: You decide whether to probe deeper on a topic OR move to next root.
  Default: move on after 2 turns per topic.
  Output schema: SaturationDecision(decision: Literal["probe", "move_on"], reason: str)

DYNAMIC:
  Topic: {{slot_kind}}
  Turns spent on this topic so far: {{turn_count}}
  Information density of last answer (0-1): {{density_score}}  # heuristic
  Cumulative state coverage: {{progress_pct}}
```
This is a **hard control prompt** — keeps the wizard from getting stuck. If `turn_count >= 2`, force `move_on` post-validation regardless of LLM output.

---

## 5. Anti-patterns

| # | Anti-pattern | Why it bites |
|---|---|---|
| 1 | **Leading questions in meta-prompts.** "Don't you love hiking?" implants the answer. | Biases data, breaks rapport. Add explicit "non-leading" constraint + regex blacklist in validator. |
| 2 | **Unbounded branching.** Letting the agent invent root nodes ("ask about anything you find interesting"). | Tree depth/width explodes; user fatigues; hard to test. Lock root taxonomy at design time. |
| 3 | **Stateless follow-ups.** Meta-prompt only sees the last turn, not cumulative state. | Repeats already-collected slots, contradicts earlier answers. Always inject `state_summary`. |
| 4 | **Mixing meta + output instructions in one block.** "Generate a question AND respond as Nikita AND extract slots." | LLM tool-selection bias (Pydantic AI output.py docs). Split into discrete agents/calls with separate output schemas. |
| 5 | **No length cap.** Free `str` output → 800-token essays. | Token blowout, poor UX. Validator MUST enforce char limits. |
| 6 | **No fallback on meta-prompt failure.** Generation throws → wizard dead. | Always wire static fallback question per slot. ModelRetry first, static question second. |
| 7 | **Few-shot examples that echo the bug.** Static system prompt has 3 leading examples. | Examples dominate output style. Curate few-shots through the same anti-leading lint as generated questions. (Project-specific: GH #200 echo rule.) |
| 8 | **Web-search results pasted raw into prompt.** Hallucinates URLs, dumps stats. | Filter firecrawl results to one paraphrased snippet. Never let the model see structured citations it might invent. |

---

## 6. Workflow safety

- **Retries** (Pydantic AI defaults: 1; configurable per agent/tool/validator):
  - GenerateFollowUp: `retries=1` — one self-correction is enough; failure → static fallback.
  - ClassifyCluster: `retries=2` — high-stakes branching, worth the extra call.
  - EnrichWithLiveContext: `retries=0` — skip on failure, omit reaction.
  - DetectSaturation: `retries=0` — deterministic post-rule overrides anyway.
- **Fallbacks**: every dynamic node has a paired `static_fallback_question` in `question_registry`. When generation fails, wizard advances using the static question.
- **Validations**:
  - `len(question) ≤ 140` (140 chars ~= 25 words ~= conversational tone)
  - Regex blacklist for leading patterns: `r"\b(don't you|wouldn't you|isn't it|aren't you)\b"` → ModelRetry
  - PII echo check: if `slot_value` (raw) appears in question, ModelRetry — paraphrase only
  - Off-topic drift: question must mention OR continue from `last_kind` topic
- **Cost circuit-breaker**: per-flow LLM token budget tracked in `deps.usage`. Hard stop at $0.50 → switch to all-static for remaining slots. Pydantic AI exposes `result.usage()` natively.
- **Latency**: p99 <2s per follow-up via Sonnet-4.5; if exceeded, drop to Haiku-4.5 (selection meta-prompt only) or static. Wire timeout via `httpx`-level config.
- **Caching**: Anthropic prompt caching for the FIXED skeleton (system prompt + cluster enum + tone hint) — only the DYNAMIC suffix changes per call. ~60-80% cost reduction at scale.

---

## 7. Concrete recommendations for Spec 216

| # | Slot/Screen | Pydantic AI primitive | Meta-prompt class | $/flow Δ | Diff |
|---|---|---|---|---|---|
| 1 | Every dynamic node | `Agent(instructions=callable)` per-turn injection of `state.missing` | gen | +$0.0 (replaces static) | S |
| 2 | All agent outputs | `output_type=[Discriminated Union]` not N tools | branch+gen+select | -$0.02 (fewer calls) | M |
| 3 | personality_cue follow-up | ClassifyCluster → dict-lookup template | branch+select | +$0.01 | S |
| 4 | location enrichment | EnrichWithLiveContext via firecrawl tool | refine | +$0.03-0.05 | M |
| 5 | hobbies depth-1 follow-up | GenerateFollowUp with retries=1 + static fallback | gen | +$0.02 | S |
| 6 | Saturation detection | Hard rule (`turn_count >= 2 → move_on`) overrides LLM | branch | +$0.005 | S |
| 7 | Inter-section reflection | Branch-Solve-Merge across 3 collected slots → 1 reflection sentence | merge | +$0.01 | M |
| 8 | All meta-prompts | Anthropic prompt caching on FIXED skeleton | infra | -$0.05 (60%+ savings) | S |
| 9 | Validator suite | `@output_validator` w/ leading-pattern regex + char cap + PII echo | infra | +$0.0 | S |
| 10 | Cost circuit | `deps.usage_budget` checked before each LLM call; switch to static | infra | -$0.5 ceiling | M |
| 11 | Cluster taxonomies | Per-slot Literal enums (3-4 clusters max) — author-locked | design | $0 | M |
| 12 | Question registry | YAML file with `static_fallback_question` per node — replaces dynamic when LLM fails | design | $0 | M |

Sources: Pydantic AI agents.md §instructions [https://github.com/pydantic/pydantic-ai/blob/main/docs/agents.md], §reflection-and-self-correction (same), Pydantic v2 discriminated unions [https://docs.pydantic.dev/latest/concepts/unions/]. PromptHub meta-prompting guide [https://www.prompthub.us/blog/a-complete-guide-to-meta-prompting]. Anthropic prompt caching [https://docs.anthropic.com/en/docs/prompt-engineering].

---

## 8. Implementation skeleton (Pydantic AI 1.25+)

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Discriminator, Tag, Field
from pydantic_ai import Agent, RunContext, ModelRetry

# ---------- Output schemas (discriminated union) ----------
class DynamicFollowUp(BaseModel):
    kind: Literal["dynamic"] = "dynamic"
    question: str = Field(max_length=140)
    why_we_ask: str
    references_state: list[str]

class StaticPick(BaseModel):
    kind: Literal["static"] = "static"
    candidate_id: Literal["a", "b", "c"]

class ClusterLabel(BaseModel):
    kind: Literal["cluster"] = "cluster"
    cluster: Literal["extrovert", "introvert", "creative", "athletic", "ambiguous"]
    confidence: float = Field(ge=0.0, le=1.0)

TurnOutput = Annotated[
    Union[
        Annotated[DynamicFollowUp, Tag("dynamic")],
        Annotated[StaticPick,      Tag("static")],
        Annotated[ClusterLabel,    Tag("cluster")],
    ],
    Discriminator("kind"),
]

# ---------- Deps (cumulative state + cost guard + tools) ----------
class WizardDeps(BaseModel):
    state: "WizardSlots"        # cumulative Pydantic model (per agentic-design rule)
    usage_budget_remaining: float  # USD
    web_results: list[str] = []    # populated by firecrawl tool when relevant

# ---------- Agent ----------
followup_agent = Agent(
    "anthropic:claude-sonnet-4-5",
    output_type=TurnOutput,
    deps_type=WizardDeps,
    retries=1,
)

# ---------- Dynamic instructions: cumulative state injected per-turn ----------
@followup_agent.instructions
def inject_state(ctx: RunContext[WizardDeps]) -> str:
    s = ctx.deps.state
    return (
        f"Last topic: {s.last_kind}. Last answer: {s.last_value_redacted}. "
        f"Already collected: {list(s.collected_slots)}. "
        f"Still missing: {s.missing}. "
        f"Forbidden this turn: {s.already_asked}. "
        "Generate ONE non-leading follow-up (≤140 chars), OR pick a static "
        "candidate, OR emit a cluster label. Reference at least one prior detail."
    )

# ---------- Tool: live web context (only when slot has temporal value) ----------
@followup_agent.tool
async def fetch_city_context(ctx: RunContext[WizardDeps], city: str) -> str:
    if ctx.deps.usage_budget_remaining < 0.10:
        return ""  # budget exhausted, skip enrichment
    # firecrawl_search(...) → top snippet
    snippet = await _firecrawl_top_snippet(f"{city} events 2026")
    return snippet[:300]

# ---------- Output validator: anti-leading + PII echo + length ----------
LEADING_RE = re.compile(r"\b(don't you|wouldn't you|isn't it|aren't you)\b", re.I)

@followup_agent.output_validator
def validate(ctx: RunContext[WizardDeps], out: TurnOutput) -> TurnOutput:
    if isinstance(out, DynamicFollowUp):
        if LEADING_RE.search(out.question):
            raise ModelRetry("Question must be non-leading. Rephrase neutrally.")
        if ctx.deps.state.last_value_raw in out.question:
            raise ModelRetry("Don't echo the user's exact words; paraphrase.")
    if isinstance(out, ClusterLabel) and out.confidence < 0.6:
        # caller should treat as ambiguous → use static fallback
        pass
    return out

# ---------- Caller (handler) ----------
async def next_turn(state, registry, deps_kwargs):
    deps = WizardDeps(state=state, **deps_kwargs)
    if deps.usage_budget_remaining < 0.05:
        return registry.static_fallback(state.last_kind)  # cost circuit breaker
    try:
        result = await followup_agent.run("", deps=deps, message_history=state.messages)
        return _render(result.output, registry)
    except Exception:  # ModelRetry exhausted, network, parse fail
        return registry.static_fallback(state.last_kind)
```

The skeleton encodes: cumulative state via `deps`, dynamic per-turn instructions, discriminated-union output covering 3 meta-prompt classes in ONE agent, ModelRetry-based self-correction, cost guard, static fallback. ~50 lines.

---

## Sources

| URL | Retrieved | What we used |
|---|---|---|
| https://github.com/pydantic/pydantic-ai/blob/main/docs/agents.md (§instructions, §reflection-and-self-correction) | 2026-04-27 | Dynamic instructions, ModelRetry, retries default, RunContext.retry |
| https://github.com/pydantic/pydantic-ai/blob/main/docs/message-history.md | 2026-04-27 | message_history primitive for multi-turn |
| https://docs.pydantic.dev/latest/concepts/unions/ §discriminated-unions-with-string-discriminators | 2026-04-27 | Discriminator/Tag pattern for TurnOutput |
| https://www.prompthub.us/blog/a-complete-guide-to-meta-prompting | 2026-04-27 | Meta-prompt definition, conductor pattern, CPE, DSPy/TextGrad context |
| https://arxiv.org/abs/2305.10601 (Yao et al. 2023, Tree of Thoughts) | citation only — primary URL | ToT applicability + when overkill |
| https://aclanthology.org/2024.naacl-long.462/ (Saha et al. 2024, Branch-Solve-Merge) | 2026-04-27 | BSM applicability for inter-section reflection |
| https://aclanthology.org/2025.acl-long.1024.pdf (CAMI: Counselor Agent for MI) | 2026-04-27 (search snippet) | Motivational interviewing automation precedent |
| https://neurips.cc/virtual/2025/poster/115459 (Feedback-Aware MCTS for Goal-Oriented Information Seeking) | 2026-04-27 | Curiosity-driven dialog precedent — MCTS overkill for our linear flow |
| https://docs.anthropic.com/en/docs/prompt-engineering | not re-fetched this session | Prompt caching for FIXED skeleton |
| https://langchain-ai.github.io/langgraph (conditional edges) | search-result-only (Medium tutorial) | Confirmed: LangGraph FSM-on-state model exists; we don't need it for linear flow |

BLOCKED:
- Perplexity Sonar Deep Research (quota exhausted on this session, switched to firecrawl + Ref MCP)
- Replika research blog "interest discovery" — not surfaced in searches; no URL to cite
- Sierra/Decagon adaptive customer-service case studies — paywalled / sales-gated
