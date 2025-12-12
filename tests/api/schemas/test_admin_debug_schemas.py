"""Tests for admin debug portal schemas.

TDD tests for T1.6: Create Admin Debug Schemas

Acceptance Criteria:
- SystemOverviewResponse schema defined
- UserListResponse schema defined
- UserDetailResponse schema defined
- JobStatusResponse schema defined
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from nikita.api.schemas.admin_debug import (
    ActiveUserCounts,
    ChapterDistribution,
    ChapterStateInfo,
    EngagementDistribution,
    EngagementStateInfo,
    GameStatusDistribution,
    JobExecutionStatus,
    JobStatusResponse,
    StateMachinesResponse,
    SystemOverviewResponse,
    UserDetailResponse,
    UserListItem,
    UserListResponse,
    UserNextActions,
    UserTimingInfo,
    ViceInfo,
    ViceProfileInfo,
)


class TestSystemOverviewResponse:
    """Test SystemOverviewResponse schema."""

    def test_system_overview_response_defined(self):
        """SystemOverviewResponse schema is defined."""
        response = SystemOverviewResponse(
            total_users=100,
            game_status=GameStatusDistribution(
                active=80, boss_fight=10, game_over=5, won=5
            ),
            chapters=ChapterDistribution(
                chapter_1=20, chapter_2=30, chapter_3=25, chapter_4=15, chapter_5=10
            ),
            engagement_states=EngagementDistribution(
                calibrating=15,
                in_zone=40,
                drifting=20,
                clingy=10,
                distant=10,
                out_of_zone=5,
            ),
            active_users=ActiveUserCounts(last_24h=50, last_7d=80, last_30d=95),
        )
        assert response.total_users == 100
        assert response.game_status.active == 80
        assert response.chapters.chapter_1 == 20
        assert response.engagement_states.in_zone == 40
        assert response.active_users.last_24h == 50


class TestUserListResponse:
    """Test UserListResponse schema."""

    def test_user_list_response_defined(self):
        """UserListResponse schema is defined."""
        response = UserListResponse(
            users=[
                UserListItem(
                    id=uuid4(),
                    telegram_id=12345,
                    email="user@example.com",
                    relationship_score=75.5,
                    chapter=3,
                    engagement_state="in_zone",
                    game_status="active",
                    last_interaction_at=datetime.now(UTC),
                    created_at=datetime.now(UTC),
                )
            ],
            total_count=1,
            page=1,
            page_size=50,
        )
        assert response.total_count == 1
        assert len(response.users) == 1
        assert response.users[0].chapter == 3


class TestUserDetailResponse:
    """Test UserDetailResponse schema."""

    def test_user_detail_response_defined(self):
        """UserDetailResponse schema is defined."""
        now = datetime.now(UTC)
        response = UserDetailResponse(
            id=uuid4(),
            telegram_id=12345,
            email="user@example.com",
            phone=None,
            relationship_score=75.5,
            chapter=3,
            chapter_name="Honeymoon",
            boss_attempts=1,
            days_played=15,
            game_status="active",
            timing=UserTimingInfo(
                grace_period_remaining_hours=5.5,
                is_in_grace_period=True,
                decay_rate_per_hour=0.5,
                hours_since_last_interaction=2.3,
                next_decay_at=now,
                boss_ready=False,
                boss_attempts_remaining=2,
            ),
            next_actions=UserNextActions(
                should_decay=False,
                decay_due_at=now,
                can_trigger_boss=False,
                boss_threshold=65.0,
                score_to_boss=10.5,
            ),
            created_at=now,
            updated_at=now,
            last_interaction_at=now,
        )
        assert response.chapter == 3
        assert response.timing.grace_period_remaining_hours == 5.5
        assert response.next_actions.boss_threshold == 65.0


class TestJobStatusResponse:
    """Test JobStatusResponse schema."""

    def test_job_status_response_defined(self):
        """JobStatusResponse schema is defined."""
        response = JobStatusResponse(
            jobs=[
                JobExecutionStatus(
                    job_name="decay",
                    last_run_at=datetime.now(UTC),
                    last_status="completed",
                    last_duration_ms=1500,
                    last_result={"users_processed": 50},
                    runs_24h=24,
                    failures_24h=0,
                ),
                JobExecutionStatus(
                    job_name="deliver",
                    last_run_at=datetime.now(UTC),
                    last_status="completed",
                    last_duration_ms=3000,
                    runs_24h=24,
                    failures_24h=1,
                ),
            ],
            recent_failures=[],
        )
        assert len(response.jobs) == 2
        assert response.jobs[0].job_name == "decay"
        assert response.jobs[1].failures_24h == 1


class TestStateMachinesResponse:
    """Test StateMachinesResponse schema."""

    def test_state_machines_response_defined(self):
        """StateMachinesResponse schema is defined."""
        response = StateMachinesResponse(
            user_id=uuid4(),
            engagement=EngagementStateInfo(
                current_state="in_zone",
                multiplier=1.0,
                calibration_score=0.85,
                consecutive_in_zone=5,
                consecutive_clingy_days=0,
                consecutive_distant_days=0,
                recent_transitions=[
                    {
                        "from_state": "drifting",
                        "to_state": "in_zone",
                        "reason": "Good interaction",
                    }
                ],
            ),
            chapter=ChapterStateInfo(
                current_chapter=3,
                chapter_name="Honeymoon",
                boss_threshold=65.0,
                current_score=60.0,
                progress_to_boss=92.3,
                boss_attempts=0,
                can_trigger_boss=False,
            ),
            vice_profile=ViceProfileInfo(
                top_vices=[
                    ViceInfo(
                        category="playful_teasing",
                        intensity_level=3,
                        engagement_score=85.0,
                        discovered_at=datetime.now(UTC),
                    )
                ],
                total_vices_discovered=3,
                expression_level="moderate",
            ),
        )
        assert response.engagement.current_state == "in_zone"
        assert response.chapter.current_chapter == 3
        assert len(response.vice_profile.top_vices) == 1
