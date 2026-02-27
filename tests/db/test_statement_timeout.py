"""Tests for configurable statement_timeout (GH #83)."""
from unittest.mock import MagicMock, patch
import pytest
from nikita.config.settings import Settings


class TestStatementTimeoutConfig:
    """Verify statement_timeout is configurable via settings."""

    def test_default_is_30000ms(self):
        """Default db_statement_timeout_ms should be 30000."""
        settings = Settings(
            _env_file=None,  # Don't read .env
        )
        assert settings.db_statement_timeout_ms == 30000

    def test_validation_minimum(self):
        """Must be >= 1000ms."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(_env_file=None, db_statement_timeout_ms=500)

    def test_validation_maximum(self):
        """Must be <= 120000ms."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(_env_file=None, db_statement_timeout_ms=200000)

    def test_custom_value_accepted(self):
        """Custom value within range should be accepted."""
        settings = Settings(_env_file=None, db_statement_timeout_ms=60000)
        assert settings.db_statement_timeout_ms == 60000
