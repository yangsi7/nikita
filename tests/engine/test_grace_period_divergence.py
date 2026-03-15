"""Document the grace period divergence between constants.py and YAML config.

constants.py: GRACE_PERIODS = {1: 72h, 2: 48h, 3: 24h, 4: 16h, 5: 8h}  (inverted)
YAML config:  grace_periods = {1: 8h, 2: 16h, 3: 24h, 4: 48h, 5: 72h}  (natural)

Spec 117 migrated production code to use YAML (ConfigLoader). The constants remain
for backward compatibility but ARE NOT authoritative. This test guards against
any production code path silently using the wrong source.
"""

import inspect
from datetime import timedelta

from nikita.config import get_config
from nikita.engine.constants import GRACE_PERIODS


class TestGracePeriodDivergence:
    """Document known divergence between constants and YAML."""

    def test_yaml_has_natural_order(self):
        """Veterans (Ch5) get MORE grace than newcomers (Ch1)."""
        cfg = get_config()
        assert cfg.get_grace_period(1) < cfg.get_grace_period(5)
        assert cfg.get_grace_period(1) == timedelta(hours=8)
        assert cfg.get_grace_period(5) == timedelta(hours=72)

    def test_constants_have_inverted_order(self):
        """Legacy constants have INVERTED order (Ch1=72h, Ch5=8h)."""
        assert GRACE_PERIODS[1] == timedelta(hours=72)
        assert GRACE_PERIODS[5] == timedelta(hours=8)

    def test_production_decay_uses_yaml_not_constants(self):
        """Verify decay/calculator.py uses get_config(), not GRACE_PERIODS."""
        import nikita.engine.decay.calculator as decay_mod

        src = inspect.getsource(decay_mod)
        assert "GRACE_PERIODS" not in src, (
            "decay/calculator.py should use get_config().get_grace_period()"
        )
        assert "get_config" in src, "decay/calculator.py should import get_config"

    def test_production_scoring_uses_yaml_not_constants(self):
        """Verify scoring/calculator.py uses get_config(), not METRIC_WEIGHTS."""
        import nikita.engine.scoring.calculator as scoring_mod

        src = inspect.getsource(scoring_mod)
        assert "METRIC_WEIGHTS" not in src, (
            "scoring/calculator.py should use get_config().get_metric_weights()"
        )
        assert "get_config" in src, (
            "scoring/calculator.py should import get_config"
        )
