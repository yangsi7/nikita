"""Tests for PersonaAdaptationService.

T5.4: Persona Adaptation Logic
Tests the mapping from user profile to Nikita persona overrides.
"""

import pytest

from nikita.services.persona_adaptation import PersonaAdaptationService


class TestPersonaAdaptationService:
    """Test suite for PersonaAdaptationService."""

    @pytest.fixture
    def service(self) -> PersonaAdaptationService:
        """Create PersonaAdaptationService instance."""
        return PersonaAdaptationService()

    # =========================================================================
    # T5.4 AC-T5.4-001: Map life_stage to Nikita occupation
    # =========================================================================

    def test_map_life_stage_tech_to_hacker(self, service: PersonaAdaptationService) -> None:
        """AC-T5.4-001: tech life_stage maps to hacker occupation."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=3,
        )
        assert result["occupation"] == "cybersecurity consultant"

    def test_map_life_stage_artist_to_digital_artist(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-001: artist life_stage maps to digital artist."""
        result = service.generate_persona_overrides(
            life_stage="artist",
            social_scene="art",
            drug_tolerance=3,
        )
        assert result["occupation"] == "digital artist and security researcher"

    def test_map_life_stage_finance_to_fintech(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-001: finance life_stage maps to fintech security."""
        result = service.generate_persona_overrides(
            life_stage="finance",
            social_scene="nightlife",
            drug_tolerance=3,
        )
        assert result["occupation"] == "fintech security analyst"

    def test_map_life_stage_student_to_researcher(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-001: student life_stage maps to security researcher."""
        result = service.generate_persona_overrides(
            life_stage="student",
            social_scene="nightlife",
            drug_tolerance=3,
        )
        assert result["occupation"] == "security researcher (grad student)"

    def test_map_life_stage_unknown_to_default(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-001: unknown life_stage gets default occupation."""
        result = service.generate_persona_overrides(
            life_stage="random_value",
            social_scene="nightlife",
            drug_tolerance=3,
        )
        assert result["occupation"] == "cybersecurity consultant"

    # =========================================================================
    # T5.4 AC-T5.4-002: Map social_scene to Nikita interests
    # =========================================================================

    def test_map_scene_techno_to_dj_hobby(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-002: techno scene maps to DJ hobby."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="techno",
            drug_tolerance=3,
        )
        assert result["hobby"] == "underground DJ"
        assert "electronic music" in result["interests"]

    def test_map_scene_art_to_gallery_hopper(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-002: art scene maps to gallery hopping."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="art",
            drug_tolerance=3,
        )
        assert result["hobby"] == "gallery hopping"
        assert "contemporary art" in result["interests"]

    def test_map_scene_dining_to_foodie(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-002: fine_dining scene maps to foodie hobby."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="fine_dining",
            drug_tolerance=3,
        )
        assert result["hobby"] == "restaurant hopping"
        assert "food and wine" in result["interests"]

    def test_map_scene_nightlife_to_club_culture(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-002: nightlife scene maps to club culture."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=3,
        )
        assert result["hobby"] == "club culture explorer"
        assert "nightlife" in result["interests"]

    def test_map_scene_unknown_to_default(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-002: unknown scene gets default interests."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="random_scene",
            drug_tolerance=3,
        )
        assert "hobby" in result  # Has some default hobby
        assert "interests" in result  # Has some interests

    # =========================================================================
    # T5.4 AC-T5.4-003: Map drug_tolerance to vice_profile intensity
    # =========================================================================

    def test_drug_tolerance_1_maps_to_low_intensity(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-003: drug_tolerance=1 maps to low vice intensity."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=1,
        )
        assert result["vice_intensity"] == 1
        assert result["edge_level"] == "subtle"

    def test_drug_tolerance_3_maps_to_moderate_intensity(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-003: drug_tolerance=3 maps to moderate vice intensity."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=3,
        )
        assert result["vice_intensity"] == 3
        assert result["edge_level"] == "moderate"

    def test_drug_tolerance_5_maps_to_high_intensity(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-003: drug_tolerance=5 maps to high vice intensity."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=5,
        )
        assert result["vice_intensity"] == 5
        assert result["edge_level"] == "explicit"

    def test_drug_tolerance_affects_substance_references(
        self, service: PersonaAdaptationService
    ) -> None:
        """AC-T5.4-003: drug_tolerance affects substance_references level."""
        low = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=1,
        )
        high = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="nightlife",
            drug_tolerance=5,
        )
        assert low["substance_references"] == "avoid"
        assert high["substance_references"] == "embrace"

    # =========================================================================
    # T5.4 Additional Tests: Combined Scenarios
    # =========================================================================

    def test_complete_persona_override_structure(
        self, service: PersonaAdaptationService
    ) -> None:
        """Test that persona overrides have all required fields."""
        result = service.generate_persona_overrides(
            life_stage="tech",
            social_scene="techno",
            drug_tolerance=4,
        )

        # All required fields present
        assert "occupation" in result
        assert "hobby" in result
        assert "interests" in result
        assert "vice_intensity" in result
        assert "edge_level" in result
        assert "substance_references" in result

    def test_artist_in_art_scene_full_mapping(
        self, service: PersonaAdaptationService
    ) -> None:
        """Test artist + art scene creates coherent persona."""
        result = service.generate_persona_overrides(
            life_stage="artist",
            social_scene="art",
            drug_tolerance=4,
        )

        # Artist in art scene = fully art-focused persona
        assert "artist" in result["occupation"].lower() or "art" in result["occupation"].lower()
        assert "gallery" in result["hobby"].lower() or "art" in result["hobby"].lower()
        assert any("art" in i.lower() for i in [result["interests"]])

    def test_student_in_techno_scene_full_mapping(
        self, service: PersonaAdaptationService
    ) -> None:
        """Test student + techno scene creates coherent persona."""
        result = service.generate_persona_overrides(
            life_stage="student",
            social_scene="techno",
            drug_tolerance=3,
        )

        # Student = researcher, techno = DJ hobby
        assert "student" in result["occupation"].lower() or "research" in result["occupation"].lower()
        assert "dj" in result["hobby"].lower()
