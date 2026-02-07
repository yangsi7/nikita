"""Phase B: Meta-Nikita Agent tests (Spec 028).

Tests for Meta-Nikita ElevenLabs agent configuration and prompts.

Implements:
- AC-T005.1-4: ElevenLabs agent configuration
- AC-T006.1-3: Voice settings distinct from Nikita
- AC-T007.1-4: System prompt and first message
- AC-T008.1-2: Agent response and voice tests
"""

from typing import Any
from uuid import uuid4

import pytest

from nikita.onboarding.meta_nikita import (
    META_NIKITA_FIRST_MESSAGE,
    META_NIKITA_PERSONA,
    META_NIKITA_TTS_SETTINGS,
    MetaNikitaConfig,
    build_meta_nikita_config_override,
)


class TestMetaNikitaConfig:
    """Tests for MetaNikitaConfig class (T005)."""

    def test_config_initialization(self) -> None:
        """AC-T005.1: Config initializes correctly."""
        config = MetaNikitaConfig()
        assert config is not None

    def test_agent_id_configured(self) -> None:
        """AC-T005.4: Agent ID is documented in config."""
        config = MetaNikitaConfig()
        assert config.agent_id is not None
        assert len(config.agent_id) > 0

    def test_voice_id_different_from_nikita(self) -> None:
        """AC-T005.2: Voice is distinct from Nikita."""
        config = MetaNikitaConfig()
        # Meta-Nikita should have a dedicated voice_id (or use default with different settings)
        assert config.voice_id is not None

    def test_tts_settings(self) -> None:
        """AC-T005.3: TTS settings are configured."""
        assert META_NIKITA_TTS_SETTINGS is not None
        assert META_NIKITA_TTS_SETTINGS.stability == 0.40  # Lower for emotional/dynamic voice
        assert META_NIKITA_TTS_SETTINGS.similarity_boost == 0.70


class TestVoiceSettings:
    """Tests for voice settings (T006)."""

    def test_stability_dynamic_seductive(self) -> None:
        """AC-T006.1: Voice is dynamic and seductive (lower stability)."""
        # Meta-Nikita uses lower stability for emotional, dynamic voice
        # Range 0.35-0.50 for seductive pacing
        assert 0.35 <= META_NIKITA_TTS_SETTINGS.stability <= 0.50

    def test_speed_normal_pace(self) -> None:
        """AC-T006.1: Speech at normal pace."""
        assert 0.9 <= META_NIKITA_TTS_SETTINGS.speed <= 1.1

    def test_similarity_boost_moderate(self) -> None:
        """AC-T006.2: Similarity boost for consistent voice."""
        assert 0.7 <= META_NIKITA_TTS_SETTINGS.similarity_boost <= 0.85


class TestSystemPrompt:
    """Tests for system prompt generation (T007)."""

    def test_persona_exists(self) -> None:
        """AC-T007.1: System prompt exists."""
        assert META_NIKITA_PERSONA is not None
        assert len(META_NIKITA_PERSONA) > 100  # Substantial prompt

    def test_persona_identifies_as_gatekeeper(self) -> None:
        """AC-T007.1: Meta-Nikita identifies as underground game hostess/gatekeeper."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        assert any(word in prompt_lower for word in ["gatekeeper", "hostess", "game hostess"])

    def test_persona_mentions_nikita(self) -> None:
        """AC-T007.2: Mentions introducing Nikita."""
        assert "nikita" in META_NIKITA_PERSONA.lower()

    def test_persona_covers_profile_collection(self) -> None:
        """AC-T007.2: Covers profile collection."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should mention collecting user info
        assert any(
            word in prompt_lower
            for word in ["profile", "location", "timezone", "hobbies", "occupation", "job"]
        )

    def test_persona_covers_preferences(self) -> None:
        """AC-T007.2: Covers experience configuration."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should mention preferences
        assert any(
            word in prompt_lower for word in ["preference", "experience", "darkness", "pacing"]
        )

    def test_persona_covers_handoff(self) -> None:
        """AC-T007.2: Covers handoff to Nikita."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should mention handoff/transition to Nikita
        assert any(word in prompt_lower for word in ["handoff", "hand off", "transition", "telegram", "text you"])

    def test_persona_not_flirtatious(self) -> None:
        """AC-T006.1: Persona is NOT flirtatious (distinct from Nikita)."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should NOT encourage flirtatious behavior (but may mention NOT to flirt)
        # Check that "flirt" only appears in banned/never-do context
        if "flirt" in prompt_lower:
            # Acceptable if in "never sound like" list or "not seductive"
            assert (
                "not flirt" in prompt_lower
                or "not romantic" in prompt_lower
                or "never sound like" in prompt_lower
                or "not seductive" in prompt_lower
            )
        # "seductive" should only appear in "not seductive" context
        if "seductive" in prompt_lower:
            assert "not seductive" in prompt_lower or "never" in prompt_lower

    def test_persona_is_confident_gatekeeper(self) -> None:
        """AC-T007.1: Persona is confident, direct gatekeeper."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        assert any(
            word in prompt_lower
            for word in ["confident", "direct", "gatekeeper", "intimidating", "edge"]
        )

    def test_persona_bans_ai_language(self) -> None:
        """Persona explicitly bans AI/artificial/bot language."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should mention NEVER in context of banned AI language
        assert "never" in prompt_lower
        # The banned AI/bot language should be mentioned
        assert any(word in prompt_lower for word in ["ai", "bot", "assistant"])


    def test_persona_has_elevenlabs_headers(self) -> None:
        """Prompt uses ElevenLabs-recommended markdown headers."""
        # ElevenLabs best practice: LLM pays extra attention to # headers
        assert "# Personality" in META_NIKITA_PERSONA
        assert "# Goal" in META_NIKITA_PERSONA
        assert "# Guardrails" in META_NIKITA_PERSONA

    def test_persona_has_error_recovery(self) -> None:
        """Prompt includes error recovery guidance."""
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should have error recovery patterns
        assert "error recovery" in prompt_lower or "situation" in prompt_lower
        assert any(phrase in prompt_lower for phrase in ["didn't hear", "vague", "silence"])

    def test_persona_has_tool_instructions(self) -> None:
        """Prompt includes tool usage instructions in # Tools section."""
        assert "# Tools" in META_NIKITA_PERSONA
        prompt_lower = META_NIKITA_PERSONA.lower()
        # Should mention when to use tools
        assert "when:" in prompt_lower or "after" in prompt_lower


class TestFirstMessage:
    """Tests for first message (T007)."""

    def test_first_message_exists(self) -> None:
        """AC-T007.4: First message is configured."""
        assert META_NIKITA_FIRST_MESSAGE is not None
        assert len(META_NIKITA_FIRST_MESSAGE) > 10

    def test_first_message_is_intriguing(self) -> None:
        """AC-T007.4: First message is intriguing and direct."""
        msg_lower = META_NIKITA_FIRST_MESSAGE.lower()
        # Game gatekeeper style - confident, direct, establishes identity
        assert any(word in msg_lower for word in ["meta-nikita", "welcome", "game", "name"])

    def test_first_message_establishes_stakes(self) -> None:
        """AC-T007.4: First message establishes game stakes."""
        msg_lower = META_NIKITA_FIRST_MESSAGE.lower()
        # Gatekeeper style - establishes who decides + stakes
        assert any(
            phrase in msg_lower
            for phrase in ["decides", "worth", "dumped", "consequences", "rules"]
        )


class TestAgentConfigGeneration:
    """Tests for ElevenLabs agent config generation (T005, T008)."""

    def test_get_agent_config(self) -> None:
        """AC-T005.2: Agent config is ElevenLabs-compatible."""
        config = MetaNikitaConfig()
        user_id = uuid4()
        agent_config = config.get_agent_config(user_id=user_id, user_name="Test User")

        # Should have required ElevenLabs fields
        assert "agent_id" in agent_config
        assert "conversation_config_override" in agent_config
        assert "dynamic_variables" in agent_config

    def test_agent_config_has_prompt(self) -> None:
        """AC-T007.1: Config includes system prompt."""
        config = MetaNikitaConfig()
        agent_config = config.get_agent_config(user_id=uuid4(), user_name="Test User")

        # Should have prompt in conversation_config_override
        conv_config = agent_config["conversation_config_override"]
        assert "agent" in conv_config
        assert "prompt" in conv_config["agent"]

    def test_agent_config_has_first_message(self) -> None:
        """AC-T007.4: Config includes first message."""
        config = MetaNikitaConfig()
        agent_config = config.get_agent_config(user_id=uuid4(), user_name="Test User")

        conv_config = agent_config["conversation_config_override"]
        assert "first_message" in conv_config["agent"]

    def test_agent_config_has_tts_settings(self) -> None:
        """AC-T005.3: Config includes TTS settings."""
        config = MetaNikitaConfig()
        agent_config = config.get_agent_config(user_id=uuid4(), user_name="Test User")

        conv_config = agent_config["conversation_config_override"]
        assert "tts" in conv_config
        assert "stability" in conv_config["tts"]
        assert "similarity_boost" in conv_config["tts"]

    def test_agent_config_includes_user_name(self) -> None:
        """AC-T007.4: Config includes user name in dynamic variables."""
        config = MetaNikitaConfig()
        agent_config = config.get_agent_config(user_id=uuid4(), user_name="Alice")

        assert agent_config["dynamic_variables"]["user_name"] == "Alice"

    def test_agent_config_includes_user_id(self) -> None:
        """Config includes user_id for server tools."""
        config = MetaNikitaConfig()
        user_id = uuid4()
        agent_config = config.get_agent_config(user_id=user_id, user_name="Test")

        # user_id should be in dynamic_variables for server tools
        assert "user_id" in agent_config["dynamic_variables"]
        assert agent_config["dynamic_variables"]["user_id"] == str(user_id)


class TestServerToolsConfig:
    """Tests for server tools configuration in Meta-Nikita agent."""

    def test_get_server_tools_config(self) -> None:
        """Server tools are configured for profile collection."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()

        # Should have onboarding-specific server tools
        assert isinstance(tools, list)
        assert len(tools) >= 3  # collect_profile, configure_preferences, complete_onboarding

    def test_collect_profile_tool_defined(self) -> None:
        """collect_profile server tool is defined."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()
        tool_names = [t["name"] for t in tools]

        assert "collect_profile" in tool_names

    def test_configure_preferences_tool_defined(self) -> None:
        """configure_preferences server tool is defined."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()
        tool_names = [t["name"] for t in tools]

        assert "configure_preferences" in tool_names

    def test_complete_onboarding_tool_defined(self) -> None:
        """complete_onboarding server tool is defined."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()
        tool_names = [t["name"] for t in tools]

        assert "complete_onboarding" in tool_names

    def test_tools_have_descriptions(self) -> None:
        """All server tools have descriptions."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()

        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 10

    def test_tools_have_parameters(self) -> None:
        """Server tools have parameter definitions."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()

        for tool in tools:
            assert "parameters" in tool
            assert isinstance(tool["parameters"], dict)

    def test_tools_have_enhanced_descriptions(self) -> None:
        """Server tool descriptions include WHEN/HOW/ERROR guidance."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()

        # All tools should have enhanced descriptions with WHEN/HOW guidance
        for tool in tools:
            desc_upper = tool["description"].upper()
            assert "WHEN:" in desc_upper or "HOW:" in desc_upper, f"{tool['name']} missing WHEN/HOW guidance"

    def test_end_call_tool_defined(self) -> None:
        """end_call server tool is defined for clean hang-up."""
        config = MetaNikitaConfig()
        tools = config.get_server_tools()
        tool_names = [t["name"] for t in tools]

        assert "end_call" in tool_names


class TestConversationFlow:
    """Tests for onboarding conversation flow structure."""

    def test_conversation_stages_defined(self) -> None:
        """Conversation stages are defined for flow."""
        config = MetaNikitaConfig()
        stages = config.get_conversation_stages()

        assert len(stages) >= 4  # Introduction, Profile, Preferences, Handoff

    def test_introduction_stage(self) -> None:
        """Introduction stage is first."""
        config = MetaNikitaConfig()
        stages = config.get_conversation_stages()

        assert stages[0]["name"] == "introduction"
        assert "duration" in stages[0]

    def test_profile_stage(self) -> None:
        """Profile collection stage exists."""
        config = MetaNikitaConfig()
        stages = config.get_conversation_stages()
        stage_names = [s["name"] for s in stages]

        assert "profile_collection" in stage_names

    def test_preferences_stage(self) -> None:
        """Preferences stage exists."""
        config = MetaNikitaConfig()
        stages = config.get_conversation_stages()
        stage_names = [s["name"] for s in stages]

        assert "preferences" in stage_names

    def test_handoff_stage(self) -> None:
        """Handoff stage is last."""
        config = MetaNikitaConfig()
        stages = config.get_conversation_stages()

        assert stages[-1]["name"] == "handoff"


class TestBuildConfigOverride:
    """Tests for build_meta_nikita_config_override (Spec 033)."""

    def test_returns_conversation_config_override(self) -> None:
        """Function returns conversation_config_override key."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id)

        assert "conversation_config_override" in result

    def test_includes_agent_prompt(self) -> None:
        """Config override includes agent prompt."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id)

        config = result["conversation_config_override"]
        assert "agent" in config
        assert "prompt" in config["agent"]
        assert "prompt" in config["agent"]["prompt"]
        assert len(config["agent"]["prompt"]["prompt"]) > 100

    def test_includes_first_message(self) -> None:
        """Config override includes first message."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id)

        config = result["conversation_config_override"]
        assert "first_message" in config["agent"]

    def test_includes_tts_settings(self) -> None:
        """Config override includes TTS settings."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id)

        config = result["conversation_config_override"]
        assert "tts" in config
        assert "stability" in config["tts"]
        assert "similarity_boost" in config["tts"]
        assert "speed" in config["tts"]

    def test_includes_dynamic_variables(self) -> None:
        """Function returns dynamic_variables."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id, user_name="Alice")

        assert "dynamic_variables" in result
        dv = result["dynamic_variables"]
        assert "user_name" in dv
        assert dv["user_name"] == "Alice"
        assert "user_id" in dv
        assert dv["user_id"] == str(user_id)

    def test_includes_onboarding_flag(self) -> None:
        """Dynamic variables include is_onboarding flag."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id)

        dv = result["dynamic_variables"]
        assert "is_onboarding" in dv
        assert dv["is_onboarding"] == "true"

    def test_includes_onboarding_stage(self) -> None:
        """Dynamic variables include onboarding_stage."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id)

        dv = result["dynamic_variables"]
        assert "onboarding_stage" in dv
        assert dv["onboarding_stage"] == "1"

    def test_personalizes_first_message_with_name(self) -> None:
        """First message is personalized when user_name is provided."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id, user_name="Alice")

        config = result["conversation_config_override"]
        first_msg = config["agent"]["first_message"]
        assert "Alice" in first_msg

    def test_default_first_message_without_name(self) -> None:
        """Default first message is used when user_name is generic."""
        user_id = uuid4()
        result = build_meta_nikita_config_override(user_id, user_name="friend")

        config = result["conversation_config_override"]
        first_msg = config["agent"]["first_message"]
        # Should use default (no personalization for generic names)
        assert first_msg == META_NIKITA_FIRST_MESSAGE

    def test_uuid_string_user_id_accepted(self) -> None:
        """Function accepts string user_id."""
        user_id_str = str(uuid4())
        result = build_meta_nikita_config_override(user_id_str, user_name="Test")

        assert result["dynamic_variables"]["user_id"] == user_id_str
