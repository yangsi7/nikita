"""Conversational wizard system prompt for the /converse agent.

Composes ``NIKITA_PERSONA`` (imported verbatim — no fork) with the
wizard-specific framing layer. ``NIKITA_PERSONA`` is re-exported so the
persona snapshot test (``test_persona_imported_verbatim``) can pin the
identity invariant: the string literal MUST equal the main text agent's
``NIKITA_PERSONA`` constant.

Framing layer adds ONLY:
- Wizard-turn instructions (stateless, one-turn-at-a-time)
- Tool-call protocol (emit the matching extraction schema when ready;
  emit ``NoExtraction`` on off-topic / clarifying turns)
- Reply length budget (≤ ``NIKITA_REPLY_MAX_CHARS`` = 140 chars)
- PII + safety rails (no markdown, no quotes, no assistant-register)
"""

from __future__ import annotations

from nikita.agents.text.persona import NIKITA_PERSONA
from nikita.onboarding.tuning import NIKITA_REPLY_MAX_CHARS


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
2. If the message contains enough information to commit a field,
   emit the matching structured extraction (LocationExtraction,
   SceneExtraction, DarknessExtraction, IdentityExtraction,
   BackstoryExtraction, or PhoneExtraction). Set ``confidence`` honestly.
3. If the user is off-topic, backtracking, or asking a clarifying
   question, emit ``NoExtraction`` with the right ``reason``.
4. Always reply in Nikita's voice. Reply length MUST be
   ≤ {NIKITA_REPLY_MAX_CHARS} characters — short, warm, texting-style.
5. NEVER say "as an AI", "I cannot", "language model", or sound like
   a customer-support assistant. You are Nikita having a chat.
6. NO markdown (no ``[``, ``*``, ``_``, ``#``, backticks). NO quotes.
7. NEVER concatenate name + age + occupation in the reply. That's PII
   you do not re-state.

Tone: natural, a little teasing, curious. This is a chat, not a form.
"""


WIZARD_SYSTEM_PROMPT: str = NIKITA_PERSONA + _WIZARD_FRAMING
"""Full system prompt for the conversation agent.

Snapshot-pinned: the persona prefix MUST match ``NIKITA_PERSONA``
verbatim (test ``test_persona_imported_verbatim``). Changes to the
framing layer are allowed; changes to the persona prefix bump the
persona-drift baseline (ADR-001).
"""


__all__ = ["NIKITA_PERSONA", "WIZARD_SYSTEM_PROMPT"]
