"""Integration tests for user_profiles RLS hardening — Spec 213 PR 213-2.

T1.5.R + TP.2 — RLS DDL tests requiring live Supabase database.

IMPORTANT: All tests in this file are marked @pytest.mark.integration.
They are SKIPPED in unit CI (no live Supabase). Run manually against
a live Supabase instance with:

    SUPABASE_URL=... SUPABASE_KEY=... pytest tests/db/test_rls_user_profiles.py -v

Tests verify:
1. New name/occupation/age columns are queryable via RLS
2. UPDATE WITH CHECK blocks id-swap attacks
3. DELETE with subquery form allows own-row deletion

These tests use the supabase-py client library. The module is skipped if
the supabase library is not installed or SUPABASE_URL/SUPABASE_KEY env vars
are absent.
"""

import os
import uuid

import pytest

# Skip the entire module if supabase library is not available
supabase = pytest.importorskip("supabase", reason="supabase library not installed")

# postgrest raises APIError on RLS/WITH CHECK violations; import conditionally
# because it's a transitive dep of supabase-py and not always installed.
try:
    from postgrest.exceptions import APIError  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — covered by integration env
    APIError = Exception  # type: ignore[misc,assignment]

# Also skip if env vars are absent.
# IMPORTANT: ``SUPABASE_KEY`` MUST be the **anon (public) key**, NOT the
# service_role key. The ``authenticated_client`` fixture uses this to start
# a session as a real end-user; if the service_role key is used instead, it
# BYPASSES ALL RLS POLICIES — every RLS assertion here would pass vacuously
# and the tests would report green while the policies are actually broken.
# The service_role key is loaded separately (see SUPABASE_SERVICE_ROLE_KEY
# below) and is used only for admin operations that deliberately bypass RLS.
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # anon/public key — see note above

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def skip_if_no_creds():
    """Skip all tests in this module if Supabase credentials are missing."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        pytest.skip(
            "SUPABASE_URL and SUPABASE_KEY must be set for RLS integration tests"
        )


@pytest.fixture(scope="module")
def supabase_admin_client(skip_if_no_creds):
    """Admin Supabase client (service_role key for setup/teardown).

    Requires SUPABASE_SERVICE_ROLE_KEY env var.
    """
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not service_role_key:
        pytest.skip("SUPABASE_SERVICE_ROLE_KEY required for RLS setup fixtures")

    from supabase import create_client

    return create_client(SUPABASE_URL, service_role_key)


@pytest.fixture(scope="module")
def test_user_credentials(supabase_admin_client):
    """Create a test user for RLS verification, yield credentials, then delete."""
    admin = supabase_admin_client
    email = f"rls-test-{uuid.uuid4().hex[:8]}@test.nikita.local"
    password = uuid.uuid4().hex

    # Create user via admin API
    response = admin.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user_id = response.user.id

    # Ensure a user_profiles row exists (service_role bypass)
    admin.table("user_profiles").upsert(
        {
            "id": user_id,
            "location_city": "Berlin",
            "drug_tolerance": 3,
            "name": None,
            "occupation": None,
            "age": None,
        }
    ).execute()

    yield {"email": email, "password": password, "user_id": user_id}

    # Teardown: delete the test user
    try:
        admin.auth.admin.delete_user(user_id)
    except Exception:
        pass  # Best-effort cleanup


@pytest.fixture
def authenticated_client(test_user_credentials):
    """Supabase client authenticated as the test user (RLS applies)."""
    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.auth.sign_in_with_password(
        {
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        }
    )
    yield client
    try:
        client.auth.sign_out()
    except Exception:
        pass


class TestUserProfilesNewColumnsRLS:
    """Tests for name/occupation/age columns queryable with RLS active (T1.5.R)."""

    def test_new_columns_queryable_with_rls(
        self, authenticated_client, test_user_credentials
    ):
        """Authenticated user can SELECT own name/occupation/age columns.

        Verifies the new columns exist in the RLS-filtered response.
        """
        user_id = test_user_credentials["user_id"]
        client = authenticated_client

        # Update own profile with new columns (service_role already seeded the row)
        update_response = (
            client.table("user_profiles")
            .update({"name": "Anna", "occupation": "designer", "age": 29})
            .eq("id", user_id)
            .execute()
        )
        assert update_response.data, "Update should succeed for own row"

        # Now SELECT and verify new columns are readable
        select_response = (
            client.table("user_profiles").select("name,occupation,age").eq("id", user_id).execute()
        )
        assert select_response.data, "SELECT should return own row"
        row = select_response.data[0]
        assert row["name"] == "Anna"
        assert row["occupation"] == "designer"
        assert row["age"] == 29

    def test_cannot_select_other_users_profile(
        self, authenticated_client, supabase_admin_client
    ):
        """RLS prevents user from reading another user's profile row.

        QA iter-4 F1 fix: previously seeded user_profiles with a bare
        ``uuid.uuid4()`` id. That would violate the FK ``user_profiles.id →
        users.id ON DELETE CASCADE`` (service_role bypasses RLS, not FK
        constraints), so the test would error out before reaching the
        assertion. We now create a real auth.users row first via the admin
        API and clean it up in the finally block.
        """
        admin = supabase_admin_client
        client = authenticated_client

        # Create a second real user so the FK to users.id is satisfied.
        other_email = f"other-{uuid.uuid4().hex[:8]}@test.local"
        other_user = admin.auth.admin.create_user(
            {
                "email": other_email,
                "password": "x" * 24,
                "email_confirm": True,
            }
        )
        other_id = other_user.user.id

        try:
            admin.table("user_profiles").upsert(
                {
                    "id": other_id,
                    "location_city": "Paris",
                    "drug_tolerance": 2,
                    "name": "Other User",
                }
            ).execute()

            # Authenticated user attempts to read the other user's row
            response = (
                client.table("user_profiles")
                .select("name")
                .eq("id", other_id)
                .execute()
            )
            # RLS should filter — result should be empty
            assert response.data == [], (
                "RLS should prevent reading another user's profile row"
            )
        finally:
            # Cleanup: cascade-deletes user_profiles row via FK ON DELETE CASCADE
            try:
                admin.auth.admin.delete_user(other_id)
            except Exception:
                pass



class TestUserProfilesRLSHardening:
    """Tests for RLS WITH CHECK hardening (TP.2)."""

    def test_update_with_check_blocks_id_swap(
        self, authenticated_client, test_user_credentials, supabase_admin_client
    ):
        """User cannot UPDATE a row's id to another user's id (WITH CHECK rejects).

        The Spec 213 migration adds WITH CHECK (id = auth.uid()) to the UPDATE policy,
        which prevents the authenticated user from swapping their row's PK to impersonate
        another user.
        """
        admin = supabase_admin_client
        client = authenticated_client
        user_id = test_user_credentials["user_id"]

        # Attempt to update id to a different UUID (id-swap attack).
        # Two valid success signals (either must hold for WITH CHECK to be enforced):
        #   1. PostgREST raises an exception (``APIError`` or ``PostgrestAPIError``)
        #      — the DB rejected the UPDATE at the policy level.
        #   2. The request returns but ``response.data`` is empty — the row did
        #      not pass the WITH CHECK and no rows were modified.
        #
        # QA iter-3 F1 fix: previously the assertion was inside a bare ``except
        # Exception: pass`` so an ``AssertionError`` (bad data path) would be
        # silently swallowed, making the test unable to fail. Now we catch only
        # the network/DB exception class, and the assertion lives in the
        # ``else`` branch so it cannot be masked.
        other_uuid = str(uuid.uuid4())
        response = None
        try:
            response = (
                client.table("user_profiles")
                .update({"id": other_uuid})
                .eq("id", user_id)
                .execute()
            )
        except APIError:
            # PostgREST raised on WITH CHECK violation — correct behavior.
            return
        # No exception: verify zero rows were updated.
        assert response is not None and (not response.data or response.data == []), (
            "WITH CHECK must block id-swap UPDATE; got response.data="
            f"{getattr(response, 'data', None)!r}"
        )

    def test_delete_subquery_form_allows_own_row(
        self, authenticated_client, supabase_admin_client
    ):
        """User CAN delete their own profile row (DELETE policy uses subquery form).

        The subquery form (USING (id = (SELECT auth.uid()))) is semantically
        equivalent but more explicit. Verify a user can DELETE their own row.
        """
        admin = supabase_admin_client
        client = authenticated_client

        # Create a throwaway user + profile for this test
        email = f"delete-test-{uuid.uuid4().hex[:8]}@test.nikita.local"
        password = uuid.uuid4().hex
        response = admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
        throwaway_id = response.user.id

        # Seed profile
        admin.table("user_profiles").upsert(
            {
                "id": throwaway_id,
                "location_city": "Berlin",
                "drug_tolerance": 3,
            }
        ).execute()

        # Authenticate as throwaway user
        from supabase import create_client

        throwaway_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        throwaway_client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        # Perform delete
        delete_response = (
            throwaway_client.table("user_profiles")
            .delete()
            .eq("id", throwaway_id)
            .execute()
        )
        # QA iter-6 F2: strengthen from ``data is not None`` (always true for
        # supabase-py DELETE responses, even when 0 rows were deleted) to a
        # follow-up SELECT via service_role that proves the row is actually
        # gone. This now falsifies the assertion on ANY failure mode:
        # permission-denied returning data=[], silent zero-row DELETE, or RLS
        # regression that blocks the subquery-form DELETE.
        assert delete_response.data is not None, "DELETE must not error"
        verify_response = (
            admin.table("user_profiles")
            .select("id")
            .eq("id", throwaway_id)
            .execute()
        )
        assert verify_response.data == [], (
            f"Row id={throwaway_id} must not exist after DELETE; "
            f"admin SELECT returned {verify_response.data!r}"
        )

        # Cleanup: sign-out + admin delete. QA iter-6 F3: the try/except on
        # ``Exception`` intentionally does NOT catch BaseException (e.g.
        # KeyboardInterrupt, SystemExit) — those should abort the test run
        # and leak detection is acceptable under those conditions.
        try:
            throwaway_client.auth.sign_out()
        except Exception:
            pass
        try:
            admin.auth.admin.delete_user(throwaway_id)
        except Exception:
            pass
