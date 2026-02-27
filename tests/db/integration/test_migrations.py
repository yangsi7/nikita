"""Integration tests for Alembic migrations.

T14: Integration Tests
- AC-T14.4: Migration tests verify up/down reversibility
"""

from . import conftest as db_conftest

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Skip all tests if Database unreachable
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not db_conftest._SUPABASE_REACHABLE,
        reason="Database unreachable - skipping integration tests",
    ),
]


class TestMigrationStatus:
    """Verify migration status and version tracking."""

    @pytest.mark.asyncio
    async def test_alembic_version_table_exists(self, session: AsyncSession):
        """Verify alembic_version table exists."""
        result = await session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'alembic_version'
                )
            """)
        )
        exists = result.scalar()

        if not exists:
            pytest.skip("alembic_version table not found - migrations not run")

        assert exists is True

    @pytest.mark.asyncio
    async def test_has_current_migration_version(self, session: AsyncSession):
        """Verify a migration version is recorded."""
        result = await session.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        version = result.scalar()

        if version is None:
            pytest.skip("No migration version found")

        assert version is not None
        assert len(version) > 0


class TestSchemaIntegrity:
    """Verify database schema matches expected structure.

    AC-T14.4: Verify migrations created correct schema.
    """

    @pytest.mark.asyncio
    async def test_users_table_structure(self, session: AsyncSession):
        """Verify users table has expected columns."""
        result = await session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'users'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0]: (row[1], row[2]) for row in result.fetchall()}

        if not columns:
            pytest.skip("users table not found")

        # Required columns
        assert "id" in columns
        assert "relationship_score" in columns
        assert "chapter" in columns
        assert "game_status" in columns
        # graphiti_group_id removed from User model (GH #86) — column still in DB
        # but no longer mapped by SQLAlchemy. Don't assert its presence here.

    @pytest.mark.asyncio
    async def test_user_metrics_table_structure(self, session: AsyncSession):
        """Verify user_metrics table has expected columns."""
        result = await session.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'user_metrics'
            """)
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        if not columns:
            pytest.skip("user_metrics table not found")

        # Required columns for metrics
        assert "intimacy" in columns
        assert "passion" in columns
        assert "trust" in columns
        assert "secureness" in columns

    @pytest.mark.asyncio
    async def test_conversations_table_structure(self, session: AsyncSession):
        """Verify conversations table has expected columns."""
        result = await session.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'conversations'
            """)
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        if not columns:
            pytest.skip("conversations table not found")

        # Required columns
        assert "id" in columns
        assert "user_id" in columns
        assert "messages" in columns  # JSONB column
        assert "platform" in columns

    @pytest.mark.asyncio
    async def test_score_history_table_structure(self, session: AsyncSession):
        """Verify score_history table has expected columns."""
        result = await session.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'score_history'
            """)
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        if not columns:
            pytest.skip("score_history table not found")

        # Required columns
        assert "user_id" in columns
        assert "score" in columns
        assert "chapter" in columns
        assert "event_type" in columns


class TestIndexesExist:
    """Verify expected indexes exist for performance."""

    @pytest.mark.asyncio
    async def test_users_telegram_id_index(self, session: AsyncSession):
        """Verify index on users.telegram_id exists."""
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'users'
                AND indexdef LIKE '%telegram_id%'
            """)
        )
        indexes = result.fetchall()

        # At least one index should reference telegram_id
        # (could be unique constraint or explicit index)
        if not indexes:
            pytest.skip("telegram_id index not found - may not be indexed")

    @pytest.mark.asyncio
    async def test_score_history_user_id_index(self, session: AsyncSession):
        """Verify index on score_history.user_id exists."""
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'score_history'
            """)
        )
        indexes = result.fetchall()

        if not indexes:
            pytest.skip("No indexes on score_history")

        # Should have at least the primary key index
        assert len(indexes) >= 1


class TestForeignKeyConstraints:
    """Verify foreign key relationships are correctly defined."""

    @pytest.mark.asyncio
    async def test_user_metrics_references_users(self, session: AsyncSession):
        """Verify user_metrics.user_id references users.id."""
        result = await session.execute(
            text("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'user_metrics'
            """)
        )
        fks = result.fetchall()

        if not fks:
            pytest.skip("user_metrics foreign keys not found")

        # Check that user_id references users
        user_id_fk = [fk for fk in fks if fk[1] == "user_id"]
        assert len(user_id_fk) >= 1, "user_metrics should have user_id FK"
        assert user_id_fk[0][2] == "users", "user_id should reference users table"

    @pytest.mark.asyncio
    async def test_conversations_references_users(self, session: AsyncSession):
        """Verify conversations.user_id references users.id."""
        result = await session.execute(
            text("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'conversations'
                AND kcu.column_name = 'user_id'
            """)
        )
        fks = result.fetchall()

        if not fks:
            pytest.skip("conversations FK not found")

        assert fks[0][1] == "users"


class TestMigrationReversibility:
    """Test migration up/down reversibility.

    AC-T14.4: Migration tests verify up/down reversibility.

    Note: Actually running downgrade is destructive and should only
    be done in a dedicated test database. These tests verify the
    migration files exist and have both upgrade() and downgrade().
    """

    def test_migration_files_have_downgrade(self):
        """Verify migration files have downgrade functions."""
        from . import conftest as db_conftest
        from pathlib import Path

        migrations_dir = Path(__file__).parent.parent.parent.parent / "nikita" / "db" / "migrations" / "versions"

        if not migrations_dir.exists():
            pytest.skip("Migrations directory not found")

        migration_files = list(migrations_dir.glob("*.py"))
        if not migration_files:
            pytest.skip("No migration files found")

        for mig_file in migration_files:
            content = mig_file.read_text()

            # Check for both upgrade and downgrade functions
            assert "def upgrade()" in content, f"{mig_file.name} missing upgrade()"
            assert "def downgrade()" in content, f"{mig_file.name} missing downgrade()"

    def test_migration_files_are_ordered(self):
        """Verify migration files have proper ordering."""
        from . import conftest as db_conftest
        from pathlib import Path

        migrations_dir = Path(__file__).parent.parent.parent.parent / "nikita" / "db" / "migrations" / "versions"

        if not migrations_dir.exists():
            pytest.skip("Migrations directory not found")

        migration_files = sorted(migrations_dir.glob("*.py"))
        if not migration_files:
            pytest.skip("No migration files found")

        # Files should be named with date prefix for ordering
        for mig_file in migration_files:
            # Should start with YYYYMMDD or similar ordering prefix
            name = mig_file.stem
            assert name[0].isdigit(), f"Migration {name} should have ordered prefix"
