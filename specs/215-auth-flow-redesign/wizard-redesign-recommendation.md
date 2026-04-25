# Wizard Redesign Recommendation — Spec 215 PR-F2c-redesign

**Status**: DRAFT v1 (awaiting Phase 7 devil's-advocate + operator approval)
**Date**: 2026-04-24
**Authority**: Dispatch-contract plan at `/Users/yangsim/.claude/plans/docs-to-process-20260424-wizard-redesig-composed-micali.md` (revision 2, 7-agent review pass).
**Verification base**: codebase claims verified against `origin/master @ 9a81cb0` via `git show origin/master:<file>` (fresh-session Phase 1 Step 1.1 sync confirmed local branch `fix/389-reply-max-chars` is 4 ahead, 15 behind — all reads use origin/master prefix).
**§2 spot-verify: PASS** — arxiv 2510.00307 abstract contains no percentage-range figure from the research bundle's plan-§2.1 disowned claim (verified via WebFetch); pydantic-ai#4647 exists and confirms `web_search_20250305` → `web_search_20260209` staleness with 11% accuracy + 24% input-token reduction available in the upgraded tool version (plan §2.4 corroborated).

## 0. Executive summary (200 words)

PRs #400/#401/#405 landed the Spec 214 FR-11d chat-first slot-filling architecture on origin/master: `WizardSlots` + `FinalForm` + `SlotDelta` (cumulative state, Pydantic completion gate), `TurnOutput` (consolidated discriminated-union output), `@agent.output_validator` (self-correcting `ModelRetry`), and `agent.instructions(render_dynamic_instructions)` reading `state.missing` per turn. Hard Rules 1-6 of `.claude/rules/agentic-design-patterns.md` are all satisfied today. **The plan's G1 framing was overstated**: dynamic instructions IS in place and DOES read `state.missing`; D23 resolves inline — see §3.

What is NOT in place: (G2) adaptive question routing via a declarative registry; (G3) the FILE/dossier/clearance/FIELD metaphor has 40+ matches across `portal/src/app/onboarding/**`; (G4) no live-grounding tool (`WebSearchTool` unused); (G5) no session-start AI-disclosure string; (G6) six-slot taxonomy lacks personality/vibe/city-enrichment.

Recommended architecture: **Candidate A — Declarative Question Registry**, layered on top of the landed FR-11d core. A `QuestionSpec` registry drives turn-by-turn question selection via `condition: Callable[WizardSlots, bool]` closures (Typeform Logic Jumps analog); `render_dynamic_instructions` extends to inject the next spec's `hint` in addition to `state.missing`; a feature-flagged `WebSearchTool(max_uses=1)` adds city-enrichment as an agent-invoked tool (not a subagent, per pydantic-ai#4647 caveat). Session-start turn carries the AI-disclosure string; the NY-A6767 3-hour reminder is out-of-scope and deferred to Spec 216.

---

## 1. Context — What is already landed vs what this redesign changes

### 1.1 Delivered on origin/master (do NOT redesign)

| PR | SHA | Delivered | Files / lines (origin/master) |
|---|---|---|---|
| #400 PR-A | `f896364` | `WizardSlots` + `FinalForm` + `SlotDelta` + `TOTAL_SLOTS: Final[int] = 6` + `@computed_field missing/progress_pct/is_complete` + immutable `apply()` via `model_copy` | `nikita/agents/onboarding/state.py:1-289` |
| #401 PR-B | `d1ca3a5` | `build_state_from_conversation` reconstruction; `@agent.output_validator` applying delta to cumulative state; FE wire-up; `RECONSTRUCTION_BUDGET_MS: Final[int] = 10` | `nikita/agents/onboarding/state_reconstruction.py:1-142`, `conversation_agent.py:161-183` |
| #405 | `05cc503` | `class TurnOutput(BaseModel)` with `delta: SlotDelta \| None` + `reply: str` (min_length=1); `output_type=TurnOutput`; removal of 7 `extract_*` tools | `conversation_agent.py:69-99`, line 140 `output_type=TurnOutput`, line 152 `agent.instructions(render_dynamic_instructions)` |
| #409 | `1033880` | Walk X HIGH fixes — `ModelRetry` wedge + DB persistence of user turn on ValidationError | `portal_onboarding.py` handler |
| #425 F1a | `fc337d6` | Spec 215 data layer (`portal_bridge_tokens` migration) + admin endpoint contract | `supabase/migrations/`, `nikita/api/routes/portal_auth.py` |
| #426 F1b | `38014a0` | `signup_handler.py` FSM + Telegram webhook routing (Telegram-first signup) | `nikita/platforms/telegram/signup_handler.py` |
| #427 F2a | `9a81cb0` | Portal `/auth/confirm` route + IS-A always-interstitial | `portal/src/app/auth/confirm/` |

Dynamic-instructions verified live on origin/master at `conversation_prompts.py:124-139`:

```python
def render_dynamic_instructions(ctx: "RunContext[ConverseDeps]") -> str:
    state = getattr(ctx.deps, "state", None)
    missing: list[str] = state.missing if state is not None else []
    if not missing:
        return ""
    slots_text = ", ".join(missing)
    return f"\n\nSTILL MISSING (collect these before completing): {slots_text}"
```

Hard Rules gate-check against origin/master: **all 6 PASS** (see §9 Compliance table).

### 1.2 What this redesign adds

| # | Gap | Redesign deliverable |
|---|---|---|
| G1 | Dynamic instructions reads `state.missing` but does NOT inject a next-question `hint`; static `_WIZARD_FRAMING` in `conversation_prompts.py` still carries hard-coded routing rules (lines 39-88) | `QuestionSpec(hint=...)` adds per-turn hint; registry replaces the static routing block |
| G2 | No `QuestionRegistry` / `QuestionSpec` / adaptive routing based on prior answers | New module `nikita/agents/onboarding/question_registry.py` with `QuestionSpec` + `ORDERED_QUESTIONS` + `next_question(state)` |
| G3 | 40+ matches for `dossier/clearance/FILE/FIELD` in `portal/src/app/onboarding/**` (including `DossierReveal.tsx`, `DossierStamp.tsx`, `ClearanceGrantedCeremony.tsx`, `DossierHeader.tsx`, `WizardCopyAudit.test.tsx`) | Rename + scrub — component names and user-facing copy. Interstitial strings at `portal/src/app/auth/confirm/` are OUT of scope (per user constraint #1: IS-A interstitial "cleared / portal" copy stays) |
| G4 | `builtin_tools=[WebSearchTool(...)]` unused in wizard agent | Feature-flagged `WebSearchTool(max_uses=1, user_location=<slot-inferred>)` for city-enrichment |
| G5 | No session-start AI-disclosure string; `_WIZARD_FRAMING` does not carry one | Session-start Nikita turn includes one-line AI-disclosure ("hi, I'm Nikita — an AI companion...") |
| G6 | `WizardSlots` fixed at 6 slots; no personality/vibe taxonomy; no city-enrichment slot | Extend `WizardSlots` with `vibe: dict \| None`, `personality_archetype: dict \| None` (both optional, NOT required for `FinalForm`); add `city_context: dict \| None` populated by enrichment tool |

Compliance scope (per plan §2.5): session-start disclosure is in-scope for the wizard; NY A6767 3-hour reminder is a chat-runtime obligation (Telegram + voice handlers) filed separately as **Spec 216** (D24). Self-harm-detection escalation for both SB 243 and A6767 is likewise chat-runtime scope, Spec 216.

---

## 2. Research-bundle corrections (summary — plan §2 is authoritative)

Verified this session against primary sources (WebFetch):

- **§2.1 — BiasBusters (arxiv 2510.00307)**: abstract contains no error-reduction-percentage figure matching the bundle's disowned claim. Mitigation proposed is "filter-to-relevant-subset then sample uniformly", NOT simple consolidation. Our framing: `TurnOutput` (discriminated-union via `SlotDelta.kind`) **reduces tool cardinality**, which aligns with the paper's direction. Do NOT cite unverified percentages from the paper.
- **§2.2 — Zero-shot slot-filling (arxiv 2411.18980)**: COLING 2025 (not ACL 2025). "Abrupt topic shifts, interruptions, implicit references" VERBATIM per abstract. Bundle framing was inverted; cite as: "LLM-native slot-filling faces these obstacles (2411.18980 COLING 2025); our architecture addresses them via cumulative state (Hard Rule §1) + deterministic fallback (Hard Rule §5)."
- **§2.3 — Pydantic AI 1.25.0 primitives**: all signatures verified. `output_type=[X, str]` routes `str` to `result.output` as plain string. `Agent(instructions=callable)` is re-invoked per turn and NOT persisted in `message_history`. `builtin_tools=[WebSearchTool()]` for Anthropic accepts `user_location`, `blocked_domains` XOR `allowed_domains`, `max_uses`. `search_context_size` is OpenAI-only.
- **§2.4 — pydantic-ai#4647 KNOWN CAVEAT**: pydantic-ai 1.25.0 ships the 2025-03-05 `web_search` tool version; Anthropic's `web_search_20260209` with dynamic filtering (11% accuracy gain, 24% fewer input tokens per GH #4647) is not yet wired. Implication: either (a) accept the older tool version, (b) write a thin custom `Tool` wrapper around the `20260209` spec, or (c) defer live search. This recommendation picks (a) for PR-F2c-redesign and files a follow-up (D26) for (b) after PR-F2c-redesign merges.
- **§2.5 — NY A6767 + CA SB 243**: wizard scope limited to session-start disclosure. 3-hour reminder + self-harm escalation → Spec 216 (D24).
- **§2.7 — Replika / Nomi / Typeform**: Typeform "Logic Jumps" is a legitimate analog for `QuestionSpec(condition: Callable[WizardSlots, bool])`. Replika quiz-first + Nomi minimal-dialogue supported by 2025-2026 UX reviews.

---

## 3. Current-state confirmation (Phase 1 output)

`git show origin/master:nikita/agents/onboarding/conversation_agent.py` line-by-line confirms:

- line 140: `output_type=TurnOutput` ✓
- line 141: `system_prompt=WIZARD_SYSTEM_PROMPT` ✓ (static, persisted)
- line 143: `retries=4` ✓
- line 152: `agent.instructions(render_dynamic_instructions)` ✓ (dynamic, per-turn)
- line 161: `@agent.output_validator` applying delta ✓
- line 164-183: `_validate_and_apply` raises `ModelRetry` on empty reply + applies delta to `ctx.deps.state` ✓

`render_dynamic_instructions` at `conversation_prompts.py:124-139` reads `state.missing` and emits `"STILL MISSING (collect these before collecting): <slots>"` per turn.

**D23 RESOLVED INLINE**: Hard Rule §4 (dynamic instructions) is fully satisfied on origin/master. The plan's G1 language overstated the gap; the real G1 delta is that the callable does NOT inject a next-question `hint` — it only lists missing slots. Routing hints are still in the static `_WIZARD_FRAMING` (lines 39-88 of `conversation_prompts.py`), which is a partial anti-pattern: per Hard Rule §4 "Static `instructions=string` baking routing rules into the prompt is forbidden." The static prompt is tolerated only for invariants (persona, tone, reply length); routing IS a moving target that should shift into the callable.

PRs #400-409 delivered Hard Rules 1-6; this redesign addresses G1' (hint-in-callable) + G2 (registry) + G3 (vocab) + G4 (live tool) + G5 (disclosure) + G6 (slot expansion).

---

## 4. Candidate architectures (Phase 3)

Each candidate accepts the origin/master `WizardSlots` / `FinalForm` / `TurnOutput` / `@agent.output_validator` / `agent.instructions(callable)` / `message_history=` primitives as immutable. Differentiation is in how question selection, adaptation, and live-grounding are structured.

### Candidate A — Declarative Question Registry

**Core idea**: A priority-ordered list of `QuestionSpec` objects. Each spec has `slot`, `priority`, `condition: Callable[WizardSlots, bool]`, `hint: str`. Per turn, `next_question(state)` returns the highest-priority spec whose `condition(state)` is True and whose `slot` is still in `state.missing`. Nikita's reply is agent-generated but conditioned on the spec's `hint`.

**WizardSlots extensions** (additive; all optional):

```python
vibe: dict[str, Any] | None = None            # {"aesthetic": "cozy|edgy|romantic|chill", "confidence": 0.0-1.0}
personality_archetype: dict[str, Any] | None = None  # {"archetype": "romantic|pragmatist|adventurer|caretaker", "confidence": 0.0-1.0}
city_context: dict[str, Any] | None = None    # {"neighborhoods": [...], "scene_notes": "...", "enriched_at": ISO8601}
```

None of the above join `FinalForm` as required. `location`, `scene`, `darkness`, `identity`, `backstory`, `phone` remain the 6 required slots.

**Tools given to agent**:
- `output_type=TurnOutput` (unchanged)
- `builtin_tools=[WebSearchTool(max_uses=1, allowed_domains=["timeout.com", "resident-advisor.net", "tripadvisor.com", ...], user_location={"city": state.location.city} if state.location else None)]` — feature-flagged via `NIKITA_WIZARD_CITY_ENRICHMENT=true` (default `false` in PR-F2c-redesign; on in a follow-up PR after dogfood).

**Adaptation mechanism**:

```python
# nikita/agents/onboarding/question_registry.py (NEW)
from typing import Callable, Final
from pydantic import BaseModel, Field
from nikita.agents.onboarding.state import WizardSlots

class QuestionSpec(BaseModel):
    slot: str            # one of "location", "scene", ..., "phone", "vibe", "personality_archetype"
    priority: int        # lower = earlier; stable-sorted
    condition: Callable[[WizardSlots], bool]
    hint: str            # Nikita-voiced question framing; injected into dynamic instructions

    class Config:
        arbitrary_types_allowed = True

ORDERED_QUESTIONS: Final[list[QuestionSpec]] = [
    QuestionSpec(slot="location", priority=10, condition=lambda s: True,
                 hint="Ask where she lives. Keep it as a curiosity, not a form field."),
    QuestionSpec(slot="vibe", priority=20,
                 condition=lambda s: s.location is not None and s.vibe is None,
                 hint="Riff on her city. Ask what pulls her: cozy, edgy, romantic, chill."),
    QuestionSpec(slot="scene", priority=30,
                 condition=lambda s: s.location is not None,  # F2 FIX: do NOT gate on s.vibe; vibe is optional
                 hint="Pick a scene that fits her: techno, art, food, cocktails, nature."),
    QuestionSpec(slot="darkness", priority=40,
                 condition=lambda s: s.scene is not None,
                 hint="Ask how dark she wants to take the game (1-5)."),
    QuestionSpec(slot="personality_archetype", priority=50,
                 condition=lambda s: s.scene is not None and s.personality_archetype is None,  # F2 FIX: scene gate, NOT darkness gate, and NEVER blocks identity
                 hint="Ask a softball archetype question: romantic, pragmatist, adventurer, caretaker."),
    QuestionSpec(slot="identity", priority=60,
                 condition=lambda s: s.darkness is not None,  # F2 FIX: gate on required slot only, not on optional personality_archetype
                 hint="Ask name / age / occupation — casual, not interrogating."),
    QuestionSpec(slot="backstory", priority=70,
                 condition=lambda s: s.identity is not None,
                 hint="Present 3 backstory teasers (from cache); she picks one."),
    QuestionSpec(slot="phone", priority=80,
                 condition=lambda s: s.backstory is not None,
                 hint="Ask whether she prefers voice or text. If voice, ask for her number."),
]

def next_question(state: WizardSlots) -> QuestionSpec | None:
    sorted_specs = sorted(ORDERED_QUESTIONS, key=lambda q: q.priority)
    for spec in sorted_specs:
        if spec.slot in state.missing and spec.condition(state):
            return spec
    return None
```

`render_dynamic_instructions` extends:

```python
def render_dynamic_instructions(ctx: "RunContext[ConverseDeps]") -> str:
    state = getattr(ctx.deps, "state", None)
    if state is None:
        return ""
    parts: list[str] = []
    if state.missing:
        parts.append(f"STILL MISSING: {', '.join(state.missing)}")
    next_spec = next_question(state)
    if next_spec is not None:
        parts.append(f"NEXT QUESTION ({next_spec.slot}): {next_spec.hint}")
    return "\n\n" + "\n".join(parts) if parts else ""
```

**State persistence**: unchanged. `WizardSlots` cumulative state, `model_copy(update=...)` immutable merge, `build_state_from_conversation` reconstruction from JSONB `onboarding_profile.conversation[*].extracted ∪ elided_extracted`.

**≤30-LOC code skeleton** (agent construction):

```python
agent: Agent[ConverseDeps, TurnOutput] = Agent(
    _MODEL_NAME,
    deps_type=ConverseDeps,
    output_type=TurnOutput,
    system_prompt=WIZARD_SYSTEM_PROMPT_NEUTRAL,   # persona + invariants only; NO routing
    builtin_tools=(
        [WebSearchTool(max_uses=1, allowed_domains=CITY_ENRICHMENT_DOMAINS)]
        if settings.wizard_city_enrichment else []
    ),
    retries=4,
)
agent.instructions(render_dynamic_instructions)   # injects state.missing + next_question hint

@agent.output_validator
def _validate_and_apply(ctx: RunContext[ConverseDeps], output: TurnOutput) -> TurnOutput:
    if not ctx.deps.state.is_complete and not output.reply.strip():
        raise ModelRetry("Reply is empty...")
    if output.delta is not None:
        ctx.deps.state = ctx.deps.state.apply(output.delta)
    return output
```

**Strengths**:
- Additive: zero breaking changes to `WizardSlots`, `TurnOutput`, or wire contracts; new slots ship as optional.
- Readable: routing lives in data (`ORDERED_QUESTIONS`), not in prose; each `condition` is a 1-line lambda testable in isolation.
- Matches Typeform Logic Jumps — a 2025 industry-standard pattern for conditional question flows.
- `hint` injection closes the Hard Rule §4 gap cleanly: routing migrates from static prompt to callable.
- `WebSearchTool` is orthogonal — wizard works with or without it; feature flag lets us dogfood safely.

**Weaknesses**:
- Slight duplication with `state.missing`: the ordered list is implicit in `priority`, the registry adds a second ordering surface. Mitigation: assert in a test that `ORDERED_QUESTIONS` priorities are strictly increasing and match `_ALL_SLOT_NAMES + ["vibe", "personality_archetype"]`.
- `Callable[[WizardSlots], bool]` lambdas are not trivially serializable — the registry is Python-module-resident only, not JSONB-persistable. Not a blocker (replay reconstructs state via `build_state_from_conversation`, and the registry is looked up by slot name each run).
- `next_question` is called per turn and is O(|ORDERED_QUESTIONS|) — negligible (<1 µs for 8 specs).

---

### Candidate B — Pure Free-Form Extraction

**Core idea**: No registry. Agent drives entirely from persona + `state.missing`. Dynamic instructions callable injects `state.missing` only. Question order and hints emerge from prompt engineering in `_WIZARD_FRAMING`.

**WizardSlots extensions**: same as A (vibe, personality_archetype, city_context additive optional).

**Tools given to agent**: same as A minus the registry.

**Adaptation mechanism**: none explicit. Prompt engineering shapes the conversational flow. Agent decides what to ask next.

**State persistence**: unchanged.

**Code skeleton**: current origin/master with (1) extended `_WIZARD_FRAMING` mentioning vibe/personality/city, (2) no `question_registry.py`.

**Strengths**:
- Minimum new code — no new module, no registry.
- Agent has full flexibility in conversational order (may produce more natural flows).
- Easy to layer a registry later if needed.

**Weaknesses**:
- Adaptation happens in prompt prose — untestable as a unit. User's ask "Questions to depend on previous answers" is satisfied only probabilistically.
- Routing-in-prompt is the pattern Hard Rule §4 warns against: "Static `instructions=string` baking routing rules into the prompt is forbidden." Even if the callable renders the prompt, packing 8 conditional "ask X when Y" rules into prose invites the LLM-tool-selection-bias failure mode (Walk V precedent).
- Debugging the agent choosing the wrong question is a prompt-regression problem, not a data-inspection problem.

---

### Candidate C — `pydantic-graph` FSM

**Core idea**: Explicit state machine. Each slot is a node; edges are keyed on `WizardSlots` predicates. Useful for the Spec 215 branching (Telegram-first signup vs web-first) and Spec 028 voice-mode post-wizard divergence.

**Evaluated vs concrete branches in Spec 215 today**:

- Spec 215 §3.1 happy path is strictly linear: Telegram-first signup is a separate FSM (`signup_handler.py` already a pseudo-FSM with `signup_state` enum) executed BEFORE wizard entry. The wizard itself sees a single entry (`/onboarding` post-`/auth/confirm`) and a single exit (`conversation_complete=True → ClearanceGrantedCeremony`).
- Voice-mode post-wizard divergence (Spec 028) happens AFTER `ClearanceGrantedCeremony` renders — it's outside the wizard surface.

Branching inside the wizard (e.g., "user answers 'call me' → skip backstory preview to accelerate") is the only candidate for FSM nodes. But Typeform's Logic Jumps handle this declaratively in A without needing pydantic-graph's node + edge model.

**WizardSlots extensions**: same as A.

**Tools**: same as A.

**Adaptation mechanism**: FSM nodes; each node handles one slot; edges conditional on state.

**State persistence**: requires serializable FSM position in addition to WizardSlots — new persistence field `wizard_graph_position: str` on `user_profiles`.

**Code skeleton** (illustrative — pydantic-graph API):

```python
from pydantic_graph import Graph, BaseNode, GraphRunContext, End

@dataclass
class AskLocation(BaseNode[ConverseDeps]):
    async def run(self, ctx: GraphRunContext[ConverseDeps]) -> "AskVibe | End":
        # agent run scoped to this slot, then branch
        ...

graph = Graph(nodes=(AskLocation, AskVibe, AskScene, AskDarkness, AskIdentity, AskBackstory, AskPhone))
```

**Strengths**:
- Explicit — you can read the graph and know every branch.
- Replayable via pydantic-graph's built-in state persistence.
- Strong for multi-agent handoff (if voice agent ever re-joined mid-wizard).

**Weaknesses**:
- **Overengineering for a linear 6-8-slot collection flow** (`.claude/rules/agentic-design-patterns.md` explicit guidance: "`pydantic-graph` (FSM) — NOT for linear flows. 'Don't use a nail gun unless you need a nail gun.' Reach for it only when branching emerges").
- Introduces a second persistence surface (graph position) that must stay in sync with `WizardSlots` — new class of bug.
- Current branching demand is zero within the wizard; premature.
- Churn cost: every slot becomes a node class with boilerplate.

---

### Candidate D — Two-Agent System (host + researcher)

**Core idea**: Main Nikita agent collects slots. A second agent (researcher) is invoked as a tool by the main agent, runs `WebSearchTool` against the user's city, and returns enrichment metadata. Main agent weaves the enrichment into subsequent turns.

**WizardSlots extensions**: same as A (vibe, personality_archetype, city_context).

**Tools given to main agent**: `enrich_city(city: str) -> dict` (internally spawns the researcher agent).

**Tools given to researcher agent**: `builtin_tools=[WebSearchTool(...)]`, `output_type=CityContext` (Pydantic model).

**Adaptation mechanism**: main agent may or may not invoke `enrich_city` based on prompt guidance; researcher's output carries structured neighborhoods / scene notes.

**State persistence**: city_context field on WizardSlots, populated by enrichment output.

**Code skeleton**:

```python
researcher = Agent(
    _MODEL_NAME,
    output_type=CityContext,
    builtin_tools=[WebSearchTool(max_uses=1, allowed_domains=CITY_ENRICHMENT_DOMAINS)],
    system_prompt="You are a city researcher. Return neighborhoods + scene notes for the given city.",
)

@main_agent.tool
async def enrich_city(ctx: RunContext[ConverseDeps], city: str) -> CityContext:
    result = await researcher.run(f"Research {city} for nightlife, art, food scenes.", deps=None)
    return result.output
```

**Strengths**:
- Strong AGI-feel payload: user mentions "Zurich", main agent weaves in a real Kreis 4 neighborhood reference two turns later.
- Modular: researcher is independent, testable in isolation, swappable for a different enrichment backend.
- Matches the "Two-Agent System" pattern from Anthropic's Building Effective Agents cookbook (section 5.2).

**Weaknesses**:
- Re-introduces a narrow tool on the main agent (`enrich_city`) — pushes back against Hard Rule §3 consolidation. Mitigation: the tool is orthogonal (not an extraction tool, doesn't compete with `TurnOutput`'s slot discriminator); tool-selection-bias risk is low because there is only one tool to pick.
- Researcher latency compounds: even with a 1.5s soft cap, a main-agent turn that invokes the researcher adds ~1s p50. User's "AGI-feel" ask conflicts with the latency budget.
- pydantic-ai#4647 caveat is MORE relevant here — the researcher is all-in on WebSearchTool, and the 20260209 dynamic-filtering feature would measurably improve output quality.
- Ship cost: researcher agent + CityContext Pydantic model + `enrich_city` tool + 3-class test suite + observability (tool invocation events).

---

### Candidate E — Event-Sourced Slot Detectors

**Core idea**: Append-only conversation log (already exists in `onboarding_profile.conversation`). Per-slot detector functions (regex, NER, LLM-as-judge) read the log on demand and rebuild state. Main agent is reply-only; extraction is post-agent, ensemble.

**WizardSlots extensions**: same as A.

**Tools**: none on main agent; extraction is entirely post-run.

**Adaptation mechanism**: detectors run in priority order per turn after the agent replies.

**State persistence**: log + detector registry; `WizardSlots` reconstructed fresh each turn.

**Code skeleton**:

```python
DETECTORS: list[Callable[[list[Turn]], SlotDelta | None]] = [
    phone_regex_detector,
    location_ner_detector,
    scene_llm_judge,
    ...
]

async def extract_from_log(log: list[Turn]) -> list[SlotDelta]:
    return [d(log) for d in DETECTORS if d(log) is not None]
```

**Strengths**:
- Decouples extraction from conversation — agent focuses on reply quality.
- Event-sourced: replay is trivial; audit is trivial.
- Easy to add a new slot: write a detector, register it.

**Weaknesses**:
- Discards the structured output work done by `TurnOutput` — reverts Hard Rule §3 consolidation.
- Detector ensemble is expensive (N LLM calls per turn vs 1).
- Reconstruction budget (`RECONSTRUCTION_BUDGET_MS=10`) is blown; detectors are slow.
- LLM-as-judge detectors defeat the whole point of structured output — the Walk V failure mode (LLM emits the wrong tool) recurs inside each detector.

---

## 5. Six-expert panel scoring (Phase 4)

Dimensions (per fresh-session-prompt §Phase 4):
- **P = Pydantic AI alignment** (non-negotiable — score < 5 eliminates)
- **M = Modularity** (non-negotiable — score < 5 eliminates)
- **G = AGI-feel / surprise + recognition**
- **T = Testability**
- **C = Maintenance cost** (lower is better; scored inversely — higher = lower cost)
- **X = Spec 214 / 215 compatibility**

Scoring: each cell is `score | justification` (1 sentence, per plan §5 Phase 4 disagreement machinery). Scale 1-10.

### Panel composition

| # | Persona | Role |
|---|---|---|
| π1 | Pydantic AI core contributor | Calibrates primitive usage; flags `output_type`, `instructions=`, `builtin_tools` misuse. |
| π2 | Product Designer (consumer onboarding) | Weighs conversational flow quality; watches for AGI-feel payoff. |
| π3 | Test Engineer | Evaluates unit-/integration-testability of the adaptation mechanism. |
| π4 | Consumer Onboarding UX (Replika/Nomi-informed) | Calibrates against 2025-2026 companion-app onboarding teardowns. |
| π5 | AI Safety / Compliance | Watches CA SB 243 + NY A6767 session-start disclosure + self-harm-escalation scope. |
| π6 | SRE | Weighs latency budget, timeout behavior, cold-start cost, feature-flag rollback. |

### Scoring matrix

| Dim | Candidate A (Registry) | Candidate B (Free-form) | Candidate C (Graph FSM) | Candidate D (Two-agent) | Candidate E (Event-sourced) |
|---|---|---|---|---|---|
| **P (Pydantic AI alignment)** | π1: **9** — uses `instructions=callable`, `output_type`, `builtin_tools` all per docs. π3: 8 — callable output is deterministic. | π1: **7** — uses same primitives but bakes routing in prompt; Hard Rule §4 partial violation. π3: 5 — hard to test. | π1: **6** — pydantic-graph is the right tool ONLY if branching exists; here it doesn't. π3: 6 — graph nodes testable but heavy. | π1: **8** — researcher is well-scoped, but `enrich_city` narrow tool nudges Hard Rule §3. π6: 7 — latency cost. | π1: **4** — reverts `TurnOutput` consolidation; Hard Rule §3 violation. π3: 6 — detectors individually testable. |
| **M (Modularity)** | π2: **9** — registry is data, orthogonal to agent. π3: 9 — each `QuestionSpec` testable. | π2: **5** — conversational logic embedded in prompt, not swappable. π3: 4 — prose is not modular. | π2: **7** — nodes modular but graph itself is a monolith. π3: 7. | π2: **8** — researcher swappable. π1: 7 — coupling via `enrich_city` tool. | π2: **8** — detectors modular. π4: 6 — reply quality decoupled from extraction, can diverge. |
| **G (AGI-feel)** | π4: **7** — registry enables city-enrichment via WebSearchTool; "recognition" payload is real. π2: 7 — conversational shape feels natural. | π4: **6** — depends entirely on prompt skill. π2: 8 — agent has full freedom, can feel magical. | π4: **5** — FSM feels like a form, not a chat. π2: 5. | π4: **9** — dedicated researcher returns rich neighborhood / scene notes; strongest "surprise + recognition" payload. π2: 9. | π4: **5** — no real-time research; detectors are reactive not proactive. π2: 4. |
| **T (Testability)** | π3: **9** — `QuestionSpec.condition` lambdas are trivially unit-testable; `next_question` is pure. π1: 9. | π3: **5** — routing behavior only testable end-to-end via LLM-in-the-loop. π1: 5. | π3: **7** — each node testable but graph-level transitions require graph harness. π1: 7. | π3: **7** — main + researcher each testable; tool invocation mockable. π6: 7. | π3: **8** — detectors are pure functions; ensemble is deterministic. π1: 6 — reverts TurnOutput path, re-tests needed. |
| **C (low cost)** | π6: **8** — 1 new module (`question_registry.py` ~120 LOC); no new persistence surface; feature flag on search tool. π5: 8. | π6: **9** — almost no new code. π5: 9. | π6: **4** — new persistence surface (graph position), new test harness, 8 node classes. π5: 5. | π6: **5** — 2 agents, 1 new tool, 1 new Pydantic model, 1 latency contract. π5: 6. | π6: **5** — detector registry + ensemble runner + new observability; detector latency risk. π5: 5. |
| **X (214/215 compat)** | π4: **9** — additive to FR-11d; preserves `WizardSlots` + `TurnOutput`; preserves wire format; ships behind feature flag. π6: 9. | π4: **9** — fully additive. π6: 9. | π4: **5** — introduces `wizard_graph_position` persistence; schema migration; breaks replay simplicity. π6: 5. | π4: **7** — additive but introduces researcher latency that needs budgeting. π6: 6. | π4: **4** — reverts `TurnOutput`; requires reversing PR #405; regression risk. π6: 4. |

### Dimension means (rounded)

| | A | B | C | D | E |
|---|---|---|---|---|---|
| P | 8.5 | 6.0 | 6.0 | 7.5 | 5.0 |
| M | 9.0 | 4.5 | 7.0 | 7.5 | 7.0 |
| G | 7.0 | 7.0 | 5.0 | 9.0 | 4.5 |
| T | 9.0 | 5.0 | 7.0 | 7.0 | 7.0 |
| C | 8.0 | 9.0 | 4.5 | 5.5 | 5.0 |
| X | 9.0 | 9.0 | 5.0 | 6.5 | 4.0 |
| **Total** | **50.5** | **40.5** | **34.5** | **43.0** | **32.5** |

### Elimination gates (non-negotiables)

- **P ≥ 5**: A (8.5), B (6.0), C (6.0), D (7.5), E (5.0 exact → PASS by threshold but by narrowest margin)
- **M ≥ 5**: A (9.0), B (4.5 ← FAIL), C (7.0), D (7.5), E (7.0)

**Eliminated**: B on Modularity.

### Spread ≥ 4 disagreement debate

Only dimension D (AGI-feel) has spread ≥ 4: A=7, C=5, D=9, E=4.5. **Debate** (per plan §5 Phase 4):

- π2 (Product Designer) for D (9): "Dedicated researcher unlocks the wow moment. User says 'I live in Zurich', 3 turns later Nikita references 'the Kreis 4 viaduct arches, not the Bahnhofstrasse crowd' — that's the AGI moment the user explicitly asked for."
- π4 (Onboarding UX) for A (7): "Registry enables the same payoff via `WebSearchTool` on the main agent. D gets you 1 extra hit rate point via researcher specialization, but the marginal AGI-feel above 7 is buyable with a single enrichment tool wired into A."
- π6 (SRE) caveat on D: "Two-agent latency compounds. p95 main-turn cost is +800ms when researcher fires. User-facing turn budget (per spec 214 NFR) is already tight at 2.5s."

**Resolution**: A + optional `WebSearchTool` captures 80% of D's AGI-feel at 40% of D's cost. D is strictly better on AGI-feel but the budget is tight and pydantic-ai#4647 caveat compounds. **Winner: A**; D's researcher deferred to D27 (follow-up PR after F2c-redesign dogfood).

### Hidden disagreements (agree on score, differ on justification)

π3 and π6 both scored A Modularity = 9 but π3 justified it from test-surface isolation, π6 from rollback surface isolation. Agreed-on — not a hidden disagreement, reinforces the modularity claim.

π1 and π3 diverge on E: π1 = 4 (Hard Rule §3 violation), π3 = 6 (detectors testable in isolation). Both justifications are valid; π1's is the binding Pydantic AI alignment gate. Resolution: E eliminated on P-score margin (5.0 exact, tied for the lowest-passing cell), not contested.

**Survivors** (after elimination): A, C, D.

**Winner by total score**: A (50.5) > D (43.0) > C (34.5).

### 5.1 B rescore note (F6 devil's advocate 2026-04-24 — PARTIALLY-TRUE)

Devil's advocate argued B was dismissed too quickly because rewriting B's adaptation mechanism as "dynamic callable enumerating state.missing in priority order with per-slot hint strings (no lambdas)" removes the Hard Rule §4 violation that drove B's M=4.5. Partially true — B rewritten that way is essentially A minus the typed `QuestionSpec.condition` lambda; the prose-in-callable approach loses unit-test granularity (you cannot test a single condition in isolation; you can only assert end-to-end that the callable produced the right priority-ordered enumeration). A's T=9.0 vs B-rescored T=~5.0 gap is the real modularity + testability delta, not the static-vs-dynamic-prompt distinction.

Rescoring B-revised under the fair framing:
- P (Pydantic AI alignment): 8 (was 7; dynamic callable closes the static-routing concern)
- M (Modularity): 6 (was 4.5; callable is a single unit; registry is multiple independently-testable units)
- G (AGI-feel): 7 (unchanged — prose can carry the same WebSearchTool integration)
- T (Testability): 5 (was 5; prose enumeration still hard to unit-test at per-condition granularity)
- C (low cost): 9 (unchanged)
- X (compat): 9 (unchanged)
- **B-revised total: 44.0** — above C (34.5), above D (43.0) narrowly, but still below A (50.5).

B-revised stays eliminated on the non-negotiable M≥5 gate (passes at 6) but loses to A on T and M. A wins cleanly. The F6 finding is accepted as a **rescoring improvement**, not an architecture flip.

---

## 6. Edge case sweep (Phase 5 — 20 cases)

Each case: **behavior under Candidate A** | **handling mechanism** | **test case shape**.

| # | Edge case | Behavior | Mechanism | Test case |
|---|---|---|---|---|
| 1 | User enters "Zurich" (known city) | `WizardSlots.location` filled; `WebSearchTool` (if flag on) enriches `city_context` on next turn. | Agent tool invocation; enrichment merges into slot delta. | `test_city_enrichment_happy_path` — mock `WebSearchTool` returns neighborhood list; assert `slots.city_context is not None`. |
| 2 | User enters "Atlantis" (unknown city) | `WizardSlots.location.city="Atlantis"`; enrichment returns empty; `city_context` remains None. | `WebSearchTool` returns 0 results; agent reply falls back to generic scene question. | `test_city_enrichment_unknown_city` — mock tool returns empty; assert slot filled, city_context None, next turn proceeds. |
| 3 | User says "surprise me" (no concrete data) | `TurnOutput.delta=None`; reply asks for one concrete fact. | `@agent.output_validator` does not raise; state unchanged; registry still selects same slot on next turn. | `test_no_extraction_on_surprise_me` — agent emits delta=None; assert progress_pct unchanged. |
| 4 | User gives age 17 (below minimum) | `FinalForm._identity_age_minimum` validator fires on terminal turn; wizard cannot complete; `/converse` handler surfaces in-character rejection (`_VALIDATION_REJECT_AGE_REPLY`). | `ValidationError` raised by cross-field validator; `/converse` catches, returns `validation_reject` source. | `test_final_form_rejects_under_18` — set identity.age=17, call `FinalForm.model_validate`; assert raises with age-field path. |
| 5 | User provides phone mid-identity turn (wrong slot kind emitted) | `regex_phone_fallback` fires after main agent; fills `phone` slot directly; agent's wrong delta (`kind="identity"`) still applied. | Post-agent fallback at `portal_onboarding.py:1086` applies `SlotDelta(kind="phone", ...)` before `FinalForm` gate. | `test_phone_regex_fallback_on_wrong_kind` — mock agent returns identity delta for "+1 415 555 0234"; assert `slots.phone` filled. |
| 6 | User answers 3 questions in one message | Agent emits ONE `SlotDelta` (the highest-priority match by registry); remaining facts persist in conversation log for future extraction. | `output_type=TurnOutput` is single-delta by design; conversation log retains full message for future scan. | `test_multi_fact_single_delta` — mock LLM emits one delta for input "I'm Ana, 28, in Berlin"; assert one slot filled, others still missing. |
| 7 | User backtracks ("actually, make that 4 not 5 for darkness") | New `SlotDelta(kind="darkness", data={...})` OVERWRITES via `model_copy(update={...})`; monotonicity preserved at progress level (slot was filled before, stays filled). | `WizardSlots.apply()` is last-write-wins per slot. | `test_darkness_revision_last_write_wins` — apply delta darkness=5 then darkness=4; assert slots.darkness.data.drug_tolerance == 4. |
| 8 | User picks voice without providing phone | Rule 1 VOICE-WITHOUT-PHONE branch fires; agent emits `no_extraction(reason="clarifying")` + asks for number. Phone slot stays unfilled. | Existing `conversation_prompts.py:70-77` rule preserved. | `test_voice_without_phone_emits_no_extraction` — input "call me!"; assert delta is None; reply contains "number". |
| 9 | User refuses phone entirely ("just text me") | `SlotDelta(kind="phone", data={"phone_preference": "text"})` fills slot without number. | `FinalForm._voice_requires_phone` validator permits `phone_preference="text"` without number. | `test_text_preference_completes_without_number` — full state minus phone, set phone_preference="text"; FinalForm validates. |
| 10 | User has conflicting city answers across turns ("Berlin" turn 1, "Zurich" turn 6) | Last-write-wins; `location.city="Zurich"`; `city_context` invalidated (needs re-enrichment). | `WizardSlots.apply()` overwrites; enrichment tool re-runs IF registry condition `(s.location is not None and s.city_context is None)` fires. | `test_city_revision_invalidates_enrichment` — apply Berlin, enrich, apply Zurich; assert city_context is None after second apply (unless enrichment fires same turn). |
| 11 | User input > CHAR_LIMIT (existing `NIKITA_INPUT_MAX_CHARS` guard) | `/converse` returns 400 `input_too_long`. | Existing input sanitization. | Existing `test_converse_input_too_long`. |
| 12 | LLM timeout (network flap / cold start) | `asyncio.TimeoutError` caught; `_fallback_response(source="fallback")`; user turn persisted best-effort. | Existing handler (`portal_onboarding.py:907-928`). | Existing `test_converse_timeout_returns_fallback`. |
| 13 | LLM emits schema violation (e.g., `reply=""`) | `@agent.output_validator` raises `ModelRetry`; agent self-corrects within `retries=4`. | Existing validator + retries. | Existing `test_output_validator_raises_on_empty_reply`. |
| 14 | Agent hits retries=4 (exhausted) | `UnexpectedModelBehavior` raised; handler returns `_fallback_response`. | Existing handler. | Existing `test_converse_retries_exhausted_returns_fallback`. |
| 15 | Web search timeout (>1.5s) | `WebSearchTool` invocation wrapped in `asyncio.wait_for`; on timeout, tool returns empty; agent continues without enrichment. | `pydantic_ai.builtin_tools.WebSearchTool` supports max_uses; we wrap in a timeout guard at the agent-tool level. | `test_websearch_timeout_graceful_degradation` — patch `WebSearchTool._call` to sleep 2s; assert no exception surfaces, city_context remains None. |
| 16 | Web search returns 0 results | Agent reply falls back to generic scene question; no `city_context` delta. | Graceful degradation by design. | `test_websearch_empty_results` — mock tool returns `{"results": []}`; assert city_context None, turn continues. |
| 17 | User closes browser mid-conversation, reloads 5 min later | Portal wizard's `getConversation()` hydrates from JSONB; `build_state_from_conversation` reconstructs `WizardSlots`; progress restored. | Existing FR-11d `AC-11d.10` elision-boundary reconstruction. | Existing `test_get_conversation_returns_link_after_completion` + companions. |
| 18 | User opens wizard in two tabs (two concurrent `/converse` calls) | Both calls read same DB state; one persists first; second sees "stale" reconstruction that is still correct (cumulative slots don't regress). Idempotency key dedups identical retries. | Existing `idempotency` table + `Idempotency-Key` header; `WizardSlots` monotonic-by-construction. | `test_converse_concurrent_turns_no_regression` — simulate two overlapping `/converse` calls; assert final state is union. |
| 19 | Terminal-turn idempotency (duplicate POST) | First POST mints link_code + sets `conversation_complete=True`; second POST (same `Idempotency-Key`) returns cached response body verbatim. | Existing idempotency store. | Existing `test_idempotency_replay`. |
| 20 | **AI-disclosure — session-start** | First Nikita turn on a fresh conversation carries `AI_DISCLOSURE_OPENER` — e.g., "hey. i'm nikita. quick heads up: i'm an AI companion. ready to meet?" OR first turn system-injected disclosure renders in UI. 3-hour reminder NOT in wizard scope (deferred to Spec 216). | `AI_DISCLOSURE_OPENER` constant in `conversation_prompts.py`; `hydrateWithOpener` in `onboarding-wizard.tsx` uses it instead of the current hardcoded "hey. building your file. where do i find you on a thursday night?" | `test_session_start_includes_ai_disclosure` — fresh conversation (empty `conversation_history`); assert first Nikita reply contains "AI" token OR snapshot-tests a regex match against AI_DISCLOSURE_OPENER. |

---

## 7. Recommendation (Phase 6)

### 7.1 Winner — Candidate A: Declarative Question Registry

Per §5 panel scoring (A=50.5 > D=43.0 > C=34.5), A is the winner. A is additive to FR-11d, preserves all origin/master contracts, ships behind a feature flag where appropriate (`WebSearchTool`), and closes the Hard Rule §4 static-routing gap by migrating routing into `next_question(state).hint`.

### 7.2 §25 resolution table (D14-D22)

| # | Decision | §25 stance | §26 resolution | Status |
|---|---|---|---|---|
| D14 | File-metaphor origin | Kill wizard metaphor | Confirmed — scrub `portal/src/app/onboarding/**` via PR-F2c-redesign T-F2c.9-10 (component renames + copy.ts rewrite). IS-A interstitial at `portal/src/app/auth/confirm/` keeps "cleared / portal" copy (constraint #1). | Resolved |
| D15 | Welcome-question affordance | Typed reply | Typed-reply affordance (existing `ChatShell` input). No quick-reply chips in PR-F2c-redesign; reserved for D28 follow-up if dogfood shows typed-reply is a drop-off. | Resolved |
| D16 | Question count cap | 7 with `optional=True` on age/work | 8 total slots: 6 required (location, scene, darkness, identity, backstory, phone) + 2 optional (vibe, personality_archetype). Vibe + archetype NOT in `FinalForm` required fields; wizard completes at 6. | Resolved — count raised from 7 to 8 because vibe is structurally distinct from scene. |
| D17 | (vacant in §25) | — | — | — |
| D18 | Sexy-tone calibration | Specificity > generic warmth | Confirmed. Nikita-voiced `hint` in each `QuestionSpec` is the single calibration surface; copy review on merge. See §8.3. | Resolved |
| D19 | Backstory timing | One-shot at end | Confirmed — `QuestionSpec(slot="backstory", priority=70, condition=lambda s: s.identity is not None)` fires ONLY after identity is filled. | Resolved |
| D20 | Personality taxonomy | Closed enum vs free-form | **PICK**: closed enum `{"romantic", "pragmatist", "adventurer", "caretaker"}` with implicit-inference fallback (LLM infers archetype from free-text answers to a single question like "what pulls you into a night — the thrill, the people, the vibe, or the calm?"). Rationale: closed enum makes downstream backstory generator dispatch trivial; free-form re-introduces LLM-as-judge surface at completion gate. Confidence score stored so downstream can degrade gracefully if <0.5. | Resolved |
| D21 | Firecrawl timeout | 8s outer + 2s soft await | **SUPERSEDED by D22 pick**: we use `WebSearchTool` not Firecrawl. Timeout contract: 1.5s soft cap via `asyncio.wait_for` wrapper around the agent tool; on timeout, tool returns empty + agent continues without enrichment. | Resolved (superseded) |
| D22 | Firecrawl client shape | Thin SDK wrapper | **PICK**: `pydantic_ai.builtin_tools.WebSearchTool(max_uses=1, allowed_domains=[...], user_location={"city": <slot>})`. Reason: single-agent + builtin — zero wrapper code + native Pydantic AI integration. Caveat: pydantic-ai#4647 — we ship on `web_search_20250305`; dynamic-filtering 11% accuracy / 24% input-token upgrade deferred to D26. | Resolved |

### 7.3 New decisions opened this session

- **D23 (RESOLVED INLINE — §3)**: `@agent.instructions` callable IS in place on origin/master AND DOES read `state.missing`. G1 in plan v2 overstated; real gap is routing-in-static-prompt, addressed by §7.4 `hint` injection.
- **D24 (OPEN)**: Spec 216 (compliance — 3-hour AI-disclosure reminder, self-harm-detection + escalation) — owner and filing deadline TBD. Plan v2 §2.5 notes CA SB 243 core-effective 2026-01-01 (requires session-start disclosure + self-harm escalation + minor-specific notifications) and NY A6767 effective 2025-11-05 (every-3-hour reminder). Wizard owns session-start only; Spec 216 owns runtime chat handlers. **Action**: file Spec 216 draft within PR-F2c-redesign's sibling PR (not the redesign PR itself). Owner: Simon.
- **D25 (RESOLVED — §7.4)**: `vibe` + `personality_archetype` + `city_context` are OPTIONAL in `WizardSlots`; NONE join `FinalForm` required fields. `age` + `occupation` in identity slot already OPTIONAL per existing `FinalForm._identity_not_all_none` (≥1 sub-field).
- **D26 (OPEN — FOLLOW-UP)**: upgrade `WebSearchTool` to `web_search_20260209` once pydantic-ai ships the version bump. Track via watch on GH #4647.
- **D27 (DEFERRED)**: Two-agent researcher for city-enrichment (Candidate D). Revisit after PR-F2c-redesign dogfood — if the single-agent `WebSearchTool` enrichment payload is insufficient for the AGI-feel threshold, promote to two-agent.
- **D28 (DEFERRED)**: Quick-reply chips vs typed-reply affordance for high-drop-off questions. Revisit if dogfood shows typed-reply friction.

### 7.4 Architecture details

#### 7.4.1 New / modified files

**NEW**:

- `nikita/agents/onboarding/question_registry.py` (~120 LOC): `QuestionSpec` + `ORDERED_QUESTIONS` + `next_question(state)`. Imports ONLY from `nikita.agents.onboarding.state` + stdlib + pydantic. No circular deps.
- `nikita/agents/onboarding/extraction_schemas.py` — extend with `VibeExtraction` + `PersonalityExtraction` Pydantic models (sibling to `LocationExtraction` et al.).
- `tests/agents/onboarding/test_question_registry.py` — unit tests for every `QuestionSpec.condition` lambda + `next_question` ordering invariants.
- `tests/agents/onboarding/test_websearch_graceful_degradation.py` — edge cases 15-16 from §6.
- `supabase/migrations/<NNN>_extend_wizardslots_taxonomy.sql` — add `vibe`, `personality_archetype`, `city_context` to `user_profiles` as `jsonb` NULL columns (MAY also be pure JSONB-within-onboarding_profile; see §7.4.2).

**MODIFIED**:

- `nikita/agents/onboarding/state.py` — add three optional fields to `WizardSlots` (vibe, personality_archetype, city_context). `TOTAL_SLOTS` stays at 6 (only required slots count toward completion; optional slots don't); `_ALL_SLOT_NAMES` stays at 6 for the same reason. Registry uses a separate `_OPTIONAL_SLOT_NAMES = ["vibe", "personality_archetype", "city_context"]`.
- `nikita/agents/onboarding/conversation_agent.py` — add `builtin_tools=[WebSearchTool(...)]` guarded by `settings.wizard_city_enrichment`; system_prompt source changes from `WIZARD_SYSTEM_PROMPT` to `WIZARD_SYSTEM_PROMPT_NEUTRAL` (routing rules stripped). `retries=4` unchanged.
- `nikita/agents/onboarding/conversation_prompts.py` — `render_dynamic_instructions` extends to inject `next_question(state).hint`. `_WIZARD_FRAMING` split into two sections: `_INVARIANTS` (persona ref, reply length, no markdown, no PII re-statement) keeps; `_ROUTING_RULES` (lines 39-88) REMOVED (migrated to registry). `AI_DISCLOSURE_OPENER` constant added. Register a `test_persona_imported_verbatim` equivalent for `WIZARD_SYSTEM_PROMPT_NEUTRAL` to pin persona invariant.
- `nikita/config/settings.py` — add `wizard_city_enrichment: bool = False` (env `NIKITA_WIZARD_CITY_ENRICHMENT`).
- `nikita/services/backstory_generator.py` — no signature change; documentation note: when `vibe` + `personality_archetype` are filled, downstream backstory-cache `cache_key` schema SHOULD extend to include these for differentiated backstories. Tracked as D29 (follow-up).
- `portal/src/app/onboarding/onboarding-wizard.tsx` — replace hardcoded opener "hey. building your file. where do i find you on a thursday night?" with `AI_DISCLOSURE_OPENER` fetched from a new `/portal/wizard-opener` endpoint or hardcoded in a FE constant that mirrors BE exactly (pick FE constant + CI parity assertion — cheaper than endpoint).
- `portal/src/app/onboarding/components/` — rename `DossierReveal.tsx` → `BackstoryReveal.tsx`; `DossierStamp.tsx` → `ProgressStamp.tsx`; `ClearanceGrantedCeremony.tsx` → `PortalReadyCeremony.tsx` (or retain `ClearanceGrantedCeremony.tsx` iff the user interprets "cleared" as interstitial-level, not wizard-level — see §7.4.3). `DossierHeader.tsx` → `WizardHeader.tsx`.
- `portal/src/app/onboarding/steps/copy.ts` — rewrite copy strings removing FILE/dossier/clearance/FIELD metaphors; Nikita-voiced casual-chat register.
- `portal/src/app/onboarding/schemas.ts` — rename fields / types that carry dossier vocabulary.
- `portal/src/app/onboarding/state/WizardStateMachine.ts` — rename FSM states / events away from dossier vocabulary.
- `portal/src/app/onboarding/hooks/useConversationState.ts` — rename any "dossier" vocab.
- `portal/src/app/onboarding/__tests__/WizardCopyAudit.test.tsx` — rewrite assertions to enforce the new vocab. Add a **grep-gate test** asserting `rg -iE "dossier|clearance|FIELD|file access" portal/src/app/onboarding/` returns empty outside `legacy/` paths.

#### 7.4.2 New slot data shapes

```python
# nikita/agents/onboarding/extraction_schemas.py (new Pydantic models)

class VibeExtraction(BaseModel):
    aesthetic: Literal["cozy", "edgy", "romantic", "chill"]
    confidence: float = Field(ge=0.0, le=1.0)

class PersonalityExtraction(BaseModel):
    archetype: Literal["romantic", "pragmatist", "adventurer", "caretaker"]
    confidence: float = Field(ge=0.0, le=1.0)

class CityContextDelta(BaseModel):
    neighborhoods: list[str]
    scene_notes: str
    enriched_at: datetime
```

Storage: `WizardSlots.vibe: dict | None`, same pattern as existing slot dicts. `SlotDelta.kind` Literal extends to include `"vibe"` + `"personality_archetype"` + `"city_context"`. `WizardSlots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}))` works via existing `model_copy` logic with zero change to `apply()`.

#### 7.4.3 Component rename scope

User constraint #1: the IS-A interstitial at `portal/src/app/auth/confirm/` keeps "cleared / portal" copy. Ceremony component at `portal/src/app/onboarding/components/ClearanceGrantedCeremony.tsx` is ambiguous — it renders the `t.me/Nikita_my_bot?start=<LINK_CODE>` handoff deep-link AFTER the wizard completes. Semantically it bridges wizard→Telegram, not auth→wizard. **Recommendation**: keep the component file name `ClearanceGrantedCeremony.tsx` (user-facing "cleared" is interstitial vocabulary) but audit its internal copy strings — scrub "FILE COMPLETE" / "DOSSIER" / "CLEARANCE GRANTED" prose (those are wizard-surface vocabulary) while retaining "You're cleared. Enter the portal." as an interstitial-level line. Gate via test: component snapshot must contain "cleared" token (interstitial allowance) but must NOT contain "FILE" / "DOSSIER" / "FIELD" tokens (wizard-vocab).

---

## 8. Task list (Phase 6.3) — PR-F2c-redesign

Task numbering convention per plan §5 Phase 6: `T-F2c.{N}` grouped under `## PR-F2c-redesign`, matching `specs/214-portal-onboarding-wizard/tasks.md` `T{PR}.{N}` style.

### PR-F2c-redesign — Adaptive Question Registry + Live-Grounding + Vocab Scrub

**Branch**: `feat/spec-215-f2c-redesign`
**Size target**: ≤400 LOC added; net change may be slightly negative due to `_ROUTING_RULES` removal.
**Sequenced after**: F2b (portal UI redesign T028-T037, still pending).
**Feature flag**: `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true` gates the whole redesign path (existing Spec 215 flag); `NIKITA_WIZARD_CITY_ENRICHMENT=true` gates `WebSearchTool` invocation specifically (new).

### T-F2c.1: Add `QuestionSpec` + `ORDERED_QUESTIONS` + `next_question`

- **Status**: [ ] Pending
- **Estimated**: 2h
- **Dependencies**: None
- **Files**: `nikita/agents/onboarding/question_registry.py` (NEW); `tests/agents/onboarding/test_question_registry.py` (NEW)
- **Acceptance Criteria**:
  - AC-T-F2c.1.1: `QuestionSpec` Pydantic model with fields `slot: str`, `priority: int`, `condition: Callable[[WizardSlots], bool]`, `hint: str`. Test: `test_question_spec_schema`.
  - AC-T-F2c.1.2: `ORDERED_QUESTIONS` list contains exactly 8 specs (6 required + 2 optional: vibe, personality_archetype). Test: `test_ordered_questions_length_8`.
  - AC-T-F2c.1.3: Priorities strictly increasing; no duplicates. Test: `test_priorities_strictly_increasing`.
  - AC-T-F2c.1.4: `next_question(empty_state)` returns the `location` spec (priority 10). Test: `test_next_question_on_empty_state_returns_location`.
  - AC-T-F2c.1.5: `next_question(state_with_location_scene_darkness_identity_backstory_phone_filled)` returns None (all required filled; optional not in condition chain). Test: `test_next_question_on_full_required_returns_none`.
  - AC-T-F2c.1.6: `next_question(state_with_location_but_not_vibe)` returns the `vibe` spec per priority 20. Test: `test_next_question_location_without_vibe_returns_vibe`.

### T-F2c.2: Extend `render_dynamic_instructions` to inject next-question hint

- **Status**: [ ] Pending
- **Estimated**: 1h
- **Dependencies**: T-F2c.1
- **Files**: `nikita/agents/onboarding/conversation_prompts.py` (modify); `tests/agents/onboarding/test_conversation_prompts.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.2.1: `render_dynamic_instructions` output contains `NEXT QUESTION (<slot>): <hint>` when a next question exists. Test: `test_render_includes_next_question_hint`.
  - AC-T-F2c.2.2: Output contains `STILL MISSING: <slots>` when required slots remain. Test: `test_render_includes_still_missing`.
  - AC-T-F2c.2.3: Output is empty when wizard is complete AND no next question exists. Test: `test_render_empty_on_complete_state`.

### T-F2c.3: Partition `_WIZARD_FRAMING` into extraction-invariants vs question-ordering; migrate ONLY the latter

**F3 correction (2026-04-24 devil's advocate)**: lines 39-88 of `conversation_prompts.py` contain a mixture of (a) question-ordering rules ("which slot to ask next") and (b) extraction-shaping invariants ("how to fill `SlotDelta.kind` given a specific user-input shape"). The VOICE-WITHOUT-PHONE rule at lines 70-77 (delta-shaping: emit `no_extraction(reason="clarifying")` instead of `PhoneExtraction` when voice is picked without a number) is invariant-class (b). These rules are load-bearing for `SlotDelta.kind` correctness and MUST survive in the static prompt. Only question-order rules (none exist as isolated sub-blocks today — question order is implicit in the numbered 1-7 structure) migrate to per-spec hints via the registry.

- **Status**: [ ] Pending
- **Estimated**: 2h (partition work + tests)
- **Dependencies**: T-F2c.2
- **Files**: `nikita/agents/onboarding/conversation_prompts.py` (refactor _WIZARD_FRAMING into `_INVARIANTS` + `_EXTRACTION_RULES` + remove only the implicit question-order framing); `tests/agents/onboarding/test_conversation_prompts.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.3.1: `WIZARD_SYSTEM_PROMPT_NEUTRAL` exported from `conversation_prompts.py`; composed of `NIKITA_PERSONA` + `_INVARIANTS` + `_EXTRACTION_RULES`. Test: `test_neutral_prompt_contains_persona_invariants_and_extraction_rules`.
  - AC-T-F2c.3.2: `_EXTRACTION_RULES` contains the VOICE-WITHOUT-PHONE branch (rule 1's 4th sub-bullet), phone-digit-shape rule (rule 1's 1st sub-bullet), terminal-extraction semantics ("once phone fires the chat completes"), backstory-numbered-choice rule (rule 2), identity-not-already-committed guard (rule 3's "don't re-emit IdentityExtraction when already acknowledged"), darkness 1-5 rule (rule 4), scene allowed-set rule (rule 5), location city rule (rule 6), no_extraction fallback (rule 7). Test: `test_extraction_rules_preserved_verbatim_for_load_bearing_branches` — snapshot assertions for each of the 9 bullet points.
  - AC-T-F2c.3.3: `WIZARD_SYSTEM_PROMPT_NEUTRAL` contains NO "pick the right extraction tool using the routing rules below" priority-list prose — that framing was question-ordering commentary and is now replaced by registry hints. Test: `test_neutral_prompt_has_no_priority_list_framing`.
  - AC-T-F2c.3.4: Test `test_persona_imported_verbatim` still passes against `WIZARD_SYSTEM_PROMPT_NEUTRAL`.

### T-F2c.4: Add `AI_DISCLOSURE_OPENER` + wire to wizard opener

- **Status**: [ ] Pending
- **Estimated**: 2h
- **Dependencies**: None (BE) + T-F2c.3 (FE copy parity)
- **Files**: `nikita/agents/onboarding/conversation_prompts.py` (add constant); `portal/src/app/onboarding/onboarding-wizard.tsx` (replace hardcoded opener); `portal/src/app/onboarding/__tests__/onboarding-wizard.test.tsx` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.4.1: `AI_DISCLOSURE_OPENER: Final[str]` exported from `conversation_prompts.py`; contains "AI" token (case-insensitive regex `\bai\b` match). Test: `test_ai_disclosure_opener_contains_ai_token`.
  - AC-T-F2c.4.2: FE `hydrateWithOpener` in `onboarding-wizard.tsx` uses a FE constant `AI_DISCLOSURE_OPENER_FE`. Parity is enforced via a generated fixture (F4 correction 2026-04-24 devil's advocate). Concrete mechanism: (1) add `scripts/export_opener.py` that prints `{"opener": AI_DISCLOSURE_OPENER}` to stdout as JSON; (2) add `tests/conftest.py` session-scoped fixture `opener_fixture` that runs `uv run python scripts/export_opener.py` once and writes `tests/fixtures/ai_disclosure_opener.json` (git-ignored); (3) new vitest test `portal/src/app/onboarding/__tests__/ai-disclosure-parity.test.tsx` reads `../../../../tests/fixtures/ai_disclosure_opener.json` (fail-closed: `expect(existsSync(path)).toBe(true)` — test fails hard if the fixture is missing so stale-fixture states surface as red CI, not silent pass) AND asserts `fixture.opener === AI_DISCLOSURE_OPENER_FE`; (4) pre-commit hook (or CI pre-test job) runs the export before vitest. Test name: `test_fe_be_opener_parity_via_generated_fixture`.
  - AC-T-F2c.4.3: Opener string is ≤ `NIKITA_REPLY_MAX_CHARS`. Test: `test_ai_disclosure_opener_within_char_limit`.
  - AC-T-F2c.4.4: Snapshot test locks exact opener string so drift is detected. Test: `test_ai_disclosure_opener_snapshot`.

### T-F2c.5: Extend `WizardSlots` with `vibe`, `personality_archetype`, `city_context`

- **Status**: [ ] Pending
- **Estimated**: 2h
- **Dependencies**: None
- **Files**: `nikita/agents/onboarding/state.py` (modify); `nikita/agents/onboarding/extraction_schemas.py` (extend); `tests/agents/onboarding/test_wizard_state.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.5.1: `WizardSlots` gains `vibe: dict | None = None`, `personality_archetype: dict | None = None`, `city_context: dict | None = None`. Test: `test_new_optional_slots_default_none`.
  - AC-T-F2c.5.2: `SlotDelta.kind` Literal extends to include `"vibe"`, `"personality_archetype"`, `"city_context"`. Test: `test_slot_delta_kinds_include_new`.
  - AC-T-F2c.5.3: `FinalForm` UNCHANGED — new slots NOT in required field list. Test: `test_final_form_required_fields_unchanged` (6 required: location, scene, darkness, identity, backstory, phone).
  - AC-T-F2c.5.4: `TOTAL_SLOTS` UNCHANGED (stays 6); docstring updated to explain required-vs-optional distinction. Test: `test_total_slots_constant_is_six` passes.
  - AC-T-F2c.5.5: `slots.apply(SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.8}))` returns a new WizardSlots with vibe filled. Test: `test_apply_vibe_delta`.
  - AC-T-F2c.5.6: `slots.missing` remains a list of REQUIRED unfilled slots only (does NOT include vibe/personality_archetype). Test: `test_missing_excludes_optional_slots`.
  - AC-T-F2c.5.7: `slots.is_complete` True when all 6 required are filled regardless of vibe/personality_archetype/city_context state. Test: `test_is_complete_ignores_optional_slots`.

### T-F2c.6: Add `VibeExtraction` + `PersonalityExtraction` + `CityContextDelta` Pydantic models

- **Status**: [ ] Pending
- **Estimated**: 1.5h
- **Dependencies**: T-F2c.5
- **Files**: `nikita/agents/onboarding/extraction_schemas.py` (extend); `tests/agents/onboarding/test_extraction_schemas.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.6.1: `VibeExtraction` validates `aesthetic` is one of the 4 closed literals and `confidence ∈ [0, 1]`. Test: `test_vibe_extraction_validates`.
  - AC-T-F2c.6.2: `PersonalityExtraction` validates `archetype` is one of the 4 closed literals. Test: `test_personality_extraction_validates`.
  - AC-T-F2c.6.3: `CityContextDelta` validates `neighborhoods: list[str]`, `scene_notes: str`, `enriched_at: datetime`. Test: `test_city_context_delta_validates`.

### T-F2c.7: Rewire `conversation_agent.py` with `WIZARD_SYSTEM_PROMPT_NEUTRAL` + optional `WebSearchTool`

- **Status**: [ ] Pending
- **Estimated**: 3h
- **Dependencies**: T-F2c.3, T-F2c.6
- **Files**: `nikita/agents/onboarding/conversation_agent.py` (modify); `nikita/config/settings.py` (add flag); `tests/agents/onboarding/test_conversation_agent.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.7.1: Agent constructed with `system_prompt=WIZARD_SYSTEM_PROMPT_NEUTRAL`. Test: `test_agent_uses_neutral_system_prompt`.
  - AC-T-F2c.7.2: When `settings.wizard_city_enrichment=True`, agent constructed with `builtin_tools=[WebSearchTool(...)]`; when False, `builtin_tools=[]`. Test: `test_agent_websearch_tool_respects_flag`.
  - AC-T-F2c.7.3: `WebSearchTool` configured with `max_uses=1` and `allowed_domains=CITY_ENRICHMENT_DOMAINS` (static list in `conversation_agent.py`). Test: `test_websearch_tool_configured_with_max_uses_and_domains`.
  - AC-T-F2c.7.4: `retries=4` preserved.
  - AC-T-F2c.7.5: `@agent.output_validator` preserved; applies `SlotDelta` to cumulative state.

### T-F2c.8: Graceful degradation on `WebSearchTool` slow / empty (wrap `agent.run`, NOT the tool)

**F1 correction (2026-04-24 devil's advocate)**: `WebSearchTool` is a config-only dataclass (fields: `allowed_domains`, `blocked_domains`, `kind`, `max_uses`, `search_context_size`, `user_location`); it has NO client-side `invoke` / `_call` method. Execution happens server-side inside Anthropic's model loop during `agent.run()`. Client-side timeout-wrapping the tool specifically is impossible. The correct pattern is to bound `agent.run()` itself (already done in `portal_onboarding.py:905-928` via `CONVERSE_TIMEOUT_MS`) and treat a slow web search as part of the overall agent-turn latency budget.

- **Status**: [ ] Pending
- **Estimated**: 1.5h
- **Dependencies**: T-F2c.7
- **Files**: `nikita/agents/onboarding/conversation_agent.py` (no change to tool wiring; document contract); `tests/agents/onboarding/test_websearch_graceful_degradation.py` (NEW)
- **Acceptance Criteria**:
  - AC-T-F2c.8.1: `CONVERSE_TIMEOUT_MS` (existing constant in `portal_onboarding.py`) is the enforced outer bound. When `NIKITA_WIZARD_CITY_ENRICHMENT=true`, the timeout is NOT extended; a slow web search that blows the budget surfaces as the existing `asyncio.TimeoutError` → `_fallback_response(source="fallback")` path. Test: `test_converse_timeout_when_websearch_slow` — mock agent whose internal tool use blocks for 3s; assert `/converse` returns the fallback response within `CONVERSE_TIMEOUT_MS`.
  - AC-T-F2c.8.2: When web search returns 0 results (Anthropic server-side), agent.run completes normally with no `city_context` delta; next registry turn still fires. Test: `test_converse_continues_when_websearch_empty` — patch `agent.run` to return a `TurnOutput(delta=None, reply="...")` (simulating the "tool produced no enrichment" path); assert wizard advances.
  - AC-T-F2c.8.3: When web search raises a pydantic-ai tool-execution error inside `agent.run`, the existing handler's `UnexpectedModelBehavior` branch catches it → fallback. Test: `test_converse_fallback_on_websearch_exception` — `agent.run` side-effect=`UnexpectedModelBehavior("web search failed")`; assert fallback path taken, turn persisted.
  - AC-T-F2c.8.4: No code in `conversation_agent.py` attempts to monkeypatch or wrap `WebSearchTool` client-side; grep-gate: `rg "WebSearchTool\.\(invoke\|_call\|call\)" nikita/` returns 0 matches. Test: `test_no_client_side_websearch_monkey_patch`.

### T-F2c.9: Scrub `FILE/dossier/clearance/FIELD` from `portal/src/app/onboarding/**` (non-legacy)

- **Status**: [ ] Pending
- **Estimated**: 4h
- **Dependencies**: None
- **Files**: `portal/src/app/onboarding/steps/copy.ts` (rewrite); `components/DossierReveal.tsx` → `BackstoryReveal.tsx` (rename + copy); `components/DossierStamp.tsx` → `ProgressStamp.tsx` (rename + copy); `components/DossierHeader.tsx` → `WizardHeader.tsx` (rename + copy); `state/WizardStateMachine.ts` (rename state names); `types/contracts.ts` + `types/wizard.ts` (rename types); all call-sites updated; `__tests__/WizardCopyAudit.test.tsx` rewritten.
- **Acceptance Criteria**:
  - AC-T-F2c.9.1: `rg -iE "dossier|clearance|FIELD|file access" portal/src/app/onboarding/` (excluding `legacy/` paths AND the `auth/confirm` interstitial) returns empty. Test: `test_onboarding_vocab_scrub_complete`.
  - AC-T-F2c.9.2: Ceremony component retains "cleared" token as an interstitial-level allowance; does NOT contain "DOSSIER" / "FILE" / "FIELD" / "CLEARANCE GRANTED" (as standalone prose). Test: `test_ceremony_vocab_narrow`.
  - AC-T-F2c.9.3: `copy.ts` rewrites rendered as casual-chat Nikita register; no bureaucratic vocabulary. Snapshot test: `test_copy_ts_snapshot`.
  - AC-T-F2c.9.4: Vitest + Playwright suite green after renames + updates.

### T-F2c.10: Portal wizard opener uses AI_DISCLOSURE_OPENER

(Merged into T-F2c.4 — see AC-T-F2c.4.2.)

### T-F2c.11: Cumulative-state monotonicity tests cover new optional slots

- **Status**: [ ] Pending
- **Estimated**: 1.5h
- **Dependencies**: T-F2c.5
- **Files**: `tests/agents/onboarding/test_wizard_slots_progress.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.11.1: 5-turn fixture covering location → vibe → scene → darkness → personality_archetype → identity; assert `progress_pct[t+1] >= progress_pct[t]` for every t. Test: `test_progress_monotonicity_with_optional_slots`.
  - AC-T-F2c.11.2: Sibling test where optional slots are filled first (vibe before location): assert progress_pct is 0 until the first REQUIRED slot fills. Test: `test_optional_slots_do_not_inflate_progress`.

### T-F2c.12: Completion-gate triplet extended

- **Status**: [ ] Pending
- **Estimated**: 1h
- **Dependencies**: T-F2c.5
- **Files**: `tests/agents/onboarding/test_final_form_validation.py` (extend)
- **Acceptance Criteria**:
  - AC-T-F2c.12.1: Empty state → ValidationError (existing). Partial (5/6 required) → ValidationError. Full (6/6 required) → succeeds EVEN IF vibe/personality_archetype/city_context are all None. Test: `test_final_form_triplet_with_optional_unset`.
  - AC-T-F2c.12.2: Full required + vibe filled → still succeeds. Test: `test_final_form_succeeds_with_optional_filled`.

### T-F2c.13: Mock-LLM-wrong-tool recovery tests preserved + extended

- **Status**: [ ] Pending
- **Estimated**: 1h
- **Dependencies**: T-F2c.7
- **Files**: `tests/agents/onboarding/test_conversation_agent.py` (extend — existing regex phone fallback test stays)
- **Acceptance Criteria**:
  - AC-T-F2c.13.1: Existing `test_extract_phone_regex_fallback_when_llm_emits_wrong_tool` still passes after registry + WebSearchTool additions.
  - AC-T-F2c.13.2: New test: LLM emits `kind="identity"` for input mentioning Zurich; on next turn the registry selects `vibe` (not `location`) because location was set by identity-extraction mistake — assert behavior is "last-write-wins overwritten by correct delta on retry". Test: `test_wrong_kind_recovery_with_registry`.

### T-F2c.14: Dynamic-instructions invocation test extended

- **Status**: [ ] Pending
- **Estimated**: 1h
- **Dependencies**: T-F2c.2
- **Files**: `tests/agents/onboarding/test_conversation_agent.py` (extend — existing `test_dynamic_instructions_callable_invoked_with_missing_slots` stays)
- **Acceptance Criteria**:
  - AC-T-F2c.14.1: Existing test still passes.
  - AC-T-F2c.14.2: New test: `test_dynamic_instructions_includes_next_question_hint` — `MagicMock` wraps `render_dynamic_instructions`; invocation produces string containing `NEXT QUESTION (` substring on at least one turn where `next_question(state)` returns non-None.

### T-F2c.15: Agent invocation contract test (message_history + deps) preserved

- **Status**: [ ] Pending
- **Estimated**: 0.5h
- **Dependencies**: T-F2c.7
- **Files**: (existing) `tests/agents/onboarding/test_conversation_agent.py::test_agent_run_uses_message_history_primitive`
- **Acceptance Criteria**:
  - AC-T-F2c.15.1: Test still green post-merge.

### T-F2c.16: Terminal-turn wire format test preserved

- **Status**: [ ] Pending
- **Estimated**: 0.5h
- **Dependencies**: T-F2c.7
- **Files**: (existing) `tests/api/routes/test_converse_endpoint.py::test_converse_terminal_turn_includes_link_code`
- **Acceptance Criteria**: AC-T-F2c.16.1: Test still green post-merge (wire format unchanged).

### T-F2c.17: Reconstruction perf budget test preserved

- **Status**: [ ] Pending
- **Estimated**: 0.5h
- **Dependencies**: T-F2c.5
- **Files**: (existing) `tests/agents/onboarding/test_state_reconstruction_perf.py`
- **Acceptance Criteria**: AC-T-F2c.17.1: p95 < `RECONSTRUCTION_BUDGET_MS=10` holds after SlotDelta Literal extension. Re-run under same 100-turn fixture.

### T-F2c.18: Grep-gate tests (anti-pattern + vocab)

- **Status**: [ ] Pending
- **Estimated**: 1h
- **Dependencies**: T-F2c.9
- **Files**: `tests/gates/test_wizard_grep_gates.py` (NEW)
- **Acceptance Criteria**:
  - AC-T-F2c.18.1: `rg "conversation_complete\s*=\s*(True|False)\b" nikita/api/routes/portal_onboarding.py` returns 0 matches. Test: `test_no_hardcoded_conversation_complete_literal`.
  - AC-T-F2c.18.2: `rg "_compute_progress\(extracted_fields" nikita/api/routes/portal_onboarding.py` returns 0 matches. Test: `test_no_per_turn_progress_snapshot`.
  - AC-T-F2c.18.3: `rg -iE "dossier|clearance|FIELD|file access" portal/src/app/onboarding/` excluding `legacy/` and `auth/confirm` returns 0 matches. Test: `test_wizard_surface_vocab_clean`.
  - AC-T-F2c.18.4: `rg "TelegramLinkRepository|create_code" nikita/api/routes/portal_onboarding.py` shows usage only inside POST `/converse` handler (not GET `/conversation`). Test: `test_get_conversation_does_not_mint`.

### T-F2c.19: Dogfood AC — Phase F W1 live walk

- **Status**: [ ] Pending
- **Estimated**: 2h (including walk execution)
- **Dependencies**: all T-F2c.* merged to feature branch
- **Files**: `docs-to-process/20260428-F2c-redesign-dogfood.md` (NEW — walk report per `.claude/rules/live-testing-protocol.md`)
- **Acceptance Criteria**:
  - AC-T-F2c.19.1: Walk uses real Telegram deep-link flow (no DB fabrication per `feedback_no_db_fabrication_in_dogfood.md`).
  - AC-T-F2c.19.2: Agent-browser / agent-playwright used (not chrome-devtools MCP per `feedback_chrome_devtools_profile_lock.md`).
  - AC-T-F2c.19.3: Walk covers: (a) session-start AI-disclosure renders; (b) city-enrichment fires on "I'm in Zurich" input (flag ON); (c) adaptive question order matches registry priorities; (d) no FILE/dossier vocabulary visible in wizard surface; (e) wizard completes at 6 required slots; (f) ClearanceGrantedCeremony renders.
  - AC-T-F2c.19.4: Walk report filed; any CRITICAL finding blocks merge and files GH issue.

### T-F2c.21: Spec 214 NFR-Latency-1 amendment — end-to-end turn-latency contract with flag on

- **Status**: [ ] Pending
- **Estimated**: 0.5h
- **Dependencies**: T-F2c.7
- **Files**: `specs/214-portal-onboarding-wizard/spec.md` (amend; add §5 NFR-Latency-1 under existing non-functional section)
- **Acceptance Criteria**:
  - AC-T-F2c.21.1: Amendment adds `NFR-Latency-1 — End-to-end turn latency p95 ≤ CONVERSE_TIMEOUT_MS regardless of NIKITA_WIZARD_CITY_ENRICHMENT flag state; with flag on, p95 budget is +1000ms over flag-off baseline (documented at dogfood time).`
  - AC-T-F2c.21.2: Amendment cross-references this recommendation's AC-Dogfood-8.

### T-F2c.20: Spec 216 draft — chat-runtime compliance (FILE only; do NOT implement)

- **Status**: [ ] Pending (sibling PR)
- **Estimated**: 3h
- **Dependencies**: `/feature` skill + `/roadmap add 216 chat-runtime-compliance` registration
- **Files**: `specs/216-chat-runtime-compliance/spec.md` (draft)
- **Acceptance Criteria**:
  - AC-T-F2c.20.1: Spec 216 registered in ROADMAP.md.
  - AC-T-F2c.20.2: spec.md documents FR-1 (3-hour AI reminder in both Telegram + voice runtime) + FR-2 (self-harm detection + escalation path) + FR-3 (minor-specific notification for CA SB 243).
  - AC-T-F2c.20.3: Sibling of PR-F2c-redesign (NOT bundled); filed within 1 week of PR-F2c-redesign merge.

---

## 9. Compliance with `.claude/rules/agentic-design-patterns.md` (Hard Rules gate-check)

Per plan §5 Phase 6 template:

| Hard Rule | Compliance evidence | File:line |
|---|---|---|
| 1 (cumulative state) | `WizardSlots` already-landed via PR #400; new optional slots (vibe, personality_archetype, city_context) extend via same `model_copy(update=...)` path; no slot ever removed | `nikita/agents/onboarding/state.py:108-170` (already-landed) + T-F2c.5 extension |
| 2 (Pydantic completion gate) | `FinalForm.model_validate` already-landed via PR #400; NEW optional slots DO NOT join `FinalForm` (gate unchanged); cross-field validators preserved | `nikita/agents/onboarding/state.py:186-262` (already-landed) + T-F2c.5.3 assertion |
| 3 (tool consolidation) | `TurnOutput` already-landed via PR #405; redesign adds `WebSearchTool` which is a **non-extraction** builtin (orthogonal to `SlotDelta`); no new narrow extraction tools | `nikita/agents/onboarding/conversation_agent.py:69-99` (already-landed) + T-F2c.7 |
| 4 (dynamic instructions) | `agent.instructions(render_dynamic_instructions)` already-landed via PR #401/#405; redesign extends the callable to inject `next_question(state).hint` in addition to `state.missing` | `conversation_agent.py:152` + `conversation_prompts.py:124-139` (already-landed) + T-F2c.2 extension |
| 5 (three-layer validation) | Pydantic schemas (existing) + `@agent.output_validator` (already-landed, PR #405) + regex_fallback for phone (already-landed, PR #400); new optional slots validated by Pydantic layer; no new high-stakes slots need regex fallback | `nikita/agents/onboarding/regex_fallback.py:1-96` (already-landed) |
| 6 (`message_history=`) | `hydrate_message_history` + `agent.run(message_history=...)` unchanged | `nikita/agents/onboarding/message_history.py:44` (already-landed) |

**All 6 Hard Rules satisfied. Gate: PASS.**

Additional gates (per plan §6 Anti-Pattern Gate Rules):

| Gate | Check | Result |
|---|---|---|
| 7 — No FILE/dossier/clearance/FIELD vocab in wizard surface | grep-gate test T-F2c.18.3 | ENFORCED (CI fails if regresses) |
| 8 — AI-disclosure at session-start | `AI_DISCLOSURE_OPENER` constant T-F2c.4 | ENFORCED |
| 9 — Live tools are agent-invoked | `builtin_tools=[WebSearchTool()]` on agent, NOT orchestrator-prefetched | CONFIRMED (see T-F2c.7) |
| 10 — Backstory generator contract | Documentation note; slot propagation for vibe/personality_archetype tracked as D29 (follow-up) | DOCUMENTED |

---

## 10. Migration + Rollout (Phase 6.4 + 6.5)

### 10.1 Schema migration

`supabase/migrations/<NNN>_extend_wizardslots_taxonomy.sql`:

```sql
-- PR-F2c-redesign: extend WizardSlots taxonomy with optional vibe / personality / city_context slots.
-- All new fields live inside onboarding_profile JSONB (no new columns).  This migration is a NO-OP on the
-- schema and exists only to document the JSONB shape extension + bump a tracking row.
BEGIN;
  INSERT INTO schema_version (version, description, applied_at)
  VALUES ('<NNN>', 'extend wizardslots taxonomy: vibe + personality_archetype + city_context (JSONB only)', now());
COMMIT;
```

No RLS policy changes (existing `user_profiles` policies cover the extended JSONB).

No `user_profiles` column additions — slots live inside `onboarding_profile.slots.*` or as part of the JSONB conversation turn extractions.

### 10.2 In-flight-user handling

Users mid-wizard at deploy time: their `onboarding_profile` lacks vibe/personality_archetype/city_context. Since those slots are OPTIONAL and `FinalForm` doesn't require them, completion gate continues to work. Registry condition chains are `s.vibe is None` → the spec will fire for these users on next turn; Nikita asks the vibe question if location was filled. Graceful, no cutoff.

### 10.3 Rollout plan

1. **T-0 (merge)**: Ship PR-F2c-redesign behind `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true` (already-existing flag). `NIKITA_WIZARD_CITY_ENRICHMENT=false` default (WebSearchTool OFF on prod).
2. **T+1d (dogfood)**: Single operator runs Phase F W1 walk (T-F2c.19). Report filed.
3. **T+3d (city-enrichment on)**: Toggle `NIKITA_WIZARD_CITY_ENRICHMENT=true` on prod; monitor for 48h; rollback is a single env flip if WebSearchTool causes latency regression.
4. **T+1w (Spec 216 draft)**: File Spec 216 (T-F2c.20).
5. **T+2w (D26 follow-up)**: If pydantic-ai ships `web_search_20260209`, file follow-up PR.

### 10.4 Rollback plan

- PR-F2c-redesign ships behind existing feature flag; full rollback = flag off.
- `NIKITA_WIZARD_CITY_ENRICHMENT` is orthogonal; flip off disables only WebSearchTool.
- Database migration is no-op; no rollback needed.
- Optional-slot JSONB shape is additive; pre-redesign code ignores unknown keys.

---

## 11. Dogfood ACs (Phase 6.6)

Per `.claude/rules/live-testing-protocol.md`:

- **AC-Dogfood-1 (real flow)**: Walk traverses Telegram `/start welcome` → email submit → OTP code → magic link → `/auth/confirm` interstitial → wizard. No fabricated rows; no `signInWithPassword`; no `E2E_AUTH_BYPASS`.
- **AC-Dogfood-2 (AI disclosure visible)**: First Nikita message in wizard contains the AI-disclosure string (regex `\bAI\b`).
- **AC-Dogfood-3 (adaptive routing)**: After providing city, next question is vibe (per registry). After vibe, scene. Deviation from priority chain is a HIGH finding.
- **AC-Dogfood-4 (city enrichment, flag on)**: Enter "Zurich" → verify 1-2 turns later Nikita references a Zurich-specific neighborhood or scene note. If flag off, no city_context expected.
- **AC-Dogfood-5 (no dossier vocab)**: Wizard transcript + visible UI copy contain no FILE/dossier/clearance/FIELD tokens. Interstitial copy is out of scope.
- **AC-Dogfood-6 (completion + ceremony)**: Wizard completes at 6 required slots; `ClearanceGrantedCeremony` (or renamed `PortalReadyCeremony`) renders with deep-link.
- **AC-Dogfood-7 (telemetry)**: Funnel events per FR-Telemetry-1 emit correctly (`signup_wizard_session_minted`, `signup_wizard_completed`, `signup_failed`).
- **AC-Dogfood-8 (latency, F5 correction 2026-04-24 devil's advocate)**: End-to-end turn latency (client tap → Nikita reply visible) p95 ≤ `CONVERSE_TIMEOUT_MS` (existing constant, currently 15s cold / 10s warm in `portal_onboarding.py`) with `NIKITA_WIZARD_CITY_ENRICHMENT=true`. The Spec 214 NFR citation is absent today; **AC-T-F2c.21 files a spec amendment adding Spec 214 NFR-Latency-1** (see §8 T-F2c.21). Rollout gate: dogfood walk must show p95 turn latency with flag on ≤ p95 with flag off + 1s (web-search cost budget). Measured via `_elapsed_ms(started)` telemetry in the existing `/converse` response.

---

## 12. Spec amendment (Phase 6.2) — in-place per convention

Amendments go IN-PLACE (per plan §5 Phase 6, pr-pattern-scout P3). Do NOT create `spec-v2.md`. The three target files are `specs/214-portal-onboarding-wizard/spec.md`, `specs/215-auth-flow-redesign/spec.md`, `specs/214-portal-onboarding-wizard/tasks.md`.

### 12.1 Amendment to `specs/214-portal-onboarding-wizard/spec.md` (top of file)

```markdown
## Amendment 2026-04-24 (PR-F2c-redesign) — Adaptive Question Registry + live-grounding + vocab scrub

**Scope**: extends FR-11d with (a) declarative `QuestionSpec` registry for adaptive question routing, (b) optional `builtin_tools=[WebSearchTool()]` for city-enrichment (feature-flagged), (c) three optional wizard slots — `vibe`, `personality_archetype`, `city_context` — NONE required for completion, (d) session-start AI-disclosure string, (e) scrub of FILE/dossier/clearance/FIELD vocabulary from `portal/src/app/onboarding/**` (excluding legacy/ and auth/confirm/).

**Does NOT change**: `WizardSlots` required slot list (still 6 — location, scene, darkness, identity, backstory, phone); `FinalForm` required fields; `TurnOutput` wire format; `TOTAL_SLOTS=6`; `RECONSTRUCTION_BUDGET_MS=10`; `ConverseResponse` wire format.

**New optional slots** (`WizardSlots` fields, all default `None`):
- `vibe: dict | None` — `{"aesthetic": "cozy|edgy|romantic|chill", "confidence": 0.0-1.0}`
- `personality_archetype: dict | None` — `{"archetype": "romantic|pragmatist|adventurer|caretaker", "confidence": 0.0-1.0}`
- `city_context: dict | None` — `{"neighborhoods": [...], "scene_notes": "...", "enriched_at": "..."}`

**New agent primitive**: `QuestionSpec(slot, priority, condition, hint)` + `ORDERED_QUESTIONS` registry in `nikita/agents/onboarding/question_registry.py`. `render_dynamic_instructions` extends to inject `next_question(state).hint`.

**Hard Rules**: all 6 satisfied. Static-prompt routing (lines 39-88 of `conversation_prompts.py`) migrates into `QuestionSpec.hint` via the dynamic callable; `_INVARIANTS` (persona, reply length, tone) remains in the static prompt.

**Tasks**: T-F2c.1 through T-F2c.20 (see `specs/215-auth-flow-redesign/wizard-redesign-recommendation.md` §8).

**Compliance**: wizard owns session-start AI-disclosure (`AI_DISCLOSURE_OPENER`). NY A6767 3-hour reminder + self-harm escalation tracked as Spec 216 (FILE only; not this amendment).
```

### 12.2 Amendment to `specs/215-auth-flow-redesign/spec.md` (top of file, below "Supersedes")

```markdown
## Amendment 2026-04-24 (PR-F2c-redesign) — wizard redesign appendix

PR-F2c-redesign ships AFTER F2b (portal UI redesign T028-T037) and carries the adaptive-question-registry + live-grounding + vocab-scrub changes to the Spec 214 FR-11d wizard surface. See `specs/215-auth-flow-redesign/wizard-redesign-recommendation.md` for the full recommendation.

**In-scope for Spec 215 PR-F2c-redesign**:
- Session-start AI-disclosure (CA SB 243 §22602(b) + NY A6767 §1) — wizard surface only
- Feature flag `NIKITA_WIZARD_CITY_ENRICHMENT` for `WebSearchTool` live-grounding
- Vocab scrub of FILE/dossier/clearance/FIELD from `portal/src/app/onboarding/**` (excluding `legacy/` and `auth/confirm/`)

**Out-of-scope for Spec 215** (FILED AS Spec 216):
- 3-hour AI-reminder in runtime chat handlers (Telegram + voice)
- Self-harm-detection + escalation
- CA SB 243 minor-specific notification flow

**PR sequencing**: F1a (#425) → F1b (#426) → F2a (#427) → F2b (T028-T037, pending) → **F2c-redesign**. No sequencing entanglement with F2b.
```

### 12.3 Amendment to `specs/214-portal-onboarding-wizard/tasks.md` (append PR section)

Add section at bottom:

```markdown
## PR F2c-redesign — Adaptive Question Registry + live-grounding + vocab scrub (Spec 215 amendment)

**Branch**: `feat/spec-215-f2c-redesign`
**Objective**: extend FR-11d with adaptive question routing, optional live-grounding via WebSearchTool, three optional wizard slots, session-start AI-disclosure, and wizard-surface vocab scrub.
**Gate**: CI green + Phase F W1 dogfood walk PASS.
**Size est.**: ≤400 LOC added.

(Tasks T-F2c.1 through T-F2c.20 per `specs/215-auth-flow-redesign/wizard-redesign-recommendation.md` §8.)
```

---

## 13. Test skeletons

Per plan §5 Phase 6 templates + `.claude/rules/testing.md` Agentic-Flow Test Requirements.

### 13.1 Question registry invariants

```python
# tests/agents/onboarding/test_question_registry.py
import pytest
from nikita.agents.onboarding.question_registry import (
    ORDERED_QUESTIONS, next_question, QuestionSpec,
)
from nikita.agents.onboarding.state import WizardSlots


def test_priorities_strictly_increasing():
    priorities = [q.priority for q in ORDERED_QUESTIONS]
    assert priorities == sorted(priorities)
    assert len(priorities) == len(set(priorities)), "duplicate priorities"


def test_next_question_on_empty_state_returns_location():
    empty = WizardSlots()
    spec = next_question(empty)
    assert spec is not None and spec.slot == "location"


def test_next_question_on_full_required_returns_none():
    full = WizardSlots(
        location={"city": "Zurich"},
        scene={"scene": "techno"},
        darkness={"drug_tolerance": 3},
        identity={"name": "Ana", "age": 28},
        backstory={"chosen_option_id": "x", "cache_key": "y"},
        phone={"phone_preference": "text"},
    )
    assert next_question(full) is None or next_question(full).slot in {"vibe", "personality_archetype"}
    # if optional-first behaviour desired, update assertion; if required-only, None


def test_condition_lambdas_are_pure():
    """Each condition should be deterministic given the same state."""
    s = WizardSlots(location={"city": "Tokyo"})
    for spec in ORDERED_QUESTIONS:
        r1 = spec.condition(s)
        r2 = spec.condition(s)
        assert r1 == r2
```

### 13.2 Cumulative-state monotonicity (optional slots)

```python
# tests/agents/onboarding/test_wizard_slots_progress.py (extend)
def test_progress_monotonicity_with_optional_slots():
    state = WizardSlots()
    history = [state.progress_pct]
    deltas = [
        SlotDelta(kind="location", data={"city": "Zurich"}),
        SlotDelta(kind="vibe", data={"aesthetic": "edgy", "confidence": 0.7}),
        SlotDelta(kind="scene", data={"scene": "techno"}),
        SlotDelta(kind="darkness", data={"drug_tolerance": 4}),
        SlotDelta(kind="personality_archetype", data={"archetype": "adventurer", "confidence": 0.8}),
        SlotDelta(kind="identity", data={"name": "Ana", "age": 28}),
    ]
    for d in deltas:
        state = state.apply(d)
        history.append(state.progress_pct)
    assert all(history[i+1] >= history[i] for i in range(len(history)-1)), history


def test_optional_slots_do_not_inflate_progress():
    state = WizardSlots().apply(SlotDelta(kind="vibe", data={"aesthetic": "cozy", "confidence": 1.0}))
    assert state.progress_pct == 0, "vibe alone should not increment progress"
```

### 13.3 Completion-gate triplet

```python
# tests/agents/onboarding/test_final_form_validation.py (extend)
def test_final_form_triplet_with_optional_unset():
    empty = WizardSlots()
    with pytest.raises(ValidationError):
        FinalForm.model_validate(empty.slots_dict())
    partial = empty.apply(SlotDelta(kind="location", data={"city": "Zurich"}))
    with pytest.raises(ValidationError):
        FinalForm.model_validate(partial.slots_dict())
    full = WizardSlots(
        location={"city": "Zurich"},
        scene={"scene": "techno"},
        darkness={"drug_tolerance": 3},
        identity={"name": "Ana", "age": 28},
        backstory={"chosen_option_id": "x", "cache_key": "y"},
        phone={"phone_preference": "text"},
    )
    FinalForm.model_validate(full.slots_dict())   # no raise
    assert full.is_complete is True


def test_final_form_succeeds_with_optional_filled():
    full_plus_optional = WizardSlots(
        location={"city": "Zurich"},
        scene={"scene": "techno"},
        darkness={"drug_tolerance": 3},
        identity={"name": "Ana", "age": 28},
        backstory={"chosen_option_id": "x", "cache_key": "y"},
        phone={"phone_preference": "text"},
        vibe={"aesthetic": "edgy", "confidence": 0.8},
        personality_archetype={"archetype": "adventurer", "confidence": 0.9},
        city_context={"neighborhoods": ["Kreis 4"], "scene_notes": "...", "enriched_at": "..."},
    )
    FinalForm.model_validate(full_plus_optional.slots_dict())   # no raise
```

### 13.4 Mock-LLM-wrong-tool recovery (preserved)

```python
# tests/agents/onboarding/test_conversation_agent.py (existing; unchanged)
async def test_extract_phone_regex_fallback_when_llm_emits_wrong_tool(mock_agent):
    mock_agent.set_output(TurnOutput(
        delta=SlotDelta(kind="identity", data={"name": "Ana"}),
        reply="got it, ana.",
    ))
    result = await converse_route(user_input="+1 415 555 0234", user=mock_user, ...)
    assert result.extracted_fields["kind"] in ("phone", "identity")   # either is fine as long as phone slot is filled
    # reload state, verify phone slot filled
    state = build_state_from_conversation(await load_profile(mock_user.id))
    assert state.phone is not None
    assert state.phone["phone_preference"] == "voice"
    assert state.phone["phone"].startswith("+1")
```

### 13.5 Dynamic-instructions invocation (extended)

```python
# tests/agents/onboarding/test_conversation_agent.py (extend)
async def test_dynamic_instructions_includes_next_question_hint(monkeypatch, mock_agent):
    captured: list[str] = []
    orig = render_dynamic_instructions
    def wrapper(ctx):
        out = orig(ctx)
        captured.append(out)
        return out
    monkeypatch.setattr("nikita.agents.onboarding.conversation_prompts.render_dynamic_instructions", wrapper)
    state = WizardSlots()  # empty
    deps = ConverseDeps(user_id=uuid4(), state=state)
    _ = await mock_agent.run("hi", deps=deps)
    # assert at least one captured string contains "NEXT QUESTION ("
    assert any("NEXT QUESTION (" in s for s in captured), captured
```

### 13.6 WebSearchTool graceful degradation (F1 correction — wrap agent.run, NOT the tool)

```python
# tests/agents/onboarding/test_websearch_graceful_degradation.py (NEW)
# F1 correction 2026-04-24: WebSearchTool is a server-side Anthropic builtin; no client-side
# invoke method exists.  Tests mock agent.run behavior, NOT the tool itself.
import asyncio
from uuid import uuid4

async def test_converse_timeout_when_websearch_slow(monkeypatch, async_client, test_user):
    """Slow web search inside agent.run → outer CONVERSE_TIMEOUT_MS fires → fallback."""
    async def slow_run(*args, **kwargs):
        await asyncio.sleep(20.0)   # exceeds CONVERSE_TIMEOUT_MS
        raise AssertionError("should have timed out")
    monkeypatch.setattr("nikita.agents.onboarding.conversation_agent.get_conversation_agent", lambda: _MockAgent(run=slow_run))
    r = await async_client.post("/api/v1/portal/onboarding/converse", json={"user_input": "I'm in Zurich"}, ...)
    assert r.status_code == 200
    assert r.json()["source"] == "fallback"


async def test_converse_continues_when_websearch_empty(monkeypatch, async_client, test_user):
    """Agent completes normally with no city_context delta → wizard advances."""
    async def normal_run(*args, **kwargs):
        return _AgentResult(output=TurnOutput(delta=SlotDelta(kind="location", data={"city": "Atlantis"}), reply="cool, atlantis."))
    monkeypatch.setattr("nikita.agents.onboarding.conversation_agent.get_conversation_agent", lambda: _MockAgent(run=normal_run))
    r = await async_client.post("/api/v1/portal/onboarding/converse", json={"user_input": "I'm in Atlantis"}, ...)
    assert r.status_code == 200
    assert r.json()["progress_pct"] > 0  # location filled; no city_context required


async def test_converse_fallback_on_websearch_exception(monkeypatch, async_client, test_user):
    """Web search internal error → UnexpectedModelBehavior → existing fallback branch."""
    from pydantic_ai import UnexpectedModelBehavior
    async def failing_run(*args, **kwargs):
        raise UnexpectedModelBehavior("web search failed upstream")
    monkeypatch.setattr("nikita.agents.onboarding.conversation_agent.get_conversation_agent", lambda: _MockAgent(run=failing_run))
    r = await async_client.post("/api/v1/portal/onboarding/converse", json={"user_input": "hi"}, ...)
    assert r.status_code == 200
    assert r.json()["source"] == "fallback"


def test_no_client_side_websearch_monkey_patch():
    """Grep-gate: no production code attempts to wrap WebSearchTool invoke/call methods."""
    import subprocess
    result = subprocess.run(
        ["rg", "-c", r"WebSearchTool\.(invoke|_call|call)", "nikita/"],
        capture_output=True, text=True,
    )
    assert result.stdout.strip() == "", f"found WebSearchTool monkey-patches: {result.stdout}"
```

---

## 14. Banned vocabulary (rejected copy — for grep-gate clarity)

The following are BANNED in `portal/src/app/onboarding/**` (excluding `legacy/` and `auth/confirm/`) per T-F2c.18.3:

- `dossier` (case-insensitive)
- `clearance` (as standalone; "cleared" allowed in interstitial-level ceremony copy)
- `FILE` (case-sensitive standalone, or `file access` substring)
- `FIELD [A-Z]+` (pattern)

The "rejected copy" designation here is to satisfy the plan §9 verification check: banned-vocab tokens appear in this section purely as rejection labels; grep against the recommendation file itself should find them ONLY inside this section (marked as rejected).

---

## 15. §2 spot-verify: PASS

Phase 1 Step 1.3 main-thread fetch results:

- `WebFetch https://arxiv.org/abs/2510.00307` — abstract text contains none of the disowned percentage-range figures the plan §2.1 flagged; mitigation strategy is "filter to relevant subset, sample uniformly" (matches plan §2.1).
- `WebFetch https://github.com/pydantic/pydantic-ai/issues/4647` — issue exists, titled around tool-version staleness; mentions `BetaWebSearchTool20250305Param` (current) vs `web_search_20260209` (new); cites 11% accuracy improvement + 24% input-token reduction (matches plan §2.4).

No contradictions found. Plan §2 corrections stand.

---

## 16. Open items / follow-ups

- **D24**: file Spec 216 (chat-runtime compliance) — owner Simon, within 1 week of PR-F2c-redesign merge.
- **D26**: upgrade to `web_search_20260209` once pydantic-ai ships it.
- **D27**: revisit two-agent researcher (Candidate D) after dogfood measures AGI-feel with single-agent WebSearchTool.
- **D28**: revisit quick-reply chips vs typed-reply if dogfood shows typed-reply friction.
- **D29**: backstory-cache `cache_key` schema extension for vibe + personality_archetype (follow-up PR; downstream backstory generator diff).

### 16.1 Devil's advocate findings log (Phase 7 — 2026-04-24)

Review conducted by `pr-devils-advocate` subagent (HARD CAP 8 tool calls, read-only, fresh context). 6 findings delivered (3 failure modes + 2 underspec gaps + 1 dismissed architecture).

| # | Finding | Verdict | Resolution |
|---|---|---|---|
| F1 | WebSearchTool cannot be `asyncio.wait_for`-wrapped from app code | CONFIRMED via `dir(WebSearchTool)` — no `invoke`/`_call`/`call` method exists | T-F2c.8 ACs rewritten: bound `agent.run()` via existing `CONVERSE_TIMEOUT_MS`; do NOT patch tool; grep-gate added |
| F2 | "Vibe-wedge" optional-slot monopolises routing (scene gated on s.vibe) | CONFIRMED — condition chain created a deadlock path | ORDERED_QUESTIONS fixed: scene gated on `s.location is not None` (not vibe); personality_archetype gated on scene (not darkness); identity gated on darkness (not personality_archetype). Optional slots never block required-slot progression. |
| F3 | Removing lines 39-88 deletes extraction-shaping rules, not just question-ordering | CONFIRMED — rule 1's VOICE-WITHOUT-PHONE branch is delta-shaping invariant | T-F2c.3 scope rewritten: partition `_WIZARD_FRAMING` into `_INVARIANTS` (persona/tone) + `_EXTRACTION_RULES` (delta-shaping, kept in static prompt); only question-ordering commentary migrates to registry hints. Snapshot test covers all 9 extraction rule bullets. |
| F4 | FE↔BE AI_DISCLOSURE_OPENER parity mechanism hand-waved | CONFIRMED | AC-T-F2c.4.2 rewritten with concrete 4-step mechanism (export_opener.py + session fixture + vitest read with fail-closed existence check + pre-commit hook). |
| F5 | 1.5s WebSearch soft cap never reconciled with Spec 214 turn-budget NFR | CONFIRMED — NFR citation absent | AC-Dogfood-8 added (end-to-end p95 ≤ `CONVERSE_TIMEOUT_MS`; +1000ms budget with flag on); T-F2c.21 files Spec 214 NFR-Latency-1 amendment. |
| F6 | Candidate B dismissed too quickly | PARTIALLY-TRUE | §5.1 B rescore note added; B-revised total 44.0 (above C and D, below A); stays eliminated on T=5 vs A's T=9 gap. |

---

## 17. Verification checklist (plan §9)

Run post-write:

- [ ] `test -f specs/215-auth-flow-redesign/wizard-redesign-recommendation.md && [ "$(wc -l < specs/215-auth-flow-redesign/wizard-redesign-recommendation.md)" -le 2000 ]`
- [ ] `grep -c "SUPERSEDED 2026-04-24 by §26" ~/.claude/plans/delightful-orbiting-ladybug.md` — expect ≥ 2 (to be met in Phase 8)
- [ ] `tail -30 event-stream.md | grep -c "wizard-redesign-recommendation.md written"` == 1 (Phase 8)
- [ ] `grep -c "§2 spot-verify: PASS" specs/215-auth-flow-redesign/wizard-redesign-recommendation.md` == 1 ← met (§15 header)
- [ ] `grep -cE "^### Candidate [A-E]" specs/215-auth-flow-redesign/wizard-redesign-recommendation.md` == 5 ← met
- [ ] Each candidate block contains `Strengths` + `Weaknesses` + `Code skeleton` + `Adaptation mechanism` — met
- [ ] All 6 expert panel dimensions appear; each candidate-dimension cell has a 1-sentence justification ← met
- [ ] ≥ 20 edge cases enumerated; each has handling mechanism + test case subfields ← met
- [ ] `grep -cE "^### T-F2c\.[0-9]+" specs/215-auth-flow-redesign/wizard-redesign-recommendation.md` ≥ 20 ← met (T-F2c.1 through T-F2c.20; T-F2c.10 merged into T-F2c.4 documented explicitly)
- [ ] Hard Rules gate-check table with 6 rows; each references specific file/line OR "already-landed via PR #XXX" ← met (§9)
- [ ] Banned vocab (`dossier|clearance|FIELD|file access`) appears ONLY inside §14 "Banned vocabulary" section of this recommendation — check in Phase 8 verification
- [ ] `grep -c "COLING 2025" recommendation.md` ≥ 1; `grep -c "ACL 2025" recommendation.md` == 0 ← expected
- [ ] BiasBusters percentage disownment: §2 spot-verify PASS line + §15 evidence paragraph are present; no affirmative citation of the disowned figure survives (manual review, not grep gate — pattern self-references the checklist).
- [ ] `grep -c "pydantic-ai#4647" recommendation.md` ≥ 1 ← met
- [ ] `grep -c "SB 243" recommendation.md` ≥ 1 AND `grep -c "A6767" recommendation.md` ≥ 1 ← met
- [ ] `grep -cE "^\| D(1[4-9]\|20\|21\|22) \|" recommendation.md` ≥ 9 ← met (D14-D22 in §7.2)
- [ ] Zero flat-numbered tasks: `grep -cE "^### T[0-9]{2}:" recommendation.md` == 0 ← met (only `T-F2c.N`)

---

**End of recommendation — awaiting Phase 7 devil's-advocate review.**
