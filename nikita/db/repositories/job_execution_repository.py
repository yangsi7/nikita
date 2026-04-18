"""JobExecution repository for admin debug portal.

Handles job execution tracking queries for monitoring scheduled jobs.
"""

from datetime import datetime, timedelta, UTC
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import cast, func, select, Date
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

    async def has_recent_execution(
        self,
        job_name: str,
        window_minutes: int = 50,
    ) -> bool:
        """Check if a successful execution occurred within the window."""
        cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)
        stmt = (
            select(JobExecution)
            .where(
                JobExecution.job_name == job_name,
                JobExecution.status == JobStatus.COMPLETED.value,
                JobExecution.completed_at >= cutoff,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

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

    async def get_today_cost_usd(
        self,
        job_name: str | None = None,
    ) -> Decimal:
        """Sum cost_usd for job executions started today (UTC).

        Implements the cost ledger primitive used by the FR-014 cost circuit
        breaker (Spec 215 B2 / GH #336). The daily-arcs handler calls this
        before invoking planner LLM jobs to enforce
        ``settings.heartbeat_cost_circuit_breaker_usd_per_day`` (default $50).

        Args:
            job_name: Optional filter scoping the sum to one job type
                (e.g. ``JobName.GENERATE_DAILY_ARCS.value``). When None, sums
                across all jobs.

        Returns:
            Aggregated cost in USD as Decimal. Returns Decimal('0') when no
            rows match (Postgres ``SUM`` of zero rows is NULL → coerced to 0).
        """
        stmt = select(func.coalesce(func.sum(JobExecution.cost_usd), 0)).where(
            cast(JobExecution.started_at, Date) == func.current_date()
        )
        if job_name is not None:
            stmt = stmt.where(JobExecution.job_name == job_name)

        result = await self.session.execute(stmt)
        total = result.scalar()
        if total is None:
            return Decimal("0")
        return Decimal(str(total))

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
