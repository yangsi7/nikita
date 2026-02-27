"""Tests for Models._normalize and prefix consistency (GH #85)."""
from unittest.mock import MagicMock, patch

from nikita.config.models import Models


class TestModelsNormalize:
    """Verify all Models methods normalize the anthropic: prefix."""

    def test_normalize_adds_prefix(self):
        assert Models._normalize("claude-haiku-4-5-20251001") == "anthropic:claude-haiku-4-5-20251001"

    def test_normalize_idempotent(self):
        assert Models._normalize("anthropic:claude-haiku-4-5-20251001") == "anthropic:claude-haiku-4-5-20251001"

    def test_haiku_normalizes(self):
        mock_settings = MagicMock()
        mock_settings.meta_prompt_model = "claude-haiku-4-5-20251001"  # No prefix
        with patch("nikita.config.models.get_settings", return_value=mock_settings):
            result = Models.haiku()
        assert result == "anthropic:claude-haiku-4-5-20251001"

    def test_sonnet_normalizes(self):
        mock_settings = MagicMock()
        mock_settings.anthropic_model = "claude-sonnet-4-6"  # No prefix
        with patch("nikita.config.models.get_settings", return_value=mock_settings):
            result = Models.sonnet()
        assert result == "anthropic:claude-sonnet-4-6"

    def test_opus_normalizes(self):
        mock_settings = MagicMock()
        mock_settings.psyche_model = "claude-opus-4-6"  # No prefix
        with patch("nikita.config.models.get_settings", return_value=mock_settings):
            result = Models.opus()
        assert result == "anthropic:claude-opus-4-6"

    def test_haiku_idempotent(self):
        mock_settings = MagicMock()
        mock_settings.meta_prompt_model = "anthropic:claude-haiku-4-5-20251001"  # Already prefixed
        with patch("nikita.config.models.get_settings", return_value=mock_settings):
            result = Models.haiku()
        assert result == "anthropic:claude-haiku-4-5-20251001"
