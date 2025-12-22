"""
Supabase Helper for E2E Tests

Provides utilities for database operations in E2E tests:
- Creating pending registrations
- Cleaning up test data
- Verifying user creation
- Conversation and message verification
- Score history and game state queries

For Claude Code execution, uses MCP tools:
- mcp__supabase__execute_sql

For CI/CD, uses Supabase Python client with service key.
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict


@dataclass
class PendingRegistration:
    """Pending registration record."""
    telegram_id: int
    email: str
    created_at: datetime
    expires_at: datetime


@dataclass
class User:
    """User record."""
    id: uuid.UUID
    telegram_id: Optional[int]
    supabase_user_id: Optional[uuid.UUID]
    created_at: datetime
    relationship_score: float


@dataclass
class Conversation:
    """Conversation record."""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    status: str
    messages_count: int = 0


@dataclass
class ScoreHistoryEntry:
    """Score history record."""
    id: uuid.UUID
    user_id: uuid.UUID
    relationship_score: float
    chapter: int
    recorded_at: datetime
    event_type: Optional[str] = None


@dataclass
class UserMetrics:
    """User metrics record."""
    user_id: uuid.UUID
    relationship_score: float
    chapter: int
    messages_sent: int
    boss_encounters: int
    last_activity: Optional[datetime] = None


@dataclass
class VerificationResult:
    """Result of a database verification check."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None


class SupabaseHelper:
    """Helper class for Supabase database operations in E2E tests."""

    def __init__(self):
        """Initialize Supabase helper."""
        self.supabase_url = os.getenv(
            "SUPABASE_URL",
            "https://vlvlwmolfdpzdfmtipji.supabase.co"
        )
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")

    # ==================== SQL Query Templates ====================

    @staticmethod
    def sql_create_pending(telegram_id: int, email: str) -> str:
        """Generate SQL to create a pending registration."""
        return f"""
            INSERT INTO pending_registrations (telegram_id, email, created_at, expires_at)
            VALUES (
                {telegram_id},
                '{email}',
                NOW(),
                NOW() + INTERVAL '15 minutes'
            )
            ON CONFLICT (telegram_id) DO UPDATE
            SET email = EXCLUDED.email,
                created_at = NOW(),
                expires_at = NOW() + INTERVAL '15 minutes'
            RETURNING telegram_id, email, created_at, expires_at;
        """

    @staticmethod
    def sql_get_pending_by_email(email: str) -> str:
        """Generate SQL to get pending registration by email."""
        return f"""
            SELECT telegram_id, email, created_at, expires_at
            FROM pending_registrations
            WHERE email = '{email}'
            LIMIT 1;
        """

    @staticmethod
    def sql_delete_pending(telegram_id: int) -> str:
        """Generate SQL to delete a pending registration."""
        return f"""
            DELETE FROM pending_registrations
            WHERE telegram_id = {telegram_id};
        """

    @staticmethod
    def sql_get_user_by_telegram_id(telegram_id: int) -> str:
        """Generate SQL to get user by Telegram ID."""
        return f"""
            SELECT u.id, u.telegram_id, u.supabase_user_id, u.created_at,
                   COALESCE(m.relationship_score, 50.0) as relationship_score
            FROM users u
            LEFT JOIN user_metrics m ON u.id = m.user_id
            WHERE u.telegram_id = {telegram_id}
            LIMIT 1;
        """

    @staticmethod
    def sql_get_user_by_supabase_id(supabase_user_id: str) -> str:
        """Generate SQL to get user by Supabase user ID."""
        return f"""
            SELECT u.id, u.telegram_id, u.supabase_user_id, u.created_at,
                   COALESCE(m.relationship_score, 50.0) as relationship_score
            FROM users u
            LEFT JOIN user_metrics m ON u.id = m.user_id
            WHERE u.supabase_user_id = '{supabase_user_id}'
            LIMIT 1;
        """

    @staticmethod
    def sql_delete_user_by_telegram_id(telegram_id: int) -> str:
        """Generate SQL to delete user and related data by Telegram ID."""
        return f"""
            -- Delete metrics first (foreign key)
            DELETE FROM user_metrics
            WHERE user_id IN (SELECT id FROM users WHERE telegram_id = {telegram_id});

            -- Delete user
            DELETE FROM users
            WHERE telegram_id = {telegram_id};
        """

    @staticmethod
    def sql_count_users_by_telegram_id(telegram_id: int) -> str:
        """Generate SQL to count users with a specific Telegram ID."""
        return f"""
            SELECT COUNT(*) as count
            FROM users
            WHERE telegram_id = {telegram_id};
        """

    @staticmethod
    def sql_update_user_telegram_id(
        supabase_user_id: str,
        telegram_id: Optional[int]
    ) -> str:
        """Generate SQL to update user's Telegram ID."""
        telegram_val = f"{telegram_id}" if telegram_id else "NULL"
        return f"""
            UPDATE users
            SET telegram_id = {telegram_val}
            WHERE supabase_user_id = '{supabase_user_id}'
            RETURNING id, telegram_id, supabase_user_id;
        """

    @staticmethod
    def sql_create_test_user(
        user_id: str,
        telegram_id: Optional[int] = None,
        supabase_user_id: Optional[str] = None
    ) -> str:
        """Generate SQL to create a test user (for portal-first scenario)."""
        telegram_val = f"{telegram_id}" if telegram_id else "NULL"
        supabase_val = f"'{supabase_user_id}'" if supabase_user_id else "NULL"
        return f"""
            INSERT INTO users (id, telegram_id, supabase_user_id, created_at)
            VALUES (
                '{user_id}',
                {telegram_val},
                {supabase_val},
                NOW()
            )
            ON CONFLICT (id) DO NOTHING
            RETURNING id, telegram_id, supabase_user_id, created_at;
        """

    # ==================== Conversation SQL Templates ====================

    @staticmethod
    def sql_get_conversations_by_user(user_id: str) -> str:
        """Generate SQL to get all conversations for a user."""
        return f"""
            SELECT id, user_id, created_at, status,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as messages_count
            FROM conversations c
            WHERE user_id = '{user_id}'
            ORDER BY created_at DESC;
        """

    @staticmethod
    def sql_get_conversations_by_telegram_id(telegram_id: int) -> str:
        """Generate SQL to get all conversations for a user by Telegram ID."""
        return f"""
            SELECT c.id, c.user_id, c.created_at, c.status,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as messages_count
            FROM conversations c
            JOIN users u ON c.user_id = u.id
            WHERE u.telegram_id = {telegram_id}
            ORDER BY c.created_at DESC;
        """

    @staticmethod
    def sql_get_latest_conversation(telegram_id: int) -> str:
        """Generate SQL to get the latest conversation for a user."""
        return f"""
            SELECT c.id, c.user_id, c.created_at, c.status,
                   (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) as messages_count
            FROM conversations c
            JOIN users u ON c.user_id = u.id
            WHERE u.telegram_id = {telegram_id}
            ORDER BY c.created_at DESC
            LIMIT 1;
        """

    @staticmethod
    def sql_get_conversation_messages(conversation_id: str) -> str:
        """Generate SQL to get all messages in a conversation."""
        return f"""
            SELECT id, conversation_id, role, content, created_at
            FROM messages
            WHERE conversation_id = '{conversation_id}'
            ORDER BY created_at ASC;
        """

    @staticmethod
    def sql_count_messages_by_telegram_id(telegram_id: int) -> str:
        """Generate SQL to count total messages for a user."""
        return f"""
            SELECT COUNT(*) as count
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE u.telegram_id = {telegram_id};
        """

    # ==================== Score & Metrics SQL Templates ====================

    @staticmethod
    def sql_get_user_metrics(telegram_id: int) -> str:
        """Generate SQL to get full user metrics."""
        return f"""
            SELECT m.user_id, m.relationship_score, m.chapter,
                   m.messages_sent, m.boss_encounters, m.last_activity
            FROM user_metrics m
            JOIN users u ON m.user_id = u.id
            WHERE u.telegram_id = {telegram_id}
            LIMIT 1;
        """

    @staticmethod
    def sql_get_score_history(telegram_id: int, limit: int = 10) -> str:
        """Generate SQL to get score history for a user."""
        return f"""
            SELECT sh.id, sh.user_id, sh.relationship_score, sh.chapter,
                   sh.recorded_at, sh.event_type
            FROM score_history sh
            JOIN users u ON sh.user_id = u.id
            WHERE u.telegram_id = {telegram_id}
            ORDER BY sh.recorded_at DESC
            LIMIT {limit};
        """

    @staticmethod
    def sql_get_latest_score(telegram_id: int) -> str:
        """Generate SQL to get the latest score for a user."""
        return f"""
            SELECT m.relationship_score, m.chapter
            FROM user_metrics m
            JOIN users u ON m.user_id = u.id
            WHERE u.telegram_id = {telegram_id}
            LIMIT 1;
        """

    # ==================== Full Cleanup SQL Templates ====================

    @staticmethod
    def sql_full_cleanup_by_telegram_id(telegram_id: int) -> str:
        """Generate SQL to delete ALL data for a test user (comprehensive cleanup)."""
        return f"""
            -- Delete messages first (references conversations)
            DELETE FROM messages
            WHERE conversation_id IN (
                SELECT c.id FROM conversations c
                JOIN users u ON c.user_id = u.id
                WHERE u.telegram_id = {telegram_id}
            );

            -- Delete conversations (references users)
            DELETE FROM conversations
            WHERE user_id IN (SELECT id FROM users WHERE telegram_id = {telegram_id});

            -- Delete score history (references users)
            DELETE FROM score_history
            WHERE user_id IN (SELECT id FROM users WHERE telegram_id = {telegram_id});

            -- Delete user metrics (references users)
            DELETE FROM user_metrics
            WHERE user_id IN (SELECT id FROM users WHERE telegram_id = {telegram_id});

            -- Delete pending registrations
            DELETE FROM pending_registrations WHERE telegram_id = {telegram_id};

            -- Delete user (finally)
            DELETE FROM users WHERE telegram_id = {telegram_id};
        """

    @staticmethod
    def sql_full_cleanup_by_email(email: str) -> str:
        """Generate SQL to delete ALL data for a test user by email."""
        return f"""
            -- Get user_id first for cascading deletes
            WITH target_user AS (
                SELECT u.id, u.telegram_id
                FROM users u
                WHERE u.email = '{email}'
                   OR u.supabase_user_id IN (
                       SELECT id FROM auth.users WHERE email = '{email}'
                   )
            )
            -- Delete in order respecting foreign keys
            DELETE FROM messages WHERE conversation_id IN (
                SELECT c.id FROM conversations c WHERE c.user_id IN (SELECT id FROM target_user)
            );
            DELETE FROM conversations WHERE user_id IN (SELECT id FROM target_user);
            DELETE FROM score_history WHERE user_id IN (SELECT id FROM target_user);
            DELETE FROM user_metrics WHERE user_id IN (SELECT id FROM target_user);
            DELETE FROM pending_registrations WHERE email = '{email}';
            DELETE FROM users WHERE id IN (SELECT id FROM target_user);
        """

    @staticmethod
    def sql_cleanup_test_range(
        min_telegram_id: int = 900000000,
        max_telegram_id: int = 999999999
    ) -> str:
        """Generate SQL to cleanup ALL test users in the test ID range."""
        return f"""
            -- Delete all test data in the 900M-999M Telegram ID range
            DELETE FROM messages
            WHERE conversation_id IN (
                SELECT c.id FROM conversations c
                JOIN users u ON c.user_id = u.id
                WHERE u.telegram_id BETWEEN {min_telegram_id} AND {max_telegram_id}
            );

            DELETE FROM conversations
            WHERE user_id IN (
                SELECT id FROM users
                WHERE telegram_id BETWEEN {min_telegram_id} AND {max_telegram_id}
            );

            DELETE FROM score_history
            WHERE user_id IN (
                SELECT id FROM users
                WHERE telegram_id BETWEEN {min_telegram_id} AND {max_telegram_id}
            );

            DELETE FROM user_metrics
            WHERE user_id IN (
                SELECT id FROM users
                WHERE telegram_id BETWEEN {min_telegram_id} AND {max_telegram_id}
            );

            DELETE FROM pending_registrations
            WHERE telegram_id BETWEEN {min_telegram_id} AND {max_telegram_id};

            DELETE FROM users
            WHERE telegram_id BETWEEN {min_telegram_id} AND {max_telegram_id};
        """

    # ==================== Verification SQL Templates ====================

    @staticmethod
    def sql_verify_registration_complete(telegram_id: int) -> str:
        """Generate SQL to verify complete registration (user exists, pending deleted)."""
        return f"""
            SELECT
                (SELECT COUNT(*) FROM users WHERE telegram_id = {telegram_id}) as user_count,
                (SELECT COUNT(*) FROM pending_registrations WHERE telegram_id = {telegram_id}) as pending_count,
                (SELECT COUNT(*) FROM user_metrics WHERE user_id IN (
                    SELECT id FROM users WHERE telegram_id = {telegram_id}
                )) as metrics_count;
        """

    @staticmethod
    def sql_verify_conversation_exists(telegram_id: int) -> str:
        """Generate SQL to verify at least one conversation exists."""
        return f"""
            SELECT
                (SELECT COUNT(*) FROM conversations WHERE user_id IN (
                    SELECT id FROM users WHERE telegram_id = {telegram_id}
                )) as conversation_count,
                (SELECT COUNT(*) FROM messages WHERE conversation_id IN (
                    SELECT c.id FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE u.telegram_id = {telegram_id}
                )) as message_count;
        """

    @staticmethod
    def sql_get_test_users_count() -> str:
        """Generate SQL to count test users in the test range."""
        return """
            SELECT COUNT(*) as count
            FROM users
            WHERE telegram_id BETWEEN 900000000 AND 999999999;
        """

    # ==================== Utility Methods ====================

    @staticmethod
    def generate_test_telegram_id() -> int:
        """Generate a unique test Telegram ID in the 900M-999M range."""
        import random
        # Use range unlikely to conflict with real users
        return random.randint(900000000, 999999999)

    @staticmethod
    def generate_test_user_id() -> str:
        """Generate a unique test user UUID."""
        return str(uuid.uuid4())

    @staticmethod
    def generate_test_email(base_email: str, telegram_id: int) -> str:
        """Generate a unique test email using + addressing.

        Args:
            base_email: Base email (e.g., 'simon.yang.ch@gmail.com')
            telegram_id: Telegram ID for uniqueness

        Returns:
            Email like 'simon.yang.ch+test912345678@gmail.com'
        """
        parts = base_email.split('@')
        if len(parts) != 2:
            raise ValueError(f"Invalid email format: {base_email}")
        return f"{parts[0]}+test{telegram_id}@{parts[1]}"

    @staticmethod
    def parse_mcp_result(result: Any) -> List[Dict[str, Any]]:
        """Parse MCP SQL execution result into list of dicts.

        Args:
            result: Raw result from mcp__supabase__execute_sql

        Returns:
            List of row dictionaries
        """
        if result is None:
            return []

        # Handle various MCP result formats
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            if 'rows' in result:
                return result['rows']
            if 'data' in result:
                return result['data']
            return [result]

        return []

    @staticmethod
    def verify_registration_from_result(result: Any) -> VerificationResult:
        """Verify registration completion from SQL result.

        Args:
            result: Result from sql_verify_registration_complete query

        Returns:
            VerificationResult with success status and details
        """
        rows = SupabaseHelper.parse_mcp_result(result)
        if not rows:
            return VerificationResult(
                success=False,
                message="No verification data returned",
                data=None
            )

        row = rows[0]
        user_count = row.get('user_count', 0)
        pending_count = row.get('pending_count', 0)
        metrics_count = row.get('metrics_count', 0)

        if user_count == 1 and pending_count == 0 and metrics_count == 1:
            return VerificationResult(
                success=True,
                message="Registration complete: user created, pending deleted, metrics initialized",
                data=row
            )

        issues = []
        if user_count != 1:
            issues.append(f"Expected 1 user, found {user_count}")
        if pending_count != 0:
            issues.append(f"Expected 0 pending, found {pending_count}")
        if metrics_count != 1:
            issues.append(f"Expected 1 metrics, found {metrics_count}")

        return VerificationResult(
            success=False,
            message=f"Registration incomplete: {'; '.join(issues)}",
            data=row,
            expected={'user_count': 1, 'pending_count': 0, 'metrics_count': 1},
            actual={'user_count': user_count, 'pending_count': pending_count, 'metrics_count': metrics_count}
        )


# ==================== Convenience Functions ====================

def create_pending_sql(telegram_id: int, email: str) -> str:
    """Convenience function to create pending registration SQL."""
    return SupabaseHelper.sql_create_pending(telegram_id, email)


def cleanup_test_data_sql(telegram_id: int, email: str) -> str:
    """Generate SQL to cleanup all test data."""
    return f"""
        -- Delete pending registration
        DELETE FROM pending_registrations WHERE telegram_id = {telegram_id};
        DELETE FROM pending_registrations WHERE email = '{email}';

        -- Delete user metrics (foreign key constraint)
        DELETE FROM user_metrics
        WHERE user_id IN (SELECT id FROM users WHERE telegram_id = {telegram_id});

        -- Delete user
        DELETE FROM users WHERE telegram_id = {telegram_id};
    """


def verify_user_created_sql(telegram_id: int) -> str:
    """Generate SQL to verify user was created."""
    return SupabaseHelper.sql_get_user_by_telegram_id(telegram_id)


def verify_pending_deleted_sql(email: str) -> str:
    """Generate SQL to verify pending registration was deleted."""
    return f"""
        SELECT COUNT(*) as count
        FROM pending_registrations
        WHERE email = '{email}';
    """
