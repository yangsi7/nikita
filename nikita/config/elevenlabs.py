"""ElevenLabs agent configuration with abstraction for dynamic agent switching."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ElevenLabsConfig(BaseSettings):
    """ElevenLabs configuration with agent ID mapping."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ELEVENLABS_",
        case_sensitive=False,
        extra="ignore",
    )

    api_key: str = Field(..., description="ElevenLabs API key")

    # Default agent ID (provided by user)
    default_agent_id: str = Field(
        default="PB6BdkFkZLbI39GHdnbQ",
        description="Default ElevenLabs agent ID",
    )

    # Agent IDs per chapter/mood - all start with default, customize as needed
    agent_chapter_1_curious: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_chapter_2_playful: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_chapter_3_vulnerable: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_chapter_4_intimate: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_chapter_5_secure: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_boss_fight: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_angry: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_sad: str = Field(default="PB6BdkFkZLbI39GHdnbQ")
    agent_flirty: str = Field(default="PB6BdkFkZLbI39GHdnbQ")

    def get_agents_dict(self) -> dict[str, str]:
        """Get all agent IDs as a dictionary."""
        return {
            "default": self.default_agent_id,
            "chapter_1_curious": self.agent_chapter_1_curious,
            "chapter_2_playful": self.agent_chapter_2_playful,
            "chapter_3_vulnerable": self.agent_chapter_3_vulnerable,
            "chapter_4_intimate": self.agent_chapter_4_intimate,
            "chapter_5_secure": self.agent_chapter_5_secure,
            "boss_fight": self.agent_boss_fight,
            "angry": self.agent_angry,
            "sad": self.agent_sad,
            "flirty": self.agent_flirty,
        }


@lru_cache
def get_elevenlabs_config() -> ElevenLabsConfig:
    """Get cached ElevenLabs config instance."""
    return ElevenLabsConfig()


# Chapter name mapping
CHAPTER_NAMES: dict[int, str] = {
    1: "Curiosity",
    2: "Intrigue",
    3: "Investment",
    4: "Intimacy",
    5: "Established",
}


def get_agent_id(
    chapter: int = 1,
    mood: str | None = None,
    is_boss: bool = False,
) -> str:
    """
    Get appropriate ElevenLabs agent ID based on game state.

    Args:
        chapter: Current chapter (1-5)
        mood: Optional mood override (angry, sad, flirty, etc.)
        is_boss: Whether this is a boss encounter

    Returns:
        ElevenLabs agent ID string
    """
    config = get_elevenlabs_config()
    agents = config.get_agents_dict()

    # Boss fight takes priority
    if is_boss:
        return agents.get("boss_fight", config.default_agent_id)

    # Mood override
    if mood and mood in agents:
        return agents[mood]

    # Chapter-specific agent
    chapter_agents = {
        1: "chapter_1_curious",
        2: "chapter_2_playful",
        3: "chapter_3_vulnerable",
        4: "chapter_4_intimate",
        5: "chapter_5_secure",
    }

    chapter_key = chapter_agents.get(chapter)
    if chapter_key and chapter_key in agents:
        return agents[chapter_key]

    return config.default_agent_id
