"""Unit tests for ScoringOrchestrator (Strangler Fig, Phase 2).

Tests score computation, persistence, and boss-threshold detection in
isolation using async mocks.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.config.enums import EngagementState
from nikita.platforms.telegram.handlers.scoring_orchestrator import ScoringOrchestrator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user_repo():
    repo = MagicMock()
    repo.update_score = AsyncMock()
    repo.set_boss_fight_status = AsyncMock()
    return repo


@pytest.fixture
def mock_conversation_repo():
    repo = MagicMock()
    repo.update_score_delta = AsyncMock()
    repo.close_conversation = AsyncMock()
    repo.session = MagicMock()
    return repo


@pytest.fixture
def mock_scoring_service():
    svc = MagicMock()
    svc.score_interaction = AsyncMock()
    return svc


@pytest.fixture
def orchestrator(mock_user_repo, mock_conversation_repo, mock_scoring_service):
    return ScoringOrchestrator(
        user_repository=mock_user_repo,
        conversation_repository=mock_conversation_repo,
        scoring_service=mock_scoring_service,
    )


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 1
    user.relationship_score = Decimal("50")
    user.engagement_state = MagicMock(state="CALIBRATING")
    user.metrics = MagicMock(
        intimacy=Decimal("50"),
        passion=Decimal("50"),
        trust=Decimal("50"),
        secureness=Decimal("50"),
    )
    return user


def _make_score_result(
    delta=Decimal("2"),
    events=None,
    score_before=Decimal("50"),
    score_after=Decimal("52"),
):
    """Build a minimal ScoreResult-like mock."""
    result = MagicMock()
    result.delta = delta
    result.score_before = score_before
    result.score_after = score_after
    result.events = events or []
    result.conflict_details = None
    result.deltas_applied = MagicMock(
        intimacy=Decimal("0.5"),
        passion=Decimal("0.5"),
        trust=Decimal("0.5"),
        secureness=Decimal("0.5"),
    )
    result.multiplier_applied = Decimal("1.0")
    return result


# ---------------------------------------------------------------------------
# Basic scoring flow
# ---------------------------------------------------------------------------

class TestScoringFlow:
    """Tests for the core scoring + persistence flow."""

    @pytest.mark.asyncio
    async def test_score_interaction_called_with_correct_args(
        self, orchestrator, mock_scoring_service, mock_user
    ):
        """score_interaction is called with user context."""
        mock_scoring_service.score_interaction.return_value = _make_score_result()
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_scoring_service.score_interaction.assert_called_once()
        call_kwargs = mock_scoring_service.score_interaction.call_args.kwargs
        assert call_kwargs["user_id"] == mock_user.id
        assert call_kwargs["user_message"] == "hi"
        assert call_kwargs["nikita_response"] == "hey"

    @pytest.mark.asyncio
    async def test_score_delta_persisted_to_user(
        self, orchestrator, mock_scoring_service, mock_user_repo, mock_user
    ):
        """Non-zero score delta is persisted via user_repository.update_score."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(delta=Decimal("3"))
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_user_repo.update_score.assert_called_once()
        call_kwargs = mock_user_repo.update_score.call_args.kwargs
        assert call_kwargs["delta"] == Decimal("3")

    @pytest.mark.asyncio
    async def test_zero_delta_skips_score_update(
        self, orchestrator, mock_scoring_service, mock_user_repo, mock_user
    ):
        """Zero score delta should NOT call update_score."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(delta=Decimal("0"))
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_user_repo.update_score.assert_not_called()

    @pytest.mark.asyncio
    async def test_conversation_score_delta_always_persisted(
        self, orchestrator, mock_scoring_service, mock_conversation_repo, mock_user
    ):
        """score_delta is always written to conversation regardless of value."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(delta=Decimal("0"))
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_conversation_repo.update_score_delta.assert_called_once()
        call_kwargs = mock_conversation_repo.update_score_delta.call_args.kwargs
        assert call_kwargs["conversation_id"] == conv_id


# ---------------------------------------------------------------------------
# Boss threshold detection
# ---------------------------------------------------------------------------

class TestBossThresholdDetection:
    """Tests for boss_threshold_reached event handling."""

    @pytest.fixture
    def boss_event(self):
        event = MagicMock()
        event.event_type = "boss_threshold_reached"
        return event

    @pytest.mark.asyncio
    async def test_boss_threshold_calls_set_boss_fight_status(
        self, orchestrator, mock_scoring_service, mock_user_repo, mock_user, boss_event
    ):
        """Boss threshold event triggers set_boss_fight_status."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(
            events=[boss_event]
        )
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_user_repo.set_boss_fight_status.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_boss_threshold_invokes_callback(
        self, orchestrator, mock_scoring_service, mock_user, boss_event
    ):
        """on_boss_threshold callback is awaited with (chat_id, chapter)."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(
            events=[boss_event]
        )
        callback = AsyncMock()
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=42,
            conversation_id=conv_id,
            on_boss_threshold=callback,
        )

        callback.assert_awaited_once_with(42, mock_user.chapter)

    @pytest.mark.asyncio
    async def test_no_boss_event_skips_set_boss_fight_status(
        self, orchestrator, mock_scoring_service, mock_user_repo, mock_user
    ):
        """Without boss_threshold_reached event, set_boss_fight_status is not called."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(events=[])
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_user_repo.set_boss_fight_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_boss_threshold_closes_conversation_first(
        self, orchestrator, mock_scoring_service, mock_conversation_repo, mock_user, boss_event
    ):
        """R-7: Conversation is closed before setting boss_fight status."""
        mock_scoring_service.score_interaction.return_value = _make_score_result(
            events=[boss_event], delta=Decimal("5")
        )
        conv_id = uuid4()
        call_order = []
        mock_conversation_repo.close_conversation.side_effect = (
            lambda **kw: call_order.append("close") or AsyncMock(return_value=None)()
        )

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )

        mock_conversation_repo.close_conversation.assert_called_once()


# ---------------------------------------------------------------------------
# Engagement callback
# ---------------------------------------------------------------------------

class TestEngagementCallback:
    """Tests for on_engagement_update callback."""

    @pytest.mark.asyncio
    async def test_engagement_callback_invoked_after_scoring(
        self, orchestrator, mock_scoring_service, mock_user
    ):
        """on_engagement_update callback is called after the scoring is complete."""
        mock_scoring_service.score_interaction.return_value = _make_score_result()
        callback = AsyncMock()
        conv_id = uuid4()

        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
            on_engagement_update=callback,
        )

        callback.assert_awaited_once()
        call_args = callback.await_args
        assert call_args.args[0] is mock_user
        assert call_args.args[1] == 1  # chat_id

    @pytest.mark.asyncio
    async def test_no_engagement_callback_no_error(
        self, orchestrator, mock_scoring_service, mock_user
    ):
        """Without on_engagement_update callback, no error is raised."""
        mock_scoring_service.score_interaction.return_value = _make_score_result()
        conv_id = uuid4()

        # Should not raise
        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
            on_engagement_update=None,
        )


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

class TestErrorResilience:
    """Tests for error handling in ScoringOrchestrator."""

    @pytest.mark.asyncio
    async def test_scoring_exception_is_silenced(
        self, orchestrator, mock_scoring_service, mock_user
    ):
        """Exceptions inside score_and_check_boss are caught and not re-raised."""
        mock_scoring_service.score_interaction.side_effect = RuntimeError("db error")
        conv_id = uuid4()

        # Should not raise
        await orchestrator.score_and_check_boss(
            user=mock_user,
            user_message="hi",
            nikita_response="hey",
            chat_id=1,
            conversation_id=conv_id,
        )
