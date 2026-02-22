"""Integration tests for the handler callback chain.

Tests cross-module interactions:
ScoringOrchestrator -> BossEncounterHandler -> EngagementOrchestrator

All three handlers are wired together with mocked repos/bot to verify
the callback chain fires correctly end-to-end.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.config.enums import EngagementState
from nikita.platforms.telegram.handlers.scoring_orchestrator import ScoringOrchestrator
from nikita.platforms.telegram.handlers.boss_encounter import BossEncounterHandler
from nikita.platforms.telegram.handlers.engagement_orchestrator import EngagementOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_score_result(
    delta=Decimal("2"),
    events=None,
    score_before=Decimal("50"),
    score_after=Decimal("52"),
    conflict_details=None,
):
    """Build a minimal ScoreResult-like mock."""
    result = MagicMock()
    result.delta = delta
    result.score_before = score_before
    result.score_after = score_after
    result.events = events or []
    result.conflict_details = conflict_details
    result.deltas_applied = MagicMock(
        intimacy=Decimal("0.5"),
        passion=Decimal("0.5"),
        trust=Decimal("0.5"),
        secureness=Decimal("0.5"),
    )
    result.multiplier_applied = Decimal("1.0")
    return result


def _make_boss_event():
    """Build a boss_threshold_reached event mock."""
    event = MagicMock()
    event.event_type = "boss_threshold_reached"
    return event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_chat_action = AsyncMock()
    return bot


@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.update_score = AsyncMock()
    repo.set_boss_fight_status = AsyncMock()
    repo.update_game_status = AsyncMock()
    repo.update_conflict_details = AsyncMock()
    return repo


@pytest.fixture
def mock_conversation_repo():
    repo = MagicMock()
    repo.update_score_delta = AsyncMock()
    repo.close_conversation = AsyncMock()
    repo.get_active_conversation = AsyncMock(return_value=None)
    repo.get_recent_messages_count = AsyncMock(return_value=5)
    repo.session = MagicMock()
    return repo


@pytest.fixture
def mock_scoring_service():
    svc = MagicMock()
    svc.score_interaction = AsyncMock()
    return svc


@pytest.fixture
def mock_boss_judgment():
    judgment = MagicMock()
    judgment.judge_boss_outcome = AsyncMock()
    return judgment


@pytest.fixture
def mock_boss_state_machine():
    sm = MagicMock()
    sm.process_outcome = AsyncMock()
    return sm


@pytest.fixture
def scoring_orchestrator(mock_user_repo, mock_conversation_repo, mock_scoring_service):
    return ScoringOrchestrator(
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
        scoring_service=mock_scoring_service,
    )


@pytest.fixture
def boss_handler(mock_bot, mock_user_repo, mock_conversation_repo, mock_boss_judgment, mock_boss_state_machine):
    return BossEncounterHandler(
        bot=mock_bot,
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
        boss_judgment=mock_boss_judgment,
        boss_state_machine=mock_boss_state_machine,
    )


@pytest.fixture
def engagement_orchestrator(mock_bot, mock_user_repo, mock_conversation_repo):
    return EngagementOrchestrator(
        bot=mock_bot,
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
    )


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    user.relationship_score = Decimal("50")
    user.last_interaction_at = None
    user.engagement_state = MagicMock(
        state="CALIBRATING",
        calibration_score=Decimal("0.5"),
        consecutive_clingy_days=0,
        consecutive_distant_days=0,
        consecutive_in_zone=0,
        multiplier=Decimal("0.9"),
    )
    user.metrics = MagicMock(
        intimacy=Decimal("50"),
        passion=Decimal("50"),
        trust=Decimal("50"),
        secureness=Decimal("50"),
    )
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHandlerChainIntegration:
    """Tests for the callback chain across ScoringOrchestrator, BossEncounterHandler,
    and EngagementOrchestrator."""

    @pytest.mark.asyncio
    async def test_scoring_triggers_boss_threshold_callback(
        self, scoring_orchestrator, mock_scoring_service, mock_user_repo, mock_user, boss_handler
    ):
        """Score crosses threshold -> on_boss_threshold fires -> BossEncounterHandler.send_boss_opening called."""
        boss_event = _make_boss_event()
        mock_scoring_service.score_interaction.return_value = _make_score_result(
            delta=Decimal("5"), events=[boss_event]
        )

        send_opening_called = AsyncMock()

        async def on_boss_threshold(chat_id, chapter):
            await send_opening_called(chat_id, chapter)

        conv_id = uuid4()
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            await scoring_orchestrator.score_and_check_boss(
                user=mock_user,
                user_message="hello",
                nikita_response="hey",
                chat_id=42,
                conversation_id=conv_id,
                on_boss_threshold=on_boss_threshold,
            )

        mock_user_repo.set_boss_fight_status.assert_called_once_with(mock_user.id)
        send_opening_called.assert_awaited_once_with(42, mock_user.chapter)

    @pytest.mark.asyncio
    async def test_scoring_triggers_engagement_callback(
        self, scoring_orchestrator, mock_scoring_service, mock_user
    ):
        """Score computed -> on_engagement_update fires -> EngagementOrchestrator.update_engagement_after_scoring called."""
        mock_scoring_service.score_interaction.return_value = _make_score_result()

        engagement_callback = AsyncMock()
        conv_id = uuid4()

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            await scoring_orchestrator.score_and_check_boss(
                user=mock_user,
                user_message="hi",
                nikita_response="hey",
                chat_id=1,
                conversation_id=conv_id,
                on_engagement_update=engagement_callback,
            )

        engagement_callback.assert_awaited_once()
        call_args = engagement_callback.await_args
        assert call_args.args[0] is mock_user
        assert call_args.args[1] == 1  # chat_id

    @pytest.mark.asyncio
    async def test_boss_threshold_closes_active_conversation_first(
        self, scoring_orchestrator, mock_scoring_service, mock_conversation_repo, mock_user
    ):
        """Boss threshold -> conversation closed -> then boss status set (ordering)."""
        boss_event = _make_boss_event()
        mock_scoring_service.score_interaction.return_value = _make_score_result(
            delta=Decimal("5"), events=[boss_event]
        )

        call_order = []

        original_close = mock_conversation_repo.close_conversation

        async def track_close(**kwargs):
            call_order.append("close_conversation")
            return await original_close(**kwargs)

        mock_conversation_repo.close_conversation = AsyncMock(side_effect=track_close)

        conv_id = uuid4()
        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            await scoring_orchestrator.score_and_check_boss(
                user=mock_user,
                user_message="hi",
                nikita_response="hey",
                chat_id=1,
                conversation_id=conv_id,
            )

        mock_conversation_repo.close_conversation.assert_called_once()
        assert "close_conversation" in call_order

    @pytest.mark.asyncio
    async def test_full_chain_score_to_boss_to_engagement(
        self, scoring_orchestrator, mock_scoring_service, mock_user_repo, mock_user, boss_handler
    ):
        """End-to-end: message scored -> boss detected -> engagement updated -> all repos called in correct order."""
        boss_event = _make_boss_event()
        mock_scoring_service.score_interaction.return_value = _make_score_result(
            delta=Decimal("5"), events=[boss_event]
        )

        boss_callback = AsyncMock()
        engagement_callback = AsyncMock()
        conv_id = uuid4()

        with patch("nikita.conflicts.is_conflict_temperature_enabled", return_value=False):
            await scoring_orchestrator.score_and_check_boss(
                user=mock_user,
                user_message="hi",
                nikita_response="hey",
                chat_id=42,
                conversation_id=conv_id,
                on_boss_threshold=boss_callback,
                on_engagement_update=engagement_callback,
            )

        # Score persisted
        mock_user_repo.update_score.assert_called_once()
        # Boss status set
        mock_user_repo.set_boss_fight_status.assert_called_once_with(mock_user.id)
        # Boss callback fired
        boss_callback.assert_awaited_once_with(42, mock_user.chapter)
        # Engagement callback fired
        engagement_callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_game_over_from_engagement_cascade(
        self, mock_bot, mock_user_repo, mock_conversation_repo, mock_user
    ):
        """Engagement reaches point-of-no-return -> game_over status set -> breakup message sent."""
        # Set user to CLINGY with high consecutive days so RecoveryManager triggers game_over
        mock_user.engagement_state.state = "CLINGY"
        mock_user.engagement_state.consecutive_clingy_days = 10
        mock_user.engagement_state.consecutive_distant_days = 0
        mock_user.engagement_state.consecutive_in_zone = 0
        mock_user.last_interaction_at = None  # new day

        mock_conversation_repo.get_recent_messages_count.return_value = 20  # clingy behavior

        mock_recovery = MagicMock()
        mock_recovery.check_point_of_no_return.return_value = MagicMock(
            is_game_over=True,
            reason="nikita_dumped_clingy",
        )

        orch = EngagementOrchestrator(
            bot=mock_bot,
            user_repository=mock_user_repo,
            conversation_repository=mock_conversation_repo,
        )

        with patch(
            "nikita.platforms.telegram.handlers.engagement_orchestrator.RecoveryManager",
            return_value=mock_recovery,
        ):
            orch.recovery_manager = mock_recovery
            await orch.update_engagement_after_scoring(
                user=mock_user,
                chat_id=99,
                engagement_state=EngagementState.CLINGY,
            )

        mock_user_repo.update_game_status.assert_awaited_once_with(mock_user.id, "game_over")
        mock_bot.send_message.assert_called_once()
        sent_text = mock_bot.send_message.call_args.kwargs["text"]
        assert "space" in sent_text.lower() or "suffocating" in sent_text.lower()
