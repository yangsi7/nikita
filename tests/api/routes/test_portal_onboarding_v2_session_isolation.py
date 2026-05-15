"""Regression test: post-onboarding chat asyncpg poisoning (GH #638 / Walk #108).

Root cause:
  _run_completion_side_effects step 5 (memory seeding) uses the ROUTE session
  to construct SupabaseMemory and call add_fact(). If add_fact() raises a DB
  exception (e.g., vector-extension unavailable, statement_timeout, unique
  violation), the route session is left in asyncpg InFailedSQLTransaction
  state.

  The outer get_async_session() dependency then tries session.commit() which
  raises InFailedSQLTransactionError. After that commit failure get_async_session
  calls session.rollback() and re-raises — BUT the underlying asyncpg connection
  is returned to the pool in a state that pool_reset_on_return='rollback' may not
  reliably clean (known gap: SQLAlchemy GH #6467 + asyncpg async checkin path).

  The NEXT request (e.g., "hey nikita" Telegram message) draws that poisoned
  connection from the pool and immediately fails with InFailedSQLTransactionError
  even before its first query. Walk #108 observed exactly this sequence.

Fix (GH #638):
  Step 5 uses its own isolated session (`async with get_session_maker()() as …`).
  A failure inside add_fact() never touches the route session; the route session
  commits cleanly; the pool connection returned by the route request is clean.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.exc import OperationalError


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_user(user_id):
    user = MagicMock()
    user.id = user_id
    user.onboarding_status = "in_progress"
    user.onboarding_profile = {}  # no backstory_preview yet
    return user


@pytest.fixture
def mock_state():
    from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2

    slots = WizardSlotsV2(
        display_name={"display_name": "Alice"},
        city={"city": "Zurich"},
        age={"age": 28},
        occupation={"occupation": "engineer"},
    )
    return WizardStateV2(slots=slots, phase=Phase.phase2)


@pytest.fixture
def route_session():
    """Simulates the FastAPI request-scoped AsyncSession."""
    session = AsyncMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def isolated_session():
    """Simulates the isolated session opened by the side-effect helper."""
    session = AsyncMock()
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def mock_session_maker(isolated_session):
    """Returns a session_maker callable whose context-manager yields isolated_session."""
    maker = MagicMock()
    maker.return_value = isolated_session
    return maker


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.update_onboarding_status = AsyncMock()
    repo.activate_game = AsyncMock()
    return repo


@pytest.fixture
def mock_profile_repo_factory(user_id):
    """Patch ProfileRepository to return a mock with no existing profile."""
    repo = AsyncMock()
    repo.get_by_user_id = AsyncMock(return_value=None)
    repo.create_profile = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# Core isolation test — the poison sequence from Walk #108
# ---------------------------------------------------------------------------


class TestMemorySeedSessionIsolation:
    """Step 5 (memory seed) must use an isolated session so that a DB error
    inside SupabaseMemory.add_fact() does NOT poison the route session.
    """

    @pytest.mark.asyncio
    async def test_route_session_not_used_by_memory_seed(
        self,
        mock_user,
        mock_state,
        route_session,
        isolated_session,
        mock_session_maker,
        mock_user_repo,
        mock_profile_repo_factory,
    ):
        """Route session must never be passed to SupabaseMemory (GH #638).

        SupabaseMemory is constructed with the isolated_session, not the
        route_session. Even if add_fact() raises, route_session.rollback is
        never called — it stays clean for the outer commit.
        """
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        memory_mock = AsyncMock()
        memory_mock.add_fact = AsyncMock()

        constructed_with = {}

        def make_memory(**kwargs):
            constructed_with.update(kwargs)
            return memory_mock

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo_factory,
            ),
            patch(
                "nikita.engine.vice.seeder.seed_vices_from_profile",
                new_callable=AsyncMock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.VicePreferenceRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
                side_effect=make_memory,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_settings",
                return_value=MagicMock(openai_api_key="sk-test-key"),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
                return_value=AsyncMock(initialize_user=AsyncMock()),
            ),
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=route_session,
            )

        # SupabaseMemory must be constructed with the isolated session, NOT the route session
        assert "session" in constructed_with, "SupabaseMemory must receive 'session' kwarg"
        assert constructed_with["session"] is not route_session, (
            "SupabaseMemory must NOT use the route session — "
            "a DB error inside add_fact() would poison the route session (GH #638)"
        )
        assert constructed_with["session"] is isolated_session, (
            "SupabaseMemory must use the isolated session from get_session_maker()"
        )

        # Route session must never have rollback called (it was never touched by memory seed)
        # seed_vices may call it if it fails, but on the happy path no rollback is expected
        route_session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_memory_seed_failure_does_not_poison_route_session(
        self,
        mock_user,
        mock_state,
        route_session,
        isolated_session,
        mock_session_maker,
        mock_user_repo,
        mock_profile_repo_factory,
    ):
        """The Walk #108 poison sequence: add_fact() raises → route session must be clean.

        If memory seeding used the route session, a DB error in add_fact() would
        leave route_session in InFailedSQLTransaction state. The outer commit would
        then raise InFailedSQLTransactionError and the pool connection would be poisoned.

        With the fix, add_fact() raises inside the isolated session; the isolated session
        is rolled back automatically by its context manager. The route session is untouched.
        """
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        # Simulate add_fact() raising a DB error (e.g., pgVector extension unavailable)
        memory_mock = AsyncMock()
        memory_mock.add_fact = AsyncMock(
            side_effect=OperationalError(
                "could not connect to server", None, None
            )
        )

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo_factory,
            ),
            patch(
                "nikita.engine.vice.seeder.seed_vices_from_profile",
                new_callable=AsyncMock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.VicePreferenceRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
                return_value=memory_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_settings",
                return_value=MagicMock(openai_api_key="sk-test-key"),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
                return_value=AsyncMock(initialize_user=AsyncMock()),
            ),
        ):
            # Must NOT raise — memory seeding failure is non-fatal
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=route_session,
            )

        # profile/status/game must have completed (steps 1-3)
        mock_profile_repo_factory.create_profile.assert_awaited_once()
        mock_user_repo.update_onboarding_status.assert_awaited_once_with(
            mock_user.id, "completed"
        )
        mock_user_repo.activate_game.assert_awaited_once_with(mock_user.id)

        # CRITICAL: route_session.rollback must NOT be called due to memory seed failure.
        # The isolated session's context manager handles cleanup; the route session is untouched.
        route_session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_isolated_session_context_manager_entered(
        self,
        mock_user,
        mock_state,
        route_session,
        isolated_session,
        mock_session_maker,
        mock_user_repo,
        mock_profile_repo_factory,
    ):
        """The isolated session must be used as a context manager so it is
        properly committed or rolled back regardless of add_fact() outcome.
        """
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        memory_mock = AsyncMock()
        memory_mock.add_fact = AsyncMock()

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo_factory,
            ),
            patch(
                "nikita.engine.vice.seeder.seed_vices_from_profile",
                new_callable=AsyncMock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.VicePreferenceRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_session_maker",
                return_value=mock_session_maker,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
                return_value=memory_mock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_settings",
                return_value=MagicMock(openai_api_key="sk-test-key"),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
                return_value=AsyncMock(initialize_user=AsyncMock()),
            ),
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=route_session,
            )

        # The session_maker must have been called to create an isolated session
        mock_session_maker.assert_called_once()
        # The context manager must have been entered (ensures cleanup on exit)
        isolated_session.__aenter__.assert_awaited_once()
        isolated_session.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_openai_key_skips_memory_seed_cleanly(
        self,
        mock_user,
        mock_state,
        route_session,
        mock_session_maker,
        mock_user_repo,
        mock_profile_repo_factory,
    ):
        """When openai_api_key is not configured, memory seeding is skipped.
        No isolated session should be opened (nothing to seed).
        Route session must remain untouched.
        """
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects

        with (
            patch(
                "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
                return_value=mock_profile_repo_factory,
            ),
            patch(
                "nikita.engine.vice.seeder.seed_vices_from_profile",
                new_callable=AsyncMock,
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.VicePreferenceRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.get_settings",
                return_value=MagicMock(openai_api_key=None),
            ),
            patch(
                "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
                return_value=AsyncMock(initialize_user=AsyncMock()),
            ),
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=mock_state,
                user_repo=mock_user_repo,
                session=route_session,
            )

        route_session.rollback.assert_not_awaited()
        # session_maker should NOT be called when there's nothing to seed
        mock_session_maker.assert_not_called()
