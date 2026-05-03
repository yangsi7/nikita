"""Tests for big5_judge.py — Spec 216-D, D1.5.

Covers:
  - Tuning constants are exact (regression guard per tuning-constants.md)
  - ``merge_dim`` Bayesian formula correctness
  - ``merge_dim`` confidence asymptotes to 0.95
  - ``merge_vector`` empty-prior path
  - ``saturated_dims`` / ``is_dim_saturated`` short-circuit gate (≥0.7)
  - ``update_big5_vector`` calls injected judge + merges
  - Judge exception → returns prior unchanged (NEVER raises)
  - Validator rejects malformed payload + missing dims
"""

from __future__ import annotations

from typing import Any

import pytest

from nikita.agents.onboarding.big5_judge import (
    CONFIDENCE_CEILING,
    DIMS,
    SCORE_MAX,
    SCORE_MIN,
    STRONG_SIGNAL_THRESHOLD,
    WEAK_SIGNAL_THRESHOLD,
    _validate_judge_output,
    is_dim_saturated,
    merge_dim,
    merge_vector,
    saturated_dims,
    update_big5_vector,
)


# ---------------------------------------------------------------------------
# Tuning constant regression guards (per tuning-constants.md)
# ---------------------------------------------------------------------------


def test_dims_are_exactly_five_ocean_letters() -> None:
    """Dim keys are the 5 OCEAN single letters in canonical order."""
    assert DIMS == ("O", "C", "E", "A", "N")


def test_threshold_constants_are_exact() -> None:
    """Spec D1.5 mandates these exact values; drift requires spec amendment."""
    assert WEAK_SIGNAL_THRESHOLD == 0.5
    assert STRONG_SIGNAL_THRESHOLD == 0.7
    assert CONFIDENCE_CEILING == 0.95


def test_score_range_constants() -> None:
    assert SCORE_MIN == 0.0
    assert SCORE_MAX == 1.0


# ---------------------------------------------------------------------------
# merge_dim Bayesian formula
# ---------------------------------------------------------------------------


def test_merge_dim_zero_prior_returns_new_sample() -> None:
    """First sample (prior_conf=0) → returns the new sample directly."""
    score, conf = merge_dim(prior=0.0, prior_conf=0.0, new_score=0.6, new_conf=0.4)
    assert score == pytest.approx(0.6)
    assert conf == pytest.approx(0.4)


def test_merge_dim_weighted_average_score() -> None:
    """Weighted average — higher confidence dominates."""
    # prior 0.2 with conf 0.1, new 0.8 with conf 0.9
    # merged = (0.2*0.1 + 0.8*0.9) / (0.1 + 0.9) = 0.74
    score, _conf = merge_dim(prior=0.2, prior_conf=0.1, new_score=0.8, new_conf=0.9)
    assert score == pytest.approx(0.74, rel=1e-6)


def test_merge_dim_confidence_asymptotic_to_ceiling() -> None:
    """Iterative merging caps confidence at CONFIDENCE_CEILING (0.95)."""
    score, conf = 0.5, 0.0
    for _ in range(100):
        score, conf = merge_dim(prior=score, prior_conf=conf, new_score=0.5, new_conf=0.7)
    assert conf <= CONFIDENCE_CEILING + 1e-9
    assert conf == pytest.approx(CONFIDENCE_CEILING, rel=1e-3)


def test_merge_dim_confidence_increases_monotonically() -> None:
    """Successive merges only ever increase confidence (asymptotic)."""
    score, conf = 0.5, 0.1
    last = conf
    for _ in range(20):
        score, conf = merge_dim(prior=score, prior_conf=conf, new_score=0.5, new_conf=0.3)
        assert conf >= last - 1e-9
        last = conf


def test_merge_dim_clamps_out_of_range_score() -> None:
    """Defensive: out-of-range new_score clamps to [0, 1]."""
    score, _conf = merge_dim(prior=0.0, prior_conf=0.0, new_score=1.5, new_conf=0.5)
    assert score == 1.0
    score2, _conf2 = merge_dim(prior=0.0, prior_conf=0.0, new_score=-0.3, new_conf=0.5)
    assert score2 == 0.0


# ---------------------------------------------------------------------------
# merge_vector — empty + populated priors
# ---------------------------------------------------------------------------


def _golden_sample(o: float = 0.7, c: float = 0.5, e: float = 0.6, a: float = 0.4, n: float = 0.3) -> dict[str, Any]:
    return {
        "O": o,
        "C": c,
        "E": e,
        "A": a,
        "N": n,
        "confidence": {"O": 0.6, "C": 0.5, "E": 0.7, "A": 0.4, "N": 0.3},
    }


def test_merge_vector_empty_prior_returns_validated_sample() -> None:
    """Empty prior → returned vector has all 5 dims + confidence dict."""
    out = merge_vector({}, _golden_sample())
    for d in DIMS:
        assert d in out
    assert "confidence" in out
    for d in DIMS:
        assert d in out["confidence"]


def test_merge_vector_assertions_on_two_samples() -> None:
    """Two consecutive merges produce a vector whose confidence values are
    higher than either sample's individual confidence."""
    sample1 = _golden_sample()
    after_1 = merge_vector({}, sample1)
    sample2 = _golden_sample(o=0.4)
    after_2 = merge_vector(after_1, sample2)
    # After two merges the O-confidence should be higher than either input.
    assert after_2["confidence"]["O"] > sample1["confidence"]["O"]
    assert after_2["confidence"]["O"] > sample2["confidence"]["O"]


def test_merge_vector_clamps_confidence_to_ceiling() -> None:
    """Iterating merges with high-conf samples never breaks the ceiling."""
    state: dict[str, Any] = {}
    for _ in range(50):
        state = merge_vector(state, _golden_sample())
    for d in DIMS:
        assert state["confidence"][d] <= CONFIDENCE_CEILING + 1e-9


# ---------------------------------------------------------------------------
# Saturation gate (≥0.7 short-circuit)
# ---------------------------------------------------------------------------


def test_saturated_dims_returns_empty_for_low_confidence() -> None:
    vec = {
        "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5,
        "confidence": {"O": 0.4, "C": 0.5, "E": 0.6, "A": 0.5, "N": 0.4},
    }
    assert saturated_dims(vec) == []


def test_saturated_dims_includes_dims_at_or_above_threshold() -> None:
    """≥0.7 saturates; <0.7 does not (spec D1.5 boundary)."""
    vec = {
        "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5,
        "confidence": {
            "O": 0.7,  # exactly threshold → saturated
            "C": 0.69,  # below
            "E": 0.85,
            "A": 0.5,
            "N": 0.95,
        },
    }
    sat = saturated_dims(vec)
    assert "O" in sat
    assert "E" in sat
    assert "N" in sat
    assert "C" not in sat
    assert "A" not in sat


def test_is_dim_saturated_boundary() -> None:
    vec = {
        "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5,
        "confidence": {"O": 0.7, "C": 0.69, "E": 0.0, "A": 0.0, "N": 0.0},
    }
    assert is_dim_saturated(vec, "O") is True
    assert is_dim_saturated(vec, "C") is False


def test_is_dim_saturated_rejects_unknown_dim() -> None:
    with pytest.raises(ValueError):
        is_dim_saturated({}, "X")


def test_saturated_dims_handles_malformed_input() -> None:
    """Defensive: malformed input → empty list, never raises."""
    assert saturated_dims(None) == []  # type: ignore[arg-type]
    assert saturated_dims({"O": 0.5}) == []
    assert saturated_dims({"confidence": "not a dict"}) == []


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def test_validate_judge_output_clamps_out_of_range() -> None:
    """Defensive clamp at validator boundary."""
    out = _validate_judge_output(
        {
            "O": 1.5, "C": -0.2, "E": 0.5, "A": 0.5, "N": 0.5,
            "confidence": {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
        }
    )
    assert out["O"] == 1.0
    assert out["C"] == 0.0


def test_validate_judge_output_rejects_missing_dim() -> None:
    with pytest.raises(ValueError):
        _validate_judge_output(
            {
                "O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5,
                # N missing
                "confidence": {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
            }
        )


def test_validate_judge_output_rejects_missing_confidence_dict() -> None:
    with pytest.raises(ValueError):
        _validate_judge_output(
            {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}
        )


def test_validate_judge_output_rejects_non_dict() -> None:
    with pytest.raises(ValueError):
        _validate_judge_output("not a dict")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# update_big5_vector — judge injection + error swallow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_big5_vector_calls_judge_and_merges() -> None:
    """Mock judge returns a golden vector; result is the merged state."""
    sample = _golden_sample()
    call_args: dict[str, Any] = {}

    async def fake_judge(prose: str, prior: dict[str, Any]) -> dict[str, Any]:
        call_args["prose"] = prose
        call_args["prior"] = prior
        return sample

    result = await update_big5_vector(
        prose="I get up at 5am and run, every day.",
        prior_vector=None,
        judge=fake_judge,
    )
    assert call_args["prose"] == "I get up at 5am and run, every day."
    assert call_args["prior"] == {}
    # Merged result has the 5 dims + confidence.
    for d in DIMS:
        assert d in result
    assert "confidence" in result


@pytest.mark.asyncio
async def test_update_big5_vector_short_circuits_empty_prose() -> None:
    """Empty / whitespace prose → returns prior_vector unchanged, no judge call."""
    judge_called = {"flag": False}

    async def fake_judge(prose: str, prior: dict[str, Any]) -> dict[str, Any]:
        judge_called["flag"] = True
        return _golden_sample()

    prior = {"O": 0.5}
    result = await update_big5_vector(prose="   ", prior_vector=prior, judge=fake_judge)
    assert result == prior
    assert judge_called["flag"] is False


@pytest.mark.asyncio
async def test_update_big5_vector_swallows_judge_exception() -> None:
    """Judge raising → returns prior unchanged + logs (NEVER raises)."""
    async def bad_judge(prose: str, prior: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("haiku api down")

    prior = {"O": 0.5, "confidence": {"O": 0.4}}
    result = await update_big5_vector(prose="hello", prior_vector=prior, judge=bad_judge)
    assert result == prior


@pytest.mark.asyncio
async def test_update_big5_vector_swallows_validator_error() -> None:
    """Judge returning malformed payload → returns prior unchanged."""
    async def malformed_judge(prose: str, prior: dict[str, Any]) -> dict[str, Any]:
        return {"O": 0.5}  # missing dims + confidence

    prior = {"O": 0.5}
    result = await update_big5_vector(prose="hi", prior_vector=prior, judge=malformed_judge)
    assert result == prior


# ---------------------------------------------------------------------------
# NR-05 contract (server-side terms exist; response surface MUST hide)
# ---------------------------------------------------------------------------


def test_judge_module_uses_opaque_dim_keys() -> None:
    """Server-side dim keys are opaque single letters — none of the 8 forbidden
    full-word personality terms appear in the public dim tuple. (The
    forbidden terms are policed on the response surface in
    tests/agents/onboarding/test_no_big5_in_response.py.)
    """
    forbidden = (
        "openness", "conscientiousness", "extraversion",
        "agreeableness", "neuroticism", "ocean", "big5",
    )
    for d in DIMS:
        assert d.lower() not in forbidden, (
            f"DIM key {d!r} matches a forbidden personality term"
        )
