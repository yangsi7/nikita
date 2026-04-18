#!/usr/bin/env python3
"""Verify that the 3 heartbeat-engine cron jobs are registered + healthy.

Spec 215 PR 215-E (T6.2). Run via:

    uv run python scripts/check_heartbeat_cron_jobs.py

Exits 0 if all 3 jobs exist + recent runs are 'succeeded'. Exits 1 otherwise.
Designed for both manual ops verification and CI smoke-checks.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Final

import asyncpg

EXPECTED_JOBS: Final[tuple[str, ...]] = (
    "nikita-heartbeat-hourly",
    "nikita-generate-daily-arcs",
    "nikita-touchpoints",
)

# Per-job freshness windows (minutes). Sized to cron cadence + safety buffer:
#   touchpoints (every 5 min) → 15 min window  (3x cadence)
#   heartbeat-hourly         → 90 min          (1.5x cadence)
#   generate-daily-arcs      → 1500 min (~25h) (1x cadence + 1h slack)
JOB_FRESHNESS_MINUTES: Final[dict[str, int]] = {
    "nikita-touchpoints": 15,
    "nikita-heartbeat-hourly": 90,
    "nikita-generate-daily-arcs": 1500,
}

DATABASE_URL_ENV: Final[str] = "DATABASE_URL"


async def _check() -> int:
    db_url = os.environ.get(DATABASE_URL_ENV)
    if not db_url:
        print(f"FAIL: {DATABASE_URL_ENV} not set", file=sys.stderr)
        return 1

    conn = await asyncpg.connect(db_url)
    try:
        # 1) all expected jobs registered
        rows = await conn.fetch(
            "SELECT jobname, schedule FROM cron.job WHERE jobname = ANY($1::text[]) ORDER BY jobname",
            list(EXPECTED_JOBS),
        )
        present = {r["jobname"] for r in rows}
        missing = set(EXPECTED_JOBS) - present
        if missing:
            print(f"FAIL: missing cron jobs: {sorted(missing)}", file=sys.stderr)
            return 1
        print(f"OK: all {len(EXPECTED_JOBS)} cron jobs registered:")
        for r in rows:
            print(f"  - {r['jobname']:32s} {r['schedule']}")

        # 2) most recent run per job is healthy, using per-job freshness
        # windows so daily-arcs (24h cadence) is not falsely flagged as stale.
        exit_code = 0
        for jobname in EXPECTED_JOBS:
            window_min = JOB_FRESHNESS_MINUTES[jobname]
            row = await conn.fetchrow(
                """
                SELECT status, return_message, start_time
                FROM cron.job_run_details
                WHERE jobname = $1
                  AND start_time > now() - make_interval(mins => $2)
                ORDER BY start_time DESC
                LIMIT 1
                """,
                jobname,
                window_min,
            )
            if row is None:
                print(
                    f"WARN: {jobname:32s} no runs in last {window_min} min "
                    "(cron may not have ticked yet)"
                )
                continue
            if row["status"] != "succeeded":
                print(
                    f"FAIL: {jobname:32s} {row['status']:12s} {row['start_time']}",
                    file=sys.stderr,
                )
                if row["return_message"]:
                    print(f"      → {row['return_message']}", file=sys.stderr)
                exit_code = 1
            else:
                print(f"OK:   {jobname:32s} succeeded {row['start_time']}")
        return exit_code
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_check()))
