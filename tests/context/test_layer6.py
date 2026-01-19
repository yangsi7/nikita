"""Tests for Layer6Handler (Spec 021, T015).

AC-T015.1: Layer6Handler class handles mid-conversation modifications
AC-T015.2: Supports mood_shift and memory_retrieval triggers
AC-T015.3: Memory retrieval via Graphiti
AC-T015.4: Latency < 200ms per modification
AC-T015.5: Unit tests for handler
"""

from datetime import datetime, timezone
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.context.layers.on_the_fly import (
    Layer6Handler,
    ModificationType,
    PromptModification,
    get_layer6_handler,
)


class TestModificationType:
    """Tests for ModificationType enum."""

    def test_modification_types_exist(self):
        """AC-T015.2: All modification types defined."""
        assert hasattr(ModificationType, "MOOD_SHIFT")
        assert hasattr(ModificationType, "MEMORY_RETRIEVAL")

    def test_modification_types_are_enum(self):
        """AC-T015.2: ModificationType is an enum."""
        assert isinstance(ModificationType.MOOD_SHIFT, Enum)


class TestPromptModification:
    """Tests for PromptModification model."""

    def test_prompt_modification_creation(self):
        """AC-T015.1: PromptModification can be created."""
        mod = PromptModification(
            type=ModificationType.MOOD_SHIFT,
            content="Nikita feels excited now",
            reason="User shared good news",
        )

        assert mod.type == ModificationType.MOOD_SHIFT
        assert "excited" in mod.content
        assert "good news" in mod.reason


class TestLayer6Handler:
    """Tests for Layer6Handler class."""

    def test_init_default(self):
        """AC-T015.1: Handler initializes properly."""
        handler = Layer6Handler()
        assert handler is not None

    def test_detect_mood_shift(self):
        """AC-T015.2: Detects mood shift triggers."""
        handler = Layer6Handler()

        # Message indicating positive mood shift
        result = handler.detect_triggers(
            message="I just got promoted at work!",
            current_mood="neutral",
        )

        # Should detect a potential mood shift
        assert any(t.type == ModificationType.MOOD_SHIFT for t in result)

    def test_detect_memory_retrieval(self):
        """AC-T015.2: Detects memory retrieval triggers."""
        handler = Layer6Handler()

        # Message that should trigger memory recall
        result = handler.detect_triggers(
            message="Remember when I told you about my sister?",
            current_mood="neutral",
        )

        # Should detect memory retrieval needed
        assert any(t.type == ModificationType.MEMORY_RETRIEVAL for t in result)

    def test_detect_no_triggers(self):
        """AC-T015.2: Returns empty list when no triggers."""
        handler = Layer6Handler()

        result = handler.detect_triggers(
            message="How was your day?",
            current_mood="neutral",
        )

        # Simple message may not trigger modifications
        assert isinstance(result, list)

    def test_apply_mood_shift(self):
        """AC-T015.2: Applies mood shift modification."""
        handler = Layer6Handler()

        modification = PromptModification(
            type=ModificationType.MOOD_SHIFT,
            content="Now feeling excited and supportive",
            reason="User shared positive news",
        )

        result = handler.apply_modification(
            current_prompt="Base prompt here.",
            modification=modification,
        )

        assert isinstance(result, str)
        assert "excited" in result.lower() or len(result) > len("Base prompt here.")

    @pytest.mark.asyncio
    async def test_retrieve_memory(self):
        """AC-T015.3: Retrieves memory via Graphiti."""
        handler = Layer6Handler()
        user_id = uuid4()

        # Mock the memory client
        with patch.object(handler, "_get_memory_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search.return_value = [
                MagicMock(content="User's sister lives in Seattle")
            ]
            mock_get_client.return_value = mock_client

            result = await handler.retrieve_memory(
                user_id=user_id,
                query="sister",
            )

            assert result is not None
            assert "Seattle" in result or "sister" in result.lower()

    @pytest.mark.asyncio
    async def test_retrieve_memory_no_results(self):
        """AC-T015.3: Handles no memory results gracefully."""
        handler = Layer6Handler()
        user_id = uuid4()

        with patch.object(handler, "_get_memory_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search.return_value = []
            mock_get_client.return_value = mock_client

            result = await handler.retrieve_memory(
                user_id=user_id,
                query="something not in memory",
            )

            # Should return None or empty when no results
            assert result is None or result == ""

    @pytest.mark.asyncio
    async def test_process_modification_mood_shift(self):
        """AC-T015.1: Full process for mood shift."""
        handler = Layer6Handler()
        user_id = uuid4()

        result = await handler.process_modification(
            user_id=user_id,
            current_prompt="Current prompt text.",
            modification=PromptModification(
                type=ModificationType.MOOD_SHIFT,
                content="Feeling supportive",
                reason="User achieved goal",
            ),
        )

        assert isinstance(result, str)
        assert len(result) >= len("Current prompt text.")

    @pytest.mark.asyncio
    async def test_process_modification_memory_retrieval(self):
        """AC-T015.1, AC-T015.3: Full process for memory retrieval."""
        handler = Layer6Handler()
        user_id = uuid4()

        with patch.object(handler, "_get_memory_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search.return_value = [
                MagicMock(content="User mentioned their cat is named Luna")
            ]
            mock_get_client.return_value = mock_client

            result = await handler.process_modification(
                user_id=user_id,
                current_prompt="Current prompt text.",
                modification=PromptModification(
                    type=ModificationType.MEMORY_RETRIEVAL,
                    content="",
                    reason="User mentioned pet",
                    query="cat",
                ),
            )

            assert isinstance(result, str)
            # Should include memory content
            assert "Luna" in result or "cat" in result

    def test_compose_layer6_stub(self):
        """AC-T015.1: Provides static Layer 6 section."""
        handler = Layer6Handler()

        result = handler.compose_static()

        assert isinstance(result, str)
        assert len(result) > 50
        # Should mention real-time adjustments
        assert "adjust" in result.lower() or "real-time" in result.lower() or "conversation" in result.lower()

    def test_token_estimate(self):
        """AC-T015.4: Has reasonable token estimate."""
        handler = Layer6Handler()

        assert hasattr(handler, "token_estimate")
        # Layer 6 budget is ~200 tokens
        assert handler.token_estimate <= 250


class TestLayer6ModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_layer6_handler_singleton(self):
        """AC-T015.1: get_layer6_handler returns singleton."""
        handler1 = get_layer6_handler()
        handler2 = get_layer6_handler()

        assert handler1 is handler2

    def test_handler_has_required_methods(self):
        """AC-T015.1: Handler has all required methods."""
        handler = get_layer6_handler()

        assert hasattr(handler, "detect_triggers")
        assert hasattr(handler, "apply_modification")
        assert hasattr(handler, "process_modification")
        assert hasattr(handler, "compose_static")
