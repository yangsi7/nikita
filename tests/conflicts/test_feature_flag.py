"""Tests for conflict temperature feature flag (Spec 057, T1).

The flag function is_conflict_temperature_enabled() is now a deprecated
stub that always returns True. No production code calls it — all
dual-path flag checks were removed. Retained only for test patch
compatibility. Will be deleted in Spec 109.
"""

from nikita.conflicts import is_conflict_temperature_enabled


class TestFeatureFlag:
    """Test conflict temperature feature flag (deprecated stub)."""

    def test_always_returns_true(self):
        """Deprecated stub always returns True regardless of settings."""
        assert is_conflict_temperature_enabled() is True
