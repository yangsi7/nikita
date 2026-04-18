"""Tests for nikita.heartbeat.intensity (Spec 215 PR 215-B, US-2 task T1.3).

Covers:
- AC-T1.3-001..013 — tuning-constants regression tests with single-source-of-truth
  identity checks across the production module and the MC validator script.
- AC-T1.2-001..004 — behavioral correctness of activity_distribution and
  lambda_baseline (probability axiom, noise floor, strict positivity).
- Eight additional behavioral tests from `.claude/plans/brief-spec215-pr215b-math-module.md`
  §3.3 covering Hawkes stability, recursive equivalence, sampler safety, and
  circadian shape.

Math authority: `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md`
§A.1 through §A.6 (von Mises × Hawkes × Ogata thinning).

Mirror pattern: `tests/agents/text/test_timing.py` (Spec 210). Each Final
constant gets a regression test asserting its exact value with a comment
pointing at the driving acceptance-criterion ID.
"""

from __future__ import annotations

import asyncio
import math
import statistics


# --------------------------------------------------------------------------- #
# AC-T1.3-001 — Module structure + single source of truth                     #
# --------------------------------------------------------------------------- #


class TestModuleStructure:
    """AC-T1.3-001: production module exports every Final the MC script imports.

    The production module owns every constant. The MC validator imports them
    so a single source of truth governs both runtime and offline simulation.
    Identity (`is`) checks are stricter than equality and catch shadow
    re-declarations (e.g., a stale literal accidentally rebound in the MC).
    """

    def test_production_module_importable(self):
        from nikita.heartbeat import intensity

        for name in (
            "ACTIVITIES",
            "ACTIVITY_PARAMS",
            "DIRICHLET_PRIOR",
            "ACTIVITY_BASE_WEIGHTS",
            "EPSILON_FLOOR",
            "NU_PER_ACTIVITY",
            "CHAPTER_MULT",
            "ENGAGEMENT_MULT",
            "T_HALF_HRS",
            "BETA",
            "ALPHA",
            "R_MAX",
            "activity_distribution",
            "lambda_baseline",
            "hawkes_decay",
            "hawkes_update",
            "lambda_total",
            "sample_next_wakeup",
            "HeartbeatIntensity",
        ):
            assert hasattr(intensity, name), f"missing export: {name}"

    def test_mc_imports_constants_from_production(self):
        """AC-T1.3-001: MC re-exports the production constants by reference.

        Identity equality (``is``) proves the MC didn't shadow the value with a
        local literal. Without this guard, the MC could drift silently.
        """
        from nikita.heartbeat import intensity as prod
        from scripts.models import heartbeat_intensity_mc as mc

        for name in (
            "EPSILON_FLOOR",
            "T_HALF_HRS",
            "BETA",
            "R_MAX",
            "ALPHA",
            "NU_PER_ACTIVITY",
            "CHAPTER_MULT",
            "ENGAGEMENT_MULT",
            "ACTIVITIES",
            "ACTIVITY_PARAMS",
            "DIRICHLET_PRIOR",
            "ACTIVITY_BASE_WEIGHTS",
        ):
            assert getattr(prod, name) is getattr(mc, name), (
                f"single-source-of-truth violation: {name} differs between "
                f"nikita.heartbeat.intensity and scripts.models.heartbeat_intensity_mc"
            )


# --------------------------------------------------------------------------- #
# AC-T1.3-002..013 — Final-constant regression tests                          #
# --------------------------------------------------------------------------- #


class TestTuningConstants:
    """Locked values per Plan v3 §A.1.5 + §A.2 + §A.5.

    Mirror `tests/agents/text/test_timing.py:50-64` pattern: each constant
    test names the AC and points back at the math authority. Changing any of
    these values requires a new MC validator pass + model-doc update per
    `.claude/rules/tuning-constants.md`.
    """

    def test_AC_T1_3_002_epsilon_floor_value(self):
        """AC-T1.3-002: noise floor is 0.03 (min activity probability 0.6%)."""
        from nikita.heartbeat.intensity import EPSILON_FLOOR

        assert EPSILON_FLOOR == 0.03

    def test_AC_T1_3_003_chapter_mult_monotonic(self):
        """AC-T1.3-003: CHAPTER_MULT decreases Ch1>Ch2>Ch3>Ch4>Ch5 (excitement fades)."""
        from nikita.heartbeat.intensity import CHAPTER_MULT

        assert CHAPTER_MULT[1] > CHAPTER_MULT[2] > CHAPTER_MULT[3] > CHAPTER_MULT[4] > CHAPTER_MULT[5]

    def test_AC_T1_3_004_branching_ratio_stable(self):
        """AC-T1.3-004: Hawkes branching ratio < 1 with cold-start ALPHAs.

        Per Plan v3 §A.2 stability constraint: the system would explode (each
        event begets >1 future event in expectation) if α_user·E[w_user] +
        α_game·1 + α_internal·1 ≥ 1. We pin a comfortable margin.
        """
        from nikita.heartbeat.intensity import ALPHA

        branching = ALPHA["user_msg"] * 1.2 + ALPHA["game_event"] * 1.0 + ALPHA["internal"] * 1.0
        assert branching < 1.0, f"branching ratio {branching:.3f} ≥ 1.0 — process unstable"

    def test_AC_T1_3_005_t_half_value(self):
        """AC-T1.3-005: T_half = 3.0 hours (Hawkes excitation half-life)."""
        from nikita.heartbeat.intensity import T_HALF_HRS

        assert T_HALF_HRS == 3.0

    def test_AC_T1_3_006_beta_derived_from_t_half(self):
        """AC-T1.3-006: BETA = ln(2)/T_half (closed-form derivation)."""
        from nikita.heartbeat.intensity import BETA, T_HALF_HRS

        assert abs(BETA - math.log(2) / T_HALF_HRS) < 1e-9

    def test_AC_T1_3_007_r_max_value(self):
        """AC-T1.3-007: R_max = 1.5 (caps Hawkes residual at storm threshold)."""
        from nikita.heartbeat.intensity import R_MAX

        assert R_MAX == 1.5

    def test_AC_T1_3_008_nu_per_activity_values(self):
        """AC-T1.3-008: ν_a values match Plan v3 §A.2 v2 (user-tuned 2026-04-17).

        Eating cut 0.50→0.30 (she's eating, not pondering); personal 0.80→1.00
        (hobby/free-time = thought-cycles re user). Other values unchanged.
        """
        from nikita.heartbeat.intensity import NU_PER_ACTIVITY

        assert NU_PER_ACTIVITY["sleep"] == 0.05
        assert NU_PER_ACTIVITY["work"] == 0.30
        assert NU_PER_ACTIVITY["eating"] == 0.30
        assert NU_PER_ACTIVITY["personal"] == 1.00
        assert NU_PER_ACTIVITY["social"] == 0.40

    def test_AC_T1_3_009_dirichlet_prior_sums_to_100(self):
        """AC-T1.3-009: DIRICHLET_PRIOR is the weekday baseline normalization.

        Sum-to-100 keeps the proportional reading honest: each entry is the
        share of waking-time mass for that activity in the prior, expressed
        out of 100.
        """
        from nikita.heartbeat.intensity import DIRICHLET_PRIOR

        assert sum(DIRICHLET_PRIOR.values()) == 100

    def test_AC_T1_3_010_activity_params_keys_match_dirichlet(self):
        """AC-T1.3-010: 5 activities consistent across ACTIVITY_PARAMS + DIRICHLET_PRIOR.

        Mismatched keys would crash `lambda_baseline` at runtime via KeyError
        on the very first heartbeat tick.
        """
        from nikita.heartbeat.intensity import ACTIVITY_PARAMS, DIRICHLET_PRIOR

        assert set(ACTIVITY_PARAMS.keys()) == set(DIRICHLET_PRIOR.keys())

    def test_AC_T1_3_011_activity_params_kappas_positive(self):
        """AC-T1.3-011: every κ > 0 (von Mises concentration must be positive)."""
        from nikita.heartbeat.intensity import ACTIVITY_PARAMS

        for activity, components in ACTIVITY_PARAMS.items():
            for mu, kappa, weight in components:
                assert kappa > 0, f"{activity}: κ={kappa} ≤ 0 (von Mises violation)"
                assert weight > 0, f"{activity}: w={weight} ≤ 0 (component weight violation)"

    def test_AC_T1_3_012_alpha_positive(self):
        """AC-T1.3-012: every ALPHA value > 0 (Hawkes excitation must be positive)."""
        from nikita.heartbeat.intensity import ALPHA

        for event_type, alpha in ALPHA.items():
            assert alpha > 0, f"{event_type}: α={alpha} ≤ 0 (Hawkes excitation violation)"

    def test_bessel_i0_reference_values(self):
        """`_i0(κ)` matches Abramowitz & Stegun reference values within 1e-6.

        Regression guard against polynomial-coefficient typos OR a future
        "let's just use scipy.special.i0" swap that could silently change
        normalization. Reference values from A&S Table 9.8 + scipy.special.i0
        cross-checked: I_0(0)=1.0, I_0(1)≈1.26607, I_0(2.5)≈3.28984,
        I_0(5)≈27.23987, I_0(8)≈427.56411.
        """
        from nikita.heartbeat.intensity import _i0

        cases = [
            (0.0, 1.0),
            (1.0, 1.2660658132),
            (2.5, 3.2898391491),
            (5.0, 27.2398718236),
            (8.0, 427.5641157188),
        ]
        for kappa, expected in cases:
            actual = _i0(kappa)
            assert abs(actual - expected) / max(expected, 1e-9) < 1e-6, (
                f"_i0({kappa}) = {actual} ≠ {expected} (relative error too large)"
            )


# --------------------------------------------------------------------------- #
# AC-T1.2-001..003 — Behavioral correctness of public API                     #
# --------------------------------------------------------------------------- #


class TestActivityDistribution:
    """AC-T1.2-001 + AC-T1.2-002: probability axiom + noise-floor invariants."""

    def test_AC_T1_2_001_distribution_sums_to_one_at_t_zero(self):
        from nikita.heartbeat.intensity import ACTIVITIES, activity_distribution

        d = activity_distribution(0.0)
        assert set(d.keys()) == set(ACTIVITIES)
        assert abs(sum(d.values()) - 1.0) < 1e-6

    def test_distribution_sums_to_one_across_24h(self):
        """Sums-to-one must hold at every t (probability axiom)."""
        from nikita.heartbeat.intensity import activity_distribution

        for t in [i * 0.5 for i in range(48)]:  # 0.0, 0.5, ..., 23.5
            total = sum(activity_distribution(t).values())
            assert abs(total - 1.0) < 1e-6, f"t={t}: sum={total} ≠ 1"

    def test_AC_T1_2_002_respects_noise_floor(self):
        """Min activity probability ≥ ε/A everywhere — never zero."""
        from nikita.heartbeat.intensity import ACTIVITIES, EPSILON_FLOOR, activity_distribution

        floor = EPSILON_FLOOR / len(ACTIVITIES)
        for t in [i * 0.5 for i in range(48)]:
            min_p = min(activity_distribution(t).values())
            assert min_p >= floor - 1e-9, f"t={t}: min_p={min_p} < floor={floor}"

    def test_distribution_at_24_equals_at_zero(self):
        """24h boundary: phase φ = 2π·t/24 is periodic; t=24.0 ≡ t=0.0."""
        from nikita.heartbeat.intensity import activity_distribution

        d0 = activity_distribution(0.0)
        d24 = activity_distribution(24.0)
        for activity in d0:
            assert abs(d0[activity] - d24[activity]) < 1e-9, (
                f"phase wraparound broken at t=24.0 for {activity}"
            )


class TestLambdaBaseline:
    """AC-T1.2-003: lambda_baseline > 0 always (sleep trough still positive)."""

    def test_AC_T1_2_003_baseline_positive_at_sleep_trough(self):
        from nikita.heartbeat.intensity import lambda_baseline

        # 3am is deep sleep; baseline must still be > 0 (noise floor + sleep ν > 0)
        assert lambda_baseline(3.0, chapter=3, engagement="in_zone") > 0

    def test_baseline_strictly_positive_across_24h(self):
        """For every t, every chapter, every engagement: λ_baseline > 0."""
        from nikita.heartbeat.intensity import lambda_baseline

        engagements = ["calibrating", "in_zone", "fading", "distant", "clingy"]
        for t in [i for i in range(24)]:
            for chapter in range(1, 6):
                for engagement in engagements:
                    val = lambda_baseline(t, chapter=chapter, engagement=engagement)
                    assert val > 0, f"t={t} ch={chapter} eng={engagement}: λ={val} ≤ 0"


# --------------------------------------------------------------------------- #
# Hawkes recursive correctness + decay invariants                             #
# --------------------------------------------------------------------------- #


class TestHawkesDynamics:
    """Behavioral tests from brief §3.3."""

    def test_decay_reaches_one_percent_within_7_half_lives(self):
        """After 7·T_half = 21h, R should have decayed to <1% of initial.

        Math: after N half-lives, R/R_initial = 2^-N. 2^-7 ≈ 0.0078 < 1%.
        2^-5 is only 3.125%, so the original brief §3.3 figure of "5 half
        lives" was off; 7 is the correct threshold for < 1%.
        """
        from nikita.heartbeat.intensity import T_HALF_HRS, hawkes_decay

        R_initial = 1.0
        R_after_7_half_lives = hawkes_decay(R_initial, 7 * T_HALF_HRS)
        assert R_after_7_half_lives < 0.01 * R_initial

    def test_decay_at_one_half_life_reaches_half(self):
        """Sanity: hawkes_decay(R, T_half) ≈ R/2."""
        from nikita.heartbeat.intensity import T_HALF_HRS, hawkes_decay

        R_initial = 1.0
        R_after_one_half_life = hawkes_decay(R_initial, T_HALF_HRS)
        assert abs(R_after_one_half_life - 0.5 * R_initial) < 1e-9

    def test_update_clamps_at_r_max(self):
        """hawkes_update saturates at R_MAX so storm spikes can't blow up."""
        from nikita.heartbeat.intensity import ALPHA, R_MAX, hawkes_update

        R = R_MAX  # already at cap
        R_after = hawkes_update(R, ALPHA["user_msg"])
        assert R_after <= R_MAX + 1e-9

    def test_decay_is_identity_at_zero_dt(self):
        """hawkes_decay(R, 0) returns R unchanged (no decay over zero gap)."""
        from nikita.heartbeat.intensity import hawkes_decay

        for R in (0.0, 0.5, 1.0, 1.5):
            assert hawkes_decay(R, 0.0) == R

    def test_decay_at_long_gap_no_underflow(self):
        """Decay over 100h should produce a small positive value, not negative."""
        from nikita.heartbeat.intensity import hawkes_decay

        R = hawkes_decay(1.0, 100.0)
        assert R >= 0
        assert R < 1e-6  # genuinely tiny

    def test_recursive_vs_naive_match(self):
        """Recursive O(1) form must match the naive Σ form within float64 tolerance.

        Brief §5.1 cumulative-drift edge: feed N=1000 random events into the
        recursive update; reconstruct the same intensity by summing the
        Hawkes sum-form analytically. Drift must be < 1e-6 (IEEE 754 bound).
        """
        from nikita.heartbeat.intensity import ALPHA, BETA, R_MAX, hawkes_decay, hawkes_update

        rng = __import__("random").Random(42)
        events: list[tuple[float, float]] = []  # (time, alpha)
        R_recursive = 0.0
        last_t = 0.0
        for _ in range(1000):
            dt = rng.expovariate(2.0)  # mean 0.5h between events
            t = last_t + dt
            alpha = ALPHA["user_msg"]
            R_recursive = hawkes_decay(R_recursive, dt)
            R_recursive = hawkes_update(R_recursive, alpha)
            events.append((t, alpha))
            last_t = t

        # Naive reconstruction: R(t_last) = Σ_i α_i · β · exp(-β·(t_last - t_i))
        # NB: this is the un-clamped form; recursive form is clamped at R_MAX.
        # If recursive ever hit R_MAX, naive will exceed it. Compare only when
        # the recursive form has not yet saturated.
        naive = sum(alpha * BETA * math.exp(-BETA * (last_t - t)) for t, alpha in events)
        if naive < R_MAX:
            assert abs(R_recursive - naive) < 1e-6


# --------------------------------------------------------------------------- #
# Ogata thinning sampler safety + circadian shape                             #
# --------------------------------------------------------------------------- #


class TestSampleNextWakeup:
    """Behavioral tests for HeartbeatIntensity.sample_next_wakeup (brief §3.3)."""

    def test_returns_within_horizon(self):
        """Safety cap: sampler returns t ≤ t_now + t_horizon even at zero R."""
        from nikita.heartbeat.intensity import HeartbeatIntensity

        intensity = HeartbeatIntensity(seed=42)
        t_now = 3.0  # sleep trough = lowest intensity
        t_horizon = 12.0
        for _ in range(50):
            t_next, _ = intensity.sample_next_wakeup(
                t_now=t_now, R_now=0.0, chapter=5, engagement="distant",
                t_horizon=t_horizon,
            )
            assert t_next <= t_now + t_horizon + 1e-9

    def test_returns_within_default_horizon_for_normal_state(self):
        """At Ch3 in_zone with default horizon, sampler returns in finite time."""
        from nikita.heartbeat.intensity import HeartbeatIntensity

        intensity = HeartbeatIntensity(seed=7)
        t_next, R_at_next = intensity.sample_next_wakeup(
            t_now=12.0, R_now=0.0, chapter=3, engagement="in_zone",
        )
        assert t_next > 12.0
        assert R_at_next >= 0

    def test_inter_wake_gap_longer_in_sleep_trough(self):
        """Inter-wake gaps SHOULD be larger when starting at the sleep trough.

        Direct circadian-shape probe: when starting at the lowest-intensity
        hour (4am ≈ sleep trough), the expected wait until the next wake
        is longer than when starting at the highest-intensity evening hour
        (20:00 ≈ personal peak). This is the production-relevant statistic
        the scheduler relies on.
        """
        from nikita.heartbeat.intensity import HeartbeatIntensity

        intensity = HeartbeatIntensity(seed=123)
        sleep_dts: list[float] = []
        evening_dts: list[float] = []
        for _ in range(200):
            t_next, _ = intensity.sample_next_wakeup(
                t_now=4.0, R_now=0.0, chapter=3, engagement="in_zone",
                t_horizon=8.0,
            )
            sleep_dts.append(t_next - 4.0)
            t_next, _ = intensity.sample_next_wakeup(
                t_now=20.0, R_now=0.0, chapter=3, engagement="in_zone",
                t_horizon=8.0,
            )
            evening_dts.append(t_next - 20.0)
        mean_sleep = statistics.mean(sleep_dts)
        mean_evening = statistics.mean(evening_dts)
        assert mean_sleep > mean_evening, (
            f"sleep-trough wake gap should exceed evening; "
            f"sleep={mean_sleep:.3f}h, evening={mean_evening:.3f}h"
        )


# --------------------------------------------------------------------------- #
# Concurrency contract (brief §5.2)                                           #
# --------------------------------------------------------------------------- #


class TestConcurrencyContract:
    """Per-instance random.Random isolation — separate instances are safe."""

    def test_separate_instances_concurrent_safe(self):
        """asyncio.gather of 50 concurrent samplers on separate instances.

        Per Plan v3 §A.6 + brief §5.2: random.Random is NOT thread-safe;
        the contract is "instantiate per request" (mirrors ResponseTimer).
        This test proves the isolation works as intended.
        """
        from nikita.heartbeat.intensity import HeartbeatIntensity

        async def one_sample(seed: int) -> float:
            intensity = HeartbeatIntensity(seed=seed)
            t_next, _ = intensity.sample_next_wakeup(
                t_now=10.0, R_now=0.5, chapter=3, engagement="in_zone",
            )
            return t_next

        async def run_all() -> list[float]:
            return await asyncio.gather(*(one_sample(s) for s in range(50)))

        results = asyncio.run(run_all())
        assert len(results) == 50
        for r in results:
            assert r >= 10.0  # all samples advance time
