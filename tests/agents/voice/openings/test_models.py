"""Tests for Opening model."""

from __future__ import annotations

from nikita.agents.voice.openings.models import Opening


class TestOpeningModel:
    """Opening Pydantic model validation and behavior."""

    def test_minimal_opening_validates(self) -> None:
        opening = Opening(
            id="test",
            name="Test Opening",
            first_message="Hey {name}",
            system_prompt_addendum="Be cool.",
        )
        assert opening.id == "test"
        assert opening.mood == "neutral"  # default
        assert opening.weight == 1.0  # default
        assert opening.is_fallback is False  # default

    def test_full_opening_validates(self) -> None:
        opening = Opening(
            id="full",
            name="Full Test",
            darkness_range=(2, 4),
            scene_tags=["techno", "art"],
            life_stage_tags=["tech"],
            first_message="Hey {name} from {city}, into {interest}?",
            system_prompt_addendum="Be warm with {name}.",
            mood="flirty",
            goals=["Learn something", "Make them laugh"],
            forbidden=["Don't be boring"],
            max_duration_hint="4min",
            weight=0.8,
            is_fallback=False,
        )
        assert opening.darkness_range == (2, 4)
        assert len(opening.scene_tags) == 2
        assert len(opening.goals) == 2

    def test_format_first_message_with_placeholders(self) -> None:
        opening = Opening(
            id="test",
            name="Test",
            first_message="Hey {name} from {city}, obsessed with {interest}?",
            system_prompt_addendum="test",
        )
        result = opening.format_first_message(
            name="Alex", city="Zurich", interest="chess"
        )
        assert "Alex" in result
        assert "Zurich" in result
        assert "chess" in result

    def test_format_first_message_defaults(self) -> None:
        opening = Opening(
            id="test",
            name="Test",
            first_message="Hey {name} from {city}",
            system_prompt_addendum="test",
        )
        result = opening.format_first_message()
        assert "there" in result  # default name
        assert "your city" in result  # default city
