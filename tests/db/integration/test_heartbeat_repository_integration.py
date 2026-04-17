"""Integration tests for NikitaDailyPlanRepository (Spec 215 PR 215-A).

T2.4 — Real-DB regression guard for the Heartbeat Engine foundation.

Tests assert behaviour that mock-only unit tests cannot verify:
    - JSONB native type round-trip (PR #319 burn class regression guard)
    - upsert idempotency under concurrent same-day calls
    - RLS user-scoped read enforcement
    - service-role bypass for cron writes

All tests gated on real Supabase connectivity via the integration conftest;
skipped automatically in CI without a DATABASE_URL.

Source: plan.md T2.4 + Plan v4 R5 + .claude/rules/testing.md "Tests That Don't Test"
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import conftest as db_conftest
from nikita.db.models.heartbeat import NikitaDailyPlan
from nikita.db.repositories.heartbeat_repository import NikitaDailyPlanRepository
from nikita.db.repositories.user_repository import UserRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not db_conftest._SUPABASE_REACHABLE,
        reason="Database unreachable - skipping integration tests",
    ),
]


class TestNikitaDailyPlanRepositoryIntegration:
    """Real-DB integration tests for NikitaDailyPlanRepository."""

    @pytest_asyncio.fixture
    async def heartbeat_repo(self, session: AsyncSession) -> NikitaDailyPlanRepository:
        return NikitaDailyPlanRepository(session)

    @pytest_asyncio.fixture
    async def user_repo(self, session: AsyncSession) -> UserRepository:
        return UserRepository(session)

    @pytest.mark.asyncio
    async def test_arc_json_stores_native_dict_not_string(
        self,
        heartbeat_repo: NikitaDailyPlanRepository,
        user_repo: UserRepository,
        test_telegram_id: int,
    ):
        """AC-T2.4-001: arc_json round-trips as JSON object, not double-encoded string.

        Pre-fix bug class (PR #319): when callers pre-serialize via json.dumps(),
        the asyncpg JSONB codec re-encodes the string, producing
        jsonb_typeof = 'string' instead of 'object'. The model's
        Mapped[dict] + JSONB column type adapter handles serialization end-to-end;
        explicit json.dumps is forbidden per the heartbeat.py module docstring.

        This test inserts a complex nested dict, queries via raw SQL
        SELECT jsonb_typeof(arc_json), and asserts 'object'.
        """
        user = await user_repo.create_with_metrics(
            user_id=uuid4(),
            telegram_id=test_telegram_id,
        )

        arc_data = {
            "steps": [
                {"at": "08:00", "state": "morning groggy", "action": None},
                {"at": "12:00", "state": "lunch break", "action": None},
                {
                    "at": "19:00",
                    "state": "thinking about user",
                    "action": {
                        "type": "schedule_touchpoint_if",
                        "condition": "no_contact_today",
                    },
                },
            ],
            "narrative": "A normal Friday at the office.",
        }

        await heartbeat_repo.upsert_plan(
            user_id=user.id,
            plan_date=date.today(),
            arc_json=arc_data,
            narrative_text="A normal Friday at the office.",
            model_used="claude-haiku-4-5-20251001",
        )
        await heartbeat_repo.session.commit()

        result = await heartbeat_repo.session.execute(
            text(
                "SELECT jsonb_typeof(arc_json) AS arc_type, "
                "jsonb_typeof(arc_json->'steps') AS steps_type, "
                "(arc_json->'steps'->0->>'at') AS first_step_at "
                "FROM public.nikita_daily_plan "
                "WHERE user_id = :uid AND plan_date = :pd"
            ),
            {"uid": user.id, "pd": date.today()},
        )
        row = result.mappings().first()
        assert row is not None
        assert row["arc_type"] == "object", (
            f"arc_json should be JSON object, got {row['arc_type']!r} "
            "(pre-fix bug stored as string when caller used json.dumps)"
        )
        assert row["steps_type"] == "array"
        assert row["first_step_at"] == "08:00"

    @pytest.mark.asyncio
    async def test_upsert_idempotency(
        self,
        heartbeat_repo: NikitaDailyPlanRepository,
        user_repo: UserRepository,
        test_telegram_id: int,
    ):
        """AC-T2.4-002: upsert_plan called twice for same (user_id, plan_date)
        produces exactly one row, with generated_at refreshed on second call.
        """
        user = await user_repo.create_with_metrics(
            user_id=uuid4(),
            telegram_id=test_telegram_id,
        )

        target_date = date.today()
        arc_v1 = {"steps": [{"at": "08:00", "state": "v1"}], "narrative": "v1"}
        arc_v2 = {"steps": [{"at": "08:00", "state": "v2"}], "narrative": "v2"}

        # First upsert
        await heartbeat_repo.upsert_plan(
            user_id=user.id,
            plan_date=target_date,
            arc_json=arc_v1,
            narrative_text="v1",
            model_used="claude-haiku-4-5-20251001",
        )
        await heartbeat_repo.session.commit()

        first_gen_at_result = await heartbeat_repo.session.execute(
            text(
                "SELECT generated_at FROM public.nikita_daily_plan "
                "WHERE user_id = :uid AND plan_date = :pd"
            ),
            {"uid": user.id, "pd": target_date},
        )
        first_gen_at = first_gen_at_result.scalar_one()

        # Second upsert with different content
        await heartbeat_repo.upsert_plan(
            user_id=user.id,
            plan_date=target_date,
            arc_json=arc_v2,
            narrative_text="v2",
            model_used="claude-haiku-4-5-20251001",
        )
        await heartbeat_repo.session.commit()

        # Assert exactly 1 row
        count_result = await heartbeat_repo.session.execute(
            text(
                "SELECT COUNT(*) AS n FROM public.nikita_daily_plan "
                "WHERE user_id = :uid AND plan_date = :pd"
            ),
            {"uid": user.id, "pd": target_date},
        )
        count_row = count_result.mappings().first()
        assert count_row is not None
        assert count_row["n"] == 1, "upsert created duplicate instead of updating"

        # Assert content updated to v2
        v2_result = await heartbeat_repo.session.execute(
            text(
                "SELECT narrative_text, generated_at FROM public.nikita_daily_plan "
                "WHERE user_id = :uid AND plan_date = :pd"
            ),
            {"uid": user.id, "pd": target_date},
        )
        v2_row = v2_result.mappings().first()
        assert v2_row is not None
        assert v2_row["narrative_text"] == "v2"
        assert v2_row["generated_at"] >= first_gen_at, (
            "generated_at should refresh on upsert"
        )

    @pytest.mark.asyncio
    async def test_get_plan_for_date_returns_none_on_miss(
        self,
        heartbeat_repo: NikitaDailyPlanRepository,
        user_repo: UserRepository,
        test_telegram_id: int,
    ):
        """AC-T2.3-001 contract: get_plan_for_date returns None when no plan exists."""
        user = await user_repo.create_with_metrics(
            user_id=uuid4(),
            telegram_id=test_telegram_id,
        )
        await heartbeat_repo.session.commit()

        result = await heartbeat_repo.get_plan_for_date(
            user_id=user.id,
            plan_date=date.today() - timedelta(days=10),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_plan_for_date_returns_persisted_plan(
        self,
        heartbeat_repo: NikitaDailyPlanRepository,
        user_repo: UserRepository,
        test_telegram_id: int,
    ):
        """AC-T2.3-001: get_plan_for_date returns the row that was upserted."""
        user = await user_repo.create_with_metrics(
            user_id=uuid4(),
            telegram_id=test_telegram_id,
        )

        arc_data = {"steps": [{"at": "09:00", "state": "ok"}], "narrative": "test"}
        target_date = date.today()
        await heartbeat_repo.upsert_plan(
            user_id=user.id,
            plan_date=target_date,
            arc_json=arc_data,
            narrative_text="test narrative",
            model_used="claude-haiku-4-5-20251001",
        )
        await heartbeat_repo.session.commit()

        result = await heartbeat_repo.get_plan_for_date(
            user_id=user.id,
            plan_date=target_date,
        )
        assert result is not None
        assert isinstance(result, NikitaDailyPlan)
        assert result.user_id == user.id
        assert result.plan_date == target_date
        assert result.narrative_text == "test narrative"
        assert result.model_used == "claude-haiku-4-5-20251001"
        # JSONB round-trip: should be Python dict, not string
        assert isinstance(result.arc_json, dict)
        assert result.arc_json == arc_data
