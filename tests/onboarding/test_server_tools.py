"""Phase C: Server Tools tests (Spec 028).

Tests for onboarding server tool handlers used by Meta-Nikita during calls.

Implements:
- AC-T009.1-4: collect_profile server tool
- AC-T010.1-4: configure_preferences server tool
- AC-T011.1-4: complete_onboarding server tool
- AC-T012.1-2: Coverage tests
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.models import (
    ConversationStyle,
    OnboardingStatus,
    PersonalityType,
    UserOnboardingProfile,
)
from nikita.onboarding.server_tools import (
    OnboardingServerToolHandler,
    OnboardingToolRequest,
    OnboardingToolResponse,
)


class TestOnboardingToolRequest:
    """Tests for OnboardingToolRequest model."""

    def test_request_with_field_name_value(self) -> None:
        """AC-T009.2: Accepts field_name and value."""
        request = OnboardingToolRequest(
            tool_name="collect_profile",
            user_id=str(uuid4()),
            parameters={"field_name": "timezone", "value": "America/New_York"},
        )
        assert request.tool_name == "collect_profile"
        assert request.parameters["field_name"] == "timezone"

    def test_request_with_preferences(self) -> None:
        """AC-T010.2: Accepts preference parameters."""
        request = OnboardingToolRequest(
            tool_name="configure_preferences",
            user_id=str(uuid4()),
            parameters={
                "darkness_level": 3,
                "pacing_weeks": 4,
                "conversation_style": "balanced",
            },
        )
        assert request.parameters["darkness_level"] == 3

    def test_request_complete_onboarding(self) -> None:
        """AC-T011.1: complete_onboarding request."""
        request = OnboardingToolRequest(
            tool_name="complete_onboarding",
            user_id=str(uuid4()),
            parameters={"notes": "Smooth onboarding call"},
        )
        assert request.tool_name == "complete_onboarding"


class TestOnboardingToolResponse:
    """Tests for OnboardingToolResponse model."""

    def test_success_response(self) -> None:
        """Response indicates success."""
        response = OnboardingToolResponse(success=True, message="Profile updated")
        assert response.success is True

    def test_error_response(self) -> None:
        """Response indicates error."""
        response = OnboardingToolResponse(
            success=False, error="Invalid field name"
        )
        assert response.success is False
        assert response.error is not None

    def test_response_with_data(self) -> None:
        """Response can include data."""
        response = OnboardingToolResponse(
            success=True,
            message="Preferences configured",
            data={"darkness_level": 3},
        )
        assert response.data is not None


class TestOnboardingServerToolHandler:
    """Tests for OnboardingServerToolHandler class."""

    @pytest.fixture
    def handler(self) -> OnboardingServerToolHandler:
        """Create handler with mocked dependencies."""
        return OnboardingServerToolHandler()

    @pytest.fixture
    def mock_user_repo(self) -> MagicMock:
        """Mock user repository."""
        return MagicMock()


class TestCollectProfile:
    """Tests for collect_profile server tool (T009)."""

    @pytest.fixture
    def handler(self) -> OnboardingServerToolHandler:
        """Create handler."""
        return OnboardingServerToolHandler()

    @pytest.mark.asyncio
    async def test_collect_timezone(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Stores timezone correctly."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                mock_save.return_value = None

                response = await handler.collect_profile(
                    user_id=user_id,
                    field_name="timezone",
                    value="America/New_York",
                )

        assert response.success is True
        assert mock_profile.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_collect_occupation(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Stores occupation correctly."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.collect_profile(
                    user_id=user_id,
                    field_name="occupation",
                    value="Software Engineer",
                )

        assert response.success is True
        assert mock_profile.occupation == "Software Engineer"

    @pytest.mark.asyncio
    async def test_collect_hobbies_single(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Stores single hobby correctly."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.collect_profile(
                    user_id=user_id,
                    field_name="hobbies",
                    value="gaming",
                )

        assert response.success is True
        assert "gaming" in mock_profile.hobbies

    @pytest.mark.asyncio
    async def test_collect_hobbies_multiple(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Stores multiple hobbies from comma-separated."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.collect_profile(
                    user_id=user_id,
                    field_name="hobbies",
                    value="gaming, reading, hiking",
                )

        assert response.success is True
        assert len(mock_profile.hobbies) == 3

    @pytest.mark.asyncio
    async def test_collect_personality_type(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Stores personality type correctly."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.collect_profile(
                    user_id=user_id,
                    field_name="personality_type",
                    value="introvert",
                )

        assert response.success is True
        assert mock_profile.personality_type == PersonalityType.INTROVERT

    @pytest.mark.asyncio
    async def test_collect_hangout_spots(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Stores hangout spots correctly."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.collect_profile(
                    user_id=user_id,
                    field_name="hangout_spots",
                    value="coffee shops, bookstores",
                )

        assert response.success is True
        assert len(mock_profile.hangout_spots) == 2

    @pytest.mark.asyncio
    async def test_collect_invalid_field(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T009.3: Rejects invalid field names."""
        user_id = uuid4()

        response = await handler.collect_profile(
            user_id=user_id,
            field_name="invalid_field",
            value="some value",
        )

        assert response.success is False
        assert "invalid" in response.error.lower()


class TestConfigurePreferences:
    """Tests for configure_preferences server tool (T010)."""

    @pytest.fixture
    def handler(self) -> OnboardingServerToolHandler:
        """Create handler."""
        return OnboardingServerToolHandler()

    @pytest.mark.asyncio
    async def test_configure_darkness_level(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.2: Accepts darkness_level."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.configure_preferences(
                    user_id=user_id,
                    darkness_level=4,
                )

        assert response.success is True
        assert mock_profile.darkness_level == 4

    @pytest.mark.asyncio
    async def test_configure_pacing_4_weeks(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.2: Accepts pacing_weeks=4."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.configure_preferences(
                    user_id=user_id,
                    pacing_weeks=4,
                )

        assert response.success is True
        assert mock_profile.pacing_weeks == 4

    @pytest.mark.asyncio
    async def test_configure_pacing_8_weeks(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.2: Accepts pacing_weeks=8."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.configure_preferences(
                    user_id=user_id,
                    pacing_weeks=8,
                )

        assert response.success is True
        assert mock_profile.pacing_weeks == 8

    @pytest.mark.asyncio
    async def test_configure_conversation_style(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.2: Accepts conversation_style."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.configure_preferences(
                    user_id=user_id,
                    conversation_style="listener",
                )

        assert response.success is True
        assert mock_profile.conversation_style == ConversationStyle.LISTENER

    @pytest.mark.asyncio
    async def test_configure_multiple_preferences(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.2: Accepts multiple preferences at once."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch.object(handler, '_persist_profile_to_db') as mock_save:
                response = await handler.configure_preferences(
                    user_id=user_id,
                    darkness_level=5,
                    pacing_weeks=8,
                    conversation_style="sharer",
                )

        assert response.success is True
        assert mock_profile.darkness_level == 5
        assert mock_profile.pacing_weeks == 8
        assert mock_profile.conversation_style == ConversationStyle.SHARER

    @pytest.mark.asyncio
    async def test_configure_darkness_level_invalid_low(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.3: Validates darkness_level >= 1."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            response = await handler.configure_preferences(
                user_id=user_id,
                darkness_level=0,
            )

        assert response.success is False

    @pytest.mark.asyncio
    async def test_configure_darkness_level_invalid_high(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.3: Validates darkness_level <= 5."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            response = await handler.configure_preferences(
                user_id=user_id,
                darkness_level=6,
            )

        assert response.success is False

    @pytest.mark.asyncio
    async def test_configure_pacing_invalid(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T010.3: Validates pacing_weeks in {4, 8}."""
        user_id = uuid4()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            response = await handler.configure_preferences(
                user_id=user_id,
                pacing_weeks=6,
            )

        assert response.success is False


class TestCompleteOnboarding:
    """Tests for complete_onboarding server tool (T011)."""

    @pytest.fixture
    def handler(self) -> OnboardingServerToolHandler:
        """Create handler."""
        return OnboardingServerToolHandler()

    @pytest.mark.asyncio
    async def test_complete_sets_onboarded_at(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T011.2: Marks user as onboarded with timestamp."""
        user_id = uuid4()
        call_id = "call_123"

        # Mock the database interactions
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.complete_onboarding = AsyncMock()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch('nikita.onboarding.server_tools.get_session_maker') as mock_get_session:
                mock_get_session.return_value.return_value = mock_session

                with patch('nikita.onboarding.server_tools.UserRepository') as mock_repo_class:
                    mock_repo_class.return_value = mock_user_repo

                    with patch.object(handler, '_trigger_handoff') as mock_handoff:
                        mock_handoff.return_value = None

                        response = await handler.complete_onboarding(
                            user_id=user_id,
                            call_id=call_id,
                        )

        assert response.success is True
        # Verify complete_onboarding was called on the repo
        mock_user_repo.complete_onboarding.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_triggers_handoff(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T011.3: Triggers handoff process."""
        user_id = uuid4()

        # Mock the database interactions
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.complete_onboarding = AsyncMock()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch('nikita.onboarding.server_tools.get_session_maker') as mock_get_session:
                mock_get_session.return_value.return_value = mock_session

                with patch('nikita.onboarding.server_tools.UserRepository') as mock_repo_class:
                    mock_repo_class.return_value = mock_user_repo

                    with patch.object(handler, '_trigger_handoff') as mock_handoff:
                        mock_handoff.return_value = None

                        response = await handler.complete_onboarding(
                            user_id=user_id,
                            call_id="call_456",
                        )

        # Verify handoff was triggered
        mock_handoff.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_with_notes(self, handler: OnboardingServerToolHandler) -> None:
        """AC-T011.1: Accepts optional notes."""
        user_id = uuid4()

        # Mock the database interactions
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.complete_onboarding = AsyncMock()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile()
            mock_get.return_value = mock_profile

            with patch('nikita.onboarding.server_tools.get_session_maker') as mock_get_session:
                mock_get_session.return_value.return_value = mock_session

                with patch('nikita.onboarding.server_tools.UserRepository') as mock_repo_class:
                    mock_repo_class.return_value = mock_user_repo

                    with patch.object(handler, '_trigger_handoff') as mock_handoff:
                        response = await handler.complete_onboarding(
                            user_id=user_id,
                            call_id="call_789",
                            notes="User was excited to start",
                        )

        assert response.success is True

    @pytest.mark.asyncio
    async def test_complete_returns_summary(self, handler: OnboardingServerToolHandler) -> None:
        """Response includes profile summary."""
        user_id = uuid4()

        # Mock the database interactions
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()

        mock_user_repo = MagicMock()
        mock_user_repo.complete_onboarding = AsyncMock()

        with patch.object(handler, '_get_or_create_profile') as mock_get:
            mock_profile = UserOnboardingProfile(
                timezone="America/New_York",
                occupation="Engineer",
                darkness_level=3,
                pacing_weeks=4,
            )
            mock_get.return_value = mock_profile

            with patch('nikita.onboarding.server_tools.get_session_maker') as mock_get_session:
                mock_get_session.return_value.return_value = mock_session

                with patch('nikita.onboarding.server_tools.UserRepository') as mock_repo_class:
                    mock_repo_class.return_value = mock_user_repo

                    with patch.object(handler, '_trigger_handoff') as mock_handoff:
                        response = await handler.complete_onboarding(
                            user_id=user_id,
                            call_id="call_abc",
                        )

        assert response.success is True
        assert response.data is not None
        assert "profile" in response.data


class TestHandleRequest:
    """Tests for general request handling."""

    @pytest.fixture
    def handler(self) -> OnboardingServerToolHandler:
        """Create handler."""
        return OnboardingServerToolHandler()

    @pytest.mark.asyncio
    async def test_handle_collect_profile_request(self, handler: OnboardingServerToolHandler) -> None:
        """Routes collect_profile requests correctly."""
        request = OnboardingToolRequest(
            tool_name="collect_profile",
            user_id=str(uuid4()),
            parameters={"field_name": "timezone", "value": "UTC"},
        )

        with patch.object(handler, 'collect_profile', new_callable=AsyncMock) as mock:
            mock.return_value = OnboardingToolResponse(success=True)
            response = await handler.handle_request(request)

        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_configure_preferences_request(self, handler: OnboardingServerToolHandler) -> None:
        """Routes configure_preferences requests correctly."""
        request = OnboardingToolRequest(
            tool_name="configure_preferences",
            user_id=str(uuid4()),
            parameters={"darkness_level": 3},
        )

        with patch.object(handler, 'configure_preferences', new_callable=AsyncMock) as mock:
            mock.return_value = OnboardingToolResponse(success=True)
            response = await handler.handle_request(request)

        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_complete_onboarding_request(self, handler: OnboardingServerToolHandler) -> None:
        """Routes complete_onboarding requests correctly."""
        request = OnboardingToolRequest(
            tool_name="complete_onboarding",
            user_id=str(uuid4()),
            parameters={"call_id": "test_call"},
        )

        with patch.object(handler, 'complete_onboarding', new_callable=AsyncMock) as mock:
            mock.return_value = OnboardingToolResponse(success=True)
            response = await handler.handle_request(request)

        mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, handler: OnboardingServerToolHandler) -> None:
        """Returns error for unknown tool."""
        request = OnboardingToolRequest(
            tool_name="unknown_tool",
            user_id=str(uuid4()),
            parameters={},
        )

        response = await handler.handle_request(request)
        assert response.success is False
        assert "unknown" in response.error.lower()
