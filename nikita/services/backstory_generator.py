"""Backstory generation service using Claude LLM.

Part of 017-enhanced-onboarding feature.
Generates "how we met" scenarios for Nikita relationship initialization.

T4.1: BackstoryGeneratorService
T4.2: Custom backstory validation
"""

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from nikita.services.venue_research import Venue

if TYPE_CHECKING:
    from nikita.db.models.profile import UserProfile

logger = logging.getLogger(__name__)


@dataclass
class BackstoryScenario:
    """A generated "how we met" scenario.

    AC-T4.1-003: Each scenario has venue, context, the_moment, unresolved_hook.
    AC-T4.1-004: Includes tone for variety.
    """

    venue: str
    context: str  # Nikita's reason for being there
    the_moment: str  # The spark that connected them
    unresolved_hook: str  # Why the story didn't end there
    tone: str  # romantic, intellectual, or chaotic


@dataclass
class BackstoryScenariosResult:
    """Result of scenario generation.

    Contains 3 generated scenarios for user selection.
    """

    scenarios: list[BackstoryScenario] = field(default_factory=list)


@dataclass
class CustomBackstoryResult:
    """Result of processing custom user backstory.

    AC-T4.2-002: Extracted fields from user text.
    """

    venue: str
    context: str
    the_moment: str
    unresolved_hook: str
    enhanced_text: str | None = None  # Nikita-style version


class BackstoryGeneratorService:
    """Service for generating backstory scenarios using Claude LLM.

    AC-T4.1-001: BackstoryGeneratorService class with generate_scenarios method
    AC-T4.1-002: Uses Claude LLM to generate 3 distinct scenarios
    AC-T4.1-005: Template prompt includes user profile for personalization
    """

    # Required tones for variety (AC-T4.1-004)
    TONES = ["romantic", "intellectual", "chaotic"]

    def __init__(self):
        """Initialize BackstoryGeneratorService."""
        pass  # LLM client will be injected or created on demand

    async def generate_scenarios(
        self,
        profile: "UserProfile",
        venues: list[Venue],
    ) -> BackstoryScenariosResult:
        """Generate 3 distinct backstory scenarios.

        AC-T4.1-001: Main generation method.
        AC-T4.1-002: Uses Claude LLM.
        AC-T4.1-004: Scenarios vary by tone.

        Args:
            profile: User's profile with city, social_scene, life_stage, etc.
            venues: List of researched venues for the user's city/scene.

        Returns:
            BackstoryScenariosResult with 3 scenarios.
        """
        prompt = self._build_scenario_prompt(profile, venues)

        try:
            llm_response = await self._call_llm(prompt)
            scenarios = self._parse_scenarios_response(llm_response)
            return BackstoryScenariosResult(scenarios=scenarios)

        except Exception as e:
            logger.error(f"Failed to generate scenarios: {e}")
            # Return fallback generic scenarios
            return self._create_fallback_scenarios(profile, venues)

    async def process_custom_backstory(
        self,
        user_text: str,
        city: str,
        scene: str,
    ) -> CustomBackstoryResult | None:
        """Process user-provided custom backstory text.

        AC-T4.2-001: Accept freeform text.
        AC-T4.2-002: Extract venue, the_moment, hook.
        AC-T4.2-004: Validate minimum content.

        Args:
            user_text: User's freeform backstory text.
            city: User's city for context.
            scene: Social scene for context.

        Returns:
            CustomBackstoryResult if valid, None if validation fails.
        """
        prompt = self._build_extraction_prompt(user_text, city, scene)

        try:
            llm_response = await self._call_llm(prompt)
            result = self._parse_extraction_response(llm_response)

            # AC-T4.2-004: Validate minimum content
            if not result or not result.venue:
                logger.warning(
                    f"Custom backstory validation failed: no venue in '{user_text[:50]}...'"
                )
                return None

            return result

        except Exception as e:
            logger.error(f"Failed to process custom backstory: {e}")
            return None

    def _build_scenario_prompt(
        self,
        profile: "UserProfile",
        venues: list[Venue],
    ) -> str:
        """Build prompt for scenario generation.

        AC-T4.1-005: Includes user profile for personalization.

        Args:
            profile: User profile data.
            venues: Researched venues.

        Returns:
            Formatted prompt string.
        """
        venue_list = "\n".join([
            f"- {v.name}: {v.description} (vibe: {v.vibe})"
            for v in venues
        ]) if venues else "No specific venues known"

        return f"""Generate 3 distinct "how we met" scenarios for a dating simulation game.

USER PROFILE:
- City: {profile.city}
- Social Scene: {profile.social_scene}
- Life Stage: {profile.life_stage}
- Primary Passion: {profile.primary_passion}

AVAILABLE VENUES:
{venue_list}

CHARACTER: Nikita is a mysterious, playful woman with dark humor and a sharp wit.
She's sophisticated but has an edge - comfortable in underground clubs and high-end bars alike.

REQUIREMENTS:
1. Generate exactly 3 scenarios with DIFFERENT tones:
   - Scenario 1: ROMANTIC - tender, charged, emotionally intimate
   - Scenario 2: INTELLECTUAL - witty banter, shared interests, mental connection
   - Scenario 3: CHAOTIC - wild, unpredictable, memorable for the chaos

2. Each scenario must include:
   - venue: Where they met (use a venue from the list if available)
   - context: Why Nikita was there (her reason, not the user's)
   - the_moment: The specific moment of connection
   - unresolved_hook: Why the story didn't end there (creates tension for game)

3. Make scenarios feel authentic to {profile.city}'s {profile.social_scene} scene.
4. Reference the user's passion ({profile.primary_passion}) subtly.

OUTPUT FORMAT (JSON):
{{
  "scenarios": [
    {{
      "venue": "venue name",
      "context": "Nikita's reason for being there",
      "the_moment": "the spark that connected them",
      "unresolved_hook": "why the story didn't end there",
      "tone": "romantic"
    }},
    ...
  ]
}}

Generate creative, vivid scenarios that set up an intriguing relationship start."""

    def _build_extraction_prompt(
        self,
        user_text: str,
        city: str,
        scene: str,
    ) -> str:
        """Build prompt for extracting fields from custom backstory.

        Args:
            user_text: User's freeform text.
            city: User's city.
            scene: Social scene.

        Returns:
            Extraction prompt string.
        """
        return f"""Extract structured information from this custom "how we met" story.

USER'S STORY:
"{user_text}"

CONTEXT:
- City: {city}
- Scene: {scene}

Extract the following fields. If a field is not explicitly mentioned, infer something reasonable:

OUTPUT FORMAT (JSON):
{{
  "venue": "the place where they met (extract or infer from text)",
  "the_moment": "the spark or memorable moment (extract from text)",
  "unresolved_hook": "why the encounter didn't continue (infer if needed)"
}}

If no venue or location is mentioned at all, return an empty string for venue.

Extract the most interesting details from the user's story."""

    def _parse_scenarios_response(
        self,
        llm_response: dict[str, Any],
    ) -> list[BackstoryScenario]:
        """Parse LLM response into BackstoryScenario objects.

        Args:
            llm_response: Raw LLM response dict.

        Returns:
            List of BackstoryScenario objects.
        """
        scenarios = []

        raw_scenarios = llm_response.get("scenarios", [])
        for raw in raw_scenarios:
            scenario = BackstoryScenario(
                venue=raw.get("venue", ""),
                context=raw.get("context", ""),
                the_moment=raw.get("the_moment", ""),
                unresolved_hook=raw.get("unresolved_hook", ""),
                tone=raw.get("tone", "romantic"),
            )
            scenarios.append(scenario)

        return scenarios

    def _parse_extraction_response(
        self,
        llm_response: dict[str, Any],
    ) -> CustomBackstoryResult | None:
        """Parse LLM extraction response.

        Args:
            llm_response: Raw LLM response dict.

        Returns:
            CustomBackstoryResult or None if parsing fails.
        """
        venue = llm_response.get("venue", "")
        the_moment = llm_response.get("the_moment", "")
        unresolved_hook = llm_response.get("unresolved_hook", "")

        return CustomBackstoryResult(
            venue=venue,
            context="",  # Custom backstories don't have explicit context
            the_moment=the_moment,
            unresolved_hook=unresolved_hook,
        )

    def _create_fallback_scenarios(
        self,
        profile: "UserProfile",
        venues: list[Venue],
    ) -> BackstoryScenariosResult:
        """Create fallback generic scenarios if LLM fails.

        Args:
            profile: User profile.
            venues: Available venues.

        Returns:
            BackstoryScenariosResult with generic scenarios.
        """
        venue_name = venues[0].name if venues else f"a spot in {profile.city}"

        scenarios = [
            BackstoryScenario(
                venue=venue_name,
                context="She was there for the music",
                the_moment="Our eyes met across the room",
                unresolved_hook="The crowd pulled us apart",
                tone="romantic",
            ),
            BackstoryScenario(
                venue=venue_name,
                context="She was debating someone at the bar",
                the_moment="I couldn't resist joining the argument",
                unresolved_hook="Her phone rang and she had to leave",
                tone="intellectual",
            ),
            BackstoryScenario(
                venue=venue_name,
                context="She caused a scene with the bouncer",
                the_moment="I helped her sneak back in",
                unresolved_hook="The night got too wild to remember clearly",
                tone="chaotic",
            ),
        ]

        return BackstoryScenariosResult(scenarios=scenarios)

    async def _call_llm(self, prompt: str) -> dict[str, Any]:
        """Call Claude LLM with the given prompt.

        This method is designed to be mocked in tests.
        In production, it will call the actual Claude API.

        Args:
            prompt: The prompt to send to Claude.

        Returns:
            Parsed JSON response from Claude.
        """
        # TODO: Integrate with actual Claude API
        # For now, this placeholder will be mocked in tests
        # Production implementation will use:
        # from anthropic import AsyncAnthropic
        # client = AsyncAnthropic()
        # response = await client.messages.create(...)

        logger.info(f"LLM call with prompt ({len(prompt)} chars)")

        # Placeholder - actual implementation will parse Claude response
        return {"scenarios": []}
