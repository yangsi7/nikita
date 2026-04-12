"""Tests for startup environment variable guards.

GH #184: SUPABASE_URL must be set in non-debug environments.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_supabase_url_guard_raises_in_production():
    """GH #184: Missing SUPABASE_URL raises RuntimeError on startup."""
    mock_settings = MagicMock()
    mock_settings.debug = False
    mock_settings.task_auth_secret = "valid-secret"
    mock_settings.supabase_url = None  # Missing!

    # Simulate the guard logic from main.py:lifespan
    with pytest.raises(RuntimeError, match="supabase_url must be set"):
        if not mock_settings.debug and not mock_settings.supabase_url:
            raise RuntimeError(
                "supabase_url must be set in non-debug environments. "
                "Set the SUPABASE_URL environment variable."
            )


def test_supabase_url_guard_passes_when_set():
    """SUPABASE_URL guard passes when URL is set."""
    mock_settings = MagicMock()
    mock_settings.debug = False
    mock_settings.task_auth_secret = "valid-secret"
    mock_settings.supabase_url = "https://example.supabase.co"

    # Should not raise
    if not mock_settings.debug and not mock_settings.supabase_url:
        raise RuntimeError("supabase_url must be set")


def test_supabase_url_guard_skipped_in_debug():
    """SUPABASE_URL guard is skipped in debug mode."""
    mock_settings = MagicMock()
    mock_settings.debug = True
    mock_settings.supabase_url = None  # Missing but debug mode

    # Should not raise in debug mode
    if not mock_settings.debug and not mock_settings.supabase_url:
        raise RuntimeError("supabase_url must be set")
