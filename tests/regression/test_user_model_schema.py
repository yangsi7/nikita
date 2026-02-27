"""Regression test for User model <-> DB schema alignment.

Prevents removing SQLAlchemy columns that still exist in the database,
which causes AttributeError at runtime.
"""
import pytest


class TestUserModelSchema:
    """Ensure User SQLAlchemy model has all columns from DB schema."""

    REQUIRED_COLUMNS = [
        "id", "telegram_id", "relationship_score", "chapter",
        "boss_attempts", "game_status", "conflict_details",
        "last_conflict_at", "cool_down_until",
        "cached_voice_prompt", "cached_voice_prompt_at",
        "notifications_enabled", "timezone",
    ]

    def test_user_model_has_required_columns(self):
        """All columns in baseline_schema.sql must exist on User model."""
        from nikita.db.models.user import User
        model_columns = {col.name for col in User.__table__.columns}
        missing = [col for col in self.REQUIRED_COLUMNS if col not in model_columns]
        assert not missing, (
            f"User model missing columns that exist in DB schema: {missing}\n"
            f"Model columns: {sorted(model_columns)}"
        )
