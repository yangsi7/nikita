"""Tests for G3: Voice Call DB Logging (Spec 072).

Verifies:
- VoiceCall model structure
- VoiceCallRepository CRUD operations
- VoiceService creates VoiceCall record after call ends

TDD: Tests written before implementation.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


# =============================================================================
# 1. VoiceCall Model Tests
# =============================================================================


class TestVoiceCallModel:
    """Test VoiceCall SQLAlchemy model."""

    def test_model_importable(self):
        """VoiceCall model can be imported."""
        from nikita.db.models.voice_call import VoiceCall
        assert VoiceCall is not None

    def test_model_has_required_fields(self):
        """VoiceCall has all required columns."""
        from nikita.db.models.voice_call import VoiceCall
        import sqlalchemy as sa

        mapper = sa.inspect(VoiceCall)
        columns = {col.key for col in mapper.columns}

        required = {
            "id",
            "user_id",
            "elevenlabs_session_id",
            "started_at",
            "ended_at",
            "duration_seconds",
            "transcript",
            "summary",
            "score_delta",
            "created_at",
        }
        assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_model_tablename(self):
        """VoiceCall uses correct table name."""
        from nikita.db.models.voice_call import VoiceCall
        assert VoiceCall.__tablename__ == "voice_calls"

    def test_model_instantiation(self):
        """VoiceCall can be instantiated with required fields."""
        from nikita.db.models.voice_call import VoiceCall

        user_id = uuid4()
        call = VoiceCall(
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
        )
        assert call.user_id == user_id

    def test_model_optional_fields_default_none(self):
        """Optional fields default to None."""
        from nikita.db.models.voice_call import VoiceCall

        call = VoiceCall(
            user_id=uuid4(),
            started_at=datetime.now(timezone.utc),
        )
        assert call.elevenlabs_session_id is None
        assert call.ended_at is None
        assert call.duration_seconds is None
        assert call.transcript is None
        assert call.summary is None
        assert call.score_delta is None


# =============================================================================
# 2. VoiceCallRepository Tests
# =============================================================================


class TestVoiceCallRepository:
    """Test VoiceCallRepository CRUD operations."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def sample_voice_call(self):
        from nikita.db.models.voice_call import VoiceCall
        return VoiceCall(
            id=uuid4(),
            user_id=uuid4(),
            elevenlabs_session_id="el_session_abc123",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            duration_seconds=180,
            transcript="nikita: Hey!\nuser: Hi!",
            summary="Brief greeting call.",
            score_delta=Decimal("2.5"),
        )

    def test_repository_importable(self):
        """VoiceCallRepository can be imported."""
        from nikita.db.repositories.voice_call_repository import VoiceCallRepository
        assert VoiceCallRepository is not None

    @pytest.mark.asyncio
    async def test_create_persists_call(self, mock_session, sample_voice_call):
        """create() adds VoiceCall to session and flushes."""
        from nikita.db.repositories.voice_call_repository import VoiceCallRepository

        repo = VoiceCallRepository(mock_session)
        await repo.create(sample_voice_call)

        mock_session.add.assert_called_once_with(sample_voice_call)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_queries_correctly(self, mock_session):
        """get_by_user() returns list of VoiceCalls for a user."""
        from nikita.db.repositories.voice_call_repository import VoiceCallRepository
        from nikita.db.models.voice_call import VoiceCall

        user_id = uuid4()

        # Mock execute to return scalars with an all() method
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoiceCallRepository(mock_session)
        results = await repo.get_by_user(user_id)

        assert isinstance(results, list)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_session_id_returns_none_when_not_found(self, mock_session):
        """get_by_session_id() returns None if session not found."""
        from nikita.db.repositories.voice_call_repository import VoiceCallRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoiceCallRepository(mock_session)
        result = await repo.get_by_session_id("nonexistent_session")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_session_id_returns_call_when_found(self, mock_session, sample_voice_call):
        """get_by_session_id() returns VoiceCall when found."""
        from nikita.db.repositories.voice_call_repository import VoiceCallRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_voice_call)
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = VoiceCallRepository(mock_session)
        result = await repo.get_by_session_id("el_session_abc123")

        assert result is sample_voice_call

    @pytest.mark.asyncio
    async def test_create_new_call_helper(self, mock_session):
        """create_new_call() creates a VoiceCall with given parameters."""
        from nikita.db.repositories.voice_call_repository import VoiceCallRepository

        user_id = uuid4()
        session_id = "el_session_xyz789"
        started_at = datetime.now(timezone.utc)

        mock_session.refresh = AsyncMock()

        repo = VoiceCallRepository(mock_session)
        call = await repo.create_new_call(
            user_id=user_id,
            elevenlabs_session_id=session_id,
            started_at=started_at,
        )

        assert call.user_id == user_id
        assert call.elevenlabs_session_id == session_id
        assert call.started_at == started_at
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()


# =============================================================================
# 3. VoiceService DB Logging Integration Tests
# =============================================================================


class TestVoiceServiceCallLogging:
    """Test VoiceService._log_call_started() creates a VoiceCall DB record."""

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.elevenlabs_api_key = "test-key"
        s.elevenlabs_default_agent_id = "test-agent"
        s.elevenlabs_webhook_secret = "test-secret"
        s.is_unified_pipeline_enabled_for_user = MagicMock(return_value=False)
        return s

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.chapter = 3
        user.game_status = "active"
        user.relationship_score = 65.0
        user.metrics = MagicMock()
        user.metrics.relationship_score = 65.0
        user.vice_preferences = []
        return user

    @pytest.mark.asyncio
    async def test_log_call_started_creates_db_record(self, mock_settings, mock_user):
        """_log_call_started() creates a VoiceCall record in the database."""
        from nikita.agents.voice.service import VoiceService

        user_id = mock_user.id
        session_id = "voice_test_session_001"

        mock_repo = AsyncMock()
        mock_repo.create_new_call = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        service = VoiceService(settings=mock_settings)

        # VoiceCallRepository is imported inside the function, patch its module path
        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
            patch(
                "nikita.db.repositories.voice_call_repository.VoiceCallRepository",
                return_value=mock_repo,
            ),
            patch(
                "nikita.agents.voice.service.VoiceCallRepository",
                return_value=mock_repo,
                create=True,
            ),
        ):
            await service._log_call_started(user_id, session_id)

        mock_repo.create_new_call.assert_called_once()
        call_kwargs = mock_repo.create_new_call.call_args
        assert call_kwargs.kwargs.get("user_id") == user_id or (
            len(call_kwargs.args) > 0 and call_kwargs.args[0] == user_id
        )

    @pytest.mark.asyncio
    async def test_log_call_started_stores_session_id(self, mock_settings, mock_user):
        """_log_call_started() stores the ElevenLabs session ID."""
        from nikita.agents.voice.service import VoiceService

        user_id = mock_user.id
        session_id = "voice_unique_session_abc"

        mock_repo = AsyncMock()
        mock_repo.create_new_call = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        service = VoiceService(settings=mock_settings)

        # Patch at the repository module level where the class lives
        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
            patch(
                "nikita.db.repositories.voice_call_repository.VoiceCallRepository",
                return_value=mock_repo,
            ),
        ):
            await service._log_call_started(user_id, session_id)

        # The call should have been made via the real class constructor path.
        # Verify by checking the repo returned from the mock class was called.
        assert mock_repo.create_new_call.called, (
            "create_new_call was not called — check patch path"
        )
        call_kwargs = mock_repo.create_new_call.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        args = call_kwargs.args if call_kwargs.args else ()
        passed_session_id = kwargs.get("elevenlabs_session_id") or (
            args[1] if len(args) > 1 else None
        )
        assert passed_session_id == session_id

    @pytest.mark.asyncio
    async def test_log_call_started_handles_db_error_gracefully(self, mock_settings, mock_user):
        """_log_call_started() handles DB errors without raising (non-fatal)."""
        from nikita.agents.voice.service import VoiceService

        user_id = mock_user.id
        session_id = "voice_error_session"

        mock_repo = AsyncMock()
        mock_repo.create_new_call = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_session_ctx = AsyncMock()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_sm = MagicMock(return_value=mock_session_ctx)

        service = VoiceService(settings=mock_settings)

        # Should not raise — error is swallowed
        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_sm),
            patch(
                "nikita.agents.voice.service.VoiceCallRepository",
                return_value=mock_repo,
                create=True,
            ),
        ):
            await service._log_call_started(user_id, session_id)
