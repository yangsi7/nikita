"""Tests for conflict temperature feature flag (Spec 057, T1).

Tests cover:
- Default flag value (OFF)
- Feature flag utility function
"""

import pytest
from unittest.mock import patch, MagicMock

from nikita.conflicts import is_conflict_temperature_enabled


class TestFeatureFlag:
    """Test conflict temperature feature flag."""

    def test_default_off(self):
        """Feature flag defaults to OFF."""
        mock_settings = MagicMock()
        mock_settings.conflict_temperature_enabled = False
        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_conflict_temperature_enabled() is False

    def test_enabled_when_set(self):
        """Feature flag returns True when enabled."""
        mock_settings = MagicMock()
        mock_settings.conflict_temperature_enabled = True
        with patch("nikita.config.settings.get_settings", return_value=mock_settings):
            assert is_conflict_temperature_enabled() is True
