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
    supabase_jwt_secret: str | None = Field(default=None, description="Supabase JWT secret for token verification")

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
    meta_prompt_model: str = Field(
        default="anthropic:claude-3-5-haiku-20241022",  # Fast model for meta-prompts
        description="Claude model for meta-prompt generation (Haiku for speed)",
    )

    # OpenAI (Embeddings) - Optional for MVP
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for embeddings")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )

    # ElevenLabs - Optional (voice agent not in MVP)
    elevenlabs_api_key: str | None = Field(default=None, description="ElevenLabs API key")

    # Firecrawl (venue research for onboarding) - 017-enhanced-onboarding
    firecrawl_api_key: str | None = Field(default=None, description="Firecrawl API key for venue search")

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

    # Portal (Vercel deployment) - Optional
    portal_url: str | None = Field(
        default=None,
        description="Portal frontend URL (e.g., https://nikita-portal.vercel.app)",
    )

    # Backend URL (Cloud Run service URL) - Required for OTP email redirects
    backend_url: str | None = Field(
        default=None,
        description="Backend service URL (e.g., https://nikita-api-xxx.run.app)",
    )

    # NOTE: No Redis/Celery - using pg_cron + Edge Functions for background tasks

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "https://portal-phi-orcin.vercel.app",
            "https://portal-yangsi7s-projects.vercel.app",  # Vercel preview deployments
        ],
        description="Allowed CORS origins",
    )

    # Game Constants
    starting_score: float = Field(default=50.0, description="Initial relationship score")
    max_boss_attempts: int = Field(default=3, description="Max boss attempts before game over")

    # Admin Configuration (comma-separated string from env var)
    admin_emails_raw: str = Field(
        default="",
        alias="ADMIN_EMAILS",
        description="Comma-separated admin email addresses (in addition to @silent-agents.com domain)",
    )

    @property
    def admin_emails(self) -> list[str]:
        """Parse comma-separated admin emails into list."""
        if not self.admin_emails_raw:
            return []
        return [e.strip() for e in self.admin_emails_raw.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
