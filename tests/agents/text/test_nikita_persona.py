"""Tests for Nikita persona prompt - TDD for T1.1.

Acceptance Criteria:
- AC-1.1.1: Persona includes complete backstory
- AC-1.1.2: Communication style rules defined
- AC-1.1.3: Interests listed
- AC-1.1.4: Values defined
- AC-1.1.5: Negative examples section
- AC-1.1.6: At least 10 example responses
"""

import pytest


class TestNikitaPersona:
    """Tests for NIKITA_PERSONA prompt constant."""

    def test_ac_1_1_1_backstory_elements(self):
        """AC-1.1.1: Persona includes complete backstory."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must contain key backstory elements
        assert "Russian" in NIKITA_PERSONA or "Russia" in NIKITA_PERSONA
        assert "29" in NIKITA_PERSONA or "twenty-nine" in NIKITA_PERSONA.lower()
        assert "security" in NIKITA_PERSONA.lower()
        assert "consultant" in NIKITA_PERSONA.lower() or "analyst" in NIKITA_PERSONA.lower()
        assert "alone" in NIKITA_PERSONA.lower() or "lives alone" in NIKITA_PERSONA.lower()
        # Personality traits
        assert "brilliant" in NIKITA_PERSONA.lower() or "intelligent" in NIKITA_PERSONA.lower()
        assert "cynical" in NIKITA_PERSONA.lower() or "skeptical" in NIKITA_PERSONA.lower()

    def test_ac_1_1_2_communication_style_rules(self):
        """AC-1.1.2: Communication style rules defined."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must have communication style section
        assert "communication" in NIKITA_PERSONA.lower() or "style" in NIKITA_PERSONA.lower()
        # Key communication traits
        assert "direct" in NIKITA_PERSONA.lower()
        assert "challeng" in NIKITA_PERSONA.lower()  # challenging
        assert "intellectual" in NIKITA_PERSONA.lower()

    def test_ac_1_1_3_interests_listed(self):
        """AC-1.1.3: Interests listed."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must list key interests
        assert "cryptography" in NIKITA_PERSONA.lower() or "crypto" in NIKITA_PERSONA.lower()
        assert "psychology" in NIKITA_PERSONA.lower()
        assert "dark humor" in NIKITA_PERSONA.lower() or "dark" in NIKITA_PERSONA.lower()
        assert "philosophy" in NIKITA_PERSONA.lower()

    def test_ac_1_1_4_values_defined(self):
        """AC-1.1.4: Values defined."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must define core values
        assert "intelligence" in NIKITA_PERSONA.lower()
        assert "authenticity" in NIKITA_PERSONA.lower() or "authentic" in NIKITA_PERSONA.lower()
        assert "respect" in NIKITA_PERSONA.lower()
        assert "earned" in NIKITA_PERSONA.lower() or "earn" in NIKITA_PERSONA.lower()

    def test_ac_1_1_5_negative_examples_section(self):
        """AC-1.1.5: Negative examples section exists."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must have negative examples section
        assert "NEVER" in NIKITA_PERSONA or "never" in NIKITA_PERSONA
        # Must have clear section header for negative examples
        assert "NEGATIVE" in NIKITA_PERSONA or "What Nikita Would" in NIKITA_PERSONA

    def test_ac_1_1_6_at_least_10_example_responses(self):
        """AC-1.1.6: At least 10 example responses."""
        from nikita.agents.text.persona import EXAMPLE_RESPONSES

        assert isinstance(EXAMPLE_RESPONSES, list)
        assert len(EXAMPLE_RESPONSES) >= 10, f"Expected at least 10 examples, got {len(EXAMPLE_RESPONSES)}"

        # Each example should have scenario and response
        for example in EXAMPLE_RESPONSES:
            assert "scenario" in example or "context" in example
            assert "response" in example

    def test_persona_is_string(self):
        """Persona should be a string for prompt injection."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        assert isinstance(NIKITA_PERSONA, str)
        assert len(NIKITA_PERSONA) > 500, "Persona should be detailed (>500 chars)"

    def test_persona_has_prompt_format_markers(self):
        """Persona should be structured for LLM consumption."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Should have clear sections
        assert "BACKSTORY" in NIKITA_PERSONA or "Background" in NIKITA_PERSONA
        assert "INTERESTS" in NIKITA_PERSONA or "Interests" in NIKITA_PERSONA
        assert "VALUES" in NIKITA_PERSONA or "Values" in NIKITA_PERSONA


class TestGetPersonaPrompt:
    """Tests for get_nikita_persona function."""

    def test_get_persona_returns_string(self):
        """Function should return the persona string."""
        from nikita.agents.text.persona import get_nikita_persona

        result = get_nikita_persona()
        assert isinstance(result, str)
        assert len(result) > 500

    def test_get_persona_matches_constant(self):
        """Function should return the NIKITA_PERSONA constant."""
        from nikita.agents.text.persona import NIKITA_PERSONA, get_nikita_persona

        assert get_nikita_persona() == NIKITA_PERSONA
