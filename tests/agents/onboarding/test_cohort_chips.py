"""Tests for cohort_chips.py — Spec 216-D, D1.7.

Covers:
  - ``cache_key_hash`` is sha256-hex (no raw PII in the key surface)
  - 6 hand-seeded narrow cohorts return chip lists ~12 items
  - 2 catch-all cohorts on miss + occupation-only match
  - ``lookup_cohort`` is case-insensitive
  - Miss returns None
  - ChipOption length caps enforced
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from nikita.agents.onboarding.cohort_chips import (
    CHIP_LABEL_MAX_LEN,
    CHIP_VALUE_MAX_LEN,
    ChipOption,
    CohortCache,
    cache_key_hash,
    lookup_cohort,
)


SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")

# 6 hand-seeded narrow cohorts per D1.7
NARROW_COHORTS = [
    ("zurich", "designer"),
    ("london", "finance"),
    ("berlin", "nurse"),
    ("brooklyn", "dev"),
    ("sf", "founder"),
    ("stockholm", "researcher"),
]


# ---------------------------------------------------------------------------
# cache_key_hash — sha256-hex, no raw PII
# ---------------------------------------------------------------------------


def test_cache_key_hash_is_sha256_hex() -> None:
    """The cache key is exactly 64 lowercase hex chars."""
    key = cache_key_hash("Zurich", "Designer")
    assert SHA256_HEX_RE.match(key) is not None, (
        f"cache_key_hash should be sha256-hex; got {key!r}"
    )


def test_cache_key_hash_hides_raw_inputs() -> None:
    """Raw city + occupation MUST NOT appear in the cache key."""
    key = cache_key_hash("Zurich", "Designer")
    assert "zurich" not in key.lower(), "raw city leaked into cache key"
    assert "designer" not in key.lower(), "raw occupation leaked into cache key"


def test_cache_key_hash_case_insensitive() -> None:
    """Same key for different-case inputs (normalization happens inside)."""
    a = cache_key_hash("Zurich", "Designer")
    b = cache_key_hash("zurich", "designer")
    c = cache_key_hash("ZURICH", "DESIGNER")
    assert a == b == c


def test_cache_key_hash_strips_whitespace() -> None:
    a = cache_key_hash("  zurich  ", " designer ")
    b = cache_key_hash("zurich", "designer")
    assert a == b


def test_cache_key_hash_distinct_for_different_pairs() -> None:
    """Different (city, occupation) → different keys."""
    keys = {cache_key_hash(c, o) for (c, o) in NARROW_COHORTS}
    assert len(keys) == len(NARROW_COHORTS), (
        "every narrow cohort must produce a distinct cache key"
    )


def test_cache_key_hash_rejects_non_string() -> None:
    """Non-string inputs raise TypeError (defensive contract)."""
    with pytest.raises(TypeError):
        cache_key_hash(None, "designer")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        cache_key_hash("zurich", 42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# lookup_cohort — narrow + catch-all + miss
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("city,occupation", NARROW_COHORTS)
def test_narrow_cohorts_return_nonempty_chip_list(city: str, occupation: str) -> None:
    """Each of the 6 hand-seeded narrow cohorts returns a non-empty chip list."""
    chips = lookup_cohort(city, occupation)
    assert chips is not None, f"narrow cohort ({city}, {occupation}) returned None"
    assert len(chips) >= 1
    for ch in chips:
        assert isinstance(ch, ChipOption)


@pytest.mark.parametrize("city,occupation", NARROW_COHORTS)
def test_narrow_cohorts_return_about_twelve_chips(city: str, occupation: str) -> None:
    """Per D1.7 the seed list is ~12 items per narrow cohort."""
    chips = lookup_cohort(city, occupation)
    assert chips is not None
    # Spec says ~12; accept a band so curation tweaks don't churn the test.
    assert 8 <= len(chips) <= 16, (
        f"({city}, {occupation}) chip list has {len(chips)} items; "
        f"expected ~12"
    )


def test_lookup_cohort_case_insensitive() -> None:
    """Mixed-case inputs hit the same cohort as lowercase."""
    a = lookup_cohort("Zurich", "Designer")
    b = lookup_cohort("zurich", "designer")
    assert a is not None and b is not None
    assert [c.value for c in a] == [c.value for c in b]


def test_lookup_cohort_catchall_on_unknown_city_known_occupation() -> None:
    """Unknown city + known catch-all occupation → catch-all chips."""
    chips = lookup_cohort("kuala-lumpur", "designer")
    assert chips is not None, "catch-all cohort 'designer' should fire on miss"
    assert len(chips) >= 1
    for ch in chips:
        assert isinstance(ch, ChipOption)


def test_lookup_cohort_miss_returns_none() -> None:
    """Truly unknown (city, occupation) returns None."""
    chips = lookup_cohort("atlantis", "shipwright-philosopher")
    assert chips is None


def test_lookup_cohort_empty_inputs_return_none() -> None:
    """Empty strings return None (defensive)."""
    assert lookup_cohort("", "designer") is None
    assert lookup_cohort("zurich", "") is None


# ---------------------------------------------------------------------------
# ChipOption — length caps
# ---------------------------------------------------------------------------


def test_chip_value_length_cap() -> None:
    """ChipOption value > CHIP_VALUE_MAX_LEN raises ValidationError."""
    too_long = "a" * (CHIP_VALUE_MAX_LEN + 1)
    with pytest.raises(ValidationError):
        ChipOption(value=too_long, label="ok")


def test_chip_label_length_cap() -> None:
    """ChipOption label > CHIP_LABEL_MAX_LEN raises ValidationError."""
    too_long = "a" * (CHIP_LABEL_MAX_LEN + 1)
    with pytest.raises(ValidationError):
        ChipOption(value="ok", label=too_long)


def test_chip_value_min_length() -> None:
    """ChipOption value must be non-empty."""
    with pytest.raises(ValidationError):
        ChipOption(value="", label="ok")


def test_all_seeded_chips_within_caps() -> None:
    """Every chip in every narrow cohort respects both caps."""
    for city, occupation in NARROW_COHORTS:
        chips = lookup_cohort(city, occupation)
        assert chips is not None
        for ch in chips:
            assert len(ch.value) <= CHIP_VALUE_MAX_LEN
            assert len(ch.label) <= CHIP_LABEL_MAX_LEN
            assert len(ch.value) >= 1
            assert len(ch.label) >= 1


# ---------------------------------------------------------------------------
# CohortCache contract surface
# ---------------------------------------------------------------------------


def test_cohort_cache_get_falls_back_to_static() -> None:
    """Empty cache → get() returns the same as lookup_cohort()."""
    cache = CohortCache()
    chips = cache.get("zurich", "designer")
    assert chips is not None
    direct = lookup_cohort("zurich", "designer")
    assert direct is not None
    assert [c.value for c in chips] == [c.value for c in direct]


def test_cohort_cache_get_static_fallback_on_miss() -> None:
    """Empty cache, unknown pair → None via static fallback."""
    cache = CohortCache()
    assert cache.get("atlantis", "shipwright-philosopher") is None


def test_cohort_cache_set_round_trip_via_get_static_fallback() -> None:
    """``set`` does not affect ``get_static_fallback`` (fallback is the
    static seed table; ``set`` writes to live cache only).

    216-E will wire ``get`` to consult the live cache first; 216-D-code's
    ``get`` short-circuits to the static fallback so this test asserts only
    the static side is unaffected.
    """
    cache = CohortCache()
    custom = [ChipOption(value="custom", label="custom chip")]
    cache.set("zurich", "designer", custom)
    # static fallback unaffected
    static = cache.get_static_fallback("zurich", "designer")
    assert static is not None
    assert any(c.value == "custom" for c in static) is False


def test_cohort_cache_returned_lists_are_copies() -> None:
    """Mutating a returned chip list MUST NOT mutate the seed table."""
    cache = CohortCache()
    chips_a = cache.get("zurich", "designer")
    assert chips_a is not None
    chips_a.clear()
    chips_b = cache.get("zurich", "designer")
    assert chips_b is not None
    assert len(chips_b) > 0, "seed table was mutated by caller"
