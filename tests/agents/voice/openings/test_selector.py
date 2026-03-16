"""Tests for OpeningSelector — profile-to-opening matching."""

from __future__ import annotations

from pathlib import Path

from nikita.agents.voice.openings.registry import OpeningRegistry
from nikita.agents.voice.openings.selector import OpeningSelector

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent.parent / (
    "nikita/agents/voice/openings/templates"
)


class TestOpeningSelector:
    """Selector matches user profile to best opening."""

    def _make_selector(self) -> OpeningSelector:
        registry = OpeningRegistry(TEMPLATES_DIR)
        return OpeningSelector(registry)

    def test_low_darkness_matches_warm_or_playful(self) -> None:
        """darkness=1 should match openings with low darkness ranges."""
        selector = self._make_selector()
        opening = selector.select(drug_tolerance=1)
        assert opening.darkness_range[0] <= 1 <= opening.darkness_range[1]

    def test_high_darkness_with_scene_matches_dark_openings(self) -> None:
        """darkness=5 + matching scene should select a dark opening."""
        selector = self._make_selector()
        # noir has scene_tags=["techno"], darkness_range=(4,5)
        opening = selector.select(drug_tolerance=5, scene="techno")
        assert opening.darkness_range[1] >= 5

    def test_high_darkness_no_scene_falls_back(self) -> None:
        """darkness=5 without scene falls back (dark openings require scene tags)."""
        selector = self._make_selector()
        opening = selector.select(drug_tolerance=5, scene=None)
        # Falls back to warm_intro since dark openings have scene_tags
        assert opening is not None

    def test_fallback_for_extreme_value(self) -> None:
        """Out-of-range darkness falls back to warm_intro."""
        selector = self._make_selector()
        opening = selector.select(drug_tolerance=99)
        assert opening.is_fallback or opening.id == "warm_intro"

    def test_scene_tag_filtering(self) -> None:
        """Opening with scene_tags should match when user has matching scene."""
        selector = self._make_selector()
        # darkness=3 + techno should potentially match "challenge" (techno tag)
        opening = selector.select(drug_tolerance=3, scene="techno")
        # Either matches challenge (has techno tag) or another matching opening
        assert opening.darkness_range[0] <= 3 <= opening.darkness_range[1]

    def test_no_scene_still_matches_openings_without_tags(self) -> None:
        """User without scene preference should still get an opening."""
        selector = self._make_selector()
        opening = selector.select(drug_tolerance=2, scene=None)
        assert opening is not None

    def test_selector_returns_opening_type(self) -> None:
        """select() always returns an Opening instance."""
        from nikita.agents.voice.openings.models import Opening

        selector = self._make_selector()
        result = selector.select(drug_tolerance=3)
        assert isinstance(result, Opening)

    def test_selector_never_raises_with_valid_templates(self) -> None:
        """With templates loaded, selector never raises for any reasonable input."""
        selector = self._make_selector()
        for dt in range(1, 6):
            for scene in [None, "techno", "art", "food", "nature", "cocktails"]:
                opening = selector.select(drug_tolerance=dt, scene=scene)
                assert opening is not None
