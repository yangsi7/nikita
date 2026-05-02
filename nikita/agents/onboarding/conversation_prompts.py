"""Wizard prompt templates + dynamic-instruction callable (Spec 216-B1+B2).

This module owns the four meta-prompt templates (M1-M4) and the per-turn
``inject_per_turn_context`` callable. The static ``_WIZARD_FRAMING`` block,
``WIZARD_SYSTEM_PROMPT`` constant, and ``render_dynamic_instructions``
function from the prior schema have been REMOVED — routing rules now live
exclusively in the dynamic callable per Hard Rule §6.

Templates carry ``[FIXED]`` and ``[DYNAMIC]`` markers. The ``[FIXED]``
block is intended to be cached via Anthropic prompt-cache breakpoint
(B1.20). The ``[DYNAMIC]`` block carries per-turn substitutions and must
NOT be cached.

The cluster taxonomies for the four prose-slot kinds (primary_hobbies,
saturday_morning, geek_out_on, together_we_could) are exposed via the
``CLUSTER_TAXONOMIES`` constant; the M2 classifier templates reference
the slot's allowed clusters dynamically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from nikita.agents.text.persona import NIKITA_PERSONA
from nikita.agents.onboarding.question_registry import next_question
from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS

if TYPE_CHECKING:
    from pydantic_ai import RunContext

    from nikita.agents.onboarding.conversation_agent import ConverseDeps


# ---------------------------------------------------------------------------
# Cluster taxonomies (B1.7) — single source of truth for M2 classifier
# ---------------------------------------------------------------------------

CLUSTER_TAXONOMIES: Final[dict[str, tuple[str, ...]]] = {
    "primary_hobbies": (
        "aesthete",
        "kinetic",
        "digital_nomad",
        "homemaker",
        "nightlife",
        "outdoorsy",
        "ambiguous",
    ),
    "saturday_morning": (
        "movement",
        "quiet",
        "social",
        "chaos",
        "ambiguous",
    ),
    "geek_out_on": (
        "hands_on",
        "system",
        "culture",
        "human",
        "ambiguous",
    ),
    "together_we_could": (
        "risk",
        "refuge",
        "craft",
        "discovery",
        "ritual",
        "ambiguous",
    ),
}


# ---------------------------------------------------------------------------
# M1 — GenerateFollowUpFromAnswer
# ---------------------------------------------------------------------------

M1_GENERATE_FOLLOW_UP: Final[str] = """[FIXED]
Role: Generate ONE non-leading follow-up question for an AI-companion onboarding chat.
Voice: dark luxe, slightly menacing, <=140 chars, no emoji, no markdown.
Output schema: DynamicFollowUp(question, why_we_ask, references_state)
Rules:
- Reference at least ONE detail from the user's last answer (paraphrase, never echo verbatim).
- NEVER use "don't you" / "wouldn't you" / leading phrases.
- Use "What" or "How" — never "Why".
- The question MUST advance signal on the cluster, not the same axis the user already covered.

[DYNAMIC]
Last topic: {slot_kind}
Last answer (redacted): {slot_value_redacted}
Detected cluster: {cluster} (confidence {confidence})
Cumulative state summary: {state_summary}
Forbidden topics this turn: {forbidden_list}
"""


# ---------------------------------------------------------------------------
# M2 — ClassifyAnswerCluster
# ---------------------------------------------------------------------------

M2_CLASSIFY_ANSWER_CLUSTER: Final[str] = """[FIXED]
Role: Classify a user's prose answer into one of {slot_kind}'s 4-7 cluster taxonomy.
Output: AnswerCluster(cluster, confidence)
If you cannot classify with confidence >=0.6, return cluster="ambiguous", confidence=<actual>.

[DYNAMIC]
Slot: {slot_kind}
Allowed clusters: {cluster_enum}
User answer (redacted): {user_answer_redacted}
"""


# ---------------------------------------------------------------------------
# M3 — RefineSummary
# ---------------------------------------------------------------------------

M3_REFINE_SUMMARY: Final[str] = """[FIXED]
Role: Compress conversation_jsonb history into <=2 sentences for system-prompt injection.
Voice: third-person, factual, no editorializing.
Output: PromptSummary(text)

[DYNAMIC]
Conversation turns: {turn_count}
Slots filled: {slots_summary}
Latest 3 user messages: {recent_messages}
"""


# ---------------------------------------------------------------------------
# M4 — DetectSaturation
# ---------------------------------------------------------------------------

M4_DETECT_SATURATION: Final[str] = """[FIXED]
Role: Decide continue-or-stop on dynamic follow-up depth for the current topic.
Output: SaturationSignal(decision, reason)
HARD OVERRIDES:
- If turn_count_for_topic >= 2 -> "move_on"
- If cluster == "ambiguous" AND turn_count_for_topic < 3 -> "probe"
- If any Big5 dimension confidence >=0.7 for an axis the topic could probe -> "move_on"

[DYNAMIC]
Topic: {slot_kind}
Turn count for topic: {turn_count}
Cluster: {cluster}
Big5 confidence vector: {big5_confidence}
Cost budget remaining: {cost_budget}
"""


# ---------------------------------------------------------------------------
# inject_per_turn_context — Hard Rule §6 dynamic instructions callable
# ---------------------------------------------------------------------------


_BASE_INSTRUCTIONS: Final[str] = f"""You are Nikita running an in-character onboarding chat.

Per turn:
1. Read the conversation history + the user's latest message.
2. Decide the next slot to extract (or no_extraction if off-topic / clarifying).
3. Always reply in Nikita's voice. Reply length MUST be <={NIKITA_REPLY_MAX_CHARS} characters.
4. NEVER use customer-support phrases ("as an AI", "language model", "I cannot").
5. NO markdown. NO double quotes. NO backticks. Apostrophes are fine.
6. NEVER concatenate name + age + occupation in the reply (PII echo).

Output:
- TurnOutput(delta, reply, next_slot_kind) on the happy path.
- TurnFailure(explanation, last_slot_kind) when the user's input cannot be processed
  (under-18, abusive, contradictions). Stay in character; never throw.
"""


def inject_per_turn_context(ctx: "RunContext[ConverseDeps]") -> str:
    """Render per-turn instruction block.

    Reads from ``ctx.deps``:
      - state.missing — list of unfilled slot names
      - next_slot_kind / next_slot_hint — registry-driven routing
      - last_slot_kind / last_value — for mirror-echo guidance
      - state_summary — one-line context for long histories

    Returns a string that Pydantic AI appends to the system message.
    The static ``_BASE_INSTRUCTIONS`` block is included so it lives in
    the cacheable prefix; the per-turn dynamic tail follows.
    """
    deps = ctx.deps
    state = getattr(deps, "state", None)
    parts: list[str] = [_BASE_INSTRUCTIONS]

    # State summary
    summary = getattr(deps, "state_summary", "") or ""
    if summary:
        parts.append(f"\nState summary: {summary}")

    # Last user value (for mirror-echo guidance)
    last_kind = getattr(deps, "last_slot_kind", None)
    last_value = getattr(deps, "last_value", None)
    if last_kind is not None and last_value:
        # Render last_kind value (it could be a SlotKind enum or string)
        last_kind_str = (
            last_kind.value if hasattr(last_kind, "value") else str(last_kind)
        )
        parts.append(
            f"\nLast turn: user filled '{last_kind_str}' (redacted). "
            "Do NOT mirror-echo their literal value back. Acknowledge briefly, "
            "then move on."
        )

    # Missing slots
    if state is not None:
        missing = list(getattr(state, "missing", []))
        if missing:
            parts.append(
                f"\nSTILL MISSING ({len(missing)} slots): " + ", ".join(missing)
            )

            # NEXT slot — use explicit hint if provided, else consult registry.
            next_kind = getattr(deps, "next_slot_kind", None)
            next_hint = getattr(deps, "next_slot_hint", None)
            if next_kind is not None:
                next_kind_str = (
                    next_kind.value if hasattr(next_kind, "value") else str(next_kind)
                )
                hint_str = next_hint or ""
                parts.append(
                    f"\nNEXT SLOT to ask: {next_kind_str}"
                    + (f" — hint: {hint_str}" if hint_str else "")
                )
            else:
                nq = next_question(state)
                if nq is not None:
                    parts.append(
                        f"\nNEXT SLOT to ask: {nq.slot} — hint: {nq.hint}"
                    )
        else:
            parts.append(
                "\nAll slots filled. The wizard is complete; reply with a "
                "warm acknowledgment and no further extraction."
            )

    return "".join(parts)


__all__ = [
    "CLUSTER_TAXONOMIES",
    "M1_GENERATE_FOLLOW_UP",
    "M2_CLASSIFY_ANSWER_CLUSTER",
    "M3_REFINE_SUMMARY",
    "M4_DETECT_SATURATION",
    "NIKITA_PERSONA",
    "inject_per_turn_context",
]
