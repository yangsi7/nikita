"""Regression guards for Spec 213 tuning constants (FR-4).

Per .claude/rules/tuning-constants.md: every tuning constant needs a test
asserting its exact current value + a comment referencing the driving GH issue.

Compound constants (tuple-of-tuples, dict) use deep-equality assertion AND
explicit boundary tests (inclusive edges).
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
from typing import Final

import pytest

from nikita.onboarding import tuning
from nikita.onboarding.tuning import (
    AGE_BUCKETS,
    BACKSTORY_CACHE_TTL_DAYS,
    BACKSTORY_GEN_TIMEOUT_S,
    BACKSTORY_HOOK_PROBABILITY,
    OCCUPATION_CATEGORIES,
    PIPELINE_GATE_MAX_WAIT_S,
    PIPELINE_GATE_POLL_INTERVAL_S,
    PREVIEW_RATE_LIMIT_PER_MIN,
    VENUE_RESEARCH_TIMEOUT_S,
    _age_bucket,
    _occupation_bucket,
    compute_backstory_cache_key,
)


# ---------------------------------------------------------------------------
# Scalar constants — exact value + type
# ---------------------------------------------------------------------------


class TestScalarConstants:
    """Regression guard: exact value for each tuning constant (GH #213)."""

    def test_venue_research_timeout_s(self):
        assert VENUE_RESEARCH_TIMEOUT_S == 15.0
        assert isinstance(VENUE_RESEARCH_TIMEOUT_S, float)

    def test_backstory_gen_timeout_s(self):
        assert BACKSTORY_GEN_TIMEOUT_S == 20.0
        assert isinstance(BACKSTORY_GEN_TIMEOUT_S, float)

    def test_pipeline_gate_poll_interval_s(self):
        assert PIPELINE_GATE_POLL_INTERVAL_S == 2.0
        assert isinstance(PIPELINE_GATE_POLL_INTERVAL_S, float)

    def test_pipeline_gate_max_wait_s(self):
        assert PIPELINE_GATE_MAX_WAIT_S == 20.0
        assert isinstance(PIPELINE_GATE_MAX_WAIT_S, float)

    def test_backstory_cache_ttl_days(self):
        assert BACKSTORY_CACHE_TTL_DAYS == 30
        assert isinstance(BACKSTORY_CACHE_TTL_DAYS, int)

    def test_backstory_hook_probability(self):
        assert BACKSTORY_HOOK_PROBABILITY == 0.50
        assert 0.0 <= BACKSTORY_HOOK_PROBABILITY <= 1.0

    def test_preview_rate_limit_per_min(self):
        assert PREVIEW_RATE_LIMIT_PER_MIN == 5
        assert isinstance(PREVIEW_RATE_LIMIT_PER_MIN, int)


class TestTimeoutRelationalInvariants:
    """Cross-constant invariants — catch silent drift when individual
    timeouts are tuned without considering their relationships (GH #213).

    Added in QA iter-6 to guard the docstring claim that
    ``PIPELINE_GATE_MAX_WAIT_S`` bounds both service timeouts. If any future
    edit raises BACKSTORY_GEN_TIMEOUT_S or VENUE_RESEARCH_TIMEOUT_S above
    20s without updating MAX_WAIT, these assertions fail — forcing the
    author to reconcile the budget.
    """

    def test_poll_interval_smaller_than_max_wait(self):
        """Portal must poll at least once before max-wait expires."""
        assert PIPELINE_GATE_POLL_INTERVAL_S < PIPELINE_GATE_MAX_WAIT_S

    def test_max_wait_at_least_backstory_timeout(self):
        """MAX_WAIT must bound BACKSTORY_GEN_TIMEOUT (the dominant service)
        so the portal does not unblock before the slower service can return
        a concrete result on the happy path."""
        assert PIPELINE_GATE_MAX_WAIT_S >= BACKSTORY_GEN_TIMEOUT_S

    def test_max_wait_at_least_venue_research_timeout(self):
        """MAX_WAIT must also bound VENUE_RESEARCH_TIMEOUT for the same
        reason — parallel fanout means the slower of the two defines the
        wait budget."""
        assert PIPELINE_GATE_MAX_WAIT_S >= VENUE_RESEARCH_TIMEOUT_S


# ---------------------------------------------------------------------------
# Compound constants — deep equality + boundary tests
# ---------------------------------------------------------------------------


class TestAgeBuckets:
    """Regression + boundary guards for AGE_BUCKETS (GH #213)."""

    def test_age_buckets_exact_value(self):
        """Deep equality on the entire tuple-of-tuples."""
        assert AGE_BUCKETS == (
            (18, 24, "young_adult"),
            (25, 34, "twenties"),
            (35, 49, "midlife"),
            (50, 99, "experienced"),
        )

    def test_age_buckets_no_gaps(self):
        """Adjacent buckets are contiguous (high+1 == next low)."""
        for (_, high, _), (low, _, _) in zip(AGE_BUCKETS, AGE_BUCKETS[1:]):
            assert low == high + 1

    def test_age_buckets_non_overlapping(self):
        """All ranges strictly ordered."""
        prev_high = -1
        for low, high, _ in AGE_BUCKETS:
            assert low > prev_high
            prev_high = high


class TestAgeToBucket:
    """Inclusive-edge boundary tests for _age_bucket."""

    @pytest.mark.parametrize(
        "age, expected",
        [
            (18, "young_adult"),  # lower edge
            (24, "young_adult"),  # upper edge of young_adult
            (25, "twenties"),  # lower edge of twenties (off-by-one guard)
            (34, "twenties"),
            (35, "midlife"),
            (49, "midlife"),
            (50, "experienced"),
            (99, "experienced"),  # upper edge of experienced
        ],
    )
    def test_boundary_inclusive(self, age: int, expected: str):
        assert _age_bucket(age) == expected

    def test_none_returns_unknown(self):
        assert _age_bucket(None) == "unknown"

    def test_below_range_returns_unknown(self):
        assert _age_bucket(17) == "unknown"

    def test_above_range_returns_unknown(self):
        assert _age_bucket(100) == "unknown"


class TestOccupationCategories:
    """Regression guard for OCCUPATION_CATEGORIES dict (GH #213)."""

    def test_occupation_categories_exact_value(self):
        """Deep equality on the full mapping."""
        assert OCCUPATION_CATEGORIES == {
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


class TestOccupationToBucket:
    """Substring-match behavior of _occupation_bucket."""

    @pytest.mark.parametrize(
        "occupation, expected",
        [
            ("Software Engineer", "tech"),
            ("Senior developer", "tech"),
            ("Visual Designer", "tech"),
            ("Freelance artist", "arts"),
            ("Jazz Musician", "arts"),
            ("Investment Banker", "finance"),
            ("Day trader", "finance"),
            ("Data analyst", "finance"),
            ("Registered nurse", "healthcare"),
            ("GP Doctor", "healthcare"),
            ("PhD student", "student"),
            ("Coffee barista", "service"),
            ("Waiter/server", "service"),
            ("Retail assistant", "service"),
        ],
    )
    def test_substring_match(self, occupation: str, expected: str):
        assert _occupation_bucket(occupation) == expected

    def test_none_returns_unknown(self):
        assert _occupation_bucket(None) == "unknown"

    def test_unknown_string_returns_other(self):
        """Occupations with no matching substring bucket into 'other'."""
        assert _occupation_bucket("Astronaut") == "other"
        assert _occupation_bucket("Chef") == "other"

    def test_empty_string_returns_other(self):
        """Empty string has no substring matches → 'other' (NOT 'unknown' reserved for None)."""
        assert _occupation_bucket("") == "other"


# ---------------------------------------------------------------------------
# compute_backstory_cache_key — determinism + shape
# ---------------------------------------------------------------------------


class TestComputeBackstoryCacheKey:
    """Validates cache key determinism + bucketing behavior."""

    def _make_profile(
        self,
        city: str | None = "Berlin",
        social_scene: str | None = "techno",
        darkness_level: int | None = 3,
        life_stage: str | None = "tech",
        interest: str | None = "music",
        age: int | None = 27,
        occupation: str | None = "Software Engineer",
    ) -> object:
        """Builds a SimpleNamespace matching UserOnboardingProfile duck-type."""
        return SimpleNamespace(
            city=city,
            social_scene=social_scene,
            darkness_level=darkness_level,
            life_stage=life_stage,
            interest=interest,
            age=age,
            occupation=occupation,
        )

    def test_deterministic_same_inputs_same_key(self):
        """Same inputs → same key (required for cache coherence FR-4a)."""
        p1 = self._make_profile()
        p2 = self._make_profile()
        assert compute_backstory_cache_key(p1) == compute_backstory_cache_key(p2)

    def test_different_city_different_key(self):
        k1 = compute_backstory_cache_key(self._make_profile(city="Berlin"))
        k2 = compute_backstory_cache_key(self._make_profile(city="Paris"))
        assert k1 != k2

    def test_city_case_insensitive(self):
        """City is lowercased for stable bucketing."""
        k1 = compute_backstory_cache_key(self._make_profile(city="Berlin"))
        k2 = compute_backstory_cache_key(self._make_profile(city="BERLIN"))
        k3 = compute_backstory_cache_key(self._make_profile(city="berlin"))
        assert k1 == k2 == k3

    def test_none_fields_bucket_to_unknown(self):
        """Missing fields substitute 'unknown'/'other' — never the raw string 'None'.

        Covers every field that can legitimately be None on an in-progress
        Pydantic profile, including ``darkness_level`` (required on submit but
        may be absent on duck-typed stand-ins).
        """
        key = compute_backstory_cache_key(
            self._make_profile(
                city=None,
                social_scene=None,
                darkness_level=None,
                life_stage=None,
                interest=None,
                age=None,
                occupation=None,
            )
        )
        assert isinstance(key, str)
        assert "unknown" in key
        # Regression guard: str(None) == "None" must never leak into the key.
        # Triggers if a None-check is accidentally removed from any bucket
        # helper or from the f-string substitution.
        assert "None" not in key
        # Shape guard: 7 parts separated by '|' — 6 delimiters regardless of
        # whether inputs are None.
        assert key.count("|") == 6

    def test_darkness_level_none_uses_unknown(self):
        """darkness_level=None maps to 'unknown' in the key, NOT 'None'.

        Explicit regression: the docstring on compute_backstory_cache_key
        promises 'unknown substituted for None values' — darkness_level is
        the only non-bucketed field in the key, so it needs its own targeted
        guard beyond the all-None case.
        """
        key = compute_backstory_cache_key(self._make_profile(darkness_level=None))
        parts = key.split("|")
        assert parts[2] == "unknown"
        assert "None" not in key

    def test_age_bucketing_applied(self):
        """Different ages in same bucket → same key portion; different buckets → different key."""
        k25 = compute_backstory_cache_key(self._make_profile(age=25))
        k30 = compute_backstory_cache_key(self._make_profile(age=30))
        # Both in 'twenties' bucket
        assert k25 == k30

        k50 = compute_backstory_cache_key(self._make_profile(age=50))
        # Different bucket
        assert k25 != k50

    def test_occupation_bucketing_applied(self):
        """Same occupation category → same key."""
        k_eng = compute_backstory_cache_key(self._make_profile(occupation="Senior Engineer"))
        k_dev = compute_backstory_cache_key(self._make_profile(occupation="Junior Developer"))
        # Both bucket to 'tech'
        assert k_eng == k_dev

    def test_returns_string(self):
        assert isinstance(compute_backstory_cache_key(self._make_profile()), str)

    def test_format_delimiter(self):
        """Key uses '|' delimiter per spec FR-3 step 3."""
        key = compute_backstory_cache_key(self._make_profile())
        # Expected format: city|scene|darkness|life_stage|interest|age_bucket|occupation_bucket (7 parts)
        assert key.count("|") == 6


# ---------------------------------------------------------------------------
# Signature test — module namespace compliance
# ---------------------------------------------------------------------------


def test_compute_backstory_cache_key_signature():
    """Asserts compute_backstory_cache_key lives at nikita.onboarding.tuning (per spec FR-4)."""
    assert hasattr(tuning, "compute_backstory_cache_key")
    assert callable(tuning.compute_backstory_cache_key)


def test_module_isolation_imports():
    """FR-4 isolation: tuning.py is a pure constants + pure-function module.

    It MUST NOT import from:
      - nikita.engine.*           (different domain; spec FR-4)
      - nikita.onboarding.models  (would couple constants to Pydantic surface)
      - nikita.db.*               (would couple constants to persistence)

    Inspects the AST rather than source text (module docstring mentions the
    forbidden paths as a negation — 'MUST NOT import' — which would produce a
    false positive on a text-substring match).
    """
    import ast
    import inspect

    forbidden_prefixes = ("nikita.engine", "nikita.db")
    forbidden_exact = {"nikita.onboarding.models"}

    src = inspect.getsource(tuning)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in forbidden_prefixes:
                    assert not alias.name.startswith(prefix), (
                        f"tuning.py imports {alias.name} (FR-4 forbids {prefix}.*)"
                    )
                assert alias.name not in forbidden_exact, (
                    f"tuning.py imports {alias.name} (FR-4 isolation)"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Guard against relative imports (`from . import X` / `from .models import Y`)
            # which would bypass the absolute-path prefix checks. Reject ANY
            # relative import — tuning.py must stay a dependency-free leaf.
            assert node.level == 0, (
                f"tuning.py uses a relative import (level={node.level}) — "
                f"disallowed; module must remain a dependency-free leaf"
            )
            for prefix in forbidden_prefixes:
                assert not module.startswith(prefix), (
                    f"tuning.py imports from {module} (FR-4 forbids {prefix}.*)"
                )
            assert module not in forbidden_exact, (
                f"tuning.py imports from {module} (FR-4 isolation — "
                f"constants module must remain free of domain-model coupling)"
            )
