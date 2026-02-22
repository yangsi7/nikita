"""Tests for Spec 058 message handler boss integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.engine.chapters.boss import BossPhase, BossPhaseState
from nikita.engine.chapters.judgment import BossResult, JudgmentResult
from nikita.engine.chapters.phase_manager import BossPhaseManager


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_handler():
    """Create a minimal mock of TelegramMessageHandler with boss deps."""
    handler = MagicMock()
    handler.bot = AsyncMock()
    handler.bot.send_message = AsyncMock()
    handler.bot.send_chat_action = AsyncMock()
    handler.user_repository = AsyncMock()
    handler.conversation_repo = AsyncMock()
    handler.conversation_repo.get_active_conversation = AsyncMock(return_value=None)
    handler.boss_judgment = AsyncMock()
    handler.boss_state_machine = AsyncMock()

    # Import real methods and bind them
    from nikita.platforms.telegram.message_handler import MessageHandler as TelegramMessageHandler

    handler._handle_boss_response = TelegramMessageHandler._handle_boss_response.__get__(handler)
    handler._handle_single_turn_boss = TelegramMessageHandler._handle_single_turn_boss.__get__(handler)
    handler._handle_multi_phase_boss = TelegramMessageHandler._handle_multi_phase_boss.__get__(handler)
    handler._send_sanitized = TelegramMessageHandler._send_sanitized.__get__(handler)
    handler._send_boss_partial_message = TelegramMessageHandler._send_boss_partial_message.__get__(handler)
    handler._send_boss_pass_message = AsyncMock()
    handler._send_boss_fail_message = AsyncMock()
    handler._send_game_over_message = AsyncMock()
    handler._send_game_won_message = AsyncMock()
    handler._send_error_response = AsyncMock()
    handler._persist_conflict_details = AsyncMock()

    return handler


@pytest.fixture
def user_in_boss_fight():
    """User in boss_fight status with conflict_details."""
    mgr = BossPhaseManager()
    state = mgr.start_boss(chapter=2)
    details = mgr.persist_phase(None, state)

    user = SimpleNamespace(
        id="test-user-id",
        chapter=2,
        game_status="boss_fight",
        boss_attempts=0,
        conflict_details=details,
    )
    return user


# ── Tests ────────────────────────────────────────────────────────────


class TestFlagOffPreservesSingleTurn:
    """AC-8.2: Flag OFF preserves single-turn flow."""

    @pytest.mark.asyncio
    async def test_single_turn_when_flag_off(self, mock_handler):
        user = SimpleNamespace(
            id="test-user", chapter=1, game_status="boss_fight",
            boss_attempts=0, conflict_details=None,
        )
        mock_handler.boss_judgment.judge_boss_outcome = AsyncMock(
            return_value=JudgmentResult(outcome="PASS", reasoning="Good")
        )
        mock_handler.boss_state_machine.process_outcome = AsyncMock(
            return_value={"passed": True, "new_chapter": 2, "message": "Advanced!"}
        )

        with patch("nikita.engine.chapters.is_multi_phase_boss_enabled", return_value=False):
            await mock_handler._handle_boss_response(user, "my answer", 12345)

        mock_handler._send_boss_pass_message.assert_called_once()


class TestMultiPhaseOpeningToResolution:
    """AC-1.1, AC-1.2: OPENING -> RESOLUTION transition."""

    @pytest.mark.asyncio
    async def test_opening_sends_resolution_prompt(self, mock_handler, user_in_boss_fight):
        with patch("nikita.engine.chapters.is_multi_phase_boss_enabled", return_value=True):
            await mock_handler._handle_boss_response(
                user_in_boss_fight, "my opening response", 12345,
            )

        # Should send resolution prompt message
        mock_handler.bot.send_message.assert_called_once()
        call_args = mock_handler.bot.send_message.call_args
        assert call_args.kwargs.get("chat_id") == 12345

        # Should persist updated state
        mock_handler._persist_conflict_details.assert_called_once()

        # Should NOT judge (judgment happens in RESOLUTION)
        mock_handler.boss_judgment.judge_multi_phase_outcome.assert_not_called()


class TestMultiPhaseResolutionToJudgment:
    """AC-1.3: RESOLUTION -> judgment with full context."""

    @pytest.mark.asyncio
    async def test_resolution_triggers_judgment(self, mock_handler):
        # User in RESOLUTION phase
        state = BossPhaseState(
            phase=BossPhase.RESOLUTION,
            chapter=3,
            turn_count=1,
            conversation_history=[
                {"role": "user", "content": "opening response"},
                {"role": "assistant", "content": "resolution prompt"},
            ],
        )
        mgr = BossPhaseManager()
        details = mgr.persist_phase(None, state)

        user = SimpleNamespace(
            id="test-user", chapter=3, game_status="boss_fight",
            boss_attempts=0, conflict_details=details,
        )

        mock_handler.boss_judgment.judge_multi_phase_outcome = AsyncMock(
            return_value=JudgmentResult(outcome="PASS", reasoning="Great", confidence=0.9)
        )
        mock_handler.boss_state_machine.process_outcome = AsyncMock(
            return_value={
                "passed": True, "outcome": "PASS",
                "new_chapter": 4, "message": "Advanced!",
            }
        )

        with patch("nikita.engine.chapters.is_multi_phase_boss_enabled", return_value=True):
            await mock_handler._handle_boss_response(user, "resolution answer", 12345)

        mock_handler.boss_judgment.judge_multi_phase_outcome.assert_called_once()
        mock_handler.boss_state_machine.process_outcome.assert_called_once()
        mock_handler._send_boss_pass_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolution_partial_sends_partial_message(self, mock_handler):
        state = BossPhaseState(
            phase=BossPhase.RESOLUTION, chapter=2, turn_count=1,
            conversation_history=[
                {"role": "user", "content": "opening"},
                {"role": "assistant", "content": "resolution"},
            ],
        )
        mgr = BossPhaseManager()
        details = mgr.persist_phase(None, state)

        user = SimpleNamespace(
            id="test-user", chapter=2, game_status="boss_fight",
            boss_attempts=0, conflict_details=details,
        )

        mock_handler.boss_judgment.judge_multi_phase_outcome = AsyncMock(
            return_value=JudgmentResult(outcome="PARTIAL", reasoning="Effort", confidence=0.6)
        )
        mock_handler.boss_state_machine.process_outcome = AsyncMock(
            return_value={
                "passed": False, "outcome": "PARTIAL",
                "game_status": "active", "attempts": 0,
                "cool_down_until": "2025-01-02T00:00:00",
                "message": "Truce",
            }
        )

        with patch("nikita.engine.chapters.is_multi_phase_boss_enabled", return_value=True):
            await mock_handler._handle_boss_response(user, "my answer", 12345)

        # Partial message should be sent
        mock_handler.bot.send_message.assert_called_once()


class TestBossTimeout:
    """AC-1.6: 24h timeout auto-FAIL."""

    @pytest.mark.asyncio
    async def test_timeout_auto_fails(self, mock_handler):
        state = BossPhaseState(
            phase=BossPhase.OPENING, chapter=2,
            started_at=datetime.now(UTC) - timedelta(hours=25),
        )
        mgr = BossPhaseManager()
        details = mgr.persist_phase(None, state)

        user = SimpleNamespace(
            id="test-user", chapter=2, game_status="boss_fight",
            boss_attempts=1, conflict_details=details,
        )

        mock_handler.boss_state_machine.process_outcome = AsyncMock(
            return_value={
                "passed": False, "outcome": "FAIL",
                "attempts": 2, "game_over": False,
                "message": "Try again!",
            }
        )

        with patch("nikita.engine.chapters.is_multi_phase_boss_enabled", return_value=True):
            await mock_handler._handle_boss_response(user, "late response", 12345)

        mock_handler.boss_state_machine.process_outcome.assert_called_once_with(
            user_id="test-user",
            user_repository=mock_handler.user_repository,
            outcome="FAIL",
        )
        mock_handler._send_boss_fail_message.assert_called_once()


class TestNoPhaseStateFallback:
    """Graceful fallback when no phase state found."""

    @pytest.mark.asyncio
    async def test_falls_back_to_single_turn(self, mock_handler):
        user = SimpleNamespace(
            id="test-user", chapter=1, game_status="boss_fight",
            boss_attempts=0, conflict_details=None,
        )

        mock_handler.boss_judgment.judge_boss_outcome = AsyncMock(
            return_value=JudgmentResult(outcome="FAIL", reasoning="Bad")
        )
        mock_handler.boss_state_machine.process_outcome = AsyncMock(
            return_value={
                "passed": False, "attempts": 1,
                "game_over": False, "message": "Try again!",
            }
        )

        with patch("nikita.engine.chapters.is_multi_phase_boss_enabled", return_value=True):
            await mock_handler._handle_boss_response(user, "answer", 12345)

        # Should fall back to single-turn judgment
        mock_handler.boss_judgment.judge_boss_outcome.assert_called_once()
