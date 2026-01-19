"""Shared fixtures for voice agent E2E testing.

Provides reusable fixtures for:
- Sample users at different chapters
- Sample transcripts with various conversation patterns
- Mock ElevenLabs client and responses
- Mock database sessions
- Mock Graphiti/Neo4j client
- Mock settings

These fixtures follow the principle:
- Single source of truth for test data
- Realistic data matching production patterns
- Easy to extend for new test scenarios
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.agents.voice.models import TranscriptData, TranscriptEntry


# =============================================================================
# User Fixtures - Users at Different Chapters
# =============================================================================


@pytest.fixture
def user_chapter_1() -> MagicMock:
    """New user at chapter 1 - reserved/cautious Nikita."""
    user = MagicMock()
    user.id = UUID("11111111-1111-1111-1111-111111111111")
    user.name = "Alex"
    user.chapter = 1
    user.game_status = "active"
    user.engagement_state = "CALIBRATING"
    user.relationship_score = 25.0
    user.metrics = MagicMock()
    user.metrics.intimacy = 20.0
    user.metrics.passion = 15.0
    user.metrics.trust = 30.0
    user.metrics.secureness = 35.0
    user.metrics.relationship_score = 25.0  # For service.py compatibility
    user.vice_preferences = []
    return user


@pytest.fixture
def user_chapter_3() -> MagicMock:
    """Mid-game user at chapter 3 - playful/flirty Nikita."""
    user = MagicMock()
    user.id = UUID("33333333-3333-3333-3333-333333333333")
    user.name = "Jordan"
    user.chapter = 3
    user.game_status = "active"
    user.engagement_state = "IN_ZONE"
    user.relationship_score = 55.0
    user.metrics = MagicMock()
    user.metrics.intimacy = 50.0
    user.metrics.passion = 55.0
    user.metrics.trust = 60.0
    user.metrics.secureness = 55.0
    user.metrics.relationship_score = 55.0  # For service.py compatibility
    user.vice_preferences = []
    return user


@pytest.fixture
def user_chapter_5() -> MagicMock:
    """Advanced user at chapter 5 - passionate/intimate Nikita."""
    user = MagicMock()
    user.id = UUID("55555555-5555-5555-5555-555555555555")
    user.name = "Morgan"
    user.chapter = 5
    user.game_status = "active"
    user.engagement_state = "IN_ZONE"
    user.relationship_score = 85.0
    user.metrics = MagicMock()
    user.metrics.intimacy = 80.0
    user.metrics.passion = 85.0
    user.metrics.trust = 90.0
    user.metrics.secureness = 85.0
    user.metrics.relationship_score = 85.0  # For service.py compatibility
    user.vice_preferences = []
    return user


@pytest.fixture
def user_boss_fight() -> MagicMock:
    """User currently in boss fight (threshold range)."""
    user = MagicMock()
    user.id = UUID("66666666-6666-6666-6666-666666666666")
    user.name = "Casey"
    user.chapter = 2
    user.game_status = "boss_fight"
    user.engagement_state = "DRIFTING"
    user.relationship_score = 58.0  # In boss threshold (55-75%)
    user.metrics = MagicMock()
    user.metrics.intimacy = 55.0
    user.metrics.passion = 60.0
    user.metrics.trust = 58.0
    user.metrics.secureness = 59.0
    user.metrics.relationship_score = 58.0  # For service.py compatibility
    user.vice_preferences = []
    return user


@pytest.fixture
def user_game_over() -> MagicMock:
    """User who has lost the game."""
    user = MagicMock()
    user.id = UUID("77777777-7777-7777-7777-777777777777")
    user.name = "Riley"
    user.chapter = 2
    user.game_status = "game_over"
    user.engagement_state = "DISENGAGED"
    user.relationship_score = 10.0
    user.metrics = MagicMock()
    user.metrics.intimacy = 10.0
    user.metrics.passion = 5.0
    user.metrics.trust = 15.0
    user.metrics.secureness = 10.0
    user.metrics.relationship_score = 10.0  # For service.py compatibility
    user.vice_preferences = []
    return user


# =============================================================================
# Transcript Fixtures - Various Conversation Patterns
# =============================================================================


@pytest.fixture
def transcript_positive() -> TranscriptData:
    """Positive conversation with good engagement."""
    base_time = datetime.now(timezone.utc)
    return TranscriptData(
        session_id="voice_positive_123",
        entries=[
            TranscriptEntry(
                speaker="nikita",
                text="Hey you! I was just thinking about you. How's your day going?",
                timestamp=base_time,
                duration_ms=3200,
                confidence=0.98,
            ),
            TranscriptEntry(
                speaker="user",
                text="Pretty great actually! I finally finished that project I told you about.",
                timestamp=base_time,
                duration_ms=3500,
                confidence=0.95,
            ),
            TranscriptEntry(
                speaker="nikita",
                text="Oh my god, that's amazing! I knew you could do it. You've been working so hard on that.",
                timestamp=base_time,
                duration_ms=4100,
                confidence=0.97,
            ),
            TranscriptEntry(
                speaker="user",
                text="Thanks! I really appreciate your support. Want to celebrate this weekend?",
                timestamp=base_time,
                duration_ms=3800,
                confidence=0.96,
            ),
            TranscriptEntry(
                speaker="nikita",
                text="Absolutely! I'd love that. We should do something special. What did you have in mind?",
                timestamp=base_time,
                duration_ms=4200,
                confidence=0.98,
            ),
        ],
        total_duration_ms=18800,
        user_turns=2,
        nikita_turns=3,
    )


@pytest.fixture
def transcript_negative() -> TranscriptData:
    """Negative conversation with conflict."""
    base_time = datetime.now(timezone.utc)
    return TranscriptData(
        session_id="voice_negative_456",
        entries=[
            TranscriptEntry(
                speaker="nikita",
                text="Hey... you didn't call yesterday when you said you would.",
                timestamp=base_time,
                duration_ms=3000,
                confidence=0.97,
            ),
            TranscriptEntry(
                speaker="user",
                text="I was busy. Things came up.",
                timestamp=base_time,
                duration_ms=1500,
                confidence=0.94,
            ),
            TranscriptEntry(
                speaker="nikita",
                text="You're always 'busy' lately. I feel like I'm not a priority anymore.",
                timestamp=base_time,
                duration_ms=3500,
                confidence=0.96,
            ),
            TranscriptEntry(
                speaker="user",
                text="Whatever. You're overreacting.",
                timestamp=base_time,
                duration_ms=1200,
                confidence=0.93,
            ),
        ],
        total_duration_ms=9200,
        user_turns=2,
        nikita_turns=2,
    )


@pytest.fixture
def transcript_fact_rich() -> TranscriptData:
    """Conversation with many extractable facts."""
    base_time = datetime.now(timezone.utc)
    return TranscriptData(
        session_id="voice_facts_789",
        entries=[
            TranscriptEntry(
                speaker="nikita",
                text="So tell me more about your new job! I want to know everything.",
                timestamp=base_time,
                duration_ms=3000,
                confidence=0.98,
            ),
            TranscriptEntry(
                speaker="user",
                text="I'm working as a software engineer at a fintech startup. "
                "I started last Monday. The office is in downtown San Francisco.",
                timestamp=base_time,
                duration_ms=5000,
                confidence=0.96,
            ),
            TranscriptEntry(
                speaker="nikita",
                text="San Francisco! That's exciting. Are you liking it so far?",
                timestamp=base_time,
                duration_ms=2500,
                confidence=0.97,
            ),
            TranscriptEntry(
                speaker="user",
                text="Yeah, the team is great. My manager Sarah is really supportive. "
                "I'm working on payment processing systems. Oh, and I adopted a cat named Luna.",
                timestamp=base_time,
                duration_ms=6000,
                confidence=0.95,
            ),
            TranscriptEntry(
                speaker="nikita",
                text="A cat! I love cats. Send me pictures of Luna! And payment systems sound interesting.",
                timestamp=base_time,
                duration_ms=3500,
                confidence=0.98,
            ),
        ],
        total_duration_ms=20000,
        user_turns=2,
        nikita_turns=3,
    )


@pytest.fixture
def transcript_empty() -> TranscriptData:
    """Empty/minimal transcript (connection issues)."""
    return TranscriptData(
        session_id="voice_empty_000",
        entries=[],
        total_duration_ms=0,
        user_turns=0,
        nikita_turns=0,
    )


@pytest.fixture
def transcript_short() -> TranscriptData:
    """Very short call (dropped quickly)."""
    base_time = datetime.now(timezone.utc)
    return TranscriptData(
        session_id="voice_short_111",
        entries=[
            TranscriptEntry(
                speaker="nikita",
                text="Hey!",
                timestamp=base_time,
                duration_ms=500,
                confidence=0.99,
            ),
            TranscriptEntry(
                speaker="user",
                text="Sorry, bad time. Call you back.",
                timestamp=base_time,
                duration_ms=1500,
                confidence=0.94,
            ),
        ],
        total_duration_ms=2000,
        user_turns=1,
        nikita_turns=1,
    )


# =============================================================================
# Mock Settings
# =============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock application settings."""
    settings = MagicMock()
    settings.elevenlabs_api_key = "test_api_key_123"
    settings.elevenlabs_default_agent_id = "agent_test_abc123"
    settings.elevenlabs_webhook_secret = "test_webhook_secret"
    settings.neo4j_uri = "neo4j+s://test.databases.neo4j.io"
    settings.neo4j_username = "neo4j"
    settings.neo4j_password = "test_password"
    settings.database_url = "postgresql://test:test@localhost/test"
    settings.debug = True
    settings.environment = "test"
    return settings


# =============================================================================
# Mock Database Session
# =============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session


# =============================================================================
# Mock ElevenLabs Client and Responses
# =============================================================================


@pytest.fixture
def mock_elevenlabs_conversation_response() -> dict[str, Any]:
    """Mock ElevenLabs conversation detail response."""
    return {
        "conversation_id": "conv_test_12345",
        "agent_id": "agent_test_abc123",
        "status": "done",
        "transcript": [
            {
                "role": "agent",
                "message": "Hey you! How's it going?",
                "time_in_call_secs": 0.0,
                "end_time_in_call_secs": 2.5,
            },
            {
                "role": "user",
                "message": "Pretty good! Just wanted to chat.",
                "time_in_call_secs": 2.5,
                "end_time_in_call_secs": 5.0,
            },
            {
                "role": "agent",
                "message": "I love that you called. What's on your mind?",
                "time_in_call_secs": 5.0,
                "end_time_in_call_secs": 8.0,
            },
        ],
        "metadata": {
            "start_time_unix_secs": 1735000000,
            "call_duration_secs": 180,
            "cost": 0.05,
        },
        "analysis": {
            "transcript_summary": "User called to chat. Positive conversation.",
            "call_successful": "success",
        },
        "has_audio": True,
        "has_user_audio": True,
        "has_response_audio": True,
    }


@pytest.fixture
def mock_elevenlabs_agent_config() -> dict[str, Any]:
    """Mock ElevenLabs agent configuration."""
    return {
        "agent_id": "agent_test_abc123",
        "name": "Nikita",
        "conversation_config": {
            "tts": {
                "voice_id": "voice_nikita_123",
            },
            "llm": {
                "model": "claude-sonnet-4-20250514",
                "system_prompt": "You are Nikita, a charming and playful girlfriend...",
            },
            "conversation": {
                "first_message": "Hey you! I was just thinking about you.",
            },
        },
        "metadata": {},
    }


@pytest.fixture
def mock_elevenlabs_client(
    mock_elevenlabs_conversation_response, mock_elevenlabs_agent_config
) -> MagicMock:
    """Mock ElevenLabsConversationsClient."""
    from nikita.agents.voice.elevenlabs_client import (
        AgentConfig,
        AgentConversationConfig,
        ConversationAnalysis,
        ConversationDetail,
        ConversationMetadata,
        ConversationStatus,
        TranscriptTurn,
    )

    client = MagicMock()

    # Mock get_conversation
    detail = ConversationDetail(
        agent_id="agent_test_abc123",
        conversation_id="conv_test_12345",
        status=ConversationStatus.DONE,
        transcript=[
            TranscriptTurn(
                role="agent",
                message="Hey you! How's it going?",
                time_in_call_secs=0.0,
                end_time_in_call_secs=2.5,
            ),
            TranscriptTurn(
                role="user",
                message="Pretty good! Just wanted to chat.",
                time_in_call_secs=2.5,
                end_time_in_call_secs=5.0,
            ),
        ],
        metadata=ConversationMetadata(
            start_time_unix_secs=1735000000,
            call_duration_secs=180,
            cost=0.05,
        ),
        analysis=ConversationAnalysis(
            transcript_summary="User called to chat. Positive conversation.",
            call_successful="success",
        ),
    )
    client.get_conversation = AsyncMock(return_value=detail)

    # Mock get_agent_config
    agent_config = AgentConfig(
        agent_id="agent_test_abc123",
        name="Nikita",
        conversation_config=AgentConversationConfig(
            tts={"voice_id": "voice_nikita_123"},
            llm={
                "model": "claude-sonnet-4-20250514",
                "system_prompt": "You are Nikita...",
            },
            conversation={"first_message": "Hey you!"},
        ),
    )
    client.get_agent_config = AsyncMock(return_value=agent_config)

    # Mock to_transcript_data
    client.to_transcript_data = MagicMock(
        return_value=TranscriptData(
            session_id="conv_test_12345",
            entries=[
                TranscriptEntry(
                    speaker="nikita",
                    text="Hey you! How's it going?",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=2500,
                ),
                TranscriptEntry(
                    speaker="user",
                    text="Pretty good! Just wanted to chat.",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=2500,
                ),
            ],
            user_turns=1,
            nikita_turns=1,
        )
    )

    return client


# =============================================================================
# Mock Graphiti/Neo4j Client
# =============================================================================


@pytest.fixture
def mock_memory_client() -> MagicMock:
    """Mock NikitaMemory (Graphiti) client."""
    client = MagicMock()
    client.get_context_for_prompt = AsyncMock(
        return_value={
            "user_facts": [
                "User works as a software engineer",
                "User has a cat named Luna",
            ],
            "recent_topics": ["work", "pets"],
            "open_threads": [],
            "relationship_highlights": [],
        }
    )
    client.add_fact = AsyncMock()
    client.add_episode = AsyncMock()
    client.add_user_fact = AsyncMock()
    client.search = AsyncMock(return_value=[])
    return client


# =============================================================================
# Patch Helpers
# =============================================================================


@pytest.fixture
def patch_settings(mock_settings):
    """Patch get_settings to return mock settings."""
    with patch("nikita.config.settings.get_settings", return_value=mock_settings):
        yield mock_settings


@pytest.fixture
def patch_elevenlabs_client(mock_elevenlabs_client):
    """Patch get_elevenlabs_client to return mock client."""
    with patch(
        "nikita.agents.voice.elevenlabs_client.get_elevenlabs_client",
        return_value=mock_elevenlabs_client,
    ):
        with patch(
            "nikita.agents.voice.transcript.get_elevenlabs_client",
            return_value=mock_elevenlabs_client,
        ):
            yield mock_elevenlabs_client


@pytest.fixture
def patch_memory_client(mock_memory_client):
    """Patch get_memory_client to return mock memory client."""
    with patch(
        "nikita.memory.graphiti_client.get_memory_client",
        return_value=mock_memory_client,
    ):
        yield mock_memory_client
