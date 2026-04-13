#!/usr/bin/env python3
"""Monte Carlo validator for Spec 210 response-timing model.

Validates: percentile distributions, momentum traces, feedback-spiral
boundedness, and EWMA unbiasedness. Produces CSV + PNGs under docs/models/.

Usage: uv run python scripts/models/response_timing_mc.py
Exit 0 if all assertions pass, 1 otherwise.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "models"
DOCS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

from nikita.agents.text.conversation_rhythm import (
    CHAPTER_BASELINES_SECONDS,
    MOMENTUM_ALPHA,
    MOMENTUM_HI,
    MOMENTUM_LO,
    SESSION_BREAK_SECONDS,
    WINDOW_SIZE,
    compute_momentum,
)
from nikita.agents.text.timing import (
    CHAPTER_CAPS_SECONDS,
    CHAPTER_COEFFICIENTS,
    LOGNORMAL_MU,
    LOGNORMAL_SIGMA,
)

# -- Design tokens for plots -------------------------------------------------
BG = "#020202"
SURFACE = "#0A0A0A"
TEXT = "#EBEBEB"
TEXT_DIM = (0.92, 0.92, 0.92, 0.28)
ACCENT = "#F383BB"
LAVENDER = "#8186D7"
SPINE_COLOR = (1, 1, 1, 0.1)
GRID_COLOR = (1, 1, 1, 0.06)
REF_COLOR = (1, 1, 1, 0.15)
REF_DIM = (1, 1, 1, 0.08)
CH_COLORS = ["#F383BB", "#D283D7", "#A985D7", "#8186D7", "#7BAAC8"]
CH_LABELS = ["Ch 1 · Infatuation", "Ch 2 · Very eager", "Ch 3 · Attentive",
             "Ch 4 · Comfortable", "Ch 5 · Settled"]

N_SAMPLES = 50_000
RNG = np.random.default_rng(42)


def sample_delays(chapter: int, n: int = N_SAMPLES) -> np.ndarray:
    coeff = CHAPTER_COEFFICIENTS[chapter]
    cap = CHAPTER_CAPS_SECONDS[chapter]
    raw = np.exp(LOGNORMAL_MU + LOGNORMAL_SIGMA * RNG.standard_normal(n)) * coeff
    return np.clip(raw, 0, cap)


def fmt(s: float) -> str:
    if s < 1:
        return f"{s * 1000:.0f}ms"
    if s < 60:
        return f"{s:.1f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.2f}h"


def percentile_table() -> dict[int, dict[str, float]]:
    rows = {}
    for ch in range(1, 6):
        d = sample_delays(ch)
        rows[ch] = {
            "coeff": CHAPTER_COEFFICIENTS[ch],
            "cap": CHAPTER_CAPS_SECONDS[ch],
            "median": float(np.median(d)),
            "p75": float(np.percentile(d, 75)),
            "p90": float(np.percentile(d, 90)),
            "p99": float(np.percentile(d, 99)),
            "max": float(np.max(d)),
            "at_cap_pct": float(np.mean(d >= CHAPTER_CAPS_SECONDS[ch]) * 100),
        }
    return rows


def write_csv(rows: dict[int, dict[str, float]]) -> Path:
    path = DOCS / "response-timing-percentiles.csv"
    with open(path, "w") as f:
        f.write("chapter,coeff,cap_s,median_s,p75_s,p90_s,p99_s,max_s,at_cap_pct\n")
        for ch, r in rows.items():
            f.write(f"{ch},{r['coeff']:.2f},{r['cap']},{r['median']:.2f},"
                    f"{r['p75']:.2f},{r['p90']:.2f},{r['p99']:.2f},"
                    f"{r['max']:.2f},{r['at_cap_pct']:.3f}\n")
    return path


def _setup_mpl():
    """Import and configure matplotlib once (Agg backend for headless)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def plot_histogram(rows: dict[int, dict[str, float]]) -> Path:
    plt = _setup_mpl()

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG)
    ax.set_facecolor(SURFACE)

    max_cap = max(CHAPTER_CAPS_SECONDS.values())
    bins = np.logspace(np.log10(0.1), np.log10(max_cap), 40)

    for ch in range(1, 6):
        d = sample_delays(ch)
        ax.hist(d, bins=bins, alpha=0.6, label=CH_LABELS[ch - 1],
                color=CH_COLORS[ch - 1], edgecolor="none")

    ax.set_xscale("log")
    ax.set_xlabel("Delay (seconds)", color=TEXT, fontsize=10)
    ax.set_ylabel("Count", color=TEXT, fontsize=10)
    ax.set_title("Response Delay Distribution by Chapter", color=TEXT, fontsize=12)
    ax.legend(fontsize=9, facecolor=SURFACE, edgecolor="none", labelcolor=TEXT)
    ax.tick_params(colors=TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)

    path = DOCS / "response-timing-histogram.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def plot_cdf() -> Path:
    plt = _setup_mpl()

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG)
    ax.set_facecolor(SURFACE)

    max_cap = max(CHAPTER_CAPS_SECONDS.values())
    x = np.logspace(np.log10(0.1), np.log10(max_cap), 200)

    for ch in range(1, 6):
        d = np.sort(sample_delays(ch))
        cdf = np.searchsorted(d, x) / len(d)
        ax.plot(x, cdf, label=CH_LABELS[ch - 1], color=CH_COLORS[ch - 1], linewidth=1.5)

    ax.axhline(0.5, color=SPINE_COLOR, linestyle="--", linewidth=0.8)
    ax.axhline(0.9, color=SPINE_COLOR, linestyle="--", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("Delay (seconds)", color=TEXT, fontsize=10)
    ax.set_ylabel("P(delay ≤ x)", color=TEXT, fontsize=10)
    ax.set_title("Cumulative Distribution Function", color=TEXT, fontsize=12)
    ax.legend(fontsize=9, facecolor=SURFACE, edgecolor="none", labelcolor=TEXT)
    ax.tick_params(colors=TEXT, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COLOR)

    path = DOCS / "response-timing-cdf.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def momentum_traces() -> Path:
    plt = _setup_mpl()

    traces = {
        "Fast (5s)":         [5, 8, 6, 7, 5, 9, 4, 6, 7, 5],
        "Normal (60s)":      [55, 70, 45, 80, 60, 50, 75, 65, 55, 70],
        "Slow (600s)":       [500, 700, 600, 800, 550, 750, 650, 720, 580, 630],
        "Accelerating":      [600, 400, 250, 120, 60, 30, 15, 10, 8, 5],
        "Decelerating":      [5, 10, 20, 50, 100, 200, 350, 500, 600, 700],
    }
    trace_colors = [ACCENT, "#D283D7", LAVENDER, "#7BAAC8", "#22d3ee"]

    fig, axes = plt.subplots(1, 5, figsize=(16, 4), facecolor=BG, sharey=True)
    chapter = 3
    baseline = CHAPTER_BASELINES_SECONDS[chapter]

    for idx, (name, gaps) in enumerate(traces.items()):
        ax = axes[idx]
        ax.set_facecolor(SURFACE)

        ms = []
        for i in range(1, len(gaps) + 1):
            m = compute_momentum(gaps[:i], chapter)
            ms.append(m)

        ax.plot(range(1, len(ms) + 1), ms, color=trace_colors[idx],
                linewidth=2, marker="o", markersize=3)
        ax.axhline(1.0, color=REF_COLOR, linestyle="--", linewidth=0.8)
        ax.axhline(MOMENTUM_LO, color=REF_DIM, linestyle=":", linewidth=0.7)
        ax.axhline(MOMENTUM_HI, color=REF_DIM, linestyle=":", linewidth=0.7)
        ax.set_title(name, color=TEXT, fontsize=9)
        ax.set_xlabel("Message #", color=TEXT, fontsize=8)
        ax.tick_params(colors=TEXT, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(SPINE_COLOR)

    axes[0].set_ylabel("M (momentum)", color=TEXT, fontsize=9)
    fig.suptitle(f"Momentum Traces (Ch {chapter}, B={baseline}s, α={MOMENTUM_ALPHA})",
                 color=TEXT, fontsize=11)

    path = DOCS / "response-timing-momentum-traces.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def test_feedback_spiral(n_sessions: int = 200, n_msgs: int = 20,
                         mirror_coeff: float = 0.5) -> bool:
    """Simulate sessions where user mirrors Nikita's delay. Assert bounded."""
    chapter = 3
    coeff = CHAPTER_COEFFICIENTS[chapter]
    cap = CHAPTER_CAPS_SECONDS[chapter]
    baseline = CHAPTER_BASELINES_SECONDS[chapter]

    session_lengths = []
    for _ in range(n_sessions):
        gaps: list[float] = []
        nikita_delay = 10.0  # seed

        for _ in range(n_msgs):
            user_gap = max(1.0, nikita_delay * mirror_coeff
                          + RNG.standard_normal() * 5.0)
            if user_gap >= SESSION_BREAK_SECONDS:
                user_gap = SESSION_BREAK_SECONDS - 1
            gaps.append(user_gap)

            m = compute_momentum(gaps[-WINDOW_SIZE:], chapter)
            z = RNG.standard_normal()
            raw = np.exp(LOGNORMAL_MU + LOGNORMAL_SIGMA * z) * coeff * m
            nikita_delay = min(cap, max(0, raw))

        session_lengths.append(sum(gaps))

    avg_length = float(np.mean(session_lengths))
    # A 20-msg session with 300s baseline would be ~6000s. Anything under
    # 50,000s (14h) is "bounded" — we're checking no runaway.
    bounded = avg_length < 50_000
    print(f"  Feedback spiral: avg session = {fmt(avg_length)} "
          f"({'PASS' if bounded else 'FAIL'})")
    return bounded


def test_unbiasedness(n_sessions: int = 10_000, n_msgs: int = 20) -> bool:
    """Draw user gaps from log-normal(log B_ch, 0.7). Assert E[M] ≈ 1.0."""
    chapter = 3
    baseline = CHAPTER_BASELINES_SECONDS[chapter]
    sigma_obs = 0.7
    # Set log-normal μ so arithmetic MEAN = baseline (not median).
    # E[X] = exp(μ + σ²/2) = baseline → μ = log(baseline) - σ²/2
    mu_adj = np.log(baseline) - sigma_obs**2 / 2.0

    m_averages = []
    for _ in range(n_sessions):
        gaps = np.exp(mu_adj + sigma_obs * RNG.standard_normal(n_msgs))
        gaps = np.clip(gaps, 1.0, SESSION_BREAK_SECONDS - 1)

        ms = []
        for i in range(1, len(gaps) + 1):
            m = compute_momentum(gaps[:i].tolist(), chapter)
            ms.append(m)
        m_averages.append(float(np.mean(ms)))

    grand_mean = float(np.mean(m_averages))
    unbiased = abs(grand_mean - 1.0) < 0.05
    print(f"  Unbiasedness: E[M] = {grand_mean:.4f} "
          f"({'PASS' if unbiased else 'FAIL'}, target 1.0 ± 0.05)")
    return unbiased


def main() -> int:
    t0 = time.monotonic()
    print("=" * 60)
    print("Response Timing MC Validator — Spec 210 v2")
    print("=" * 60)

    print(f"\nParameters: μ={LOGNORMAL_MU}, σ={LOGNORMAL_SIGMA}, "
          f"α={MOMENTUM_ALPHA}, N={N_SAMPLES:,}")
    print(f"Coefficients: {CHAPTER_COEFFICIENTS}")
    print(f"Caps: {CHAPTER_CAPS_SECONDS}")
    print(f"Baselines: {CHAPTER_BASELINES_SECONDS}")

    # 1. Percentile table + CSV
    print("\n--- Percentile Table ---")
    rows = percentile_table()
    csv_path = write_csv(rows)
    print(f"{'Ch':>3} {'Coeff':>6} {'Cap':>6} {'p50':>8} {'p75':>8} "
          f"{'p90':>8} {'p99':>8} {'Max':>8} {'@cap':>7}")
    for ch, r in rows.items():
        print(f"{ch:>3} {r['coeff']:>6.2f} {fmt(r['cap']):>6} "
              f"{fmt(r['median']):>8} {fmt(r['p75']):>8} "
              f"{fmt(r['p90']):>8} {fmt(r['p99']):>8} "
              f"{fmt(r['max']):>8} {r['at_cap_pct']:>6.2f}%")
    print(f"  CSV → {csv_path.relative_to(ROOT)}")

    # 2. Plots
    print("\n--- Generating Plots ---")
    hist_path = plot_histogram(rows)
    print(f"  Histogram → {hist_path.relative_to(ROOT)}")
    cdf_path = plot_cdf()
    print(f"  CDF → {cdf_path.relative_to(ROOT)}")
    traces_path = momentum_traces()
    print(f"  Momentum traces → {traces_path.relative_to(ROOT)}")

    # 3. Assertions
    print("\n--- Assertions ---")
    all_pass = True

    # Ch1 cap enforcement
    ch1_max = rows[1]["max"]
    ch1_ok = ch1_max <= CHAPTER_CAPS_SECONDS[1]
    print(f"  Ch1 max ≤ {CHAPTER_CAPS_SECONDS[1]}s: "
          f"{fmt(ch1_max)} {'PASS' if ch1_ok else 'FAIL'}")
    all_pass &= ch1_ok

    # Ch1 median < 5s
    ch1_med = rows[1]["median"]
    ch1_med_ok = ch1_med < 5.0
    print(f"  Ch1 median < 5s: {fmt(ch1_med)} "
          f"{'PASS' if ch1_med_ok else 'FAIL'}")
    all_pass &= ch1_med_ok

    # Monotonic medians (Ch1 < Ch2 < ... < Ch5)
    medians = [rows[ch]["median"] for ch in range(1, 6)]
    mono_ok = all(medians[i] < medians[i + 1] for i in range(4))
    print(f"  Monotonic medians: {[fmt(m) for m in medians]} "
          f"{'PASS' if mono_ok else 'FAIL'}")
    all_pass &= mono_ok

    # Feedback spiral
    all_pass &= test_feedback_spiral()

    # Unbiasedness
    all_pass &= test_unbiasedness()

    elapsed = time.monotonic() - t0
    print(f"\n{'=' * 60}")
    status = "ALL PASS" if all_pass else "SOME FAILED"
    print(f"Result: {status} ({elapsed:.1f}s)")
    print(f"{'=' * 60}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
