"""Route-handler wiring helpers for the 13-slot wizard (Spec 216-DE-wire).

Glue layer between the /answer route handler (``portal_onboarding.py``)
and the agent-flow building blocks shipped by 216-D-code (Big5 judge,
12-archetype taxonomy, cohort chips) + 216-E (firecrawl tools, cost
guard, ``WebSearchTool``).

This module is deliberately minimal: it owns only **pure predicates**
(when to run Big5, when to populate cohort chips, when to populate
archetype cards) plus **factory builders** that construct Anthropic-backed
``JudgeCallable`` / ``ArchetypePicker`` / ``BackstoryGenerator`` callables
for production use.

NR-05: nothing in this module appears in any HTTP response. Big5 results
flow through ``users.big5_vector`` JSONB; archetype/backstory results
appear only via the curated ``ArchetypeCard`` / ``BackstoryCard`` shapes
which contain no personality-axis terminology.

Rule cross-references:
  - .claude/rules/agentic-design-patterns.md Hard Rule §1 (cumulative state)
  - master spec NR-05
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from nikita.agents.onboarding.archetypes import (
    ARCHETYPES,
    ARCHETYPE_PROSE_MAX_LEN,
    ARCHETYPE_SEED_LEN,
    ArchetypeCard,
    ArchetypePicker,
    BackstoryCard,
    BackstoryGenerator,
    NUM_ARCHETYPE_CANDIDATES,
)
from nikita.agents.onboarding.big5_judge import DIMS, Big5Vector, JudgeCallable
from nikita.agents.onboarding.question_registry import SlotKind


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Slot kinds whose user-prose answer should be scored by the Big5 judge.
# Cross-referenced from spec D1.5 + master spec NR-05. Single source of
# truth: any new prose-shaped slot must be added here AND in the test
# fixture in tests/agents/onboarding/test_wiring_helpers.py.
PROSE_SLOT_KINDS_FOR_BIG5: frozenset[SlotKind] = frozenset(
    {
        SlotKind.saturday_morning,
        SlotKind.geek_out_on,
        SlotKind.together_we_could,
        SlotKind.same_weird_if,
        SlotKind.primary_hobbies,
    }
)


# ---------------------------------------------------------------------------
# Predicates — pure, side-effect free, cheap to call per turn
# ---------------------------------------------------------------------------


def should_run_big5_judge(slot_kind: SlotKind | None) -> bool:
    """True iff the just-extracted slot is one of the prose-shaped slots.

    The Big5 judge runs after a successful prose extraction; non-prose slots
    (display_name, age, city, ...) carry no personality signal.
    """
    if slot_kind is None:
        return False
    return slot_kind in PROSE_SLOT_KINDS_FOR_BIG5


def should_populate_cohort_chips(next_slot_kind: SlotKind | None) -> bool:
    """True iff the next turn will ask about primary_hobbies.

    Per spec D1.7: cohort chips are surfaced ONLY on the hobbies turn.
    """
    return next_slot_kind == SlotKind.primary_hobbies


def should_populate_archetype_cards(next_slot_kind: SlotKind | None) -> bool:
    """True iff the next turn will ask the user to pick a backstory.

    Per spec D1.6: archetype cards are surfaced ONLY on backstory_pick.
    """
    return next_slot_kind == SlotKind.backstory_pick


# ---------------------------------------------------------------------------
# Seed helpers — sha256-hex stable identifiers for cohort grouping
# ---------------------------------------------------------------------------


def _archetype_seed(label: str, city: str | None, occupation: str | None) -> str:
    """Build a sha256-hex seed for an ArchetypeCard.

    The seed is a stable opaque identifier joining (label, city, occupation).
    It contains no raw PII because it is hashed; the FE uses it purely to
    group an ArchetypeCard with its matching BackstoryCard.
    """
    payload = "|".join(
        [
            label.strip().lower(),
            (city or "").strip().lower(),
            (occupation or "").strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Default-fallback builders — used when the Anthropic-backed picker errors
# ---------------------------------------------------------------------------


def default_archetype_cards(
    *,
    city: str | None,
    occupation: str | None,
) -> list[ArchetypeCard]:
    """Deterministic 3-card fallback when the LLM picker fails.

    Picks the first 3 labels from the LOCKED 12-list with a generic prose
    line so the wizard surface stays usable. Logged at WARNING by the
    caller; never raises.
    """
    fallback_prose = (
        "a quiet shape that fits the way you move through the day."
    )
    if len(fallback_prose) > ARCHETYPE_PROSE_MAX_LEN:  # pragma: no cover
        fallback_prose = fallback_prose[:ARCHETYPE_PROSE_MAX_LEN]
    return [
        ArchetypeCard(
            label=ARCHETYPES[i],  # type: ignore[arg-type]
            prose=fallback_prose,
            archetype_seed=_archetype_seed(ARCHETYPES[i], city, occupation),
        )
        for i in range(NUM_ARCHETYPE_CANDIDATES)
    ]


# ---------------------------------------------------------------------------
# Anthropic-backed factory builders
# ---------------------------------------------------------------------------

# These constructors return async callables matching the
# ``JudgeCallable`` / ``ArchetypePicker`` / ``BackstoryGenerator`` Protocol
# aliases. They wrap an ``AsyncAnthropic`` client; call sites pass the
# returned callable into ``update_big5_vector`` / ``pick_three_archetypes``
# / ``generate_three_personas`` respectively.
#
# All three are best-effort: on any client / parse error they raise so the
# upstream entrypoint (which already catches Exception) falls back. NR-05
# enforced by never returning the raw vector to the caller — only the
# upstream merger touches the inferred state.

def _haiku_model() -> str:
    """Resolve the Haiku model id at call time (not import time).

    Defers to ``nikita.config.models.Models.haiku()`` which reads from
    settings — single source of truth + matches the approved-models gate
    in ``tests/regression/test_model_strings.py``.
    """
    from nikita.config.models import Models  # noqa: PLC0415

    return Models.haiku()


def _opus_model() -> str:
    """Resolve the Opus model id at call time (mirrors ``_haiku_model``)."""
    from nikita.config.models import Models  # noqa: PLC0415

    return Models.opus()

_BIG5_SYSTEM = (
    "You score short user prose along five hidden personality dimensions "
    "labelled O, C, E, A, N (each in [0,1]). You also report per-dimension "
    "confidence in [0,1]. Reply with JSON ONLY: "
    '{"O":0.x,"C":0.x,"E":0.x,"A":0.x,"N":0.x,"confidence":'
    '{"O":0.x,"C":0.x,"E":0.x,"A":0.x,"N":0.x}}'
)

_PICKER_SYSTEM = (
    "You pick exactly 3 archetypes from the LOCKED list of 12: "
    + ", ".join(ARCHETYPES)
    + ". Return JSON ONLY with the shape "
    '[{"label":"the runner","prose":"<=150 chars","archetype_seed":"<sha256-hex>"}, ...]. '
    "Each prose must be <=150 chars, dark luxe, no emoji, no markdown."
)

_GENERATOR_SYSTEM = (
    "You write exactly 3 short backstory sketches (<=150 chars each) for "
    "the chosen archetype. Return JSON ONLY: "
    '[{"prose":"<=150 chars","archetype_seed":"<seed>"}, ...]. '
    "No emoji, no markdown."
)


def _make_anthropic_client():  # noqa: ANN202 — return type is anthropic.AsyncAnthropic
    """Return an ``AsyncAnthropic`` client or raise if the key is unset.

    Imports inline so modules that do not need the Anthropic SDK don't
    pay the import cost.
    """
    from anthropic import AsyncAnthropic  # noqa: PLC0415

    from nikita.config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()
    api_key = getattr(settings, "anthropic_api_key", None)
    if not api_key:
        raise RuntimeError("anthropic_api_key not configured")
    return AsyncAnthropic(api_key=api_key)


async def _anthropic_text_call(
    *,
    client,  # noqa: ANN001 — anthropic.AsyncAnthropic
    model: str,
    system: str,
    user: str,
    max_tokens: int,
) -> str:
    """Single-turn Anthropic Messages call returning the raw text content."""
    msg = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Anthropic Messages API returns content blocks; concatenate text blocks.
    chunks: list[str] = []
    for block in getattr(msg, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            chunks.append(text)
    return "".join(chunks).strip()


def make_anthropic_judge() -> JudgeCallable:
    """Construct a Haiku-backed Big5 judge callable.

    Signature matches ``JudgeCallable``: ``(prose, prior_vector) -> Big5Vector``.
    Raises on any error — the upstream ``update_big5_vector`` catches and
    falls back to the prior vector (NR-05 hidden surface).
    """

    async def _judge(prose: str, prior_vector: Big5Vector) -> dict[str, Any]:
        client = _make_anthropic_client()
        prior_summary = json.dumps(
            {d: prior_vector.get(d, 0.0) for d in DIMS}
        )
        user = (
            f"Prior vector (server-side): {prior_summary}\n"
            f"User prose to score:\n{prose[:2000]}"
        )
        text = await _anthropic_text_call(
            client=client,
            model=_haiku_model(),
            system=_BIG5_SYSTEM,
            user=user,
            max_tokens=400,
        )
        return json.loads(text)

    return _judge


def make_anthropic_picker() -> ArchetypePicker:
    """Construct an Opus-backed archetype picker callable.

    Returns a callable matching ``ArchetypePicker``: takes kwargs
    ``(big5, city, occupation, hobbies, darkness)`` and returns a list of 3
    ``ArchetypeCard`` instances. Raises on any error — the route layer
    falls back to ``default_archetype_cards``.
    """

    async def _picker(
        *,
        big5: dict[str, float],
        city: str,
        occupation: str,
        hobbies: list[str],
        darkness: int,
    ) -> list[ArchetypeCard]:
        client = _make_anthropic_client()
        # NR-05: do not echo the big5 dict in any user-facing surface; it is
        # consumed only by the LLM and discarded after the picker call.
        user = json.dumps(
            {
                "big5_summary": {d: float(big5.get(d, 0.0)) for d in DIMS},
                "city": city or "",
                "occupation": occupation or "",
                "hobbies": list(hobbies)[:8],
                "darkness": int(darkness),
            }
        )
        text = await _anthropic_text_call(
            client=client,
            model=_opus_model(),
            system=_PICKER_SYSTEM,
            user=user,
            max_tokens=900,
        )
        raw = json.loads(text)
        cards: list[ArchetypeCard] = []
        for item in raw:
            label = item.get("label", "")
            prose = item.get("prose", "")
            seed = item.get("archetype_seed") or _archetype_seed(
                label, city, occupation
            )
            # If the LLM returned a non-sha256 seed (length/format wrong), fall
            # back to the canonical seed builder. ArchetypeCard's pattern
            # validator would otherwise reject the card.
            if not (
                isinstance(seed, str)
                and len(seed) == ARCHETYPE_SEED_LEN
                and all(c in "0123456789abcdef" for c in seed)
            ):
                seed = _archetype_seed(label, city, occupation)
            cards.append(
                ArchetypeCard(label=label, prose=prose, archetype_seed=seed)
            )
        return cards

    return _picker


def make_anthropic_generator() -> BackstoryGenerator:
    """Construct an Opus-backed backstory persona generator callable.

    Currently unused by the /answer wiring (216-DE-wire ships archetype
    cards as the backstory_pick surface; per-archetype persona generation
    is deferred until the FE consumes both surfaces). Provided so future
    PRs can call it via ``generate_three_personas`` without contract
    churn.
    """

    async def _generator(
        *,
        picked_archetype: str,
        city: str,
        voice_tone: str,
        archetype_seed: str,
    ) -> list[BackstoryCard]:
        client = _make_anthropic_client()
        user = json.dumps(
            {
                "picked_archetype": picked_archetype,
                "city": city or "",
                "voice_tone": voice_tone or "",
                "archetype_seed": archetype_seed,
            }
        )
        text = await _anthropic_text_call(
            client=client,
            model=_opus_model(),
            system=_GENERATOR_SYSTEM,
            user=user,
            max_tokens=600,
        )
        raw = json.loads(text)
        cards: list[BackstoryCard] = []
        for item in raw:
            cards.append(
                BackstoryCard(
                    prose=item.get("prose", ""),
                    archetype_seed=item.get("archetype_seed") or archetype_seed,
                )
            )
        return cards

    return _generator


__all__ = [
    "PROSE_SLOT_KINDS_FOR_BIG5",
    "default_archetype_cards",
    "make_anthropic_generator",
    "make_anthropic_judge",
    "make_anthropic_picker",
    "should_populate_archetype_cards",
    "should_populate_cohort_chips",
    "should_run_big5_judge",
]
