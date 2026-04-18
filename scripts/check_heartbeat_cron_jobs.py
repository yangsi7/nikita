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

        # 2) most recent runs (within last 2h) are healthy
        recent = await conn.fetch(
            """
            SELECT jobname, status, return_message, start_time
            FROM cron.job_run_details
            WHERE jobname = ANY($1::text[])
              AND start_time > now() - interval '2 hours'
            ORDER BY start_time DESC
            """,
            list(EXPECTED_JOBS),
        )
        if not recent:
            print(
                "WARN: no runs in last 2h (cron may not have ticked yet — "
                "check again after the next scheduled minute)"
            )
            return 0
        bad = [r for r in recent if r["status"] != "succeeded"]
        if bad:
            print(f"FAIL: {len(bad)} unhealthy run(s):", file=sys.stderr)
            for r in bad:
                print(
                    f"  - {r['jobname']:32s} {r['status']:12s} {r['start_time']}",
                    file=sys.stderr,
                )
                if r["return_message"]:
                    print(f"      → {r['return_message']}", file=sys.stderr)
            return 1
        print(f"OK: {len(recent)} recent run(s), all 'succeeded'")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_check()))
