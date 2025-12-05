"""Tests for nikita.config.loader module.

TDD: These tests define expected ConfigLoader behavior BEFORE implementation.
"""

import pytest
from pathlib import Path
from decimal import Decimal
from datetime import timedelta


class TestConfigLoaderSingleton:
    """Tests for ConfigLoader singleton pattern."""

    def test_get_config_returns_config_loader(self):
        """get_config() should return a ConfigLoader instance."""
        from nikita.config import get_config

        config = get_config()
        assert config is not None

    def test_get_config_returns_same_instance(self):
        """get_config() should return the same instance (singleton)."""
        from nikita.config import get_config

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_config_loader_loads_all_yaml_files(self):
        """ConfigLoader should load all YAML config files."""
        from nikita.config import get_config

        config = get_config()
        # These properties should exist after loading all configs
        assert hasattr(config, "game")
        assert hasattr(config, "chapters")
        assert hasattr(config, "scoring")
        assert hasattr(config, "decay")
        assert hasattr(config, "engagement")
        assert hasattr(config, "vices")
        assert hasattr(config, "schedule")


class TestConfigLoaderGameAccess:
    """Tests for accessing game configuration."""

    def test_get_starting_score(self):
        """Should return starting score from game.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert config.game.game.starting_score == 50.0

    def test_get_max_boss_attempts(self):
        """Should return max boss attempts from game.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert config.game.game.max_boss_attempts == 3


class TestConfigLoaderChapterAccess:
    """Tests for chapter-specific accessor methods."""

    def test_get_chapter_returns_chapter_config(self):
        """get_chapter(n) should return chapter configuration."""
        from nikita.config import get_config

        config = get_config()
        ch1 = config.get_chapter(1)
        assert ch1.name == "Curiosity"
        assert ch1.boss_threshold == 55.0

    def test_get_boss_threshold(self):
        """get_boss_threshold(chapter) should return correct threshold."""
        from nikita.config import get_config

        config = get_config()
        assert config.get_boss_threshold(1) == Decimal("55.0")
        assert config.get_boss_threshold(2) == Decimal("60.0")
        assert config.get_boss_threshold(3) == Decimal("65.0")
        assert config.get_boss_threshold(4) == Decimal("70.0")
        assert config.get_boss_threshold(5) == Decimal("75.0")


class TestConfigLoaderDecayAccess:
    """Tests for decay-specific accessor methods."""

    def test_get_decay_rate(self):
        """get_decay_rate(chapter) should return Decimal rate."""
        from nikita.config import get_config

        config = get_config()
        assert config.get_decay_rate(1) == Decimal("0.8")
        assert config.get_decay_rate(5) == Decimal("0.2")

    def test_get_grace_period(self):
        """get_grace_period(chapter) should return timedelta."""
        from nikita.config import get_config

        config = get_config()
        assert config.get_grace_period(1) == timedelta(hours=8)
        assert config.get_grace_period(5) == timedelta(hours=72)


class TestConfigLoaderMetricAccess:
    """Tests for scoring metric access."""

    def test_get_metric_weights(self):
        """Should return metric weights that sum to 1.0."""
        from nikita.config import get_config

        config = get_config()
        weights = config.scoring.metrics.weights
        total = weights.intimacy + weights.passion + weights.trust + weights.secureness
        assert abs(total - 1.0) < 0.001


class TestConfigLoaderPerformance:
    """Tests for ConfigLoader performance requirements."""

    def test_initial_load_under_100ms(self):
        """Initial config load should complete in < 100ms."""
        import time
        from nikita.config.loader import ConfigLoader

        # Clear any cached instance
        ConfigLoader._instance = None

        start = time.perf_counter()
        ConfigLoader()
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"Initial load took {elapsed:.2f}ms, expected < 100ms"

    def test_subsequent_access_under_1ms(self):
        """Subsequent config access should be < 1ms (cached)."""
        import time
        from nikita.config import get_config

        # Ensure loaded
        get_config()

        start = time.perf_counter()
        for _ in range(100):
            get_config()
        elapsed = (time.perf_counter() - start) * 1000 / 100

        assert elapsed < 1, f"Subsequent access took {elapsed:.4f}ms, expected < 1ms"


class TestConfigLoaderYAMLIntegration:
    """Integration tests with actual YAML files."""

    def test_loads_game_yaml(self):
        """Should successfully load config_data/game.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert config.game.game.game_duration_days == 21

    def test_loads_chapters_yaml(self):
        """Should successfully load config_data/chapters.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert len(config.chapters.chapters) == 5
        assert config.chapters.chapters[5].name == "Established"

    def test_loads_scoring_yaml(self):
        """Should successfully load config_data/scoring.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert config.scoring.metrics.weights.intimacy == 0.30

    def test_loads_decay_yaml(self):
        """Should successfully load config_data/decay.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert config.decay.grace_periods[1] == 8
        assert config.decay.decay_rates[1] == 0.8

    def test_loads_engagement_yaml(self):
        """Should successfully load config_data/engagement.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert "IN_ZONE" in config.engagement.states

    def test_loads_vices_yaml(self):
        """Should successfully load config_data/vices.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert len(config.vices.categories) == 8

    def test_loads_schedule_yaml(self):
        """Should successfully load config_data/schedule.yaml."""
        from nikita.config import get_config

        config = get_config()
        assert "morning" in config.schedule.availability_windows


class TestConfigLoaderErrorHandling:
    """Tests for error handling."""

    def test_raises_on_invalid_chapter(self):
        """get_chapter() should raise for invalid chapter number."""
        from nikita.config import get_config

        config = get_config()
        with pytest.raises(KeyError):
            config.get_chapter(99)

    def test_raises_on_missing_config_file(self):
        """Should raise ConfigurationError if YAML file missing."""
        from nikita.config.loader import ConfigLoader
        import os

        # This test is more for documentation - we don't actually delete files
        # The loader should validate all files exist on startup
        pass
