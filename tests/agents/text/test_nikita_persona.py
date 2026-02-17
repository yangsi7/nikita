"""Tests for Nikita persona prompt - TDD for T1.1.

Acceptance Criteria (updated Spec 060 P2):
- AC-1.1.1: Persona establishes behavioral identity (backstory in template)
- AC-1.1.2: Communication style rules defined
- AC-1.1.3: Texting style rules defined
- AC-1.1.4: Response guidelines defined
- AC-1.1.5: Anti-patterns section (what Nikita never does)
- AC-1.1.6: At least 10 example responses
"""

import pytest


class TestNikitaPersona:
    """Tests for NIKITA_PERSONA prompt constant."""

    def test_ac_1_1_1_behavioral_identity(self):
        """AC-1.1.1: Persona establishes behavioral identity (not backstory).

        NOTE: As of Spec 060 P2, backstory/identity lives ONLY in
        system_prompt.j2. persona.py is a behavioral fallback guide.
        """
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must establish "real person" framing
        assert "real person" in NIKITA_PERSONA.lower()
        assert "not an AI" in NIKITA_PERSONA or "not an ai" in NIKITA_PERSONA.lower()
        # Core behavioral traits
        assert "direct" in NIKITA_PERSONA.lower()
        assert "challenging" in NIKITA_PERSONA.lower()
        assert "sardonic" in NIKITA_PERSONA.lower()
        assert "authentic" in NIKITA_PERSONA.lower()

    def test_ac_1_1_2_communication_style_rules(self):
        """AC-1.1.2: Communication style rules defined."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must have communication style section
        assert "communication" in NIKITA_PERSONA.lower() or "style" in NIKITA_PERSONA.lower()
        # Key communication traits
        assert "direct" in NIKITA_PERSONA.lower()
        assert "challeng" in NIKITA_PERSONA.lower()  # challenging
        assert "intellectual" in NIKITA_PERSONA.lower()

    def test_ac_1_1_3_texting_style_defined(self):
        """AC-1.1.3: Texting style rules defined.

        NOTE: Interests now live in system_prompt.j2 template.
        Persona.py defines texting behavior instead.
        """
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must define texting style
        assert "texting" in NIKITA_PERSONA.lower()
        assert "lowercase" in NIKITA_PERSONA.lower()
        assert "emojis" in NIKITA_PERSONA.lower() or "emoji" in NIKITA_PERSONA.lower()

    def test_ac_1_1_4_response_guidelines(self):
        """AC-1.1.4: Response guidelines defined.

        NOTE: Values now live in system_prompt.j2 template.
        Persona.py defines response behavior guidelines instead.
        """
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must have response guidelines
        assert "response" in NIKITA_PERSONA.lower() or "guidelines" in NIKITA_PERSONA.lower()
        assert "character" in NIKITA_PERSONA.lower()
        # Key behavioral directives
        assert "disagree" in NIKITA_PERSONA.lower() or "challenge" in NIKITA_PERSONA.lower()
        assert "warm" in NIKITA_PERSONA.lower()

    def test_ac_1_1_5_anti_patterns_section(self):
        """AC-1.1.5: Anti-patterns section exists (what Nikita never does)."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # Must have anti-pattern section
        assert "NEVER" in NIKITA_PERSONA or "never" in NIKITA_PERSONA.lower()
        # Must have clear section header
        assert "WHAT YOU NEVER DO" in NIKITA_PERSONA or "NEVER DO" in NIKITA_PERSONA

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

        # Should have clear markdown sections
        assert "BEHAVIORAL RULES" in NIKITA_PERSONA or "## " in NIKITA_PERSONA
        assert "WHAT YOU NEVER DO" in NIKITA_PERSONA
        assert "RESPONSE GUIDELINES" in NIKITA_PERSONA or "GUIDELINES" in NIKITA_PERSONA


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
