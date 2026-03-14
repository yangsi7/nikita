"""Tests for vice_pipeline_enabled setting (Spec 114 AC-006)."""

from nikita.config.settings import Settings


class TestVicePipelineSetting:
    """AC-006: vice_pipeline_enabled exists and defaults to False."""

    def test_vice_flag_setting_default(self):
        """Settings().vice_pipeline_enabled defaults to False (safe rollout gate)."""
        settings = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            supabase_service_role_key="test-service-key",
            database_url="postgresql://test",
            anthropic_api_key="test-key",
        )
        assert settings.vice_pipeline_enabled is False
