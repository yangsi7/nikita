"""POST /converse idempotency cache (Spec 214 FR-11d, GH #352).

Backing table: ``llm_idempotency_cache`` (see
``supabase/migrations/20260419120000_llm_idempotency_cache.sql``).

Dedupe key = ``(user_id, turn_id)`` where ``turn_id`` is a
client-generated UUIDv4 — either on the ``Idempotency-Key`` HTTP header
or in ``ConverseRequest.turn_id``. A HIT within 5 minutes returns the
cached response body + status verbatim; the endpoint skips the agent
call, rate-limit decrement, JSONB write, and LLM spend increment (M5).

TTL enforcement lives in the pg_cron ``llm_idempotency_cache_prune``
job defined in the migration (hourly delete). The repo does not rely on
a DB-side TTL filter at read time; instead it computes
``now() - created_at`` against
``IDEMPOTENCY_CACHE_TTL_SECONDS`` so stale rows between cron runs are
ignored by the endpoint.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 5-minute TTL — pinned in tech-spec §2.3 and AC-11d.3c.
IDEMPOTENCY_CACHE_TTL_SECONDS: int = 300


class IdempotencyStore:
    """Async wrapper around ``llm_idempotency_cache``.

    Uses raw SQL text rather than a SQLAlchemy ORM model because the
    table is write-rare / read-rare and shaped by the cron job; keeping
    it ORM-free avoids an extra model class that is never imported by
    the hot text-agent path.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, user_id: UUID, turn_id: UUID
    ) -> tuple[dict[str, Any], int] | None:
        """Return ``(response_body, status_code)`` if HIT within TTL, else None.

        Returns ``None`` when the row is absent or older than
        ``IDEMPOTENCY_CACHE_TTL_SECONDS``. The TTL check is applied in
        Python rather than SQL so a single round-trip serves both
        branches.
        """
        row = await self._session.execute(
            text(
                """
                SELECT response_body, status_code, created_at
                  FROM llm_idempotency_cache
                 WHERE user_id = :uid AND turn_id = :tid
                """
            ),
            {"uid": user_id, "tid": turn_id},
        )
        record = row.first()
        if record is None:
            return None
        response_body, status_code, created_at = record
        if (
            datetime.now(timezone.utc) - created_at
            > timedelta(seconds=IDEMPOTENCY_CACHE_TTL_SECONDS)
        ):
            return None
        return dict(response_body), int(status_code)

    async def put(
        self,
        user_id: UUID,
        turn_id: UUID,
        response_body: dict[str, Any],
        status_code: int,
    ) -> None:
        """Store a cache entry. ``ON CONFLICT DO NOTHING`` preserves the
        first winner's body under a concurrent racing-write scenario.
        """
        await self._session.execute(
            text(
                """
                INSERT INTO llm_idempotency_cache
                    (user_id, turn_id, response_body, status_code)
                VALUES (:uid, :tid, CAST(:body AS jsonb), :status)
                ON CONFLICT (user_id, turn_id) DO NOTHING
                """
            ),
            {
                "uid": user_id,
                "tid": turn_id,
                "body": _json_dumps(response_body),
                "status": status_code,
            },
        )


def _json_dumps(value: dict[str, Any]) -> str:
    """Canonical JSON serialization for JSONB column insertion.

    Deliberately uses ``json.dumps`` directly rather than SQLAlchemy's
    JSONB type to keep this module ORM-free. CAST-to-jsonb in the SQL
    text ensures Postgres treats the string as JSON, not TEXT.
    """
    import json

    return json.dumps(value, separators=(",", ":"), default=str)


__all__ = [
    "IDEMPOTENCY_CACHE_TTL_SECONDS",
    "IdempotencyStore",
]
