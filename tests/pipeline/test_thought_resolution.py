"""Tests for thought auto-resolution — Spec 104 Story 3.

Cross-ref extracted facts against active thoughts, auto-resolve matches.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_resolve_exact_match():
    """Exact matching thought is marked as used."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    thought = MagicMock()
    thought.content = "He works in finance"
    thought.used_at = None

    with patch.object(repo, "get_active_thoughts", return_value=[thought]):
        with patch.object(repo, "mark_thought_used", return_value=thought) as mock_mark:
            resolved = await repo.resolve_matching_thoughts(
                user_id=uuid4(),
                facts=["He works in finance"],
            )

    assert resolved >= 1
    mock_mark.assert_called()


@pytest.mark.asyncio
async def test_resolve_similar_match():
    """Similar thought (>0.6 similarity) is resolved."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    thought = MagicMock()
    thought.content = "He works in the finance industry"
    thought.used_at = None
    thought.id = uuid4()

    with patch.object(repo, "get_active_thoughts", return_value=[thought]):
        with patch.object(repo, "mark_thought_used", return_value=thought) as mock_mark:
            resolved = await repo.resolve_matching_thoughts(
                user_id=uuid4(),
                facts=["He works in finance"],
            )

    assert resolved >= 1


@pytest.mark.asyncio
async def test_resolve_no_match():
    """No matching thoughts means 0 resolved."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    thought = MagicMock()
    thought.content = "She loves hiking in mountains"
    thought.used_at = None

    with patch.object(repo, "get_active_thoughts", return_value=[thought]):
        with patch.object(repo, "mark_thought_used") as mock_mark:
            resolved = await repo.resolve_matching_thoughts(
                user_id=uuid4(),
                facts=["He works in finance"],
            )

    assert resolved == 0
    mock_mark.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_empty_facts():
    """Empty facts list returns 0."""
    from nikita.db.repositories.thought_repository import NikitaThoughtRepository

    mock_session = AsyncMock()
    repo = NikitaThoughtRepository(mock_session)

    resolved = await repo.resolve_matching_thoughts(
        user_id=uuid4(),
        facts=[],
    )

    assert resolved == 0
