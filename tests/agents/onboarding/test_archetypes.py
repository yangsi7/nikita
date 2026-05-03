"""Tests for archetypes.py — Spec 216-D, D1.6.

Covers:
  - 12-archetype tuple is locked (regression guard)
  - ArchetypeCard rejects invented labels at parse time (Pydantic Literal)
  - ArchetypeCard prose length cap enforced
  - ArchetypeCard archetype_seed must be sha256-hex
  - ``validate_archetype_picks`` rejects wrong-count + duplicates
  - ``pick_three_archetypes`` calls the injected picker + validates output
  - ``generate_three_personas`` rejects out-of-taxonomy archetype
  - ``is_valid_archetype_label`` is a pure helper
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from pydantic import ValidationError

from nikita.agents.onboarding.archetypes import (
    ARCHETYPES,
    ARCHETYPE_PROSE_MAX_LEN,
    ARCHETYPE_SEED_LEN,
    NUM_ARCHETYPE_CANDIDATES,
    NUM_BACKSTORY_PERSONAS,
    ArchetypeCard,
    BackstoryCard,
    generate_three_personas,
    is_valid_archetype_label,
    pick_three_archetypes,
    validate_archetype_picks,
)


def _seed(value: str = "alpha") -> str:
    """Return a deterministic sha256-hex string suitable for archetype_seed."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Locked 12-tuple regression guard
# ---------------------------------------------------------------------------


def test_archetype_taxonomy_is_locked_to_twelve_labels() -> None:
    """Spec D1.6 LOCKS exactly these 12 labels in this order. Changing this
    test means amending the spec — never the other way around.
    """
    expected = (
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
    assert ARCHETYPES == expected, (
        "12-archetype taxonomy drift detected; per spec D1.6 the list is "
        "LOCKED. If you intentionally changed the taxonomy, update the spec "
        "first."
    )


def test_archetype_taxonomy_length_constants() -> None:
    """Tuning constants stay in lockstep with the tuple."""
    assert len(ARCHETYPES) == 12
    assert NUM_ARCHETYPE_CANDIDATES == 3
    assert NUM_BACKSTORY_PERSONAS == 3


def test_is_valid_archetype_label_for_each_locked_label() -> None:
    for label in ARCHETYPES:
        assert is_valid_archetype_label(label) is True


def test_is_valid_archetype_label_rejects_invented() -> None:
    for invented in ("the unicorn", "the cyborg", "", "RUNNER", "the runner "):
        assert is_valid_archetype_label(invented) is False, (
            f"{invented!r} should not be a valid archetype label"
        )


# ---------------------------------------------------------------------------
# ArchetypeCard — Pydantic gates
# ---------------------------------------------------------------------------


def test_archetype_card_accepts_valid_payload() -> None:
    card = ArchetypeCard(
        label="the runner",
        prose="someone who only feels alive moving",
        archetype_seed=_seed(),
    )
    assert card.label == "the runner"


def test_archetype_card_rejects_invented_label() -> None:
    """Pydantic Literal rejection at parse time."""
    with pytest.raises(ValidationError) as exc:
        ArchetypeCard(
            label="the unicorn",  # type: ignore[arg-type]
            prose="ok",
            archetype_seed=_seed(),
        )
    assert "literal" in str(exc.value).lower() or "the unicorn" in str(exc.value)


def test_archetype_card_prose_length_cap() -> None:
    """prose > ARCHETYPE_PROSE_MAX_LEN raises ValidationError."""
    too_long = "a" * (ARCHETYPE_PROSE_MAX_LEN + 1)
    with pytest.raises(ValidationError):
        ArchetypeCard(
            label="the runner",
            prose=too_long,
            archetype_seed=_seed(),
        )


def test_archetype_card_seed_must_be_sha256_hex() -> None:
    """archetype_seed must match ^[a-f0-9]{64}$ — no raw PII."""
    with pytest.raises(ValidationError):
        ArchetypeCard(
            label="the runner",
            prose="ok",
            archetype_seed="zurich|designer|3",  # raw PII pattern
        )
    with pytest.raises(ValidationError):
        ArchetypeCard(
            label="the runner",
            prose="ok",
            archetype_seed="A" * ARCHETYPE_SEED_LEN,  # uppercase hex
        )


def test_archetype_card_prose_min_length() -> None:
    """Empty prose rejected."""
    with pytest.raises(ValidationError):
        ArchetypeCard(
            label="the runner",
            prose="",
            archetype_seed=_seed(),
        )


# ---------------------------------------------------------------------------
# validate_archetype_picks
# ---------------------------------------------------------------------------


def _three_distinct_cards() -> list[ArchetypeCard]:
    return [
        ArchetypeCard(label="the runner", prose="alpha", archetype_seed=_seed("a")),
        ArchetypeCard(label="the maker", prose="beta", archetype_seed=_seed("b")),
        ArchetypeCard(label="the watcher", prose="gamma", archetype_seed=_seed("c")),
    ]


def test_validate_archetype_picks_accepts_three_distinct() -> None:
    out = validate_archetype_picks(_three_distinct_cards())
    assert len(out) == 3
    assert {c.label for c in out} == {"the runner", "the maker", "the watcher"}


def test_validate_archetype_picks_rejects_wrong_count() -> None:
    too_few = _three_distinct_cards()[:2]
    with pytest.raises(ValidationError):
        validate_archetype_picks(too_few)
    too_many = _three_distinct_cards() + [
        ArchetypeCard(label="the climber", prose="delta", archetype_seed=_seed("d"))
    ]
    with pytest.raises(ValidationError):
        validate_archetype_picks(too_many)


def test_validate_archetype_picks_rejects_duplicate_label() -> None:
    cards = [
        ArchetypeCard(label="the runner", prose="a", archetype_seed=_seed("a")),
        ArchetypeCard(label="the runner", prose="b", archetype_seed=_seed("b")),
        ArchetypeCard(label="the maker", prose="c", archetype_seed=_seed("c")),
    ]
    with pytest.raises(ValidationError):
        validate_archetype_picks(cards)


# ---------------------------------------------------------------------------
# pick_three_archetypes — picker injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pick_three_archetypes_calls_picker_and_validates() -> None:
    """Mock picker returns 3 valid cards → result equals picker output."""
    expected = _three_distinct_cards()
    call_kwargs: dict[str, Any] = {}

    async def fake_picker(**kwargs: Any) -> list[ArchetypeCard]:
        call_kwargs.update(kwargs)
        return expected

    out = await pick_three_archetypes(
        big5={"O": 0.7, "C": 0.5, "E": 0.6, "A": 0.4, "N": 0.3},
        city="zurich",
        occupation="designer",
        hobbies=["running"],
        darkness=3,
        picker=fake_picker,
    )
    assert [c.label for c in out] == [c.label for c in expected]
    # Picker received all 5 inputs as kwargs.
    assert call_kwargs["city"] == "zurich"
    assert call_kwargs["darkness"] == 3
    assert call_kwargs["hobbies"] == ["running"]


@pytest.mark.asyncio
async def test_pick_three_archetypes_rejects_picker_with_invented_label() -> None:
    """Picker returning a Pydantic-invalid card raises ValidationError —
    NOT ModelRetry. Per spec D1.6 invalid LLM output is a contract
    violation, not a retry-able error.
    """
    async def bad_picker(**_: Any) -> list[ArchetypeCard]:
        # Cannot construct ArchetypeCard with invented label (Pydantic
        # rejects), so simulate the failure mode at picker boundary.
        return [
            ArchetypeCard(label="the unicorn", prose="x", archetype_seed=_seed())  # type: ignore[arg-type]
        ]

    with pytest.raises(ValidationError):
        await pick_three_archetypes(
            big5={},
            city="x",
            occupation="x",
            hobbies=[],
            darkness=0,
            picker=bad_picker,
        )


@pytest.mark.asyncio
async def test_pick_three_archetypes_rejects_picker_with_duplicate_label() -> None:
    async def dup_picker(**_: Any) -> list[ArchetypeCard]:
        return [
            ArchetypeCard(label="the runner", prose="a", archetype_seed=_seed("a")),
            ArchetypeCard(label="the runner", prose="b", archetype_seed=_seed("b")),
            ArchetypeCard(label="the maker", prose="c", archetype_seed=_seed("c")),
        ]

    with pytest.raises(ValidationError):
        await pick_three_archetypes(
            big5={},
            city="x",
            occupation="x",
            hobbies=[],
            darkness=0,
            picker=dup_picker,
        )


@pytest.mark.asyncio
async def test_pick_three_archetypes_no_picker_raises() -> None:
    """Calling without a picker raises RuntimeError (216-E will inject)."""
    with pytest.raises(RuntimeError):
        await pick_three_archetypes(
            big5={},
            city="x",
            occupation="x",
            hobbies=[],
            darkness=0,
        )


# ---------------------------------------------------------------------------
# generate_three_personas — generator injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_three_personas_returns_three_cards() -> None:
    seed = _seed("zurich|designer|the runner")

    async def fake_gen(**_: Any) -> list[BackstoryCard]:
        return [
            BackstoryCard(prose="one", archetype_seed=seed),
            BackstoryCard(prose="two", archetype_seed=seed),
            BackstoryCard(prose="three", archetype_seed=seed),
        ]

    out = await generate_three_personas(
        picked_archetype="the runner",
        city="zurich",
        voice_tone="dark-luxe",
        archetype_seed=seed,
        generator=fake_gen,
    )
    assert len(out) == 3


@pytest.mark.asyncio
async def test_generate_three_personas_rejects_invalid_archetype() -> None:
    seed = _seed()

    async def fake_gen(**_: Any) -> list[BackstoryCard]:
        return []

    with pytest.raises(ValueError):
        await generate_three_personas(
            picked_archetype="the unicorn",
            city="zurich",
            voice_tone="dark-luxe",
            archetype_seed=seed,
            generator=fake_gen,
        )


@pytest.mark.asyncio
async def test_generate_three_personas_enforces_count() -> None:
    seed = _seed()

    async def two_only(**_: Any) -> list[BackstoryCard]:
        return [
            BackstoryCard(prose="one", archetype_seed=seed),
            BackstoryCard(prose="two", archetype_seed=seed),
        ]

    with pytest.raises(ValueError):
        await generate_three_personas(
            picked_archetype="the runner",
            city="zurich",
            voice_tone="dark-luxe",
            archetype_seed=seed,
            generator=two_only,
        )


@pytest.mark.asyncio
async def test_generate_three_personas_no_generator_raises() -> None:
    with pytest.raises(RuntimeError):
        await generate_three_personas(
            picked_archetype="the runner",
            city="zurich",
            voice_tone="dark-luxe",
            archetype_seed=_seed(),
        )
