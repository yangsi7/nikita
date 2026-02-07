"""Voice agent data models.

This module contains all Pydantic models for the voice agent:
- Server tool communication (ServerToolRequest, ServerToolResponse)
- Transcript handling (TranscriptEntry, TranscriptData)
- Scoring (CallScore, TurnScore)
- Context (VoiceContext)
- Results (CallResult)
- TTS configuration (TTSSettings) - FR-016, FR-017
- Dynamic variables (DynamicVariables) - FR-018
- Conversation config (ConversationConfig) - FR-025
- Session management (VoiceSession) - FR-024
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class ServerToolName(str, Enum):
    """Server tools available for ElevenLabs to call (FR-007)."""

    GET_CONTEXT = "get_context"
    GET_MEMORY = "get_memory"
    SCORE_TURN = "score_turn"
    UPDATE_MEMORY = "update_memory"


class CallEndReason(str, Enum):
    """Reasons a voice call ended."""

    USER_HANGUP = "user_hangup"
    NIKITA_ENDED = "nikita_ended"
    TIMEOUT = "timeout"
    ERROR = "error"
    CONNECTION_LOST = "connection_lost"


class NikitaMood(str, Enum):
    """Nikita's emotional state affecting voice (FR-017)."""

    FLIRTY = "flirty"
    VULNERABLE = "vulnerable"
    ANNOYED = "annoyed"
    PLAYFUL = "playful"
    DISTANT = "distant"
    NEUTRAL = "neutral"


# =============================================================================
# SERVER TOOL MODELS (FR-007, FR-022)
# =============================================================================


class ServerToolRequest(BaseModel):
    """Request from ElevenLabs server tool webhook (AC-T004.1).

    ElevenLabs calls our server tools when the LLM needs context or memory.
    The request is authenticated via signed token containing user_id.
    """

    tool_name: ServerToolName = Field(..., description="Which server tool to execute")
    user_id: str = Field(..., description="User ID from signed auth token")
    session_id: str = Field(..., description="ElevenLabs conversation session ID")
    data: dict[str, Any] | None = Field(
        default=None, description="Tool-specific parameters"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Request timestamp"
    )

    model_config = {"from_attributes": True}


class ServerToolResponse(BaseModel):
    """Response to ElevenLabs server tool call (FR-022).

    Must respond within 2 seconds (FR-022 requirement).
    If timeout occurs, return cache_friendly fallback.
    """

    success: bool = Field(..., description="Whether tool execution succeeded")
    tool_name: ServerToolName | None = Field(
        default=None, description="Which tool was called (for debugging)"
    )
    data: dict[str, Any] | None = Field(
        default=None, description="Tool response data for LLM"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    cache_friendly: bool = Field(
        default=False,
        description="If True, response is safe to cache/reuse (timeout fallback)",
    )
    latency_ms: int | None = Field(
        default=None, description="Tool execution time in milliseconds"
    )


# =============================================================================
# TRANSCRIPT MODELS (FR-009)
# =============================================================================


class TranscriptEntry(BaseModel):
    """Single entry in a voice conversation transcript (AC-T004.2).

    Each entry represents one turn of speech with timing and speaker info.
    """

    speaker: str = Field(..., description="'user' or 'nikita'")
    text: str = Field(..., description="Transcribed speech content")
    timestamp: datetime = Field(..., description="When this turn occurred")
    duration_ms: int | None = Field(
        default=None, description="Duration of speech in milliseconds"
    )
    confidence: float | None = Field(
        default=None, description="STT confidence score (0-1)"
    )

    model_config = {"from_attributes": True}


class TranscriptData(BaseModel):
    """Complete transcript for a voice call."""

    session_id: str = Field(..., description="ElevenLabs session ID")
    entries: list[TranscriptEntry] = Field(
        default_factory=list, description="Ordered list of transcript entries"
    )
    total_duration_ms: int = Field(default=0, description="Total call duration in ms")
    user_turns: int = Field(default=0, description="Number of user speech turns")
    nikita_turns: int = Field(default=0, description="Number of Nikita speech turns")


# =============================================================================
# SCORING MODELS (FR-006)
# =============================================================================


class TurnScore(BaseModel):
    """Score for a single conversation turn."""

    turn_number: int = Field(..., description="Turn index in conversation")
    authenticity_delta: float = Field(default=0.0)
    vulnerability_delta: float = Field(default=0.0)
    consistency_delta: float = Field(default=0.0)
    effort_delta: float = Field(default=0.0)
    analysis: str | None = Field(
        default=None, description="LLM analysis of the turn"
    )


class CallScore(BaseModel):
    """Aggregate score for an entire voice call (AC-T004.3).

    Voice scoring aggregates multiple turn scores into a single
    relationship score delta, applying engagement multipliers.
    """

    user_id: UUID = Field(..., description="User who made the call")
    session_id: str = Field(..., description="ElevenLabs session ID")
    call_duration_seconds: int = Field(..., description="Total call duration")
    turns_scored: int = Field(default=0, description="Number of turns analyzed")

    # Metric deltas (aggregate of all turns)
    authenticity_delta: float = Field(default=0.0)
    vulnerability_delta: float = Field(default=0.0)
    consistency_delta: float = Field(default=0.0)
    effort_delta: float = Field(default=0.0)

    # Aggregate score
    aggregate_score_delta: float = Field(
        default=0.0, description="Total relationship score change"
    )
    engagement_multiplier: float = Field(
        default=1.0, description="Multiplier from engagement state"
    )

    # Turn breakdown
    turn_scores: list[TurnScore] = Field(
        default_factory=list, description="Individual turn scores"
    )

    model_config = {"from_attributes": True}


# =============================================================================
# CONTEXT MODELS
# =============================================================================


class VoiceContext(BaseModel):
    """Context loaded for voice conversation (AC-T004.4).

    Same context used by MetaPromptService but formatted for
    voice dynamic variables and server tool responses.
    """

    # User info
    user_id: UUID
    user_name: str
    chapter: int = Field(ge=1, le=5)
    relationship_score: float

    # Game state
    engagement_state: str = Field(default="IN_ZONE")
    game_status: str = Field(default="active")

    # Vices (for personalization)
    primary_vice: str | None = None
    vice_severity: float = Field(default=0.5)

    # Memory context (from Graphiti)
    recent_topics: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)
    user_facts: list[str] = Field(default_factory=list)

    # Nikita state (computed)
    nikita_mood: NikitaMood = Field(default=NikitaMood.NEUTRAL)
    nikita_energy: str = Field(default="medium")
    time_of_day: str = Field(default="afternoon")

    # Conversation history summary
    last_conversation_summary: str | None = None
    days_since_last_contact: int = Field(default=0)

    model_config = {"from_attributes": True}


# =============================================================================
# RESULT MODELS
# =============================================================================


class CallResult(BaseModel):
    """Result of a completed voice call (AC-T004.5).

    Returned after call ends, containing summary of outcomes.
    """

    success: bool = Field(..., description="Whether call completed normally")
    session_id: str = Field(..., description="ElevenLabs session ID")
    user_id: UUID

    # Scoring outcome
    score_applied: bool = Field(default=False, description="Whether scoring was applied")
    score_delta: float | None = Field(
        default=None, description="Relationship score change"
    )

    # Transcript
    transcript_id: str | None = Field(
        default=None, description="ID of stored transcript"
    )
    duration_seconds: int = Field(default=0)

    # Errors
    end_reason: CallEndReason = Field(default=CallEndReason.USER_HANGUP)
    error_message: str | None = None

    model_config = {"from_attributes": True}


# =============================================================================
# TTS MODELS (FR-016, FR-017)
# =============================================================================


class TTSSettings(BaseModel):
    """TTS parameters for ElevenLabs voice synthesis.

    Controls emotional expressiveness of Nikita's voice:
    - stability: How consistent the voice is (lower = more emotional variation)
    - similarity_boost: How close to original voice (higher = more authentic)
    - speed: Speech speed multiplier (1.0 = normal)
    """

    stability: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Voice stability (lower = more expressive)",
    )
    similarity_boost: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Voice similarity to original",
    )
    speed: float = Field(
        default=1.0,
        ge=0.7,
        le=1.2,
        description="Speech speed multiplier",
    )

    model_config = {"frozen": True}  # Immutable for safety


# =============================================================================
# DYNAMIC VARIABLES MODELS (FR-018)
# =============================================================================


class DynamicVariables(BaseModel):
    """Dynamic variables injected into ElevenLabs conversation.

    Variables are available in system prompt as {{variable_name}}.
    Secret variables (secret__*) are not sent to LLM, only used server-side.

    Spec 032: Expanded to include full context parity with text agent:
    - Today/conversation summaries
    - 4D emotional state (arousal, valence, dominance, intimacy)
    - Humanization context (daily events, conflicts)
    - Aggregated context_block for prompt injection
    """

    # User context (visible to LLM)
    user_name: str = Field(default="")
    chapter: int = Field(default=1)
    relationship_score: float = Field(default=50.0)
    engagement_state: str = Field(default="IN_ZONE")

    # Spec 029: Voice-text parity - additional user context
    secureness: float = Field(default=50.0, description="User's secureness metric")
    hours_since_last: float = Field(default=0.0, description="Hours since last interaction")

    # Nikita state (visible to LLM)
    nikita_mood: str = Field(default="neutral")
    nikita_energy: str = Field(default="medium")
    time_of_day: str = Field(default="afternoon")
    day_of_week: str = Field(default="Monday", description="Current day of week")
    nikita_activity: str = Field(
        default="doing her thing",
        description="What Nikita is currently doing",
    )

    # Conversation context (visible to LLM)
    recent_topics: str = Field(default="")  # Comma-separated
    open_threads: str = Field(default="")  # Comma-separated

    # Spec 032: Expanded context fields for voice-text parity
    # Summaries
    today_summary: str = Field(
        default="",
        description="Summary of today's interactions",
    )
    last_conversation_summary: str = Field(
        default="",
        description="Summary of the last conversation",
    )

    # 4D Emotional State (Spec 023 integration)
    nikita_mood_arousal: float = Field(
        default=0.5,
        description="Arousal dimension (0=calm, 1=excited)",
    )
    nikita_mood_valence: float = Field(
        default=0.5,
        description="Valence dimension (0=negative, 1=positive)",
    )
    nikita_mood_dominance: float = Field(
        default=0.5,
        description="Dominance dimension (0=submissive, 1=dominant)",
    )
    nikita_mood_intimacy: float = Field(
        default=0.5,
        description="Intimacy dimension (0=distant, 1=close)",
    )

    # Humanization context (Specs 022, 027 integration)
    nikita_daily_events: str = Field(
        default="",
        description="What Nikita has been doing today (life simulation)",
    )
    active_conflict_type: str = Field(
        default="",
        description="Type of active relationship conflict (if any)",
    )
    active_conflict_severity: float = Field(
        default=0.0,
        description="Severity of active conflict (0-1)",
    )

    # Contextual enrichment
    emotional_context: str = Field(
        default="",
        description="Summary of current emotional context",
    )
    user_backstory: str = Field(
        default="",
        description="How user and Nikita met (from onboarding)",
    )
    context_block: str = Field(
        default="",
        description="Aggregated context for prompt injection (≤500 tokens)",
    )

    # Secret variables (NOT sent to LLM, used for server tool auth)
    # Note: These ARE sent to ElevenLabs webhook response but hidden from LLM
    # Used for {{secret__*}} substitution in server tool parameters
    secret__user_id: str = Field(default="")
    secret__signed_token: str = Field(default="")

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for ElevenLabs API, filtering secrets."""
        return {
            k: str(v)
            for k, v in self.model_dump().items()
            if not k.startswith("secret__")
        }

    def to_dict_with_secrets(self) -> dict[str, str]:
        """Convert to dict including secrets (for server-side use)."""
        return {k: str(v) for k, v in self.model_dump().items()}


# =============================================================================
# CONVERSATION CONFIG MODELS (FR-025)
# =============================================================================


class ConversationConfig(BaseModel):
    """Conversation configuration overrides for ElevenLabs.

    Used at call start to customize system prompt, voice, and LLM settings.
    Implements FR-025: Conversation Config Overrides.
    """

    # System prompt override (personalized via MetaPromptService)
    system_prompt: str | None = Field(
        default=None, description="Full system prompt override"
    )

    # First message override (personalized greeting)
    first_message: str | None = Field(
        default=None, description="Override first Nikita message"
    )

    # TTS settings (from chapter/mood calculation)
    tts: TTSSettings | None = Field(
        default=None, description="Voice settings override"
    )

    # LLM settings
    llm_model: str | None = Field(
        default=None, description="Override LLM model (e.g., claude-sonnet-4)"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="LLM temperature override"
    )
    max_tokens: int | None = Field(
        default=None, description="Max response tokens"
    )

    # Dynamic variables
    dynamic_variables: DynamicVariables | None = Field(
        default=None, description="Variables for prompt interpolation"
    )


# =============================================================================
# SESSION MODELS (FR-024)
# =============================================================================


class VoiceSession(BaseModel):
    """Voice session state for connection recovery (FR-024).

    Tracks session state to enable recovery from connection drops.
    """

    session_id: str = Field(..., description="ElevenLabs session ID")
    user_id: UUID
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # State preservation
    turn_count: int = Field(default=0)
    accumulated_score_delta: float = Field(default=0.0)
    context_snapshot: VoiceContext | None = Field(
        default=None, description="Context at session start for recovery"
    )

    # Connection state
    is_connected: bool = Field(default=True)
    recovery_token: str | None = Field(
        default=None, description="Token for session recovery"
    )
    disconnect_count: int = Field(default=0, description="Number of disconnections")

    model_config = {"from_attributes": True}
