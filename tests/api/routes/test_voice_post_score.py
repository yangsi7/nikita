"""Voice post-score hook tests (Spec 113).

Covers:
- AC-001: Boss triggered when threshold reached
- AC-002: Boss not triggered below threshold
- AC-003: Boss exempt when game_status != "active"
- AC-004: Consecutive crises incremented on negative delta + zone == "critical"
- AC-005: Consecutive crises reset on positive delta
- AC-006a: Boss hook failure is non-fatal (webhook returns 200)
- AC-006b: Crisis hook failure is non-fatal (webhook returns 200)

All tests call _process_webhook_event() directly and patch dependencies at their
source modules (lazy imports inside the function require source-level patching).
"""

from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event_data(user_id):
    """Build a minimal post_call_transcription payload with one valid exchange."""
    return {
        "type": "post_call_transcription",
        "data": {
            "conversation_id": "test-session-123",
            "transcript": [
                {"role": "user", "message": "Hello Nikita"},
                {"role": "agent", "message": "Hi there!"},
            ],
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "secret__user_id": str(user_id),
                }
            },
        },
    }


def make_call_score(
    intimacy: int = 0,
    passion: int = 0,
    trust: int = 0,
    secureness: int = 0,
) -> MagicMock:
    """Build a mock CallScore with controlled delta values."""
    cs = MagicMock()
    cs.session_id = "test-session-123"
    cs.deltas = MagicMock()
    cs.deltas.intimacy = Decimal(str(intimacy))
    cs.deltas.passion = Decimal(str(passion))
    cs.deltas.trust = Decimal(str(trust))
    cs.deltas.secureness = Decimal(str(secureness))
    cs.explanation = "test explanation"
    cs.confidence = 0.9
    return cs


def make_user(
    user_id=None,
    relationship_score=Decimal("60"),
    chapter=1,
    game_status="active",
    cool_down_until=None,
):
    """Build a mock User for repository returns."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.relationship_score = relationship_score
    user.chapter = chapter
    user.game_status = game_status
    user.cool_down_until = cool_down_until
    user.conflict_details = {}
    return user


# ---------------------------------------------------------------------------
# Session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """Sync-where-needed, async-where-needed session mock."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_session_maker(mock_session):
    """Factory that returns an async context manager yielding mock_session."""

    @asynccontextmanager
    async def _cm():
        yield mock_session

    def factory():
        return _cm()

    return factory


# ---------------------------------------------------------------------------
# Common patch context: all IO-touching dependencies except the one under test
# ---------------------------------------------------------------------------


def base_patches(mock_session_maker, mock_user_repo, mock_conversation, mock_scorer_cls):
    """Return a list of (target, kwargs) for patch() calls common to all tests."""
    return [
        ("nikita.db.database.get_session_maker", {"return_value": mock_session_maker}),
        ("nikita.db.repositories.user_repository.UserRepository", {"return_value": mock_user_repo}),
        ("nikita.db.models.conversation.Conversation", {"return_value": mock_conversation}),
        ("nikita.agents.voice.scoring.VoiceCallScorer", {"new": mock_scorer_cls}),
        ("nikita.api.routes.voice.get_settings",),
    ]


# ---------------------------------------------------------------------------
# Story 1: Boss trigger after voice scoring (AC-001, AC-002, AC-003, AC-006a)
# ---------------------------------------------------------------------------


class TestVoicePostScoreBoss:
    """Boss hook tests."""

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_conversation(self):
        conv = MagicMock()
        conv.id = uuid4()
        return conv

    @pytest.fixture
    def mock_scorer_cls(self):
        """VoiceCallScorer class mock — score_call + apply_score succeed by default."""
        scorer = AsyncMock()
        scorer.score_call = AsyncMock(return_value=make_call_score(intimacy=2, passion=2, trust=2, secureness=2))
        scorer.apply_score = AsyncMock()
        cls = MagicMock(return_value=scorer)
        return cls

    @pytest.mark.asyncio
    async def test_voice_post_score_triggers_boss(
        self, user_id, mock_session, mock_session_maker, mock_conversation, mock_scorer_cls
    ):
        """AC-001: Boss triggered when BossStateMachine.should_trigger_boss returns True."""
        from nikita.api.routes.voice import _process_webhook_event

        user = make_user(user_id=user_id, relationship_score=Decimal("58"), game_status="active")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock()

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine") as mock_boss_cls,
            patch("nikita.conflicts.persistence.load_conflict_details", new_callable=AsyncMock, return_value=None),
            patch("nikita.conflicts.persistence.save_conflict_details", new_callable=AsyncMock),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_boss = MagicMock()
            mock_boss.should_trigger_boss.return_value = True
            mock_boss_cls.return_value = mock_boss
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        assert result.get("status") == "processed"
        mock_user_repo.set_boss_fight_status.assert_awaited_once_with(user_id)

    @pytest.mark.asyncio
    async def test_voice_post_score_no_boss_below_threshold(
        self, user_id, mock_session, mock_session_maker, mock_conversation, mock_scorer_cls
    ):
        """AC-002: Boss not triggered when should_trigger_boss returns False."""
        from nikita.api.routes.voice import _process_webhook_event

        user = make_user(user_id=user_id, relationship_score=Decimal("30"), game_status="active")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock()

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine") as mock_boss_cls,
            patch("nikita.conflicts.persistence.load_conflict_details", new_callable=AsyncMock, return_value=None),
            patch("nikita.conflicts.persistence.save_conflict_details", new_callable=AsyncMock),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_boss = MagicMock()
            mock_boss.should_trigger_boss.return_value = False
            mock_boss_cls.return_value = mock_boss
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        assert result.get("status") == "processed"
        mock_user_repo.set_boss_fight_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_voice_post_score_boss_exempt_non_active(
        self, user_id, mock_session, mock_session_maker, mock_conversation, mock_scorer_cls
    ):
        """AC-003: Boss not triggered when game_status != 'active' (BSM returns False)."""
        from nikita.api.routes.voice import _process_webhook_event

        user = make_user(user_id=user_id, relationship_score=Decimal("70"), game_status="boss_fight")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock()

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine") as mock_boss_cls,
            patch("nikita.conflicts.persistence.load_conflict_details", new_callable=AsyncMock, return_value=None),
            patch("nikita.conflicts.persistence.save_conflict_details", new_callable=AsyncMock),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_boss = MagicMock()
            # BossStateMachine correctly returns False for non-active game_status
            mock_boss.should_trigger_boss.return_value = False
            mock_boss_cls.return_value = mock_boss
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        assert result.get("status") == "processed"
        mock_user_repo.set_boss_fight_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_voice_post_score_boss_failure_non_fatal(
        self, user_id, mock_session, mock_session_maker, mock_conversation, mock_scorer_cls
    ):
        """AC-006a: Boss hook raises → webhook still returns status=processed."""
        from nikita.api.routes.voice import _process_webhook_event

        user = make_user(user_id=user_id, relationship_score=Decimal("60"), game_status="active")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock(side_effect=RuntimeError("DB exploded"))

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine") as mock_boss_cls,
            patch("nikita.conflicts.persistence.load_conflict_details", new_callable=AsyncMock, return_value=None),
            patch("nikita.conflicts.persistence.save_conflict_details", new_callable=AsyncMock),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_boss = MagicMock()
            mock_boss.should_trigger_boss.return_value = True
            mock_boss_cls.return_value = mock_boss
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        # Must complete successfully despite boss hook failure
        assert result.get("status") == "processed"


# ---------------------------------------------------------------------------
# Story 2: Consecutive crises after voice scoring (AC-004, AC-005, AC-006b)
# ---------------------------------------------------------------------------


class TestVoicePostScoreCrises:
    """Consecutive crises hook tests."""

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_conversation(self):
        conv = MagicMock()
        conv.id = uuid4()
        return conv

    @pytest.fixture
    def no_boss_cls(self):
        """Boss SM that never triggers (keeps boss out of crises tests)."""
        boss = MagicMock()
        boss.should_trigger_boss.return_value = False
        cls = MagicMock(return_value=boss)
        return cls

    @pytest.mark.asyncio
    async def test_voice_post_score_crises_increment(
        self, user_id, mock_session, mock_session_maker, mock_conversation, no_boss_cls
    ):
        """AC-004: consecutive_crises incremented on negative delta + zone == 'critical'."""
        from nikita.api.routes.voice import _process_webhook_event
        from nikita.conflicts.models import ConflictDetails

        user = make_user(user_id=user_id, relationship_score=Decimal("35"), game_status="active")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock()

        # score_delta will be (-3) + (-2) + (-2) + (-1) = -8 → negative
        scorer = AsyncMock()
        scorer.score_call = AsyncMock(
            return_value=make_call_score(intimacy=-3, passion=-2, trust=-2, secureness=-1)
        )
        scorer.apply_score = AsyncMock()
        mock_scorer_cls = MagicMock(return_value=scorer)

        initial_details = ConflictDetails(consecutive_crises=1, zone="critical")
        saved_details: list[dict] = []

        async def capture_save(uid, d, s):
            saved_details.append(d)

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine", new=no_boss_cls),
            patch(
                "nikita.conflicts.persistence.load_conflict_details",
                new_callable=AsyncMock,
                return_value=initial_details.to_jsonb(),
            ),
            patch("nikita.conflicts.persistence.save_conflict_details", new=capture_save),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        assert result.get("status") == "processed"
        assert len(saved_details) == 1, "save_conflict_details must be called once"
        saved = ConflictDetails.from_jsonb(saved_details[0])
        assert saved.consecutive_crises == 2  # incremented from 1

    @pytest.mark.asyncio
    async def test_voice_post_score_crises_reset(
        self, user_id, mock_session, mock_session_maker, mock_conversation, no_boss_cls
    ):
        """AC-005: consecutive_crises reset to 0 on positive score delta."""
        from nikita.api.routes.voice import _process_webhook_event
        from nikita.conflicts.models import ConflictDetails

        user = make_user(user_id=user_id, relationship_score=Decimal("65"), game_status="active")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock()

        # score_delta = 3+2+2+1 = +8 → positive
        scorer = AsyncMock()
        scorer.score_call = AsyncMock(
            return_value=make_call_score(intimacy=3, passion=2, trust=2, secureness=1)
        )
        scorer.apply_score = AsyncMock()
        mock_scorer_cls = MagicMock(return_value=scorer)

        initial_details = ConflictDetails(consecutive_crises=3, zone="stable")
        saved_details: list[dict] = []

        async def capture_save(uid, d, s):
            saved_details.append(d)

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine", new=no_boss_cls),
            patch(
                "nikita.conflicts.persistence.load_conflict_details",
                new_callable=AsyncMock,
                return_value=initial_details.to_jsonb(),
            ),
            patch("nikita.conflicts.persistence.save_conflict_details", new=capture_save),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        assert result.get("status") == "processed"
        assert len(saved_details) == 1, "save_conflict_details must be called once"
        saved = ConflictDetails.from_jsonb(saved_details[0])
        assert saved.consecutive_crises == 0  # reset

    @pytest.mark.asyncio
    async def test_voice_post_score_crises_failure_non_fatal(
        self, user_id, mock_session, mock_session_maker, mock_conversation, no_boss_cls
    ):
        """AC-006b: Crisis hook raises → webhook still returns status=processed."""
        from nikita.api.routes.voice import _process_webhook_event

        user = make_user(user_id=user_id, relationship_score=Decimal("35"), game_status="active")
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user)
        mock_user_repo.set_boss_fight_status = AsyncMock()

        scorer = AsyncMock()
        scorer.score_call = AsyncMock(
            return_value=make_call_score(intimacy=-3, passion=-2, trust=-2, secureness=-1)
        )
        scorer.apply_score = AsyncMock()
        mock_scorer_cls = MagicMock(return_value=scorer)

        with (
            patch("nikita.db.database.get_session_maker", return_value=mock_session_maker),
            patch("nikita.db.repositories.user_repository.UserRepository", return_value=mock_user_repo),
            patch("nikita.db.models.conversation.Conversation", return_value=mock_conversation),
            patch("nikita.agents.voice.scoring.VoiceCallScorer", new=mock_scorer_cls),
            patch("nikita.engine.chapters.boss.BossStateMachine", new=no_boss_cls),
            patch(
                "nikita.conflicts.persistence.load_conflict_details",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB failure"),
            ),
            patch("nikita.conflicts.persistence.save_conflict_details", new_callable=AsyncMock),
            patch("nikita.api.routes.voice.get_settings") as mock_settings,
        ):
            mock_settings.return_value.unified_pipeline_enabled = False

            result = await _process_webhook_event(make_event_data(user_id))

        # Must complete successfully despite crisis hook failure
        assert result.get("status") == "processed"
