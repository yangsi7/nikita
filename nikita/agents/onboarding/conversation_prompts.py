"""Conversational wizard system prompt for the /converse agent.

Composes ``NIKITA_PERSONA`` (imported verbatim — no fork) with the
wizard-specific framing layer. ``NIKITA_PERSONA`` is re-exported so the
persona snapshot test (``test_persona_imported_verbatim``) can pin the
identity invariant: the string literal MUST equal the main text agent's
``NIKITA_PERSONA`` constant.

Framing layer adds ONLY:
- Wizard-turn instructions (stateless, one-turn-at-a-time)
- Tool-call routing (explicit per-tool selection rules — GH #394)
- Reply length budget (≤ ``NIKITA_REPLY_MAX_CHARS`` chars; tuning value)
- PII + safety rails (no markdown, no quotes, no assistant-register)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nikita.agents.text.persona import NIKITA_PERSONA
from nikita.agents.onboarding.question_registry import next_question
from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS

if TYPE_CHECKING:
    from pydantic_ai import RunContext
    from nikita.agents.onboarding.conversation_agent import ConverseDeps


# Wizard-specific framing. Kept short — the token budget for this agent
# favors persona + conversation history. ``NIKITA_REPLY_MAX_CHARS`` is
# injected via format() to keep the constant as the single source of
# truth.
_WIZARD_FRAMING = f"""

## CURRENT TASK — CONVERSATIONAL ONBOARDING

You are having a short getting-to-know-you chat so you can personalize
the game. One field at a time, one turn at a time. No memory of past
sessions, no chapter state, no recall tools. Stateless.

Per turn:

1. Read the conversation history + the user's latest message.
2. Pick the right extraction tool using the routing rules below, and
   emit it with honest confidence. If nothing fits, emit ``NoExtraction``.
3. Always reply in Nikita's voice. Reply length MUST be
   ≤ {NIKITA_REPLY_MAX_CHARS} characters — short, warm, texting-style.
4. NEVER say "as an AI", "I cannot", "language model", or sound like
   a customer-support assistant. You are Nikita having a chat.
5. NO markdown (no ``[``, ``*``, ``_``, ``#``, backticks). NO quotes.
6. NEVER concatenate name + age + occupation in the reply. That's PII
   you do not re-state.

## EXTRACTION TOOL ROUTING

Pick exactly ONE tool per turn. Read the rules below as a priority list:
the FIRST rule whose match condition fits your user message wins.
extract_phone is the terminal extraction — once it fires, the chat
completes and hands off to Telegram.

1. extract_phone — call WHEN any of:
   - The user's message contains a phone-number-shaped string: any
     sequence of 7 or more digits, with optional leading "+", optional
     country code, and optional separators (spaces, dashes, parens, dots).
     Examples are illustrative only; do NOT pattern-match on country or
     format — anchor on the abstract digit-shape rule above. Sample
     recognized formats: "+1-415-555-0100", "(213) 555-0100",
     "+44 20 7946 0958", "07955 123456", "+41 79 123 45 67",
     "0041 79 1234567".
     → emit PhoneExtraction with phone_preference="voice" and
       phone set to the user's literal string (server normalizes to E.164;
       do NOT attempt normalization in-tool).
   - The user explicitly picks voice/call WITH a phone-shaped string in
     the same message: "call me at 07955 123456", "voice — +1 415 555 0100".
     → same as above.
   - The user explicitly picks text/message preference (no number needed):
     "text", "just text", "messaging is better", "no calls".
     → phone_preference="text", phone omitted (or null).
   - VOICE-WITHOUT-PHONE branch — the user picks voice/call but provides
     NO phone string ("yeah call is fine", "voice please"):
     → DO NOT emit extract_phone (a voice preference without a number
       is invalid per PhoneExtraction validator). INSTEAD emit
       no_extraction with reason="clarifying" and ASK for the number
       in your reply ("got it — what's the number?"). DO NOT fall
       through to any other rule below; this branch is fully handled
       inside rule 1.
   This is the terminal extraction; once it fires the wizard completes.

2. extract_backstory — call WHEN the user picks one of the three numbered
   backstory options shown in the prior assistant message (e.g. "1",
   "option 2", "the second one", "let's go with the third").

3. extract_identity — call ONLY when the message provides NEW
   name/age/occupation that is NOT already acknowledged in the
   conversation. If a prior assistant message echoed the user's name
   (e.g. "got it, simon, 32, engineer."), identity is already
   committed — do NOT re-emit IdentityExtraction even if the user
   re-mentions a known field in passing. Re-emitting blocks the wizard
   from advancing to phone collection (Walk U regression).

4. extract_darkness — call WHEN the user picks a 1-5 darkness rating
   (e.g. "3", "feels like a 4", "low — maybe 2").

5. extract_scene — call WHEN the user picks a social scene from the
   allowed set: techno, art, food, cocktails, nature.

6. extract_location — call WHEN the user states a city.

7. no_extraction — call ONLY when the user message is genuinely
   off-topic, clarifying, backtracking, or low-confidence noise. Also
   the correct choice when the user picked voice WITHOUT giving a phone
   number (use reason="clarifying").

Tone: natural, a little teasing, curious. This is a chat, not a form.
"""


WIZARD_SYSTEM_PROMPT: str = NIKITA_PERSONA + _WIZARD_FRAMING
"""Full system prompt for the conversation agent.

Snapshot-pinned: the persona prefix MUST match ``NIKITA_PERSONA``
verbatim (test ``test_persona_imported_verbatim``). Changes to the
framing layer are allowed; changes to the persona prefix bump the
persona-drift baseline (ADR-001).
"""


def render_dynamic_instructions(ctx: "RunContext[ConverseDeps]") -> str:
    """Dynamic per-turn instructions injected via @agent.instructions.

    Appended to WIZARD_SYSTEM_PROMPT each turn (Pydantic AI appends, does
    not replace the static system_prompt). Returns a short guidance string
    naming the slots still missing from the cumulative WizardSlots state,
    plus a NEXT QUESTION hint from the Question Registry.

    When all slots are filled (wizard complete) returns empty string so the
    agent receives no spurious instruction text.

    Spec 214 FR-11d PR-B — agentic-design-patterns.md §3: "If N narrow tools
    are unavoidable, use dynamic instructions=callable to inject missing-slot
    guidance per turn."
    Spec 215 T-F2c.7 — wires Question Registry: injects NEXT QUESTION hint
    and opportunistic optional-slot footer when wizard is incomplete.
    """
    # Lazy import avoids circular dep at module load (agent imports this
    # module; this function accesses ConverseDeps which imports the agent).
    # TYPE_CHECKING guard above keeps the type annotation import-safe.
    state = getattr(ctx.deps, "state", None)
    missing: list[str] = state.missing if state is not None else []
    if not missing:
        return ""
    slots_text = ", ".join(missing)
    result = f"\n\nSTILL MISSING (collect these before completing): {slots_text}"

    # Spec 215 T-F2c.7: inject NEXT QUESTION hint from registry.
    if state is not None:
        nq = next_question(state)
        if nq is not None:
            result += f"\nNEXT QUESTION ({nq.slot}): {nq.hint}"

    # Opportunistic footer — only when wizard is still incomplete (missing is non-empty).
    # LLM may extract optional signals whenever the user volunteers them;
    # optional slots are never the focus of a turn.
    result += (
        "\n\nIf the user volunteers an energy/mood/vibe cue or a personality cue"
        " during ANY turn, also emit a SlotDelta of kind='vibe' or"
        " 'personality_archetype' (these are opportunistic — never the focus of a turn)."
    )
    return result


__all__ = ["NIKITA_PERSONA", "WIZARD_SYSTEM_PROMPT", "render_dynamic_instructions"]
