"""Per-turn Big Five inference judge (Spec 216-D, D1.5).

After every prose answer slot (saturday_morning, geek_out_on, together_we_could,
same_weird_if, primary_hobbies + optional probes), this judge invokes a Haiku
model to score the user's prose along the 5 OCEAN dimensions and merges the
result into a cumulative ``big5_vector`` per the Bayesian-merge formula.

NR-05 enforcement (single-source-of-truth, .claude/rules/agentic-design-patterns.md):
  - This module's outputs are SERVER-SIDE state ONLY.
  - The 8 forbidden personality terms (big5, ocean, openness, conscientiousness,
    extraversion, agreeableness, neuroticism, confidence) MUST NEVER appear
    in any TurnOutput, AnswerResponse, or StateResponse field name.
  - Tested in tests/agents/onboarding/test_no_big5_in_response.py.

Bayesian merge (per spec D1.5):

  total_w = prior_conf + new_conf
  if total_w == 0:
      → (new_score, new_conf)
  else:
      merged_score = (prior * prior_conf + new_score * new_conf) / total_w
      merged_conf  = min(0.95, prior_conf + new_conf * (1 - prior_conf))

Confidence thresholds:
  - 0.5  → "weak signal"  → continue probing
  - 0.7  → "strong signal" → M4 short-circuits further probes on that axis
  - 0.95 → asymptotic ceiling

The actual Haiku call is dependency-injected so unit tests pass a mock that
returns golden vectors. 216-E wires the production Anthropic client.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Final


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

# OCEAN dimension keys — single-letter alphabetic to keep server-side state
# compact AND opaque to anyone reading the JSONB. Alphabetic order: openness,
# conscientiousness, extraversion, agreeableness, neuroticism.
DIMS: Final[tuple[str, ...]] = ("O", "C", "E", "A", "N")

WEAK_SIGNAL_THRESHOLD: Final[float] = 0.5
"""Per-dim confidence at or below which we treat the signal as weak.

Current value: 0.5 (Spec 216-D-code, D1.5 introduction).
Rationale: spec D1.5 calls 0.5 the "weak signal — continue probing"
boundary. Below it the planner keeps probing the dim across more turns;
above it the planner can move on. Single source of truth — referenced
only in this module.
"""

STRONG_SIGNAL_THRESHOLD: Final[float] = 0.7
"""Per-dim confidence at or above which the planner short-circuits further
probes on that axis (M4 short-circuit per spec D1.5).

Current value: 0.7 (Spec 216-D-code, D1.5 introduction).
Rationale: spec D1.5 calls 0.7 the "strong signal — M4 short-circuit"
boundary. Above it the inference is reliable enough to skip subsequent
probes targeting that dim, freeing budget for under-sampled dims.
"""

CONFIDENCE_CEILING: Final[float] = 0.95
"""Asymptotic ceiling on per-dim confidence after Bayesian merge.

Current value: 0.95 (Spec 216-D-code, D1.5 introduction).
Rationale: spec D1.5 mandates "asymptotic to 0.95" so confidence never
saturates at 1.0 — leaves epistemic room for late-conversation
correction. Hard cap; do NOT raise without UX/eng review.
"""

SCORE_MIN: Final[float] = 0.0
SCORE_MAX: Final[float] = 1.0
"""Per-dim score range (inclusive). Hard bounds applied during merge.

Spec D1.5: each dim is a float in [0, 1]. Out-of-range Haiku output is
clamped + logged (defensive — never raises in production)."""

_EXCEPTION_LOG_MAX_LEN: Final[int] = 200
"""Max chars logged for a judge-call exception repr.

Current value: 200 (Spec 216-D-code, hardening on QA review).
Rationale: Anthropic SDK 4xx errors can echo the request prefix in the
exception message, which would leak the user's prose to Cloud Run logs.
Bounding the logged repr to 200 chars keeps triage signal (exception
type + first line) without echoing arbitrary user content. The exception
class is logged separately via ``type(exc).__name__``.
"""


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# A judge call returns the cumulative server-side vector shape:
#   {"O": 0.x, "C": 0.x, "E": 0.x, "A": 0.x, "N": 0.x,
#    "confidence": {"O": 0.x, "C": 0.x, "E": 0.x, "A": 0.x, "N": 0.x}}
# This is purely server-side state — it is persisted to ``users.big5_vector``
# JSONB and consumed by the planner's saturation check. NR-05 governs only
# the HTTP response surface (response-model FIELD names), not server-side
# dict keys; the ``Big5Vector`` alias is internal and never leaks into any
# Pydantic response model. We use ``dict[str, Any]`` rather than a more
# precise TypedDict to keep this module dependency-light.
Big5Vector = dict[str, Any]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _clamp(x: float, lo: float = SCORE_MIN, hi: float = SCORE_MAX) -> float:
    """Clamp ``x`` into ``[lo, hi]`` — defensive against out-of-range LLM output."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _validate_judge_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalize a judge payload.

    Returns a new dict with all 5 dims + a confidence dict, each value clamped
    to ``[SCORE_MIN, SCORE_MAX]``. Raises ``ValueError`` on missing dim or
    missing confidence dict (Haiku contract is non-negotiable).
    """
    if not isinstance(payload, dict):
        raise ValueError(
            f"judge output must be a dict, got {type(payload).__name__}"
        )
    out: dict[str, Any] = {}
    for d in DIMS:
        if d not in payload:
            raise ValueError(f"judge output missing dim {d!r}; got keys {sorted(payload.keys())}")
        out[d] = _clamp(float(payload[d]))
    conf_in = payload.get("confidence")
    if not isinstance(conf_in, dict):
        raise ValueError(
            "judge output missing 'confidence' dict; "
            f"got type {type(conf_in).__name__}"
        )
    out_conf: dict[str, float] = {}
    for d in DIMS:
        if d not in conf_in:
            raise ValueError(
                f"judge output missing confidence for dim {d!r}; "
                f"got keys {sorted(conf_in.keys())}"
            )
        out_conf[d] = _clamp(float(conf_in[d]))
    out["confidence"] = out_conf
    return out


# ---------------------------------------------------------------------------
# Bayesian merge
# ---------------------------------------------------------------------------


def merge_dim(
    prior: float,
    prior_conf: float,
    new_score: float,
    new_conf: float,
) -> tuple[float, float]:
    """Merge a single dim's prior + new sample via the spec D1.5 formula.

    Returns ``(merged_score, merged_conf)``. Both clamped to their valid
    ranges. ``merged_conf`` asymptotes to ``CONFIDENCE_CEILING``.
    """
    total_weight = prior_conf + new_conf
    if total_weight == 0:
        return _clamp(new_score), _clamp(new_conf, hi=CONFIDENCE_CEILING)
    merged_score = (prior * prior_conf + new_score * new_conf) / total_weight
    merged_conf = min(
        CONFIDENCE_CEILING,
        prior_conf + new_conf * (1 - prior_conf),
    )
    return _clamp(merged_score), _clamp(merged_conf, hi=CONFIDENCE_CEILING)


def merge_vector(prior: Big5Vector, new: Big5Vector) -> Big5Vector:
    """Merge a new judge sample into the cumulative vector.

    ``prior`` may be empty (first turn). Both vectors are validated /
    normalized via ``_validate_judge_output`` for ``new``; ``prior`` is
    treated as already-normalized (server-side trust boundary).
    """
    new_norm = _validate_judge_output(new)
    out: Big5Vector = {}
    out_conf: dict[str, float] = {}
    prior_conf = prior.get("confidence") if isinstance(prior, dict) else None
    for d in DIMS:
        prior_score = (
            float(prior.get(d, 0.0)) if isinstance(prior, dict) else 0.0
        )
        prior_dim_conf = (
            float(prior_conf.get(d, 0.0))
            if isinstance(prior_conf, dict)
            else 0.0
        )
        merged_score, merged_conf = merge_dim(
            prior_score,
            prior_dim_conf,
            new_norm[d],
            new_norm["confidence"][d],
        )
        out[d] = merged_score
        out_conf[d] = merged_conf
    out["confidence"] = out_conf
    return out


# ---------------------------------------------------------------------------
# Saturation / short-circuit query
# ---------------------------------------------------------------------------


def saturated_dims(vec: Big5Vector) -> list[str]:
    """Return the list of dim keys whose confidence ≥ STRONG_SIGNAL_THRESHOLD.

    The planner uses this to short-circuit further probes on saturated axes
    (M4 short-circuit per spec D1.5).
    """
    if not isinstance(vec, dict):
        return []
    conf = vec.get("confidence")
    if not isinstance(conf, dict):
        return []
    return [
        d for d in DIMS if float(conf.get(d, 0.0)) >= STRONG_SIGNAL_THRESHOLD
    ]


def is_dim_saturated(vec: Big5Vector, dim: str) -> bool:
    """True iff the specified dim's confidence ≥ STRONG_SIGNAL_THRESHOLD."""
    if dim not in DIMS:
        raise ValueError(f"dim {dim!r} not in {DIMS}")
    if not isinstance(vec, dict):
        return False
    conf = vec.get("confidence")
    if not isinstance(conf, dict):
        return False
    return float(conf.get(dim, 0.0)) >= STRONG_SIGNAL_THRESHOLD


# ---------------------------------------------------------------------------
# Public update entrypoint
# ---------------------------------------------------------------------------


# A judge callable accepts (prose, prior_vector) and returns the new sample
# {O, C, E, A, N, confidence: {...}}. 216-E wires the Haiku-backed default;
# 216-D-code ships the dependency-injected surface so unit tests can stub it.
JudgeCallable = Callable[[str, Big5Vector], Awaitable[dict[str, Any]]]


async def update_big5_vector(
    *,
    prose: str,
    prior_vector: Big5Vector | None,
    judge: JudgeCallable,
) -> Big5Vector:
    """Per-turn Big5 update entrypoint (D1.5).

    Calls ``judge(prose, prior_vector)`` to get a new sample, then merges it
    into ``prior_vector`` via the spec Bayesian formula.

    The caller (route layer in 216-E) passes the cumulative ``prior_vector``
    loaded from ``users.big5_vector`` JSONB and writes the returned vector
    back. ``prose`` is the user's literal answer for the current slot.

    On any judge / merge error the function logs and returns the prior
    vector unchanged — never raises in production. Personality inference is
    a hidden enrichment surface; failure must be silent (NR-05).
    """
    if not isinstance(prose, str) or not prose.strip():
        return prior_vector or {}
    prior = prior_vector or {}
    try:
        sample = await judge(prose, prior)
        merged = merge_vector(prior, sample)
        return merged
    except Exception as exc:
        # NEVER re-raise — surface stays hidden (NR-05). Log enough to triage
        # without echoing the user's prose back to logs. Anthropic SDK 4xx
        # errors can include the request prefix (= user input), so we log
        # only the exception class + a bounded-length repr (no prose).
        exc_repr = repr(exc)
        if len(exc_repr) > _EXCEPTION_LOG_MAX_LEN:
            exc_repr = exc_repr[:_EXCEPTION_LOG_MAX_LEN] + "..."
        logger.warning(
            "big5_judge_update_failed exc_type=%s exc=%s prior_keys=%s",
            type(exc).__name__,
            exc_repr,
            sorted(prior.keys()) if isinstance(prior, dict) else None,
        )
        return prior


__all__ = [
    "Big5Vector",
    "CONFIDENCE_CEILING",
    "DIMS",
    "JudgeCallable",
    "SCORE_MAX",
    "SCORE_MIN",
    "STRONG_SIGNAL_THRESHOLD",
    "WEAK_SIGNAL_THRESHOLD",
    "is_dim_saturated",
    "merge_dim",
    "merge_vector",
    "saturated_dims",
    "update_big5_vector",
]
