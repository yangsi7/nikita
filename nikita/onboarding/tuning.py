"""Tuning constants for Spec 213 onboarding backend (FR-4).

Domain-specific timeouts, cache TTLs, rate limits, and bucket mappings for
the portal onboarding handoff path.

CONSTRAINT (FR-4 isolation): This module MUST NOT import from
nikita.engine.constants. Onboarding is a distinct domain from the scoring engine
and pipeline stages; sharing constants would couple unrelated concerns.

Per .claude/rules/tuning-constants.md, every constant has:
  - Current value
  - Prior values with driving PR/GH issue
  - One-line rationale for *this* value

Regression guards in tests/onboarding/test_tuning_constants.py.
"""

from __future__ import annotations

from typing import Final

from nikita.onboarding.models import UserOnboardingProfile

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
Rationale: covers Cloud Run cold-start (5s) + venue research (15s) + safety margin.
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
    """Map age to bucket label per AGE_BUCKETS. Returns 'unknown' if None."""
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


def compute_backstory_cache_key(profile: UserOnboardingProfile) -> str:
    """Deterministic cache key for backstory generation.

    Format: 'city|scene|darkness|life_stage|interest|age_bucket|occupation_bucket'
    with 'unknown' substituted for None values. City normalized to lowercase.

    This function is canonical. Both the facade (FR-3) and the preview endpoint
    (FR-4a) compute the same key for the same profile; cache coherence depends on it.
    """
    city = (profile.city or "unknown").lower()
    scene = profile.social_scene or "unknown"
    darkness = str(profile.darkness_level)
    life_stage = profile.life_stage or "unknown"
    interest = (profile.interest or "unknown").lower()
    age_bkt = _age_bucket(profile.age)
    occ_bkt = _occupation_bucket(profile.occupation)
    return f"{city}|{scene}|{darkness}|{life_stage}|{interest}|{age_bkt}|{occ_bkt}"
