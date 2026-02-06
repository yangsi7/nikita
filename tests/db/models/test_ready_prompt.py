"""Tests for ReadyPrompt model (Spec 042 T0.4)."""

from uuid import uuid4

import pytest

from nikita.db.models.ready_prompt import ReadyPrompt


class TestReadyPromptModel:
    """Tests for ReadyPrompt SQLAlchemy model."""

    def test_has_all_required_columns(self):
        """AC-0.4.1: ReadyPrompt model with all columns mapped."""
        table = ReadyPrompt.__table__
        expected_columns = {
            "id", "user_id", "platform", "prompt_text", "token_count",
            "context_snapshot", "pipeline_version", "generation_time_ms",
            "is_current", "conversation_id", "created_at",
        }
        actual_columns = {c.name for c in table.columns}
        assert expected_columns.issubset(actual_columns), (
            f"Missing columns: {expected_columns - actual_columns}"
        )

    def test_no_updated_at_column(self):
        """ReadyPrompt is immutable - no updated_at column."""
        table = ReadyPrompt.__table__
        column_names = {c.name for c in table.columns}
        assert "updated_at" not in column_names

    def test_context_snapshot_is_jsonb(self):
        """AC-0.4.2: context_snapshot is JSONB type."""
        column = ReadyPrompt.__table__.columns["context_snapshot"]
        assert column.nullable is True
        assert "JSONB" in str(column.type).upper()

    def test_user_id_foreign_key(self):
        """AC-0.4.3: FK to users table with cascade delete."""
        column = ReadyPrompt.__table__.columns["user_id"]
        fks = list(column.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].column) == "users.id"
        assert fks[0].ondelete == "CASCADE"

    def test_conversation_id_foreign_key_nullable(self):
        """AC-0.4.3: FK to conversations, nullable."""
        column = ReadyPrompt.__table__.columns["conversation_id"]
        assert column.nullable is True
        fks = list(column.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].column) == "conversations.id"

    def test_platform_not_nullable(self):
        """Platform field is required."""
        column = ReadyPrompt.__table__.columns["platform"]
        assert column.nullable is False

    def test_is_current_default_true(self):
        """is_current defaults to True."""
        column = ReadyPrompt.__table__.columns["is_current"]
        assert column.nullable is False

    def test_model_instantiation(self):
        """Can create ReadyPrompt instance with all fields."""
        user_id = uuid4()
        prompt = ReadyPrompt(
            id=uuid4(),
            user_id=user_id,
            platform="text",
            prompt_text="You are Nikita...",
            token_count=500,
            context_snapshot={"chapter": 2, "score": 65.0},
            pipeline_version="042-v1",
            generation_time_ms=8500.0,
            is_current=True,
        )
        assert prompt.user_id == user_id
        assert prompt.platform == "text"
        assert prompt.prompt_text == "You are Nikita..."
        assert prompt.token_count == 500
        assert prompt.context_snapshot["chapter"] == 2
        assert prompt.pipeline_version == "042-v1"
        assert prompt.generation_time_ms == 8500.0
        assert prompt.is_current is True

    def test_model_voice_platform(self):
        """Can create ReadyPrompt with voice platform."""
        prompt = ReadyPrompt(
            id=uuid4(),
            user_id=uuid4(),
            platform="voice",
            prompt_text="Voice prompt...",
            token_count=200,
            pipeline_version="042-v1",
            generation_time_ms=3000.0,
            is_current=True,
        )
        assert prompt.platform == "voice"

    def test_tablename(self):
        """Table name is ready_prompts."""
        assert ReadyPrompt.__tablename__ == "ready_prompts"
