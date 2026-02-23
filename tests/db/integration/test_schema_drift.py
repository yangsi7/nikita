"""Schema drift detection — compares SQLAlchemy models against live database.

Catches model edits that lack a corresponding migration. Uses Base.metadata.tables
which auto-discovers all models via nikita/db/models/__init__.py imports.

Marked integration — skips if DB unreachable.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from nikita.db.models import Base  # triggers all model imports

pytestmark = [pytest.mark.integration]

# Tables managed outside SQLAlchemy (Supabase internals, pgVector, etc.)
SKIP_TABLES = frozenset({
    "schema_migrations",  # supabase internal
    "secrets",            # vault
})


async def _db_tables(engine: AsyncEngine) -> set[str]:
    """Return set of table names in the public schema."""
    query = sa.text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    async with engine.connect() as conn:
        rows = await conn.execute(query)
        return {r[0] for r in rows}


async def _db_columns(engine: AsyncEngine) -> dict[str, dict[str, dict]]:
    """Return {table: {column: {type, nullable}}} for public schema."""
    query = sa.text(
        "SELECT table_name, column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' "
        "ORDER BY table_name, ordinal_position"
    )
    async with engine.connect() as conn:
        rows = await conn.execute(query)
        result: dict[str, dict[str, dict]] = {}
        for table, col, dtype, nullable in rows:
            result.setdefault(table, {})[col] = {
                "type": dtype,
                "nullable": nullable == "YES",
            }
        return result


def _model_tables() -> dict[str, sa.Table]:
    """Return {tablename: Table} from SQLAlchemy metadata."""
    return {
        name: table
        for name, table in Base.metadata.tables.items()
        if name not in SKIP_TABLES
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_model_tables_exist_in_db(engine: AsyncEngine):
    """Every model __tablename__ must have a corresponding DB table."""
    db_tables = await _db_tables(engine)
    model_tables = _model_tables()

    missing = set(model_tables.keys()) - db_tables
    assert not missing, (
        f"Model tables missing from DB (need migration): {sorted(missing)}"
    )


@pytest.mark.asyncio
async def test_all_model_columns_exist_in_db(engine: AsyncEngine):
    """Every mapped_column in models must exist in the DB.

    This is the test that would have caught the cool_down_until gap.
    """
    db_columns = await _db_columns(engine)
    model_tables = _model_tables()

    missing: list[str] = []
    for table_name, table in model_tables.items():
        db_cols = db_columns.get(table_name, {})
        if not db_cols:
            # Table-level miss caught by test_all_model_tables_exist_in_db
            continue
        for col in table.columns:
            if col.name not in db_cols:
                missing.append(f"{table_name}.{col.name}")

    assert not missing, (
        f"Model columns missing from DB (need migration): {sorted(missing)}"
    )


@pytest.mark.asyncio
async def test_no_nullable_mismatch(engine: AsyncEngine):
    """Model nullable flags should match DB nullable flags.

    Ignores primary keys (always NOT NULL in DB regardless of model annotation)
    and columns with server_default (DB may differ from model intent).
    """
    db_columns = await _db_columns(engine)
    model_tables = _model_tables()

    mismatches: list[str] = []
    for table_name, table in model_tables.items():
        db_cols = db_columns.get(table_name, {})
        if not db_cols:
            continue
        for col in table.columns:
            if col.primary_key:
                continue
            if col.server_default is not None:
                continue
            db_col = db_cols.get(col.name)
            if db_col is None:
                continue  # missing column caught elsewhere
            model_nullable = bool(col.nullable)
            db_nullable = db_col["nullable"]
            if model_nullable != db_nullable:
                mismatches.append(
                    f"{table_name}.{col.name}: "
                    f"model={'NULL' if model_nullable else 'NOT NULL'} "
                    f"vs db={'NULL' if db_nullable else 'NOT NULL'}"
                )

    assert not mismatches, (
        f"Nullable mismatches between model and DB:\n"
        + "\n".join(f"  - {m}" for m in sorted(mismatches))
    )
