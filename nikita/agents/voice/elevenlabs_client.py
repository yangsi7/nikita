"""ElevenLabs Conversations API client for voice agent testing and verification.

This module provides a comprehensive client for interacting with the ElevenLabs
Conversational AI API, including:
- Listing conversations with filters
- Fetching full conversation details with transcripts
- Fetching agent configuration
- Converting API responses to internal models

Used primarily for:
- Post-call verification (fetch transcripts, validate prompts)
- E2E testing (verify conversation state)
- Debugging (inspect agent config, conversation flow)

API Reference: https://elevenlabs.io/docs/api-reference/conversations
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

import httpx

from nikita.agents.voice.models import TranscriptData, TranscriptEntry
from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


class ConversationStatus(str, Enum):
    """Conversation processing status."""

    INITIATED = "initiated"
    IN_PROGRESS = "in-progress"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class ConversationDirection(str, Enum):
    """Call direction."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


@dataclass
class TranscriptTurn:
    """Single turn in a conversation transcript."""

    role: Literal["user", "agent"]
    message: str
    time_in_call_secs: float
    end_time_in_call_secs: float | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None


@dataclass
class ConversationMetadata:
    """Metadata about a conversation."""

    start_time_unix_secs: int
    call_duration_secs: int | None = None
    cost: float | None = None
    feedback: dict[str, Any] | None = None
    authorization_method: str | None = None
    charging: dict[str, Any] | None = None


@dataclass
class ConversationAnalysis:
    """Analysis results from conversation evaluation."""

    transcript_summary: str | None = None
    evaluation_criteria_results: dict[str, Any] | None = None
    data_collection_results: dict[str, Any] | None = None
    call_successful: str | None = None  # "success", "failure", "unknown"


@dataclass
class ConversationSummary:
    """Summary of a conversation from list endpoint."""

    agent_id: str
    conversation_id: str
    start_time_unix_secs: int
    call_duration_secs: int
    message_count: int
    status: ConversationStatus
    call_successful: str | None = None
    agent_name: str | None = None
    transcript_summary: str | None = None
    direction: ConversationDirection | None = None
    rating: float | None = None


@dataclass
class ConversationDetail:
    """Full conversation details including transcript."""

    agent_id: str
    conversation_id: str
    status: ConversationStatus
    transcript: list[TranscriptTurn]
    metadata: ConversationMetadata | None = None
    analysis: ConversationAnalysis | None = None
    has_audio: bool = False
    has_user_audio: bool = False
    has_response_audio: bool = False
    user_id: str | None = None


@dataclass
class ConversationListResponse:
    """Response from list conversations endpoint."""

    conversations: list[ConversationSummary]
    has_more: bool
    next_cursor: str | None = None


@dataclass
class AgentConversationConfig:
    """Agent conversation configuration."""

    agent_id: str | None = None
    tts: dict[str, Any] | None = None
    conversation: dict[str, Any] | None = None
    asr: dict[str, Any] | None = None
    turn: dict[str, Any] | None = None
    language_preset: str | None = None
    llm: dict[str, Any] | None = None
    safety: dict[str, Any] | None = None


@dataclass
class AgentConfig:
    """Full agent configuration."""

    agent_id: str
    name: str
    conversation_config: AgentConversationConfig | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    platform_settings: dict[str, Any] | None = None
    tags: list[str] | None = None

    @property
    def system_prompt(self) -> str | None:
        """Extract system prompt from conversation config."""
        if not self.conversation_config or not self.conversation_config.llm:
            return None
        return self.conversation_config.llm.get("system_prompt")

    @property
    def first_message(self) -> str | None:
        """Extract first message from conversation config."""
        if not self.conversation_config or not self.conversation_config.conversation:
            return None
        return self.conversation_config.conversation.get("first_message")

    @property
    def voice_id(self) -> str | None:
        """Extract voice ID from TTS config."""
        if not self.conversation_config or not self.conversation_config.tts:
            return None
        return self.conversation_config.tts.get("voice_id")

    @property
    def llm_model(self) -> str | None:
        """Extract LLM model from config."""
        if not self.conversation_config or not self.conversation_config.llm:
            return None
        return self.conversation_config.llm.get("model")


class ElevenLabsConversationsClient:
    """Client for ElevenLabs Conversations API.

    Provides methods to:
    - List conversations for an agent
    - Get full conversation details with transcript
    - Get agent configuration
    - Convert responses to internal models

    Example usage:
        client = ElevenLabsConversationsClient()

        # List recent conversations
        result = await client.list_conversations(agent_id="...", limit=10)

        # Get full transcript
        detail = await client.get_conversation("conversation_id")

        # Get agent config
        config = await client.get_agent_config("agent_id")
    """

    BASE_URL = "https://api.elevenlabs.io/v1/convai"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the client.

        Args:
            api_key: ElevenLabs API key. If None, uses settings.
            timeout: HTTP request timeout in seconds.
        """
        self.api_key = api_key or get_settings().elevenlabs_api_key
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("ElevenLabs API key is required")

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def list_conversations(
        self,
        agent_id: str | None = None,
        limit: int = 30,
        cursor: str | None = None,
        call_start_after_unix: int | None = None,
        call_start_before_unix: int | None = None,
        include_summary: bool = False,
    ) -> ConversationListResponse:
        """List conversations with optional filters.

        Args:
            agent_id: Filter by specific agent ID
            limit: Max conversations to return (1-100)
            cursor: Pagination cursor from previous response
            call_start_after_unix: Filter calls after this timestamp
            call_start_before_unix: Filter calls before this timestamp
            include_summary: Include transcript summaries

        Returns:
            ConversationListResponse with conversations and pagination info

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        params: dict[str, Any] = {
            "page_size": min(limit, 100),
        }

        if agent_id:
            params["agent_id"] = agent_id
        if cursor:
            params["cursor"] = cursor
        if call_start_after_unix:
            params["call_start_after_unix"] = call_start_after_unix
        if call_start_before_unix:
            params["call_start_before_unix"] = call_start_before_unix
        if include_summary:
            params["summary_mode"] = "include"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/conversations",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        conversations = [
            ConversationSummary(
                agent_id=c["agent_id"],
                conversation_id=c["conversation_id"],
                start_time_unix_secs=c["start_time_unix_secs"],
                call_duration_secs=c.get("call_duration_secs", 0),
                message_count=c.get("message_count", 0),
                status=ConversationStatus(c["status"]),
                call_successful=c.get("call_successful"),
                agent_name=c.get("agent_name"),
                transcript_summary=c.get("transcript_summary"),
                direction=ConversationDirection(c["direction"]) if c.get("direction") else None,
                rating=c.get("rating"),
            )
            for c in data.get("conversations", [])
        ]

        return ConversationListResponse(
            conversations=conversations,
            has_more=data.get("has_more", False),
            next_cursor=data.get("next_cursor"),
        )

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> ConversationDetail:
        """Get full conversation details including transcript.

        Args:
            conversation_id: The conversation ID to fetch

        Returns:
            ConversationDetail with full transcript

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/conversations/{conversation_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        # Parse transcript
        transcript = [
            TranscriptTurn(
                role=t["role"],
                message=t.get("message", ""),
                time_in_call_secs=t.get("time_in_call_secs", 0),
                end_time_in_call_secs=t.get("end_time_in_call_secs"),
                tool_calls=t.get("tool_calls"),
                tool_results=t.get("tool_results"),
            )
            for t in data.get("transcript", [])
        ]

        # Parse metadata
        metadata = None
        if "metadata" in data:
            m = data["metadata"]
            metadata = ConversationMetadata(
                start_time_unix_secs=m.get("start_time_unix_secs", 0),
                call_duration_secs=m.get("call_duration_secs"),
                cost=m.get("cost"),
                feedback=m.get("feedback"),
                authorization_method=m.get("authorization_method"),
                charging=m.get("charging"),
            )

        # Parse analysis
        analysis = None
        if data.get("analysis"):
            a = data["analysis"]
            analysis = ConversationAnalysis(
                transcript_summary=a.get("transcript_summary"),
                evaluation_criteria_results=a.get("evaluation_criteria_results"),
                data_collection_results=a.get("data_collection_results"),
                call_successful=a.get("call_successful"),
            )

        return ConversationDetail(
            agent_id=data["agent_id"],
            conversation_id=data["conversation_id"],
            status=ConversationStatus(data["status"]),
            transcript=transcript,
            metadata=metadata,
            analysis=analysis,
            has_audio=data.get("has_audio", False),
            has_user_audio=data.get("has_user_audio", False),
            has_response_audio=data.get("has_response_audio", False),
            user_id=data.get("user_id"),
        )

    async def get_agent_config(
        self,
        agent_id: str,
    ) -> AgentConfig:
        """Get agent configuration.

        Args:
            agent_id: The agent ID to fetch

        Returns:
            AgentConfig with full configuration

        Raises:
            httpx.HTTPStatusError: On API errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/agents/{agent_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        # Parse conversation config
        conv_config = None
        if "conversation_config" in data:
            cc = data["conversation_config"]
            conv_config = AgentConversationConfig(
                agent_id=cc.get("agent_id"),
                tts=cc.get("tts"),
                conversation=cc.get("conversation"),
                asr=cc.get("asr"),
                turn=cc.get("turn"),
                language_preset=cc.get("language_preset"),
                llm=cc.get("llm"),
                safety=cc.get("safety"),
            )

        return AgentConfig(
            agent_id=data["agent_id"],
            name=data.get("name", ""),
            conversation_config=conv_config,
            metadata=data.get("metadata", {}),
            platform_settings=data.get("platform_settings"),
            tags=data.get("tags"),
        )

    def to_transcript_data(
        self,
        detail: ConversationDetail,
    ) -> TranscriptData:
        """Convert ConversationDetail to internal TranscriptData model.

        Args:
            detail: ElevenLabs conversation detail

        Returns:
            TranscriptData compatible with internal scoring/analysis
        """
        entries = []
        base_time = datetime.now(timezone.utc)

        for turn in detail.transcript:
            speaker = "nikita" if turn.role == "agent" else "user"
            entry = TranscriptEntry(
                speaker=speaker,
                text=turn.message,
                timestamp=base_time,  # Could be computed from time_in_call_secs
                duration_ms=int((turn.end_time_in_call_secs or turn.time_in_call_secs) * 1000)
                if turn.end_time_in_call_secs
                else None,
                confidence=None,
            )
            entries.append(entry)

        user_turns = sum(1 for e in entries if e.speaker == "user")
        nikita_turns = sum(1 for e in entries if e.speaker == "nikita")

        return TranscriptData(
            session_id=detail.conversation_id,
            entries=entries,
            user_turns=user_turns,
            nikita_turns=nikita_turns,
        )

    async def get_latest_conversation(
        self,
        agent_id: str,
        user_id: str | None = None,
    ) -> ConversationDetail | None:
        """Get the most recent conversation for an agent/user.

        Convenience method for testing and verification.

        Args:
            agent_id: Agent ID to filter by
            user_id: Optional user ID to filter by (metadata)

        Returns:
            Latest ConversationDetail or None if no conversations
        """
        result = await self.list_conversations(agent_id=agent_id, limit=1)
        if not result.conversations:
            return None

        return await self.get_conversation(result.conversations[0].conversation_id)

    async def save_transcript_to_file(
        self,
        conversation_id: str,
        output_path: str,
    ) -> str:
        """Fetch transcript and save to a file.

        Useful for debugging and manual inspection.

        Args:
            conversation_id: Conversation to fetch
            output_path: File path to write transcript

        Returns:
            Path to the saved file
        """
        detail = await self.get_conversation(conversation_id)

        lines = [
            f"# Conversation: {detail.conversation_id}",
            f"Agent: {detail.agent_id}",
            f"Status: {detail.status.value}",
            "",
            "## Transcript",
            "",
        ]

        for turn in detail.transcript:
            speaker = "Nikita" if turn.role == "agent" else "User"
            lines.append(f"**{speaker}** ({turn.time_in_call_secs:.1f}s):")
            lines.append(turn.message)
            lines.append("")

        if detail.analysis and detail.analysis.transcript_summary:
            lines.extend([
                "## Summary",
                detail.analysis.transcript_summary,
            ])

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"[ELEVENLABS] Saved transcript to {output_path}")
        return output_path


# Factory function
def get_elevenlabs_client(
    api_key: str | None = None,
) -> ElevenLabsConversationsClient:
    """Get ElevenLabs client instance.

    Args:
        api_key: Optional API key override

    Returns:
        Configured client instance
    """
    return ElevenLabsConversationsClient(api_key=api_key)
