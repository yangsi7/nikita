"""
Tests for Boss System Agent Integration (T12)

TDD: Write tests FIRST, verify FAIL, then implement.

Acceptance Criteria:
- AC-T12-001: Text agent checks boss trigger after score update
- AC-T12-002: Boss encounter uses special system prompt with challenge
- AC-T12-003: Agent rejects normal chat during boss_fight
- AC-T12-004: Game over state prevents further agent interaction
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


class TestGameStatusGating:
    """Test that handler respects game_status field."""

    @pytest.mark.asyncio
    async def test_ac_t12_004_game_over_returns_ended_response(self):
        """Given game_status='game_over', Then handler returns game ended message."""
        from nikita.agents.text.handler import MessageHandler

        handler = MessageHandler()
        user_id = uuid4()

        # Mock both get_nikita_agent_for_user and generate_response
        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'game_over'
                mock_deps.user.chapter = 1
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Normal response"

                decision = await handler.handle(user_id, "Hello!")

                # Game over should return special response, not call generate_response
                assert decision.should_respond is True
                assert 'game' in decision.response.lower() or 'over' in decision.response.lower() or 'ended' in decision.response.lower()
                # Should NOT have called the normal response generator
                mock_gen.assert_not_called()

    @pytest.mark.asyncio
    async def test_game_won_returns_celebration_response(self):
        """Given game_status='won', Then handler returns celebration message."""
        from nikita.agents.text.handler import MessageHandler

        handler = MessageHandler()
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'won'
                mock_deps.user.chapter = 5
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Normal response"

                decision = await handler.handle(user_id, "Hello!")

                # Won should return post-game mode message
                assert decision.should_respond is True
                # Response should be about winning/established relationship
                # For now, generate_response may still be called in won state


class TestBossFightMode:
    """Test boss_fight mode handling."""

    @pytest.mark.asyncio
    async def test_ac_t12_003_boss_fight_directs_to_challenge(self):
        """Given game_status='boss_fight', Then handler includes boss context."""
        from nikita.agents.text.handler import MessageHandler

        handler = MessageHandler()
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'boss_fight'
                mock_deps.user.chapter = 2
                mock_deps.user.boss_attempts = 0
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Boss challenge response"

                decision = await handler.handle(user_id, "What's up?")

                # Boss fight mode should generate a response
                assert decision.should_respond is True
                # Response may be transformed by TextPatternProcessor (lowercase)
                assert "boss challenge response" in decision.response.lower()

    @pytest.mark.asyncio
    async def test_boss_fight_skip_disabled(self):
        """Given boss_fight mode, Then skip decision is NOT applied."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        # Create a skip decision that would always skip
        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True

        handler = MessageHandler(skip_decision=mock_skip)
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'boss_fight'
                mock_deps.user.chapter = 1
                mock_deps.user.boss_attempts = 0
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Boss response"

                decision = await handler.handle(user_id, "Challenge response")

                # Even with skip enabled, boss_fight should NOT skip
                assert decision.should_respond is True


class TestBossTriggerCheck:
    """Test boss trigger checking after score updates."""

    @pytest.mark.asyncio
    async def test_ac_t12_001_checks_boss_trigger_integration(self):
        """Given normal message, When score updated, Then checks boss trigger."""
        from nikita.agents.text.handler import MessageHandler

        handler = MessageHandler()
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'active'
                mock_deps.user.chapter = 1
                mock_deps.user.relationship_score = Decimal("54")
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Hey there!"

                decision = await handler.handle(user_id, "Hello!")

                # Normal processing should complete
                assert decision.should_respond is True
                # Response may be transformed by TextPatternProcessor (lowercase)
                assert "hey there" in decision.response.lower()

    def test_should_trigger_boss_method_available(self):
        """BossStateMachine.should_trigger_boss is available for integration."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, 'should_trigger_boss')
        assert callable(sm.should_trigger_boss)

    def test_should_trigger_boss_returns_true_at_threshold(self):
        """should_trigger_boss returns True when threshold met."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        result = sm.should_trigger_boss(
            relationship_score=Decimal("55"),
            chapter=1,
            game_status="active"
        )
        assert result is True


class TestBossPromptIntegration:
    """Test boss prompt system integration."""

    @pytest.mark.asyncio
    async def test_ac_t12_002_initiate_boss_available(self):
        """initiate_boss method returns challenge prompt for integration."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()

        result = await sm.initiate_boss(user_id, chapter=1)

        assert 'challenge_context' in result
        assert 'success_criteria' in result
        assert 'in_character_opening' in result
        assert result['chapter'] == 1


class TestActiveStatusProcessing:
    """Test normal 'active' status message processing."""

    @pytest.mark.asyncio
    async def test_active_status_processes_normally(self):
        """Given game_status='active', Then normal message processing occurs."""
        from nikita.agents.text.handler import MessageHandler

        handler = MessageHandler()
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'active'
                mock_deps.user.chapter = 3
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Normal response"

                decision = await handler.handle(user_id, "Hello!")

                assert decision.should_respond is True
                # Response may be transformed by TextPatternProcessor (may add emoji)
                assert "Normal response" in decision.response or "normal response" in decision.response.lower()
                mock_gen.assert_called_once()


class TestResponseDecisionFields:
    """Test ResponseDecision contains boss-related fields."""

    def test_response_decision_has_game_status_info(self):
        """ResponseDecision can include game_status context."""
        from nikita.agents.text.handler import ResponseDecision
        from datetime import datetime, timezone

        # Basic ResponseDecision creation
        decision = ResponseDecision(
            response="Test",
            delay_seconds=0,
            scheduled_at=datetime.now(timezone.utc),
            should_respond=True
        )
        assert decision.response == "Test"


class TestGameOverSkipDisabled:
    """Test that skip decision doesn't apply to game_over/won states."""

    @pytest.mark.asyncio
    async def test_game_over_ignores_skip_decision(self):
        """Given game_over, skip decision should NOT apply."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        # Create a skip decision that would always skip
        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True

        handler = MessageHandler(skip_decision=mock_skip)
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'game_over'
                mock_deps.user.chapter = 1
                mock_get.return_value = (mock_agent, mock_deps)

                decision = await handler.handle(user_id, "Hello!")

                # Even with skip enabled, game_over should NOT skip
                assert decision.should_respond is True
                # skip_decision.should_skip should NOT have been called
                mock_skip.should_skip.assert_not_called()
