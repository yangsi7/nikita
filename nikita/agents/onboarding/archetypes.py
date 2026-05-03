"""Curated 12-archetype taxonomy + meta-prompt picker (Spec 216-D, D1.6).

The 12 archetypes are LOCKED — the validator MUST reject any LLM output
referencing a label outside this tuple. Single source of truth.

Pipeline shape:

  ``pick_three_archetypes(big5, city, occupation, hobbies, darkness)``
      → 3 ``ArchetypeCard`` instances picked from the LOCKED 12-list
      → wired by 216-E /answer handler on the backstory_pick turn.

  ``generate_three_personas(picked_archetype, city, voice_tone, ...)``
      → 3 ``BackstoryCard`` short prose options (≤150 chars each)
      → user picks one; selection becomes ``backstory_seed`` server-side.

The actual LLM calls are wired by the route layer in 216-E (firecrawl +
Opus meta-prompt). 216-D-code ships the deterministic surface (taxonomy +
validators + Pydantic shapes + reject-invalid-label gate) so the route
layer can wire the agent without contract churn.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Final, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

ARCHETYPE_PROSE_MAX_LEN: Final[int] = 150
"""Max char length for archetype prose copy.

Current value: 150 (Spec 216-D-code, D1.6 introduction).
Rationale: 150 chars fits a single dark-luxe SMS-segment of body copy
comfortably while staying under the wizard reply budget. Tighter than
the default 280 ``NIKITA_REPLY_MAX_CHARS`` because the FE renders three
cards stacked, and any single card exceeding 150 chars wraps awkwardly.
Regression-guarded by ``test_archetype_card_prose_length`` in
``tests/agents/onboarding/test_archetypes.py``.
"""

BACKSTORY_PROSE_MAX_LEN: Final[int] = 150
"""Max char length for backstory persona prose.

Current value: 150 (Spec 216-D-code, D1.6 introduction).
Rationale: parallels ``ARCHETYPE_PROSE_MAX_LEN`` — backstory cards render
the same way in the FE. Single source of truth for prose ceilings; do
NOT diverge without UX review.
"""

ARCHETYPE_SEED_LEN: Final[int] = 64
"""Length of the sha256-hex seed attached to each ArchetypeCard.

Current value: 64 (Spec 216-D-code, D1.6 introduction).
Rationale: full sha256 hex (64 chars). The seed is a stable opaque
identifier for cohort-grouping and downstream caching; raw archetype
labels appear elsewhere in the response, so the seed is purely a
group-by handle. NEVER derive from raw PII.
"""

NUM_ARCHETYPE_CANDIDATES: Final[int] = 3
"""Number of archetype cards picked per call.

Current value: 3 (Spec 216-D-code, D1.6).
Rationale: spec mandates exactly 3 cards. UX choice: 3 is the minimum
that gives the user a real selection while staying under the cognitive
load of a longer list.
"""

NUM_BACKSTORY_PERSONAS: Final[int] = 3
"""Number of persona backstory cards generated per archetype.

Current value: 3 (Spec 216-D-code, D1.6).
Rationale: same as ``NUM_ARCHETYPE_CANDIDATES`` — cohesive UX.
"""


# ---------------------------------------------------------------------------
# LOCKED 12-archetype taxonomy — single source of truth (D1.6)
# ---------------------------------------------------------------------------

# Tuple is intentionally Final + immutable. Validators reject any label not
# in this tuple. NEVER expand without spec amendment + test update.
ARCHETYPES: Final[tuple[str, ...]] = (
    "the runner",
    "the maker",
    "the watcher",
    "the climber",
    "the seeker",
    "the architect",
    "the survivor",
    "the rebel",
    "the romantic",
    "the wanderer",
    "the host",
    "the fugitive",
)

# Literal type matching ARCHETYPES — used for Pydantic validation.
# Lockstep with the tuple is enforced by the module-load assertion below
# AND the regression test
# ``test_archetype_taxonomy_is_locked_to_twelve_labels`` in
# ``tests/agents/onboarding/test_archetypes.py``.
ArchetypeLabel = Literal[
    "the runner",
    "the maker",
    "the watcher",
    "the climber",
    "the seeker",
    "the architect",
    "the survivor",
    "the rebel",
    "the romantic",
    "the wanderer",
    "the host",
    "the fugitive",
]

# Module-load lockstep assertion — fails import (and every test) if the
# tuple and Literal drift. Cheaper signal than waiting for a runtime test.
assert set(ARCHETYPES) == set(get_args(ArchetypeLabel)), (
    "ARCHETYPES tuple and ArchetypeLabel Literal drifted; update both "
    "in lockstep."
)


# ---------------------------------------------------------------------------
# Pydantic shapes
# ---------------------------------------------------------------------------


class ArchetypeCard(BaseModel):
    """One of three archetype-pick cards surfaced to the user.

    ``label`` is a Literal type whose membership is policed by Pydantic at
    parse time — invented labels raise ``ValidationError`` (NOT
    ``ModelRetry``: invalid LLM output here is a contract violation, not a
    retry-able error per the design rule in spec D1.6).

    ``prose`` is the dark-luxe rationale copy (≤150 chars, no emoji, no
    markdown — same surface rules as wizard replies).

    ``archetype_seed`` is a sha256-hex stable identifier for cohort
    grouping. NEVER raw PII.
    """

    model_config = ConfigDict(extra="forbid")

    label: ArchetypeLabel = Field(
        description="One of the LOCKED 12-archetype labels. Pydantic rejects "
        "anything else.",
    )
    prose: str = Field(
        min_length=1,
        max_length=ARCHETYPE_PROSE_MAX_LEN,
        description="≤150 char dark-luxe rationale. No emoji, no markdown.",
    )
    archetype_seed: str = Field(
        min_length=ARCHETYPE_SEED_LEN,
        max_length=ARCHETYPE_SEED_LEN,
        pattern=r"^[a-f0-9]{64}$",
        description="sha256-hex opaque seed for cohort grouping (no PII).",
    )

    # Note: per-instance ``label in ARCHETYPES`` defensive check was removed
    # in QA iter-2 — the module-load assertion above (set(ARCHETYPES) ==
    # set(get_args(ArchetypeLabel))) catches drift at import time, making
    # the per-instance check unreachable in normal flow. Cleaner to fail
    # fast at import than to carry dead defensive code.


class BackstoryCard(BaseModel):
    """One of three persona-backstory cards generated for the picked archetype.

    Short prose only (≤150 chars). The user's pick becomes ``backstory_seed``
    server-side — a hashed identifier of the chosen prose, NOT the prose
    itself in the cache key (closes #446 PII echo).
    """

    model_config = ConfigDict(extra="forbid")

    prose: str = Field(
        min_length=1,
        max_length=BACKSTORY_PROSE_MAX_LEN,
        description="≤150 char dark-luxe persona prose. No emoji, no markdown.",
    )
    archetype_seed: str = Field(
        min_length=ARCHETYPE_SEED_LEN,
        max_length=ARCHETYPE_SEED_LEN,
        pattern=r"^[a-f0-9]{64}$",
        description="sha256-hex archetype-grouping seed (matches the picked "
        "ArchetypeCard's seed — joins the two surfaces).",
    )


# ---------------------------------------------------------------------------
# Validator helpers
# ---------------------------------------------------------------------------


def is_valid_archetype_label(label: str) -> bool:
    """Pure helper — True iff label is in the LOCKED 12-archetype taxonomy."""
    return label in ARCHETYPES


class ArchetypePicks(RootModel[list[ArchetypeCard]]):
    """Length-3 list of distinct in-taxonomy archetype picks.

    Wraps ``list[ArchetypeCard]`` with cross-field validation. The label
    in-taxonomy guarantee comes from ``ArchetypeCard``'s ``Literal``;
    this RootModel adds count + uniqueness gates. Idiomatic Pydantic v2
    — replaces a verbose ``ValidationError.from_exception_data``
    construction.
    """

    @model_validator(mode="after")
    def _exactly_three_distinct(self) -> "ArchetypePicks":
        cards = self.root
        if len(cards) != NUM_ARCHETYPE_CANDIDATES:
            raise ValueError(
                f"expected exactly {NUM_ARCHETYPE_CANDIDATES} cards, "
                f"got {len(cards)}"
            )
        labels = [c.label for c in cards]
        if len(set(labels)) != len(labels):
            raise ValueError(
                f"duplicate archetype label among picks: {labels!r}; "
                "picks must be distinct"
            )
        return self


def validate_archetype_picks(cards: list[ArchetypeCard]) -> list[ArchetypeCard]:
    """Validate that ``cards`` is a length-3 list of distinct in-taxonomy
    archetypes. Raises ``pydantic.ValidationError`` on any violation.

    Kept as a thin function so the route layer can call it directly without
    knowing the ``ArchetypePicks`` wrapper. Implementation delegates to the
    RootModel so the validation logic lives in one place.
    """
    return ArchetypePicks.model_validate(cards).root


# ---------------------------------------------------------------------------
# Picker scaffolds
# ---------------------------------------------------------------------------


# 216-D-code ships the surface; 216-E wires the actual Opus meta-prompt + the
# firecrawl city/occupation enrichment. The function signature is the
# contract that 216-E preserves.
#
# ``ArchetypePicker`` and ``BackstoryGenerator`` are precise Callable type
# aliases so static checkers + IDEs see the expected call signature. We use
# Callable rather than ``typing.Protocol`` because callers always pass a
# bare ``async def`` function (no class with ``__call__``); a Protocol
# would be over-machinery for the use-case.

ArchetypePicker = Callable[..., Awaitable[list["ArchetypeCard"]]]
"""Async callable that returns 3 archetype cards.

Expected kwargs (passed by ``pick_three_archetypes``):
  big5: dict[str, float], city: str, occupation: str,
  hobbies: list[str], darkness: int
"""

BackstoryGenerator = Callable[..., Awaitable[list["BackstoryCard"]]]
"""Async callable that returns 3 backstory cards.

Expected kwargs (passed by ``generate_three_personas``):
  picked_archetype: str, city: str, voice_tone: str, archetype_seed: str
"""


async def pick_three_archetypes(
    big5: dict[str, float],
    city: str,
    occupation: str,
    hobbies: list[str],
    darkness: int,
    *,
    picker: ArchetypePicker | None = None,
) -> list[ArchetypeCard]:
    """Pick exactly 3 archetypes from the LOCKED 12-list.

    The default ``picker`` is None — when None, the function delegates to a
    dependency-injected callable so unit tests can stub the LLM. 216-E will
    pass an Opus-backed picker; 216-D-code's tests pass a mock picker.

    Returns 3 distinct ``ArchetypeCard`` instances. Raises
    ``ValidationError`` if the picker emits an out-of-taxonomy label.
    """
    if picker is None:
        raise RuntimeError(
            "pick_three_archetypes requires a picker callable; 216-E wires "
            "the Opus default. 216-D-code ships only the validation surface."
        )

    raw = await picker(
        big5=big5,
        city=city,
        occupation=occupation,
        hobbies=hobbies,
        darkness=darkness,
    )
    # ArchetypeCard's Literal[...] + @model_validator catches invented labels
    # at parse time. We additionally enforce length + uniqueness here.
    return validate_archetype_picks(raw)


async def generate_three_personas(
    picked_archetype: str,
    city: str,
    voice_tone: str,
    *,
    archetype_seed: str,
    generator: BackstoryGenerator | None = None,
) -> list[BackstoryCard]:
    """Generate exactly 3 short persona backstory cards (≤150 chars each).

    Like ``pick_three_archetypes``, the actual LLM call is dependency-injected
    via ``generator``. ``picked_archetype`` MUST be in ARCHETYPES. The
    returned cards share the ``archetype_seed`` so the FE can join them.
    """
    if not is_valid_archetype_label(picked_archetype):
        raise ValueError(
            f"picked_archetype {picked_archetype!r} not in LOCKED taxonomy"
        )
    if generator is None:
        raise RuntimeError(
            "generate_three_personas requires a generator callable; 216-E "
            "wires the Opus default."
        )

    raw = await generator(
        picked_archetype=picked_archetype,
        city=city,
        voice_tone=voice_tone,
        archetype_seed=archetype_seed,
    )
    if len(raw) != NUM_BACKSTORY_PERSONAS:
        raise ValueError(
            f"generator returned {len(raw)} personas; expected "
            f"{NUM_BACKSTORY_PERSONAS}"
        )
    # Pydantic per-field validation already enforces prose length + seed
    # shape; nothing more needed here.
    return list(raw)


__all__ = [
    "ARCHETYPES",
    "ARCHETYPE_PROSE_MAX_LEN",
    "ARCHETYPE_SEED_LEN",
    "ArchetypeCard",
    "ArchetypeLabel",
    "ArchetypePicker",
    "ArchetypePicks",
    "BACKSTORY_PROSE_MAX_LEN",
    "BackstoryCard",
    "BackstoryGenerator",
    "NUM_ARCHETYPE_CANDIDATES",
    "NUM_BACKSTORY_PERSONAS",
    "generate_three_personas",
    "is_valid_archetype_label",
    "pick_three_archetypes",
    "validate_archetype_picks",
]
