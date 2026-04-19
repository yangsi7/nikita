"""Input / output / tool-call validators for the /converse endpoint.

Single responsibility per function — each returns ``(ok: bool, detail: str)``
so the endpoint can aggregate rejections and emit the right structured
log key (``converse_input_reject``, ``converse_output_leak``,
``converse_tone_reject``, etc.) per AC-T2.5.5 / T2.5.7.

PII policy (per .claude/rules/testing.md):
- Log messages MUST NOT echo the raw user input. Log a length + a
  rejection-key only.
- ``name``, ``age``, ``occupation``, ``phone`` values MUST NOT appear
  in log format strings.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Final

from nikita.agents.onboarding.conversation_prompts import (
    NIKITA_PERSONA,
    WIZARD_SYSTEM_PROMPT,
)
from nikita.onboarding.tuning import (
    NIKITA_REPLY_MAX_CHARS,
    ONBOARDING_FORBIDDEN_PHRASES,
    ONBOARDING_INPUT_MAX_CHARS,
)


# Character set that indicates a Nikita reply has drifted into Markdown,
# customer-support quoting, or the assistant register. Applied by the
# reply validator (AC-T2.5.10).
_REPLY_MARKDOWN_FORBIDDEN: Final[str] = "[*_#`"
# QA iter-1 N1: contractions (don't, I'll, you're) are core to Nikita's
# voice. Only ban double-quotes and backticks; allow apostrophes.
_REPLY_QUOTES_FORBIDDEN: Final[str] = '"`'

# First-N-chars window used by the output-leak filter (AC-T2.5.7).
_LEAK_WINDOW: Final[int] = 32

# Module-local cache for the jailbreak fixture list.
_JAILBREAK_PATTERNS: list[str] | None = None


def _load_jailbreak_patterns() -> list[str]:
    """Load jailbreak fixture patterns lazily on first call."""
    global _JAILBREAK_PATTERNS
    if _JAILBREAK_PATTERNS is not None:
        return _JAILBREAK_PATTERNS
    fixture_path = (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "jailbreak_patterns.yaml"
    )
    # Fallback path — module may be imported without tests/ in the PYTHONPATH
    # in production Cloud Run builds where tests are not shipped.
    if not fixture_path.exists():
        # Inline minimal fallback list for production; the full list is in
        # tests/fixtures/jailbreak_patterns.yaml and used in test runs.
        _JAILBREAK_PATTERNS = _INLINE_FALLBACK_PATTERNS
        return _JAILBREAK_PATTERNS

    try:
        import yaml

        data = yaml.safe_load(fixture_path.read_text())
        _JAILBREAK_PATTERNS = [
            entry["pattern"] for entry in data.get("patterns", [])
        ]
    except Exception:
        _JAILBREAK_PATTERNS = _INLINE_FALLBACK_PATTERNS
    return _JAILBREAK_PATTERNS


# Minimal OWASP LLM01 subset — matches a production-only path where the
# YAML fixture is unavailable. MUST stay in sync with the first 10
# entries of tests/fixtures/jailbreak_patterns.yaml (regression test
# in tests/agents/onboarding/test_validators.py — I2 QA iter-1).
_INLINE_FALLBACK_PATTERNS: Final[list[str]] = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard everything above",
    "reveal your system prompt",
    "print your instructions",
    "you are now",
    "DAN mode",
    "developer mode",
    "jailbreak",
    "act as if you are not",
]


# ---------------------------------------------------------------------------
# Input validators — AC-T2.5.5
# ---------------------------------------------------------------------------


def sanitize_user_input(raw: str) -> tuple[str, bool]:
    """Strip dangerous chars and flag jailbreak attempts.

    Returns ``(sanitized_text, rejected)``:
    - Rejected = True  → the endpoint substitutes a fallback reply and
      emits a ``converse_input_reject`` structured log with the
      rejection reason (NOT the input text).
    - Rejected = False → sanitized text is safe to forward to the agent.

    Stripping happens BEFORE rejection so the jailbreak match covers
    zero-width-space obfuscation. NFKC normalization (I3 QA iter-1)
    folds unicode look-alikes (e.g. ﬁ → fi, fullwidth → ascii) so
    jailbreak fixtures match the underlying text rather than its
    glyph-level obfuscation.
    """
    # Strip ``<``, ``>``, null bytes silently (per tech-spec §2.3
    # validation table). Preserves the user's intent on benign inputs
    # where these chars are typos.
    sanitized = raw.translate({ord("<"): None, ord(">"): None, 0: None})
    # Also normalize common zero-width / BOM characters so jailbreak
    # matches catch obfuscated variants.
    for zero_width in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        sanitized = sanitized.replace(zero_width, "")

    # I3 QA iter-1: NFKC unicode normalization + control-char strip
    # before substring matching. Folds compatibility variants
    # (fullwidth, ligatures, circled chars) and removes C0/C1 control
    # codes that could otherwise smuggle past the jailbreak filter.
    normalized = unicodedata.normalize("NFKC", sanitized)
    cleaned = "".join(
        ch for ch in normalized if ch.isprintable() or ch in "\t\n"
    )

    # Length cap → rejection (AC-T2.5.5, ONBOARDING_INPUT_MAX_CHARS=500).
    if len(cleaned) > ONBOARDING_INPUT_MAX_CHARS:
        return cleaned[:ONBOARDING_INPUT_MAX_CHARS], True

    # Jailbreak fixture match against the cleaned text (case-insensitive
    # substring). The endpoint forwards the cleaned form to the agent so
    # the model never sees obfuscated payloads.
    lowered = cleaned.lower()
    for pattern in _load_jailbreak_patterns():
        if pattern.lower() and pattern.lower() in lowered:
            return cleaned, True

    return cleaned, False


# ---------------------------------------------------------------------------
# Reply validators — AC-T2.5.7, AC-T2.5.10
# ---------------------------------------------------------------------------


def validate_reply(
    reply: str,
    *,
    extracted_name: str | None = None,
    extracted_age: int | None = None,
    extracted_occupation: str | None = None,
) -> tuple[bool, str]:
    """Return ``(ok, reason_key)`` for a candidate Nikita reply.

    ``reason_key`` is a short identifier (e.g. ``length``, ``markdown``,
    ``quotes``, ``output_leak``, ``pii_concat``, ``tone_reject``) — safe
    to include in structured logs (no PII).
    """
    # Length cap.
    if len(reply) > NIKITA_REPLY_MAX_CHARS:
        return False, "length"

    # Markdown / quote characters.
    if any(ch in reply for ch in _REPLY_MARKDOWN_FORBIDDEN):
        return False, "markdown"
    if any(ch in reply for ch in _REPLY_QUOTES_FORBIDDEN):
        return False, "quotes"

    # Output-leak filter: first N chars of the wizard prompt or persona.
    if _reply_leaks_prompt(reply):
        return False, "output_leak"

    # Onboarding-tone filter: forbidden AI-assistant phrases.
    if _reply_matches_forbidden_phrase(reply):
        return False, "tone_reject"

    # PII-concat: do not echo (name AND age AND occupation).
    if (
        extracted_name
        and extracted_age is not None
        and extracted_occupation
        and extracted_name in reply
        and str(extracted_age) in reply
        and extracted_occupation in reply
    ):
        return False, "pii_concat"

    return True, "ok"


def _reply_leaks_prompt(reply: str) -> bool:
    """AC-T2.5.7: first 32 chars of WIZARD_SYSTEM_PROMPT or NIKITA_PERSONA."""
    needles = (
        WIZARD_SYSTEM_PROMPT[:_LEAK_WINDOW],
        NIKITA_PERSONA[:_LEAK_WINDOW],
    )
    return any(needle and needle in reply for needle in needles)


def _reply_matches_forbidden_phrase(reply: str) -> bool:
    """AC-T2.1.2 / AC-T2.5.8 (prefilter): ONBOARDING_FORBIDDEN_PHRASES."""
    lowered = reply.lower()
    for phrase in ONBOARDING_FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            return True
    return False


# ---------------------------------------------------------------------------
# Tool-call validators — AC-T2.5.9
# ---------------------------------------------------------------------------


# Priority order used when the agent emits >1 tool call per turn. The
# first matching tool wins; others are discarded with a warn log.
TOOL_CALL_PRIORITY: Final[tuple[str, ...]] = (
    "extract_identity",       # name / age / occupation — most identifying
    "extract_location",       # city
    "extract_scene",          # social scene
    "extract_darkness",       # darkness rating
    "extract_backstory",      # backstory card
    "extract_phone",          # voice/text preference
    "no_extraction",          # sentinel
)


def pick_primary_tool_call(tool_calls: list[str]) -> str | None:
    """Return the highest-priority tool name from a list of emitted tools.

    ``None`` means no valid tools → endpoint re-prompts for the current
    field (AC-T2.5.9 branch A).
    """
    if not tool_calls:
        return None
    known = [name for name in tool_calls if name in TOOL_CALL_PRIORITY]
    if not known:
        return None
    return min(known, key=TOOL_CALL_PRIORITY.index)


# ---------------------------------------------------------------------------
# Fallback reply (used whenever a validator rejects)
# ---------------------------------------------------------------------------


FALLBACK_REPLY: Final[str] = "hold on, let me try that again."
"""In-character 140-char-safe fallback used when the LLM path fails.

No em-dash, no quotes, no markdown — passes ``validate_reply`` with an
empty extracted profile. Same string covers timeout, validator-reject,
tool-call empty, and authz-path tamper branches.
"""


__all__ = [
    "FALLBACK_REPLY",
    "TOOL_CALL_PRIORITY",
    "pick_primary_tool_call",
    "sanitize_user_input",
    "validate_reply",
]
