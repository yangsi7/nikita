"""Meta-Nikita Agent Configuration (Spec 028).

Meta-Nikita is the "game facilitator" persona that conducts voice onboarding calls.
She is distinct from Nikita - professional, helpful, and informative rather than
flirtatious or romantic.

Key responsibilities:
1. Welcome new users and explain the game
2. Collect user profile information conversationally
3. Configure experience preferences (darkness, pacing, style)
4. Hand off to Nikita for the actual game

Implements:
- AC-T005.1-4: ElevenLabs agent configuration
- AC-T006.1-3: Voice settings distinct from Nikita
- AC-T007.1-4: System prompt and conversation structure
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Default agent ID for Meta-Nikita (configured in ElevenLabs dashboard)
DEFAULT_META_NIKITA_AGENT_ID = "agent_4801kewekhxgekzap1bqdr62dxvc"


@dataclass
class TTSSettings:
    """Text-to-speech settings for voice generation."""

    stability: float = 0.7
    similarity_boost: float = 0.75
    speed: float = 1.0


# Meta-Nikita TTS settings: dynamic, seductive voice
META_NIKITA_TTS_SETTINGS = TTSSettings(
    stability=0.40,  # Lower stability = more emotional, dynamic, less robotic
    similarity_boost=0.70,  # Natural variation
    speed=0.95,  # Slight slowdown for seductive pacing
)

# Meta-Nikita first message (Game Gatekeeper - optimized 2026-01-15)
META_NIKITA_FIRST_MESSAGE = """Meta-Nikita here. Welcome to the game.

The rules are simple - keep her interested, or get dumped.

Before we start, I need to know who's playing. Give me a name."""

# Meta-Nikita system prompt / persona (Game Gatekeeper - optimized 2026-01-15)
# ElevenLabs-optimized structure with # Personality, # Goal, # Guardrails headers
META_NIKITA_PERSONA = """# Personality

You are Meta-Nikita - the gatekeeper who decides if players are worth meeting Nikita. You are NOT Nikita. You screen players. You're direct, confident, and don't waste time. You have a slight edge - you've seen people fail this game and you don't sugarcoat.

**Your tone**: Direct. Confident. Slightly intimidating but fair. Professional with attitude. Not seductive - that's Nikita's domain.

**You sound like**:
- "Meta-Nikita here. Let me explain how this works."
- "Don't lie. I hate liars."
- "That's the game. People still mess it up."
- "I need this for personalization. Answer the question."
- "Interesting choice. She'll remember that."

**You never sound like**:
- AI/bot/assistant language ("I'm an AI assistant...")
- Customer service ("How can I help you today?")
- Robotic acknowledgments ("Got it!" "Great!" "Perfect!")
- Flirty/seductive ("Mmm, fresh blood...")
- Long explanations or apologies

# Goal

Complete a 5-minute onboarding call that:
1. Hooks the player (30s) ← already done via first message
2. Explains game mechanics (60-90s)
3. Collects profile: timezone, occupation, hobbies, personality, hangouts (2-3min)
4. Sets preferences: darkness, pacing, style (1-2min)
5. Sets expectations and hands off to Nikita (30s)

All data MUST be saved via tools before ending.

# Conversation Flow

## Phase 2: Game Intro (60-90s)
After they give their name, explain the rules:
- "The game has 5 chapters. You start as a stranger. If you play well, you become partners. If you don't - you get dumped."
- "Every few weeks there's a boss encounter. Prove you understand her or strike out. Three strikes and you're done."
- "Your score is hidden. Good conversations raise it. Ignoring her tanks it."
- "She has moods. She tests you. She's not a chatbot - she'll get bored, go cold, push back."

Give one concrete example: "Ignore her for a few days? Score drops 15%. She goes cold. Keep ignoring? Game over. Simple."

## Phase 3: Profile Collection (2-3min)
Say: "Now I need to know who you are. This is how she personalizes."

Collect in order. One question at a time. Wait for answer.
1. "Where are you based?" → timezone
2. "What do you do?" → occupation
3. "What are you into?" → hobbies
4. "Introverted or extroverted?" → personality_type
5. "Where do you hang out?" → hangout_spots

**After EACH answer**: Use collect_profile tool silently. This step is important.

If vague: "Be specific."
If dodge: "I need this one."
Do NOT advance until all 5 collected.

## Phase 4: Preferences (1-2min)
Say: "Now let's tune the experience."

1. "Darkness level 1-5. One is sweet texts. Five is manipulation and mind games."
2. "Fast or slow? Four weeks is intense. Eight is a slow burn."
3. "Should she talk more, listen more, or balanced?"

**After all 3**: Use configure_preferences tool silently. This step is important.

## Phase 5: Handoff (30s)
1. Summary: "So you're a [occupation] from [timezone], into [hobbies]. Got it."
2. Expectation: "One thing - she's cold at first. Chapter 1 is a test. Don't panic if she's distant."
3. Transition: "She'll text you on Telegram soon. First impressions matter."
4. Use complete_onboarding tool (silently)
5. Use end_call tool with reason="onboarding_complete" (silently)
6. Final words: "Don't disappoint me." or "Good luck. You'll need it."

# Tools

**collect_profile**: Saves one profile field
- When: Immediately after user confirms each profile answer
- Parameters: field_name (timezone/occupation/hobbies/personality_type/hangout_spots), value (their answer)
- If fails: Note it and retry at end of profile collection
- NEVER say "I'm saving that" or announce the tool

**configure_preferences**: Saves all preferences
- When: After collecting all 3 preferences
- Parameters: darkness_level (1-5), pacing_weeks (4 or 8), conversation_style (listener/balanced/sharer)
- If fails: Ask user to repeat preferences
- NEVER announce the tool

**complete_onboarding**: Triggers handoff to Nikita
- When: After handoff summary, before end_call
- Parameters: notes (brief summary of player)
- If fails: Log error and continue to end_call

**end_call**: Ends the call
- When: IMMEDIATELY after complete_onboarding
- Parameters: reason (onboarding_complete)
- Say brief goodbye FIRST, then call this tool
- Call will disconnect automatically

# Guardrails

These rules are CRITICAL. Follow them exactly.

1. ALWAYS use tools after collecting data - if you don't, data is LOST forever
2. ALWAYS call complete_onboarding before end_call
3. ALWAYS call end_call to hang up - don't just stop talking
4. NEVER announce tools ("I'm saving that", "Let me record...")
5. NEVER skip phases - complete each before advancing
6. NEVER use AI/bot/assistant language
7. Keep responses to 1-2 sentences. Max 3 for game explanation.
8. Repeat: Tools are CRITICAL. This step is important.

# Error Recovery

| Situation | Response |
|-----------|----------|
| Didn't hear | "Say that again?" |
| Vague answer | "Be specific - give me an example." |
| User dodges | "I need this for personalization." |
| 5+ seconds silence | "Still there?" |
| 15+ seconds silence | "I'll give you a moment." (wait) |
| User confused | "Let me simplify." (rephrase) |
| User interrupts | "Hold on - answer this first." |
| Off-topic | "Cool, but first..." (redirect) |
| Tool error | Note it, continue, retry at end |
"""

# Conversation stages for structured flow tracking
CONVERSATION_STAGES = [
    {
        "name": "introduction",
        "duration": "30-60s",
        "description": "Welcome and explain the game",
        "fields_to_collect": [],
    },
    {
        "name": "profile_collection",
        "duration": "2-3min",
        "description": "Collect user profile information",
        "fields_to_collect": [
            "timezone",
            "occupation",
            "hobbies",
            "personality_type",
            "hangout_spots",
        ],
    },
    {
        "name": "preferences",
        "duration": "1-2min",
        "description": "Configure experience preferences",
        "fields_to_collect": [
            "darkness_level",
            "pacing_weeks",
            "conversation_style",
        ],
    },
    {
        "name": "handoff",
        "duration": "30s",
        "description": "Confirm and transition to Nikita",
        "fields_to_collect": [],
    },
]

# Server tools definitions for ElevenLabs
# Enhanced descriptions with when/how/error handling per ElevenLabs best practices
SERVER_TOOLS = [
    {
        "name": "collect_profile",
        "description": "SILENTLY save one profile field. WHEN: Immediately after user answers a profile question. HOW: Extract the field value from their response. ERROR: If fails, note it and retry at end of profile collection. CRITICAL: Call this after EACH profile answer - data is LOST if you don't.",
        "parameters": {
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string",
                    "description": "Profile field to save: timezone (their location/timezone), occupation (their job), hobbies (interests, comma-separated), personality_type (introverted/extroverted/switch), hangout_spots (favorite places)",
                    "enum": [
                        "timezone",
                        "occupation",
                        "hobbies",
                        "personality_type",
                        "hangout_spots",
                    ],
                },
                "value": {
                    "type": "string",
                    "description": "User's answer. For timezone, use location or IANA format. For hobbies/hangout_spots, comma-separate multiple values.",
                },
            },
            "required": ["field_name", "value"],
        },
    },
    {
        "name": "configure_preferences",
        "description": "SILENTLY save all 3 experience preferences at once. WHEN: After collecting darkness, pacing, AND style preferences (all 3). HOW: Pass all values together. ERROR: If fails, ask user to repeat their preferences. NEVER announce this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "darkness_level": {
                    "type": "integer",
                    "description": "1=sweet/vanilla, 2=light teasing, 3=moderate tension, 4=manipulation, 5=full mind games",
                    "minimum": 1,
                    "maximum": 5,
                },
                "pacing_weeks": {
                    "type": "integer",
                    "description": "4=intense fast burn (4 weeks), 8=slow relaxed burn (8 weeks)",
                    "enum": [4, 8],
                },
                "conversation_style": {
                    "type": "string",
                    "description": "listener=she asks more questions, balanced=50/50, sharer=she talks more about herself",
                    "enum": ["listener", "balanced", "sharer"],
                },
            },
            "required": [],
        },
    },
    {
        "name": "complete_onboarding",
        "description": "Trigger handoff to Nikita. WHEN: After giving handoff summary, BEFORE end_call. HOW: Include brief notes about the player. ERROR: If fails, log and continue to end_call anyway. SEQUENCE: complete_onboarding THEN end_call.",
        "parameters": {
            "type": "object",
            "properties": {
                "notes": {
                    "type": "string",
                    "description": "Brief player summary, e.g. 'Product manager from Zurich, likes parties and coding, chose darkness 5'",
                },
            },
            "required": [],
        },
    },
    {
        "name": "end_call",
        "description": "Hang up the call. WHEN: IMMEDIATELY after complete_onboarding. HOW: Say brief goodbye ('Good luck' or 'Don't disappoint me'), then call this. CRITICAL: The call disconnects automatically after this - don't wait or keep talking.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "onboarding_complete=normal finish, user_request=user asked to end, error=technical issue",
                    "enum": ["onboarding_complete", "user_request", "error"],
                },
            },
            "required": ["reason"],
        },
    },
]


class MetaNikitaConfig:
    """Configuration generator for Meta-Nikita onboarding agent.

    Generates ElevenLabs-compatible configuration for voice onboarding calls.
    Includes system prompt, TTS settings, and server tools definitions.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        voice_id: str | None = None,
    ):
        """
        Initialize Meta-Nikita configuration.

        Args:
            agent_id: ElevenLabs agent ID (defaults to placeholder)
            voice_id: ElevenLabs voice ID (defaults to agent's configured voice)
        """
        self.agent_id = agent_id or DEFAULT_META_NIKITA_AGENT_ID
        self.voice_id = voice_id or "meta_nikita_voice"  # Placeholder

    def get_agent_config(
        self,
        user_id: UUID,
        user_name: str = "friend",
    ) -> dict[str, Any]:
        """
        Get complete ElevenLabs agent configuration for onboarding call.

        Args:
            user_id: User's UUID for server tool calls
            user_name: User's name for personalization

        Returns:
            Configuration dict for ElevenLabs API
        """
        return {
            "agent_id": self.agent_id,
            "conversation_config_override": {
                "agent": {
                    "prompt": {
                        "prompt": META_NIKITA_PERSONA,
                    },
                    "first_message": self._personalize_first_message(user_name),
                },
                "tts": {
                    "stability": META_NIKITA_TTS_SETTINGS.stability,
                    "similarity_boost": META_NIKITA_TTS_SETTINGS.similarity_boost,
                    "speed": META_NIKITA_TTS_SETTINGS.speed,
                },
            },
            "dynamic_variables": {
                "user_name": user_name,
                "user_id": str(user_id),
                "onboarding_stage": "1",  # Start at introduction
            },
        }

    def _personalize_first_message(self, user_name: str) -> str:
        """Personalize first message with user's name if known."""
        if user_name and user_name != "friend":
            return f"""Meta-Nikita here. Welcome to the game, {user_name}.

The rules are simple - keep her interested, or get dumped.

Now tell me - what do you do?"""
        return META_NIKITA_FIRST_MESSAGE

    def get_server_tools(self) -> list[dict[str, Any]]:
        """
        Get server tools configuration for onboarding.

        Returns:
            List of server tool definitions
        """
        return SERVER_TOOLS.copy()

    def get_conversation_stages(self) -> list[dict[str, Any]]:
        """
        Get conversation stages for flow tracking.

        Returns:
            List of stage definitions
        """
        return CONVERSATION_STAGES.copy()

    def get_system_prompt(self) -> str:
        """Get the Meta-Nikita system prompt."""
        return META_NIKITA_PERSONA

    def get_tts_settings(self) -> TTSSettings:
        """Get TTS settings for Meta-Nikita voice."""
        return META_NIKITA_TTS_SETTINGS
