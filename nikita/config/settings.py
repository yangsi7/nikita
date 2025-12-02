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

    # Supabase - Optional for MVP (graceful degradation)
    supabase_url: str | None = Field(default=None, description="Supabase project URL")
    supabase_anon_key: str | None = Field(default=None, description="Supabase anonymous/public key")
    supabase_service_key: str | None = Field(default=None, description="Supabase service role key")

    # Database (direct connection for SQLAlchemy) - Optional for health checks
    database_url: str | None = Field(default=None, description="PostgreSQL connection string")

    # Neo4j Aura (Graphiti temporal knowledge graphs) - Optional for MVP
    neo4j_uri: str | None = Field(default=None, description="Neo4j Aura connection URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str | None = Field(default=None, description="Neo4j password")

    # Anthropic (Claude for text agent + scoring) - Optional for health checks
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-5-20250929",  # Updated 2025-12-02 to latest
        description="Claude model for text agent",
    )

    # OpenAI (Embeddings) - Optional for MVP
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for embeddings")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )

    # ElevenLabs - Optional (voice agent not in MVP)
    elevenlabs_api_key: str | None = Field(default=None, description="ElevenLabs API key")

    # Telegram - Optional for basic health checks
    telegram_bot_token: str | None = Field(default=None, description="Telegram bot token")
    telegram_webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for Telegram bot",
    )
    telegram_webhook_secret: str | None = Field(
        default=None,
        description="Telegram webhook secret for validation",
    )

    # NOTE: No Redis/Celery - using pg_cron + Edge Functions for background tasks

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
