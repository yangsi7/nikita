"""Tests for Nikita persona meta-instruction framework - TDD for T1.1.

Acceptance Criteria (updated Spec 060 P2):
- AC-1.1.1: Persona establishes behavioral identity (backstory in template)
- AC-1.1.2: Communication style rules defined
- AC-1.1.3: Texting style rules defined
- AC-1.1.4: Response guidelines defined
- AC-1.1.5: Anti-patterns section (what Nikita never does)
- AC-1.1.6: At least 10 example responses
- AC-1.1.7: Meta-instructions for personalization based on user context
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


class TestPersonalizationMetaInstructions:
    """Tests for personalization meta-instructions in NIKITA_PERSONA.

    AC-1.1.7: persona.py must contain meta-instructions that teach the model
    HOW to adapt behavior based on dynamic user context, not hardcoded identity.
    """

    def test_meta_instructions_section_exists(self):
        """Meta-instructions section present in persona."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        assert "META-INSTRUCTIONS" in NIKITA_PERSONA or "PERSONALIZATION" in NIKITA_PERSONA

    def test_occupation_adaptation_rules(self):
        """Meta-instructions include occupation-based adaptation."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        lower = NIKITA_PERSONA.lower()
        # Must teach model to adapt based on user's work
        assert "occupation" in lower or "work" in lower or "tech" in lower
        assert "creative" in lower or "craft" in lower

    def test_communication_mirroring_rules(self):
        """Meta-instructions include communication pattern mirroring."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        lower = NIKITA_PERSONA.lower()
        # Must teach model to mirror message patterns
        assert "mirror" in lower or "match" in lower
        assert "message length" in lower or "energy" in lower

    def test_knowledge_usage_rules(self):
        """Meta-instructions teach how to USE accumulated knowledge."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        lower = NIKITA_PERSONA.lower()
        # Must warn against robotic fact recitation
        assert "database" in lower or "recite" in lower
        # Must teach natural weaving of knowledge
        assert "weave" in lower or "natural" in lower

    def test_trust_level_adaptation(self):
        """Meta-instructions adapt behavior based on relationship depth."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        lower = NIKITA_PERSONA.lower()
        # Must have rules for different trust levels
        assert "trust" in lower or "vulnerability" in lower
        # Must reference early vs deep relationship stages
        assert "early" in lower
        assert "shared" in lower or "history" in lower

    def test_no_hardcoded_identity(self):
        """Meta-instructions must NOT contain hardcoded identity details."""
        from nikita.agents.text.persona import NIKITA_PERSONA

        # These belong in system_prompt.j2, not persona.py
        assert "Berlin" not in NIKITA_PERSONA
        assert "Prenzlauer" not in NIKITA_PERSONA
        assert "Russian" not in NIKITA_PERSONA
        assert "Volkov" not in NIKITA_PERSONA
        assert "MIT" not in NIKITA_PERSONA
        assert "Brooklyn" not in NIKITA_PERSONA
        assert "Schrödinger" not in NIKITA_PERSONA


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
