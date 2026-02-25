"""Tests for Spec 102 Story 3: Score Reconciliation.

T3.3: 3 tests verifying:
- Corrects drift when > threshold
- Ignores small drift (below threshold)
- Returns None when user has no metrics
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.db.repositories.user_repository import UserRepository


def _make_user(relationship_score: Decimal, metrics_composite: Decimal):
    """Create mock user with metrics returning given composite."""
    user = MagicMock()
    user.id = uuid4()
    user.relationship_score = relationship_score
    user.chapter = 2
    user.metrics = MagicMock()
    user.metrics.calculate_composite_score.return_value = metrics_composite
    return user


@pytest.fixture
def session():
    s = AsyncMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.add = MagicMock()
    return s


@pytest.fixture
def repo(session):
    return UserRepository(session)


class TestScoreReconciliation:
    """Spec 102 FR-003: Score reconciliation corrects drift."""

    @pytest.mark.asyncio
    async def test_corrects_drift_above_threshold(self, repo):
        """AC: drift of 1.3 (65.5 composite vs 64.2 score) → corrected to 65.5."""
        user = _make_user(
            relationship_score=Decimal("64.20"),
            metrics_composite=Decimal("65.50"),
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=user):
            result = await repo.reconcile_score(user.id)

            assert result is not None
            assert result["old_score"] == Decimal("64.20")
            assert result["new_score"] == Decimal("65.50")
            assert result["drift"] == Decimal("1.30")
            # Verify user score was updated
            assert user.relationship_score == Decimal("65.50")

    @pytest.mark.asyncio
    async def test_ignores_small_drift(self, repo):
        """AC: drift of 0.005 → no correction (below 0.01 threshold)."""
        user = _make_user(
            relationship_score=Decimal("64.200"),
            metrics_composite=Decimal("64.205"),
        )

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=user):
            result = await repo.reconcile_score(user.id)

            assert result is None
            # Score unchanged
            assert user.relationship_score == Decimal("64.200")

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_user(self, repo):
        """AC: Returns None when user not found."""
        with patch.object(repo, "get", new_callable=AsyncMock, return_value=None):
            result = await repo.reconcile_score(uuid4())
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_user_without_metrics(self, repo):
        """AC: Returns None when user has no metrics loaded."""
        user = MagicMock()
        user.metrics = None

        with patch.object(repo, "get", new_callable=AsyncMock, return_value=user):
            result = await repo.reconcile_score(uuid4())
            assert result is None
