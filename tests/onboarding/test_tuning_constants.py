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
    CHAT_COMPLETION_RATE_GATE_N,
    CHAT_COMPLETION_RATE_TOLERANCE_PP,
    CONFIDENCE_CONFIRMATION_THRESHOLD,
    CONVERSE_429_RETRY_AFTER_SEC,
    CONVERSE_DAILY_LLM_CAP_USD,
    CONVERSE_PER_IP_RPM,
    CONVERSE_PER_USER_RPM,
    CONVERSE_TIMEOUT_MS,
    HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC,
    HANDOFF_GREETING_STALE_AFTER_SEC,
    LLM_SOURCE_RATE_GATE_MIN,
    LLM_SOURCE_RATE_GATE_N,
    MIN_USER_AGE,
    NIKITA_REPLY_MAX_CHARS,
    OCCUPATION_CATEGORIES,
    ONBOARDING_FORBIDDEN_PHRASES,
    ONBOARDING_INPUT_MAX_CHARS,
    PERSONA_DRIFT_COSINE_MIN,
    PERSONA_DRIFT_FEATURE_TOLERANCE,
    PERSONA_DRIFT_SEED_SAMPLES,
    PIPELINE_GATE_MAX_WAIT_S,
    PIPELINE_GATE_POLL_INTERVAL_S,
    PREVIEW_RATE_LIMIT_PER_MIN,
    STRICTMODE_GUARD_MS,
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


# ---------------------------------------------------------------------------
# Spec 214 FR-11d — /converse endpoint constants (AC-T2.1.1, AC-T2.1.2)
# ---------------------------------------------------------------------------


class TestSpec214ConverseConstants:
    """Regression guards for the 22 FR-11d tuning constants (Spec 214 + GH #378).

    Each constant is asserted (value + type) so accidental tuning drift
    fails a test rather than silently shipping. Matches the audit table in
    ``specs/214-portal-onboarding-wizard/technical-spec.md`` §10. Count grew
    from 19 to 22 when GH #378 split CONVERSE_TIMEOUT_MS into warm/cold
    (adding CONVERSE_TIMEOUT_MS_WARM, _COLD, and CONVERSE_COLD_WARMUP_WINDOW_SEC).
    """

    def test_onboarding_input_max_chars(self):
        assert ONBOARDING_INPUT_MAX_CHARS == 500
        assert isinstance(ONBOARDING_INPUT_MAX_CHARS, int)

    def test_nikita_reply_max_chars(self):
        assert NIKITA_REPLY_MAX_CHARS == 140
        assert isinstance(NIKITA_REPLY_MAX_CHARS, int)

    def test_converse_per_user_rpm(self):
        assert CONVERSE_PER_USER_RPM == 20
        assert isinstance(CONVERSE_PER_USER_RPM, int)

    def test_converse_per_ip_rpm(self):
        assert CONVERSE_PER_IP_RPM == 30
        assert isinstance(CONVERSE_PER_IP_RPM, int)

    def test_converse_daily_llm_cap_usd(self):
        assert CONVERSE_DAILY_LLM_CAP_USD == 2.00
        assert isinstance(CONVERSE_DAILY_LLM_CAP_USD, float)

    def test_converse_timeout_ms(self):
        # GH #378: legacy alias retained, now equal to the warm value
        # (8000 ms). Cold/warm split lives in CONVERSE_TIMEOUT_MS_WARM and
        # CONVERSE_TIMEOUT_MS_COLD; new code should use get_converse_timeout_ms().
        assert CONVERSE_TIMEOUT_MS == tuning.CONVERSE_TIMEOUT_MS_WARM
        assert isinstance(CONVERSE_TIMEOUT_MS, int)

    def test_converse_429_retry_after_sec(self):
        assert CONVERSE_429_RETRY_AFTER_SEC == 30
        assert isinstance(CONVERSE_429_RETRY_AFTER_SEC, int)

    def test_confidence_confirmation_threshold(self):
        assert CONFIDENCE_CONFIRMATION_THRESHOLD == 0.85
        assert isinstance(CONFIDENCE_CONFIRMATION_THRESHOLD, float)

    def test_min_user_age(self):
        assert MIN_USER_AGE == 18
        assert isinstance(MIN_USER_AGE, int)

    def test_strictmode_guard_ms(self):
        assert STRICTMODE_GUARD_MS == 50
        assert isinstance(STRICTMODE_GUARD_MS, int)

    def test_handoff_greeting_backstop_interval_sec(self):
        assert HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC == 60
        assert isinstance(HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC, int)

    def test_handoff_greeting_stale_after_sec(self):
        assert HANDOFF_GREETING_STALE_AFTER_SEC == 30
        assert isinstance(HANDOFF_GREETING_STALE_AFTER_SEC, int)

    def test_persona_drift_feature_tolerance(self):
        assert PERSONA_DRIFT_FEATURE_TOLERANCE == 0.15
        assert isinstance(PERSONA_DRIFT_FEATURE_TOLERANCE, float)

    def test_persona_drift_cosine_min(self):
        assert PERSONA_DRIFT_COSINE_MIN == 0.70
        assert isinstance(PERSONA_DRIFT_COSINE_MIN, float)

    def test_persona_drift_seed_samples(self):
        assert PERSONA_DRIFT_SEED_SAMPLES == 20
        assert isinstance(PERSONA_DRIFT_SEED_SAMPLES, int)

    def test_llm_source_rate_gate_n(self):
        assert LLM_SOURCE_RATE_GATE_N == 100
        assert isinstance(LLM_SOURCE_RATE_GATE_N, int)

    def test_llm_source_rate_gate_min(self):
        assert LLM_SOURCE_RATE_GATE_MIN == 0.90
        assert isinstance(LLM_SOURCE_RATE_GATE_MIN, float)

    def test_chat_completion_rate_tolerance_pp(self):
        assert CHAT_COMPLETION_RATE_TOLERANCE_PP == 5
        assert isinstance(CHAT_COMPLETION_RATE_TOLERANCE_PP, int)

    def test_chat_completion_rate_gate_n(self):
        assert CHAT_COMPLETION_RATE_GATE_N == 50
        assert isinstance(CHAT_COMPLETION_RATE_GATE_N, int)

    def test_all_19_constants_present_and_typed(self):
        """AC-T2.1.1: all 19 FR-11d constants exist with ``Final[...]`` types.

        Module-level ``__annotations__`` preserves the ``Final[...]`` types
        per PEP 526; each constant must appear with a concrete type.
        """
        expected = {
            "ONBOARDING_INPUT_MAX_CHARS": int,
            "NIKITA_REPLY_MAX_CHARS": int,
            "CONVERSE_PER_USER_RPM": int,
            "CONVERSE_PER_IP_RPM": int,
            "CONVERSE_DAILY_LLM_CAP_USD": float,
            "CONVERSE_TIMEOUT_MS": int,
            "CONVERSE_TIMEOUT_MS_WARM": int,
            "CONVERSE_TIMEOUT_MS_COLD": int,
            "CONVERSE_COLD_WARMUP_WINDOW_SEC": float,
            "CONVERSE_429_RETRY_AFTER_SEC": int,
            "CONFIDENCE_CONFIRMATION_THRESHOLD": float,
            "MIN_USER_AGE": int,
            "STRICTMODE_GUARD_MS": int,
            "HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC": int,
            "HANDOFF_GREETING_STALE_AFTER_SEC": int,
            "PERSONA_DRIFT_FEATURE_TOLERANCE": float,
            "PERSONA_DRIFT_COSINE_MIN": float,
            "PERSONA_DRIFT_SEED_SAMPLES": int,
            "LLM_SOURCE_RATE_GATE_N": int,
            "LLM_SOURCE_RATE_GATE_MIN": float,
            "CHAT_COMPLETION_RATE_TOLERANCE_PP": int,
            "CHAT_COMPLETION_RATE_GATE_N": int,
        }
        assert len(expected) == 22
        for name, expected_type in expected.items():
            assert hasattr(tuning, name), f"missing constant {name}"
            value = getattr(tuning, name)
            assert isinstance(value, expected_type), (
                f"{name} expected {expected_type} got {type(value)}"
            )

    def test_forbidden_phrases_minimum_length(self):
        """AC-T2.1.2: ≥12 forbidden-phrase entries."""
        assert isinstance(ONBOARDING_FORBIDDEN_PHRASES, tuple)
        assert len(ONBOARDING_FORBIDDEN_PHRASES) >= 12, (
            f"ONBOARDING_FORBIDDEN_PHRASES has "
            f"{len(ONBOARDING_FORBIDDEN_PHRASES)} entries; AC-T2.1.2 requires ≥12"
        )
        for phrase in ONBOARDING_FORBIDDEN_PHRASES:
            assert isinstance(phrase, str)
            assert phrase, "empty forbidden phrase not allowed"


class TestConverseTimeoutColdWarmSplit:
    """GH #378 regression guards for the cold/warm /converse timeout split.

    Walk P (2026-04-21) observed every wizard turn timing out at the prior
    2500ms ceiling because real LLM calls take ~6s on warm Cloud Run and
    cold-start adds another 5-15s. The single-value timeout was split into
    a warm budget (8s) and a cold budget (30s, used for the first
    CONVERSE_COLD_WARMUP_WINDOW_SEC seconds of process life).
    """

    def test_warm_timeout_at_least_5_seconds(self):
        """Warm timeout must accommodate observed real LLM latency.

        Walk P logs showed warm-instance request taking ~6s end-to-end with
        ~2.5s LLM portion; agent.run timeout must allow at least 5s for the
        LLM proper. 5000 ms is the absolute floor; current value (8000 ms)
        gives 60% headroom for the long tail.
        """
        assert tuning.CONVERSE_TIMEOUT_MS_WARM >= 5000, (
            f"CONVERSE_TIMEOUT_MS_WARM={tuning.CONVERSE_TIMEOUT_MS_WARM} ms "
            f"is below the 5000 ms empirical floor (Walk P 2026-04-21). "
            f"Real warm LLM calls take ~6s end-to-end."
        )

    def test_cold_timeout_strictly_greater_than_warm(self):
        """Cold > warm by definition. Otherwise the split is pointless."""
        assert tuning.CONVERSE_TIMEOUT_MS_COLD > tuning.CONVERSE_TIMEOUT_MS_WARM, (
            "CONVERSE_TIMEOUT_MS_COLD must be > _WARM; otherwise the cold "
            "branch in get_converse_timeout_ms() is dead."
        )

    def test_cold_timeout_at_least_15_seconds(self):
        """Cold timeout must absorb Cloud Run cold-start (5-15s) + warm budget.

        15s is the minimum reasonable value; current default (30000 ms)
        gives ample headroom for the worst-case cold-start tail.
        """
        assert tuning.CONVERSE_TIMEOUT_MS_COLD >= 15000, (
            f"CONVERSE_TIMEOUT_MS_COLD={tuning.CONVERSE_TIMEOUT_MS_COLD} ms "
            f"is below the 15000 ms minimum to absorb Cloud Run cold-start."
        )

    def test_warmup_window_positive(self):
        """The cold→warm transition window must be > 0."""
        assert tuning.CONVERSE_COLD_WARMUP_WINDOW_SEC > 0, (
            "CONVERSE_COLD_WARMUP_WINDOW_SEC must be positive; otherwise "
            "the cold branch never fires."
        )

    def test_legacy_alias_equals_warm(self):
        """The deprecated CONVERSE_TIMEOUT_MS alias must match _WARM.

        Code that still imports the legacy name should get the steady-state
        (warm) value, not the cold one — cold is an opt-in via the helper.
        """
        assert tuning.CONVERSE_TIMEOUT_MS == tuning.CONVERSE_TIMEOUT_MS_WARM


class TestGetConverseTimeoutMs:
    """Behavior of the cold/warm helper at runtime.

    These tests use the helper's ``now`` DI parameter to simulate any
    process-uptime window, so the module-level ``_PROCESS_START_MONOTONIC``
    global is never mutated. That keeps the tests isolation-safe under
    pytest-xdist and removes the need for a ``try/finally`` restore dance.
    """

    def test_returns_warm_after_warmup_window(self):
        """After the warmup window, the helper returns the warm value."""
        from nikita.api.routes import portal_onboarding

        # now = start + (warmup + 1s) → uptime > warmup → warm branch.
        far_future = (
            portal_onboarding._PROCESS_START_MONOTONIC
            + tuning.CONVERSE_COLD_WARMUP_WINDOW_SEC
            + 1.0
        )
        assert (
            portal_onboarding.get_converse_timeout_ms(now=far_future)
            == tuning.CONVERSE_TIMEOUT_MS_WARM
        )

    def test_returns_cold_within_warmup_window(self):
        """During the warmup window, the helper returns the cold value."""
        from nikita.api.routes import portal_onboarding

        # now = start + 0.1s → uptime < warmup → cold branch.
        just_started = portal_onboarding._PROCESS_START_MONOTONIC + 0.1
        assert (
            portal_onboarding.get_converse_timeout_ms(now=just_started)
            == tuning.CONVERSE_TIMEOUT_MS_COLD
        )

    def test_returns_cold_at_warmup_boundary(self):
        """At exactly ``_PROCESS_START + warmup``, the helper returns warm.

        The boundary condition matters: the helper uses ``<`` (strict), so
        uptime equal to the warmup window crosses into the warm branch.
        This guards against an accidental flip to ``<=`` which would leave
        the instance on the COLD budget one tick longer than intended.
        """
        from nikita.api.routes import portal_onboarding

        at_boundary = (
            portal_onboarding._PROCESS_START_MONOTONIC
            + tuning.CONVERSE_COLD_WARMUP_WINDOW_SEC
        )
        assert (
            portal_onboarding.get_converse_timeout_ms(now=at_boundary)
            == tuning.CONVERSE_TIMEOUT_MS_WARM
        )
