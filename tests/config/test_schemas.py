"""Tests for nikita.config.schemas module.

TDD: These tests define expected Pydantic validation behavior BEFORE implementation.
"""

import pytest
from pydantic import ValidationError


class TestGameConfigSchema:
    """Tests for GameConfig Pydantic schema."""

    def test_game_config_validates_game_yaml(self):
        """GameConfig should validate the game.yaml structure."""
        from nikita.config.schemas import GameConfig

        valid_data = {
            "game": {
                "starting_score": 50.0,
                "score_range": {"min": 0, "max": 100},
                "max_boss_attempts": 3,
                "game_duration_days": 21,
                "default_timezone": "UTC",
            },
            "session": {
                "idle_timeout_minutes": 30,
                "max_session_hours": 8,
            },
        }
        config = GameConfig(**valid_data)
        assert config.game.starting_score == 50.0
        assert config.game.max_boss_attempts == 3

    def test_game_config_rejects_invalid_starting_score(self):
        """GameConfig should reject starting_score outside 0-100."""
        from nikita.config.schemas import GameConfig

        invalid_data = {
            "game": {
                "starting_score": 150.0,  # Invalid: > 100
                "score_range": {"min": 0, "max": 100},
                "max_boss_attempts": 3,
                "game_duration_days": 21,
                "default_timezone": "UTC",
            },
            "session": {"idle_timeout_minutes": 30, "max_session_hours": 8},
        }
        with pytest.raises(ValidationError):
            GameConfig(**invalid_data)

    def test_game_config_rejects_zero_boss_attempts(self):
        """GameConfig should reject max_boss_attempts <= 0."""
        from nikita.config.schemas import GameConfig

        invalid_data = {
            "game": {
                "starting_score": 50.0,
                "score_range": {"min": 0, "max": 100},
                "max_boss_attempts": 0,  # Invalid: must be > 0
                "game_duration_days": 21,
                "default_timezone": "UTC",
            },
            "session": {"idle_timeout_minutes": 30, "max_session_hours": 8},
        }
        with pytest.raises(ValidationError):
            GameConfig(**invalid_data)


class TestChaptersConfigSchema:
    """Tests for ChaptersConfig Pydantic schema."""

    def test_chapters_config_validates_five_chapters(self):
        """ChaptersConfig should validate exactly 5 chapters."""
        from nikita.config.schemas import ChaptersConfig

        valid_data = {
            "chapters": {
                1: {"name": "Curiosity", "day_range": {"start": 1, "end": 3}, "boss_threshold": 55.0},
                2: {"name": "Intrigue", "day_range": {"start": 4, "end": 7}, "boss_threshold": 60.0},
                3: {"name": "Investment", "day_range": {"start": 8, "end": 11}, "boss_threshold": 65.0},
                4: {"name": "Intimacy", "day_range": {"start": 12, "end": 16}, "boss_threshold": 70.0},
                5: {"name": "Established", "day_range": {"start": 17, "end": 21}, "boss_threshold": 75.0},
            },
            "bosses": {
                1: {"name": "Test", "trigger": "trigger", "challenge": "challenge"},
                2: {"name": "Test", "trigger": "trigger", "challenge": "challenge"},
                3: {"name": "Test", "trigger": "trigger", "challenge": "challenge"},
                4: {"name": "Test", "trigger": "trigger", "challenge": "challenge"},
                5: {"name": "Test", "trigger": "trigger", "challenge": "challenge"},
            },
        }
        config = ChaptersConfig(**valid_data)
        assert len(config.chapters) == 5

    def test_chapters_config_rejects_non_increasing_thresholds(self):
        """ChaptersConfig should reject non-monotonically increasing boss thresholds."""
        from nikita.config.schemas import ChaptersConfig

        invalid_data = {
            "chapters": {
                1: {"name": "Ch1", "day_range": {"start": 1, "end": 3}, "boss_threshold": 55.0},
                2: {"name": "Ch2", "day_range": {"start": 4, "end": 7}, "boss_threshold": 50.0},  # INVALID
                3: {"name": "Ch3", "day_range": {"start": 8, "end": 11}, "boss_threshold": 65.0},
                4: {"name": "Ch4", "day_range": {"start": 12, "end": 16}, "boss_threshold": 70.0},
                5: {"name": "Ch5", "day_range": {"start": 17, "end": 21}, "boss_threshold": 75.0},
            },
            "bosses": {i: {"name": "T", "trigger": "t", "challenge": "c"} for i in range(1, 6)},
        }
        with pytest.raises(ValidationError):
            ChaptersConfig(**invalid_data)

    def test_chapters_config_rejects_overlapping_day_ranges(self):
        """ChaptersConfig should reject overlapping day ranges."""
        from nikita.config.schemas import ChaptersConfig

        invalid_data = {
            "chapters": {
                1: {"name": "Ch1", "day_range": {"start": 1, "end": 5}, "boss_threshold": 55.0},
                2: {"name": "Ch2", "day_range": {"start": 4, "end": 7}, "boss_threshold": 60.0},  # OVERLAPS
                3: {"name": "Ch3", "day_range": {"start": 8, "end": 11}, "boss_threshold": 65.0},
                4: {"name": "Ch4", "day_range": {"start": 12, "end": 16}, "boss_threshold": 70.0},
                5: {"name": "Ch5", "day_range": {"start": 17, "end": 21}, "boss_threshold": 75.0},
            },
            "bosses": {i: {"name": "T", "trigger": "t", "challenge": "c"} for i in range(1, 6)},
        }
        with pytest.raises(ValidationError):
            ChaptersConfig(**invalid_data)


class TestScoringConfigSchema:
    """Tests for ScoringConfig Pydantic schema."""

    def test_scoring_config_validates_weights_sum_to_one(self):
        """ScoringConfig metric weights must sum to 1.0."""
        from nikita.config.schemas import ScoringConfig

        valid_data = {
            "metrics": {
                "weights": {
                    "intimacy": 0.30,
                    "passion": 0.25,
                    "trust": 0.25,
                    "secureness": 0.20,
                },
                "starting_values": {"intimacy": 50.0, "passion": 50.0, "trust": 50.0, "secureness": 50.0},
                "delta_range": {"min": -10.0, "max": 10.0},
            },
            "quality_modifiers": {
                "excellent": {"min_delta": 3.0, "max_delta": 10.0},
                "good": {"min_delta": 1.0, "max_delta": 5.0},
                "neutral": {"min_delta": -2.0, "max_delta": 2.0},
                "poor": {"min_delta": -5.0, "max_delta": -1.0},
                "terrible": {"min_delta": -10.0, "max_delta": -3.0},
            },
            "engagement_multipliers": {
                "IN_ZONE": 1.0,
                "CALIBRATING": 0.8,
                "DRIFTING_COLD": 0.7,
                "DRIFTING_HOT": 0.7,
                "RECOVERY": 0.5,
                "CRITICAL": 0.3,
            },
        }
        config = ScoringConfig(**valid_data)
        weights = config.metrics.weights
        total = weights.intimacy + weights.passion + weights.trust + weights.secureness
        assert abs(total - 1.0) < 0.001

    def test_scoring_config_rejects_invalid_weights_sum(self):
        """ScoringConfig should reject weights that don't sum to 1.0."""
        from nikita.config.schemas import ScoringConfig

        invalid_data = {
            "metrics": {
                "weights": {
                    "intimacy": 0.40,
                    "passion": 0.40,
                    "trust": 0.40,
                    "secureness": 0.40,  # Sum = 1.6, INVALID
                },
                "starting_values": {"intimacy": 50.0, "passion": 50.0, "trust": 50.0, "secureness": 50.0},
                "delta_range": {"min": -10.0, "max": 10.0},
            },
            "quality_modifiers": {},
            "engagement_multipliers": {
                "IN_ZONE": 1.0,
                "CALIBRATING": 0.8,
                "DRIFTING_COLD": 0.7,
                "DRIFTING_HOT": 0.7,
                "RECOVERY": 0.5,
                "CRITICAL": 0.3,
            },
        }
        with pytest.raises(ValidationError):
            ScoringConfig(**invalid_data)


class TestDecayConfigSchema:
    """Tests for DecayConfig Pydantic schema."""

    def test_decay_config_validates_all_chapters(self):
        """DecayConfig should have values for all 5 chapters."""
        from nikita.config.schemas import DecayConfig

        valid_data = {
            "grace_periods": {1: 8, 2: 16, 3: 24, 4: 48, 5: 72},
            "decay_rates": {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.3, 5: 0.2},
            "daily_caps": {1: 12.0, 2: 10.0, 3: 8.0, 4: 6.0, 5: 4.0},
            "schedule": {"check_interval_minutes": 60, "min_decay_interval_minutes": 60},
        }
        config = DecayConfig(**valid_data)
        assert len(config.grace_periods) == 5
        assert len(config.decay_rates) == 5

    def test_decay_config_rejects_missing_chapter(self):
        """DecayConfig should reject missing chapter definitions."""
        from nikita.config.schemas import DecayConfig

        invalid_data = {
            "grace_periods": {1: 8, 2: 16, 3: 24, 4: 48},  # Missing chapter 5
            "decay_rates": {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.3, 5: 0.2},
            "daily_caps": {1: 12.0, 2: 10.0, 3: 8.0, 4: 6.0, 5: 4.0},
            "schedule": {"check_interval_minutes": 60, "min_decay_interval_minutes": 60},
        }
        with pytest.raises(ValidationError):
            DecayConfig(**invalid_data)


class TestEngagementConfigSchema:
    """Tests for EngagementConfig Pydantic schema."""

    def test_engagement_config_validates_six_states(self):
        """EngagementConfig should have exactly 6 states."""
        from nikita.config.schemas import EngagementConfig

        valid_data = {
            "states": {
                "CALIBRATING": {"description": "d", "score_multiplier": 0.8, "recovery_rate": 1.0, "is_healthy": True},
                "IN_ZONE": {"description": "d", "score_multiplier": 1.0, "recovery_rate": 1.0, "is_healthy": True},
                "DRIFTING_COLD": {"description": "d", "score_multiplier": 0.7, "recovery_rate": 0.8, "is_healthy": False},
                "DRIFTING_HOT": {"description": "d", "score_multiplier": 0.7, "recovery_rate": 0.8, "is_healthy": False},
                "RECOVERY": {"description": "d", "score_multiplier": 0.5, "recovery_rate": 0.6, "is_healthy": False},
                "CRITICAL": {"description": "d", "score_multiplier": 0.3, "recovery_rate": 0.4, "is_healthy": False},
            },
            "calibration": {
                "required_interactions": 10,
                "tolerance": {"tight": 0.15, "normal": 0.25, "loose": 0.35},
            },
            "transitions": {
                "cold_threshold": 3,
                "hot_threshold": 3,
                "recovery_threshold": 5,
                "critical_threshold_hours": 24,
            },
            "ideal_messages_per_day": {1: 8, 2: 6, 3: 5, 4: 4, 5: 3},
        }
        config = EngagementConfig(**valid_data)
        assert len(config.states) == 6


class TestVicesConfigSchema:
    """Tests for VicesConfig Pydantic schema."""

    def test_vices_config_validates_eight_categories(self):
        """VicesConfig should have exactly 8 vice categories."""
        from nikita.config.schemas import VicesConfig

        valid_data = {
            "categories": {
                "intellectual_dominance": {"name": "ID", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "risk_taking": {"name": "RT", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "substances": {"name": "SU", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "sexuality": {"name": "SE", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "emotional_intensity": {"name": "EI", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "rule_breaking": {"name": "RB", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "dark_humor": {"name": "DH", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
                "vulnerability": {"name": "VU", "description": "d", "prompt_modifier": "p", "detection_signals": ["s"]},
            },
            "intensity_levels": {
                "low": {"multiplier": 0.5, "description": "Low"},
                "medium": {"multiplier": 1.0, "description": "Medium"},
                "high": {"multiplier": 1.5, "description": "High"},
            },
            "discovery": {"min_interactions": 5, "confidence_threshold": 0.7, "max_tracked_vices": 5},
        }
        config = VicesConfig(**valid_data)
        assert len(config.categories) == 8
