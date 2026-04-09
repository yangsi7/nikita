"""Tests for OpeningSelector wiring in inbound handler (Spec 209 PR 209-2).

AC-FR002-001: Profile params extracted and passed to OpeningSelector
AC-FR002-002: No profile -> fallback to static chapter-keyed greeting
AC-FR002-003: Selector exception -> fallback + warning log
AC-FR002-004: Template interpolates name, city, interest
"""

from __future__ import annotations

import logging
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.openings.models import Opening


def _make_user(**overrides):
    """Create a mock User for inbound handler tests."""
    defaults = dict(
        id=uuid4(),
        chapter=3,
        game_status="active",
        name="Alex",
        relationship_score=Decimal("65.0"),
        metrics=MagicMock(relationship_score=Decimal("65.0")),
        vice_preferences=[],
        onboarding_profile={
            "name": "Alex",
            "darkness_level": 4,
            "hangout_spots": ["techno"],
            "location_city": "Berlin",
            "hobbies": ["DJing"],
        },
        timezone="UTC",
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_opening(**overrides):
    """Create an Opening model for testing."""
    defaults = dict(
        id="test_opening",
        name="Test Opening",
        first_message="Hey {name}! Love {city}. Into {interest}?",
        system_prompt_addendum="Test addendum",
        darkness_range=(1, 5),
    )
    defaults.update(overrides)
    return Opening(**defaults)


class TestOpeningSelectorWiring:
    """Spec 209 FR-002: Dynamic voice openings via OpeningSelector."""

    def test_full_profile_extracts_params(self):
        """AC-FR002-001: Profile params extracted and passed to selector."""
        from nikita.agents.voice.inbound import InboundCallHandler

        user = _make_user()
        handler = InboundCallHandler()

        opening = _make_opening()
        mock_selector = MagicMock()
        mock_selector.select.return_value = opening

        with patch(
            "nikita.agents.voice.openings.OpeningSelector",
            return_value=mock_selector,
        ), patch(
            "nikita.agents.voice.openings.registry.get_opening_registry",
        ):
            result = handler._get_first_message(user)

        mock_selector.select.assert_called_once_with(
            drug_tolerance=4,
            scene="techno",
            life_stage=None,
        )

    def test_full_profile_interpolates_template(self):
        """AC-FR002-004: Template interpolates name, city, interest."""
        from nikita.agents.voice.inbound import InboundCallHandler

        user = _make_user()
        handler = InboundCallHandler()

        opening = _make_opening()
        mock_selector = MagicMock()
        mock_selector.select.return_value = opening

        with patch(
            "nikita.agents.voice.openings.OpeningSelector",
            return_value=mock_selector,
        ), patch(
            "nikita.agents.voice.openings.registry.get_opening_registry",
        ):
            result = handler._get_first_message(user)

        assert "Alex" in result
        assert "Berlin" in result
        assert "DJing" in result

    def test_no_profile_uses_fallback(self):
        """AC-FR002-002: No onboarding_profile -> fallback to chapter-keyed greeting."""
        from nikita.agents.voice.inbound import InboundCallHandler

        user = _make_user(onboarding_profile=None, name="stranger", chapter=2)
        handler = InboundCallHandler()

        mock_selector = MagicMock()
        mock_selector.select.side_effect = ValueError("no templates match")

        with patch(
            "nikita.agents.voice.openings.OpeningSelector",
            return_value=mock_selector,
        ), patch(
            "nikita.agents.voice.openings.registry.get_opening_registry",
        ):
            result = handler._get_first_message(user)

        # Fallback for chapter 2
        assert "Good timing" in result

    def test_selector_exception_uses_fallback(self, caplog):
        """AC-FR002-003: Selector exception -> fallback + warning log."""
        from nikita.agents.voice.inbound import InboundCallHandler

        user = _make_user(chapter=3, name="TestUser")
        handler = InboundCallHandler()

        mock_selector = MagicMock()
        mock_selector.select.side_effect = ValueError("No templates loaded")

        with patch(
            "nikita.agents.voice.openings.OpeningSelector",
            return_value=mock_selector,
        ), patch(
            "nikita.agents.voice.openings.registry.get_opening_registry",
        ), caplog.at_level(logging.WARNING, logger="nikita.agents.voice.inbound"):
            result = handler._get_first_message(user)

        assert "OpeningSelector failed" in caplog.text
        # Fallback should match chapter 3 greeting
        assert "TestUser" in result

    def test_empty_hangout_spots_scene_none(self):
        """hangout_spots: [] -> scene=None."""
        from nikita.agents.voice.inbound import InboundCallHandler

        user = _make_user(
            onboarding_profile={
                "name": "Alex",
                "darkness_level": 3,
                "hangout_spots": [],
                "location_city": "Zurich",
                "hobbies": ["hiking"],
            }
        )
        handler = InboundCallHandler()

        opening = _make_opening()
        mock_selector = MagicMock()
        mock_selector.select.return_value = opening

        with patch(
            "nikita.agents.voice.openings.OpeningSelector",
            return_value=mock_selector,
        ), patch(
            "nikita.agents.voice.openings.registry.get_opening_registry",
        ):
            handler._get_first_message(user)

        mock_selector.select.assert_called_once_with(
            drug_tolerance=3,
            scene=None,
            life_stage=None,
        )

    def test_fallback_matches_chapter_keyed_strings(self):
        """Fallback output matches current hardcoded strings for chapters 1-5."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        expected_fragments = {
            1: "right? What's going on?",
            2: "Good timing",
            3: "I was hoping you'd call",
            4: "I've been wanting to hear your voice",
            5: "I missed you",
        }

        for chapter, fragment in expected_fragments.items():
            user = _make_user(chapter=chapter, name="Tester")

            # Force fallback by raising from selector
            mock_selector = MagicMock()
            mock_selector.select.side_effect = ValueError("force fallback")

            with patch(
                "nikita.agents.voice.openings.OpeningSelector",
                return_value=mock_selector,
            ), patch(
                "nikita.agents.voice.openings.registry.get_opening_registry",
            ):
                result = handler._get_first_message(user)

            assert fragment in result, f"Chapter {chapter} fallback missing expected fragment"
