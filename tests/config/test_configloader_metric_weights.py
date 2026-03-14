"""Tests for ConfigLoader.get_metric_weights() (Spec 117 FR-001).

AC-001: get_metric_weights() returns {str: Decimal} matching scoring.yaml values.
"""

from decimal import Decimal

import pytest


class TestGetMetricWeights:
    """AC-001: ConfigLoader.get_metric_weights() returns correct dict."""

    def test_returns_dict(self):
        """Returns a dict (not a Pydantic model)."""
        from nikita.config import get_config
        weights = get_config().get_metric_weights()
        assert isinstance(weights, dict)

    def test_has_all_four_metrics(self):
        """All four scoring metrics are present."""
        from nikita.config import get_config
        weights = get_config().get_metric_weights()
        assert set(weights.keys()) == {"intimacy", "passion", "trust", "secureness"}

    def test_values_are_decimal(self):
        """All values are Decimal instances."""
        from nikita.config import get_config
        weights = get_config().get_metric_weights()
        assert all(isinstance(v, Decimal) for v in weights.values())

    def test_weights_sum_to_one(self):
        """Metric weights sum to 1.0 (matches MetricWeights validator)."""
        from nikita.config import get_config
        weights = get_config().get_metric_weights()
        total = sum(weights.values())
        assert abs(total - Decimal("1.0")) < Decimal("0.01")

    def test_matches_scoring_yaml(self):
        """Values match scoring.yaml: intimacy=0.30, passion=0.25, trust=0.25, secureness=0.20."""
        from nikita.config import get_config
        weights = get_config().get_metric_weights()
        assert weights["intimacy"] == Decimal("0.30")
        assert weights["passion"] == Decimal("0.25")
        assert weights["trust"] == Decimal("0.25")
        assert weights["secureness"] == Decimal("0.20")
