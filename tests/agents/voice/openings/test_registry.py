"""Tests for OpeningRegistry — YAML template loading and lookup."""

from __future__ import annotations

from pathlib import Path

from nikita.agents.voice.openings.registry import OpeningRegistry

# Use the real templates directory
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent.parent / (
    "nikita/agents/voice/openings/templates"
)


class TestOpeningRegistry:
    """Registry loads YAML templates and provides lookup."""

    def test_loads_all_templates(self) -> None:
        registry = OpeningRegistry(TEMPLATES_DIR)
        openings = registry.get_all()
        assert len(openings) >= 5, f"Expected >= 5 openings, got {len(openings)}"

    def test_get_by_id_warm_intro(self) -> None:
        registry = OpeningRegistry(TEMPLATES_DIR)
        opening = registry.get("warm_intro")
        assert opening is not None
        assert opening.id == "warm_intro"
        assert opening.is_fallback is True

    def test_get_by_id_challenge(self) -> None:
        registry = OpeningRegistry(TEMPLATES_DIR)
        opening = registry.get("challenge")
        assert opening is not None
        assert opening.darkness_range == (3, 4)

    def test_get_nonexistent_returns_none(self) -> None:
        registry = OpeningRegistry(TEMPLATES_DIR)
        assert registry.get("nonexistent_opening_xyz") is None

    def test_get_fallback(self) -> None:
        registry = OpeningRegistry(TEMPLATES_DIR)
        fallback = registry.get_fallback()
        assert fallback is not None
        assert fallback.id == "warm_intro"
        assert fallback.is_fallback is True

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Registry handles empty templates directory gracefully."""
        registry = OpeningRegistry(tmp_path)
        assert len(registry) == 0
        assert registry.get_fallback() is None

    def test_all_templates_have_required_fields(self) -> None:
        """Every template must have id, name, first_message, system_prompt_addendum."""
        registry = OpeningRegistry(TEMPLATES_DIR)
        for opening in registry.get_all():
            assert opening.id, f"Opening missing id"
            assert opening.name, f"Opening {opening.id} missing name"
            assert opening.first_message, f"Opening {opening.id} missing first_message"
            assert opening.system_prompt_addendum, (
                f"Opening {opening.id} missing system_prompt_addendum"
            )

    def test_all_templates_have_format_placeholders(self) -> None:
        """Every first_message must contain {name} placeholder."""
        registry = OpeningRegistry(TEMPLATES_DIR)
        for opening in registry.get_all():
            assert "{name}" in opening.first_message, (
                f"Opening {opening.id} first_message missing {{name}} placeholder"
            )

    def test_all_templates_have_goals_and_forbidden(self) -> None:
        """Every template should have at least one goal and one forbidden rule."""
        registry = OpeningRegistry(TEMPLATES_DIR)
        for opening in registry.get_all():
            assert len(opening.goals) >= 1, (
                f"Opening {opening.id} has no goals"
            )
            assert len(opening.forbidden) >= 1, (
                f"Opening {opening.id} has no forbidden rules"
            )
