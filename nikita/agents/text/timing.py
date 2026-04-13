"""Response timing module for Nikita text agent (Spec 210 v2).

Computes the response delay Nikita waits before replying to an incoming
message. Delay fires **only on new-conversation starts** (≥ 15-minute gap
since the user's last message) — ongoing ping-pong exchanges return 0.

Model (see ``docs/models/response-timing.md``):

.. code-block:: text

    delay = min(chapter_cap[ch],  exp(mu + sigma*Z) * c_ch * M)

- ``exp(mu + sigma*Z)``  : base log-normal sample (Z ~ N(0, 1))
- ``c_ch``               : per-chapter coefficient (excitement-fades; Ch1 smallest)
- ``M``                  : momentum coefficient from :mod:`conversation_rhythm`
- ``chapter_cap[ch]``    : per-chapter hard ceiling (Ch1 = 10s, Ch5 = 1800s)

**Why log-normal?** Empirically the best fit for casual human messaging
response latency (Stouffer 2006 vs. Barabási 2005; Malmgren 2009). Natural
right skew, finite variance, multiplicative interpretation.

**Why excitement-fades coefficients?** Dopamine-driven infatuation produces
hyper-responsive early-chapter cadence (Fisher 2004; Berger & Calabrese
1975 URT); established relationships reply slower (Scissors 2014).

**Dev-mode bypass**: when ``ENVIRONMENT=development`` or ``DEBUG=true``,
:meth:`ResponseTimer.calculate_delay` returns 0 unconditionally so local
iteration is fast.

See also:
    - :mod:`nikita.agents.text.conversation_rhythm` — momentum coefficient
    - ``specs/210-kill-skip-variable-response/spec.md`` — FR-005..FR-015
    - ``.claude/rules/stochastic-models.md`` — governance rule
    - ``scripts/models/response_timing_mc.py`` — Monte Carlo validator
"""

from __future__ import annotations

import logging
import math
import random
from typing import Final

from nikita.agents.text.conversation_rhythm import (
    MOMENTUM_HI,
    MOMENTUM_LO,
)
from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Model parameters                                                            #
# --------------------------------------------------------------------------- #

# Log-normal base parameters. exp(mu) is the base median delay in seconds.
# With mu = 2.996 the base median is ~20s; sigma = 1.714 gives a p90 of ~3min.
# These are tuning constants validated by scripts/models/response_timing_mc.py.
LOGNORMAL_MU: Final[float] = 2.996
LOGNORMAL_SIGMA: Final[float] = 1.714

# Per-chapter multiplicative coefficients. Monotone-increasing with chapter
# (excitement fades). Applied to the log-normal sample before the cap clamp.
CHAPTER_COEFFICIENTS: Final[dict[int, float]] = {
    1: 0.15,  # Infatuation: ~3s median after multiplication
    2: 0.30,  # Very eager: ~6s
    3: 0.50,  # Attentive: ~10s
    4: 0.75,  # Comfortable: ~15s
    5: 1.00,  # Settled: ~20s (baseline)
}

# Per-chapter HARD caps (seconds). The delay is clamped to [0, cap] AFTER all
# multipliers. Ch1 is aggressively capped at 10s so users almost never wait.
CHAPTER_CAPS_SECONDS: Final[dict[int, int]] = {
    1: 10,     # 10 seconds
    2: 60,     # 1 minute
    3: 300,    # 5 minutes
    4: 900,    # 15 minutes
    5: 1800,   # 30 minutes
}

# Default fallbacks for unknown/invalid chapters (treat like Ch1).
DEFAULT_COEFFICIENT: Final[float] = CHAPTER_COEFFICIENTS[1]
DEFAULT_CAP_SECONDS: Final[int] = CHAPTER_CAPS_SECONDS[1]

# Legacy constant retained for back-compat with a few test modules that still
# import it. DO NOT use in new code — rely on CHAPTER_COEFFICIENTS /
# CHAPTER_CAPS_SECONDS instead. Kept as (0, cap) for each chapter so any
# legacy ``min_sec <= delay <= max_sec`` assertions still pass with delay=0.
TIMING_RANGES: Final[dict[int, tuple[int, int]]] = {
    ch: (0, CHAPTER_CAPS_SECONDS[ch]) for ch in CHAPTER_CAPS_SECONDS
}
DEFAULT_TIMING_RANGE: Final[tuple[int, int]] = TIMING_RANGES[1]


# --------------------------------------------------------------------------- #
# ResponseTimer                                                               #
# --------------------------------------------------------------------------- #


class ResponseTimer:
    """Compute response delay using log-normal × chapter × momentum.

    The delay is sampled per call (non-deterministic). Clamped to
    ``[0, CHAPTER_CAPS_SECONDS[chapter]]`` after all multipliers.

    Example::

        timer = ResponseTimer()
        delay = timer.calculate_delay(
            chapter=1,
            is_new_conversation=True,
            momentum=0.8,
        )
        # Returns an int in [0, 10] for Ch1.
    """

    def __init__(self, jitter_factor: float = 0.0) -> None:
        # jitter_factor retained for backwards-compat with old tests; the
        # log-normal sample already provides natural variance.
        self.jitter_factor = jitter_factor

    def calculate_delay(
        self,
        chapter: int,
        *,
        is_new_conversation: bool = True,
        momentum: float = 1.0,
    ) -> int:
        """Compute the delay in seconds for a new Nikita response.

        Args:
            chapter: The user's current chapter (1-5). Invalid -> Ch1 fallback.
            is_new_conversation: Whether this message starts a new session
                (gap ≥ 15 min since last user message). If False, return 0
                immediately (ongoing ping-pong — no delay).
            momentum: Momentum coefficient M in
                ``[MOMENTUM_LO, MOMENTUM_HI]`` from
                :func:`conversation_rhythm.compute_momentum`. Defaults to
                1.0 (neutral).

        Returns:
            Integer seconds in ``[0, CHAPTER_CAPS_SECONDS[chapter]]``.

        Notes:
            - Dev-mode bypass returns 0 when env=development or debug=True.
            - Ongoing conversations (is_new_conversation=False) always
              return 0 — momentum is irrelevant there.
            - Boss-fight / won states bypass this function entirely (see
              ``nikita/agents/text/handler.py`` lines ~340-356).
        """
        # Dev-mode bypass (keeps local iteration fast)
        settings = get_settings()
        if settings.environment == "development" or settings.debug:
            logger.info(
                "[TIMING] Development mode: bypassing delay for chapter %s",
                chapter,
            )
            return 0

        # Ongoing session -> no delay
        if not is_new_conversation:
            return 0

        coeff = CHAPTER_COEFFICIENTS.get(chapter, DEFAULT_COEFFICIENT)
        cap = CHAPTER_CAPS_SECONDS.get(chapter, DEFAULT_CAP_SECONDS)

        # Clamp momentum defensively (should already be bounded upstream)
        m = max(MOMENTUM_LO, min(MOMENTUM_HI, float(momentum)))

        # Log-normal sample: exp(mu + sigma * Z), Z ~ N(0, 1)
        z = random.gauss(0.0, 1.0)
        base = math.exp(LOGNORMAL_MU + LOGNORMAL_SIGMA * z)

        raw = base * coeff * m

        # Clamp to [0, cap] and cast to int
        delay = int(max(0.0, min(float(cap), raw)))

        logger.info(
            "[TIMING] ch=%s is_new=%s m=%.2f base=%.1fs coeff=%.2f -> delay=%ss (cap=%s)",
            chapter,
            is_new_conversation,
            m,
            base,
            coeff,
            delay,
            cap,
        )
        return delay

    def calculate_delay_human_readable(
        self,
        chapter: int,
        *,
        is_new_conversation: bool = True,
        momentum: float = 1.0,
    ) -> str:
        """Calculate delay and return in human-readable format.

        Same semantics as :meth:`calculate_delay` but formatted as a short
        English string (e.g., ``"3 minutes"``, ``"8 seconds"``).
        """
        seconds = self.calculate_delay(
            chapter,
            is_new_conversation=is_new_conversation,
            momentum=momentum,
        )
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)

        parts: list[str] = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs and not parts:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")
        return " ".join(parts) if parts else "0 seconds"
