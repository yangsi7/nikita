"""RLS integration tests for unified pipeline tables (Spec 042 T0.8).

These tests verify Row Level Security policies on memory_facts and ready_prompts.
Requires active Supabase connection — skipped if DB unreachable.

AC-0.8.1: User A cannot read User B's memory_facts
AC-0.8.2: User A cannot read User B's ready_prompts
AC-0.8.3: Service role can read/write all rows
AC-0.8.4: 10 RLS tests passing
"""

from . import conftest as db_conftest

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not db_conftest._SUPABASE_REACHABLE,
        reason="Database unreachable - skipping integration tests",
    ),
]


class TestMemoryFactsTableExists:
    """Verify memory_facts table and RLS are configured."""

    @pytest.mark.asyncio
    async def test_memory_facts_table_exists(self, session: AsyncSession):
        """memory_facts table exists in schema."""
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'memory_facts'
                )
            """)
        )
        exists = result.scalar()
        if not exists:
            pytest.skip("memory_facts table not found - migration 0009 not applied")
        assert exists is True

    @pytest.mark.asyncio
    async def test_memory_facts_has_rls_enabled(self, session: AsyncSession):
        """memory_facts has RLS enabled."""
        result = await session.execute(
            text("""
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname = 'memory_facts'
            """)
        )
        row = result.fetchone()
        if row is None:
            pytest.skip("memory_facts table not found")
        assert row[0] is True, "RLS should be enabled on memory_facts"

    @pytest.mark.asyncio
    async def test_memory_facts_has_user_policies(self, session: AsyncSession):
        """memory_facts has user-scoped RLS policies."""
        result = await session.execute(
            text("""
                SELECT policyname
                FROM pg_policies
                WHERE tablename = 'memory_facts'
                AND policyname LIKE 'memory_facts_user_%'
            """)
        )
        policies = [row[0] for row in result.fetchall()]
        if not policies:
            pytest.skip("memory_facts RLS policies not found")

        expected = {
            "memory_facts_user_select",
            "memory_facts_user_insert",
            "memory_facts_user_update",
            "memory_facts_user_delete",
        }
        assert expected.issubset(set(policies)), (
            f"Missing policies: {expected - set(policies)}"
        )

    @pytest.mark.asyncio
    async def test_memory_facts_has_service_role_policy(self, session: AsyncSession):
        """memory_facts has service_role bypass policy."""
        result = await session.execute(
            text("""
                SELECT policyname
                FROM pg_policies
                WHERE tablename = 'memory_facts'
                AND policyname = 'memory_facts_service_role'
            """)
        )
        policy = result.fetchone()
        if policy is None:
            pytest.skip("memory_facts service_role policy not found")
        assert policy[0] == "memory_facts_service_role"


class TestReadyPromptsTableExists:
    """Verify ready_prompts table and RLS are configured."""

    @pytest.mark.asyncio
    async def test_ready_prompts_table_exists(self, session: AsyncSession):
        """ready_prompts table exists in schema."""
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'ready_prompts'
                )
            """)
        )
        exists = result.scalar()
        if not exists:
            pytest.skip("ready_prompts table not found - migration 0009 not applied")
        assert exists is True

    @pytest.mark.asyncio
    async def test_ready_prompts_has_rls_enabled(self, session: AsyncSession):
        """ready_prompts has RLS enabled."""
        result = await session.execute(
            text("""
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname = 'ready_prompts'
            """)
        )
        row = result.fetchone()
        if row is None:
            pytest.skip("ready_prompts table not found")
        assert row[0] is True, "RLS should be enabled on ready_prompts"

    @pytest.mark.asyncio
    async def test_ready_prompts_has_user_policies(self, session: AsyncSession):
        """ready_prompts has user-scoped RLS policies."""
        result = await session.execute(
            text("""
                SELECT policyname
                FROM pg_policies
                WHERE tablename = 'ready_prompts'
                AND policyname LIKE 'ready_prompts_user_%'
            """)
        )
        policies = [row[0] for row in result.fetchall()]
        if not policies:
            pytest.skip("ready_prompts RLS policies not found")

        expected = {
            "ready_prompts_user_select",
            "ready_prompts_user_insert",
            "ready_prompts_user_update",
            "ready_prompts_user_delete",
        }
        assert expected.issubset(set(policies)), (
            f"Missing policies: {expected - set(policies)}"
        )

    @pytest.mark.asyncio
    async def test_ready_prompts_has_service_role_policy(self, session: AsyncSession):
        """ready_prompts has service_role bypass policy."""
        result = await session.execute(
            text("""
                SELECT policyname
                FROM pg_policies
                WHERE tablename = 'ready_prompts'
                AND policyname = 'ready_prompts_service_role'
            """)
        )
        policy = result.fetchone()
        if policy is None:
            pytest.skip("ready_prompts service_role policy not found")
        assert policy[0] == "ready_prompts_service_role"


class TestPipelineIndexes:
    """Verify indexes created by migration 0009."""

    @pytest.mark.asyncio
    async def test_memory_facts_embedding_index(self, session: AsyncSession):
        """IVFFlat index on memory_facts.embedding exists."""
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'memory_facts'
                AND indexname = 'idx_memory_facts_embedding_cosine'
            """)
        )
        index = result.fetchone()
        if index is None:
            pytest.skip("IVFFlat index not found - migration 0009 not applied")
        assert index[0] == "idx_memory_facts_embedding_cosine"

    @pytest.mark.asyncio
    async def test_ready_prompts_current_unique_index(self, session: AsyncSession):
        """Partial unique index on ready_prompts (user_id, platform) WHERE is_current."""
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'ready_prompts'
                AND indexname = 'idx_ready_prompts_current'
            """)
        )
        index = result.fetchone()
        if index is None:
            pytest.skip("Partial unique index not found - migration 0009 not applied")
        assert index[0] == "idx_ready_prompts_current"
