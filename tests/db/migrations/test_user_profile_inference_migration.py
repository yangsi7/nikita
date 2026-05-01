"""Static structure tests for Spec 216-D-migration.

Verifies the migration SQL file declares the required columns, CHECK
constraints, and backfill predicate by parsing the file. Runs in the
unit suite (no live DB required) so the pre-push gate catches drift
without needing a Supabase round-trip.

Live-DB introspection of post-migration schema is covered separately in
``tests/db/integration/test_user_profile_inference_columns.py``
(``@pytest.mark.integration``, skipped without ``_SUPABASE_REACHABLE``).

Acceptance criteria covered:
- D1.1: ``users.big5_vector`` JSONB DEFAULT '{}'::jsonb
- D1.2: ``users.backstory_seed`` TEXT NULL with CHECK length≤300
- D1.3: ``users.brand_resonance_signal`` NUMERIC NULL with CHECK [0,1]
- D1.8: ``backstory_cache.cache_key`` sha256 backfill via regex predicate
- D1.10: top-level columns (NOT JSONB-embedded)
- D1.11: idempotent DO-block CHECK pattern
- D1.12: ``users.archetype_candidates`` JSONB DEFAULT '[]'::jsonb
"""

from __future__ import annotations

from pathlib import Path

import pytest

MIGRATION_PATH: Path = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20260502120000_user_profile_inference.sql"
)


@pytest.fixture(scope="module")
def migration_sql() -> str:
    """Load migration SQL once per test module."""
    assert MIGRATION_PATH.exists(), (
        f"Migration file missing at {MIGRATION_PATH}"
    )
    return MIGRATION_PATH.read_text()


class TestColumnAdditions:
    """Each new column on public.users — verified by SQL substring match."""

    def test_big5_vector_column_added(self, migration_sql: str) -> None:
        """D1.1: big5_vector JSONB DEFAULT '{}'::jsonb."""
        assert "big5_vector JSONB DEFAULT '{}'::jsonb" in migration_sql

    def test_backstory_seed_column_added(self, migration_sql: str) -> None:
        """D1.2: backstory_seed TEXT (no DEFAULT, NULLable)."""
        assert "backstory_seed TEXT" in migration_sql

    def test_brand_resonance_signal_column_added(
        self, migration_sql: str
    ) -> None:
        """D1.3: brand_resonance_signal NUMERIC (NULLable)."""
        assert "brand_resonance_signal NUMERIC" in migration_sql

    def test_archetype_candidates_column_added(
        self, migration_sql: str
    ) -> None:
        """D1.12: archetype_candidates JSONB DEFAULT '[]'::jsonb."""
        assert "archetype_candidates JSONB DEFAULT '[]'::jsonb" in migration_sql

    def test_columns_added_via_ADD_COLUMN_IF_NOT_EXISTS(
        self, migration_sql: str
    ) -> None:
        """All ADD COLUMN statements use IF NOT EXISTS for idempotency."""
        # Count ADD COLUMN occurrences within the public.users block
        users_block_start = migration_sql.find("ALTER TABLE public.users")
        users_block_end = migration_sql.find(";", users_block_start)
        users_block = migration_sql[users_block_start:users_block_end]
        # Each of the 4 columns must be guarded with IF NOT EXISTS
        assert users_block.count("ADD COLUMN IF NOT EXISTS") == 4, (
            f"Expected 4 ADD COLUMN IF NOT EXISTS clauses; found "
            f"{users_block.count('ADD COLUMN IF NOT EXISTS')}. The migration "
            f"must be idempotent (D1.11)."
        )

    def test_columns_are_top_level_not_jsonb_embedded(
        self, migration_sql: str
    ) -> None:
        """D1.10: columns are top-level on public.users, NOT inside a
        JSONB embedding column (e.g., onboarding_profile->big5_vector).
        The migration must not modify ``onboarding_profile`` JSONB.
        """
        assert "onboarding_profile->" not in migration_sql, (
            "D1.10 violation: migration must add top-level columns, not "
            "embed inside an existing JSONB column."
        )
        assert "jsonb_set(onboarding_profile" not in migration_sql, (
            "D1.10 violation: migration must add top-level columns, not "
            "modify onboarding_profile JSONB."
        )


class TestCheckConstraints:
    """CHECK constraints wrapped in idempotent DO-block guard (D1.11)."""

    def test_backstory_seed_length_constraint_present(
        self, migration_sql: str
    ) -> None:
        """D1.2: backstory_seed length ≤ 300."""
        assert "check_users_backstory_seed_length" in migration_sql
        # Constraint body must enforce length≤300 with NULL allowance
        assert "length(backstory_seed) <= 300" in migration_sql

    def test_brand_resonance_range_constraint_present(
        self, migration_sql: str
    ) -> None:
        """D1.3: brand_resonance_signal in [0, 1]."""
        assert "check_users_brand_resonance_range" in migration_sql
        # Range bounds must be present
        assert "brand_resonance_signal >= 0" in migration_sql
        assert "brand_resonance_signal <= 1" in migration_sql

    def test_constraints_use_idempotent_do_block_pattern(
        self, migration_sql: str
    ) -> None:
        """D1.11: each CHECK constraint is wrapped in DO-block IF NOT
        EXISTS guard so re-running the migration is safe.
        Counted occurrences of pg_constraint lookup must equal 2 (one
        per CHECK constraint added).
        """
        pg_constraint_lookups = migration_sql.count(
            "FROM pg_constraint"
        )
        assert pg_constraint_lookups == 2, (
            f"Expected 2 pg_constraint guard blocks (one per CHECK "
            f"constraint per D1.11); found {pg_constraint_lookups}."
        )

    def test_constraints_are_named(self, migration_sql: str) -> None:
        """Constraints use deterministic names (NOT auto-generated) so
        the DO-block guard can locate them by name on re-run.
        """
        # Anonymous CHECK (e.g. `CHECK (...)` without `CONSTRAINT name`)
        # would survive re-runs but produce duplicates with auto-generated
        # names; the DO-block pattern requires named constraints.
        assert "CONSTRAINT check_users_backstory_seed_length" in migration_sql
        assert "CONSTRAINT check_users_brand_resonance_range" in migration_sql


class TestBackfillPredicate:
    """D1.8: cache_key sha256 backfill uses regex predicate, not length."""

    def test_backfill_uses_sha256_encoding(self, migration_sql: str) -> None:
        """Backfill hashes via encode(sha256(...), 'hex')."""
        assert "encode(sha256(cache_key::bytea), 'hex')" in migration_sql

    def test_backfill_uses_regex_predicate_not_length(
        self, migration_sql: str
    ) -> None:
        """D1.8: predicate must be regex `!~ '^[a-f0-9]{64}$'`, NOT
        `length(cache_key) != 64`. Length-based filtering would
        accidentally match raw keys that happen to be 64 chars long
        (e.g., long city + occupation strings).
        """
        # Required: regex anti-match on sha256-hex shape
        assert "cache_key !~ '^[a-f0-9]{64}$'" in migration_sql, (
            "D1.8 violation: backfill must use regex predicate "
            "`cache_key !~ '^[a-f0-9]{64}$'` to avoid double-hashing."
        )
        # Forbidden: length-based predicate (per D1.8 explicit anti-pattern)
        assert "length(cache_key) != 64" not in migration_sql
        assert "length(cache_key) <> 64" not in migration_sql

    def test_backfill_handles_null_cache_key_safely(
        self, migration_sql: str
    ) -> None:
        """NULL cache_key rows are excluded from the UPDATE."""
        assert "cache_key IS NOT NULL" in migration_sql

    def test_backfill_only_in_backstory_cache_table(
        self, migration_sql: str
    ) -> None:
        """D1.8 backfill is scoped to backstory_cache; no other tables
        touched.
        """
        # exactly one UPDATE statement, against backstory_cache
        update_count = migration_sql.count("UPDATE public.backstory_cache")
        assert update_count == 1, (
            f"Expected exactly 1 UPDATE on backstory_cache; "
            f"found {update_count}."
        )


class TestRollbackComment:
    """Migration includes a documented rollback path (project convention)."""

    def test_rollback_section_present(self, migration_sql: str) -> None:
        """Rollback comment block at the end of the file."""
        assert "ROLLBACK" in migration_sql

    def test_rollback_drops_all_added_columns(
        self, migration_sql: str
    ) -> None:
        """Rollback comment lists DROP COLUMN for each new column."""
        assert "DROP COLUMN IF EXISTS big5_vector" in migration_sql
        assert "DROP COLUMN IF EXISTS backstory_seed" in migration_sql
        assert "DROP COLUMN IF EXISTS brand_resonance_signal" in migration_sql
        assert "DROP COLUMN IF EXISTS archetype_candidates" in migration_sql

    def test_rollback_drops_all_added_constraints(
        self, migration_sql: str
    ) -> None:
        """Rollback drops both CHECK constraints by name."""
        assert (
            "DROP CONSTRAINT IF EXISTS check_users_backstory_seed_length"
            in migration_sql
        )
        assert (
            "DROP CONSTRAINT IF EXISTS check_users_brand_resonance_range"
            in migration_sql
        )

    def test_rollback_documents_backfill_irreversibility(
        self, migration_sql: str
    ) -> None:
        """Rollback comment explicitly notes the cache_key sha256
        backfill is NOT reversible (raw values irrecoverable).
        """
        assert "NOT reversible" in migration_sql or "not reversible" in migration_sql
