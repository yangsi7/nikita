"""Test fixtures for pipeline stages."""

from datetime import datetime, UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import structlog

from nikita.context.pipeline_context import PipelineContext


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def pipeline_context() -> PipelineContext:
    """Create test pipeline context."""
    return PipelineContext(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock structlog logger."""
    logger = MagicMock()
    logger.bind.return_value = logger
    return logger


@pytest.fixture
def sample_conversation() -> dict[str, Any]:
    """Create sample conversation for testing."""
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "messages": [
            {"role": "user", "content": "Hey Nikita!"},
            {"role": "assistant", "content": "Hey babe! How was your day?"},
            {"role": "user", "content": "It was good, thanks for asking."},
            {"role": "assistant", "content": "That's great to hear!"},
        ],
        "status": "processing",
        "created_at": datetime.now(UTC),
    }


@pytest.fixture
def sample_extraction_result() -> dict[str, Any]:
    """Create sample extraction result for testing."""
    return {
        "facts": [
            {"content": "User had a good day", "confidence": 0.9},
        ],
        "summary": "User shared about their day",
        "thoughts": [
            {"content": "User seems happy today"},
        ],
        "entities": [],
        "thread_updates": [],
    }
