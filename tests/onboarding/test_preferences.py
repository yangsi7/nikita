"""Phase F: Preference Configuration tests (Spec 028).

Tests for PreferenceConfigurator class and darkness/pacing mapping.

Implements:
- AC-T022.1-4: PreferenceConfigurator class
- AC-T023.1-4: Darkness level mapping
- AC-T024.1-4: Pacing configuration
- AC-T025.1-2: Coverage tests
"""

from uuid import uuid4

import pytest

from nikita.onboarding.models import ConversationStyle, UserOnboardingProfile
from nikita.onboarding.preference_config import (
    DarknessLevelConfig,
    PacingConfig,
    PreferenceConfigurator,
    get_darkness_config,
    get_pacing_config,
)


class TestPreferenceConfigurator:
    """Tests for PreferenceConfigurator class (T022)."""

    @pytest.fixture
    def configurator(self) -> PreferenceConfigurator:
        """Create configurator instance."""
        return PreferenceConfigurator()

    def test_configure_darkness_level(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.2: configure() sets darkness level."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            darkness_level=4,
        )

        assert result.success is True
        profile = configurator.get_preferences(user_id)
        assert profile.darkness_level == 4

    def test_configure_pacing(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.2: configure() sets pacing."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            pacing_weeks=8,
        )

        assert result.success is True
        profile = configurator.get_preferences(user_id)
        assert profile.pacing_weeks == 8

    def test_configure_conversation_style(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.2: configure() sets conversation style."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            conversation_style=ConversationStyle.LISTENER,
        )

        assert result.success is True
        profile = configurator.get_preferences(user_id)
        assert profile.conversation_style == ConversationStyle.LISTENER

    def test_configure_multiple_preferences(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.3: Can configure multiple preferences at once."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            darkness_level=5,
            pacing_weeks=4,
            conversation_style=ConversationStyle.SHARER,
        )

        assert result.success is True
        profile = configurator.get_preferences(user_id)
        assert profile.darkness_level == 5
        assert profile.pacing_weeks == 4
        assert profile.conversation_style == ConversationStyle.SHARER

    def test_configure_returns_result(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.2: configure() returns result with applied settings."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            darkness_level=3,
        )

        assert result.success is True
        assert result.applied["darkness_level"] == 3

    def test_configure_invalid_darkness(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.3: Invalid darkness level rejected."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            darkness_level=10,
        )

        assert result.success is False
        assert result.error is not None

    def test_configure_invalid_pacing(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.3: Invalid pacing rejected."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            pacing_weeks=6,
        )

        assert result.success is False
        assert result.error is not None

    def test_configure_updates_existing(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.3: Can update existing preferences."""
        user_id = uuid4()

        configurator.configure(user_id=user_id, darkness_level=2)
        configurator.configure(user_id=user_id, darkness_level=4)

        profile = configurator.get_preferences(user_id)
        assert profile.darkness_level == 4

    def test_preferences_isolated_between_users(self, configurator: PreferenceConfigurator) -> None:
        """AC-T022.1: Each user has separate preferences."""
        user1 = uuid4()
        user2 = uuid4()

        configurator.configure(user_id=user1, darkness_level=1)
        configurator.configure(user_id=user2, darkness_level=5)

        assert configurator.get_preferences(user1).darkness_level == 1
        assert configurator.get_preferences(user2).darkness_level == 5


class TestDarknessLevelMapping:
    """Tests for darkness level mapping (T023)."""

    def test_level_1_vanilla(self) -> None:
        """AC-T023.2: Level 1 = vanilla (wholesome)."""
        config = get_darkness_config(1)

        assert config.level == 1
        assert config.name == "vanilla"
        assert config.allows_manipulation is False
        assert config.allows_substance_mentions is False
        assert config.emotional_intensity == "low"

    def test_level_2_mild(self) -> None:
        """AC-T023.1: Level 2 = mild edge."""
        config = get_darkness_config(2)

        assert config.level == 2
        assert config.name == "mild"
        assert config.allows_manipulation is False
        assert config.emotional_intensity == "moderate"

    def test_level_3_default(self) -> None:
        """AC-T023.1: Level 3 = default balanced."""
        config = get_darkness_config(3)

        assert config.level == 3
        assert config.name == "balanced"
        assert config.allows_manipulation is True
        assert config.manipulation_intensity == "subtle"

    def test_level_4_edgy(self) -> None:
        """AC-T023.1: Level 4 = edgy."""
        config = get_darkness_config(4)

        assert config.level == 4
        assert config.name == "edgy"
        assert config.allows_manipulation is True
        assert config.allows_substance_mentions is True
        assert config.emotional_intensity == "high"

    def test_level_5_noir(self) -> None:
        """AC-T023.2: Level 5 = full noir."""
        config = get_darkness_config(5)

        assert config.level == 5
        assert config.name == "noir"
        assert config.allows_manipulation is True
        assert config.manipulation_intensity == "overt"
        assert config.allows_substance_mentions is True
        assert config.allows_possessiveness is True
        assert config.emotional_intensity == "extreme"

    def test_darkness_config_has_description(self) -> None:
        """AC-T023.3: Each level has description."""
        for level in range(1, 6):
            config = get_darkness_config(level)
            assert config.description is not None
            assert len(config.description) > 0

    def test_darkness_config_behavioral_traits(self) -> None:
        """AC-T023.1: Config maps to behavioral traits."""
        config = get_darkness_config(3)

        # Should have behavioral trait mappings
        assert hasattr(config, "behavioral_traits")
        assert isinstance(config.behavioral_traits, dict)

    def test_invalid_darkness_level_raises(self) -> None:
        """AC-T023.1: Invalid level raises ValueError."""
        with pytest.raises(ValueError):
            get_darkness_config(0)

        with pytest.raises(ValueError):
            get_darkness_config(6)


class TestPacingConfiguration:
    """Tests for pacing configuration (T024)."""

    def test_4_weeks_intense(self) -> None:
        """AC-T024.1: 4 weeks = intense pacing."""
        config = get_pacing_config(4)

        assert config.weeks == 4
        assert config.name == "intense"
        assert config.chapters_per_week == 1.25  # 5 chapters / 4 weeks
        assert config.description is not None

    def test_8_weeks_relaxed(self) -> None:
        """AC-T024.2: 8 weeks = relaxed pacing."""
        config = get_pacing_config(8)

        assert config.weeks == 8
        assert config.name == "relaxed"
        assert config.chapters_per_week == 0.625  # 5 chapters / 8 weeks
        assert config.description is not None

    def test_pacing_affects_decay_rate(self) -> None:
        """AC-T024.1-2: Pacing affects decay rate."""
        intense = get_pacing_config(4)
        relaxed = get_pacing_config(8)

        # Intense pacing has higher decay (more pressure)
        assert intense.decay_multiplier > relaxed.decay_multiplier

    def test_pacing_affects_touchpoint_frequency(self) -> None:
        """AC-T024.1-2: Pacing affects touchpoint frequency."""
        intense = get_pacing_config(4)
        relaxed = get_pacing_config(8)

        # Intense pacing has more frequent touchpoints
        assert intense.touchpoints_per_day > relaxed.touchpoints_per_day

    def test_invalid_pacing_raises(self) -> None:
        """AC-T024.3: Invalid pacing raises ValueError."""
        with pytest.raises(ValueError):
            get_pacing_config(6)


class TestConversationStyleConfig:
    """Tests for conversation style configuration."""

    @pytest.fixture
    def configurator(self) -> PreferenceConfigurator:
        """Create configurator instance."""
        return PreferenceConfigurator()

    def test_listener_style(self, configurator: PreferenceConfigurator) -> None:
        """Listener style: more questions, less sharing."""
        user_id = uuid4()
        configurator.configure(
            user_id=user_id,
            conversation_style=ConversationStyle.LISTENER,
        )

        style_config = configurator.get_conversation_style_config(user_id)
        assert style_config.question_ratio > 0.4
        assert style_config.sharing_ratio < 0.3

    def test_sharer_style(self, configurator: PreferenceConfigurator) -> None:
        """Sharer style: more sharing, fewer questions."""
        user_id = uuid4()
        configurator.configure(
            user_id=user_id,
            conversation_style=ConversationStyle.SHARER,
        )

        style_config = configurator.get_conversation_style_config(user_id)
        assert style_config.sharing_ratio > 0.4
        assert style_config.question_ratio < 0.3

    def test_balanced_style_default(self, configurator: PreferenceConfigurator) -> None:
        """Balanced style is default."""
        user_id = uuid4()
        # No configuration - should be balanced

        style_config = configurator.get_conversation_style_config(user_id)
        assert 0.3 <= style_config.question_ratio <= 0.4
        assert 0.3 <= style_config.sharing_ratio <= 0.4


class TestPreferenceIntegration:
    """Integration tests for preference configuration."""

    @pytest.fixture
    def configurator(self) -> PreferenceConfigurator:
        """Create configurator instance."""
        return PreferenceConfigurator()

    def test_full_preference_configuration(self, configurator: PreferenceConfigurator) -> None:
        """Configure all preferences for a user."""
        user_id = uuid4()

        result = configurator.configure(
            user_id=user_id,
            darkness_level=4,
            pacing_weeks=4,
            conversation_style=ConversationStyle.LISTENER,
        )

        assert result.success is True

        # Verify all configured
        prefs = configurator.get_preferences(user_id)
        assert prefs.darkness_level == 4
        assert prefs.pacing_weeks == 4
        assert prefs.conversation_style == ConversationStyle.LISTENER

    def test_get_behavioral_config(self, configurator: PreferenceConfigurator) -> None:
        """Get combined behavioral configuration."""
        user_id = uuid4()
        configurator.configure(
            user_id=user_id,
            darkness_level=3,
            pacing_weeks=4,
        )

        behavioral = configurator.get_behavioral_config(user_id)

        # Should combine darkness and pacing configs
        assert behavioral.darkness_config is not None
        assert behavioral.pacing_config is not None
        assert behavioral.decay_rate > 0
        assert behavioral.allows_manipulation is True

    def test_preference_to_dict(self, configurator: PreferenceConfigurator) -> None:
        """Preferences can be serialized to dict."""
        user_id = uuid4()
        configurator.configure(
            user_id=user_id,
            darkness_level=5,
            pacing_weeks=8,
            conversation_style=ConversationStyle.SHARER,
        )

        prefs_dict = configurator.to_dict(user_id)

        assert prefs_dict["darkness_level"] == 5
        assert prefs_dict["pacing_weeks"] == 8
        assert prefs_dict["conversation_style"] == "sharer"
