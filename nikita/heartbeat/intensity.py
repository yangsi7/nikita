"""Heartbeat intensity math module for Nikita Heartbeat Engine (Spec 215 v1).

Computes Nikita's instantaneous "thought-about-user" intensity, used by the
heartbeat scheduler (Phase 2) and the offline Monte Carlo validator
(:mod:`scripts.models.heartbeat_intensity_mc`).

Total intensity (see ``docs/models/heartbeat-intensity.md`` and Plan v3 §A.5):

.. code-block:: text

    λ_heartbeat(t | H_t, c, e)
        = M_chapter(c) · M_engagement(e) · Σ_a p(a | t) · ν_a
          + Σ_{t_i < t}  α(k_i) · w_i · β · exp(−β · (t − t_i))

- ``p(a | t)`` : von Mises mixture over circadian phase φ = 2π·t/24, softmaxed
  with a uniform noise floor ε so no activity probability is ever zero
- ``ν_a``      : per-activity heartbeat base rate (dream-state for sleep,
  high for personal/free time)
- ``M_chapter``: monotone-decreasing chapter modulator (early infatuation =
  more thoughts, settled = fewer)
- ``M_engagement``: state modulator (clingy boosts, distant suppresses)
- ``α(k)·w·β·exp(−β·τ)`` : Hawkes self-excitation contribution per past event,
  exponential decay with half-life T_half = 3 h

**Why von Mises × softmax?** Activity over 24 h is circular (φ wraps at
midnight); von Mises is the canonical circular Gaussian (Borbely 2016
Process C is a cosine forcing, mathematically equivalent). Softmax gives
honest probabilities; the ε floor satisfies the user's "never zero"
constraint (Plan v3 §A.1).

**Why Hawkes self-excitation?** Conversations beget more thoughts —
relationship-relevant excitation that decays over hours, not minutes. The
exponential kernel admits an O(1) recursive update form (Rizoiu et al.
2017), critical for production where the residual is persisted on the
user row and updated per event. Branching ratio is bounded < 1 by
construction (see :func:`hawkes_update` cap).

**Phase boundary**: this module ships Phase 1 of three. Phase 1 is
weekday-only (no weekend rave-mode swap), runs offline (the safety-net
hourly cron is in PR 215-D), and uses cold-start ALPHA values (no
per-user Bayesian state — that's Phase 3). The constants here are
forward-compatible: Phase 2 introduces ``ACTIVITY_PARAMS_WEEKEND`` as a
sibling table, Phase 3 introduces ``users.bayesian_state`` JSONB.

**Thread safety**: :class:`HeartbeatIntensity` wraps a per-instance
``random.Random`` for the Ogata thinning sampler. ``random.Random`` is
NOT safe to share across asyncio tasks — instantiate per request, do
NOT cache a singleton. Mirrors the
:class:`nikita.agents.text.timing.ResponseTimer` pattern.

See also:
    - ``scripts/models/heartbeat_intensity_mc.py`` — Monte Carlo validator
    - ``docs/models/heartbeat-intensity.md`` — model documentation
    - ``specs/215-heartbeat-engine/`` — SDD artifacts (spec, plan, tasks)
    - ``.claude/rules/stochastic-models.md`` — governance rule
    - ``/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md`` §A.1-A.6
      — math authority (von Mises × Hawkes × Ogata thinning derivation)
"""

from __future__ import annotations

import math
import random
from typing import Final

# --------------------------------------------------------------------------- #
# Layer 1 — Activity distribution (von Mises mixture + softmax + ε floor)     #
# --------------------------------------------------------------------------- #

# Five-activity discrete partition (Plan v3 §A.1). Order is canonical for
# stackplot rendering and CSV export; do NOT reorder without updating
# scripts/models/heartbeat_intensity_mc.py plot legends.
ACTIVITIES: Final[list[str]] = ["sleep", "work", "eating", "personal", "social"]

# Per-activity von Mises mixture: list[(μ_radians, κ, weight_within_activity)].
# K=2 for sleep (bimodal across midnight) and eating (lunch + dinner).
# Source: Plan v3 §A.1.5 (Phase 1 weekday baseline).
# Phase 2 will introduce a sibling ACTIVITY_PARAMS_WEEKEND for rave-mode swap;
# do not extend this table — replace with a day-of-week selector function.
ACTIVITY_PARAMS: Final[dict[str, list[tuple[float, float, float]]]] = {
    "sleep": [
        (2 * math.pi * 2.0 / 24, 4.0, 0.6),   # 02:00 peak (post-midnight)
        (2 * math.pi * 23.0 / 24, 4.0, 0.4),  # 23:00 peak (pre-midnight)
    ],
    "work": [(2 * math.pi * 10.5 / 24, 4.0, 1.0)],  # 10:30 weekday peak
    "eating": [
        (2 * math.pi * 12.5 / 24, 6.0, 0.5),  # lunch
        (2 * math.pi * 19.0 / 24, 6.0, 0.5),  # dinner
    ],
    "personal": [(2 * math.pi * 20.0 / 24, 2.5, 1.0)],  # broad evening peak
    "social": [(2 * math.pi * 21.0 / 24, 4.0, 1.0)],    # sharp evening peak
}

# ATUS 2024-grounded Dirichlet prior on activity proportions. Sums to 100
# (each entry is the % share of waking-time mass for that activity in the
# weekday baseline). Phase 3 Bayesian update will compose this with per-user
# observed activity counts to produce a posterior.
# Source: Plan v3 §A.1.5 v1 baseline (existing 7 PNGs were generated with
# these values; see PR #326). Phase 2 may swap to v2 user-tuned values.
DIRICHLET_PRIOR: Final[dict[str, int]] = {
    "sleep": 35,
    "work": 25,
    "eating": 10,
    "personal": 20,
    "social": 10,
}

# Normalized base weights (proportional to DIRICHLET_PRIOR). Cached at
# module load — DIRICHLET_PRIOR is Final, so this is safe.
_TOTAL_PRIOR: Final[int] = sum(DIRICHLET_PRIOR.values())
ACTIVITY_BASE_WEIGHTS: Final[dict[str, float]] = {
    a: w / _TOTAL_PRIOR for a, w in DIRICHLET_PRIOR.items()
}

# Uniform noise floor for the activity distribution. ε=0.03 → minimum
# activity probability is ε/A = 0.03/5 = 0.6% everywhere, satisfying the
# "never zero" constraint (Plan v3 §A.1).
# Recommended range: [0.02, 0.05] — too low collapses to softmax, too high
# washes out the circadian signal.
EPSILON_FLOOR: Final[float] = 0.03


def vonmises_mixture(
    t_hours: float, components: list[tuple[float, float, float]]
) -> float:
    """Evaluate Σ_k w_k · exp(κ_k · cos(φ - μ_k)) at t_hours.

    Phase φ = 2π · (t mod 24) / 24, so the function is exactly 24-periodic.
    No normalization (used as a relative weight inside softmax).
    """
    phi = 2 * math.pi * (t_hours % 24) / 24
    return sum(
        weight * math.exp(kappa * math.cos(phi - mu))
        for mu, kappa, weight in components
    )


def activity_distribution(t_hours: float) -> dict[str, float]:
    """Activity probability distribution p(a | t).

    Returns a dict keyed by :data:`ACTIVITIES` whose values sum to 1.0
    (within floating-point tolerance). The minimum value is bounded below
    by ``EPSILON_FLOOR / len(ACTIVITIES)`` (the noise-floor invariant).
    """
    A = len(ACTIVITIES)
    raw = {
        a: ACTIVITY_BASE_WEIGHTS[a] * vonmises_mixture(t_hours, ACTIVITY_PARAMS[a])
        for a in ACTIVITIES
    }
    total = sum(raw.values())
    softmax = {a: r / total for a, r in raw.items()}
    return {a: (1 - EPSILON_FLOOR) * softmax[a] + EPSILON_FLOOR / A for a in ACTIVITIES}


# --------------------------------------------------------------------------- #
# Layer 2 — Activity-conditional heartbeat rate ν_a (heartbeats/hour)         #
# --------------------------------------------------------------------------- #

# Per-activity base "thought about user" rate (Plan v3 §A.2 v2 user-tuned
# 2026-04-17). Cuts vs v1: eating 0.50→0.30 ("she's eating, not pondering"),
# personal 0.80→1.00 ("hobby/free time = thought-cycles"). Sleep, work,
# social unchanged. Regression-guarded by AC-T1.3-008.
NU_PER_ACTIVITY: Final[dict[str, float]] = {
    "sleep": 0.05,    # ~once per 20 h ("dream-state thoughts only")
    "work": 0.30,     # occasional thoughts during work
    "eating": 0.30,   # less reflective than v1 assumed
    "personal": 1.00, # free time / hobbies = high thought-cycles
    "social": 0.40,   # distracted by other people, but reminded
}


# --------------------------------------------------------------------------- #
# Layer 4 — Modulators (chapter, engagement)                                  #
# --------------------------------------------------------------------------- #

# Multiplicative chapter modulator. Monotone-decreasing: early-infatuation
# Ch1 has the most "she's thinking about you" intensity; settled Ch5 the
# least. Regression-guarded by AC-T1.3-003.
CHAPTER_MULT: Final[dict[int, float]] = {
    1: 1.5,  # Infatuation
    2: 1.3,  # Eager
    3: 1.1,  # Building
    4: 1.0,  # Comfortable (baseline)
    5: 0.9,  # Settled
}

# Engagement-state modulator. Clingy boosts (1.6×), distant suppresses
# (0.4×). Source: Spec 014/057 engagement state machine.
ENGAGEMENT_MULT: Final[dict[str, float]] = {
    "calibrating": 1.4,
    "in_zone": 1.0,
    "fading": 0.7,
    "distant": 0.4,
    "clingy": 1.6,
}


def lambda_baseline(
    t_hours: float, chapter: int = 3, engagement: str = "in_zone"
) -> float:
    """Marginal heartbeat baseline λ_baseline(t) = M_ch · M_eng · Σ_a p(a|t)·ν_a.

    Always > 0 by construction (noise floor + sleep ν > 0). This is the
    "circadian + chapter + engagement" intensity BEFORE Hawkes excitation.
    """
    p = activity_distribution(t_hours)
    return (
        CHAPTER_MULT[chapter]
        * ENGAGEMENT_MULT[engagement]
        * sum(p[a] * NU_PER_ACTIVITY[a] for a in ACTIVITIES)
    )


# --------------------------------------------------------------------------- #
# Layer 3 — Hawkes self-excitation (exponential kernel, T_half = 3 h)         #
# --------------------------------------------------------------------------- #

# Half-life of Hawkes excitation. After T_half hours, the residual decays
# to half its post-event value. Regression-guarded by AC-T1.3-005.
T_HALF_HRS: Final[float] = 3.0

# β = ln(2) / T_half ≈ 0.231 hr⁻¹. Closed-form derivation pinned by
# AC-T1.3-006 (must match math.log(2) / T_HALF_HRS within float tolerance).
BETA: Final[float] = math.log(2) / T_HALF_HRS

# Per-event-type excitation strength α(k). Cold-start values (no per-user
# Bayesian state in Phase 1). Branching-ratio constraint α·E[w] < 1 is
# regression-guarded by AC-T1.3-004:
#   0.40 · 1.2  +  0.15 · 1.0  +  0.05 · 1.0  =  0.68  <  1.0
# The 0.32 stability margin lets E[w_user] swing up to ~2.4 before the
# system becomes self-exciting beyond control.
ALPHA: Final[dict[str, float]] = {
    "user_msg": 0.40,
    "game_event": 0.15,
    "internal": 0.05,
}

# Hard cap on Hawkes residual to bound storm spikes (Plan v3 §A.5).
# R_max ≈ 3 · μ_base where μ_base ≈ Σ_a w_a^prior · ν_a ≈ 0.5. Cap holds
# even under sustained chat bursts; without it, a 10-msg burst could push
# R well above the natural cap and produce an unrealistic intensity.
# Regression-guarded by AC-T1.3-007.
R_MAX: Final[float] = 1.5


def hawkes_decay(R: float, dt_hours: float) -> float:
    """Decay residual R over a time gap dt: R(t+dt) = R · exp(−β · dt).

    Pure decay only — does NOT add a new event excitation. Use
    :func:`hawkes_update` for the post-event step. dt=0 returns R
    unchanged (identity at zero gap, regression-guarded by tests).
    """
    return R * math.exp(-BETA * dt_hours)


def hawkes_update(R: float, alpha_k: float, weight: float = 1.0) -> float:
    """Add an event's excitation to the residual: R + α_k · w · β, capped at R_MAX.

    Caller is responsible for decaying R first via :func:`hawkes_decay` if
    time has elapsed since the last event. The cap prevents storm spikes.
    """
    return min(R + alpha_k * weight * BETA, R_MAX)


# --------------------------------------------------------------------------- #
# Layer 5 — Total intensity                                                   #
# --------------------------------------------------------------------------- #


def lambda_total(
    t_hours: float, R: float, chapter: int = 3, engagement: str = "in_zone"
) -> float:
    """Total instantaneous intensity λ_total = λ_baseline + R."""
    return lambda_baseline(t_hours, chapter, engagement) + R


# --------------------------------------------------------------------------- #
# Layer 6 — Self-scheduling: Ogata thinning to sample next wake               #
# --------------------------------------------------------------------------- #

# Default lookahead horizon for Ogata thinning. The hourly safety-net cron
# (PR 215-D) catches degenerate cases where the sampler returns t_now +
# t_horizon (no acceptance within budget).
DEFAULT_HORIZON_HRS: Final[float] = 24.0

# Internal safety bound on the thinning loop: cap the number of
# accept-reject iterations to avoid pathological tight-loops if λ_max is
# misconfigured. 2000 iterations at average inter-arrival ≥ 1 minute is
# already > 33 hours of simulated time, well past the 24h horizon.
_MAX_THINNING_ITERATIONS: Final[int] = 2000


def _max_baseline_in_window(
    t_start: float,
    t_end: float,
    chapter: int,
    engagement: str,
    *,
    samples: int = 13,
) -> float:
    """Upper bound on λ_baseline over [t_start, t_end] via 13-point sampling.

    Ogata thinning needs an UPPER BOUND on the intensity in the proposal
    window. 13 samples in a 1-hour window is dense enough for the ε-floor
    + von Mises mixture to be conservatively bounded.
    """
    grid = [t_start + (t_end - t_start) * i / (samples - 1) for i in range(samples)]
    return max(lambda_baseline(s, chapter, engagement) for s in grid)


def sample_next_wakeup(
    t_now: float,
    R_now: float,
    chapter: int,
    engagement: str,
    rng: random.Random,
    t_horizon: float = DEFAULT_HORIZON_HRS,
) -> tuple[float, float]:
    """Ogata thinning sampler — returns (t_next, R_at_t_next).

    Args:
        t_now: current time (hours)
        R_now: current Hawkes residual (scalar; persisted on user row)
        chapter: 1-5
        engagement: one of :data:`ENGAGEMENT_MULT` keys
        rng: per-call ``random.Random`` instance (NOT thread-safe to share)
        t_horizon: max hours to look ahead. If exceeded, returns
            ``(t_now + t_horizon, R_at_horizon)`` and the safety-net
            hourly cron picks up.

    Returns:
        Tuple of (next-wake time in hours, residual at that time).

    Raises:
        ValueError: if engagement is not a recognized state.
    """
    if engagement not in ENGAGEMENT_MULT:
        raise ValueError(f"unknown engagement state: {engagement!r}")

    t = t_now
    R = R_now
    for _ in range(_MAX_THINNING_ITERATIONS):
        # Upper bound on λ_total in the next 1-hour proposal window.
        # λ_total = λ_baseline + R; R only decreases between events, so
        # using current R is a safe (loose) upper bound.
        lambda_max = _max_baseline_in_window(t, t + 1.0, chapter, engagement) + R
        if lambda_max <= 1e-9:
            return t_now + t_horizon, R

        # Propose the next homogeneous-Poisson interval at rate lambda_max
        dt = rng.expovariate(lambda_max)
        t_cand = t + dt
        if (t_cand - t_now) > t_horizon:
            return t_now + t_horizon, hawkes_decay(R, t_horizon)

        # Decay R to candidate time, then evaluate true intensity
        R_cand = hawkes_decay(R, dt)
        lambda_actual = lambda_baseline(t_cand, chapter, engagement) + R_cand

        # Accept-reject
        u = rng.uniform(0, lambda_max)
        if u <= lambda_actual:
            return t_cand, R_cand

        # Rejected — advance state and retry
        t, R = t_cand, R_cand

    # Defensive: hit the iteration cap. Return horizon fallback so the
    # safety-net cron picks up. Should be unreachable in practice.
    return t_now + t_horizon, R


# --------------------------------------------------------------------------- #
# HeartbeatIntensity — production-side wrapper with per-instance RNG          #
# --------------------------------------------------------------------------- #


class HeartbeatIntensity:
    """Per-request heartbeat-intensity sampler with isolated RNG.

    Mirrors :class:`nikita.agents.text.timing.ResponseTimer` (Spec 210).
    Each instance owns a private ``random.Random``; ``random.Random`` is
    NOT safe to share across asyncio tasks, so the production handler in
    PR 215-D will instantiate one per request rather than caching a
    singleton.

    Example::

        intensity = HeartbeatIntensity(seed=42)
        t_next, R_at_next = intensity.sample_next_wakeup(
            t_now=12.0, R_now=0.3, chapter=3, engagement="in_zone",
        )
    """

    def __init__(self, seed: int | None = None) -> None:
        # Per-instance RNG for thread safety under concurrent requests.
        self._rng = random.Random(seed)

    def sample_next_wakeup(
        self,
        t_now: float,
        R_now: float,
        chapter: int,
        engagement: str,
        t_horizon: float = DEFAULT_HORIZON_HRS,
    ) -> tuple[float, float]:
        """Sample the next wake time using this instance's RNG.

        Returns ``(t_next, R_at_t_next)``. See module-level
        :func:`sample_next_wakeup` for full semantics.
        """
        return sample_next_wakeup(
            t_now=t_now,
            R_now=R_now,
            chapter=chapter,
            engagement=engagement,
            rng=self._rng,
            t_horizon=t_horizon,
        )
