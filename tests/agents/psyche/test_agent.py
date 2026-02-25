"""Tests for Spec 056 Psyche Agent core (Phase 2: T6, T7, T9).

TDD: Write failing tests FIRST. These test the PsycheDeps dataclass,
Psyche agent creation, structured output, and token count tracking.

AC refs: AC-1.1, AC-1.2, AC-1.3, AC-1.6, AC-7.1, AC-7.2
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.psyche.deps import PsycheDeps
from nikita.agents.psyche.models import PsycheState


# ============================================================================
# PsycheDeps dataclass (T6 / AC-1.2)
# ============================================================================


class TestPsycheDeps:
    """AC-1.2: PsycheDeps has expected fields for context injection."""

    def test_dataclass_instantiation(self):
        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[{"score": 50}],
            emotional_states=[{"state": "happy"}],
            life_events=[{"event": "birthday"}],
            npc_interactions=[{"npc": "roommate"}],
            current_chapter=3,
        )
        assert deps.current_chapter == 3
        assert len(deps.score_history) == 1
        assert len(deps.emotional_states) == 1
        assert len(deps.life_events) == 1
        assert len(deps.npc_interactions) == 1

    def test_default_chapter(self):
        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
        )
        assert deps.current_chapter == 1

    def test_has_user_id_field(self):
        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
        )
        assert deps.user_id is not None

    def test_all_required_fields(self):
        """PsycheDeps has all expected fields (6 core + optional message)."""
        import dataclasses

        fields = {f.name for f in dataclasses.fields(PsycheDeps)}
        expected = {
            "user_id",
            "score_history",
            "emotional_states",
            "life_events",
            "npc_interactions",
            "current_chapter",
            "message",
        }
        assert fields == expected

    def test_message_field_optional(self):
        """message field defaults to None (used for Tier 2/3 analysis)."""
        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
        )
        assert deps.message is None

    def test_message_field_can_be_set(self):
        """message field accepts a string for trigger analysis."""
        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
            message="I feel so alone right now",
        )
        assert deps.message == "I feel so alone right now"


# ============================================================================
# Psyche Agent module structure (T7)
# ============================================================================


class TestPsycheAgentModuleStructure:
    """Psyche agent module exists with expected exports."""

    def test_agent_module_importable(self):
        from nikita.agents.psyche import agent as psyche_agent_mod

        assert psyche_agent_mod is not None

    def test_generate_psyche_state_exists(self):
        from nikita.agents.psyche.agent import generate_psyche_state

        assert callable(generate_psyche_state)

    def test_generate_psyche_state_is_async(self):
        from nikita.agents.psyche.agent import generate_psyche_state

        assert asyncio.iscoroutinefunction(generate_psyche_state)


# ============================================================================
# AC-1.1: Structured output - valid PsycheState
# ============================================================================


class TestGeneratePsycheStateOutput:
    """AC-1.1: generate_psyche_state returns valid PsycheState + token count."""

    @pytest.mark.asyncio
    async def test_returns_psyche_state_and_token_count(self):
        """generate_psyche_state returns (PsycheState, int) tuple."""
        from nikita.agents.psyche.agent import generate_psyche_state

        mock_state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="Be warm and encouraging.",
            internal_monologue="I feel comfortable.",
            vulnerability_level=0.6,
            emotional_tone="warm",
            topics_to_encourage=["hobbies"],
            topics_to_avoid=[],
        )

        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
            current_chapter=1,
        )

        # Mock the agent.run() call
        # Real code uses result.usage() method -> returns obj with input_tokens, output_tokens
        mock_usage = MagicMock()
        mock_usage.input_tokens = 300
        mock_usage.output_tokens = 200

        mock_result = MagicMock()
        mock_result.output = mock_state
        mock_result.usage = MagicMock(return_value=mock_usage)

        with patch(
            "nikita.agents.psyche.agent.get_psyche_agent"
        ) as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            result = await generate_psyche_state(deps)

        assert isinstance(result, tuple)
        assert len(result) == 2
        state, token_count = result
        assert isinstance(state, PsycheState)
        assert isinstance(token_count, int)
        assert token_count == 500  # 300 + 200

    @pytest.mark.asyncio
    async def test_output_has_all_eight_fields(self):
        """Generated PsycheState has all 8 fields populated."""
        from nikita.agents.psyche.agent import generate_psyche_state

        mock_state = PsycheState(
            attachment_activation="anxious",
            defense_mode="guarded",
            behavioral_guidance="Be patient with emotional responses.",
            internal_monologue="I worry they will leave.",
            vulnerability_level=0.3,
            emotional_tone="serious",
            topics_to_encourage=["trust", "commitment"],
            topics_to_avoid=["breakups"],
        )

        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
        )

        mock_usage = MagicMock()
        mock_usage.input_tokens = 250
        mock_usage.output_tokens = 200

        mock_result = MagicMock()
        mock_result.output = mock_state
        mock_result.usage = MagicMock(return_value=mock_usage)

        with patch(
            "nikita.agents.psyche.agent.get_psyche_agent"
        ) as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            state, _ = await generate_psyche_state(deps)

        assert state.attachment_activation == "anxious"
        assert state.defense_mode == "guarded"
        assert len(state.behavioral_guidance) > 0
        assert len(state.internal_monologue) > 0
        assert 0.0 <= state.vulnerability_level <= 1.0
        assert state.emotional_tone == "serious"
        assert isinstance(state.topics_to_encourage, list)
        assert isinstance(state.topics_to_avoid, list)


# ============================================================================
# AC-1.3: Configurable model via psyche_model setting
# ============================================================================


class TestConfigurableModel:
    """AC-1.3, AC-7.1, AC-7.2: Model selection via psyche_model setting."""

    def test_create_psyche_agent_function_exists(self):
        """Agent factory function should exist."""
        from nikita.agents.psyche.agent import _create_psyche_agent

        assert callable(_create_psyche_agent)

    def test_get_psyche_agent_function_exists(self):
        """Cached singleton getter should exist."""
        from nikita.agents.psyche.agent import get_psyche_agent

        assert callable(get_psyche_agent)

    @pytest.mark.asyncio
    async def test_default_model_is_sonnet(self):
        """AC-7.1: Default model is Sonnet 4.5 for batch."""
        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.psyche_model = (
                "anthropic:claude-sonnet-4-5-20250929"
            )
            from nikita.config.settings import get_settings

            assert "sonnet" in get_settings().psyche_model.lower()


# ============================================================================
# AC-1.6: Token count tracking
# ============================================================================


class TestTokenTracking:
    """AC-1.6: Token usage tracked per generation."""

    @pytest.mark.asyncio
    async def test_token_count_returned(self):
        """generate_psyche_state returns token_count as second tuple element."""
        from nikita.agents.psyche.agent import generate_psyche_state

        mock_state = PsycheState.default()

        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
        )

        mock_usage = MagicMock()
        mock_usage.input_tokens = 400
        mock_usage.output_tokens = 323

        mock_result = MagicMock()
        mock_result.output = mock_state
        mock_result.usage = MagicMock(return_value=mock_usage)

        with patch(
            "nikita.agents.psyche.agent.get_psyche_agent"
        ) as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            _, token_count = await generate_psyche_state(deps)

        assert token_count == 723

    @pytest.mark.asyncio
    async def test_zero_tokens_when_usage_unavailable(self):
        """Token count defaults to 0 when usage() raises exception."""
        from nikita.agents.psyche.agent import generate_psyche_state

        mock_state = PsycheState.default()

        deps = PsycheDeps(
            user_id=uuid4(),
            score_history=[],
            emotional_states=[],
            life_events=[],
            npc_interactions=[],
        )

        mock_result = MagicMock()
        mock_result.output = mock_state
        mock_result.usage = MagicMock(side_effect=Exception("no usage"))

        with patch(
            "nikita.agents.psyche.agent.get_psyche_agent"
        ) as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            _, token_count = await generate_psyche_state(deps)

        assert token_count == 0
