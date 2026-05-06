"""Deterministic bare-token fallback for high-stakes wizard slots.

Closes GH #484 (Walk A1 C1): the conversation agent silently no-ops
(``TurnOutput.delta = None``) when the user types a bare-token first answer
like ``"Walker"`` — sentence forms (``"my name is Walker"``) work, but
single-word inputs are interpreted as clarifications. The wizard's first
slot is ``display_name``; without it filled, every new user is stuck at
screen 1 with progress=0 forever.

Per ``.claude/rules/agentic-design-patterns.md`` Hard Rule §5
(Validation Layering — three layers required, deterministic post-processing
as defense in depth against LLM tool-selection bias), this module provides
the third layer: after ``agent.run`` returns, if no extraction landed AND
the next-asked slot is one we can shape-validate (currently
``display_name``), force-extract from the user input.

The agent prompt was also tightened (``conversation_prompts.py``
``inject_per_turn_context`` now carries an explicit BARE-TOKEN RULE) so
the LLM does the right thing on the happy path. This fallback only fires
when prompt-side guidance failed.

Scope: intentionally narrow. ``display_name`` is the highest-blast-radius
slot (turn 0 / turn 1 / blocks the entire wizard). Future slots can be
added here as walks surface analogous failures, but each addition needs:
  - a shape predicate that's strict enough not to mis-fire on valid agent
    clarification turns ("?" inputs, etc.)
  - a regression test asserting both happy + failure cases
  - precedent in a walk report

Anti-pattern this is NOT: free-form text fallback. Bare-token-only,
specific slots only, narrow predicates only. The agent remains the
primary extractor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nikita.agents.onboarding.state import SlotDelta, WizardSlots


# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

DISPLAY_NAME_MAX_CHARS: int = 30
"""Max characters for a bare-token display_name fallback.

Rationale: real human names are short. 30 covers double-barreled names
(``Mary Jane``) plus generous slack. Beyond 30 the input is almost
certainly a sentence, and the agent should have extracted; falling back
on a 30+ char string is more dangerous than letting the agent re-ask.
"""

DISPLAY_NAME_MAX_WORDS: int = 3
"""Max whitespace-separated words for bare-token display_name fallback.

Three covers ``Mary Jane Watson`` shape; four+ words is almost certainly
a sentence/question. Pair with ``DISPLAY_NAME_MAX_CHARS`` — both must
hold for the heuristic to fire.
"""


# ---------------------------------------------------------------------------
# Shape predicates
# ---------------------------------------------------------------------------


def _looks_like_question(text: str) -> bool:
    """True if ``text`` looks like a clarification rather than a value.

    Conservative: any ``?`` or leading WH-word ("what", "why", "how", "when",
    "where") trips the predicate. False positives here cost a re-ask (cheap);
    false negatives cost a wrongly-stored slot value (expensive — user has
    to recover via UI).
    """
    stripped = text.strip()
    if not stripped:
        return True
    if "?" in stripped:
        return True
    first_word = stripped.split(maxsplit=1)[0].lower().rstrip(".,!:")
    if first_word in {"what", "why", "how", "when", "where", "who", "which"}:
        return True
    # Sentence-shaped "I'm Walker", "my name is Walker", "you can call me Bob"
    # — pronoun / possessive / "be" leads. Kept narrow on purpose: anything
    # adjacent to a real name (e.g. "Mary") will not match.
    if first_word in {
        "i", "i'm", "im", "you", "we", "my", "me", "mine", "your",
        "is", "are", "was", "were", "the", "a", "an", "actually",
        "no", "yes", "sure", "ok", "okay",
    }:
        return True
    return False


def _is_bare_token(text: str, *, max_chars: int, max_words: int) -> bool:
    """True if ``text`` is short enough to interpret as a single value."""
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > max_chars:
        return False
    word_count = len(stripped.split())
    if word_count == 0 or word_count > max_words:
        return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def try_bare_token_fill(
    state: "WizardSlots",
    user_input: str,
    *,
    next_slot_kind: str | None,
) -> "SlotDelta | None":
    """Return a SlotDelta if ``user_input`` can be force-extracted, else None.

    Args:
        state: cumulative wizard state AFTER the agent's
            ``apply_turn_delta`` call. We only fire if the slot is still
            unfilled.
        user_input: the raw user message for this turn (NOT redacted; the
            fallback needs the literal value).
        next_slot_kind: the slot the agent was supposed to extract this
            turn. ``None`` means we do not have a routing hint and the
            fallback must be conservative (skip).

    Returns:
        ``SlotDelta`` to apply, or ``None`` if no fallback applies.
        Callers should ``state.apply(delta)`` and reassign.

    Currently handles:
      - ``display_name`` — bare 1-3 word, ≤30 char, no question shape.

    Future slot extensions (per .claude/rules/agentic-design-patterns.md
    Hard Rule §5) can be added with their own shape predicates + tests.
    """
    if next_slot_kind != "display_name":
        return None

    # Don't overwrite a filled slot. The agent may have extracted in a
    # previous turn that we're seeing the latency-tail of — never clobber.
    if getattr(state, "display_name", None) is not None:
        return None

    if _looks_like_question(user_input):
        return None

    if not _is_bare_token(
        user_input,
        max_chars=DISPLAY_NAME_MAX_CHARS,
        max_words=DISPLAY_NAME_MAX_WORDS,
    ):
        return None

    # Local import to avoid circular: state.py imports nothing from this
    # module, but this module's public function returns a state.SlotDelta.
    from nikita.agents.onboarding.state import SlotDelta  # noqa: PLC0415

    canonical = user_input.strip().rstrip(".,!:")
    return SlotDelta(
        kind="display_name",
        data={"display_name": canonical},
    )


__all__ = [
    "DISPLAY_NAME_MAX_CHARS",
    "DISPLAY_NAME_MAX_WORDS",
    "try_bare_token_fill",
]
