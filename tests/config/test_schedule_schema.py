"""Verify schedule.yaml loads without cron_schedules field (PR #121 DC-013).

PR #121 removed the cron_schedules YAML block, replacing it with a comment
pointing to docs/deployment.md as the single authoritative pg_cron registry.
The CronSchedules schema class was dead code with zero production readers.
"""

from nikita.config.loader import ConfigLoader


def test_schedule_config_loads_without_cron_schedules():
    """ConfigLoader must not require cron_schedules in schedule.yaml."""
    config = ConfigLoader()
    assert config.schedule is not None
    assert hasattr(config.schedule, "availability_windows")
    assert len(config.schedule.availability_windows) > 0


def test_schedule_has_chapter_response_timing():
    """schedule.yaml still provides chapter response timing."""
    config = ConfigLoader()
    assert hasattr(config.schedule, "chapter_response_timing")
    assert 1 in config.schedule.chapter_response_timing
    assert 5 in config.schedule.chapter_response_timing
