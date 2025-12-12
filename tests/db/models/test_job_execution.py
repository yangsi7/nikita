"""Tests for JobExecution model.

TDD tests for T1.2: Create JobExecution Model

Acceptance Criteria:
- AC-FR008-001: Model supports all 5 job types (decay, deliver, summary, cleanup, process-conversations)
- AC-FR008-003: Model has status field (running, completed, failed)
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from nikita.db.models.job_execution import JobExecution, JobName, JobStatus


class TestJobExecutionModel:
    """Test suite for JobExecution model."""

    def test_model_instantiation(self):
        """Basic model instantiation works."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY,
            started_at=datetime.now(UTC),
            status=JobStatus.RUNNING,
        )
        assert job.job_name == JobName.DECAY
        assert job.status == JobStatus.RUNNING

    def test_all_job_names_defined(self):
        """AC-FR008-001: All 5 job types are supported."""
        expected_jobs = {"decay", "deliver", "summary", "cleanup", "process-conversations"}
        actual_jobs = {j.value for j in JobName}
        assert actual_jobs == expected_jobs

    def test_all_status_values_defined(self):
        """AC-FR008-003: All status values are defined."""
        expected_statuses = {"running", "completed", "failed"}
        actual_statuses = {s.value for s in JobStatus}
        assert actual_statuses == expected_statuses

    def test_decay_job_creation(self):
        """AC-FR008-001: decay job type works."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY,
            started_at=datetime.now(UTC),
            status=JobStatus.RUNNING,
        )
        assert job.job_name.value == "decay"

    def test_deliver_job_creation(self):
        """AC-FR008-001: deliver job type works."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.DELIVER,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED,
        )
        assert job.job_name.value == "deliver"

    def test_summary_job_creation(self):
        """AC-FR008-001: summary job type works."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.SUMMARY,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED,
        )
        assert job.job_name.value == "summary"

    def test_cleanup_job_creation(self):
        """AC-FR008-001: cleanup job type works."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.CLEANUP,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED,
        )
        assert job.job_name.value == "cleanup"

    def test_process_conversations_job_creation(self):
        """AC-FR008-001: process-conversations job type works."""
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.PROCESS_CONVERSATIONS,
            started_at=datetime.now(UTC),
            status=JobStatus.COMPLETED,
        )
        assert job.job_name.value == "process-conversations"

    def test_completed_job_with_result(self):
        """Completed jobs can have result dict."""
        result = {"users_processed": 50, "errors": 0}
        now = datetime.now(UTC)
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.DECAY,
            started_at=now,
            completed_at=now,
            status=JobStatus.COMPLETED,
            result=result,
            duration_ms=1250,
        )
        assert job.result == result
        assert job.duration_ms == 1250
        assert job.completed_at == now

    def test_failed_job_with_error_result(self):
        """AC-FR008-003: Failed jobs capture error info."""
        result = {"error": "Database connection failed", "attempts": 3}
        job = JobExecution(
            id=uuid4(),
            job_name=JobName.DELIVER,
            started_at=datetime.now(UTC),
            status=JobStatus.FAILED,
            result=result,
        )
        assert job.status == JobStatus.FAILED
        assert "error" in job.result

    def test_tablename(self):
        """Table name is correct."""
        assert JobExecution.__tablename__ == "job_executions"
