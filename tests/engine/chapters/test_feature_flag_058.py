"""Tests for Spec 058 feature flag: multi_phase_boss_enabled."""

from __future__ import annotations

from unittest.mock import patch

from nikita.engine.chapters import is_multi_phase_boss_enabled


class TestMultiPhaseBossFeatureFlag:
    """AC-8.1, AC-8.2: Feature flag defaults OFF, respects env var."""

    def test_flag_defaults_off(self):
        """Feature flag defaults to OFF."""
        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.multi_phase_boss_enabled = False
            assert is_multi_phase_boss_enabled() is False

    def test_flag_respects_env_on(self):
        """Feature flag respects ON setting."""
        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.multi_phase_boss_enabled = True
            assert is_multi_phase_boss_enabled() is True
