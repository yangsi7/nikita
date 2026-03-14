"""Tests for Spec 117 — ConfigLoader migration cleanup assertions.

AC-002: scoring/calculator.py no longer imports METRIC_WEIGHTS/BOSS_THRESHOLDS at module level
AC-003: decay/calculator.py no longer imports DECAY_RATES/GRACE_PERIODS at module level
AC-004: game_state.py no longer imports from engine.constants
AC-005: chapters/boss.py no longer imports BOSS_ENCOUNTERS
AC-006: engine/__init__.py contains only module docstring (no re-exports)
AC-007: BOSS_ENCOUNTERS, GAME_STATUSES, CHAPTER_DAY_RANGES absent from constants.__all__
"""

import inspect


class TestEngineInitCleanup:
    """AC-006: nikita.engine no longer re-exports deprecated constants."""

    def test_engine_init_no_deprecated_exports(self):
        """AC-006: nikita.engine package has no re-exported constants."""
        import nikita.engine as engine
        for name in ["CHAPTER_NAMES", "CHAPTER_BEHAVIORS", "DECAY_RATES",
                     "GRACE_PERIODS", "BOSS_THRESHOLDS"]:
            assert not hasattr(engine, name), (
                f"nikita.engine.{name} should be removed (DC-008) — "
                "nobody imports from nikita.engine directly"
            )


class TestConstantsAllCleanup:
    """AC-007: Deprecated names removed from constants.__all__."""

    def test_boss_encounters_not_in_all(self):
        """AC-007: BOSS_ENCOUNTERS removed from __all__ (DC-005)."""
        from nikita.engine import constants
        assert "BOSS_ENCOUNTERS" not in constants.__all__

    def test_game_statuses_not_in_all(self):
        """AC-007: GAME_STATUSES removed from __all__ (DC-006)."""
        from nikita.engine import constants
        assert "GAME_STATUSES" not in constants.__all__

    def test_chapter_day_ranges_not_in_all(self):
        """AC-007: CHAPTER_DAY_RANGES removed from __all__ (DC-007)."""
        from nikita.engine import constants
        assert "CHAPTER_DAY_RANGES" not in constants.__all__


class TestProductionImportMigration:
    """AC-002/003: Module-level constant imports removed from production code."""

    def test_scoring_calculator_no_metric_weights_import(self):
        """AC-002: scoring/calculator.py no longer imports METRIC_WEIGHTS at module level."""
        import nikita.engine.scoring.calculator as mod
        src = inspect.getsource(mod)
        # Check the top 25 lines (module-level imports)
        top_lines = "\n".join(src.split("\n")[:25])
        assert "METRIC_WEIGHTS" not in top_lines, (
            "METRIC_WEIGHTS must be removed from module-level imports in calculator.py"
        )

    def test_scoring_calculator_no_boss_thresholds_import(self):
        """AC-002: scoring/calculator.py no longer imports BOSS_THRESHOLDS at module level."""
        import nikita.engine.scoring.calculator as mod
        src = inspect.getsource(mod)
        top_lines = "\n".join(src.split("\n")[:25])
        assert "BOSS_THRESHOLDS" not in top_lines, (
            "BOSS_THRESHOLDS must be removed from module-level imports in calculator.py"
        )

    def test_decay_calculator_no_decay_rates_import(self):
        """AC-003: decay/calculator.py no longer imports DECAY_RATES at module level."""
        import nikita.engine.decay.calculator as mod
        src = inspect.getsource(mod)
        top_lines = "\n".join(src.split("\n")[:20])
        assert "DECAY_RATES" not in top_lines, (
            "DECAY_RATES must be removed from module-level imports in decay/calculator.py"
        )

    def test_decay_calculator_no_grace_periods_import(self):
        """AC-003: decay/calculator.py no longer imports GRACE_PERIODS at module level."""
        import nikita.engine.decay.calculator as mod
        src = inspect.getsource(mod)
        top_lines = "\n".join(src.split("\n")[:20])
        assert "GRACE_PERIODS" not in top_lines, (
            "GRACE_PERIODS must be removed from module-level imports in decay/calculator.py"
        )

    def test_boss_py_no_boss_encounters_import(self):
        """AC-005: chapters/boss.py no longer imports BOSS_ENCOUNTERS."""
        import nikita.engine.chapters.boss as mod
        src = inspect.getsource(mod)
        assert "BOSS_ENCOUNTERS" not in src, (
            "BOSS_ENCOUNTERS must be removed from boss.py — it was imported but never used"
        )

    def test_game_state_no_engine_constants_import(self):
        """AC-004: game_state.py no longer imports from engine.constants at module level."""
        import nikita.pipeline.stages.game_state as mod
        src = inspect.getsource(mod)
        # These constant names must not appear in module-level imports
        top_lines = "\n".join(src.split("\n")[:20])
        assert "engine.constants" not in top_lines, (
            "game_state.py must not import from nikita.engine.constants at module level"
        )
        assert "BOSS_THRESHOLDS" not in top_lines, (
            "BOSS_THRESHOLDS must be removed from module-level imports in game_state.py"
        )
        assert "CHAPTER_NAMES" not in top_lines, (
            "CHAPTER_NAMES must be removed from module-level imports in game_state.py"
        )


class TestConfigLoaderBehavioralEquivalence:
    """AC-008 behavioral equivalence: ConfigLoader returns same values as deprecated constants."""

    def test_boss_thresholds_match_constants(self):
        """ConfigLoader boss thresholds match engine.constants BOSS_THRESHOLDS."""
        from decimal import Decimal
        from nikita.config import get_config
        from nikita.engine.constants import BOSS_THRESHOLDS
        for chapter in range(1, 6):
            assert get_config().get_boss_threshold(chapter) == Decimal(str(BOSS_THRESHOLDS[chapter])), (
                f"Chapter {chapter} boss threshold diverged between ConfigLoader and constants"
            )

    def test_decay_rates_match_constants(self):
        """ConfigLoader decay rates match engine.constants DECAY_RATES."""
        from decimal import Decimal
        from nikita.config import get_config
        from nikita.engine.constants import DECAY_RATES
        for chapter in range(1, 6):
            assert get_config().get_decay_rate(chapter) == Decimal(str(DECAY_RATES[chapter])), (
                f"Chapter {chapter} decay rate diverged between ConfigLoader and constants"
            )

    def test_metric_weights_match_constants(self):
        """ConfigLoader metric weights match engine.constants METRIC_WEIGHTS."""
        from decimal import Decimal
        from nikita.config import get_config
        from nikita.engine.constants import METRIC_WEIGHTS
        weights = get_config().get_metric_weights()
        for metric, expected in METRIC_WEIGHTS.items():
            assert weights[metric] == Decimal(str(expected)), (
                f"Metric weight '{metric}' diverged between ConfigLoader and constants"
            )
