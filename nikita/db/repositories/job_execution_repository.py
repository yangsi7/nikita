"""JobExecution repository for admin debug portal.

Handles job execution tracking queries for monitoring scheduled jobs.
"""

from datetime import datetime, UTC
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.job_execution import JobExecution, JobStatus
from nikita.db.repositories.base import BaseRepository


class JobExecutionRepository(BaseRepository[JobExecution]):
    """Repository for JobExecution entity.

    Handles job execution tracking and queries for admin debug portal.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize JobExecutionRepository."""
        super().__init__(session, JobExecution)

    async def get_latest_by_job_name(self, job_name: str) -> JobExecution | None:
        """Get the most recent execution for a specific job type.

        Args:
            job_name: The job name (decay, deliver, summary, cleanup, process-conversations).

        Returns:
            Most recent JobExecution or None if no executions found.
        """
        stmt = (
            select(JobExecution)
            .where(JobExecution.job_name == job_name)
            .order_by(JobExecution.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_executions(
        self,
        job_name: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[JobExecution]:
        """Get recent job executions with optional filtering.

        Args:
            job_name: Filter by job name (optional).
            status: Filter by status (optional).
            limit: Maximum number of executions to return (default: 20).

        Returns:
            List of JobExecution records ordered by started_at DESC.
        """
        stmt = select(JobExecution)

        if job_name is not None:
            stmt = stmt.where(JobExecution.job_name == job_name)
        if status is not None:
            stmt = stmt.where(JobExecution.status == status)

        stmt = stmt.order_by(JobExecution.started_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def start_execution(self, job_name: str) -> JobExecution:
        """Start tracking a new job execution.

        Creates a new JobExecution record with RUNNING status.

        Args:
            job_name: The job name being started.

        Returns:
            The created JobExecution record.
        """
        execution = JobExecution(
            id=uuid4(),
            job_name=job_name,
            started_at=datetime.now(UTC),
            status=JobStatus.RUNNING.value,
        )
        return await self.create(execution)

    async def complete_execution(
        self,
        execution_id: UUID,
        result: dict | None = None,
    ) -> JobExecution:
        """Mark a job execution as completed.

        Args:
            execution_id: The execution ID to mark complete.
            result: Optional result data (metrics, counts, etc.).

        Returns:
            The updated JobExecution record.

        Raises:
            ValueError: If execution not found.
        """
        execution = await self.get(execution_id)
        if execution is None:
            raise ValueError(f"JobExecution {execution_id} not found")

        now = datetime.now(UTC)
        execution.status = JobStatus.COMPLETED.value
        execution.completed_at = now
        execution.result = result

        # Calculate duration in milliseconds
        if execution.started_at:
            delta = now - execution.started_at
            execution.duration_ms = int(delta.total_seconds() * 1000)

        return await self.update(execution)

    async def fail_execution(
        self,
        execution_id: UUID,
        result: dict | None = None,
    ) -> JobExecution:
        """Mark a job execution as failed.

        Args:
            execution_id: The execution ID to mark failed.
            result: Optional error details.

        Returns:
            The updated JobExecution record.

        Raises:
            ValueError: If execution not found.
        """
        execution = await self.get(execution_id)
        if execution is None:
            raise ValueError(f"JobExecution {execution_id} not found")

        now = datetime.now(UTC)
        execution.status = JobStatus.FAILED.value
        execution.completed_at = now
        execution.result = result

        # Calculate duration in milliseconds
        if execution.started_at:
            delta = now - execution.started_at
            execution.duration_ms = int(delta.total_seconds() * 1000)

        return await self.update(execution)
