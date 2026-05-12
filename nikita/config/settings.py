"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal
from uuid import UUID

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

    # Observability (BKD-001)
    slow_request_threshold_seconds: float = Field(
        default=30.0,
        description="Log a warning for requests slower than this many seconds (Spec 036 T3.1). "
                    "Override via SLOW_REQUEST_THRESHOLD_SECONDS env var.",
    )

    # Supabase - Optional for MVP (graceful degradation)
    supabase_url: str | None = Field(default=None, description="Supabase project URL")
    supabase_anon_key: str | None = Field(default=None, description="Supabase anonymous/public key")
    supabase_service_key: str | None = Field(default=None, description="Supabase service role key")
    supabase_jwt_secret: str | None = Field(default=None, description="Supabase JWT secret for token verification")

    # Database (direct connection for SQLAlchemy) - Optional for health checks
    database_url: str | None = Field(default=None, description="PostgreSQL connection string")

    # NOTE: Legacy Neo4j configuration removed (Spec 042 T5.2)
    # Memory system now uses SupabaseMemory (pgVector)

    # Anthropic (Claude for text agent + scoring) - Optional for health checks
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model for text agent",
    )
    meta_prompt_model: str = Field(
        default="claude-haiku-4-5-20251001",  # Fast model for meta-prompts
        description="Claude model for meta-prompt generation (Haiku for speed)",
    )

    # OpenAI (Embeddings) - Optional for MVP
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for embeddings")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )

    # Memory dedup (Spec 042 / Spec 102 / GH #199 / Spec 216 EM-3b)
    # Cosine similarity above this threshold suppresses duplicate facts written
    # via SupabaseMemory.add_fact. History (driving issue → value):
    #   - Spec 042              → 0.95
    #   - GH #157  (commit 077d9ee) → 0.92
    #   - GH #199  (PR #255)       → 0.87  (current default)
    # Therapist-fact E2E variants (2026-03-30) embed at ~0.88-0.91; 0.87 catches
    # them while still admitting genuinely-distinct facts (different-occupation
    # examples cluster at 0.82-0.88). Future tightening should land with a new
    # GH issue, a bump here, and an updated comment per
    # `.claude/rules/tuning-constants.md`.
    memory_dedup_similarity_threshold: float = Field(
        default=0.87,
        description="Cosine similarity threshold for memory fact deduplication. "
                    "See nikita/config/settings.py history comment + GH #199.",
        ge=0.0,
        le=1.0,
    )

    # ElevenLabs - Voice Agent (Spec 007)
    elevenlabs_api_key: str | None = Field(default=None, description="ElevenLabs API key")
    elevenlabs_default_agent_id: str | None = Field(
        default=None,
        description="ElevenLabs default agent ID for voice conversations",
    )
    elevenlabs_webhook_secret: str | None = Field(
        default=None,
        description="ElevenLabs webhook secret: x-webhook-secret header for pre-call auth (GH #258); HMAC for post-call (FR-026)",
    )
    elevenlabs_meta_nikita_agent_id: str | None = Field(
        default=None,
        description="ElevenLabs agent ID for Meta-Nikita onboarding calls (Spec 028) - DEPRECATED: Use config override",
    )
    elevenlabs_phone_number_id: str | None = Field(
        default=None,
        description="ElevenLabs phone number resource ID for outbound calls (Spec 033)",
    )
    elevenlabs_voice_id: str | None = Field(
        default=None,
        description="ElevenLabs voice ID for V3 Conversational (Spec 108)",
    )

    # Twilio - Phone integration for voice calls (FR-019, FR-020)
    twilio_account_sid: str | None = Field(default=None, description="Twilio Account SID")
    twilio_auth_token: str | None = Field(default=None, description="Twilio Auth Token")
    twilio_phone_number: str | None = Field(
        default=None,
        description="Twilio phone number for inbound/outbound calls (E.164 format)",
    )

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

    # Background Tasks (pg_cron endpoints)
    task_auth_secret: str | None = Field(
        default=None,
        description="Authentication secret for pg_cron task endpoints (separate from webhook secret for security isolation)",
    )

    # Portal (Vercel deployment) - canonical apex per .claude/rules/vercel-cors-canonical.md
    # GH #374: switched from Optional[str]=None (with 5 stale Vercel-alias fallbacks)
    # to required str with canonical default. Override via PORTAL_URL for staging.
    portal_url: str = Field(
        default="https://nikita-mygirl.com",
        description="Portal frontend URL (default: canonical production apex)",
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
            "https://nikita-mygirl.com",
            "https://nikita-preview.vercel.app",
        ],
        description="Allowed CORS origins",
    )

    # Game Constants
    starting_score: float = Field(default=50.0, description="Initial relationship score")
    max_boss_attempts: int = Field(default=3, description="Max boss attempts before game over")

    # LLM Retry (Spec 109, FR-002)
    llm_retry_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max retry attempts for transient LLM failures (rate limits, server errors, timeouts)",
    )
    llm_retry_base_wait: float = Field(
        default=1.0,
        ge=0.1,
        le=30.0,
        description="Base wait time (seconds) for exponential backoff between LLM retries",
    )

    # Database statement timeout (PR #81 review finding I1)
    db_statement_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=120000,
        description="PostgreSQL statement_timeout in milliseconds. Applied on connect and checkout.",
    )

    # LLM per-call timeout (PR #81 review finding I2)
    llm_retry_call_timeout: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
        description="Per-call timeout in seconds for LLM API calls (asyncio.wait_for).",
    )

    # LLM Startup Validation
    llm_warmup_enabled: bool = Field(
        default=True,
        description="Real LLM call on startup to validate API key. Disable to reduce cold-start cost/latency.",
    )

    # Feature Flags (Spec 021)
    enable_post_processing_pipeline: bool = Field(
        default=True,
        description="Enable hierarchical prompt composition post-processing pipeline",
    )

    # Feature Flag: Life Sim Enhanced (Spec 055)
    life_sim_enhanced: bool = Field(
        default=True,
        description="Enable enhanced life sim (routine, bidirectional mood, NPC consolidation). Rollback: LIFE_SIM_ENHANCED=false",
    )

    # Feature Flag: Conflict Temperature (Spec 057) — LEGACY: always ON, flag retained for env override safety
    conflict_temperature_enabled: bool = Field(
        default=True,
        description="Legacy flag (always ON). Temperature system is the sole conflict path. All dual-path code removed.",
    )

    # Feature Flag: Psyche Agent (Spec 056)
    psyche_agent_enabled: bool = Field(
        default=True,
        description="Enable daily psyche agent (PsycheState generation, trigger detector, L3 prompt injection). Rollback: PSYCHE_AGENT_ENABLED=false",
    )
    psyche_model: str = Field(
        default="claude-opus-4-6",
        description="Claude Opus for psyche agent deep analysis",
    )

    # Feature Flag: Multi-Phase Boss (Spec 058)
    multi_phase_boss_enabled: bool = Field(
        default=True,
        description="Enable 2-phase boss encounters with PARTIAL outcome. Rollback: MULTI_PHASE_BOSS_ENABLED=false",
    )

    # Feature Flag: Pipeline Observability (Spec 110)
    observability_enabled: bool = Field(
        default=True,
        description="Enable pipeline event emission (EventEmitter). When OFF, NullEmitter used — zero overhead. Rollback: OBSERVABILITY_ENABLED=false",
    )

    # Vice Pipeline (Spec 114, GE-006)
    vice_pipeline_enabled: bool = Field(
        default=False,
        description="Enable ViceStage in pipeline (GE-006). Opt-in: set VICE_PIPELINE_ENABLED=true. Rollback: VICE_PIPELINE_ENABLED=false.",
    )

    # Unified Pipeline (Spec 042, activated Spec 043)
    unified_pipeline_enabled: bool = Field(
        default=True,
        description="Enable unified pipeline for prompt generation and post-processing. Rollback: UNIFIED_PIPELINE_ENABLED=false",
    )
    unified_pipeline_rollout_pct: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Canary rollout percentage (0-100). Uses hash(user_id) for deterministic sampling.",
    )

    # Response Timing v2 (Spec 210) — log-normal × chapter × momentum
    # Module-level constants in nikita/agents/text/timing.py and
    # nikita/agents/text/conversation_rhythm.py are canonical; this flag
    # is the primary rollback lever. MOMENTUM_ENABLED=false collapses M to 1.0.
    momentum_enabled: bool = Field(
        default=True,
        description="Enable momentum coefficient M in response-timing delay. Rollback: MOMENTUM_ENABLED=false (M=1.0, no-op).",
    )

    # Heartbeat Engine (Spec 215) — activity-aware self-driven life-simulation loop.
    # Phase 1 ships disabled by default per FR-020 rollback contract; flipping
    # HEARTBEAT_ENGINE_ENABLED=true activates the daily-arc generator + hourly
    # heartbeat handler (the pg_cron jobs nikita-heartbeat-hourly and
    # nikita-generate-daily-arcs are registered separately at the Supabase layer).
    # Cost guard: heartbeat_cost_circuit_breaker_usd_per_day caps daily LLM
    # spend. The /tasks/generate-daily-arcs handler returns HTTP 503 with
    # Retry-After when the ceiling is reached (FR-014).
    heartbeat_engine_enabled: bool = Field(
        default=False,
        description=(
            "Spec 215: enable Heartbeat Engine continuous self-driven "
            "life-simulation loop. Rollback: HEARTBEAT_ENGINE_ENABLED=false "
            "(no-op all heartbeat code paths)."
        ),
    )
    heartbeat_cost_circuit_breaker_usd_per_day: float = Field(
        default=50.0,
        description=(
            "Spec 215 FR-014: daily aggregate USD ceiling for heartbeat LLM "
            "ops. Engages graceful degradation (HTTP 503 + Retry-After to "
            "next midnight UTC) when reached. Override via "
            "HEARTBEAT_COST_CIRCUIT_BREAKER_USD_PER_DAY env var."
        ),
    )

    def is_unified_pipeline_enabled_for_user(self, user_id: str | UUID) -> bool:
        """Check if unified pipeline is enabled for a specific user.

        Uses hash-based deterministic sampling for gradual rollout.

        Args:
            user_id: User ID (UUID or string)

        Returns:
            True if unified pipeline should be used for this user
        """
        if not self.unified_pipeline_enabled:
            return False
        if self.unified_pipeline_rollout_pct >= 100:
            return True
        if self.unified_pipeline_rollout_pct <= 0:
            return False
        # Deterministic hash-based sampling
        user_hash = hash(str(user_id)) % 100
        return user_hash < self.unified_pipeline_rollout_pct

    # ------------------------------------------------------------------
    # Spec 218 Slice 218-2: wizard v2 (agent-driven) per-user rollout flag
    # ------------------------------------------------------------------

    wizard_v2_enabled: bool = Field(
        default=True,
        description=(
            "Spec 218 onboarding wizard v2 (agent-driven dynamic UI). "
            "Enabled by default as of PR-218-8 (v1 modules deleted atomically). "
            "Sticky per session: once a fresh onboarding session is started "
            "and stamped with `state_version` in `user.onboarding_profile` "
            "JSONB, that session continues on its stamped version regardless "
            "of subsequent flag flips (per plan R11)."
        ),
    )
    wizard_v2_rollout_pct: int = Field(
        default=0,
        ge=0,
        le=100,
        description=(
            "Per-user cohort percentage when `wizard_v2_enabled` is True. "
            "Deterministic hash-based sampling on user_id (mirrors "
            "`unified_pipeline_rollout_pct` precedent). 0 = nobody, 100 = "
            "everybody. Solo-dev posture: typically 0 or 100 — partial "
            "percentages are theatre for a project with zero retained users."
        ),
    )

    def is_wizard_v2_enabled_for_user(self, user_id: str) -> bool:
        """Per-user wizard v2 gate. Mirrors ``is_unified_pipeline_enabled_for_user``.

        Returns True only when the global flag is on AND the user's
        deterministic hash falls within the rollout pct band. Callers
        MUST stamp the session's `state_version` immediately on first
        fresh-start evaluation (per plan R1 + R11); subsequent turns
        honor the stamp regardless of current flag state.
        """
        if not self.wizard_v2_enabled:
            return False
        if self.wizard_v2_rollout_pct >= 100:
            return True
        if self.wizard_v2_rollout_pct <= 0:
            return False
        user_hash = hash(str(user_id)) % 100
        return user_hash < self.wizard_v2_rollout_pct

    # ------------------------------------------------------------------
    # Spec 216-B3 (T-B3-5): /converse sunset feature flag
    # ------------------------------------------------------------------

    converse_sunset_enabled: bool = Field(
        default=True,
        description=(
            "RFC 8594 sunset for legacy POST /api/v1/onboarding/converse. "
            "Default True (216-C cinematic wizard shipped 2026-05; FE moved "
            "to /answer + /state; zero production importers of legacy "
            "use-onboarding-api.ts remain). When True, /converse returns "
            "410 Gone with Sunset / Deprecation / Link headers. Set to "
            "False ONLY for explicit rollback testing or to revive the "
            "legacy path; doing so requires an ADR per Walk A1 C3 "
            "Option E rationale (handover plan, 2026-05-05). Followup: "
            "delete the handler + ConverseRequest/Response + use-onboarding-api.ts "
            "after 14-day monitoring window confirms 0 inbound calls."
        ),
    )
    converse_sunset_date: str = Field(
        default="Wed, 01 Jul 2026 00:00:00 GMT",
        description=(
            "RFC 8594 fixed instant served as the Sunset header value when "
            "converse_sunset_enabled is True. Ops sets this at deploy time; "
            "NOT computed relative-to-now per request."
        ),
    )

    # ------------------------------------------------------------------
    # Spec 216-E: Firecrawl agentic tools + fetch-budget guard
    # ------------------------------------------------------------------

    firecrawl_api_key: str = Field(
        default="",
        description=(
            "Firecrawl API key for the 4 wizard fetch_* tools (Spec 216-E). "
            "Stored as a Cloud Run secret env var (FIRECRAWL_API_KEY); never "
            "logged in plaintext or returned in any HTTP response. Empty "
            "default disables firecrawl and forces static cohort fallback."
        ),
    )
    firecrawl_timeout_s: float = Field(
        default=3.0,
        description=(
            "Per-attempt firecrawl timeout in seconds (Spec 216-E E1.6/E1.11). "
            "NOT cumulative across retries — each fetch_* call wraps a single "
            "asyncio.wait_for at this timeout. On timeout the tool falls "
            "through to the static cohort fallback within the same attempt."
        ),
    )
    fetch_budget_hard_usd: str = Field(
        default="0.15",
        description=(
            "Per-flow fetch-tool cumulative budget hard ceiling, USD as Decimal "
            "string (Spec 216-E E1.3). Mirrored by "
            "``cost_guard.FETCH_BUDGET_HARD_USD``; settings value is the "
            "ops-overridable knob, the constant is the in-code default."
        ),
    )
    fetch_budget_warn_usd: str = Field(
        default="0.10",
        description=(
            "Per-flow fetch-tool soft-warn threshold, USD as Decimal string "
            "(Spec 216-E E1.3). Crossing this threshold logs a warning but "
            "does NOT block further calls."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
