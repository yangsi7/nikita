"""Conversation rhythm helpers for Spec 210 v2.

Pure functions that compute the **momentum coefficient M**, a multiplicative
scalar applied to the base log-normal × chapter response-delay model.

Momentum captures conversation pacing reciprocity: when the user has been
responding quickly, Nikita responds quickly in turn; when the user lets the
conversation cool, Nikita's replies stretch out. This is a simple, bounded
analogue of Hawkes-style self-exciting processes (Hawkes 1971; Avrahami &
Hudson 2006 on CMC responsiveness; Jacobson 1988 on EWMA smoothing).

Formulation (documented in ``docs/models/response-timing.md``):

.. code-block:: text

    B_ch = chapter baseline inter-message gap (seconds)
    S    = B_ch                              # prior seed
    for g in gap_history[-10:]:
        S = alpha*g + (1-alpha)*S            # EWMA update
    M    = clip(S / B_ch, M_LO, M_HI)

**Bayesian interpretation.** The EWMA seeded at ``B_ch`` is equivalent to the
posterior mean under a log-normal likelihood ``log(g) ~ N(mu_p, sigma_obs**2)``
with a Normal prior ``mu_p ~ N(log(B_ch), sigma_prior**2)``. Choosing
``alpha ≈ sigma_obs**2 / (sigma_obs**2 + sigma_prior**2 * N)`` recovers the
conjugate update; with our defaults (``alpha=0.35``, ``sigma_obs=0.6``,
``sigma_prior=0.8``) the posterior contracts meaningfully after ~3
observations while keeping the chapter prior dominant on cold start.

See also:
    - ``nikita/agents/text/timing.py`` — applies M inside ``ResponseTimer``
    - ``docs/models/response-timing.md`` — full derivation, MC results,
      citations (Stouffer 2006, Wu 2010, Malmgren 2009, Fisher 2004,
      Berger & Calabrese 1975, Scissors 2014)
    - ``specs/210-kill-skip-variable-response/spec.md`` FR-013
    - ``.claude/rules/stochastic-models.md`` — governance rule
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Final

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

# Chapter baseline inter-message gap in seconds. Acts as the prior for the
# EWMA posterior. Lower baselines mean "expected cadence is faster" at that
# chapter, so the same absolute user gap maps to a higher M (slower Nikita).
CHAPTER_BASELINES_SECONDS: Final[dict[int, int]] = {
    1: 300,  # Infatuation: 5 min baseline
    2: 240,  # Very eager: 4 min
    3: 180,  # Attentive: 3 min
    4: 120,  # Comfortable: 2 min
    5: 90,   # Settled: 1.5 min
}

# EWMA smoothing factor in [0, 1]. Higher alpha = faster reaction to the most
# recent gap; lower alpha = smoother, more prior-driven. See Jacobson 1988 for
# TCP RTT smoothing analogue (classic alpha=0.125; we use 0.35 because the
# sample-rate is per-message, not per-ack, and we want visible reactivity).
MOMENTUM_ALPHA: Final[float] = 0.35

# Hard bounds on the final M coefficient. These prevent pathological
# feedback spirals even at adversarial user behavior (see pitfalls section of
# docs/models/response-timing.md).
MOMENTUM_LO: Final[float] = 0.1
MOMENTUM_HI: Final[float] = 5.0

# Gaps greater than or equal to this value are treated as session breaks, not
# in-session reciprocity data, and are dropped from ``gap_history``. Matches
# ``TEXT_SESSION_TIMEOUT_MINUTES = 15`` in nikita/context/session_detector.py.
SESSION_BREAK_SECONDS: Final[int] = 900

# Hard cap on the history window: at most this many of the most recent gaps
# are considered when computing M.
WINDOW_SIZE: Final[int] = 10

# Minimum delta floor (seconds) — avoids log(0) downstream and protects
# against two messages that arrive with the same timestamp (clock jitter /
# same-second events).
MIN_DELTA_SECONDS: Final[float] = 1.0


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


def compute_momentum(gap_history: list[float], chapter: int) -> float:
    """Compute the momentum coefficient M from a user-turn gap history.

    Args:
        gap_history: Most-recent-last list of user-turn inter-message gaps
            in seconds. Should already be session-break-filtered via
            ``_compute_user_gaps``. May be empty.
        chapter: The user's current chapter (1-5). Invalid chapters fall
            back to the Chapter 1 baseline.

    Returns:
        A finite scalar in the closed interval ``[MOMENTUM_LO, MOMENTUM_HI]``.
        Returns exactly ``1.0`` when ``gap_history`` is empty.
    """
    if not gap_history:
        return 1.0

    baseline = CHAPTER_BASELINES_SECONDS.get(
        chapter, CHAPTER_BASELINES_SECONDS[1]
    )

    # Seed EWMA at the chapter baseline (Bayesian prior). Iterate over at
    # most WINDOW_SIZE most-recent entries in oldest-first order so the
    # latest observation has the greatest weight.
    window = gap_history[-WINDOW_SIZE:]
    ewma = float(baseline)
    for gap in window:
        ewma = MOMENTUM_ALPHA * float(gap) + (1.0 - MOMENTUM_ALPHA) * ewma

    raw = ewma / float(baseline)
    return max(MOMENTUM_LO, min(MOMENTUM_HI, raw))


def _compute_user_gaps(messages: list[dict]) -> list[float]:
    """Extract the last-N user-turn inter-message gaps in seconds.

    Filters the conversation history to user turns only, parses their
    timestamps, computes consecutive deltas, drops session breaks, floors
    sub-second deltas at :data:`MIN_DELTA_SECONDS`, and returns at most
    the last :data:`WINDOW_SIZE` deltas in oldest-first order.

    Messages with missing or unparseable timestamps are silently skipped
    (defensive; malformed rows must not crash the timing path).

    Args:
        messages: List of message dicts with ``role`` and ``timestamp``
            fields. Timestamps are produced by ``Conversation.add_message``
            via ``datetime.now().isoformat()`` — currently naive local time.
            We parse all entries in the same naive space so deltas remain
            consistent within a single conversation.

    Returns:
        List of floats (seconds), oldest first, length ``<= WINDOW_SIZE``.
    """
    if not messages:
        return []

    parsed: list[datetime] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        raw_ts = msg.get("timestamp")
        if not isinstance(raw_ts, str):
            continue
        try:
            ts = datetime.fromisoformat(raw_ts)
        except (ValueError, TypeError):
            continue
        parsed.append(ts)

    if len(parsed) < 2:
        return []

    # Defensive sort — insertion order should already be chronological
    parsed.sort()

    deltas: list[float] = []
    prev = parsed[0]
    for ts in parsed[1:]:
        raw = (ts - prev).total_seconds()
        prev = ts
        if raw >= SESSION_BREAK_SECONDS:
            # Session break — drop this delta entirely
            continue
        if raw < MIN_DELTA_SECONDS:
            raw = MIN_DELTA_SECONDS
        deltas.append(float(raw))

    return deltas[-WINDOW_SIZE:]
