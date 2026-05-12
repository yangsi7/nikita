r"""Spec 218 Slice 218-4 — persist + DAG invalidation for chip_multi + phone + voice_or_text.

Per ``specs/218-onboarding-wizard-v2-agent-driven/subspecs/4/slice.md``.

New slot persistence in slice 218-4:
  primary_hobbies     -> list[str] with 1-5 non-empty items
  hangouts_personalized -> list[str] with 1-5 non-empty items
  voice_or_text       -> str in {"voice", "text"}
  phone               -> E.164 str matching ``^\+[1-9]\d{6,14}$``

FR-007 DAG wiring:
  - voice_or_text="text" -> phone added to invalidated (dropped from required)
  - voice_or_text="voice" -> phone NOT invalidated

RED phase: tests fail until PR-218-4 implementation lands.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_retry_counts():
    """Clear ``_retry_counts`` between tests — defense-in-depth per slice-218-3 pattern."""
    from nikita.api.routes import portal_onboarding_v2  # noqa: PLC0415

    portal_onboarding_v2._retry_counts.clear()
    yield
    portal_onboarding_v2._retry_counts.clear()


# ---------------------------------------------------------------------------
# primary_hobbies persistence
# ---------------------------------------------------------------------------


class TestPrimaryHobbiesPersist:
    """handle_v2_answer persists primary_hobbies as list[str]."""

    @pytest.mark.asyncio
    async def test_primary_hobbies_submit_persists_list(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "primary_hobbies"
        req.value = ["music", "sports", "travel"]

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    ChipMultiAsk,
                    Option,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=ChipMultiAsk(
                            component="chip_multi",
                            slot="hangouts_personalized",
                            prompt="Which spots?",
                            options=[
                                Option(value="berghain", label="Berghain"),
                                Option(value="kitkat", label="KitKat"),
                                Option(value="tresor", label="Tresor"),
                            ],
                            min_pick=1,
                            max_pick=3,
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates is not None
                assert "slots" in updates
                hobbies_slot = updates["slots"].get("primary_hobbies")
                assert hobbies_slot is not None
                assert hobbies_slot["primary_hobbies"] == ["music", "sports", "travel"]
                assert envelope.component == "chip_multi"

    @pytest.mark.asyncio
    async def test_primary_hobbies_empty_list_no_ops(self) -> None:
        """Empty list is malformed -> no persistence call -> re-ask same target."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "primary_hobbies"
        req.value = []

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    ChipMultiAsk,
                    Option,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=ChipMultiAsk(
                            component="chip_multi",
                            slot="primary_hobbies",
                            prompt="What are your hobbies?",
                            options=[
                                Option(value="music", label="Music"),
                                Option(value="sports", label="Sports"),
                            ],
                            min_pick=1,
                            max_pick=2,
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                # Empty list rejected -> no persist
                repo.update_onboarding_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_primary_hobbies_more_than_five_items_no_ops(self) -> None:
        """chip_multi with > 5 items is rejected (cap = 5)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "primary_hobbies"
        req.value = ["a", "b", "c", "d", "e", "f"]  # 6 items > cap 5

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    ChipMultiAsk,
                    Option,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=ChipMultiAsk(
                            component="chip_multi",
                            slot="primary_hobbies",
                            prompt="What are your hobbies?",
                            options=[
                                Option(value="music", label="Music"),
                                Option(value="sports", label="Sports"),
                            ],
                            min_pick=1,
                            max_pick=2,
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_not_awaited()


    @pytest.mark.asyncio
    async def test_primary_hobbies_whitespace_padded_items_stripped(self) -> None:
        """Whitespace-padded chip entries are stripped before persist (QA iter-3)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "primary_hobbies"
        req.value = ["  music  ", "sports ", " travel", "   "]  # last is whitespace-only

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    ChipMultiAsk,
                    Option,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=ChipMultiAsk(
                            component="chip_multi",
                            slot="hangouts_personalized",
                            prompt="Which spots?",
                            options=[
                                Option(value="berghain", label="Berghain"),
                                Option(value="kitkat", label="KitKat"),
                                Option(value="tresor", label="Tresor"),
                            ],
                            min_pick=1,
                            max_pick=3,
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)

                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                hobbies_slot = updates["slots"].get("primary_hobbies")
                # Whitespace-only item dropped; surviving items stripped.
                assert hobbies_slot["primary_hobbies"] == ["music", "sports", "travel"]


# ---------------------------------------------------------------------------
# voice_or_text persistence + FR-007 DAG
# ---------------------------------------------------------------------------


class TestVoiceOrTextPersistAndInvalidation:
    """voice_or_text submit persists correctly; voice_or_text='text' invalidates phone."""

    @pytest.mark.asyncio
    async def test_voice_or_text_voice_persists_and_does_not_invalidate_phone(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "voice_or_text"
        req.value = "voice"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import PhoneAsk  # noqa: PLC0415

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=PhoneAsk(
                            component="phone",
                            slot="phone",
                            prompt="What's your number?",
                        )
                    )
                )

                envelope = await handle_v2_answer(req, mock_user, mock_session)

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates is not None
                assert updates["slots"]["voice_or_text"] == {"voice_or_text": "voice"}
                # phone NOT in invalidated when voice selected
                invalidated = updates.get("invalidated", [])
                assert "phone" not in invalidated
                assert envelope.component == "phone"

    @pytest.mark.asyncio
    async def test_voice_or_text_text_invalidates_phone(self) -> None:
        """voice_or_text='text' triggers FR-007: phone dependency invalidated."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
                # phone was previously filled (user previously chose voice)
                "phone": {"phone": "+14155550100"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "voice_or_text"
        req.value = "text"

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

                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates is not None
                assert updates["slots"]["voice_or_text"] == {"voice_or_text": "text"}
                # phone MUST be invalidated when user flips to text
                assert "phone" in (updates.get("invalidated") or [])
                # phone slot must be popped from merged_slots
                assert "phone" not in updates["slots"]
                assert envelope.component == "handler_handoff"
                assert envelope.handler == "v1"

    @pytest.mark.asyncio
    async def test_voice_or_text_invalid_value_no_ops(self) -> None:
        """voice_or_text='carrier_pigeon' is not in {'voice','text'} -> no persist."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "voice_or_text"
        req.value = "carrier_pigeon"

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
                            slot="voice_or_text",
                            prompt="Voice or text?",
                            options=[
                                Option(value="voice", label="Voice"),
                                Option(value="text", label="Text"),
                            ],
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_not_awaited()


# ---------------------------------------------------------------------------
# phone persistence
# ---------------------------------------------------------------------------


class TestPhonePersist:
    """handle_v2_answer persists phone as E.164 string."""

    @pytest.mark.asyncio
    async def test_phone_valid_e164_persists(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
                "voice_or_text": {"voice_or_text": "voice"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "phone"
        req.value = "+14155550100"

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

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates is not None
                assert updates["slots"]["phone"] == {"phone": "+14155550100"}

    @pytest.mark.asyncio
    async def test_phone_invalid_no_plus_no_ops(self) -> None:
        """Phone without '+' prefix is not E.164 -> no persist."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
                "voice_or_text": {"voice_or_text": "voice"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "phone"
        req.value = "14155550100"  # no + prefix

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import PhoneAsk  # noqa: PLC0415

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=PhoneAsk(
                            component="phone",
                            slot="phone",
                            prompt="What's your number?",
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_phone_too_short_no_ops(self) -> None:
        """E.164 requires 7+ digits after country code; +123 is too short."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
                "voice_or_text": {"voice_or_text": "voice"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "phone"
        req.value = "+123"  # too short

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import PhoneAsk  # noqa: PLC0415

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=PhoneAsk(
                            component="phone",
                            slot="phone",
                            prompt="What's your number?",
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)
                repo.update_onboarding_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_phone_valid_e164_minimum_length_persists(self) -> None:
        """E.164 minimum: +1234567 (7 digits after country code prefix)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {
                "display_name": {"display_name": "Sam"},
                "age": {"age": 28, "dob": "1998-04-12"},
                "city": {"city": "berlin"},
                "occupation": {"occupation": "engineer"},
                "primary_hobbies": {"primary_hobbies": ["music"]},
                "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
                "voice_or_text": {"voice_or_text": "voice"},
            },
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "phone"
        req.value = "+1234567"  # 7 total digits, minimum E.164

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

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates is not None
                assert updates["slots"]["phone"]["phone"] == "+1234567"
