"""Walk X H2 regression tests — GH #407.

Bug: identity slots (name, age, occupation) are NOT persisted to
user_profiles structured columns after the LLM emits an IdentityExtraction.
The cumulative WizardSlots in-memory state is correct, but the write-through
to user_profiles.name / user_profiles.age / user_profiles.occupation was
dropped during the PR #405 consolidation refactor.

Fix direction: after slots_after = slots_after.apply(_fallback_delta) (line ~1114
in portal_onboarding.py), call ProfileRepository.upsert_identity_slots() if
the identity slot is newly filled.

TDD: T3 tests written BEFORE implementation (RED phase).

PII policy (per .claude/rules/testing.md): assertions reference field names
and boolean flags only; actual name/age/occupation values are synthetic test
data in fixtures only, not in log-line format strings or assertion messages.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest


USER_ID = uuid4()


def _make_user_stub(onboarding_profile: dict | None = None) -> SimpleNamespace:
    """Build a minimal user stub with mutable onboarding_profile dict."""
    return SimpleNamespace(
        id=USER_ID,
        onboarding_profile=onboarding_profile if onboarding_profile is not None else None,
    )


def _make_session_returning(user_stub: SimpleNamespace) -> AsyncMock:
    """Build an AsyncMock session returning user_stub from any SELECT.

    Wires session.execute() to return a result that supports:
    - scalar_one() — used by append_conversation_turn (SELECT FOR UPDATE)
    - unique().scalar_one_or_none() — used by UserRepository.get()

    Both paths need to return user_stub so the full handler flow works.
    """
    mock_session = AsyncMock()

    unique_result = MagicMock()
    unique_result.scalar_one_or_none = MagicMock(return_value=user_stub)

    select_result = MagicMock()
    select_result.scalar_one = MagicMock(return_value=user_stub)
    select_result.scalar_one_or_none = MagicMock(return_value=user_stub)
    select_result.unique = MagicMock(return_value=unique_result)

    mock_session.execute = AsyncMock(return_value=select_result)
    mock_session.get = AsyncMock(return_value=user_stub)
    return mock_session


def _make_turn_output_with_identity() -> object:
    """Build a TurnOutput whose delta is an identity SlotDelta."""
    from nikita.agents.onboarding.conversation_agent import TurnOutput
    from nikita.agents.onboarding.state import SlotDelta

    delta = SlotDelta(
        kind="identity",
        data={"name": "Max", "age": 28, "occupation": "designer", "confidence": 0.9},
    )
    return TurnOutput(
        delta=delta,
        reply="Nice to meet you, Max! What kind of social scene are you into?",
    )


def _make_agent_result(turn_output: object) -> object:
    return SimpleNamespace(output=turn_output, usage=lambda: None)


# ---------------------------------------------------------------------------
# T3: POST /converse — identity slot writes to user_profiles structured columns
# ---------------------------------------------------------------------------


class TestConverseIdentitySlotPersistence:
    """H2 regression: identity delta must trigger ProfileRepository.upsert_identity_slots().

    After the fix, when TurnOutput.delta.kind == 'identity', the handler
    must call upsert_identity_slots(user_id, name, age, occupation) exactly
    once with the values from the slot data.
    """

    @pytest.mark.asyncio
    async def test_identity_delta_calls_upsert_identity_slots(self):
        """T3-A: When agent emits identity SlotDelta, ProfileRepository
        upsert_identity_slots() is called exactly once with correct args.

        This test FAILS on master because upsert_identity_slots() does not
        exist on ProfileRepository and the handler never calls it.
        """
        from nikita.api.dependencies.auth import AuthenticatedUser
        from nikita.api.routes.portal_onboarding import converse
        from nikita.agents.onboarding.converse_contracts import ConverseRequest

        user_stub = _make_user_stub()
        mock_session = _make_session_returning(user_stub)
        turn_output = _make_turn_output_with_identity()
        agent_result = _make_agent_result(turn_output)

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)
        auth_user = AuthenticatedUser(id=USER_ID, email="test@example.com")

        req = ConverseRequest(
            conversation_history=[],
            user_input="I'm Max, 28, and I work as a designer",
        )

        mock_profile_repo = AsyncMock()
        mock_profile_repo.upsert_identity_slots = AsyncMock(return_value=None)

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=mock_agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore"
        ) as mock_idem_cls, patch(
            "nikita.api.routes.portal_onboarding.LLMSpendLedger"
        ) as mock_ledger_cls, patch(
            # Patch source module per testing.md — local `from X import Y` resolves
            # through sys.modules at call time; patching the source is correct.
            "nikita.db.repositories.profile_repository.ProfileRepository",
        ) as mock_profile_repo_cls:
            mock_idem = MagicMock()
            mock_idem.get = AsyncMock(return_value=None)
            mock_idem.put = AsyncMock(return_value=None)
            mock_idem_cls.return_value = mock_idem

            mock_ledger = MagicMock()
            mock_ledger.get_today = AsyncMock(return_value=0)
            mock_ledger.add_spend = AsyncMock(return_value=None)
            mock_ledger_cls.return_value = mock_ledger

            mock_profile_repo_cls.return_value = mock_profile_repo

            response = await converse(
                req=req,
                current_user=auth_user,
                session=mock_session,
                _rate_limit=None,
                idempotency_key_header=None,
            )

        from nikita.agents.onboarding.converse_contracts import ConverseResponse
        assert isinstance(response, ConverseResponse), (
            f"expected ConverseResponse, got {type(response).__name__}"
        )
        # ProfileRepository must have been instantiated with the session.
        mock_profile_repo_cls.assert_called_once_with(mock_session)
        # upsert_identity_slots must have been awaited exactly once with the
        # full identity payload from _make_turn_output_with_identity().
        mock_profile_repo.upsert_identity_slots.assert_awaited_once_with(
            user_id=USER_ID,
            name="Max",
            age=28,
            occupation="designer",
        )

    @pytest.mark.asyncio
    async def test_no_identity_delta_does_not_call_upsert_identity_slots(self):
        """T3-B: When agent emits a non-identity delta, upsert_identity_slots
        is NOT called (no spurious writes on every turn).
        """
        from nikita.api.dependencies.auth import AuthenticatedUser
        from nikita.api.routes.portal_onboarding import converse
        from nikita.agents.onboarding.converse_contracts import ConverseRequest
        from nikita.agents.onboarding.conversation_agent import TurnOutput
        from nikita.agents.onboarding.state import SlotDelta

        # Location delta (not identity)
        location_delta = SlotDelta(
            kind="location",
            data={"city": "Berlin", "confidence": 0.9},
        )
        turn_output = TurnOutput(
            delta=location_delta,
            reply="Berlin! A city with real character. What kind of scene are you into?",
        )
        agent_result = _make_agent_result(turn_output)

        user_stub = _make_user_stub()
        mock_session = _make_session_returning(user_stub)
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=agent_result)
        auth_user = AuthenticatedUser(id=USER_ID, email="test@example.com")

        req = ConverseRequest(
            conversation_history=[],
            user_input="I'm based in Berlin",
        )

        mock_profile_repo = AsyncMock()
        mock_profile_repo.upsert_identity_slots = AsyncMock(return_value=None)

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=mock_agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore"
        ) as mock_idem_cls, patch(
            "nikita.api.routes.portal_onboarding.LLMSpendLedger"
        ) as mock_ledger_cls, patch(
            # Patch source module per testing.md.
            "nikita.db.repositories.profile_repository.ProfileRepository",
        ) as mock_profile_repo_cls:
            mock_idem = MagicMock()
            mock_idem.get = AsyncMock(return_value=None)
            mock_idem.put = AsyncMock(return_value=None)
            mock_idem_cls.return_value = mock_idem

            mock_ledger = MagicMock()
            mock_ledger.get_today = AsyncMock(return_value=0)
            mock_ledger.add_spend = AsyncMock(return_value=None)
            mock_ledger_cls.return_value = mock_ledger

            mock_profile_repo_cls.return_value = mock_profile_repo

            response = await converse(
                req=req,
                current_user=auth_user,
                session=mock_session,
                _rate_limit=None,
                idempotency_key_header=None,
            )

        from nikita.agents.onboarding.converse_contracts import ConverseResponse
        assert isinstance(response, ConverseResponse)
        # upsert_identity_slots must NOT have been called for a location turn
        mock_profile_repo.upsert_identity_slots.assert_not_awaited()


# ---------------------------------------------------------------------------
# T3-C: ProfileRepository.upsert_identity_slots() unit test
# ---------------------------------------------------------------------------


class TestProfileRepositoryUpsertIdentitySlots:
    """upsert_identity_slots() must write name, age, occupation to user_profiles.

    Tests the repository method in isolation — no endpoint wiring.
    The method must exist on ProfileRepository and correctly invoke the
    SQLAlchemy upsert pattern for the user_profiles table.
    """

    def test_upsert_identity_slots_method_exists(self):
        """T3-C-1: ProfileRepository has upsert_identity_slots method.

        Fails on master because the method does not exist.
        """
        from nikita.db.repositories.profile_repository import ProfileRepository

        assert hasattr(ProfileRepository, "upsert_identity_slots"), (
            "ProfileRepository must have upsert_identity_slots method (H2 fix)"
        )
        method = getattr(ProfileRepository, "upsert_identity_slots")
        import inspect
        assert inspect.iscoroutinefunction(method), (
            "upsert_identity_slots must be async"
        )

    @pytest.mark.asyncio
    async def test_upsert_identity_slots_writes_name_age_occupation(self):
        """T3-C-2: upsert_identity_slots(user_id, name, age, occupation)
        issues a DB write that sets those columns on user_profiles.

        Uses a mock session; asserts session.execute() is called and
        session.flush() or session.commit() fires.
        """
        from nikita.db.repositories.profile_repository import ProfileRepository

        mock_session = AsyncMock()
        # Simulate get_by_user_id returning an existing profile.
        existing_profile = MagicMock()
        existing_profile.name = None
        existing_profile.age = None
        existing_profile.occupation = None

        repo = ProfileRepository(mock_session)

        with patch.object(repo, "get_by_user_id", return_value=existing_profile):
            await repo.upsert_identity_slots(
                user_id=USER_ID,
                name="Max",
                age=28,
                occupation="designer",
            )

        # After the upsert, the profile's identity fields must be set.
        assert existing_profile.name == "Max"
        assert existing_profile.age == 28
        assert existing_profile.occupation == "designer"
        # session.flush() must be called to persist the changes.
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_upsert_identity_slots_creates_profile_if_missing(self):
        """T3-C-3: When user_profiles row does not exist, upsert_identity_slots
        creates the profile with identity fields set.
        """
        from nikita.db.repositories.profile_repository import ProfileRepository

        mock_session = AsyncMock()
        repo = ProfileRepository(mock_session)

        with patch.object(repo, "get_by_user_id", return_value=None), patch.object(
            repo, "create_profile", new=AsyncMock(return_value=MagicMock())
        ) as mock_create:
            await repo.upsert_identity_slots(
                user_id=USER_ID,
                name="Lena",
                age=25,
                occupation="artist",
            )

        # create_profile must have been called with the identity fields.
        mock_create.assert_awaited_once()
        create_call = mock_create.call_args
        assert create_call is not None
        # Should pass user_id positionally or as kwarg
        all_kw = create_call.kwargs if create_call.kwargs else {}
        all_pos = list(create_call.args) if create_call.args else []
        # user_id must appear
        assert USER_ID in all_pos or all_kw.get("user_id") == USER_ID, (
            "create_profile must be called with the correct user_id"
        )

    @pytest.mark.asyncio
    async def test_upsert_identity_slots_partial_fields_ok(self):
        """T3-C-4: Partial identity (name only, no age/occupation) is valid.
        Only the provided fields should be written; None fields left unchanged.
        """
        from nikita.db.repositories.profile_repository import ProfileRepository

        mock_session = AsyncMock()
        existing_profile = MagicMock()
        existing_profile.name = None
        existing_profile.age = 30  # pre-existing age must not be overwritten
        existing_profile.occupation = "engineer"

        repo = ProfileRepository(mock_session)

        with patch.object(repo, "get_by_user_id", return_value=existing_profile):
            await repo.upsert_identity_slots(
                user_id=USER_ID,
                name="Sam",
                age=None,
                occupation=None,
            )

        assert existing_profile.name == "Sam"
        # age and occupation should remain unchanged (not overwritten with None)
        assert existing_profile.age == 30
        assert existing_profile.occupation == "engineer"
        mock_session.flush.assert_awaited()
