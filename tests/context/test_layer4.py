"""Tests for Layer4Computer (Spec 021, T009).

AC-T009.1: Layer4Computer class analyzes conversation context
AC-T009.2: Determines situation type: morning, evening, after-gap, mid-conversation
AC-T009.3: Generates situational meta-instructions
AC-T009.4: Token count within budget (~150)
AC-T009.5: Unit tests for each situation type
"""

from datetime import datetime, timedelta, timezone
from enum import Enum

import pytest

from nikita.context.layers.situation import (
    Layer4Computer,
    SituationType,
    get_layer4_computer,
)


class TestSituationType:
    """Tests for SituationType enum."""

    def test_situation_types_exist(self):
        """AC-T009.2: All situation types defined."""
        assert hasattr(SituationType, "MORNING")
        assert hasattr(SituationType, "EVENING")
        assert hasattr(SituationType, "AFTER_GAP")
        assert hasattr(SituationType, "MID_CONVERSATION")

    def test_situation_types_are_enum(self):
        """AC-T009.2: SituationType is an enum."""
        assert isinstance(SituationType.MORNING, Enum)


class TestLayer4Computer:
    """Tests for Layer4Computer class."""

    def test_init_default(self):
        """AC-T009.1: Computer initializes properly."""
        computer = Layer4Computer()
        assert computer is not None

    def test_detect_morning(self):
        """AC-T009.2: Detect morning situation (5-11am)."""
        computer = Layer4Computer()
        # 8am local
        morning_time = datetime.now(timezone.utc).replace(hour=8, minute=0)

        situation = computer.detect_situation(
            current_time=morning_time,
            last_interaction=morning_time - timedelta(hours=2),  # Recent but not active
            conversation_active=False,
        )

        assert situation == SituationType.MORNING

    def test_detect_evening(self):
        """AC-T009.2: Detect evening situation (6-11pm)."""
        computer = Layer4Computer()
        # 9pm local
        evening_time = datetime.now(timezone.utc).replace(hour=21, minute=0)

        situation = computer.detect_situation(
            current_time=evening_time,
            last_interaction=evening_time - timedelta(hours=2),  # Recent but not active
            conversation_active=False,
        )

        assert situation == SituationType.EVENING

    def test_detect_after_gap(self):
        """AC-T009.2: Detect after-gap situation (>4 hours since last)."""
        computer = Layer4Computer()
        current = datetime.now(timezone.utc).replace(hour=14, minute=0)  # 2pm

        situation = computer.detect_situation(
            current_time=current,
            last_interaction=current - timedelta(hours=6),  # 6 hours ago
            conversation_active=False,
        )

        assert situation == SituationType.AFTER_GAP

    def test_detect_mid_conversation(self):
        """AC-T009.2: Detect mid-conversation (active conv, <15 min since last)."""
        computer = Layer4Computer()
        current = datetime.now(timezone.utc)

        situation = computer.detect_situation(
            current_time=current,
            last_interaction=current - timedelta(minutes=5),  # 5 min ago
            conversation_active=True,
        )

        assert situation == SituationType.MID_CONVERSATION

    def test_compose_morning(self):
        """AC-T009.3: Compose morning situational prompt."""
        computer = Layer4Computer()
        prompt = computer.compose(SituationType.MORNING)

        assert isinstance(prompt, str)
        assert len(prompt) > 30
        assert any(
            word in prompt.lower()
            for word in ["morning", "start", "day", "check", "wake"]
        )

    def test_compose_evening(self):
        """AC-T009.3: Compose evening situational prompt."""
        computer = Layer4Computer()
        prompt = computer.compose(SituationType.EVENING)

        assert isinstance(prompt, str)
        assert len(prompt) > 30
        assert any(
            word in prompt.lower()
            for word in ["evening", "night", "wind", "relax", "end"]
        )

    def test_compose_after_gap(self):
        """AC-T009.3: Compose after-gap situational prompt."""
        computer = Layer4Computer()
        prompt = computer.compose(SituationType.AFTER_GAP)

        assert isinstance(prompt, str)
        assert len(prompt) > 30
        assert any(
            word in prompt.lower()
            for word in ["reconnect", "back", "miss", "catch up", "return"]
        )

    def test_compose_mid_conversation(self):
        """AC-T009.3: Compose mid-conversation situational prompt."""
        computer = Layer4Computer()
        prompt = computer.compose(SituationType.MID_CONVERSATION)

        assert isinstance(prompt, str)
        assert len(prompt) > 30
        assert any(
            word in prompt.lower()
            for word in ["continu", "flow", "respond", "natural", "topic"]
        )

    def test_token_estimate_within_budget(self):
        """AC-T009.4: Token estimate is within budget (~150)."""
        computer = Layer4Computer()

        for situation in SituationType:
            prompt = computer.compose(situation)
            # Rough estimate: 1 token ≈ 4 characters
            estimated_tokens = len(prompt) // 4

            assert estimated_tokens <= 200, f"{situation} exceeds budget: {estimated_tokens}"
            assert estimated_tokens >= 30, f"{situation} too short: {estimated_tokens}"

    def test_detect_and_compose(self):
        """AC-T009.1, AC-T009.3: Full detection and composition flow."""
        computer = Layer4Computer()
        current = datetime.now(timezone.utc).replace(hour=9, minute=0)

        prompt = computer.detect_and_compose(
            current_time=current,
            last_interaction=current - timedelta(hours=12),
            conversation_active=False,
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_different_situations_different_prompts(self):
        """AC-T009.3: Each situation has unique prompt."""
        computer = Layer4Computer()
        prompts = [computer.compose(sit) for sit in SituationType]

        unique_prompts = set(prompts)
        assert len(unique_prompts) == len(SituationType), "All situations should have unique prompts"

    def test_get_situation_hints(self):
        """AC-T009.3: Get structured hints for each situation."""
        computer = Layer4Computer()

        for situation in SituationType:
            hints = computer.get_situation_hints(situation)
            assert isinstance(hints, dict)
            assert "opening_style" in hints
            assert "topics_to_consider" in hints
            assert "tone_adjustment" in hints

    def test_mid_conversation_priority_over_time(self):
        """AC-T009.2: Mid-conversation takes priority over time-based situations."""
        computer = Layer4Computer()
        # 8am morning time but conversation is active
        morning_time = datetime.now(timezone.utc).replace(hour=8, minute=0)

        situation = computer.detect_situation(
            current_time=morning_time,
            last_interaction=morning_time - timedelta(minutes=2),
            conversation_active=True,  # Active conversation
        )

        # Should be mid-conversation, not morning
        assert situation == SituationType.MID_CONVERSATION


class TestLayer4ModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_layer4_computer_singleton(self):
        """AC-T009.1: get_layer4_computer returns singleton."""
        computer1 = get_layer4_computer()
        computer2 = get_layer4_computer()

        assert computer1 is computer2

    def test_convenience_detection(self):
        """AC-T009.1: Convenience function works."""
        computer = get_layer4_computer()
        current = datetime.now(timezone.utc)

        situation = computer.detect_situation(
            current_time=current,
            last_interaction=current - timedelta(minutes=5),
            conversation_active=True,
        )

        assert situation == SituationType.MID_CONVERSATION
