"""Tests for JobExecutionRepository.

TDD tests for T1.4: Create JobExecution Repository

Acceptance Criteria:
- CRUD operations for job executions
- `get_latest_by_job_name()` returns most recent execution per job
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.job_execution import JobExecution, JobName, JobStatus
from nikita.db.repositories.job_execution_repository import JobExecutionRepository


class TestJobExecutionRepository:
    """Test suite for JobExecutionRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session) -> JobExecutionRepository:
        """Create repository instance with mock session."""
        return JobExecutionRepository(mock_session)

    # ========================================
    # CRUD Operations Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_create_job_execution(self, repository, mock_session):
        """Can create a job execution."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY.value,
            started_at=datetime.now(UTC),
            status=JobStatus.RUNNING.value,
        )

        result = await repository.create(job)

        mock_session.add.assert_called_once_with(job)
        mock_session.flush.assert_called()
        assert result == job

    @pytest.mark.asyncio
    async def test_get_job_execution_by_id(self, repository, mock_session):
        """Can retrieve job execution by ID."""
        job_id = uuid4()
        job = JobExecution(
            id=job_id,
            job_name=JobName.DELIVER.value,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED.value,
        )
        mock_session.get.return_value = job

        retrieved = await repository.get(job_id)

        mock_session.get.assert_called_once_with(JobExecution, job_id)
        assert retrieved == job

    @pytest.mark.asyncio
    async def test_update_job_execution(self, repository, mock_session):
        """Can update job execution status and result."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.SUMMARY.value,
            started_at=datetime.now(UTC),
            status=JobStatus.RUNNING.value,
        )

        job.status = JobStatus.COMPLETED.value
        job.result = {"summaries_generated": 10}
        job.duration_ms = 5000

        result = await repository.update(job)

        mock_session.flush.assert_called()
        assert result == job

    @pytest.mark.asyncio
    async def test_delete_job_execution(self, repository, mock_session):
        """Can delete job execution."""
        job_id = uuid4()
        job = JobExecution(
            id=job_id,
            job_name=JobName.CLEANUP.value,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED.value,
        )
        mock_session.get.return_value = job

        deleted = await repository.delete_by_id(job_id)

        mock_session.delete.assert_called_once_with(job)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, repository, mock_session):
        """Delete returns False for nonexistent job."""
        mock_session.get.return_value = None

        deleted = await repository.delete_by_id(uuid4())

        assert deleted is False

    # ========================================
    # get_latest_by_job_name Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_get_latest_by_job_name_returns_job(self, repository, mock_session):
        """get_latest_by_job_name returns most recent execution."""
        now = datetime.now(UTC)
        newest_job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY.value,
            started_at=now,
            status=JobStatus.COMPLETED.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = newest_job
        mock_session.execute.return_value = mock_result

        latest = await repository.get_latest_by_job_name(JobName.DECAY.value)

        assert latest == newest_job
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_by_job_name_returns_none_if_no_jobs(
        self, repository, mock_session
    ):
        """get_latest_by_job_name returns None if no matching jobs."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        latest = await repository.get_latest_by_job_name(
            JobName.PROCESS_CONVERSATIONS.value
        )

        assert latest is None

    # ========================================
    # get_recent_executions Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_get_recent_executions(self, repository, mock_session):
        """get_recent_executions returns jobs ordered by started_at DESC."""
        now = datetime.now(UTC)
        jobs = [
            JobExecution(
                id=uuid4(),
                job_name=JobName.DECAY.value,
                started_at=now - timedelta(hours=i),
                status=JobStatus.COMPLETED.value,
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = jobs
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        recent = await repository.get_recent_executions(limit=3)

        assert len(recent) == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_executions_with_job_name_filter(
        self, repository, mock_session
    ):
        """get_recent_executions can filter by job name."""
        decay_job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY.value,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED.value,
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [decay_job]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        recent = await repository.get_recent_executions(
            job_name=JobName.DECAY.value, limit=10
        )

        assert len(recent) == 1
        assert recent[0].job_name == JobName.DECAY.value

    @pytest.mark.asyncio
    async def test_get_recent_executions_with_status_filter(
        self, repository, mock_session
    ):
        """get_recent_executions can filter by status."""
        failed_job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY.value,
            started_at=datetime.now(UTC),
            status=JobStatus.FAILED.value,
        )

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [failed_job]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        recent = await repository.get_recent_executions(
            status=JobStatus.FAILED.value, limit=10
        )

        assert len(recent) == 1
        assert recent[0].status == JobStatus.FAILED.value

    # ========================================
    # Helper Methods Tests
    # ========================================

    @pytest.mark.asyncio
    async def test_start_execution(self, repository, mock_session):
        """start_execution creates a new running job execution."""
        execution = await repository.start_execution(JobName.DECAY.value)

        assert execution.job_name == JobName.DECAY.value
        assert execution.status == JobStatus.RUNNING.value
        assert execution.started_at is not None
        assert execution.completed_at is None
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_execution(self, repository, mock_session):
        """complete_execution marks job as completed with result."""
        now = datetime.now(UTC)
        execution = JobExecution(
            id=uuid4(),
            job_name=JobName.DELIVER.value,
            started_at=now - timedelta(seconds=5),
            status=JobStatus.RUNNING.value,
        )
        mock_session.get.return_value = execution

        result = {"messages_delivered": 25}
        completed = await repository.complete_execution(execution.id, result=result)

        assert completed.status == JobStatus.COMPLETED.value
        assert completed.result == result
        assert completed.completed_at is not None
        assert completed.duration_ms is not None
        assert completed.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_complete_execution_not_found(self, repository, mock_session):
        """complete_execution raises ValueError if execution not found."""
        mock_session.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await repository.complete_execution(uuid4())

    @pytest.mark.asyncio
    async def test_fail_execution(self, repository, mock_session):
        """fail_execution marks job as failed with error."""
        now = datetime.now(UTC)
        execution = JobExecution(
            id=uuid4(),
            job_name=JobName.SUMMARY.value,
            started_at=now - timedelta(seconds=2),
            status=JobStatus.RUNNING.value,
        )
        mock_session.get.return_value = execution

        error_result = {"error": "Database connection timeout"}
        failed = await repository.fail_execution(execution.id, result=error_result)

        assert failed.status == JobStatus.FAILED.value
        assert failed.result == error_result
        assert failed.completed_at is not None
        assert failed.duration_ms is not None

    @pytest.mark.asyncio
    async def test_fail_execution_not_found(self, repository, mock_session):
        """fail_execution raises ValueError if execution not found."""
        mock_session.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await repository.fail_execution(uuid4())
