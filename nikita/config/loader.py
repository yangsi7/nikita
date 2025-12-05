"""Configuration loader for YAML config files.

Implements a singleton pattern for efficient config access across the application.
"""

from datetime import timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from nikita.config.schemas import (
    ChapterDefinition,
    ChaptersConfig,
    DecayConfig,
    EngagementConfig,
    GameConfig,
    ScheduleConfig,
    ScoringConfig,
    VicesConfig,
)


class ConfigurationError(Exception):
    """Raised when configuration loading fails."""

    pass


class ConfigLoader:
    """Singleton configuration loader for all YAML configs.

    Usage:
        config = ConfigLoader()  # Or use get_config()
        starting_score = config.game.game.starting_score
        boss_threshold = config.get_boss_threshold(1)
    """

    _instance: "ConfigLoader | None" = None
    _initialized: bool = False

    def __new__(cls) -> "ConfigLoader":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Load all YAML configs on first initialization."""
        if ConfigLoader._initialized:
            return

        self._config_dir = Path(__file__).parent.parent / "config_data"
        self._load_all_configs()
        ConfigLoader._initialized = True

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        """Load a YAML file from the config directory."""
        filepath = self._config_dir / filename
        if not filepath.exists():
            raise ConfigurationError(f"Config file not found: {filepath}")

        with open(filepath) as f:
            return yaml.safe_load(f)

    def _load_all_configs(self) -> None:
        """Load and validate all configuration files."""
        # Load game config
        game_data = self._load_yaml("game.yaml")
        self.game = GameConfig(**game_data)

        # Load chapters config
        chapters_data = self._load_yaml("chapters.yaml")
        self.chapters = ChaptersConfig(**chapters_data)

        # Load scoring config
        scoring_data = self._load_yaml("scoring.yaml")
        self.scoring = ScoringConfig(**scoring_data)

        # Load decay config
        decay_data = self._load_yaml("decay.yaml")
        self.decay = DecayConfig(**decay_data)

        # Load engagement config
        engagement_data = self._load_yaml("engagement.yaml")
        self.engagement = EngagementConfig(**engagement_data)

        # Load vices config
        vices_data = self._load_yaml("vices.yaml")
        self.vices = VicesConfig(**vices_data)

        # Load schedule config
        schedule_data = self._load_yaml("schedule.yaml")
        self.schedule = ScheduleConfig(**schedule_data)

    # =========================================================================
    # Convenience accessor methods
    # =========================================================================

    def get_chapter(self, chapter_num: int) -> ChapterDefinition:
        """Get configuration for a specific chapter.

        Args:
            chapter_num: Chapter number (1-5)

        Returns:
            ChapterDefinition with name, day_range, boss_threshold

        Raises:
            KeyError: If chapter doesn't exist
        """
        if chapter_num not in self.chapters.chapters:
            raise KeyError(f"Invalid chapter number: {chapter_num}")
        return self.chapters.chapters[chapter_num]

    def get_boss_threshold(self, chapter_num: int) -> Decimal:
        """Get boss threshold for a chapter as Decimal.

        Args:
            chapter_num: Chapter number (1-5)

        Returns:
            Boss threshold as Decimal (e.g., Decimal("55.0"))
        """
        chapter = self.get_chapter(chapter_num)
        return Decimal(str(chapter.boss_threshold))

    def get_decay_rate(self, chapter_num: int) -> Decimal:
        """Get decay rate for a chapter as Decimal.

        Args:
            chapter_num: Chapter number (1-5)

        Returns:
            Decay rate per hour as Decimal (e.g., Decimal("0.8"))
        """
        if chapter_num not in self.decay.decay_rates:
            raise KeyError(f"Invalid chapter number: {chapter_num}")
        return Decimal(str(self.decay.decay_rates[chapter_num]))

    def get_grace_period(self, chapter_num: int) -> timedelta:
        """Get grace period for a chapter as timedelta.

        Args:
            chapter_num: Chapter number (1-5)

        Returns:
            Grace period as timedelta (e.g., timedelta(hours=8))
        """
        if chapter_num not in self.decay.grace_periods:
            raise KeyError(f"Invalid chapter number: {chapter_num}")
        hours = self.decay.grace_periods[chapter_num]
        return timedelta(hours=hours)

    def get_daily_cap(self, chapter_num: int) -> Decimal:
        """Get daily decay cap for a chapter.

        Args:
            chapter_num: Chapter number (1-5)

        Returns:
            Daily decay cap as Decimal
        """
        if chapter_num not in self.decay.daily_caps:
            raise KeyError(f"Invalid chapter number: {chapter_num}")
        return Decimal(str(self.decay.daily_caps[chapter_num]))


@lru_cache(maxsize=1)
def get_config() -> ConfigLoader:
    """Get the singleton ConfigLoader instance.

    This function is cached for performance - subsequent calls
    return the same instance without re-checking the singleton.

    Returns:
        ConfigLoader instance with all configs loaded
    """
    return ConfigLoader()
