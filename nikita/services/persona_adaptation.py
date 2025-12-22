"""Persona adaptation service for Nikita customization.

Part of 017-enhanced-onboarding feature.
Maps user profile to Nikita persona overrides.

T5.4: Persona Adaptation Logic
- AC-T5.4-001: Map life_stage to Nikita occupation
- AC-T5.4-002: Map social_scene to Nikita interests
- AC-T5.4-003: Map drug_tolerance to vice_profile intensity
"""

from typing import Any


class PersonaAdaptationService:
    """Service for adapting Nikita's persona based on user profile.

    AC-T5.4: Generates persona_overrides dict for UserBackstory.

    The persona overrides customize Nikita's character to match the user's
    world - her job, hobbies, and edge level adapt to feel authentic.
    """

    # AC-T5.4-001: Life stage to occupation mapping
    LIFE_STAGE_OCCUPATIONS: dict[str, str] = {
        "tech": "cybersecurity consultant",
        "artist": "digital artist and security researcher",
        "finance": "fintech security analyst",
        "student": "security researcher (grad student)",
        "entrepreneur": "startup security advisor",
        "creative": "digital artist and security researcher",
        "professional": "cybersecurity consultant",
        "other": "cybersecurity consultant",
    }

    # AC-T5.4-002: Social scene to hobby/interests mapping
    SCENE_HOBBIES: dict[str, str] = {
        "techno": "underground DJ",
        "art": "gallery hopping",
        "fine_dining": "restaurant hopping",
        "nightlife": "club culture explorer",
        "music": "live music hunting",
        "cocktails": "speakeasy hunting",
        "outdoor": "urban exploration",
        "gaming": "competitive gaming",
        "fitness": "underground boxing",
    }

    SCENE_INTERESTS: dict[str, str] = {
        "techno": "electronic music",
        "art": "contemporary art",
        "fine_dining": "food and wine",
        "nightlife": "nightlife",
        "music": "live music",
        "cocktails": "mixology",
        "outdoor": "urban exploration",
        "gaming": "gaming culture",
        "fitness": "fitness and martial arts",
    }

    # AC-T5.4-003: Drug tolerance to edge level mapping
    TOLERANCE_EDGE_LEVELS: dict[int, str] = {
        1: "subtle",      # No explicit substance references
        2: "light",       # Occasional alcohol mentions
        3: "moderate",    # Natural party references
        4: "bold",        # Open about substances
        5: "explicit",    # Full embrace of party culture
    }

    TOLERANCE_SUBSTANCE_REFS: dict[int, str] = {
        1: "avoid",           # Never mention substances
        2: "minimal",         # Rare alcohol references
        3: "casual",          # Normal party mentions
        4: "open",            # Direct substance references
        5: "embrace",         # Full party culture embrace
    }

    def generate_persona_overrides(
        self,
        life_stage: str,
        social_scene: str,
        drug_tolerance: int,
    ) -> dict[str, Any]:
        """Generate persona overrides based on user profile.

        Args:
            life_stage: User's life stage (tech, artist, finance, etc.)
            social_scene: User's social scene (techno, art, fine_dining, etc.)
            drug_tolerance: User's drug tolerance 1-5.

        Returns:
            Dict with persona overrides:
            - occupation: Nikita's job title
            - hobby: Nikita's main hobby
            - interests: Nikita's interests string
            - vice_intensity: 1-5 intensity level
            - edge_level: subtle/light/moderate/bold/explicit
            - substance_references: avoid/minimal/casual/open/embrace
        """
        # Normalize inputs
        life_stage_norm = life_stage.lower() if life_stage else "other"
        scene_norm = social_scene.lower() if social_scene else "nightlife"
        tolerance = max(1, min(5, drug_tolerance if drug_tolerance else 3))

        # AC-T5.4-001: Map life_stage to occupation
        occupation = self.LIFE_STAGE_OCCUPATIONS.get(
            life_stage_norm,
            self.LIFE_STAGE_OCCUPATIONS["other"],
        )

        # AC-T5.4-002: Map social_scene to hobby and interests
        hobby = self.SCENE_HOBBIES.get(
            scene_norm,
            self.SCENE_HOBBIES["nightlife"],
        )
        interests = self.SCENE_INTERESTS.get(
            scene_norm,
            self.SCENE_INTERESTS["nightlife"],
        )

        # AC-T5.4-003: Map drug_tolerance to edge level
        edge_level = self.TOLERANCE_EDGE_LEVELS.get(tolerance, "moderate")
        substance_refs = self.TOLERANCE_SUBSTANCE_REFS.get(tolerance, "casual")

        return {
            "occupation": occupation,
            "hobby": hobby,
            "interests": interests,
            "vice_intensity": tolerance,
            "edge_level": edge_level,
            "substance_references": substance_refs,
        }

    def format_for_prompt(self, overrides: dict[str, Any]) -> str:
        """Format persona overrides for system prompt inclusion.

        Args:
            overrides: Dict from generate_persona_overrides().

        Returns:
            Formatted string for system prompt.
        """
        if not overrides:
            return ""

        lines = [
            f"- Occupation: {overrides.get('occupation', 'cybersecurity consultant')}",
            f"- Hobby: {overrides.get('hobby', 'club culture explorer')}",
            f"- Interests: {overrides.get('interests', 'nightlife')}",
            f"- Edge Level: {overrides.get('edge_level', 'moderate')}",
            f"- Substance References: {overrides.get('substance_references', 'casual')}",
        ]
        return "\n".join(lines)
