"""Hand-seeded cohort chip suggestions for the primary_hobbies turn (Spec 216-D, D1.7).

Maps `(city, occupation)` pairs to ordered chip-list suggestions. Cache key is
the sha256-hex of `lowercase_city + "|" + lowercase_occupation` — the raw values
NEVER appear in the cache key, log lines, or any returned dict (closes #446 PII
leak in cache_key surface).

Hand-seeded cohorts (D1.7 spec list, hand-curated):
  - (zurich, designer)
  - (london, finance)
  - (berlin, nurse)
  - (brooklyn, dev)
  - (sf, founder)
  - (stockholm, researcher)

Plus 2 catch-all cohorts (any-city × archetypal occupations) so misses on the
6-tuple narrow set still get a usable chip list when the (city, occupation) is
plausible. Catch-alls are matched on occupation alone.

216-E will replace the static dict with a firecrawl-backed live-lookup +
TTL-bounded cache. The current ``CohortCache`` shape is the contract surface
that 216-E will preserve. TODO(216-E Q4): wire TTL eviction.
"""

from __future__ import annotations

import hashlib
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

CHIP_VALUE_MAX_LEN: Final[int] = 24
"""Max chip ``value`` (token sent back from FE on selection).

Current value: 24 (Spec 216-D-code, D1.7 introduction).
Rationale: Chip values are URL-safe slugs that piggy-back on the same
sanitization budget as other wizard inputs; 24 chars covers slugs like
``sourdough-starter`` while staying tight for FE button rendering.
Regression-guarded by ``test_chip_value_length`` in
``tests/agents/onboarding/test_cohort_chips.py``.
"""

CHIP_LABEL_MAX_LEN: Final[int] = 32
"""Max chip ``label`` (human-facing copy on the chip button).

Current value: 32 (Spec 216-D-code, D1.7 introduction).
Rationale: 32 chars fits a single FE button row at the design's body
type-scale without truncation. Tighter than the 64-char general slot
ceiling because chip rows render N items per row.
"""

# 216-E will replace this with a firecrawl-backed lookup. Until then the
# static dict is sufficient. ChipOption shape MUST stay stable.

CITY_OCCUPATION_DELIM: Final[str] = "|"
"""Delimiter for the sha256 hash input. Stable across releases — changing this
invalidates every cached entry; treat as a contract."""


# ---------------------------------------------------------------------------
# ChipOption — Pydantic shape for a single chip suggestion
# ---------------------------------------------------------------------------


class ChipOption(BaseModel):
    """One chip in a cohort suggestion list.

    ``value`` is the slug echoed back when the user selects the chip (used as
    a free-form tag downstream). ``label`` is the user-facing copy.
    """

    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1, max_length=CHIP_VALUE_MAX_LEN)
    label: str = Field(min_length=1, max_length=CHIP_LABEL_MAX_LEN)


# ---------------------------------------------------------------------------
# Hand-seeded cohort table
# ---------------------------------------------------------------------------


def _chips(*pairs: tuple[str, str]) -> list[ChipOption]:
    """Helper to build a ChipOption list from (value, label) tuples."""
    return [ChipOption(value=v, label=l) for v, l in pairs]


# Each entry is keyed by sha256_hex(lowercase_city|lowercase_occupation) so the
# raw PII never lives in the cache key surface. The literal sha256 values
# below are computed at import time via ``cache_key_hash`` for clarity, but
# stored alongside the canonical (city, occupation) seed used to compute them
# so future maintainers can verify the mapping.

# Catch-all cohorts (occupation-only). Looked up when no narrow match found.
_CATCHALL_COHORTS: dict[str, list[ChipOption]] = {
    "designer": _chips(
        ("morning-pages", "morning pages"),
        ("studio-time", "studio time"),
        ("vinyl", "vinyl crates"),
        ("typography", "typography"),
        ("film-photo", "film photo"),
        ("ceramics", "ceramics"),
        ("sketchbooks", "sketchbooks"),
        ("gallery-walks", "gallery walks"),
        ("sourdough", "sourdough"),
        ("running", "running"),
        ("vintage", "vintage hunting"),
        ("dj-sets", "DJ sets"),
    ),
    "dev": _chips(
        ("side-projects", "side projects"),
        ("mech-keyboards", "mech keyboards"),
        ("retro-games", "retro games"),
        ("home-lab", "home lab"),
        ("3d-print", "3D printing"),
        ("synth-noodling", "synth noodling"),
        ("trail-running", "trail running"),
        ("specialty-coffee", "specialty coffee"),
        ("rationalist-blogs", "rationalist blogs"),
        ("climbing", "bouldering"),
        ("sci-fi", "sci-fi novels"),
        ("indie-rpgs", "indie RPGs"),
    ),
}


def _build_narrow_cohorts() -> dict[str, list[ChipOption]]:
    """Build the narrow (city, occupation) cohort table keyed by sha256-hex."""
    raw_seeds: dict[tuple[str, str], list[ChipOption]] = {
        ("zurich", "designer"): _chips(
            ("limmat-swims", "Limmat swims"),
            ("zhdk-talks", "ZHdK talks"),
            ("freitag", "Freitag hunting"),
            ("specialty-coffee", "specialty coffee"),
            ("alpine-hikes", "alpine hikes"),
            ("flea-marketing", "flea markets"),
            ("type-design", "type design"),
            ("vinyl", "vinyl crates"),
            ("ceramics", "ceramics"),
            ("kunsthaus", "Kunsthaus visits"),
            ("running", "running"),
            ("natural-wine", "natural wine"),
        ),
        ("london", "finance"): _chips(
            ("rowing", "rowing"),
            ("sunday-roasts", "Sunday roasts"),
            ("squash", "squash"),
            ("vinyl", "vinyl crates"),
            ("hatton-cycle", "Hatton cycling"),
            ("longreads", "longreads"),
            ("chess-clubs", "chess clubs"),
            ("hampstead-walks", "Hampstead walks"),
            ("natural-wine", "natural wine"),
            ("members-clubs", "members clubs"),
            ("running", "running"),
            ("garage-rock", "garage rock"),
        ),
        ("berlin", "nurse"): _chips(
            ("techno-fridays", "techno Fridays"),
            ("berghain", "Berghain queues"),
            ("sauna", "sauna nights"),
            ("cycling", "cycling"),
            ("flea-marketing", "flea markets"),
            ("yoga", "yoga"),
            ("plant-shops", "plant shops"),
            ("bouldering", "bouldering"),
            ("philosophy", "philosophy talks"),
            ("running", "running"),
            ("urban-gardens", "urban gardens"),
            ("specialty-coffee", "specialty coffee"),
        ),
        ("brooklyn", "dev"): _chips(
            ("indie-cinema", "indie cinema"),
            ("specialty-coffee", "specialty coffee"),
            ("running", "running"),
            ("synth-noodling", "synth noodling"),
            ("vinyl", "vinyl crates"),
            ("rooftops", "rooftop sunsets"),
            ("bouldering", "bouldering"),
            ("home-lab", "home lab"),
            ("longform-fiction", "longform fiction"),
            ("podcasts", "deep podcasts"),
            ("retro-games", "retro games"),
            ("bodega-runs", "bodega runs"),
        ),
        ("sf", "founder"): _chips(
            ("ocean-runs", "ocean runs"),
            ("sauna", "sauna nights"),
            ("rationalist-blogs", "rationalist blogs"),
            ("bouldering", "bouldering"),
            ("specialty-coffee", "specialty coffee"),
            ("longreads", "longreads"),
            ("synth-noodling", "synth noodling"),
            ("burner-camps", "burner camps"),
            ("hot-springs", "hot springs"),
            ("trail-running", "trail running"),
            ("sci-fi", "sci-fi novels"),
            ("kettlebells", "kettlebells"),
        ),
        ("stockholm", "researcher"): _chips(
            ("sauna", "sauna nights"),
            ("cross-country", "cross-country"),
            ("philosophy", "philosophy talks"),
            ("specialty-coffee", "specialty coffee"),
            ("sci-fi", "sci-fi novels"),
            ("bouldering", "bouldering"),
            ("running", "running"),
            ("vinyl", "vinyl crates"),
            ("sourdough", "sourdough"),
            ("nordic-noir", "Nordic noir"),
            ("archipelago", "archipelago hops"),
            ("longreads", "longreads"),
        ),
    }
    return {
        cache_key_hash(city, occupation): chips
        for (city, occupation), chips in raw_seeds.items()
    }


def cache_key_hash(city: str, occupation: str) -> str:
    """Compute the sha256-hex cache key for a (city, occupation) pair.

    Inputs are lowercased + stripped before hashing — case-insensitive matching
    per D1.7. The raw values NEVER appear in the returned key, in log lines,
    or in any chip option payload.
    """
    if not isinstance(city, str) or not isinstance(occupation, str):
        raise TypeError("cache_key_hash requires string inputs")
    normalized = (
        city.strip().lower()
        + CITY_OCCUPATION_DELIM
        + occupation.strip().lower()
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# Built once at import — hand-seeded data is static.
_NARROW_COHORTS: Final[dict[str, list[ChipOption]]] = _build_narrow_cohorts()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup_cohort(city: str, occupation: str) -> list[ChipOption] | None:
    """Lookup chip suggestions for a (city, occupation) pair.

    Order of resolution:
      1. Narrow `(city, occupation)` match via sha256-hex key.
      2. Catch-all on occupation alone (case-insensitive).
      3. None on miss.

    Inputs are case-insensitively normalized; the raw values are not echoed
    into the returned chips' values or labels — chips are pre-curated copy.
    """
    if not city or not occupation:
        return None

    narrow_key = cache_key_hash(city, occupation)
    narrow_hit = _NARROW_COHORTS.get(narrow_key)
    if narrow_hit is not None:
        return list(narrow_hit)

    occupation_norm = occupation.strip().lower()
    catchall = _CATCHALL_COHORTS.get(occupation_norm)
    if catchall is not None:
        return list(catchall)
    return None


# ---------------------------------------------------------------------------
# CohortCache — contract surface for 216-E
# ---------------------------------------------------------------------------


class CohortCache:
    """Static-fallback cohort cache.

    216-D-code ships with a hand-seeded dict; 216-E will swap in a
    firecrawl-backed live-lookup with TTL eviction. The class shape is the
    contract that 216-E preserves.

    TODO(216-E Q4): replace static dict with TTL-bounded LRU + firecrawl
    live-lookup. Default TTL TBD pending firecrawl-budget design.
    """

    def __init__(self) -> None:
        # Empty by default — get() falls through to ``get_static_fallback``.
        self._memo: dict[str, list[ChipOption]] = {}

    def get(self, city: str, occupation: str) -> list[ChipOption] | None:
        """Return chips for the (city, occupation) pair, or None on miss.

        216-D-code: identical to ``get_static_fallback``. 216-E will check
        live-lookup cache first.
        """
        return self.get_static_fallback(city, occupation)

    def set(self, city: str, occupation: str, chips: list[ChipOption]) -> None:
        """Memoize a chip list for a (city, occupation) pair.

        216-D-code: write-through to in-memory dict (no eviction). 216-E
        will add TTL.
        """
        if not chips:
            return
        key = cache_key_hash(city, occupation)
        self._memo[key] = list(chips)

    def get_static_fallback(
        self, city: str, occupation: str
    ) -> list[ChipOption] | None:
        """Look up the hand-seeded cohort without touching live state."""
        return lookup_cohort(city, occupation)


__all__ = [
    "CHIP_LABEL_MAX_LEN",
    "CHIP_VALUE_MAX_LEN",
    "ChipOption",
    "CohortCache",
    "cache_key_hash",
    "lookup_cohort",
]
