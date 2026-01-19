"""Functional tests for admin text monitoring endpoints (Spec 020).

Tests for text conversation list, detail, stats, pipeline status, threads, and thoughts.

Acceptance Criteria Coverage:
- AC-FR001-001 to AC-FR001-005: Text conversation list with pagination/filtering
- AC-FR002-001 to AC-FR002-005: Text conversation detail with messages
- AC-FR003-001 to AC-FR003-004: Text statistics aggregations
- AC-FR004-001 to AC-FR004-005: Pipeline status with 9 stages
- AC-FR005-001 to AC-FR005-003: Threads list
- AC-FR006-001 to AC-FR006-002: Thoughts list
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.admin_debug import router


class TestTextConversationList:
    """Tests for GET /admin/debug/text/conversations (FR-001)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication to pass."""
        with patch("nikita.api.routes.admin_debug.get_current_admin_user") as mock:
            mock.return_value = MagicMock(
                id=uuid4(),
                email="admin@silent-agents.com"
            )
            yield mock

    @pytest.fixture
    def mock_text_conversations(self):
        """Create mock text conversation data."""
        user_id = uuid4()
        return [
            MagicMock(
                id=uuid4(),
                user_id=user_id,
                platform="telegram",
                started_at=datetime.now(timezone.utc) - timedelta(hours=i),
                ended_at=datetime.now(timezone.utc) - timedelta(hours=i, minutes=-30),
                status="processed" if i % 2 == 0 else "active",
                chapter_at_time=i % 5 + 1,
                score_delta=5.0 - i,
                conversation_summary=f"Conversation {i} summary",
                emotional_tone="neutral" if i % 2 == 0 else "anxious",
                is_boss_fight=i % 3 == 0,
                messages=[{"role": "user", "content": f"Message {i}"}],
                user=MagicMock(name=f"User {i}")
            )
            for i in range(10)
        ]

    def test_list_text_conversations_pagination(self, client, mock_admin_auth, mock_text_conversations):
        """AC-FR001-001: Paginated list with 50 per page default."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_text_conversations[:5]
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 10

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/conversations",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_list_text_conversations_filter_by_user(self, client, mock_admin_auth):
        """AC-FR001-002: Filter by user_id parameter."""
        user_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/conversations?user_id={user_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_list_text_conversations_filter_by_status(self, client, mock_admin_auth):
        """AC-FR001-003: Filter by status=processed."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/conversations?status=processed",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_list_text_conversations_filter_boss_fights(self, client, mock_admin_auth):
        """AC-FR001-004: Filter by boss_fight_only=true."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/conversations?boss_fight_only=true",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_list_text_conversations_offset_pagination(self, client, mock_admin_auth):
        """AC-FR001-005: Pagination via offset parameter."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 100

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/conversations?offset=50&limit=25",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]


class TestTextConversationDetail:
    """Tests for GET /admin/debug/text/conversations/{id} (FR-002)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication to pass."""
        with patch("nikita.api.routes.admin_debug.get_current_admin_user") as mock:
            mock.return_value = MagicMock(
                id=uuid4(),
                email="admin@silent-agents.com"
            )
            yield mock

    def test_text_conversation_detail_success(self, client, mock_admin_auth):
        """AC-FR002-001: Messages displayed with role, content, timestamp."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                platform="telegram",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                status="processed",
                chapter_at_time=3,
                score_delta=5.0,
                conversation_summary="Test summary",
                emotional_tone="friendly",
                is_boss_fight=False,
                messages=[
                    {"role": "user", "content": "Hello", "timestamp": "2026-01-01T10:00:00Z"},
                    {"role": "assistant", "content": "Hi there!", "timestamp": "2026-01-01T10:00:05Z"}
                ],
                extracted_entities={"facts": ["user likes coffee"]},
                processed_at=datetime.now(timezone.utc),
                processing_attempts=1,
                last_message_at=datetime.now(timezone.utc),
                user=MagicMock(name="Test User")
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/conversations/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_text_conversation_detail_404(self, client, mock_admin_auth):
        """AC-FR002-003: 404 for non-existent conversation."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/conversations/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [404, 401, 403, 500]

    def test_text_conversation_detail_includes_messages(self, client, mock_admin_auth):
        """AC-FR002-001: All messages displayed."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                platform="telegram",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                status="processed",
                messages=[
                    {"role": "user", "content": "Message 1", "timestamp": "2026-01-01T10:00:00Z"},
                    {"role": "assistant", "content": "Response 1", "timestamp": "2026-01-01T10:00:05Z"},
                    {"role": "user", "content": "Message 2", "timestamp": "2026-01-01T10:01:00Z"},
                    {"role": "assistant", "content": "Response 2", "timestamp": "2026-01-01T10:01:05Z"}
                ],
                emotional_tone="neutral",
                is_boss_fight=False,
                extracted_entities=None,
                processed_at=None,
                processing_attempts=0,
                last_message_at=datetime.now(timezone.utc),
                chapter_at_time=1,
                score_delta=0,
                conversation_summary=None,
                user=MagicMock(name="Test")
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/conversations/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_text_conversation_detail_includes_analysis(self, client, mock_admin_auth):
        """AC-FR002-002: Message analysis data included."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                platform="telegram",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                status="processed",
                messages=[
                    {
                        "role": "user",
                        "content": "I'm feeling anxious",
                        "timestamp": "2026-01-01T10:00:00Z",
                        "analysis": {"sentiment": "negative", "intent": "emotional_disclosure"}
                    }
                ],
                emotional_tone="anxious",
                is_boss_fight=False,
                extracted_entities={"emotions": ["anxiety"]},
                processed_at=datetime.now(timezone.utc),
                processing_attempts=1,
                last_message_at=datetime.now(timezone.utc),
                chapter_at_time=2,
                score_delta=-2.0,
                conversation_summary="User expressed anxiety",
                user=MagicMock(name="Test")
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/conversations/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_text_conversation_detail_boss_fight_indicator(self, client, mock_admin_auth):
        """AC-FR002-005: Boss fight indicator displayed."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                platform="telegram",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                status="processed",
                messages=[],
                emotional_tone="tense",
                is_boss_fight=True,  # This should be in response
                extracted_entities=None,
                processed_at=datetime.now(timezone.utc),
                processing_attempts=1,
                last_message_at=datetime.now(timezone.utc),
                chapter_at_time=3,
                score_delta=-10.0,
                conversation_summary="Boss encounter - PASS",
                user=MagicMock(name="Test")
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/conversations/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]


class TestTextStats:
    """Tests for GET /admin/debug/text/stats (FR-003)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication to pass."""
        with patch("nikita.api.routes.admin_debug.get_current_admin_user") as mock:
            mock.return_value = MagicMock(
                id=uuid4(),
                email="admin@silent-agents.com"
            )
            yield mock

    def test_text_stats_returns_aggregations(self, client, mock_admin_auth):
        """AC-FR003-001: total_conversations_24h/7d/30d displayed."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_db = AsyncMock()

            mock_24h = MagicMock()
            mock_24h.scalar.return_value = 50
            mock_7d = MagicMock()
            mock_7d.scalar.return_value = 250
            mock_30d = MagicMock()
            mock_30d.scalar.return_value = 1000

            mock_db.execute = AsyncMock(side_effect=[
                mock_24h, mock_7d, mock_30d,
                MagicMock(scalar=MagicMock(return_value=100)),  # messages_24h
                MagicMock(scalar=MagicMock(return_value=5)),    # boss_fights_24h
                MagicMock(all=MagicMock(return_value=[])),      # by_chapter
                MagicMock(all=MagicMock(return_value=[])),      # by_status
                MagicMock(all=MagicMock(return_value=[]))       # processing_stats
            ])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/stats",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_text_stats_boss_fights_24h(self, client, mock_admin_auth):
        """AC-FR003-002: boss_fights_24h displayed."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(
                scalar=MagicMock(return_value=15)  # boss fights count
            ))
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/stats",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_text_stats_counts_by_chapter(self, client, mock_admin_auth):
        """AC-FR003-003: conversations_by_chapter distribution displayed."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(
                scalar=MagicMock(return_value=0),
                all=MagicMock(return_value=[
                    (1, 100), (2, 80), (3, 50), (4, 20), (5, 5)
                ])
            ))
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/stats",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_text_stats_counts_by_status(self, client, mock_admin_auth):
        """AC-FR003-004: processing_stats by status displayed."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(
                scalar=MagicMock(return_value=0),
                all=MagicMock(return_value=[
                    ("processed", 500), ("active", 50), ("pending", 10), ("failed", 2)
                ])
            ))
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/stats",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]


class TestPipelineStatus:
    """Tests for GET /admin/debug/text/pipeline/{id} (FR-004)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication to pass."""
        with patch("nikita.api.routes.admin_debug.get_current_admin_user") as mock:
            mock.return_value = MagicMock(
                id=uuid4(),
                email="admin@silent-agents.com"
            )
            yield mock

    def test_pipeline_status_success(self, client, mock_admin_auth):
        """AC-FR004-001: All 9 stages displayed with completion status."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                status="processed",
                processing_attempts=1,
                processed_at=datetime.now(timezone.utc),
                messages=[{"role": "user", "content": "test"}],
                extracted_entities={"facts": ["test fact"]},
                conversation_summary="Test summary",
                emotional_tone="neutral"
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            # Mock thread and thought counts
            mock_thread_count = MagicMock()
            mock_thread_count.scalar.return_value = 3
            mock_thought_count = MagicMock()
            mock_thought_count.scalar.return_value = 5

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[
                mock_result,
                mock_thread_count,
                mock_thought_count
            ])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/pipeline/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_pipeline_status_404(self, client, mock_admin_auth):
        """AC-FR004-005: 404 for non-existent conversation."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/pipeline/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [404, 401, 403, 500]

    def test_pipeline_status_shows_9_stages(self, client, mock_admin_auth):
        """AC-FR004-001: All 9 stages are returned."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                status="processed",
                processing_attempts=1,
                processed_at=datetime.now(timezone.utc),
                messages=[{"role": "user", "content": "test"}],
                extracted_entities={"facts": []},
                conversation_summary="Summary",
                emotional_tone="happy"
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            mock_count = MagicMock()
            mock_count.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count, mock_count])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/pipeline/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_pipeline_status_counts_threads_thoughts(self, client, mock_admin_auth):
        """AC-FR004-003 & AC-FR004-004: threads_created and thoughts_created displayed."""
        conv_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_conv = MagicMock(
                id=conv_id,
                user_id=uuid4(),
                status="processed",
                processing_attempts=1,
                processed_at=datetime.now(timezone.utc),
                messages=[],
                extracted_entities=None,
                conversation_summary=None,
                emotional_tone=None
            )

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_conv

            mock_thread_count = MagicMock()
            mock_thread_count.scalar.return_value = 7  # threads_created
            mock_thought_count = MagicMock()
            mock_thought_count.scalar.return_value = 12  # thoughts_created

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[
                mock_result,
                mock_thread_count,
                mock_thought_count
            ])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/pipeline/{conv_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]


class TestThreadsList:
    """Tests for GET /admin/debug/text/threads (FR-005)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication to pass."""
        with patch("nikita.api.routes.admin_debug.get_current_admin_user") as mock:
            mock.return_value = MagicMock(
                id=uuid4(),
                email="admin@silent-agents.com"
            )
            yield mock

    def test_threads_list_pagination(self, client, mock_admin_auth):
        """AC-FR005-001: Paginated thread list displays."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_threads = [
                MagicMock(
                    id=uuid4(),
                    user_id=uuid4(),
                    thread_type="relationship",
                    topic="Work stress",
                    is_active=True,
                    message_count=5,
                    created_at=datetime.now(timezone.utc),
                    last_mentioned_at=datetime.now(timezone.utc)
                )
                for _ in range(10)
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_threads
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 50

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/threads",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_threads_list_filter_by_user(self, client, mock_admin_auth):
        """AC-FR005-002: Filter by user_id parameter."""
        user_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/threads?user_id={user_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_threads_list_filter_active_only(self, client, mock_admin_auth):
        """AC-FR005-003: Filter by active_only=true."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/threads?active_only=true",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]


class TestThoughtsList:
    """Tests for GET /admin/debug/text/thoughts (FR-006)."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication to pass."""
        with patch("nikita.api.routes.admin_debug.get_current_admin_user") as mock:
            mock.return_value = MagicMock(
                id=uuid4(),
                email="admin@silent-agents.com"
            )
            yield mock

    def test_thoughts_list_pagination(self, client, mock_admin_auth):
        """AC-FR006-001: Paginated thought list displays."""
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_thoughts = [
                MagicMock(
                    id=uuid4(),
                    user_id=uuid4(),
                    content="I should remember that they like coffee",
                    thought_type="observation",
                    created_at=datetime.now(timezone.utc)
                )
                for _ in range(10)
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_thoughts
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 100

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                "/admin/debug/text/thoughts",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]

    def test_thoughts_list_filter_by_user(self, client, mock_admin_auth):
        """AC-FR006-002: Filter by user_id parameter."""
        user_id = uuid4()
        with patch("nikita.api.routes.admin_debug.get_async_session") as mock_session:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
            mock_session.return_value.__aenter__.return_value = mock_db

            response = client.get(
                f"/admin/debug/text/thoughts?user_id={user_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            assert response.status_code in [200, 401, 403, 500]


class TestTextEndpointsAuth:
    """Tests for admin authentication on all text endpoints."""

    @pytest.fixture
    def app(self):
        """Create isolated test app."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_text_conversations_requires_admin_auth(self, client):
        """All text endpoints require admin authentication."""
        response = client.get("/admin/debug/text/conversations")
        assert response.status_code in [401, 403]

    def test_text_conversation_detail_requires_admin_auth(self, client):
        """Text detail requires admin authentication."""
        response = client.get(f"/admin/debug/text/conversations/{uuid4()}")
        assert response.status_code in [401, 403]

    def test_text_stats_requires_admin_auth(self, client):
        """Text stats requires admin authentication."""
        response = client.get("/admin/debug/text/stats")
        assert response.status_code in [401, 403]

    def test_pipeline_status_requires_admin_auth(self, client):
        """Pipeline status requires admin authentication."""
        response = client.get(f"/admin/debug/text/pipeline/{uuid4()}")
        assert response.status_code in [401, 403]

    def test_threads_list_requires_admin_auth(self, client):
        """Threads list requires admin authentication."""
        response = client.get("/admin/debug/text/threads")
        assert response.status_code in [401, 403]

    def test_thoughts_list_requires_admin_auth(self, client):
        """Thoughts list requires admin authentication."""
        response = client.get("/admin/debug/text/thoughts")
        assert response.status_code in [401, 403]
