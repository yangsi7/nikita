"""Value-mutation regression guards for tuning constants (GH #479).

Per ``.claude/rules/tuning-constants.md``: every scoring, decay, threshold,
and weight needs a regression guard asserting its EXACT current value.
Behavior tests with tolerance margins (±0.01, etc.) cannot detect a silent
one-byte mutation (e.g., ``0.8 → 0.79``); these tests can. Source-of-truth
references appear inline next to every assertion.

Two surfaces are covered, by design:

1. **Legacy constants** in ``nikita/engine/constants.py`` (DEPRECATED, kept
   for backward compat per Spec 117). These remain exported via ``__all__``
   and are read by a small set of legacy callers.
2. **YAML-loaded canonical values** via ``nikita.config.get_config()``. Spec
   117 made these authoritative; production code reads here.

Both surfaces must hold their declared values. Drift in either is a
PR-blocker, since:

  - Drift in the legacy constants breaks any module still importing them.
  - Drift in the YAML or its accessors silently re-tunes the live game.

Cross-references:
  - ``nikita/engine/constants.py:132-168`` (BOSS_THRESHOLDS, DECAY_RATES,
    GRACE_PERIODS, METRIC_WEIGHTS legacy declarations)
  - ``nikita/config_data/decay.yaml:6-28`` (canonical grace_periods,
    decay_rates, daily_caps)
  - ``nikita/config_data/scoring.yaml:7-11`` (canonical metric weights)
  - ``nikita/config_data/chapters.yaml`` (canonical boss_threshold per
    chapter)
  - ``nikita/config/loader.py:118-182`` (ConfigLoader accessors)
  - ``tests/engine/test_grace_period_divergence.py`` documents the
    intentional inversion between legacy GRACE_PERIODS and YAML.

If you intentionally change one of these values, update BOTH the source of
truth AND the assertion below, and add a CHANGELOG-style line in this
docstring referencing the driving GH issue / PR.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from nikita.config import get_config
from nikita.engine.constants import (
    BOSS_THRESHOLDS,
    DECAY_RATES,
    GRACE_PERIODS,
    METRIC_WEIGHTS,
)

# ---------------------------------------------------------------------------
# Legacy constants (nikita/engine/constants.py)
# ---------------------------------------------------------------------------


class TestBossThresholdsLegacy:
    """Legacy ``BOSS_THRESHOLDS`` exact-value guard.

    Source of truth: ``nikita/engine/constants.py:132-138``.
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, Decimal("55.00")),
            (2, Decimal("60.00")),
            (3, Decimal("65.00")),
            (4, Decimal("70.00")),
            (5, Decimal("75.00")),
        ],
    )
    def test_exact_value(self, chapter: int, expected: Decimal) -> None:
        assert BOSS_THRESHOLDS[chapter] == expected, (
            f"BOSS_THRESHOLDS[{chapter}] drifted; expected {expected}, "
            f"got {BOSS_THRESHOLDS[chapter]} — see GH #479."
        )

    def test_keys_complete(self) -> None:
        """Map must cover exactly chapters 1-5 — no extras, no gaps."""
        assert set(BOSS_THRESHOLDS.keys()) == {1, 2, 3, 4, 5}


class TestDecayRatesLegacy:
    """Legacy ``DECAY_RATES`` exact-value guard (hourly % loss).

    Source of truth: ``nikita/engine/constants.py:141-147``.
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, Decimal("0.8")),
            (2, Decimal("0.6")),
            (3, Decimal("0.4")),
            (4, Decimal("0.3")),
            (5, Decimal("0.2")),
        ],
    )
    def test_exact_value(self, chapter: int, expected: Decimal) -> None:
        assert DECAY_RATES[chapter] == expected, (
            f"DECAY_RATES[{chapter}] drifted; expected {expected}, "
            f"got {DECAY_RATES[chapter]} — see GH #479."
        )

    def test_keys_complete(self) -> None:
        assert set(DECAY_RATES.keys()) == {1, 2, 3, 4, 5}


class TestGracePeriodsLegacy:
    """Legacy ``GRACE_PERIODS`` exact-value guard.

    NOTE: legacy values are INVERTED relative to the YAML config (Ch1=72h
    here, Ch1=8h in YAML). See ``test_grace_period_divergence.py`` for the
    cross-source contract test. This file only guards the legacy values
    against silent drift; the inversion itself is intentional and tested
    elsewhere.

    Source of truth: ``nikita/engine/constants.py:153-159``.
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, timedelta(hours=72)),
            (2, timedelta(hours=48)),
            (3, timedelta(hours=24)),
            (4, timedelta(hours=16)),
            (5, timedelta(hours=8)),
        ],
    )
    def test_exact_value(
        self, chapter: int, expected: timedelta
    ) -> None:
        assert GRACE_PERIODS[chapter] == expected, (
            f"GRACE_PERIODS[{chapter}] drifted; expected {expected}, "
            f"got {GRACE_PERIODS[chapter]} — see GH #479."
        )

    def test_keys_complete(self) -> None:
        assert set(GRACE_PERIODS.keys()) == {1, 2, 3, 4, 5}


class TestMetricWeightsLegacy:
    """Legacy ``METRIC_WEIGHTS`` exact-value guard.

    Source of truth: ``nikita/engine/constants.py:163-168``.
    Composite score = intimacy*0.30 + passion*0.25 + trust*0.25 +
    secureness*0.20. The weights MUST sum to exactly 1.00.
    """

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("intimacy", Decimal("0.30")),
            ("passion", Decimal("0.25")),
            ("trust", Decimal("0.25")),
            ("secureness", Decimal("0.20")),
        ],
    )
    def test_exact_value(self, name: str, expected: Decimal) -> None:
        assert METRIC_WEIGHTS[name] == expected, (
            f"METRIC_WEIGHTS[{name!r}] drifted; expected {expected}, "
            f"got {METRIC_WEIGHTS[name]} — see GH #479."
        )

    def test_weights_sum_to_one(self) -> None:
        """Weights must sum to exactly Decimal('1.00') — no float fuzz."""
        total = sum(METRIC_WEIGHTS.values(), Decimal("0"))
        assert total == Decimal("1.00"), (
            f"METRIC_WEIGHTS sum to {total}, expected Decimal('1.00')."
        )

    def test_keys_complete(self) -> None:
        assert set(METRIC_WEIGHTS.keys()) == {
            "intimacy",
            "passion",
            "trust",
            "secureness",
        }


# ---------------------------------------------------------------------------
# YAML-loaded canonical values (Spec 117, production reads here)
# ---------------------------------------------------------------------------


class TestBossThresholdYAML:
    """Canonical boss thresholds from ``chapters.yaml`` via ConfigLoader.

    Source of truth: ``nikita/config_data/chapters.yaml`` ``boss_threshold``
    field per chapter, surfaced by
    ``ConfigLoader.get_boss_threshold(chapter)``.
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, Decimal("55.0")),
            (2, Decimal("60.0")),
            (3, Decimal("65.0")),
            (4, Decimal("70.0")),
            (5, Decimal("75.0")),
        ],
    )
    def test_exact_value(self, chapter: int, expected: Decimal) -> None:
        cfg = get_config()
        assert cfg.get_boss_threshold(chapter) == expected, (
            f"chapters.yaml boss_threshold for Ch{chapter} drifted; "
            f"expected {expected}, got {cfg.get_boss_threshold(chapter)} "
            f"— see GH #479."
        )


class TestDecayRatesYAML:
    """Canonical decay rates from ``decay.yaml`` via ConfigLoader.

    Source of truth: ``nikita/config_data/decay.yaml:15-20``, surfaced by
    ``ConfigLoader.get_decay_rate(chapter)``.
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, Decimal("0.8")),
            (2, Decimal("0.6")),
            (3, Decimal("0.4")),
            (4, Decimal("0.3")),
            (5, Decimal("0.2")),
        ],
    )
    def test_exact_value(self, chapter: int, expected: Decimal) -> None:
        cfg = get_config()
        assert cfg.get_decay_rate(chapter) == expected, (
            f"decay.yaml decay_rates[{chapter}] drifted; expected "
            f"{expected}, got {cfg.get_decay_rate(chapter)} "
            f"— see GH #479."
        )


class TestDailyDecayCapsYAML:
    """Canonical daily decay caps from ``decay.yaml`` via ConfigLoader.

    Source of truth: ``nikita/config_data/decay.yaml:23-28``, surfaced by
    ``ConfigLoader.get_daily_cap(chapter)``. Values are percent-per-day.
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, Decimal("12.0")),
            (2, Decimal("10.0")),
            (3, Decimal("8.0")),
            (4, Decimal("6.0")),
            (5, Decimal("4.0")),
        ],
    )
    def test_exact_value(self, chapter: int, expected: Decimal) -> None:
        cfg = get_config()
        assert cfg.get_daily_cap(chapter) == expected, (
            f"decay.yaml daily_caps[{chapter}] drifted; expected "
            f"{expected}, got {cfg.get_daily_cap(chapter)} "
            f"— see GH #479."
        )


class TestGracePeriodsYAML:
    """Canonical grace periods from ``decay.yaml`` via ConfigLoader.

    Source of truth: ``nikita/config_data/decay.yaml:6-11``, surfaced by
    ``ConfigLoader.get_grace_period(chapter)``. Production reads here;
    the legacy ``GRACE_PERIODS`` constant is intentionally inverted (see
    ``test_grace_period_divergence.py``).
    """

    @pytest.mark.parametrize(
        ("chapter", "expected"),
        [
            (1, timedelta(hours=8)),
            (2, timedelta(hours=16)),
            (3, timedelta(hours=24)),
            (4, timedelta(hours=48)),
            (5, timedelta(hours=72)),
        ],
    )
    def test_exact_value(
        self, chapter: int, expected: timedelta
    ) -> None:
        cfg = get_config()
        assert cfg.get_grace_period(chapter) == expected, (
            f"decay.yaml grace_periods[{chapter}] drifted; expected "
            f"{expected}, got {cfg.get_grace_period(chapter)} "
            f"— see GH #479."
        )


class TestMetricWeightsYAML:
    """Canonical metric weights from ``scoring.yaml`` via ConfigLoader.

    Source of truth: ``nikita/config_data/scoring.yaml:7-11``, surfaced by
    ``ConfigLoader.get_metric_weights()``. Weights MUST sum to 1.00.
    """

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("intimacy", Decimal("0.30")),
            ("passion", Decimal("0.25")),
            ("trust", Decimal("0.25")),
            ("secureness", Decimal("0.20")),
        ],
    )
    def test_exact_value(self, name: str, expected: Decimal) -> None:
        cfg = get_config()
        weights = cfg.get_metric_weights()
        assert weights[name] == expected, (
            f"scoring.yaml metric weight for {name!r} drifted; expected "
            f"{expected}, got {weights[name]} — see GH #479."
        )

    def test_weights_sum_to_one(self) -> None:
        cfg = get_config()
        weights = cfg.get_metric_weights()
        total = sum(weights.values(), Decimal("0"))
        assert total == Decimal("1.00"), (
            f"scoring.yaml metric weights sum to {total}, "
            f"expected Decimal('1.00')."
        )
