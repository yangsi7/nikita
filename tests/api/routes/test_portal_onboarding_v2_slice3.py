"""Spec 218 Slice 218-3 — apply-prior-submission + persist + 3 new slot shapes.

Per `specs/218-onboarding-wizard-v2-agent-driven/subspecs/3/slice.md` +
`docs-to-process/20260512-handover-spec-218-PR2-shipped.md` §3.

RED phase: imports + behavior absent on master commit 01922be.
Verifies that PR-218-3 closes the slice-218-2 persist gap AND lands the
4-slot v2 coverage (display_name, age, city, occupation).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


# ---------------------------------------------------------------------------
# Slice-218-2 persist gap fix — display_name advance
# ---------------------------------------------------------------------------


class TestApplyPriorSubmissionPersistsAndAdvances:
    """`handle_v2_answer` MUST apply req.slot_kind+value to slots and
    persist before picking next target. Slice 218-2 shipped this surface
    without the apply step; slice 218-3 closes the gap.
    """

    @pytest.mark.asyncio
    async def test_display_name_submit_persists_and_advances_to_age(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        # Empty profile -> slots empty -> first target was display_name.
        mock_user.onboarding_profile = {}

        # req simulates "user just typed 'Sam' for display_name slot".
        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "display_name"
        req.value = "Sam"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                # Agent emits CalendarAsk for age (the next target).
                agent = mock_agent_getter.return_value
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    CalendarAsk,
                )

                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=CalendarAsk(
                            component="calendar",
                            slot="age",
                            prompt="When were you born?",
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)

                # Persisted display_name into slots payload.
                repo.update_onboarding_profile.assert_awaited_once()
                kwargs = repo.update_onboarding_profile.await_args.kwargs
                args = repo.update_onboarding_profile.await_args.args
                # Match either positional or kwargs call shape.
                updates = kwargs.get("profile_updates")
                if updates is None and len(args) >= 2:
                    updates = args[1]
                assert updates is not None, "update_onboarding_profile invoked with no updates"
                assert "slots" in updates
                assert updates["slots"].get("display_name") == {"display_name": "Sam"}

                # Agent emitted for age target -> CalendarAsk envelope.
                assert envelope.component == "calendar"
                assert envelope.slot == "age"

    @pytest.mark.asyncio
    async def test_age_calendar_submit_persists_age_int_and_dob(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {"display_name": {"display_name": "Sam"}},
        }

        # DoB 1998-04-12; age computed as today.year - 1998 - (today<04/12 ? 1 : 0)
        dob_iso = "1998-04-12"
        today = date.today()
        expected_age = today.year - 1998 - (
            (today.month, today.day) < (4, 12)
        )

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "age"
        req.value = dob_iso

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    Option,
                    SingleSelectAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=SingleSelectAsk(
                            component="single_select",
                            slot="city",
                            prompt="Which city are you in?",
                            options=[
                                Option(value="berlin", label="Berlin"),
                                Option(value="nyc", label="NYC"),
                            ],
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)

                repo.update_onboarding_profile.assert_awaited_once()
                kwargs = repo.update_onboarding_profile.await_args.kwargs
                args = repo.update_onboarding_profile.await_args.args
                updates = kwargs.get("profile_updates") or (args[1] if len(args) >= 2 else None)
                assert updates is not None
                age_slot = updates["slots"]["age"]
                assert age_slot["age"] == expected_age
                assert age_slot["dob"] == dob_iso
                assert envelope.slot == "city"

    @pytest.mark.asyncio
    async def test_city_select_submit_persists_and_advances_to_occupation(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "city"
        req.value = "berlin"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    TextShortAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=TextShortAsk(
                            component="text_short",
                            slot="occupation",
                            prompt="What do you do?",
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_awaited_once()
                kwargs = repo.update_onboarding_profile.await_args.kwargs
                args = repo.update_onboarding_profile.await_args.args
                updates = kwargs.get("profile_updates") or (args[1] if len(args) >= 2 else None)
                assert updates is not None
                assert updates["slots"]["city"] == {"city": "berlin"}
                assert envelope.slot == "occupation"

    @pytest.mark.asyncio
    async def test_occupation_submit_persists_then_advances_to_handoff(self) -> None:
        """After 4 covered slots filled, next target is primary_hobbies
        which is NOT in slice-218-3 coverage -> HandlerHandoffAsk.
        """
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "occupation"
        req.value = "engineer"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    HandlerHandoffAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=HandlerHandoffAsk(
                            component="handler_handoff",
                            handler="v1",
                            next_url="/api/v1/converse/onboarding",
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_awaited_once()
                assert envelope.component == "handler_handoff"
                assert envelope.handler == "v1"

    @pytest.mark.asyncio
    async def test_apply_request_ignores_unknown_slot_kind(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {}

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "totally_unknown_slot"
        req.value = "anything"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    TextShortAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=TextShortAsk(
                            component="text_short",
                            slot="display_name",
                            prompt="?",
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                # No persistence call — unknown slot_kind silently ignored.
                repo.update_onboarding_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_apply_request_rejects_dob_equal_today(self) -> None:
        """DoB == today yields age=0, which is rejected as nonsensical."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {"display_name": {"display_name": "Sam"}},
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "age"
        req.value = date.today().isoformat()

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    CalendarAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=CalendarAsk(
                            component="calendar",
                            slot="age",
                            prompt="When were you born?",
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_not_awaited()
                # Re-asks age — DoB=today silently rejected.
                assert envelope.slot == "age"

    @pytest.mark.asyncio
    async def test_apply_request_handles_leap_day_dob(self) -> None:
        """DoB Feb 29 on a leap year parses + computes age correctly."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {"display_name": {"display_name": "Sam"}},
        }

        dob_iso = "2000-02-29"
        today = date.today()
        expected_age = today.year - 2000 - (
            (today.month, today.day) < (2, 29)
        )

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "age"
        req.value = dob_iso

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    Option,
                    SingleSelectAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=SingleSelectAsk(
                            component="single_select",
                            slot="city",
                            prompt="Which city?",
                            options=[
                                Option(value="berlin", label="Berlin"),
                                Option(value="nyc", label="NYC"),
                            ],
                        )
                    )
                )
                await handle_v2_answer(req, mock_user, mock_session)
                kwargs = repo.update_onboarding_profile.await_args.kwargs
                args = repo.update_onboarding_profile.await_args.args
                updates = kwargs.get("profile_updates") or (args[1] if len(args) >= 2 else None)
                assert updates is not None
                assert updates["slots"]["age"]["age"] == expected_age
                assert updates["slots"]["age"]["dob"] == dob_iso

    @pytest.mark.asyncio
    async def test_apply_request_invalidates_downstream_when_re_editing_city(self) -> None:
        """Re-editing city when hangouts already filled MUST null hangouts
        and surface ``invalidated: [hangouts_personalized]`` in JSONB
        update payload per FR-007 DAG invalidation.
        """
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        # Hangouts pre-filled (slice-218-4 scenario simulated here to
        # gate FR-007 wiring inside slice-218-3 helper).
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "city"
        req.value = "nyc"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    HandlerHandoffAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=HandlerHandoffAsk(
                            component="handler_handoff",
                            handler="v1",
                            next_url="/api/v1/converse/onboarding",
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                kwargs = repo.update_onboarding_profile.await_args.kwargs
                args = repo.update_onboarding_profile.await_args.args
                updates = kwargs.get("profile_updates") or (args[1] if len(args) >= 2 else None)
                assert updates is not None
                assert updates["slots"]["city"] == {"city": "nyc"}
                # Hangouts null-ed out per FR-007.
                assert "hangouts_personalized" not in updates["slots"]
                assert updates.get("invalidated") == ["hangouts_personalized"]

    @pytest.mark.asyncio
    async def test_apply_request_ignores_malformed_dob_string(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {"display_name": {"display_name": "Sam"}},
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "age"
        req.value = "this is not a date"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    CalendarAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=CalendarAsk(
                            component="calendar",
                            slot="age",
                            prompt="When were you born?",
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_not_awaited()
                # Re-asks age — target unchanged.
                assert envelope.slot == "age"
