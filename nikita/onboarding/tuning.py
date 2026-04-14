"""Tuning constants for Spec 213 onboarding backend (FR-4).

Domain-specific timeouts, cache TTLs, rate limits, and bucket mappings for
the portal onboarding handoff path.

CONSTRAINT (FR-4 isolation): This module MUST NOT import from
nikita.engine.constants, nikita.onboarding.models, or nikita.db.*. It is a
pure constants + pure-function module. `compute_backstory_cache_key` is
duck-typed — any object exposing the right attributes works at runtime.

Per .claude/rules/tuning-constants.md, every constant has:
  - Current value
  - Prior values with driving PR/GH issue
  - One-line rationale for *this* value

Regression guards in tests/onboarding/test_tuning_constants.py.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Service call timeouts
# ---------------------------------------------------------------------------

VENUE_RESEARCH_TIMEOUT_S: Final[float] = 15.0
"""Per-call timeout for VenueResearchService.research_venues.

Prior values: none (new in Spec 213, GH #213).
Rationale: Firecrawl typical p95 ~8s; 15s budget covers cold cache + 1 retry.
"""

BACKSTORY_GEN_TIMEOUT_S: Final[float] = 20.0
"""Per-call timeout for BackstoryGeneratorService.generate_scenarios.

Prior values: none (new in Spec 213, GH #213).
Rationale: Claude Haiku typical p95 ~12s; 20s covers tail latency + 1 retry.
"""

# ---------------------------------------------------------------------------
# Pipeline-ready gate
# ---------------------------------------------------------------------------

PIPELINE_GATE_POLL_INTERVAL_S: Final[float] = 2.0
"""Portal poll interval for /pipeline-ready endpoint.

Prior values: none (new in Spec 213, GH #213).
Rationale: balances perceived responsiveness vs Cloud Run cold-start churn.
"""

PIPELINE_GATE_MAX_WAIT_S: Final[float] = 20.0
"""Maximum portal wait for pipeline readiness before unblocking.

Prior values: none (new in Spec 213, GH #213).
Rationale: VenueResearch (15s) and BackstoryGenerator (20s) run in parallel
fanout, so the dominant bound is BACKSTORY_GEN_TIMEOUT_S (20s). Cloud Run
cold-start (~5s) is absorbed by the parallel fanout. If either service
exceeds 20s, the portal unblocks with 'degraded' state per FR-2a and the
backend continues its pipeline independently. Invariant guarded by tests
in test_tuning_constants.py::TestTimeoutRelationalInvariants.
"""

# ---------------------------------------------------------------------------
# Cache + generation tuning
# ---------------------------------------------------------------------------

BACKSTORY_CACHE_TTL_DAYS: Final[int] = 30
"""Backstory cache TTL for unique (city, scene, ...) profile shape.

Prior values: none (new in Spec 213, GH #213).
Rationale: matches existing VenueCache TTL; balances cost vs scenario freshness.
"""

BACKSTORY_HOOK_PROBABILITY: Final[float] = 0.50
"""Probability that FirstMessageGenerator includes a backstory hook in the first message.

Prior values: none (new in Spec 213, GH #213).
Rationale: 50% creates variety; testable via patched value (1.0 always-include, 0.0 never-include).
"""

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------

PREVIEW_RATE_LIMIT_PER_MIN: Final[int] = 5
"""Per-user rate limit for POST /onboarding/preview-backstory (FR-4a.1).

Prior values: none (new in Spec 213, iter-7 amendment).
Rationale: each call triggers Claude + Firecrawl; 5/min covers wizard navigation and
legitimate retries but prevents abuse/DoS. Voice rate limit is 20/min — different surface
with different cost profile. Separate counter key prefix 'preview:' avoids sharing quota
with the voice rate limiter.
"""

# ---------------------------------------------------------------------------
# Cache-key bucketing
# ---------------------------------------------------------------------------

AGE_BUCKETS: Final[tuple[tuple[int, int, str], ...]] = (
    (18, 24, "young_adult"),
    (25, 34, "twenties"),
    (35, 49, "midlife"),
    (50, 99, "experienced"),
)
"""Age bucketing for backstory cache key. Inclusive boundaries.

Prior values: none (new in Spec 213).
Rationale: 4 buckets balance cache hit ratio vs personalization granularity.
"""

OCCUPATION_CATEGORIES: Final[dict[str, str]] = {
    # mapping: lowercase substring → coarse category for cache key
    "engineer": "tech",
    "developer": "tech",
    "designer": "tech",
    "artist": "arts",
    "musician": "arts",
    "writer": "arts",
    "banker": "finance",
    "trader": "finance",
    "analyst": "finance",
    "nurse": "healthcare",
    "doctor": "healthcare",
    "student": "student",
    "barista": "service",
    "server": "service",
    "retail": "service",
}
"""Coarse occupation categorization for backstory cache key.

Original full string preserved in profile.occupation; this is for cache bucketing only.
Prior values: none (new in Spec 213).
Rationale: 6 categories balance cache hit ratio vs persona variety. Default: 'other'.
"""


# ---------------------------------------------------------------------------
# Bucket helpers (module-private per spec FR-3 step 3)
# ---------------------------------------------------------------------------


def _age_bucket(age: int | None) -> str:
    """Map age to bucket label per AGE_BUCKETS.

    Returns 'unknown' for ``None`` input and for any age outside the
    AGE_BUCKETS range (18–99 inclusive).

    Invariant: in the production path, ``age`` is validated upstream by
    ``OnboardingV2ProfileRequest`` / ``BackstoryPreviewRequest`` (both
    constrain ``Field(ge=18, le=99)``), so out-of-range inputs only occur
    via duck-typed test stubs. Tests verify both below-range (17) and
    above-range (100) both bucket to 'unknown'.
    """
    if age is None:
        return "unknown"
    for low, high, label in AGE_BUCKETS:
        if low <= age <= high:
            return label
    return "unknown"  # outside any bucket


def _occupation_bucket(occupation: str | None) -> str:
    """Map occupation string to coarse category per OCCUPATION_CATEGORIES.

    Substring match (lowercased). Returns 'other' if no match, 'unknown' if None.
    """
    if occupation is None:
        return "unknown"
    occ_lower = occupation.lower()
    for substring, category in OCCUPATION_CATEGORIES.items():
        if substring in occ_lower:
            return category
    return "other"


# ---------------------------------------------------------------------------
# Cache-key computation (public — used by facade + preview endpoint)
# ---------------------------------------------------------------------------


def compute_backstory_cache_key(profile: object) -> str:
    """Deterministic cache key for backstory generation.

    Format: 'city|scene|darkness|life_stage|interest|age_bucket|occupation_bucket'
    with 'unknown' substituted for None values. City normalized to lowercase.

    ``profile`` is duck-typed: any object exposing ``city``, ``social_scene``,
    ``darkness_level``, ``life_stage``, ``interest``, ``age``, ``occupation``
    satisfies the contract. This keeps ``tuning.py`` import-free and lets the
    function be reused by the facade (FR-3), the preview endpoint (FR-4a),
    and tests without a Pydantic dependency.

    Both call sites (facade + preview endpoint) compute the same key for the
    same logical profile; cache coherence depends on it.
    """
    city = (getattr(profile, "city", None) or "unknown").lower()
    scene = getattr(profile, "social_scene", None) or "unknown"
    # None darkness → "unknown" (matches docstring promise and keeps the key
    # from ever containing the literal string "None").
    darkness_raw = getattr(profile, "darkness_level", None)
    darkness = str(darkness_raw) if darkness_raw is not None else "unknown"
    life_stage = getattr(profile, "life_stage", None) or "unknown"
    interest = (getattr(profile, "interest", None) or "unknown").lower()
    age_bkt = _age_bucket(getattr(profile, "age", None))
    occ_bkt = _occupation_bucket(getattr(profile, "occupation", None))
    return f"{city}|{scene}|{darkness}|{life_stage}|{interest}|{age_bkt}|{occ_bkt}"
