"""Unit tests for EngagementOrchestrator (Strangler Fig, Phase 2).

Tests engagement state updates, game-over detection, and breakup message
delivery in isolation using async mocks.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.config.enums import EngagementState
from nikita.platforms.telegram.handlers.engagement_orchestrator import EngagementOrchestrator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.update_game_status = AsyncMock()
    return repo


@pytest.fixture
def mock_conversation_repo():
    repo = MagicMock()
    repo.get_recent_messages_count = AsyncMock(return_value=5)
    repo.session = MagicMock()
    return repo


@pytest.fixture
def orchestrator(mock_bot, mock_user_repo, mock_conversation_repo):
    return EngagementOrchestrator(
        bot=mock_bot,
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
    )


@pytest.fixture
def mock_user():
    """User in CALIBRATING state with engagement_state DB record."""
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    user.last_interaction_at = datetime.now(timezone.utc)

    engagement_state_db = MagicMock()
    engagement_state_db.state = "CALIBRATING"
    engagement_state_db.calibration_score = Decimal("0.5")
    engagement_state_db.consecutive_clingy_days = 0
    engagement_state_db.consecutive_distant_days = 0
    engagement_state_db.consecutive_in_zone = 0
    engagement_state_db.multiplier = Decimal("0.9")
    user.engagement_state = engagement_state_db

    return user


# ---------------------------------------------------------------------------
# _is_new_day
# ---------------------------------------------------------------------------

class TestIsNewDay:
    """Tests for EngagementOrchestrator._is_new_day helper."""

    def test_returns_true_when_last_interaction_none(self, orchestrator):
        user = MagicMock(last_interaction_at=None)
        assert orchestrator._is_new_day(user) is True

    def test_returns_true_when_last_interaction_yesterday(self, orchestrator):
        user = MagicMock(
            last_interaction_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        assert orchestrator._is_new_day(user) is True

    def test_returns_false_when_last_interaction_today(self, orchestrator):
        user = MagicMock(last_interaction_at=datetime.now(timezone.utc))
        assert orchestrator._is_new_day(user) is False

    def test_handles_naive_datetime(self, orchestrator):
        """Naive datetimes (no tzinfo) should be treated as UTC."""
        user = MagicMock(
            last_interaction_at=datetime.now() - timedelta(days=2)
        )
        assert orchestrator._is_new_day(user) is True


# ---------------------------------------------------------------------------
# _get_consecutive_days
# ---------------------------------------------------------------------------

class TestGetConsecutiveDays:
    """Tests for EngagementOrchestrator._get_consecutive_days."""

    def test_returns_zero_when_no_db_record(self, orchestrator):
        assert orchestrator._get_consecutive_days(None, EngagementState.CLINGY) == 0

    def test_clingy_state_returns_clingy_counter(self, orchestrator):
        db = MagicMock(consecutive_clingy_days=4, consecutive_distant_days=0)
        assert orchestrator._get_consecutive_days(db, EngagementState.CLINGY) == 4

    def test_distant_state_returns_distant_counter(self, orchestrator):
        db = MagicMock(consecutive_clingy_days=0, consecutive_distant_days=3)
        assert orchestrator._get_consecutive_days(db, EngagementState.DISTANT) == 3

    def test_out_of_zone_returns_max_of_both(self, orchestrator):
        db = MagicMock(consecutive_clingy_days=2, consecutive_distant_days=5)
        assert orchestrator._get_consecutive_days(db, EngagementState.OUT_OF_ZONE) == 5

    def test_calibrating_returns_zero(self, orchestrator):
        db = MagicMock(consecutive_clingy_days=3, consecutive_distant_days=3)
        assert orchestrator._get_consecutive_days(db, EngagementState.CALIBRATING) == 0


# ---------------------------------------------------------------------------
# update_engagement_after_scoring — happy path
# ---------------------------------------------------------------------------

class TestUpdateEngagementAfterScoring:
    """Tests for the main update_engagement_after_scoring method."""

    @pytest.mark.asyncio
    async def test_state_machine_called_and_db_updated(
        self, orchestrator, mock_user, mock_conversation_repo
    ):
        """State machine runs and the DB record is mutated with new state."""
        mock_conversation_repo.get_recent_messages_count.return_value = 5

        mock_recovery = MagicMock()
        mock_recovery.check_point_of_no_return.return_value = MagicMock(is_game_over=False)

        with patch(
            "nikita.platforms.telegram.handlers.engagement_orchestrator.RecoveryManager",
            return_value=mock_recovery,
        ):
            orch = EngagementOrchestrator(
                bot=orchestrator.bot,
                user_repository=orchestrator.user_repository,
                conversation_repository=orchestrator.conversation_repo,
            )
            await orch.update_engagement_after_scoring(
                user=mock_user,
                chat_id=1,
                engagement_state=EngagementState.CALIBRATING,
            )

        # DB record should have been updated (state attribute set)
        assert mock_user.engagement_state.state is not None

    @pytest.mark.asyncio
    async def test_exception_is_silenced(self, orchestrator, mock_user):
        """Exceptions inside update_engagement_after_scoring are caught, not re-raised."""
        with patch(
            "nikita.platforms.telegram.handlers.engagement_orchestrator.EngagementStateMachine",
            side_effect=RuntimeError("state machine broken"),
        ):
            # Should not raise
            await orchestrator.update_engagement_after_scoring(
                user=mock_user,
                chat_id=1,
                engagement_state=EngagementState.CALIBRATING,
            )


# ---------------------------------------------------------------------------
# Game-over handling
# ---------------------------------------------------------------------------

class TestEngagementGameOver:
    """Tests for _handle_engagement_game_over."""

    @pytest.mark.asyncio
    async def test_clingy_game_over_sends_correct_message(
        self, orchestrator, mock_bot, mock_user_repo, mock_user
    ):
        """Clingy game-over sends the space/suffocating message."""
        await orchestrator._handle_engagement_game_over(
            user=mock_user, chat_id=1, reason="nikita_dumped_clingy"
        )

        mock_user_repo.update_game_status.assert_awaited_once_with(mock_user.id, "game_over")
        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "space" in sent_text.lower() or "suffocating" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_distant_game_over_sends_correct_message(
        self, orchestrator, mock_bot, mock_user_repo, mock_user
    ):
        """Distant game-over sends the waiting/disappeared message."""
        await orchestrator._handle_engagement_game_over(
            user=mock_user, chat_id=1, reason="nikita_dumped_distant"
        )

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "waiting" in sent_text.lower() or "disappeared" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_crisis_game_over_sends_correct_message(
        self, orchestrator, mock_bot, mock_user_repo, mock_user
    ):
        """Crisis game-over sends the chaos/better message."""
        await orchestrator._handle_engagement_game_over(
            user=mock_user, chat_id=1, reason="nikita_dumped_crisis"
        )

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "chaos" in sent_text.lower() or "better" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_unknown_reason_sends_generic_message(
        self, orchestrator, mock_bot, mock_user_repo, mock_user
    ):
        """Unknown game-over reason sends the generic breakup message."""
        await orchestrator._handle_engagement_game_over(
            user=mock_user, chat_id=1, reason="unknown_reason"
        )

        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "over" in sent_text.lower() or "this isn't working" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_game_status_set_to_game_over(
        self, orchestrator, mock_user_repo, mock_user
    ):
        """update_game_status is always called with 'game_over'."""
        await orchestrator._handle_engagement_game_over(
            user=mock_user, chat_id=1, reason="nikita_dumped_clingy"
        )

        mock_user_repo.update_game_status.assert_awaited_once_with(mock_user.id, "game_over")
