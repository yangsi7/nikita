"""Tests for the live-vs-offline heartbeat parity validator (Spec 215 PR 215-F).

These tests mock the SQL-result level (production has no heartbeat events at PR
write time). They cover four scenarios:

    1. PASS — observed inter-wake distribution matches MC samples (no drift).
    2. FAIL — observed diverges from MC (synthetic drift).
    3. Per-chapter breakdown is in the JSON output for ALL chapters 1-5.
    4. Empty observed data is handled gracefully (warning, exit 0 — not crash).

Coverage strategy: bypass the real Supabase MCP client by patching
``fetch_observed_inter_wake`` (the validator's I/O boundary). Every test
provides synthetic numpy arrays directly, so the code paths under test are
the KS computation, exit-code policy, and JSON shape.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch

import numpy as np
import pytest

from scripts.models.heartbeat_live_parity import (
    P_VALUE_THRESHOLD,
    ks_two_sample,
    main,
    run_parity,
)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _matched_observed(rng_seed: int = 7) -> dict[int, np.ndarray]:
    """Synthetic 'observed' that mirrors the MC distribution (should PASS).

    Use a fixed seed so the test is deterministic. We sample directly from
    the same exponential family the MC uses so KS p-values are high.
    """
    rng = np.random.default_rng(rng_seed)
    return {ch: rng.exponential(scale=1.0 / (1.0 + 0.1 * ch), size=200)
            for ch in range(1, 6)}


def _drifted_observed(rng_seed: int = 7) -> dict[int, np.ndarray]:
    """Synthetic 'observed' with heavy drift (should FAIL KS).

    Multiplies inter-wake gaps by 5 — the empirical distribution is
    stochastically dominated by the MC, so KS rejects with very small p.
    """
    rng = np.random.default_rng(rng_seed)
    return {ch: rng.exponential(scale=5.0, size=200) for ch in range(1, 6)}


def _matched_mc(rng_seed: int = 13) -> dict[int, np.ndarray]:
    """MC reference samples drawn from the same family as ``_matched_observed``."""
    rng = np.random.default_rng(rng_seed)
    return {ch: rng.exponential(scale=1.0 / (1.0 + 0.1 * ch), size=2000)
            for ch in range(1, 6)}


# --------------------------------------------------------------------------- #
# KS primitive sanity                                                         #
# --------------------------------------------------------------------------- #


def test_ks_two_sample_returns_high_p_for_same_distribution():
    rng = np.random.default_rng(0)
    a = rng.exponential(scale=1.0, size=500)
    b = rng.exponential(scale=1.0, size=500)
    stat, p = ks_two_sample(a, b)
    assert 0 <= stat <= 1
    assert p > 0.05  # cannot reject same-distribution hypothesis


def test_ks_two_sample_returns_low_p_for_different_distribution():
    rng = np.random.default_rng(0)
    a = rng.exponential(scale=1.0, size=500)
    b = rng.exponential(scale=5.0, size=500)
    _, p = ks_two_sample(a, b)
    assert p < 0.001  # decisively rejects same-distribution hypothesis


# --------------------------------------------------------------------------- #
# Main scenarios                                                              #
# --------------------------------------------------------------------------- #


def test_passes_when_observed_matches_mc():
    """AC: validator exits 0 + no failed chapters when distributions match."""
    observed = _matched_observed()
    mc = _matched_mc()

    result = run_parity(observed=observed, mc_samples=mc)

    assert result["status"] == "pass"
    assert result["exit_code"] == 0
    assert all(ch["passed"] for ch in result["chapters"].values()), \
        f"Expected all chapters to pass, got: {result['chapters']}"


def test_fails_when_observed_diverges_from_mc():
    """AC: validator exits 1 + flags failing chapters when distributions diverge."""
    observed = _drifted_observed()
    mc = _matched_mc()

    result = run_parity(observed=observed, mc_samples=mc)

    assert result["status"] == "fail"
    assert result["exit_code"] == 1
    failing = [ch for ch, data in result["chapters"].items() if not data["passed"]]
    assert len(failing) == 5, \
        f"Expected all 5 chapters to fail under heavy drift, got failing={failing}"
    # Each failing chapter must report p ≤ threshold
    for ch_data in result["chapters"].values():
        if not ch_data["passed"]:
            assert ch_data["p_value"] <= P_VALUE_THRESHOLD


def test_per_chapter_breakdown_in_output():
    """AC: JSON output contains per-chapter p-value, ks_statistic, sample sizes for chapters 1-5."""
    observed = _matched_observed()
    mc = _matched_mc()

    result = run_parity(observed=observed, mc_samples=mc)

    for chapter in range(1, 6):
        assert chapter in result["chapters"], f"Missing chapter {chapter}"
        ch_data = result["chapters"][chapter]
        assert "p_value" in ch_data
        assert "ks_statistic" in ch_data
        assert "n_observed" in ch_data
        assert "n_mc" in ch_data
        assert "passed" in ch_data
        assert ch_data["n_observed"] == 200
        assert ch_data["n_mc"] == 2000


def test_handles_empty_observed_data_gracefully():
    """AC: empty observed data produces structured 'no_data' status, exit 0 (no spurious alert)."""
    observed: dict[int, np.ndarray] = {ch: np.array([]) for ch in range(1, 6)}
    mc = _matched_mc()

    result = run_parity(observed=observed, mc_samples=mc)

    assert result["status"] == "no_data"
    assert result["exit_code"] == 0
    for chapter in range(1, 6):
        ch_data = result["chapters"][chapter]
        assert ch_data["passed"] is True  # not actively failing
        assert ch_data["n_observed"] == 0
        assert ch_data["p_value"] is None
        assert ch_data["ks_statistic"] is None


def test_partial_data_still_evaluates_present_chapters():
    """If only some chapters have observed data, those are KS-tested; others marked no_data."""
    observed = {1: _matched_observed()[1], 3: _matched_observed()[3]}
    # Chapters 2, 4, 5 absent
    mc = _matched_mc()

    result = run_parity(observed=observed, mc_samples=mc)

    assert result["chapters"][1]["n_observed"] == 200
    assert result["chapters"][1]["p_value"] is not None
    assert result["chapters"][2]["n_observed"] == 0
    assert result["chapters"][2]["p_value"] is None
    assert result["chapters"][3]["n_observed"] == 200
    assert result["chapters"][3]["p_value"] is not None


# --------------------------------------------------------------------------- #
# Main entry point — exit code + JSON to stdout                               #
# --------------------------------------------------------------------------- #


def test_main_emits_json_to_stdout_and_returns_exit_code():
    """main() emits a single JSON document to stdout and returns int exit code."""
    observed = _matched_observed()

    with patch(
        "scripts.models.heartbeat_live_parity.fetch_observed_inter_wake",
        return_value=observed,
    ), patch(
        "scripts.models.heartbeat_live_parity.generate_mc_samples",
        return_value=_matched_mc(),
    ):
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main([])

    assert exit_code == 0
    payload = json.loads(buf.getvalue())
    assert payload["status"] == "pass"
    assert "chapters" in payload


def test_main_returns_1_on_drift():
    observed = _drifted_observed()

    with patch(
        "scripts.models.heartbeat_live_parity.fetch_observed_inter_wake",
        return_value=observed,
    ), patch(
        "scripts.models.heartbeat_live_parity.generate_mc_samples",
        return_value=_matched_mc(),
    ):
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = main([])

    assert exit_code == 1
    payload = json.loads(buf.getvalue())
    assert payload["status"] == "fail"
