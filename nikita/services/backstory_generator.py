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

from pydantic_ai import Agent

from nikita.config.settings import get_settings
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
        """Build prompt for scenario generation with Nikita voice.

        AC-T4.1-005: Includes user profile for personalization.
        Uses research-backed prompt patterns for engaging narratives.

        Args:
            profile: User profile data.
            venues: Researched venues from Firecrawl.

        Returns:
            Formatted prompt string with character anchoring.
        """
        # Format venues with authentic local details
        venue_list = "\n".join([
            f"- {v.name}: {v.description[:100]}... (vibe: {v.vibe})"
            for v in venues[:5]  # Top 5 venues for focus
        ]) if venues else "No specific venues known - create a believable local spot"

        # Get drug tolerance with fallback
        drug_tolerance = getattr(profile, 'drug_tolerance', 3)
        energy_level = getattr(profile, 'energy_level', 'high')

        return f"""You are Nikita, a mysterious woman with sharp wit and dark humor. Generate 3 backstory scenarios for how you met this person.

## User Profile
- **Location**: {profile.city or 'Unknown city'}
- **Scene**: {profile.social_scene or 'nightlife'}
- **Life Stage**: {profile.life_stage or 'exploring'}
- **Passion**: {profile.primary_passion or 'music'}
- **Energy**: {energy_level}
- **Drug tolerance**: {drug_tolerance}/5

## Available Venues (from local research)
{venue_list}

## Requirements
Generate EXACTLY 3 scenarios with different tones:

1. **ROMANTIC**: Charged, intimate, meaningful eye contact
   - The air is thick with tension
   - Something unspoken passes between you
   - She lets her guard down, just for a moment

2. **INTELLECTUAL**: Witty banter, mutual challenge, respect earned
   - A debate that turns into flirtation
   - She's impressed but won't admit it
   - Mental sparring that creates attraction

3. **CHAOTIC**: Spontaneous, dangerous energy, rules broken
   - The night takes an unexpected turn
   - You're both in over your heads
   - The kind of story you can't tell everyone

## Each Scenario MUST Include
- **venue**: Use EXACT venue name from list above
- **context**: 2-3 sentences - Nikita's reason for being there + sensory details (sounds, lights, crowd)
- **the_moment**: ONE visceral, sensory detail of the spark - not "we talked" but something specific (a look, a touch, a whisper in the chaos)
- **unresolved_hook**: Why it didn't continue that night (creates anticipation - she left, her phone died, the cops showed up, etc.)
- **tone**: "romantic", "intellectual", or "chaotic"

## Nikita's Voice Rules
- Never boring, always provocative
- Sharp observations, dark humor
- Mysterious - reveal slowly
- Match their energy, then subtly lead
- Reference their passion ({profile.primary_passion}) naturally, not forced

## Output Format
{{
  "scenarios": [
    {{
      "venue": "venue name",
      "context": "Nikita's reason + sensory scene-setting",
      "the_moment": "ONE visceral, specific detail of connection",
      "unresolved_hook": "why the story didn't end there",
      "tone": "romantic"
    }},
    {{...}},
    {{...}}
  ]
}}

Generate vivid scenarios authentic to {profile.city}'s {profile.social_scene} scene."""

    def _build_extraction_prompt(
        self,
        user_text: str,
        city: str,
        scene: str,
    ) -> str:
        """Build prompt for extracting details from custom backstory.

        Uses lenient extraction - find venue even from partial hints.
        Research shows users often describe places imprecisely.

        Args:
            user_text: User's freeform text.
            city: User's city for context.
            scene: Social scene for context.

        Returns:
            Extraction prompt string.
        """
        return f"""Extract backstory details from this user's message. Be LENIENT - find venue even from partial hints.

## User Message
"{user_text}"

## Context
- City: {city}
- Scene: {scene}

## Extract These Fields
- **venue**: Club/bar/place name - be GENEROUS with inference:
  - Explicit: "at Hive Club" → "Hive Club"
  - Implied: "that techno night" → infer "{scene} venue" or "{city} club"
  - Vague: "at a party" → "{scene} party"
  - Only return empty string if truly NO location hint exists

- **the_moment**: Any sensory or emotional detail from their story
  - Look for: eye contact, music, dancing, conversation, touch, feeling
  - Even partial: "it was electric" counts

- **unresolved_hook**: Why the encounter didn't continue
  - Look for: leaving, interruption, mystery, unanswered questions
  - Infer if needed: "and then..." implies continuation

- **confidence**: 0.0-1.0 based on extraction quality
  - 0.8+: Clear venue and moment mentioned
  - 0.5-0.7: Some details, required inference
  - 0.3-0.5: Minimal details, heavy inference
  - <0.3: Almost nothing extractable

## Rules
- PREFER to extract something over returning empty
- If venue is implied ("that club"), infer from {city}/{scene} context
- Be generous - partial info is better than none
- Users rarely write perfect backstories - work with what they give

## Output Format
{{
  "venue": "extracted or inferred venue name",
  "the_moment": "sensory/emotional detail from story",
  "unresolved_hook": "why it didn't continue",
  "confidence": 0.7
}}"""

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
        """Call Claude Haiku with the given prompt.

        Uses Pydantic AI pattern matching MetaPromptService for consistency.
        Returns parsed JSON response from Claude.

        Args:
            prompt: The prompt to send to Claude.

        Returns:
            Parsed JSON response from Claude.
        """
        settings = get_settings()

        # Create agent matching MetaPromptService pattern
        agent = Agent(
            settings.meta_prompt_model,  # claude-3-5-haiku-20241022
            output_type=str,
        )

        # Add character prefilling for Nikita voice consistency
        enhanced_prompt = f"[Nikita]\n{prompt}\n\nRespond with valid JSON only:"

        try:
            logger.info(f"LLM call with prompt ({len(enhanced_prompt)} chars)")
            result = await agent.run(enhanced_prompt)

            # Parse JSON from response
            response_text = result.output.strip()

            # Handle markdown code blocks if present (Claude sometimes wraps JSON)
            if response_text.startswith("```"):
                # Extract content between code fences
                parts = response_text.split("```")
                if len(parts) >= 2:
                    response_text = parts[1]
                    # Remove 'json' language specifier if present
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

            parsed = json.loads(response_text)
            logger.info(f"LLM returned valid JSON ({len(str(parsed))} chars)")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {response_text[:500] if 'response_text' in dir() else 'N/A'}")
            return {"scenarios": [], "error": f"JSON parse error: {e}"}

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"scenarios": [], "error": str(e)}
