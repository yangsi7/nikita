"""Tests for Social Circle Integration in Handoff (Spec 035 T2.2).

TDD tests for wiring social circle generation to onboarding handoff.

Note: Social circle generation and pipeline bootstrap run as background
tasks via asyncio.create_task() to avoid Cloud Run timeouts (ONBOARD-TIMEOUT fix).
Tests use asyncio.sleep(0) to yield control and let tasks complete.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.onboarding.handoff import HandoffManager
from nikita.onboarding.models import (
    ConversationStyle,
    PersonalityType,
    UserOnboardingProfile,
)


class TestHandoffSocialCircleGeneration:
    """Tests for social circle generation during handoff."""

    @pytest.fixture
    def profile(self):
        """Create a test profile."""
        return UserOnboardingProfile(
            timezone="Europe/Berlin",
            occupation="Software Engineer",
            hobbies=["music", "gaming"],
            personality_type=PersonalityType.AMBIVERT,
            hangout_spots=["tech_meetup", "coffee_shop"],
            darkness_level=3,
            pacing_weeks=4,
            conversation_style=ConversationStyle.BALANCED,
        )

    @pytest.fixture
    def manager(self):
        """Create a HandoffManager."""
        return HandoffManager()

    @pytest.mark.asyncio
    async def test_execute_handoff_generates_social_circle(
        self, manager, profile
    ):
        """Test that execute_handoff generates a social circle for the user."""
        user_id = uuid4()
        telegram_id = 123456789

        with patch.object(
            manager, "_send_first_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"success": True}

            with patch(
                "nikita.onboarding.handoff.generate_and_store_social_circle",
                new_callable=AsyncMock,
            ) as mock_generate:
                mock_generate.return_value = True

                result = await manager.execute_handoff(
                    user_id=user_id,
                    telegram_id=telegram_id,
                    profile=profile,
                    user_name="TestUser",
                )

                # Let background task complete
                await asyncio.sleep(0)

                # Social circle should be generated
                mock_generate.assert_called_once()
                call_args = mock_generate.call_args
                assert call_args[1]["user_id"] == user_id
                assert call_args[1]["location"] is not None  # timezone used
                assert call_args[1]["hobbies"] == ["music", "gaming"]
                assert call_args[1]["job_field"] == "Software Engineer"

    @pytest.mark.asyncio
    async def test_execute_handoff_extracts_location_from_timezone(
        self, manager, profile
    ):
        """Test that location is extracted from timezone for adaptation."""
        user_id = uuid4()

        with patch.object(
            manager, "_send_first_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"success": True}

            with patch(
                "nikita.onboarding.handoff.generate_and_store_social_circle",
                new_callable=AsyncMock,
            ) as mock_generate:
                mock_generate.return_value = True

                await manager.execute_handoff(
                    user_id=user_id,
                    telegram_id=123456789,
                    profile=UserOnboardingProfile(
                        timezone="America/Los_Angeles",
                        occupation="Designer",
                        hobbies=[],
                    ),
                    user_name="Test",
                )

                # Let background task complete
                await asyncio.sleep(0)

                # Should extract Los Angeles from timezone
                call_args = mock_generate.call_args
                location = call_args[1]["location"]
                assert "Los_Angeles" in location or "los angeles" in location.lower()

    @pytest.mark.asyncio
    async def test_execute_handoff_uses_hangout_spots_for_meeting_context(
        self, manager, profile
    ):
        """Test that hangout spots inform meeting context."""
        user_id = uuid4()

        with patch.object(
            manager, "_send_first_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"success": True}

            with patch(
                "nikita.onboarding.handoff.generate_and_store_social_circle",
                new_callable=AsyncMock,
            ) as mock_generate:
                mock_generate.return_value = True

                await manager.execute_handoff(
                    user_id=user_id,
                    telegram_id=123456789,
                    profile=UserOnboardingProfile(
                        hangout_spots=["club", "party"],
                        hobbies=[],
                    ),
                    user_name="Test",
                )

                # Let background task complete
                await asyncio.sleep(0)

                call_args = mock_generate.call_args
                meeting_context = call_args[1]["meeting_context"]
                assert meeting_context is not None

    @pytest.mark.asyncio
    async def test_execute_handoff_continues_if_social_circle_fails(
        self, manager, profile
    ):
        """Test that handoff continues even if social circle generation fails."""
        user_id = uuid4()

        with patch.object(
            manager, "_send_first_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"success": True}

            with patch(
                "nikita.onboarding.handoff.generate_and_store_social_circle",
                new_callable=AsyncMock,
            ) as mock_generate:
                # Simulate failure
                mock_generate.side_effect = Exception("Database error")

                result = await manager.execute_handoff(
                    user_id=user_id,
                    telegram_id=123456789,
                    profile=profile,
                    user_name="Test",
                )

                # Let background task complete (it catches the exception)
                await asyncio.sleep(0)

                # Handoff should still succeed (social circle is non-blocking)
                assert result.success is True
                assert result.first_message_sent is True

    @pytest.mark.asyncio
    async def test_execute_handoff_logs_social_circle_failure(
        self, manager, profile, caplog
    ):
        """Test that social circle generation failures are logged."""
        user_id = uuid4()

        with patch.object(
            manager, "_send_first_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"success": True}

            with patch(
                "nikita.onboarding.handoff.generate_and_store_social_circle",
                new_callable=AsyncMock,
            ) as mock_generate:
                mock_generate.side_effect = Exception("Test error")

                import logging
                with caplog.at_level(logging.WARNING):
                    await manager.execute_handoff(
                        user_id=user_id,
                        telegram_id=123456789,
                        profile=profile,
                        user_name="Test",
                    )

                    # Let background task complete (logs the warning)
                    await asyncio.sleep(0)

                # Should log warning
                assert any(
                    "social circle" in record.message.lower()
                    for record in caplog.records
                )


class TestGenerateAndStoreSocialCircle:
    """Tests for the generate_and_store_social_circle helper."""

    @pytest.mark.asyncio
    async def test_generate_and_store_creates_db_records(self):
        """Test that social circle is stored in database."""
        from nikita.onboarding.handoff import generate_and_store_social_circle

        user_id = uuid4()

        # Patch inside the function's import location
        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.social_circle_repository.SocialCircleRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.create_circle_for_user = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                with patch(
                    "nikita.life_simulation.social_generator.generate_social_circle_for_user"
                ) as mock_gen:
                    mock_circle = MagicMock()
                    mock_circle.characters = []
                    mock_gen.return_value = mock_circle

                    result = await generate_and_store_social_circle(
                        user_id=user_id,
                        location="Berlin",
                        hobbies=["music"],
                        job_field="Tech",
                        meeting_context="Party",
                    )

                    # Verify result
                    assert result is True

                    # Verify generation was called
                    mock_gen.assert_called_once_with(
                        user_id=user_id,
                        location="Berlin",
                        hobbies=["music"],
                        job_field="Tech",
                        meeting_context="Party",
                    )

    @pytest.mark.asyncio
    async def test_generate_and_store_commits_transaction(self):
        """Test that database transaction is committed."""
        from nikita.onboarding.handoff import generate_and_store_social_circle

        user_id = uuid4()

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.social_circle_repository.SocialCircleRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.create_circle_for_user = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                with patch(
                    "nikita.life_simulation.social_generator.generate_social_circle_for_user"
                ) as mock_gen:
                    mock_circle = MagicMock()
                    mock_circle.characters = []
                    mock_gen.return_value = mock_circle

                    await generate_and_store_social_circle(
                        user_id=user_id,
                        location="Berlin",
                    )

                    # Verify commit was called
                    mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_and_store_logs_error_with_traceback(self, caplog):
        """AC-2.1.1: Exception handler logs error with exc_info=True for full traceback (Spec 036)."""
        import logging
        from nikita.onboarding.handoff import generate_and_store_social_circle

        user_id = uuid4()

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.life_simulation.social_generator.generate_social_circle_for_user"
            ) as mock_gen:
                # Simulate error during generation
                mock_gen.side_effect = ValueError("Test database error")

                with caplog.at_level(logging.ERROR):
                    result = await generate_and_store_social_circle(
                        user_id=user_id,
                        location="Berlin",
                    )

                    # Should return False but not crash
                    assert result is False

                    # Should log error with user_id context
                    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
                    assert len(error_records) > 0
                    error_msg = error_records[0].message
                    assert str(user_id) in error_msg or "social circle" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_successful_generation_still_works(self):
        """AC-2.1.4: Successful generation still works after error handling changes (Spec 036)."""
        from nikita.onboarding.handoff import generate_and_store_social_circle

        user_id = uuid4()

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.social_circle_repository.SocialCircleRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.create_circle_for_user = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                with patch(
                    "nikita.life_simulation.social_generator.generate_social_circle_for_user"
                ) as mock_gen:
                    mock_circle = MagicMock()
                    mock_circle.characters = [MagicMock(), MagicMock()]
                    mock_gen.return_value = mock_circle

                    result = await generate_and_store_social_circle(
                        user_id=user_id,
                        location="Berlin",
                        hobbies=["music"],
                    )

                    # Should succeed
                    assert result is True
