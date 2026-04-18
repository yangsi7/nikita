#!/usr/bin/env python3
"""Live-vs-offline heartbeat parity validator (Spec 215 PR 215-F, FR-016).

Compares production-observed heartbeat inter-wake distributions (last 7 days,
``scheduled_events WHERE event_type='heartbeat'``) against the offline Monte
Carlo distribution from :mod:`nikita.heartbeat.intensity`. Performs a
Kolmogorov-Smirnov two-sample test per chapter and exits 0/1.

**Why KS?** The two-sample KS statistic measures the maximum vertical gap
between two empirical CDFs without assuming a specific parametric form.
Inter-wake gaps from the Hawkes-modulated intensity are NOT exponentially
distributed (excitation makes them sub-exponential at short lags), so a
parametric test would mis-specify the null. KS is distribution-free.

**Why exit code policy "any chapter p ≤ 0.01 → exit 1"?** A single failing
chapter is a real signal — the model and reality diverge for at least one
relationship phase. The threshold 0.01 is intentionally strict (Type I error
~1%) because we run nightly and the "alert if EVER fails" cost over a year
is non-trivial; we want false-positive rate ≤ 365 × 0.01 ≈ 3.6 alerts/year
per chapter. The CI workflow files a GH issue with severity:high on exit 1.

**Why mock at SQL-result level in tests?** Production has zero heartbeat
events at PR write time (PR 215-F is the first to ship the validator).
Tests inject synthetic numpy arrays directly through the
``fetch_observed_inter_wake`` boundary; the live SQL is exercised only in
CI cron after Phase 2 of Spec 215 ships.

**KS implementation**: We re-implement the two-sample KS p-value via the
Smirnov asymptotic series (Numerical Recipes 14.3.4) instead of importing
SciPy. SciPy is not in pyproject.toml and adding a heavy native dep just
for one statistic is poor cost/benefit. The Smirnov series converges fast
(<1e-8 after ~10 terms for typical effective N).

Usage::

    uv run python scripts/models/heartbeat_live_parity.py
    uv run python scripts/models/heartbeat_live_parity.py --window-days 14
    uv run python scripts/models/heartbeat_live_parity.py --mc-samples 5000

Exit codes:
    0  All chapters pass parity OR no observed data yet (no alert)
    1  At least one chapter has p ≤ P_VALUE_THRESHOLD (drift detected)

Output: JSON document on stdout with per-chapter breakdown
(``ks_statistic``, ``p_value``, ``n_observed``, ``n_mc``, ``passed``).

See also:
    - scripts/models/heartbeat_intensity_mc.py — offline MC validator
    - .github/workflows/heartbeat-parity-nightly.yml — CI cron
    - specs/215-heartbeat-engine/spec.md FR-016
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from typing import Any, Final

import numpy as np

from nikita.heartbeat.intensity import sample_next_wakeup

# --------------------------------------------------------------------------- #
# Tunable thresholds (kept here, not in nikita/, since this is a validator)   #
# --------------------------------------------------------------------------- #

# A chapter PASSES parity iff KS p-value > P_VALUE_THRESHOLD. 0.01 chosen
# to bound nightly false-positive rate to ~3.6 alerts/chapter/year. Tighter
# than the typical 0.05 because we run on a fixed schedule.
P_VALUE_THRESHOLD: Final[float] = 0.01

# Default rolling window of production data to consider.
DEFAULT_WINDOW_DAYS: Final[int] = 7

# Default MC sample count per chapter. Larger → tighter KS p-values + slower.
# 2000 gives KS standard error ~0.02 — adequate for chapter-level decisions.
DEFAULT_MC_SAMPLES: Final[int] = 2000

# Engagement state used for MC reference. We compare against the modal
# engagement state ('in_zone') because per-event engagement isn't currently
# stored on scheduled_events; treat divergence per chapter as the lever.
MC_REFERENCE_ENGAGEMENT: Final[str] = "in_zone"

# Deterministic seed for the MC reference distribution so nightly runs are
# reproducible (the only stochasticity should be the production data).
MC_SEED: Final[int] = 0xDEADBEEF


# --------------------------------------------------------------------------- #
# Two-sample Kolmogorov-Smirnov                                               #
# --------------------------------------------------------------------------- #


def _kolmogorov_p(d: float, n_eff: float) -> float:
    """Asymptotic two-sided KS p-value via Smirnov series.

    Returns Pr(D >= d) under the null where ``n_eff`` is the harmonic-mean
    sample size. Numerical Recipes 14.3.4. Series converges in ~10 terms for
    en >= 4. Returns 1.0 for degenerate inputs (n_eff <= 0 or d == 0).
    """
    if n_eff <= 0 or d <= 0:
        return 1.0
    en = math.sqrt(n_eff)
    # Stevens 1970 small-sample correction
    lam = (en + 0.12 + 0.11 / en) * d
    lam2 = -2.0 * lam * lam
    total = 0.0
    fac = 2.0
    prev = 0.0
    for j in range(1, 101):
        term = fac * math.exp(lam2 * j * j)
        total += term
        if abs(term) <= 0.001 * abs(prev) or abs(term) <= 1.0e-10 * total:
            return min(max(total, 0.0), 1.0)
        fac = -fac
        prev = term
    return 1.0  # series failed to converge → conservative (no rejection)


def ks_two_sample(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test (D statistic + asymptotic p-value).

    Returns (D, p) where D = max |F_a(x) - F_b(x)| over the pooled support
    and p ≈ Pr(D >= observed | both samples drawn from same distribution).

    Both arrays must be 1-D and have at least 1 element each. Behaviour with
    empty arrays is undefined (caller must guard).
    """
    a_sorted = np.sort(np.asarray(a, dtype=float))
    b_sorted = np.sort(np.asarray(b, dtype=float))
    n_a = a_sorted.size
    n_b = b_sorted.size
    if n_a == 0 or n_b == 0:
        return 0.0, 1.0
    # Pool, then compute step-CDF differences via searchsorted
    pooled = np.concatenate([a_sorted, b_sorted])
    cdf_a = np.searchsorted(a_sorted, pooled, side="right") / n_a
    cdf_b = np.searchsorted(b_sorted, pooled, side="right") / n_b
    d = float(np.max(np.abs(cdf_a - cdf_b)))
    n_eff = n_a * n_b / (n_a + n_b)
    p = _kolmogorov_p(d, n_eff)
    return d, p


# --------------------------------------------------------------------------- #
# I/O boundary — mockable in tests                                            #
# --------------------------------------------------------------------------- #


def fetch_observed_inter_wake(
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[int, np.ndarray]:
    """Pull observed heartbeat inter-wake gaps (hours) per chapter from Supabase.

    Live implementation queries scheduled_events:

        SELECT user_id, chapter, scheduled_at
        FROM scheduled_events
        WHERE event_type = 'heartbeat'
          AND scheduled_at > now() - interval '{window_days} days'
        ORDER BY user_id, scheduled_at;

    For each user, computes inter-wake = diff(scheduled_at) in hours, groups
    by chapter, returns ``{chapter: ndarray}``.

    Wired against the production Supabase MCP at runtime. In CI/nightly the
    MCP isn't available from a GitHub Actions runner, so the cron uses the
    REST API or a service-role JWT against the Supabase HTTP endpoint
    (configured via SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY env vars in the
    workflow). Since prod has zero heartbeat events at PR-F write time,
    this function is a no-op stub returning empty arrays — the validator
    correctly reports ``no_data`` and exits 0. It will be wired up in PR
    215-D once the heartbeat dispatcher starts emitting rows.

    Tests patch this function directly to inject synthetic distributions.
    """
    # Phase 1 stub: no observed data exists yet. Return empty arrays per
    # chapter so the validator reports 'no_data' rather than crashing.
    # PR 215-D wires the real query.
    return {chapter: np.array([]) for chapter in range(1, 6)}


def generate_mc_samples(
    n_samples: int = DEFAULT_MC_SAMPLES,
    seed: int = MC_SEED,
) -> dict[int, np.ndarray]:
    """Generate per-chapter MC inter-wake samples via Ogata thinning.

    For each chapter 1-5, runs ``sample_next_wakeup`` repeatedly from a
    cold-start state (R=0, randomized t_now ∈ [0, 24)) and collects
    inter-wake gaps in hours. Reuses production sampler so MC <> live
    comparison cannot drift from a divergent implementation.
    """
    rng = random.Random(seed)
    out: dict[int, np.ndarray] = {}
    for chapter in range(1, 6):
        gaps: list[float] = []
        # Start at an arbitrary phase to mix circadian, then chain wakes
        t_now = rng.uniform(0.0, 24.0)
        R = 0.0
        for _ in range(n_samples):
            t_next, R_next = sample_next_wakeup(
                t_now=t_now,
                R_now=R,
                chapter=chapter,
                engagement=MC_REFERENCE_ENGAGEMENT,
                rng=rng,
            )
            gap = t_next - t_now
            # Skip horizon-truncated gaps (degenerate "no event in 24h")
            if gap < 24.0 - 1e-6:
                gaps.append(gap)
            t_now = t_next
            R = R_next
        out[chapter] = np.asarray(gaps, dtype=float)
    return out


# --------------------------------------------------------------------------- #
# Core validator                                                              #
# --------------------------------------------------------------------------- #


def run_parity(
    observed: dict[int, np.ndarray],
    mc_samples: dict[int, np.ndarray],
    *,
    p_threshold: float = P_VALUE_THRESHOLD,
) -> dict[str, Any]:
    """Compare observed vs MC per chapter; return structured result.

    Per chapter:
        - If observed is empty → ``passed=True``, p_value/ks_statistic=None,
          contributes ``no_data`` flavor to overall status.
        - Else KS-test against MC; ``passed = p_value > p_threshold``.

    Overall status:
        - "pass" if all chapters have observed data and all pass
        - "fail" if ANY chapter has observed data and fails
        - "no_data" if NO chapter has observed data
    """
    chapters: dict[int, dict[str, Any]] = {}
    any_data = False
    any_failed = False

    for chapter in range(1, 6):
        obs = observed.get(chapter, np.array([]))
        mc = mc_samples.get(chapter, np.array([]))
        n_obs = int(obs.size)
        n_mc = int(mc.size)

        if n_obs == 0:
            chapters[chapter] = {
                "passed": True,
                "p_value": None,
                "ks_statistic": None,
                "n_observed": 0,
                "n_mc": n_mc,
                "reason": "no_observed_data",
            }
            continue

        any_data = True
        if n_mc == 0:
            # Defensive — MC should never be empty, but don't crash if it is
            chapters[chapter] = {
                "passed": True,
                "p_value": None,
                "ks_statistic": None,
                "n_observed": n_obs,
                "n_mc": 0,
                "reason": "no_mc_reference",
            }
            continue

        d, p = ks_two_sample(obs, mc)
        passed = p > p_threshold
        if not passed:
            any_failed = True
        chapters[chapter] = {
            "passed": passed,
            "p_value": float(p),
            "ks_statistic": float(d),
            "n_observed": n_obs,
            "n_mc": n_mc,
        }

    if not any_data:
        status = "no_data"
        exit_code = 0
    elif any_failed:
        status = "fail"
        exit_code = 1
    else:
        status = "pass"
        exit_code = 0

    return {
        "status": status,
        "exit_code": exit_code,
        "p_threshold": p_threshold,
        "chapters": chapters,
    }


# --------------------------------------------------------------------------- #
# CLI entry                                                                   #
# --------------------------------------------------------------------------- #


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    p.add_argument("--mc-samples", type=int, default=DEFAULT_MC_SAMPLES)
    p.add_argument("--mc-seed", type=int, default=MC_SEED)
    p.add_argument(
        "--p-threshold", type=float, default=P_VALUE_THRESHOLD,
        help="A chapter passes iff KS p-value > threshold (default 0.01)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry: fetch live data + MC samples, run parity, emit JSON, return exit code."""
    args = _build_arg_parser().parse_args(argv)
    observed = fetch_observed_inter_wake(window_days=args.window_days)
    mc_samples = generate_mc_samples(n_samples=args.mc_samples, seed=args.mc_seed)
    result = run_parity(
        observed=observed,
        mc_samples=mc_samples,
        p_threshold=args.p_threshold,
    )
    # Emit JSON on stdout (the GH Actions step pipes this into a comment + log)
    print(json.dumps(result, indent=2, default=str))
    return int(result["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
