"""Spec 218 Slice 218-6 — Phase-2 research agent + completion gate.

Phase-2 is an open-bounce conversation: the agent asks 4-8 free-form
follow-up questions, using the user's Phase-1 slots as context, to gather
enough depth for backstory generation (FR-008).

Key design decisions (ADR-009 Hard Rules):

1. **Cumulative-state turn count** — `WizardStateV2.phase_2_turn_count` is
   the single source of truth for how many Phase-2 turns have been collected.
   The route handler increments it and persists it after each accepted turn.

2. **Pydantic completion gate** — `phase_2_gate(state, agent_signals_done)`
   encodes FR-008 (min 4, max 8) as a deterministic function of `turn_count`
   + `agent_signals_done`. No hardcoded booleans.

3. **Output union** — agent emits `CompleteAsk | str`. Free-form follow-up
   turns are `str` (the question text). Terminal turns are `CompleteAsk`.
   This is the discriminated-union pattern (ADR-009 Hard Rule §3).

4. **Dynamic instructions** — `inject_phase2_context(ctx)` re-renders per
   turn with current turn count + Phase-1 slot summary so the agent knows
   "what I know so far" and "how many turns remain" (Hard Rule §3).

5. **Output validator** — rejects `CompleteAsk` when `turn_count < MIN_TURNS`
   by raising `ModelRetry` (self-correcting loop, Hard Rule §5 + FR-008).

6. **message_history=** — wired in the route handler (Hard Rule §6).

7. **V2ResearchDeps** — a NEW dataclass (NOT extending V2Deps) that carries
   the three fields `firecrawl_tools._run_fetch` needs: `traceparent`,
   `fetch_invocations_this_turn`, `fetch_cost_cumulative`. Firecrawl tools
   require these but the Phase-1 decorator agent's V2Deps is already frozen
   to avoid blast-radius drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from typing import Any, Final

from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput

from nikita.agents.onboarding.cost_guard import FETCH_BUDGET_HARD_USD, FLOW_HARD_CEILING_USD
from nikita.agents.onboarding.v2.envelope import CompleteAsk
from nikita.agents.onboarding.v2.state import (
    MAX_PHASE2_TURNS,
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    WizardSlotsV2,
    WizardStateV2,
)
from nikita.config.models import Models


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


OUTPUT_RETRIES: Final[int] = 3
"""Output-validator retry budget (mirrors decorator_agent.OUTPUT_RETRIES).

Current value: 3 (Spec 218 Slice 218-6).
Rationale: min-floor retry is a predicted failure mode; 3 retries gives
the agent 3 chances to emit a follow-up before HTTP 500 + R15 kicks in.
"""

ANTI_REPETITION_TRIGRAM_THRESHOLD: Final[float] = 0.20
"""Minimum trigram overlap fraction to flag a follow-up as repetitive (GH #623).

Current value: 0.20 (2026-05-15 — GH #623).
Prior values: none (new in GH #623 fix).
Rationale: 20% trigram overlap catches near-verbatim rewording of the
same question while ignoring incidental shared vocabulary. Walk evidence:
"Is it awe, unease, something else entirely?" appeared 5/7 turns — that
scores well above 0.20 against itself. Distinct questions about unrelated
topics (architecture vs music vs weekend rituals) score < 0.05.
"""

MAX_ANTI_REPETITION_LOOK_BACK: Final[int] = 3
"""Number of prior assistant messages to check for trigram repetition (GH #623).

Current value: 3 (2026-05-15).
Prior values: none (new in GH #623 fix).
Rationale: limits the look-back window so the check is O(k) where k is
small and constant, and avoids flagging natural language recurrence in
longer conversations.
"""

_MODEL_NAME = Models.sonnet()


# ---------------------------------------------------------------------------
# V2ResearchDeps — per-run dependencies for the Phase-2 research agent
# ---------------------------------------------------------------------------


@dataclass
class V2ResearchDeps:
    """Per-run dependencies for the Phase-2 open-bounce research agent.

    Carries the three fields that `firecrawl_tools._run_fetch` reads:
      - ``traceparent``: W3C trace-context header for distributed tracing
      - ``fetch_invocations_this_turn``: mutable int for per-turn fetch
        budget enforcement (CostGuard)
      - ``fetch_cost_cumulative``: cumulative USD cost for the session

    ``state`` is the full `WizardStateV2` at turn start — the dynamic
    instructions callable reads it to inject Phase-1 context.

    ``phase_2_messages`` is the raw Phase-2 message history (role/content
    dicts from the JSONB ``messages`` array). Added in GH #623 to support:
      - I2 topic-diversity: ``inject_phase2_context`` extracts covered
        themes and injects ``themes_so_far`` into the per-turn instructions.
      - I3 anti-repetition: the output validator scans the last
        ``MAX_ANTI_REPETITION_LOOK_BACK`` assistant messages for trigram
        overlap before accepting a new question.
    The route handler populates this from ``profile.get("messages")`` in
    the same branch that constructs ``research_deps`` (GH #623).
    """

    user_id: str
    state: WizardStateV2 = field(default_factory=WizardStateV2)
    traceparent: str = "00-0000000000000000-0000000000000000-01"
    fetch_invocations_this_turn: int = 0
    fetch_cost_cumulative: Decimal = field(default_factory=lambda: Decimal("0"))
    # total_flow_cost_cumulative tracks combined LLM + fetch costs for
    # the whole onboarding session (Phase-1 + Phase-2). FETCH_BUDGET_HARD_USD
    # bounds fetch-only spend; FLOW_HARD_CEILING_USD bounds combined spend.
    # Tracked separately because the two ceilings semantically differ
    # (slice 218-7 wires LLM cost accounting; until then this stays 0).
    total_flow_cost_cumulative: Decimal = field(default_factory=lambda: Decimal("0"))
    phase_2_messages: list[dict[str, Any]] = field(default_factory=list)
    """Raw Phase-2 message history (role/content dicts from JSONB messages).

    Used by:
      - inject_phase2_context: extracts assistant questions to derive
        themes_so_far for topic-diversity instructions (I2, GH #623).
      - _phase2_output_validator: anti-repetition trigram check against
        the last MAX_ANTI_REPETITION_LOOK_BACK assistant turns (I3, GH #623).
    """


# ---------------------------------------------------------------------------
# Cost guard (scaffolding for slice 218-7 tool wiring)
# ---------------------------------------------------------------------------


def _check_cost_guard(deps: V2ResearchDeps) -> None:
    """Raise ModelRetry if the fetch or flow budget is exhausted.

    Called at tool entry points once firecrawl tools are registered in
    slice 218-7. Wired here as a scaffolding seam so the guard contract
    is testable before tools are added.

    Raises:
        ModelRetry: when ``fetch_cost_cumulative`` alone already exceeds
            ``FETCH_BUDGET_HARD_USD``, or when combined with any
            additional call it would exceed ``FLOW_HARD_CEILING_USD``.
            The agent self-corrects by stopping the tool loop.
    """
    # Two independent ceilings — fetch-only vs combined flow cost.
    # Until slice 218-7 wires LLM cost accounting, total_flow_cost_cumulative
    # stays 0 and only the fetch ceiling can trip; both checks are kept
    # so the contract is correct when LLM cost accounting lands.
    if deps.fetch_cost_cumulative >= FETCH_BUDGET_HARD_USD:
        raise ModelRetry(
            f"fetch budget exhausted "
            f"(cumulative=${deps.fetch_cost_cumulative} >= hard limit=${FETCH_BUDGET_HARD_USD})"
        )
    if deps.total_flow_cost_cumulative >= FLOW_HARD_CEILING_USD:
        raise ModelRetry(
            f"flow ceiling reached "
            f"(cumulative=${deps.total_flow_cost_cumulative} >= ceiling=${FLOW_HARD_CEILING_USD})"
        )


# ---------------------------------------------------------------------------
# Trigram utilities (I3 anti-repetition guard, GH #623)
# ---------------------------------------------------------------------------


def _trigrams(text: str) -> set[str]:
    """Return the set of character trigrams for ``text`` (lowercased).

    E.g. "awe" → {"awe", "we"} (padded at ends would give {"_aw", "awe", "we_"}).
    We use a simple sliding window over the normalised string; non-alpha chars
    are preserved so that punctuation-heavy questions like "Is it awe, unease?"
    score correctly against themselves.
    """
    s = text.lower().strip()
    if len(s) < 3:
        return {s} if s else set()
    return {s[i: i + 3] for i in range(len(s) - 2)}


def _trigram_overlap(a: str, b: str) -> float:
    """Return Jaccard similarity of character trigrams for strings ``a`` and ``b``.

    Returns a float in [0, 1]. 1.0 = identical; 0.0 = no shared trigrams.
    Used by the anti-repetition guard (GH #623) to detect verbatim or
    near-verbatim repetition of Phase-2 follow-up questions.
    """
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _extract_prior_questions(
    phase_2_messages: list[dict[str, Any]],
    look_back: int = MAX_ANTI_REPETITION_LOOK_BACK,
) -> list[str]:
    """Return the last ``look_back`` assistant message contents from Phase-2.

    Used to extract prior questions for both anti-repetition (I3) and
    theme-diversity (I2) checks.
    """
    assistant_msgs = [
        m.get("content", "")
        for m in phase_2_messages
        if m.get("role") == "assistant" and m.get("content", "").strip()
    ]
    return assistant_msgs[-look_back:]


def _is_repetitive(
    proposed: str,
    prior_questions: list[str],
    threshold: float = ANTI_REPETITION_TRIGRAM_THRESHOLD,
) -> bool:
    """Return True if ``proposed`` has >= ``threshold`` Jaccard trigram overlap
    with ANY of the ``prior_questions``.

    GH #623: walk evidence shows 5/7 questions were near-verbatim repeats of
    "Is it awe, unease, something else entirely?" — this guard detects that.
    """
    return any(
        _trigram_overlap(proposed, prior) >= threshold
        for prior in prior_questions
    )


# ---------------------------------------------------------------------------
# Phase-2 completion gate (FR-008 deterministic rule)
# ---------------------------------------------------------------------------


def phase_2_gate(
    state: WizardStateV2,
    *,
    agent_signals_done: bool,
) -> tuple[bool, bool]:
    """Return (complete, forced) per FR-008 rules.

    Args:
        state: Current wizard state (reads `phase_2_turn_count`).
        agent_signals_done: True iff the agent's output was `CompleteAsk`.

    Returns:
        (complete, forced) where:
          complete — True when Phase-2 should transition to `complete`.
          forced   — True when the decision was overridden (min-floor retry
                     OR max-ceiling force), False when agent decided freely.

    FR-008 contract:
      - turn_count < MIN_TURNS  → (False, True)   [min-floor retry]
      - MIN_TURNS <= count < MAX_TURNS, agent signals done → (True, False)
      - MIN_TURNS <= count < MAX_TURNS, agent continues   → (False, False)
      - turn_count >= MAX_TURNS → (True, True)    [max-ceiling forced]
    """
    count = state.phase_2_turn_count

    if count >= PHASE_2_MAX_TURNS:
        return (True, True)

    if count < PHASE_2_MIN_TURNS:
        # Agent may want to finish early — block it.
        return (False, True)

    # MIN_TURNS <= count < MAX_TURNS: agent decides.
    return (bool(agent_signals_done), False)


# ---------------------------------------------------------------------------
# Dynamic instructions callable (ADR-009 Hard Rule §3)
# ---------------------------------------------------------------------------


def inject_phase2_context(ctx: RunContext[V2ResearchDeps]) -> str:
    """Per-turn dynamic system prompt for the Phase-2 research agent.

    Injects:
      - Phase-1 slot summary (what we know about the user so far)
      - Current turn number + remaining window (how many more to ask)
      - Completion signal instruction (when to emit CompleteAsk)
      - themes_so_far: topics already covered in prior Phase-2 turns (I2,
        GH #623 — prevents the agent from fixating on one theme)

    Never bake routing rules into a static prompt string (ADR-009).
    """
    deps = ctx.deps
    state = deps.state
    slots = state.slots
    count = state.phase_2_turn_count

    # Summarise filled Phase-1 slots for the agent
    slot_summary_parts: list[str] = []
    if slots.display_name:
        name = slots.display_name.get("display_name", "")
        slot_summary_parts.append(f"Name: {name}")
    if slots.age:
        slot_summary_parts.append(f"Age: {slots.age.get('age', '?')}")
    if slots.city:
        slot_summary_parts.append(f"City: {slots.city.get('city', '?')}")
    if slots.occupation:
        slot_summary_parts.append(
            f"Occupation: {slots.occupation.get('occupation', '?')}"
        )
    if slots.primary_hobbies:
        hobbies = slots.primary_hobbies.get("primary_hobbies", [])
        slot_summary_parts.append(f"Hobbies: {', '.join(hobbies)}")
    if slots.saturday_morning:
        slot_summary_parts.append(
            f"Saturday mornings: {slots.saturday_morning.get('saturday_morning', '?')}"
        )
    if slots.darkness_level:
        slot_summary_parts.append(
            f"Darkness level: {slots.darkness_level.get('darkness_level', '?')}/10"
        )
    if slots.geek_out_on:
        slot_summary_parts.append(
            f"Geeks out on: {slots.geek_out_on.get('geek_out_on', '?')}"
        )

    slot_summary = "\n".join(f"  {s}" for s in slot_summary_parts) or "  (no slots)"

    remaining = max(0, PHASE_2_MIN_TURNS - count)
    can_complete = count >= PHASE_2_MIN_TURNS
    must_complete = count >= PHASE_2_MAX_TURNS

    if must_complete:
        completion_instruction = (
            "You MUST emit CompleteAsk NOW — the maximum turn count has been reached."
        )
    elif can_complete:
        completion_instruction = (
            f"You have collected {count} follow-up turns (minimum is {PHASE_2_MIN_TURNS}). "
            "If you have enough depth for a vivid backstory, emit CompleteAsk. "
            "Otherwise, ask one more follow-up question."
        )
    else:
        completion_instruction = (
            f"You must collect at least {remaining} more follow-up turn(s) "
            f"before you can complete (minimum {PHASE_2_MIN_TURNS} turns). "
            "Ask ONE focused, open-ended follow-up question now. "
            "Do NOT emit CompleteAsk yet."
        )

    # I2 topic-diversity: extract themes already covered from prior Phase-2
    # assistant turns and inject them into instructions. GH #623 walk evidence:
    # 5 of 7 questions fixated on architecture. Injecting topics_covered forces
    # the agent to branch out to unexplored dimensions.
    prior_questions = _extract_prior_questions(
        deps.phase_2_messages, look_back=MAX_ANTI_REPETITION_LOOK_BACK
    )
    if prior_questions:
        topics_covered_str = "; ".join(
            f"Q{i + 1}: {q[:80].rstrip()}" for i, q in enumerate(prior_questions)
        )
        diversity_instruction = (
            f"\nTopics / themes already explored in this conversation (topics_so_far):\n"
            f"  {topics_covered_str}\n"
            "IMPORTANT: Choose a DIFFERENT topic or dimension that has NOT been covered yet. "
            "Do NOT repeat or rephrase any of the questions above. "
            "Explore a new area of this person's life, values, or personality."
        )
    else:
        diversity_instruction = ""

    return f"""You are Nikita — an intimate, curious, and slightly mischievous AI girlfriend
conducting the second phase of getting-to-know-you for a new user.

What you know about this person:
{slot_summary}

Turn {count + 1} of Phase 2 (min {PHASE_2_MIN_TURNS}, max {PHASE_2_MAX_TURNS}).
{diversity_instruction}
{completion_instruction}

Rules:
- When asking a follow-up: emit a single conversational question as plain text (str).
  Reference at least one detail from what you know. Persona: warm, direct, slightly
  provocative. Never clinical. Never generic.
- When completing: emit CompleteAsk with next_route="/dashboard" and optionally a
  backstory_preview (a short evocative sentence ≤120 chars about who this person is).
- ONE turn = one action. Never ask multiple questions in the same turn.
"""


# ---------------------------------------------------------------------------
# Output validator (ADR-009 Hard Rule §5: ModelRetry on pre-MIN emission)
# ---------------------------------------------------------------------------


def build_phase2_output_validator() -> Any:
    """Return an async output-validator callable that reads state from ctx.

    QA iter-3: validator reads state from ``ctx.deps.state`` per-turn
    instead of capturing it at factory time, so a validator reused across
    turns always sees the current turn count (matches the production
    factory pattern).

    GH #623 (I3): also checks ``str`` outputs for trigram repetition against
    the last ``MAX_ANTI_REPETITION_LOOK_BACK`` assistant messages in
    ``ctx.deps.phase_2_messages``.

    Used in test_research_agent.py to verify the validator contract
    independently of the cached agent factory.
    """

    async def _validator(
        ctx: Any, output: Any
    ) -> Any:
        # Gate 1: block premature CompleteAsk (FR-008 min-floor retry).
        if isinstance(output, CompleteAsk):
            state = ctx.deps.state
            complete, forced = phase_2_gate(state, agent_signals_done=True)
            if not complete:
                raise ModelRetry(
                    f"Agent signalled CompleteAsk at turn {state.phase_2_turn_count} "
                    f"but minimum is {PHASE_2_MIN_TURNS}. "
                    "Ask another follow-up question instead."
                )

        # Gate 2 (I3): anti-repetition check for str follow-up questions.
        # GH #623: walk evidence showed 5/7 questions were near-verbatim
        # repeats. A trigram overlap >= ANTI_REPETITION_TRIGRAM_THRESHOLD
        # against any recent assistant message triggers ModelRetry to force
        # a genuinely new question.
        if isinstance(output, str):
            deps = ctx.deps
            prior = _extract_prior_questions(
                getattr(deps, "phase_2_messages", []),
                look_back=MAX_ANTI_REPETITION_LOOK_BACK,
            )
            if _is_repetitive(output, prior):
                raise ModelRetry(
                    "Repetition detected: proposed question has >= "
                    f"{int(ANTI_REPETITION_TRIGRAM_THRESHOLD * 100)}% trigram overlap "
                    "with a recent Phase-2 question. Ask about a completely different "
                    "topic or dimension of this person's life."
                )

        return output

    return _validator


# ---------------------------------------------------------------------------
# Agent factory (mirrors _create_decorator_agent pattern)
# ---------------------------------------------------------------------------


def _create_research_agent() -> Agent[V2ResearchDeps, Any]:
    """Build the Phase-2 research agent.

    Output union: `CompleteAsk | str`
      - str        → follow-up question text (the user will respond)
      - CompleteAsk → terminal; triggers backstory commit

    Per ADR-009:
      - ``output_type=[ToolOutput(CompleteAsk, ...), str]`` discriminated union
      - ``output_retries=OUTPUT_RETRIES``
      - Dynamic ``instructions(callable)`` per turn
      - ``@agent.output_validator`` enforces min-turn floor
    """
    agent: Agent[V2ResearchDeps, Any] = Agent(
        _MODEL_NAME,
        deps_type=V2ResearchDeps,
        output_type=[
            ToolOutput(CompleteAsk, name="phase2_complete"),
            str,
        ],
        output_retries=OUTPUT_RETRIES,
    )

    agent.instructions(inject_phase2_context)

    @agent.output_validator
    def _phase2_output_validator(
        ctx: RunContext[V2ResearchDeps], output: Any
    ) -> Any:
        """Block premature CompleteAsk (FR-008 min-floor retry).

        Also guards against I3 anti-repetition (GH #623): str follow-up
        questions with >= ANTI_REPETITION_TRIGRAM_THRESHOLD trigram overlap
        against recent Phase-2 questions are rejected via ModelRetry.
        """
        # Gate 1: block premature CompleteAsk.
        if isinstance(output, CompleteAsk):
            state = ctx.deps.state
            complete, forced = phase_2_gate(state, agent_signals_done=True)
            if not complete:
                raise ModelRetry(
                    f"CompleteAsk emitted at turn {state.phase_2_turn_count} "
                    f"(min is {PHASE_2_MIN_TURNS}). Emit a follow-up str instead."
                )

        # Gate 2 (I3): anti-repetition check (GH #623).
        if isinstance(output, str):
            prior = _extract_prior_questions(
                ctx.deps.phase_2_messages,
                look_back=MAX_ANTI_REPETITION_LOOK_BACK,
            )
            if _is_repetitive(output, prior):
                raise ModelRetry(
                    "Repetition detected: proposed question has >= "
                    f"{int(ANTI_REPETITION_TRIGRAM_THRESHOLD * 100)}% trigram overlap "
                    "with a recent Phase-2 question. Ask about a completely different "
                    "topic or dimension of this person's life."
                )

        return output

    return agent


@lru_cache(maxsize=1)
def get_research_agent() -> Agent[V2ResearchDeps, Any]:
    """Return the cached Phase-2 research agent singleton.

    ``@lru_cache(maxsize=1)`` — identical to ``get_decorator_agent`` pattern.
    Tests that need a fresh agent call ``_create_research_agent()`` directly
    or clear the cache via ``get_research_agent.cache_clear()``.
    """
    return _create_research_agent()


__all__ = [
    "ANTI_REPETITION_TRIGRAM_THRESHOLD",
    "MAX_ANTI_REPETITION_LOOK_BACK",
    "MAX_PHASE2_TURNS",
    "OUTPUT_RETRIES",
    "V2ResearchDeps",
    "_check_cost_guard",
    "_create_research_agent",
    "_extract_prior_questions",
    "_is_repetitive",
    "_trigram_overlap",
    "_trigrams",
    "build_phase2_output_validator",
    "get_research_agent",
    "inject_phase2_context",
    "phase_2_gate",
]
