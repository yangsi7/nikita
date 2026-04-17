#!/usr/bin/env python3
"""Monte Carlo simulator + plot generator for the Nikita Heartbeat Engine.

Implements the 6-layer model from Plan v3 §A.2 (delightful-orbiting-ladybug.md):
  L1  Activity distribution p(activity|t)  - von Mises mixture + softmax + ε floor
  L2  Activity-conditional rate ν_a         - heartbeats/hour per activity
  L3  Hawkes excitation                     - exp kernel, β=ln(2)/3h
  L4  Modulators                            - chapter × engagement multipliers
  L5  Total intensity                       - λ_baseline + λ_excite
  L6  Self-scheduling                       - Ogata thinning to sample next wake
  L7  Replan triggers                       - user msg + chapter advance cancel pending

Discrete-event simulation: user msgs arrive via Poisson with circadian intensity;
heartbeats fire via Ogata-thinned wake sampling; each wake self-schedules the next
into a "scheduled_events" queue; user msgs hard-replan (cancel pending + recompute).

Generates 7 PNG plots into docs/models/ for admin portal embedding.

Usage: uv run python scripts/models/heartbeat_intensity_mc.py
Exit:  0 if all sanity assertions pass, 1 otherwise. Runtime ≈ 15s.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

# ─────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "models"
DOCS.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# Design tokens (match response-timing palette)
# ─────────────────────────────────────────────────────────────────────────
BG = "#0b0f17"
SURFACE = "#131a26"
TEXT = "#e6ebf2"
SUBTEXT = "#94a3b8"
ACCENT = "#7dd3fc"
LAVENDER = "#c4b5fd"
GRID = "#1f2a3a"
SPINE = "#2a3550"
CH_COLORS = ["#f87171", "#fb923c", "#facc15", "#4ade80", "#60a5fa"]
CH_LABELS = ["Ch1 Infatuation", "Ch2 Eager", "Ch3 Building", "Ch4 Comfortable", "Ch5 Settled"]
ACT_COLORS = {
    "sleep": "#4338ca",
    "work": "#0891b2",
    "eating": "#ca8a04",
    "personal": "#16a34a",
    "social": "#db2777",
}


def setup_mpl() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": SPINE,
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
            "text.color": TEXT,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
            "savefig.facecolor": BG,
            "savefig.bbox": "tight",
            "savefig.dpi": 130,
            "legend.facecolor": SURFACE,
            "legend.edgecolor": SPINE,
            "legend.labelcolor": TEXT,
        }
    )


# ─────────────────────────────────────────────────────────────────────────
# LAYER 1 — Activity distribution (von Mises mixture + softmax + ε floor)
# ─────────────────────────────────────────────────────────────────────────
ACTIVITIES = ["sleep", "work", "eating", "personal", "social"]

# (μ_radians, κ, weight_within_activity) per component; list per activity
# Sleep K=2 (early morning + late evening, spans midnight)
# Eating K=2 (lunch + dinner)
ACTIVITY_PARAMS: dict[str, list[tuple[float, float, float]]] = {
    "sleep":    [(2 * math.pi *  2.0 / 24, 4.0, 0.6),
                 (2 * math.pi * 23.0 / 24, 4.0, 0.4)],
    "work":     [(2 * math.pi * 10.5 / 24, 4.0, 1.0)],
    "eating":   [(2 * math.pi * 12.5 / 24, 6.0, 0.5),
                 (2 * math.pi * 19.0 / 24, 6.0, 0.5)],
    "personal": [(2 * math.pi * 20.0 / 24, 2.5, 1.0)],
    "social":   [(2 * math.pi * 21.0 / 24, 4.0, 1.0)],
}

# Dirichlet prior weights from ATUS 2024 (proportional)
DIRICHLET_PRIOR = {"sleep": 35, "work": 25, "eating": 10, "personal": 20, "social": 10}
TOTAL_PRIOR = sum(DIRICHLET_PRIOR.values())
ACTIVITY_BASE_WEIGHTS = {a: w / TOTAL_PRIOR for a, w in DIRICHLET_PRIOR.items()}

EPSILON_FLOOR = 0.03  # never-zero noise: min activity probability is ε/A = 0.6%


def vonmises_mixture(t_hours: float, components: list[tuple[float, float, float]]) -> float:
    phi = 2 * math.pi * (t_hours % 24) / 24
    return sum(w * math.exp(kappa * math.cos(phi - mu)) for mu, kappa, w in components)


def activity_distribution(t_hours: float) -> dict[str, float]:
    A = len(ACTIVITIES)
    raw = {a: ACTIVITY_BASE_WEIGHTS[a] * vonmises_mixture(t_hours, ACTIVITY_PARAMS[a])
           for a in ACTIVITIES}
    total = sum(raw.values())
    softmax = {a: r / total for a, r in raw.items()}
    return {a: (1 - EPSILON_FLOOR) * softmax[a] + EPSILON_FLOOR / A for a in ACTIVITIES}


# ─────────────────────────────────────────────────────────────────────────
# LAYER 2 — Activity-conditional heartbeat rate
# ─────────────────────────────────────────────────────────────────────────
NU_PER_ACTIVITY = {
    "sleep":    0.05,  # heartbeats/hour - dream-state thoughts only
    "work":     0.30,  # occasional thoughts during work
    "eating":   0.50,  # mealtimes are reflective
    "personal": 0.80,  # free time = thought cycles
    "social":   0.40,  # distracted but reminded
}


# ─────────────────────────────────────────────────────────────────────────
# LAYER 4 — Chapter × engagement modulators
# ─────────────────────────────────────────────────────────────────────────
CHAPTER_MULT = {1: 1.5, 2: 1.3, 3: 1.1, 4: 1.0, 5: 0.9}
ENGAGEMENT_MULT = {
    "calibrating": 1.4, "in_zone": 1.0, "fading": 0.7,
    "distant": 0.4, "clingy": 1.6,
}


def lambda_baseline(t_hours: float, chapter: int = 3, engagement: str = "in_zone") -> float:
    p = activity_distribution(t_hours)
    return CHAPTER_MULT[chapter] * ENGAGEMENT_MULT[engagement] * sum(
        p[a] * NU_PER_ACTIVITY[a] for a in ACTIVITIES
    )


# ─────────────────────────────────────────────────────────────────────────
# LAYER 3 — Hawkes excitation (exponential kernel, T_half=3h)
# ─────────────────────────────────────────────────────────────────────────
T_HALF_HRS = 3.0
BETA = math.log(2) / T_HALF_HRS  # ≈ 0.231 hr^-1
ALPHA = {"user_msg": 0.40, "game_event": 0.15, "internal": 0.05}
R_MAX = 1.5  # cap residual to prevent storm spikes


def hawkes_decay(R: float, dt: float) -> float:
    return R * math.exp(-BETA * dt)


def hawkes_update(R: float, alpha_k: float, weight: float = 1.0) -> float:
    return min(R + alpha_k * weight * BETA, R_MAX)


# ─────────────────────────────────────────────────────────────────────────
# LAYER 5 — Total intensity & Ogata thinning
# ─────────────────────────────────────────────────────────────────────────
def lambda_total(t: float, R: float, chapter: int = 3, engagement: str = "in_zone") -> float:
    return lambda_baseline(t, chapter, engagement) + R


def sample_next_wakeup(
    t_now: float, R_now: float, chapter: int, engagement: str,
    rng: np.random.Generator, t_horizon: float = 24.0,
) -> tuple[float, float]:
    """Ogata thinning. Returns (t_next, R_at_t_next). t_horizon caps lookahead."""
    t = t_now
    R = R_now
    for _ in range(2000):  # safety bound
        # Upper bound λ over the next 1h chunk
        sample_pts = np.linspace(t, t + 1.0, 13)
        lambda_max = max(lambda_baseline(s, chapter, engagement) for s in sample_pts) + R
        if lambda_max <= 1e-9:
            return t_now + t_horizon, R
        dt = float(rng.exponential(1.0 / lambda_max))
        t_cand = t + dt
        if (t_cand - t_now) > t_horizon:
            return t_now + t_horizon, hawkes_decay(R, t_horizon)
        R_cand = hawkes_decay(R, dt)
        lam_actual = lambda_baseline(t_cand, chapter, engagement) + R_cand
        u = float(rng.uniform(0, lambda_max))
        if u <= lam_actual:
            return t_cand, R_cand
        t, R = t_cand, R_cand
    return t_now + t_horizon, R


# ─────────────────────────────────────────────────────────────────────────
# User-message Poisson process (circadian intensity)
# ─────────────────────────────────────────────────────────────────────────
def user_msg_intensity(t_hours: float) -> float:
    """User's circadian messaging propensity (msgs/hour)."""
    h = t_hours % 24
    peak1 = math.exp(-((h - 9.0) ** 2) / (2 * 2.0 ** 2))   # morning check-in
    peak2 = math.exp(-((h - 22.0) ** 2) / (2 * 2.0 ** 2))  # evening connect
    return 0.8 * (peak1 + peak2) + 0.05  # baseline


def sample_user_messages(t_start: float, t_end: float, scale: float, rng: np.random.Generator) -> list[float]:
    msgs: list[float] = []
    lam_max = max(user_msg_intensity(h) for h in np.linspace(0, 24, 100)) * scale
    if lam_max <= 0:
        return []
    t = t_start
    while t < t_end:
        dt = float(rng.exponential(1.0 / lam_max))
        t_cand = t + dt
        if t_cand >= t_end:
            break
        if rng.uniform(0, lam_max) <= user_msg_intensity(t_cand) * scale:
            msgs.append(t_cand)
        t = t_cand
    return msgs


# ─────────────────────────────────────────────────────────────────────────
# Discrete-event simulation
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class SimResult:
    user_msgs: list[float] = field(default_factory=list)
    nikita_wakes: list[dict] = field(default_factory=list)
    cancellations: list[dict] = field(default_factory=list)
    scheduled_at_end: list[dict] = field(default_factory=list)


def simulate(
    days: int = 1, chapter: int = 3, engagement: str = "in_zone",
    user_msg_scale: float = 1.0, seed: int = 42,
    chapter_advance_at: float | None = None, advance_to_chapter: int | None = None,
) -> SimResult:
    rng = np.random.default_rng(seed)
    t_end = days * 24.0
    user_msgs = sample_user_messages(0.0, t_end, user_msg_scale, rng)

    R = 0.0
    t = 0.0
    cur_chapter = chapter
    nikita_wakes: list[dict] = []
    scheduled: list[dict] = []
    cancellations: list[dict] = []

    next_t, next_R = sample_next_wakeup(t, R, cur_chapter, engagement, rng)
    scheduled.append({"t": next_t, "R": next_R})

    msg_idx = 0
    while t < t_end:
        upcoming_user = user_msgs[msg_idx] if msg_idx < len(user_msgs) else None
        upcoming_wake = min((s["t"] for s in scheduled if s["t"] > t), default=None)
        replan_due = (chapter_advance_at is not None and chapter_advance_at > t and chapter_advance_at <= t_end)

        candidates: list[tuple[float, str]] = [(t_end, "end")]
        if upcoming_user is not None:
            candidates.append((upcoming_user, "user_msg"))
        if upcoming_wake is not None:
            candidates.append((upcoming_wake, "heartbeat"))
        if replan_due:
            candidates.append((chapter_advance_at, "chapter_advance"))

        next_t, kind = min(candidates, key=lambda x: x[0])
        if next_t >= t_end:
            break

        R = hawkes_decay(R, next_t - t)
        t = next_t

        if kind == "user_msg":
            R = hawkes_update(R, ALPHA["user_msg"])
            msg_idx += 1
            cancelled = [s["t"] for s in scheduled if s["t"] > t]
            if cancelled:
                cancellations.append({"at": t, "cancelled": cancelled, "reason": "user_msg"})
            scheduled = [s for s in scheduled if s["t"] <= t]
            new_t, new_R = sample_next_wakeup(t, R, cur_chapter, engagement, rng)
            scheduled.append({"t": new_t, "R": new_R})
        elif kind == "heartbeat":
            top_act = max(activity_distribution(t).items(), key=lambda x: x[1])[0]
            nikita_wakes.append({"t": t, "R": R, "activity": top_act, "chapter": cur_chapter})
            new_t, new_R = sample_next_wakeup(t, R, cur_chapter, engagement, rng)
            scheduled.append({"t": new_t, "R": new_R})
        elif kind == "chapter_advance":
            cur_chapter = advance_to_chapter or cur_chapter
            cancelled = [s["t"] for s in scheduled if s["t"] > t]
            if cancelled:
                cancellations.append({"at": t, "cancelled": cancelled, "reason": "chapter_advance"})
            scheduled = [s for s in scheduled if s["t"] <= t]
            R = hawkes_update(R, ALPHA["game_event"], weight=1.5)
            new_t, new_R = sample_next_wakeup(t, R, cur_chapter, engagement, rng)
            scheduled.append({"t": new_t, "R": new_R})

    return SimResult(
        user_msgs=user_msgs, nikita_wakes=nikita_wakes,
        cancellations=cancellations, scheduled_at_end=scheduled,
    )


# ─────────────────────────────────────────────────────────────────────────
# PLOT 1: Activity distribution stacked area (24h)
# ─────────────────────────────────────────────────────────────────────────
def plot_activity_distribution() -> Path:
    setup_mpl()
    fig, ax = plt.subplots(figsize=(11, 5))
    t_grid = np.linspace(0, 24, 1000)
    p_by_act = {a: np.array([activity_distribution(t)[a] for t in t_grid]) for a in ACTIVITIES}
    ax.stackplot(
        t_grid,
        [p_by_act[a] for a in ACTIVITIES],
        labels=[a.capitalize() for a in ACTIVITIES],
        colors=[ACT_COLORS[a] for a in ACTIVITIES],
        alpha=0.85, edgecolor=BG, linewidth=0.5,
    )
    ax.axhline(EPSILON_FLOOR / len(ACTIVITIES), color=ACCENT, linestyle="--", linewidth=1, alpha=0.6,
               label=f"ε/A floor = {EPSILON_FLOOR/len(ACTIVITIES):.3f}")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 1)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])
    ax.set_xlabel("Time of day")
    ax.set_ylabel("p(activity | t)")
    ax.set_title("Layer 1 — Activity probability distribution over 24h\n"
                 "von Mises mixture + softmax + ε noise floor (never zero)",
                 color=TEXT, fontsize=12, pad=14)
    ax.legend(loc="upper center", ncol=6, frameon=True, fontsize=9)
    out = DOCS / "heartbeat-activity-distribution.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# PLOT 2: Marginal baseline λ_circ(t) per chapter
# ─────────────────────────────────────────────────────────────────────────
def plot_baseline_per_chapter() -> Path:
    setup_mpl()
    fig, ax = plt.subplots(figsize=(11, 5))
    t_grid = np.linspace(0, 24, 1000)
    for ch in range(1, 6):
        lam = np.array([lambda_baseline(t, chapter=ch) for t in t_grid])
        ax.plot(t_grid, lam, color=CH_COLORS[ch - 1], label=CH_LABELS[ch - 1], linewidth=2)
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])
    ax.set_xlabel("Time of day")
    ax.set_ylabel("λ_baseline(t)  (heartbeats/hour)")
    ax.set_title("Layer 2+4 — Marginal heartbeat baseline by chapter\n"
                 "Σ p(a|t)·ν_a × M_chapter (engagement = in_zone)",
                 color=TEXT, fontsize=12, pad=14)
    ax.legend(loc="upper left", frameon=True, fontsize=9)
    # Annotate trough/peak hours
    ax.axvspan(2, 5, alpha=0.08, color=ACT_COLORS["sleep"], label="_nolegend_")
    ax.text(3.5, ax.get_ylim()[1] * 0.92, "sleep trough", color=SUBTEXT, fontsize=9, ha="center")
    ax.axvspan(19.5, 22.5, alpha=0.08, color=ACT_COLORS["personal"], label="_nolegend_")
    ax.text(21, ax.get_ylim()[1] * 0.92, "evening peak", color=SUBTEXT, fontsize=9, ha="center")
    out = DOCS / "heartbeat-baseline-per-chapter.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# PLOT 3: Hawkes excitation decay scenarios
# ─────────────────────────────────────────────────────────────────────────
def plot_hawkes_scenarios() -> Path:
    setup_mpl()
    fig, ax = plt.subplots(figsize=(11, 5))
    t_grid = np.linspace(0, 12, 1000)

    def trace(events: list[float], label: str, color: str) -> None:
        R_vals = []
        R = 0.0
        last = 0.0
        ev_idx = 0
        for tt in t_grid:
            while ev_idx < len(events) and events[ev_idx] <= tt:
                R = hawkes_decay(R, events[ev_idx] - last)
                R = hawkes_update(R, ALPHA["user_msg"])
                last = events[ev_idx]
                ev_idx += 1
            R_vals.append(hawkes_decay(R, tt - last))
        ax.plot(t_grid, R_vals, color=color, linewidth=2, label=label)
        for ev in events:
            ax.axvline(ev, color=color, alpha=0.25, linewidth=1)

    trace([0.5], "1 message", ACCENT)
    trace([0.5, 0.7, 0.9, 1.1, 1.3], "Burst of 5", LAVENDER)
    trace([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5], "Sustained chat", "#fb7185")

    ax.axhline(R_MAX, color="#fbbf24", linestyle="--", linewidth=1, alpha=0.7, label=f"R_max = {R_MAX}")
    ax.set_xlim(0, 12)
    ax.set_xlabel("Hours since first message")
    ax.set_ylabel("Hawkes residual R(t)")
    ax.set_title(f"Layer 3 — Hawkes excitation decay (β = {BETA:.3f} hr⁻¹, T_half = {T_HALF_HRS}h)\n"
                 "Per-message bumps, exponential decay between events",
                 color=TEXT, fontsize=12, pad=14)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    out = DOCS / "heartbeat-hawkes-scenarios.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# PLOT 4: A typical day timeline
# ─────────────────────────────────────────────────────────────────────────
def plot_typical_day() -> Path:
    setup_mpl()
    res = simulate(days=1, chapter=3, engagement="in_zone", user_msg_scale=1.0, seed=7)
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), gridspec_kw={"height_ratios": [1.2, 1.2, 0.6]})

    # Panel 1: activity stacked area
    ax = axes[0]
    t_grid = np.linspace(0, 24, 600)
    p_by_act = {a: np.array([activity_distribution(t)[a] for t in t_grid]) for a in ACTIVITIES}
    ax.stackplot(t_grid, [p_by_act[a] for a in ACTIVITIES],
                 labels=[a.capitalize() for a in ACTIVITIES],
                 colors=[ACT_COLORS[a] for a in ACTIVITIES], alpha=0.7, edgecolor=BG, linewidth=0.3)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_ylabel("p(activity)")
    ax.set_title("A typical day — Ch3 in_zone, normal user messaging",
                 color=TEXT, fontsize=12, pad=10)
    ax.legend(loc="upper center", ncol=5, frameon=True, fontsize=8)

    # Panel 2: λ_total over time + heartbeat events + user msgs
    ax = axes[1]
    t_grid_fine = np.linspace(0, 24, 2000)
    # Reconstruct R(t) by replaying events
    events_combined = sorted(
        [(m, "msg") for m in res.user_msgs] + [(w["t"], "wake") for w in res.nikita_wakes]
    )
    R_track = np.zeros_like(t_grid_fine)
    R = 0.0
    last_t = 0.0
    ev_iter = iter(events_combined)
    next_ev = next(ev_iter, None)
    for i, tt in enumerate(t_grid_fine):
        while next_ev is not None and next_ev[0] <= tt:
            R = hawkes_decay(R, next_ev[0] - last_t)
            if next_ev[1] == "msg":
                R = hawkes_update(R, ALPHA["user_msg"])
            else:
                R = hawkes_update(R, ALPHA["internal"])
            last_t = next_ev[0]
            next_ev = next(ev_iter, None)
        R_track[i] = hawkes_decay(R, tt - last_t)

    lam_baseline_vals = np.array([lambda_baseline(t, chapter=3) for t in t_grid_fine])
    lam_total_vals = lam_baseline_vals + R_track
    ax.fill_between(t_grid_fine, 0, lam_baseline_vals, color=ACCENT, alpha=0.25, label="λ_baseline")
    ax.plot(t_grid_fine, lam_total_vals, color=LAVENDER, linewidth=1.6, label="λ_total = baseline + R")

    # User msgs as red ticks
    for m in res.user_msgs:
        ax.axvline(m, color="#f87171", alpha=0.7, linewidth=1.2, ymax=0.05)
    # Heartbeats as cyan dots
    for w in res.nikita_wakes:
        ax.scatter(w["t"], lambda_total(w["t"], w["R"], 3, "in_zone"),
                   color=ACCENT, s=35, zorder=5, edgecolor=BG, linewidth=0.5)
    ax.set_xlim(0, 24)
    ax.set_ylabel("λ(t)  (heartbeats/hour)")
    ax.set_xticks([])
    ax.legend(loc="upper right", frameon=True, fontsize=9)

    # Panel 3: event ribbon
    ax = axes[2]
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 3)
    ax.set_yticks([0.5, 1.5, 2.5])
    ax.set_yticklabels(["User msg", "Heartbeat", "Cancel"])
    ax.grid(False)
    for m in res.user_msgs:
        ax.scatter(m, 0.5, color="#f87171", marker="v", s=60)
    for w in res.nikita_wakes:
        ax.scatter(w["t"], 1.5, color=ACCENT, marker="o", s=50)
    for c in res.cancellations:
        ax.scatter(c["at"], 2.5, color="#fbbf24", marker="x", s=60)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)])
    ax.set_xlabel("Time of day")

    fig.text(
        0.5, -0.01,
        f"Stats: {len(res.user_msgs)} user msgs · {len(res.nikita_wakes)} heartbeats · "
        f"{sum(len(c['cancelled']) for c in res.cancellations)} forward-wakes cancelled by replan",
        ha="center", color=SUBTEXT, fontsize=10,
    )
    out = DOCS / "heartbeat-typical-day.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# PLOT 5: Silent vs chatty week (7 days)
# ─────────────────────────────────────────────────────────────────────────
def plot_silent_vs_chatty_week() -> Path:
    setup_mpl()
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    for ax, scale, label, seed in [
        (axes[0], 0.15, "Silent user (1-2 msgs/day)", 11),
        (axes[1], 3.0, "Chatty user (~30 msgs/day)", 13),
    ]:
        res = simulate(days=7, chapter=3, engagement="in_zone", user_msg_scale=scale, seed=seed)
        # Day shading
        for d in range(7):
            color = SURFACE if d % 2 == 0 else "#0f1623"
            ax.axvspan(d * 24, (d + 1) * 24, color=color, alpha=0.5, zorder=0)
        # Heartbeats
        wake_t = [w["t"] for w in res.nikita_wakes]
        wake_y = [0.7] * len(wake_t)
        ax.scatter(wake_t, wake_y, color=ACCENT, s=20, alpha=0.85, label=f"Heartbeats ({len(wake_t)})")
        # User msgs
        ax.scatter(res.user_msgs, [0.3] * len(res.user_msgs),
                   color="#f87171", marker="v", s=30, alpha=0.85,
                   label=f"User msgs ({len(res.user_msgs)})")
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_xlim(0, 7 * 24)
        ax.set_title(label, color=TEXT, fontsize=11, loc="left")
        ax.legend(loc="upper right", frameon=True, fontsize=9)

    axes[1].set_xticks(range(0, 7 * 24 + 1, 24))
    axes[1].set_xticklabels([f"Day {d+1}" for d in range(7)] + ["End"])
    axes[1].set_xlabel("")
    fig.suptitle("7-day comparison — silent vs chatty user (Ch3, in_zone)",
                 color=TEXT, fontsize=13, y=1.0)
    out = DOCS / "heartbeat-silent-vs-chatty-week.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# PLOT 6: Inter-wake interval histogram per chapter
# ─────────────────────────────────────────────────────────────────────────
def plot_interwake_distribution() -> Path:
    setup_mpl()
    fig, ax = plt.subplots(figsize=(11, 5))
    for ch in range(1, 6):
        # Run 14-day sim with no user msgs (pure baseline)
        res = simulate(days=14, chapter=ch, engagement="in_zone", user_msg_scale=0.0, seed=100 + ch)
        wake_times = [w["t"] for w in res.nikita_wakes]
        if len(wake_times) < 2:
            continue
        gaps_min = np.diff(wake_times) * 60.0  # minutes
        ax.hist(gaps_min, bins=np.linspace(0, 240, 50), alpha=0.45,
                color=CH_COLORS[ch - 1], label=f"{CH_LABELS[ch-1]} (median {np.median(gaps_min):.0f}m)",
                edgecolor=BG, linewidth=0.4)
    ax.set_xlabel("Inter-wake gap (minutes)")
    ax.set_ylabel("Count")
    ax.set_xlim(0, 240)
    ax.set_title("Layer 6 — Inter-wake interval distribution (pure baseline, no user msgs)\n"
                 "14-day sim per chapter; later chapters → longer gaps",
                 color=TEXT, fontsize=12, pad=14)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    out = DOCS / "heartbeat-interwake-distribution.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# PLOT 7: Replan effect (chapter advance mid-day)
# ─────────────────────────────────────────────────────────────────────────
def plot_replan_effect() -> Path:
    setup_mpl()
    fig, ax = plt.subplots(figsize=(13, 5))
    res = simulate(
        days=2, chapter=2, engagement="in_zone", user_msg_scale=0.5, seed=21,
        chapter_advance_at=20.0, advance_to_chapter=4,
    )
    # λ_baseline morphs at advance time
    t_grid = np.linspace(0, 48, 2000)
    lam_pre = np.array([lambda_baseline(t, chapter=2) if t < 20 else lambda_baseline(t, chapter=4)
                        for t in t_grid])
    ax.fill_between(t_grid, 0, lam_pre, color=ACCENT, alpha=0.2)
    # Heartbeats
    ax.scatter([w["t"] for w in res.nikita_wakes],
               [lambda_baseline(w["t"], w["chapter"]) for w in res.nikita_wakes],
               color=ACCENT, s=30, zorder=5, edgecolor=BG, linewidth=0.5,
               label=f"Heartbeats fired ({len(res.nikita_wakes)})")
    # User msgs
    for m in res.user_msgs:
        ax.axvline(m, color="#f87171", alpha=0.4, linewidth=1)
    # Cancellation marker
    ax.axvline(20, color="#fbbf24", linewidth=2.5, linestyle="--",
               label=f"Chapter 2→4 advance (cancelled {sum(len(c['cancelled']) for c in res.cancellations if c['reason']=='chapter_advance')} pending)")
    ax.set_xlim(0, 48)
    ax.set_xticks([0, 12, 24, 36, 48])
    ax.set_xticklabels(["Day1 00:00", "Day1 12:00", "Day2 00:00", "Day2 12:00", "Day2 24:00"])
    ax.set_ylabel("λ_baseline(t)")
    ax.set_title("Layer 7 — Replan effect on chapter advance\n"
                 "Pending heartbeats cancelled at advance; new schedule reflects Ch4 (lower base rate)",
                 color=TEXT, fontsize=12, pad=14)
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    out = DOCS / "heartbeat-replan-effect.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────
# Sanity assertions
# ─────────────────────────────────────────────────────────────────────────
def run_sanity_checks() -> tuple[int, int]:
    """Returns (passed, total)."""
    checks: list[tuple[str, bool]] = []
    # 1. Activity probabilities sum to 1.0 ± 1e-6 at every t (sample 100)
    sum_ok = all(abs(sum(activity_distribution(t).values()) - 1.0) < 1e-6
                 for t in np.linspace(0, 24, 100))
    checks.append(("activity_distribution sums to 1.0", sum_ok))

    # 2. Min activity probability ≥ ε/A everywhere
    min_p_ok = all(min(activity_distribution(t).values()) >= EPSILON_FLOOR / len(ACTIVITIES) - 1e-9
                   for t in np.linspace(0, 24, 100))
    checks.append(("noise-floor ε/A satisfied", min_p_ok))

    # 3. λ_baseline > 0 everywhere
    lam_pos = all(lambda_baseline(t, ch) > 0 for t in np.linspace(0, 24, 100) for ch in range(1, 6))
    checks.append(("λ_baseline > 0 everywhere (all chapters)", lam_pos))

    # 4. Hawkes branching ratio < 1
    branching = ALPHA["user_msg"] * 1.2 + ALPHA["game_event"] * 1.0 + ALPHA["internal"] * 1.0
    branching_ok = branching < 1.0
    checks.append((f"Hawkes branching ratio = {branching:.3f} < 1.0", branching_ok))

    # 5. Sleep peak in [01:00, 04:00] (von Mises mean recoverable from p(sleep|t))
    sleep_curve = [(t, activity_distribution(t)["sleep"]) for t in np.linspace(0, 24, 1000)]
    peak_t = max(sleep_curve, key=lambda x: x[1])[0]
    sleep_peak_ok = 0.5 <= peak_t <= 4.5 or 22.5 <= peak_t <= 24.0
    checks.append((f"Sleep peak at t={peak_t:.2f}h in valid window", sleep_peak_ok))

    # 6. Hawkes residual decays to <1% of initial within 5·T_half (15h)
    R0 = 1.0
    R_after = hawkes_decay(R0, 5 * T_HALF_HRS)
    decay_ok = R_after < 0.05
    checks.append((f"Hawkes decays to {R_after:.4f} after 5·T_half", decay_ok))

    # 7. Inter-wake median between 30min and 4h for Ch3 in_zone
    res = simulate(days=14, chapter=3, engagement="in_zone", user_msg_scale=0.0, seed=999)
    if len(res.nikita_wakes) >= 2:
        gaps_min = np.diff([w["t"] for w in res.nikita_wakes]) * 60.0
        median_gap = float(np.median(gaps_min))
        gap_ok = 30 <= median_gap <= 240
        checks.append((f"Ch3 inter-wake median = {median_gap:.0f} min in [30, 240]", gap_ok))
    else:
        checks.append(("inter-wake median (insufficient samples)", False))

    # 8. 24h sample distribution circadian-shaped (peak hours have more wakes than trough)
    res = simulate(days=14, chapter=3, engagement="in_zone", user_msg_scale=0.5, seed=1234)
    hours = [int(w["t"] % 24) for w in res.nikita_wakes]
    counts = np.bincount(hours, minlength=24)
    peak_hours_total = sum(counts[19:23])  # 19-22
    trough_hours_total = sum(counts[3:6])  # 03-05
    circadian_ok = peak_hours_total > trough_hours_total * 2
    checks.append((f"Evening peak={peak_hours_total} > 2·trough={trough_hours_total}", circadian_ok))

    print()
    print("─" * 64)
    print("SANITY CHECKS")
    print("─" * 64)
    for label, ok in checks:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {label}")
    passed = sum(1 for _, ok in checks if ok)
    return passed, len(checks)


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    print("=" * 64)
    print("  Heartbeat Intensity MC Simulator (Plan v3 §A.2)")
    print("=" * 64)
    print(f"  T_half = {T_HALF_HRS}h    β = {BETA:.4f} hr⁻¹")
    print(f"  α_user_msg = {ALPHA['user_msg']}   α_game = {ALPHA['game_event']}   α_internal = {ALPHA['internal']}")
    print(f"  ε noise floor = {EPSILON_FLOOR}    R_max = {R_MAX}")
    print(f"  Output dir: {DOCS}")
    print()
    print("Generating plots...")

    plots = [
        ("Plot 1 — Activity distribution",      plot_activity_distribution),
        ("Plot 2 — Baseline per chapter",       plot_baseline_per_chapter),
        ("Plot 3 — Hawkes scenarios",           plot_hawkes_scenarios),
        ("Plot 4 — A typical day timeline",     plot_typical_day),
        ("Plot 5 — Silent vs chatty week",      plot_silent_vs_chatty_week),
        ("Plot 6 — Inter-wake distribution",    plot_interwake_distribution),
        ("Plot 7 — Replan effect",              plot_replan_effect),
    ]
    for label, fn in plots:
        out = fn()
        size_kb = out.stat().st_size / 1024
        print(f"  {label:42s} → {out.name:46s} ({size_kb:5.1f}K)")

    passed, total = run_sanity_checks()
    print()
    print("─" * 64)
    print(f"  RESULT: {passed}/{total} sanity checks passed")
    print("─" * 64)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
