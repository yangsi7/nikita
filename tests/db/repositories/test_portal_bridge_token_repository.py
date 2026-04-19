"""Tests for PortalBridgeTokenRepository (Spec 214 FR-11c T1.1).

Unit tests with mocked AsyncSession. Integration tests live in
`tests/db/integration/test_portal_bridge_tokens.py` and exercise the
RLS policies + atomic consume against a real DB.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from nikita.db.models.portal_bridge_token import PortalBridgeToken
from nikita.db.repositories.portal_bridge_token_repository import (
    PortalBridgeTokenRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """AsyncSession mock wired for common repo call shapes."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> PortalBridgeTokenRepository:
    return PortalBridgeTokenRepository(mock_session)


class TestMint:
    """AC-T1.1.2: `mint(user_id, reason)` inserts row with TTL matrix."""

    @pytest.mark.asyncio
    async def test_mint_resume_reason_sets_24h_ttl(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """reason='resume' → expires_at ≈ now + 24h."""
        user_id = uuid4()
        before = datetime.now(UTC)

        token = await repo.mint(user_id, "resume")

        assert isinstance(token, str)
        assert len(token) >= 32  # urlsafe base64(32 bytes) → ~43 chars
        mock_session.add.assert_called_once()
        added = mock_session.add.call_args.args[0]
        assert isinstance(added, PortalBridgeToken)
        assert added.user_id == user_id
        assert added.reason == "resume"
        assert added.token == token
        # TTL within 1 second of 24h
        delta = added.expires_at - before
        assert timedelta(hours=23, minutes=59) < delta < timedelta(
            hours=24, minutes=1
        )

    @pytest.mark.asyncio
    async def test_mint_re_onboard_reason_sets_1h_ttl(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """reason='re-onboard' → expires_at ≈ now + 1h."""
        user_id = uuid4()
        before = datetime.now(UTC)

        await repo.mint(user_id, "re-onboard")

        added = mock_session.add.call_args.args[0]
        delta = added.expires_at - before
        assert timedelta(minutes=59) < delta < timedelta(hours=1, minutes=1)

    @pytest.mark.asyncio
    async def test_mint_rejects_invalid_reason(
        self, repo: PortalBridgeTokenRepository
    ) -> None:
        """Only 'resume' and 're-onboard' are accepted (CHECK constraint mirror)."""
        with pytest.raises(ValueError):
            await repo.mint(uuid4(), "not-a-reason")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_mint_returns_fresh_token_each_call(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """Two mints → two distinct tokens."""
        t1 = await repo.mint(uuid4(), "resume")
        t2 = await repo.mint(uuid4(), "resume")
        assert t1 != t2


class TestConsume:
    """AC-T1.1.3: atomic single-use consume."""

    @pytest.mark.asyncio
    async def test_consume_valid_token_returns_user_id(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """Active, unexpired, unconsumed → returns user_id."""
        user_id = uuid4()
        # UPDATE ... RETURNING user_id returns a single row
        result = MagicMock()
        result.first.return_value = (user_id,)
        mock_session.execute.return_value = result

        got = await repo.consume("sometoken")

        assert got == user_id
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_consume_already_consumed_returns_none(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """Second call on the same token (predicate excludes consumed rows) → None."""
        result = MagicMock()
        result.first.return_value = None
        mock_session.execute.return_value = result

        got = await repo.consume("sometoken")

        assert got is None

    @pytest.mark.asyncio
    async def test_consume_expired_returns_none(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """Predicate includes `expires_at > now()` → expired token returns None."""
        result = MagicMock()
        result.first.return_value = None
        mock_session.execute.return_value = result

        got = await repo.consume("expired")

        assert got is None

    @pytest.mark.asyncio
    async def test_consume_unknown_token_returns_none(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        """Unknown token → zero rows matched → None."""
        result = MagicMock()
        result.first.return_value = None
        mock_session.execute.return_value = result

        got = await repo.consume("unknown")

        assert got is None


class TestRevokeAllForUser:
    """AC-T1.1.4: `revoke_all_for_user(user_id)` marks active tokens consumed."""

    @pytest.mark.asyncio
    async def test_revoke_returns_rowcount(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        result = MagicMock()
        result.rowcount = 3
        mock_session.execute.return_value = result

        count = await repo.revoke_all_for_user(uuid4())

        assert count == 3
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoke_with_no_active_tokens_returns_zero(
        self, repo: PortalBridgeTokenRepository, mock_session: AsyncMock
    ) -> None:
        result = MagicMock()
        result.rowcount = 0
        mock_session.execute.return_value = result

        count = await repo.revoke_all_for_user(uuid4())

        assert count == 0


class TestPortalBridgeTokenModel:
    """Model-level: token generator + TTL helpers."""

    def test_create_resume_token_has_24h_expiry(self) -> None:
        user_id = uuid4()
        before = datetime.now(UTC)

        token = PortalBridgeToken.create(user_id, "resume")

        assert token.user_id == user_id
        assert token.reason == "resume"
        assert token.token
        assert token.consumed_at is None
        delta = token.expires_at - before
        assert timedelta(hours=23, minutes=59) < delta < timedelta(
            hours=24, minutes=1
        )

    def test_create_re_onboard_token_has_1h_expiry(self) -> None:
        user_id = uuid4()
        before = datetime.now(UTC)

        token = PortalBridgeToken.create(user_id, "re-onboard")

        delta = token.expires_at - before
        assert timedelta(minutes=59) < delta < timedelta(hours=1, minutes=1)

    def test_create_rejects_invalid_reason(self) -> None:
        with pytest.raises(ValueError):
            PortalBridgeToken.create(uuid4(), "invalid-reason")  # type: ignore[arg-type]

    def test_generate_token_is_urlsafe(self) -> None:
        from nikita.db.models.portal_bridge_token import generate_portal_bridge_token

        tok = generate_portal_bridge_token()
        # urlsafe base64 of 32 bytes = 43 chars, no padding
        assert len(tok) >= 32
        assert all(
            c.isalnum() or c in ("-", "_")
            for c in tok
        ), "token must be urlsafe"
