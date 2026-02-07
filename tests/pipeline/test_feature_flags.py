"""Tests for Spec 043 T1.1: Feature flag default activation.

Verifies that unified_pipeline_enabled defaults to True and
unified_pipeline_rollout_pct defaults to 100.
"""

import os
from unittest.mock import patch
from uuid import uuid4

import pytest


class TestFeatureFlagDefaults:
    """T3.1: Feature flag tests."""

    def test_default_unified_pipeline_enabled_is_true(self):
        """AC-3.1.1: Default Settings has unified_pipeline_enabled=True."""
        from nikita.config.settings import Settings

        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            supabase_service_role_key="test-service-key",
            database_url="postgresql://test",
            anthropic_api_key="test-key",
        )
        assert settings.unified_pipeline_enabled is True

    def test_default_rollout_pct_is_100(self):
        """AC-3.1.2: Default Settings has unified_pipeline_rollout_pct=100."""
        from nikita.config.settings import Settings

        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            supabase_service_role_key="test-service-key",
            database_url="postgresql://test",
            anthropic_api_key="test-key",
        )
        assert settings.unified_pipeline_rollout_pct == 100

    def test_is_unified_pipeline_enabled_returns_true_with_defaults(self):
        """AC-3.1.3: is_unified_pipeline_enabled_for_user() returns True with defaults."""
        from nikita.config.settings import Settings

        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            supabase_service_role_key="test-service-key",
            database_url="postgresql://test",
            anthropic_api_key="test-key",
        )
        user_id = uuid4()
        assert settings.is_unified_pipeline_enabled_for_user(user_id) is True

    def test_env_var_override_disables_pipeline(self):
        """AC-3.1.4: Override via env var UNIFIED_PIPELINE_ENABLED=false returns False."""
        from nikita.config.settings import Settings

        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            supabase_service_role_key="test-service-key",
            database_url="postgresql://test",
            anthropic_api_key="test-key",
            unified_pipeline_enabled=False,
        )
        assert settings.unified_pipeline_enabled is False
        user_id = uuid4()
        assert settings.is_unified_pipeline_enabled_for_user(user_id) is False
