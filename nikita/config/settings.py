"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous/public key")
    supabase_service_key: str = Field(..., description="Supabase service role key")

    # Database (direct connection for SQLAlchemy)
    database_url: str = Field(..., description="PostgreSQL connection string")

    # FalkorDB (Graphiti)
    falkordb_url: str = Field(
        default="falkordb://localhost:6379",
        description="FalkorDB connection URL",
    )

    # Anthropic (Claude for text agent + scoring)
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model for text agent",
    )

    # OpenAI (Embeddings)
    openai_api_key: str = Field(..., description="OpenAI API key for embeddings")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )

    # ElevenLabs
    elevenlabs_api_key: str = Field(..., description="ElevenLabs API key")

    # Telegram
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for Telegram bot",
    )

    # Redis (Celery broker)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # Game Constants
    starting_score: float = Field(default=50.0, description="Initial relationship score")
    max_boss_attempts: int = Field(default=3, description="Max boss attempts before game over")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
