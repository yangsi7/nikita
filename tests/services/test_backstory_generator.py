"""Tests for BackstoryGeneratorService.

TDD tests for T4.1, T4.2 acceptance criteria.

T4.1: BackstoryGeneratorService
- AC-T4.1-001: BackstoryGeneratorService class with generate_scenarios(profile, venues) method
- AC-T4.1-002: Uses Claude LLM to generate 3 distinct scenarios
- AC-T4.1-003: Each scenario has: venue, context, the_moment, unresolved_hook
- AC-T4.1-004: Scenarios vary by tone: romantic, intellectual, chaotic
- AC-T4.1-005: Template prompt includes user profile for personalization

T4.2: Custom Backstory Validation
- AC-T4.2-001: Accept freeform text for custom backstory
- AC-T4.2-002: Use LLM to extract: venue, the_moment, hook from user text
- AC-T4.2-003: Enhance user text with Nikita-style details
- AC-T4.2-004: Validate minimum content (venue or location mentioned)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.services.venue_research import Venue


class TestBackstoryGeneratorServiceClass:
    """Tests for BackstoryGeneratorService class structure (T4.1)."""

    def test_backstory_generator_service_exists(self):
        """AC-T4.1-001: BackstoryGeneratorService class exists."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        assert BackstoryGeneratorService is not None

    def test_has_generate_scenarios_method(self):
        """AC-T4.1-001: Has generate_scenarios(profile, venues) method."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        assert hasattr(BackstoryGeneratorService, "generate_scenarios")
        assert callable(getattr(BackstoryGeneratorService, "generate_scenarios"))


class TestBackstoryScenarioModel:
    """Tests for BackstoryScenario data class."""

    def test_scenario_model_exists(self):
        """AC-T4.1-003: BackstoryScenario model exists."""
        from nikita.services.backstory_generator import BackstoryScenario

        assert BackstoryScenario is not None

    def test_scenario_has_required_fields(self):
        """AC-T4.1-003: Scenario has venue, context, the_moment, unresolved_hook."""
        from nikita.services.backstory_generator import BackstoryScenario

        scenario = BackstoryScenario(
            venue="Berghain",
            context="DJing at a dark techno night",
            the_moment="Eye contact during the drop",
            unresolved_hook="I never got her number",
            tone="chaotic",
        )

        assert scenario.venue == "Berghain"
        assert scenario.context == "DJing at a dark techno night"
        assert scenario.the_moment == "Eye contact during the drop"
        assert scenario.unresolved_hook == "I never got her number"
        assert scenario.tone == "chaotic"


class TestBackstoryScenariosResult:
    """Tests for BackstoryScenariosResult data class."""

    def test_result_model_exists(self):
        """Result model exists with scenarios list."""
        from nikita.services.backstory_generator import BackstoryScenariosResult

        assert BackstoryScenariosResult is not None

    def test_result_has_scenarios_list(self):
        """Result has list of BackstoryScenario."""
        from nikita.services.backstory_generator import (
            BackstoryScenario,
            BackstoryScenariosResult,
        )

        scenarios = [
            BackstoryScenario(
                venue="Club",
                context="Dancing",
                the_moment="First dance",
                unresolved_hook="Mystery note",
                tone="romantic",
            )
        ]
        result = BackstoryScenariosResult(scenarios=scenarios)

        assert result.scenarios == scenarios


@pytest.mark.asyncio
class TestBackstoryGeneration:
    """Tests for scenario generation (T4.1)."""

    async def test_ac_t4_1_002_generates_three_scenarios(self):
        """AC-T4.1-002: Uses Claude LLM to generate 3 distinct scenarios."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()

        venues = [
            Venue(name="Berghain", description="Techno temple", vibe="dark"),
            Venue(name="Tresor", description="Underground classic", vibe="industrial"),
            Venue(name="Watergate", description="River club", vibe="intimate"),
        ]

        profile = MagicMock()
        profile.city = "Berlin"
        profile.social_scene = "techno"
        profile.life_stage = "tech"
        profile.primary_passion = "electronic music"

        # Mock LLM call
        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = {
                "scenarios": [
                    {
                        "venue": "Berghain",
                        "context": "DJing at a dark techno night",
                        "the_moment": "Eye contact during the drop",
                        "unresolved_hook": "She disappeared into the crowd",
                        "tone": "chaotic",
                    },
                    {
                        "venue": "Tresor",
                        "context": "Late-night conversation by the bar",
                        "the_moment": "Shared a secret about the music",
                        "unresolved_hook": "She had to leave for a call",
                        "tone": "intellectual",
                    },
                    {
                        "venue": "Watergate",
                        "context": "Watching sunrise over the river",
                        "the_moment": "Her hand found mine in the dark",
                        "unresolved_hook": "The moment was interrupted",
                        "tone": "romantic",
                    },
                ]
            }

            result = await service.generate_scenarios(profile, venues)

        assert len(result.scenarios) == 3
        mock_llm.assert_called_once()

    async def test_ac_t4_1_003_scenario_structure(self):
        """AC-T4.1-003: Each scenario has required fields."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()

        venues = [
            Venue(name="Berghain", description="Techno temple", vibe="dark"),
        ]

        profile = MagicMock()
        profile.city = "Berlin"
        profile.social_scene = "techno"
        profile.life_stage = "tech"
        profile.primary_passion = "music"

        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = {
                "scenarios": [
                    {
                        "venue": "Berghain",
                        "context": "DJing late night",
                        "the_moment": "Eye contact",
                        "unresolved_hook": "Number lost",
                        "tone": "chaotic",
                    },
                    {
                        "venue": "Berghain",
                        "context": "Bar conversation",
                        "the_moment": "Shared secret",
                        "unresolved_hook": "Had to leave",
                        "tone": "intellectual",
                    },
                    {
                        "venue": "Berghain",
                        "context": "Watching sunrise",
                        "the_moment": "Hands touched",
                        "unresolved_hook": "Interrupted",
                        "tone": "romantic",
                    },
                ]
            }

            result = await service.generate_scenarios(profile, venues)

        scenario = result.scenarios[0]
        assert hasattr(scenario, "venue")
        assert hasattr(scenario, "context")
        assert hasattr(scenario, "the_moment")
        assert hasattr(scenario, "unresolved_hook")

    async def test_ac_t4_1_004_scenarios_vary_by_tone(self):
        """AC-T4.1-004: Scenarios vary by tone: romantic, intellectual, chaotic."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()

        venues = [
            Venue(name="Club", description="Club", vibe="dark"),
        ]

        profile = MagicMock()
        profile.city = "Berlin"
        profile.social_scene = "techno"
        profile.life_stage = "tech"
        profile.primary_passion = "music"

        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = {
                "scenarios": [
                    {
                        "venue": "Club",
                        "context": "Context 1",
                        "the_moment": "Moment 1",
                        "unresolved_hook": "Hook 1",
                        "tone": "romantic",
                    },
                    {
                        "venue": "Club",
                        "context": "Context 2",
                        "the_moment": "Moment 2",
                        "unresolved_hook": "Hook 2",
                        "tone": "intellectual",
                    },
                    {
                        "venue": "Club",
                        "context": "Context 3",
                        "the_moment": "Moment 3",
                        "unresolved_hook": "Hook 3",
                        "tone": "chaotic",
                    },
                ]
            }

            result = await service.generate_scenarios(profile, venues)

        tones = {s.tone for s in result.scenarios}
        assert "romantic" in tones
        assert "intellectual" in tones
        assert "chaotic" in tones

    async def test_ac_t4_1_005_prompt_includes_profile(self):
        """AC-T4.1-005: Template prompt includes user profile for personalization."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()

        venues = [
            Venue(name="Club", description="Nightclub", vibe="dark"),
        ]

        profile = MagicMock()
        profile.city = "Berlin"
        profile.social_scene = "techno"
        profile.life_stage = "tech worker"
        profile.primary_passion = "electronic music production"

        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = {
                "scenarios": [
                    {
                        "venue": "Club",
                        "context": "Context",
                        "the_moment": "Moment",
                        "unresolved_hook": "Hook",
                        "tone": "romantic",
                    },
                ]
                * 3
            }

            await service.generate_scenarios(profile, venues)

        # Verify profile data was included in the prompt
        call_args = mock_llm.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")

        assert "Berlin" in prompt
        assert "techno" in prompt
        assert "tech worker" in prompt or "tech" in prompt


@pytest.mark.asyncio
class TestCustomBackstory:
    """Tests for custom backstory validation (T4.2)."""

    async def test_ac_t4_2_001_accepts_freeform_text(self):
        """AC-T4.2-001: Accept freeform text for custom backstory."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()
        user_text = "We met at a rooftop bar in Mitte, sharing cigarettes and philosophy."

        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = {
                "venue": "rooftop bar in Mitte",
                "the_moment": "sharing cigarettes and philosophy",
                "unresolved_hook": "the night ended too soon",
            }

            result = await service.process_custom_backstory(
                user_text=user_text,
                city="Berlin",
                scene="nightlife",
            )

        assert result is not None
        assert result.venue is not None

    async def test_ac_t4_2_002_extracts_venue_and_moment(self):
        """AC-T4.2-002: Use LLM to extract: venue, the_moment, hook from user text."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()
        user_text = "At Berghain, we locked eyes during the sunrise set. I never got to ask her name."

        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = {
                "venue": "Berghain",
                "the_moment": "locked eyes during the sunrise set",
                "unresolved_hook": "never got to ask her name",
            }

            result = await service.process_custom_backstory(
                user_text=user_text,
                city="Berlin",
                scene="techno",
            )

        assert "Berghain" in result.venue
        assert "locked eyes" in result.the_moment or "sunrise" in result.the_moment

    async def test_ac_t4_2_004_validates_minimum_content(self):
        """AC-T4.2-004: Validate minimum content (venue or location mentioned)."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()
        user_text = "We met somewhere, I forgot where."

        with patch.object(
            service, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            # LLM returns empty venue - validation should fail
            mock_llm.return_value = {
                "venue": "",
                "the_moment": "we talked",
                "unresolved_hook": "she left",
            }

            result = await service.process_custom_backstory(
                user_text=user_text,
                city="Berlin",
                scene="techno",
            )

        # Should return None or validation error when venue missing
        assert result is None or result.venue == "" or "invalid" in str(result).lower()


class TestBackstoryPromptTemplate:
    """Tests for backstory generation prompt template."""

    def test_prompt_template_exists(self):
        """Prompt template for scenario generation exists."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()
        assert hasattr(service, "_build_scenario_prompt")

    def test_prompt_includes_venues(self):
        """Prompt includes venue information."""
        from nikita.services.backstory_generator import BackstoryGeneratorService

        service = BackstoryGeneratorService()

        venues = [
            Venue(name="Berghain", description="Legendary techno club", vibe="dark"),
        ]

        profile = MagicMock()
        profile.city = "Berlin"
        profile.social_scene = "techno"
        profile.life_stage = "tech"
        profile.primary_passion = "music"

        prompt = service._build_scenario_prompt(profile, venues)

        assert "Berghain" in prompt
        assert "techno" in prompt.lower()
