"""Integration tests for the /answer wiring of 216-D + 216-E (Spec 216-DE-wire).

Verifies the route handler:
  - Resets ``deps.fetch_invocations_this_turn = 0`` per turn.
  - Passes ``builtin_tools=[prepared_web_search(...)]`` to ``agent.run`` (or
    ``[]`` on turn 0 when no city is set).
  - Triggers Big5 judge persistence on prose slots; nothing on non-prose.
  - Populates ``cohort_chips`` ONLY when next_slot_kind=primary_hobbies.
  - Populates ``archetype_cards`` ONLY when next_slot_kind=backstory_pick.
  - NEVER leaks any of the 8 forbidden personality terms in the response.

Test architecture mirrors ``test_onboarding_answer.py``: mock the agent at
``get_conversation_agent`` boundary, mock repositories, real router +
TestClient.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")

FORBIDDEN_TERMS = (
    "big5",
    "ocean",
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "confidence",
)


def _make_app(user_id: UUID = USER_ID) -> tuple[FastAPI, AsyncMock]:
    from nikita.api.dependencies.auth import (
        AuthenticatedUser,
        get_authenticated_user,
        get_current_user_id,
    )
    from nikita.api.middleware.rate_limit import answer_rate_limit
    from nikita.api.routes.portal_onboarding import router
    from nikita.db.database import get_async_session

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/onboarding")

    mock_session = AsyncMock(spec=AsyncSession)

    async def _session_override():
        return mock_session

    async def _auth_override() -> AuthenticatedUser:
        return AuthenticatedUser(id=user_id, email="test@example.com")

    async def _rate_limit_bypass() -> None:
        return None

    app.dependency_overrides[get_async_session] = _session_override
    app.dependency_overrides[get_authenticated_user] = _auth_override
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[answer_rate_limit] = _rate_limit_bypass
    return app, mock_session


def _make_user(profile: dict | None = None, big5_vector: dict | None = None) -> MagicMock:
    user = MagicMock()
    user.id = USER_ID
    user.onboarding_profile = profile if profile is not None else {}
    user.big5_vector = big5_vector if big5_vector is not None else {}
    user.archetype_candidates = []
    return user


def _make_agent_run_result(
    *,
    delta_kind: str | None,
    delta_data: dict | None,
    reply: str,
    next_slot_kind: str | None = None,
):
    from nikita.agents.onboarding.conversation_agent import TurnOutput
    from nikita.agents.onboarding.question_registry import SlotKind
    from nikita.agents.onboarding.state import SlotDelta

    delta = (
        SlotDelta(kind=delta_kind, data=delta_data or {})
        if delta_kind is not None
        else None
    )
    next_kind = SlotKind(next_slot_kind) if next_slot_kind else None
    output = TurnOutput(delta=delta, reply=reply, next_slot_kind=next_kind)
    result = MagicMock(name="agent_run_result")
    result.output = output
    return result


def _patches(agent: MagicMock, user_repo: MagicMock, link_repo: MagicMock,
             idem_store: MagicMock, append_mock: AsyncMock):
    """Return the standard patch context managers used across the suite."""
    return [
        patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=agent,
        ),
        patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=idem_store,
        ),
        patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            append_mock,
        ),
        patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ),
        patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=link_repo,
        ),
    ]


def _bare_idem() -> MagicMock:
    s = MagicMock()
    s.get = AsyncMock(return_value=None)
    s.put = AsyncMock()
    return s


def _bare_link_repo() -> MagicMock:
    r = MagicMock()
    r.get_active_for_user = AsyncMock(return_value=None)
    r.create_link_code = AsyncMock()
    return r


def _post(app: FastAPI, payload: dict):
    client = TestClient(app)
    return client.post("/api/v1/onboarding/answer", json=payload)


# ---------------------------------------------------------------------------
# B1: deps.fetch_invocations_this_turn is reset at turn start
# ---------------------------------------------------------------------------


class TestFetchInvocationsResetPerTurn:
    """ConverseDeps fresh per turn ⇒ fetch_invocations_this_turn == 0."""

    def test_run_kwargs_carries_fresh_deps(self) -> None:
        app, _ = _make_app()
        agent = MagicMock()
        agent.run = AsyncMock(
            return_value=_make_agent_run_result(
                delta_kind="city", delta_data={"city": "Zurich"}, reply="ok"
            )
        )
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        captured: dict = {}

        async def _capture(*_args, **kwargs):
            captured["deps"] = kwargs.get("deps")
            captured["builtin_tools"] = kwargs.get("builtin_tools")
            return _make_agent_run_result(
                delta_kind="city", delta_data={"city": "Zurich"}, reply="ok"
            )

        with patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=_capture,
        ), \
            patch(
                "nikita.api.routes.portal_onboarding.get_conversation_agent",
                return_value=agent,
            ), \
            patch(
                "nikita.api.routes.portal_onboarding.IdempotencyStore",
                return_value=_bare_idem(),
            ), \
            patch(
                "nikita.api.routes.portal_onboarding.append_conversation_turn",
                AsyncMock(),
            ), \
            patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=user_repo,
            ), \
            patch(
                "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
                return_value=_bare_link_repo(),
            ):
            response = _post(
                app,
                {
                    "slot_kind": "city",
                    "value": "Zurich",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        deps = captured["deps"]
        assert deps is not None, "run_agent_with_capture must be called with deps."
        assert deps.fetch_invocations_this_turn == 0, (
            "Per-turn budget MUST be reset before agent.run."
        )
        # Turn 0 (no city in state yet) ⇒ builtin_tools is empty list.
        assert isinstance(captured["builtin_tools"], list)


# ---------------------------------------------------------------------------
# B2: Big5 judge persists on prose slots; not on non-prose
# ---------------------------------------------------------------------------


class TestBig5Wiring:
    """216-DE-wire: Big5 judge fires on prose slots, persists via repo."""

    def test_prose_slot_triggers_big5_persist(self) -> None:
        app, _ = _make_app()
        agent = MagicMock()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        # Stub update_big5_vector to return a non-empty merged vector.
        async def _fake_update_big5(*, prose, prior_vector, judge):  # noqa: ANN001
            return {
                "O": 0.6,
                "C": 0.5,
                "E": 0.4,
                "A": 0.7,
                "N": 0.3,
                "confidence": {"O": 0.6, "C": 0.5, "E": 0.4, "A": 0.7, "N": 0.3},
            }

        with patch(
            "nikita.api.routes.portal_onboarding.update_big5_vector",
            new=_fake_update_big5,
        ), patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ), patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=AsyncMock(
                return_value=_make_agent_run_result(
                    delta_kind="saturday_morning",
                    delta_data={"saturday_morning": "I run by the river."},
                    reply="ok",
                )
            ),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "saturday_morning",
                    "value": "I run by the river.",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        user_repo.update_big5_vector.assert_awaited_once()
        # Verify NR-05: response body never contains the forbidden terms.
        body_text = response.text.lower()
        for term in FORBIDDEN_TERMS:
            assert term not in body_text, (
                f"NR-05 violation: {term!r} appears in response body."
            )

    def test_non_prose_slot_does_not_trigger_big5(self) -> None:
        app, _ = _make_app()
        agent = MagicMock()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=agent,
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ), patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=AsyncMock(
                return_value=_make_agent_run_result(
                    delta_kind="city",
                    delta_data={"city": "Zurich"},
                    reply="ok",
                )
            ),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "city",
                    "value": "Zurich",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        user_repo.update_big5_vector.assert_not_called()


# ---------------------------------------------------------------------------
# B3: cohort_chips populated only on next=primary_hobbies
# ---------------------------------------------------------------------------


class TestCohortChipsWiring:
    def test_cohort_chips_present_when_next_is_hobbies(self) -> None:
        app, _ = _make_app()
        # Existing profile with city + occupation already filled.
        # Use a known cohort: (zurich, designer) is in the seed table.
        profile = {
            "conversation": [
                {
                    "role": "user",
                    "content": "I'm a designer.",
                    "extracted": {
                        "kind": "occupation",
                        "occupation": "designer",
                    },
                    "slot_kind": "occupation",
                },
                {
                    "role": "user",
                    "content": "Zurich.",
                    "extracted": {"kind": "city", "city": "Zurich"},
                    "slot_kind": "city",
                },
            ]
        }
        user = _make_user(profile=profile)
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=user)
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=MagicMock(),
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ), patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=AsyncMock(
                return_value=_make_agent_run_result(
                    delta_kind="darkness_level",
                    delta_data={"darkness_level": 3},
                    reply="ok",
                    next_slot_kind="primary_hobbies",
                )
            ),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "darkness_level",
                    "value": "3",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        chips = body["output"].get("cohort_chips")
        assert chips is not None, (
            "cohort_chips MUST be populated when next_slot_kind=primary_hobbies."
        )
        assert isinstance(chips, list) and len(chips) > 0
        assert all("value" in c and "label" in c for c in chips)

    def test_cohort_chips_none_when_next_is_other_slot(self) -> None:
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=MagicMock(),
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ), patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=AsyncMock(
                return_value=_make_agent_run_result(
                    delta_kind="city",
                    delta_data={"city": "Zurich"},
                    reply="ok",
                    next_slot_kind="darkness_level",
                )
            ),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "city",
                    "value": "Zurich",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["output"].get("cohort_chips") is None


# ---------------------------------------------------------------------------
# B4: archetype_cards populated only on next=backstory_pick
# ---------------------------------------------------------------------------


class TestArchetypeCardsWiring:
    def test_archetype_cards_populated_on_backstory_pick_via_fallback(self) -> None:
        """When the picker raises, the route falls back to default_archetype_cards."""
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        async def _failing_picker(*args, **kwargs):  # noqa: ANN001, ARG001
            raise RuntimeError("picker failed")

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=MagicMock(),
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ), patch(
            "nikita.api.routes.portal_onboarding.pick_three_archetypes",
            new=_failing_picker,
        ), patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=AsyncMock(
                return_value=_make_agent_run_result(
                    delta_kind="voice_tone_pref",
                    delta_data={"voice_tone_pref": "text"},
                    reply="ok",
                    next_slot_kind="backstory_pick",
                )
            ),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "voice_tone_pref",
                    "value": "text",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        cards = body["output"].get("archetype_cards")
        assert cards is not None, "archetype_cards MUST populate on backstory_pick turn."
        assert len(cards) == 3
        for c in cards:
            assert "label" in c and "prose" in c and "archetype_seed" in c
        user_repo.update_archetype_candidates.assert_awaited_once()

    def test_archetype_cards_none_when_next_is_other(self) -> None:
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        with patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=MagicMock(),
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ), patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=AsyncMock(
                return_value=_make_agent_run_result(
                    delta_kind="city",
                    delta_data={"city": "Zurich"},
                    reply="ok",
                    next_slot_kind="darkness_level",
                )
            ),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "city",
                    "value": "Zurich",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["output"].get("archetype_cards") is None
        user_repo.update_archetype_candidates.assert_not_called()


# ---------------------------------------------------------------------------
# B5: builtin_tools wiring
# ---------------------------------------------------------------------------


class TestBuiltinToolsWiring:
    """Verify run_agent_with_capture receives builtin_tools list."""

    def test_builtin_tools_kwarg_present(self) -> None:
        app, _ = _make_app()
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=_make_user())
        user_repo.update_big5_vector = AsyncMock()
        user_repo.update_archetype_candidates = AsyncMock()

        captured: dict = {}

        async def _capture(*_args, **kwargs):
            captured["builtin_tools"] = kwargs.get("builtin_tools")
            return _make_agent_run_result(
                delta_kind="city", delta_data={"city": "Zurich"}, reply="ok"
            )

        with patch(
            "nikita.api.routes.portal_onboarding.run_agent_with_capture",
            new=_capture,
        ), patch(
            "nikita.api.routes.portal_onboarding.get_conversation_agent",
            return_value=MagicMock(),
        ), patch(
            "nikita.api.routes.portal_onboarding.IdempotencyStore",
            return_value=_bare_idem(),
        ), patch(
            "nikita.api.routes.portal_onboarding.append_conversation_turn",
            AsyncMock(),
        ), patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=user_repo,
        ), patch(
            "nikita.db.repositories.telegram_link_repository.TelegramLinkRepository",
            return_value=_bare_link_repo(),
        ):
            response = _post(
                app,
                {
                    "slot_kind": "city",
                    "value": "Zurich",
                    "turn_id": str(uuid4()),
                },
            )

        assert response.status_code == 200, response.text
        assert "builtin_tools" in captured, (
            "Handler MUST pass builtin_tools= to agent.run / run_agent_with_capture."
        )
        assert isinstance(captured["builtin_tools"], list)
