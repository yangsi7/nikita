"""Tests for portal emotional state endpoints.

TDD tests for Spec 047: Deep Insights — Emotional state, life events, thoughts,
narrative arcs, social circle, detailed score history, and threads.

Acceptance Criteria:
- AC-T47.1: /emotional-state returns current 4D state
- AC-T47.2: /emotional-state/history returns time-filtered points
- AC-T47.3: /life-events returns events with optional date filter
- AC-T47.4: /thoughts returns paginated thoughts with type filter
- AC-T47.5: /narrative-arcs returns active/resolved arcs
- AC-T47.6: /social-circle returns friends list
- AC-T47.7: /score-history/detailed returns metric deltas from event_details
- AC-T47.8: /threads returns filtered threads with open_count
"""

from datetime import datetime, timedelta, timezone, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.dependencies.auth import get_current_user_id
from nikita.api.routes.portal import router
from nikita.db.database import get_async_session
from nikita.emotional_state.models import ConflictState, EmotionalStateModel
from nikita.life_simulation.models import (
    EmotionalImpact,
    EventDomain,
    EventType,
    LifeEvent,
    TimeOfDay,
)


UTC = timezone.utc


class TestEmotionalState:
    """Test suite for /emotional-state endpoint (AC-T47.1)."""

    @pytest.fixture
    def mock_user_id(self):
        """Create a mock user ID."""
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        """Create isolated test app with dependency overrides."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def unauthed_app(self):
        """Create test app without auth override (for auth tests)."""
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client with dependency overrides."""
        return TestClient(app)

    @pytest.fixture
    def unauthed_client(self, unauthed_app):
        """Create test client without auth override."""
        return TestClient(unauthed_app)

    def test_emotional_state_endpoint_exists(self, unauthed_client):
        """Endpoint is registered at /portal/emotional-state."""
        response = unauthed_client.get("/portal/emotional-state")
        # Should return 401/403 without auth, not 404
        assert response.status_code in [401, 403]

    def test_emotional_state_requires_auth(self, unauthed_client):
        """GET /emotional-state requires authentication."""
        response = unauthed_client.get("/portal/emotional-state")
        assert response.status_code in [401, 403]

    def test_emotional_state_returns_default_for_new_user(self, client, mock_user_id):
        """AC-T47.1: Returns default state (all 0.5) when no state exists."""
        with patch("nikita.api.routes.portal.get_state_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_current_state.return_value = None
            mock_get_store.return_value = mock_store

            response = client.get("/portal/emotional-state")

            assert response.status_code == 200
            data = response.json()
            # Default state: all 0.5, no conflict
            assert data["arousal"] == 0.5
            assert data["valence"] == 0.5
            assert data["dominance"] == 0.5
            assert data["intimacy"] == 0.5
            assert data["conflict_state"] == ConflictState.NONE.value
            assert data["conflict_started_at"] is None
            assert data["conflict_trigger"] is None

    def test_emotional_state_returns_actual_state(self, client, mock_user_id):
        """AC-T47.1: Returns actual state when state exists."""
        state_id = uuid4()
        now = datetime.now(UTC)
        mock_state = EmotionalStateModel(
            user_id=mock_user_id,
            state_id=state_id,
            arousal=0.7,
            valence=0.6,
            dominance=0.8,
            intimacy=0.9,
            conflict_state=ConflictState.COLD,
            conflict_started_at=now - timedelta(hours=2),
            conflict_trigger="forgot anniversary",
            last_updated=now,
        )

        with patch("nikita.api.routes.portal.get_state_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_current_state.return_value = mock_state
            mock_get_store.return_value = mock_store

            response = client.get("/portal/emotional-state")

            assert response.status_code == 200
            data = response.json()
            assert data["state_id"] == str(state_id)
            assert data["arousal"] == 0.7
            assert data["valence"] == 0.6
            assert data["dominance"] == 0.8
            assert data["intimacy"] == 0.9
            assert data["conflict_state"] == ConflictState.COLD.value
            assert data["conflict_trigger"] == "forgot anniversary"
            assert "description" in data


class TestEmotionalStateHistory:
    """Test suite for /emotional-state/history endpoint (AC-T47.2)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_emotional_state_history_returns_empty_for_new_user(self, client, mock_user_id):
        """AC-T47.2: Returns empty list when no history exists."""
        with patch("nikita.api.routes.portal.get_state_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_state_history.return_value = []
            mock_get_store.return_value = mock_store

            response = client.get("/portal/emotional-state/history?hours=24")

            assert response.status_code == 200
            data = response.json()
            assert data["points"] == []
            assert data["total_count"] == 0

    def test_emotional_state_history_filters_by_hours_window(self, client, mock_user_id):
        """AC-T47.2: Returns points within hours window."""
        now = datetime.now(UTC)
        # Create states: one within window, one outside
        states = [
            EmotionalStateModel(
                user_id=mock_user_id,
                state_id=uuid4(),
                arousal=0.7,
                valence=0.6,
                dominance=0.8,
                intimacy=0.9,
                conflict_state=ConflictState.NONE,
                last_updated=now - timedelta(hours=12),  # Within 24h
            ),
            EmotionalStateModel(
                user_id=mock_user_id,
                state_id=uuid4(),
                arousal=0.5,
                valence=0.5,
                dominance=0.5,
                intimacy=0.5,
                conflict_state=ConflictState.NONE,
                last_updated=now - timedelta(hours=30),  # Outside 24h
            ),
        ]

        with patch("nikita.api.routes.portal.get_state_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_state_history.return_value = states
            mock_get_store.return_value = mock_store

            response = client.get("/portal/emotional-state/history?hours=24")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1  # Only one within window
            assert data["points"][0]["arousal"] == 0.7

    def test_emotional_state_history_default_24_hours(self, client, mock_user_id):
        """AC-T47.2: Defaults to 24 hours when hours param omitted."""
        with patch("nikita.api.routes.portal.get_state_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_state_history.return_value = []
            mock_get_store.return_value = mock_store

            response = client.get("/portal/emotional-state/history")

            assert response.status_code == 200
            mock_store.get_state_history.assert_called_once()


class TestLifeEvents:
    """Test suite for /life-events endpoint (AC-T47.3)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_life_events_returns_empty_for_new_user(self, client, mock_user_id):
        """AC-T47.3: Returns empty list when no events exist."""
        with patch("nikita.api.routes.portal.get_event_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_events_for_date.return_value = []
            mock_get_store.return_value = mock_store

            response = client.get("/portal/life-events")

            assert response.status_code == 200
            data = response.json()
            assert data["events"] == []
            assert data["total_count"] == 0
            assert "date" in data

    def test_life_events_accepts_date_param(self, client, mock_user_id):
        """AC-T47.3: Accepts date query param in YYYY-MM-DD format."""
        target_date = "2026-02-10"

        with patch("nikita.api.routes.portal.get_event_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_events_for_date.return_value = []
            mock_get_store.return_value = mock_store

            response = client.get(f"/portal/life-events?date_str={target_date}")

            assert response.status_code == 200
            data = response.json()
            assert data["date"] == target_date

    def test_life_events_returns_events_for_date(self, client, mock_user_id):
        """AC-T47.3: Returns events for specified date."""
        event = LifeEvent(
            user_id=mock_user_id,
            event_id=uuid4(),
            event_date=date(2026, 2, 10),
            time_of_day=TimeOfDay.MORNING,
            domain=EventDomain.WORK,
            event_type=EventType.WIN,
            description="Got promotion at work today",
            entities=["boss", "team"],
            importance=0.8,
            emotional_impact=EmotionalImpact(
                arousal_delta=0.2,
                valence_delta=0.3,
                dominance_delta=0.1,
                intimacy_delta=0.0,
            ),
            created_at=datetime.now(UTC),
        )

        with patch("nikita.api.routes.portal.get_event_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_events_for_date.return_value = [event]
            mock_get_store.return_value = mock_store

            response = client.get("/portal/life-events?date_str=2026-02-10")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1
            assert data["events"][0]["description"] == "Got promotion at work today"
            assert data["events"][0]["importance"] == 0.8
            assert data["events"][0]["emotional_impact"]["valence_delta"] == 0.3

    def test_life_events_invalid_date_format(self, client, mock_user_id):
        """AC-T47.3: Returns 422 for invalid date format."""
        response = client.get("/portal/life-events?date_str=invalid-date")

        assert response.status_code == 422


class TestThoughts:
    """Test suite for /thoughts endpoint (AC-T47.4)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_thoughts_returns_paginated_results(self, client, mock_user_id):
        """AC-T47.4: Returns paginated thoughts with has_more flag."""
        # Create 25 mock thoughts
        thoughts = [
            MagicMock(
                id=uuid4(),
                thought_type="observation",
                content=f"Thought {i}",
                source_conversation_id=None,
                expires_at=None,
                used_at=None,
                psychological_context=None,
                created_at=datetime.now(UTC),
            )
            for i in range(25)
        ]

        with patch("nikita.api.routes.portal.NikitaThoughtRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_paginated.return_value = (thoughts[:20], 25)
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/thoughts?limit=20&offset=0")

            assert response.status_code == 200
            data = response.json()
            assert len(data["thoughts"]) == 20
            assert data["total_count"] == 25
            assert data["has_more"] is True

    def test_thoughts_filters_by_type(self, client, mock_user_id):
        """AC-T47.4: Filters thoughts by type parameter."""
        with patch("nikita.api.routes.portal.NikitaThoughtRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_paginated.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/thoughts?type=observation")

            assert response.status_code == 200
            mock_repo.get_paginated.assert_called_once()
            call_args = mock_repo.get_paginated.call_args
            assert call_args[1]["thought_type"] == "observation"

    def test_thoughts_all_type_passes_none(self, client, mock_user_id):
        """AC-T47.4: type=all passes None to repository."""
        with patch("nikita.api.routes.portal.NikitaThoughtRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_paginated.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/thoughts?type=all")

            assert response.status_code == 200
            call_args = mock_repo.get_paginated.call_args
            assert call_args[1]["thought_type"] is None


class TestNarrativeArcs:
    """Test suite for /narrative-arcs endpoint (AC-T47.5)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_narrative_arcs_returns_only_active_by_default(self, client, mock_user_id):
        """AC-T47.5: Returns only active arcs when active_only=true (default)."""
        active_arc = MagicMock(
            id=uuid4(),
            template_name="career_success",
            category="professional",
            current_stage="rising",
            stage_progress=2,
            conversations_in_arc=3,
            max_conversations=7,
            current_description="Job interview process",
            involved_characters=["hiring manager"],
            emotional_impact={"valence": 0.3},
            is_active=True,
            started_at=datetime.now(UTC),
            resolved_at=None,
        )

        with patch("nikita.api.routes.portal.NarrativeArcRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_active_arcs.return_value = [active_arc]
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/narrative-arcs")

            assert response.status_code == 200
            data = response.json()
            assert len(data["active_arcs"]) == 1
            assert len(data["resolved_arcs"]) == 0
            assert data["total_count"] == 1
            mock_repo.get_active_arcs.assert_called_once()

    def test_narrative_arcs_returns_both_when_active_only_false(self, client, mock_user_id):
        """AC-T47.5: Returns active + resolved when active_only=false."""
        active_arc = MagicMock(
            id=uuid4(),
            template_name="career_success",
            category="professional",
            current_stage="rising",
            stage_progress=2,
            conversations_in_arc=3,
            max_conversations=7,
            current_description="Job interview",
            involved_characters=[],
            emotional_impact={},
            is_active=True,
            started_at=datetime.now(UTC),
            resolved_at=None,
        )
        resolved_arc = MagicMock(
            id=uuid4(),
            template_name="family_conflict",
            category="personal",
            current_stage="resolved",
            stage_progress=5,
            conversations_in_arc=7,
            max_conversations=7,
            current_description="Reconciled with sister",
            involved_characters=["sister"],
            emotional_impact={},
            is_active=False,
            started_at=datetime.now(UTC) - timedelta(days=14),
            resolved_at=datetime.now(UTC),
        )

        with patch("nikita.api.routes.portal.NarrativeArcRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_all_arcs.return_value = [active_arc, resolved_arc]
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/narrative-arcs?active_only=false")

            assert response.status_code == 200
            data = response.json()
            assert len(data["active_arcs"]) == 1
            assert len(data["resolved_arcs"]) == 1
            assert data["total_count"] == 2


class TestSocialCircle:
    """Test suite for /social-circle endpoint (AC-T47.6)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_social_circle_returns_empty_for_new_user(self, client, mock_user_id):
        """AC-T47.6: Returns empty list when no friends exist."""
        with patch("nikita.api.routes.portal.SocialCircleRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_circle.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/social-circle")

            assert response.status_code == 200
            data = response.json()
            assert data["friends"] == []
            assert data["total_count"] == 0

    def test_social_circle_returns_friends_list(self, client, mock_user_id):
        """AC-T47.6: Returns friends with full details."""
        friend = MagicMock(
            id=uuid4(),
            friend_name="Emma",
            friend_role="best_friend",
            age=27,
            occupation="graphic designer",
            personality="creative and outgoing",
            relationship_to_nikita="College roommate, close confidant",
            storyline_potential=["career_advice", "relationship_drama"],
            is_active=True,
        )

        with patch("nikita.api.routes.portal.SocialCircleRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_circle.return_value = [friend]
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/social-circle")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1
            assert data["friends"][0]["friend_name"] == "Emma"
            assert data["friends"][0]["age"] == 27
            assert data["friends"][0]["is_active"] is True


class TestDetailedScoreHistory:
    """Test suite for /score-history/detailed endpoint (AC-T47.7)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_detailed_score_history_returns_metric_deltas(self, client, mock_user_id):
        """AC-T47.7: Returns points with metric deltas from event_details JSONB."""
        entry = MagicMock(
            id=uuid4(),
            score=75.5,
            chapter=3,
            event_type="conversation",
            recorded_at=datetime.now(UTC),
            event_details={
                "intimacy_delta": 0.5,
                "passion_delta": 0.3,
                "trust_delta": 0.2,
                "secureness_delta": 0.1,
                "composite_delta": 1.1,
                "conversation_id": str(uuid4()),
            },
        )

        with patch("nikita.api.routes.portal.ScoreHistoryRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_history_since.return_value = [entry]
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/score-history/detailed?days=30")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1
            point = data["points"][0]
            assert point["score"] == 75.5
            assert point["intimacy_delta"] == 0.5
            assert point["passion_delta"] == 0.3
            assert point["trust_delta"] == 0.2
            assert point["secureness_delta"] == 0.1
            assert point["score_delta"] == 1.1
            assert point["conversation_id"] is not None

    def test_detailed_score_history_handles_null_event_details(self, client, mock_user_id):
        """AC-T47.7: Handles null event_details gracefully."""
        entry = MagicMock(
            id=uuid4(),
            score=70.0,
            chapter=2,
            event_type="decay",
            recorded_at=datetime.now(UTC),
            event_details=None,  # No details
        )

        with patch("nikita.api.routes.portal.ScoreHistoryRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_history_since.return_value = [entry]
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/score-history/detailed?days=7")

            assert response.status_code == 200
            data = response.json()
            point = data["points"][0]
            assert point["score"] == 70.0
            assert point["intimacy_delta"] is None
            assert point["passion_delta"] is None
            assert point["score_delta"] is None


class TestThreads:
    """Test suite for /threads endpoint (AC-T47.8)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_threads_returns_filtered_threads(self, client, mock_user_id):
        """AC-T47.8: Returns threads filtered by status and type."""
        thread = MagicMock(
            id=uuid4(),
            thread_type="question",
            content="Where should we go for dinner?",
            status="open",
            source_conversation_id=uuid4(),
            created_at=datetime.now(UTC),
            resolved_at=None,
        )

        with patch("nikita.api.routes.portal.ConversationThreadRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_threads_filtered.return_value = ([thread], 1)
            mock_repo.get_open_threads.return_value = [thread]
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/threads?status=open&type=question")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 1
            assert data["threads"][0]["status"] == "open"
            assert data["threads"][0]["thread_type"] == "question"

    def test_threads_always_includes_open_count(self, client, mock_user_id):
        """AC-T47.8: Always includes open_count regardless of filter."""
        with patch("nikita.api.routes.portal.ConversationThreadRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_threads_filtered.return_value = ([], 0)
            # Mock 5 open threads
            mock_repo.get_open_threads.return_value = [MagicMock()] * 5
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/threads?status=resolved")

            assert response.status_code == 200
            data = response.json()
            assert data["open_count"] == 5  # Always computed
            assert data["total_count"] == 0  # Filtered results

    def test_threads_status_all_passes_none(self, client, mock_user_id):
        """AC-T47.8: status=all passes None to repository."""
        with patch("nikita.api.routes.portal.ConversationThreadRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_threads_filtered.return_value = ([], 0)
            mock_repo.get_open_threads.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/threads?status=all")

            assert response.status_code == 200
            call_args = mock_repo.get_threads_filtered.call_args
            assert call_args[1]["status"] is None

    def test_threads_type_all_passes_none(self, client, mock_user_id):
        """AC-T47.8: type=all passes None to repository."""
        with patch("nikita.api.routes.portal.ConversationThreadRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_threads_filtered.return_value = ([], 0)
            mock_repo.get_open_threads.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/portal/threads?type=all")

            assert response.status_code == 200
            call_args = mock_repo.get_threads_filtered.call_args
            assert call_args[1]["thread_type"] is None


class TestQueryValidation:
    """Test suite for Query parameter validation (GH #62)."""

    @pytest.fixture
    def mock_user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def app(self, mock_user_id, mock_session):
        test_app = FastAPI()
        test_app.include_router(router, prefix="/portal")
        test_app.dependency_overrides[get_current_user_id] = lambda: mock_user_id
        test_app.dependency_overrides[get_async_session] = lambda: mock_session
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_emotional_history_negative_hours_rejected(self, client):
        """GH #62: hours=-1 returns 422."""
        response = client.get("/portal/emotional-state/history?hours=-1")
        assert response.status_code == 422

    def test_emotional_history_zero_hours_rejected(self, client):
        """GH #62: hours=0 returns 422."""
        response = client.get("/portal/emotional-state/history?hours=0")
        assert response.status_code == 422

    def test_emotional_history_hours_exceeding_max_rejected(self, client):
        """GH #62: hours=721 (> max 720) returns 422."""
        response = client.get("/portal/emotional-state/history?hours=721")
        assert response.status_code == 422

    def test_thoughts_negative_limit_rejected(self, client):
        """GH #62: limit=-1 returns 422."""
        response = client.get("/portal/thoughts?limit=-1")
        assert response.status_code == 422

    def test_thoughts_zero_limit_rejected(self, client):
        """GH #62: limit=0 returns 422."""
        response = client.get("/portal/thoughts?limit=0")
        assert response.status_code == 422

    def test_thoughts_negative_offset_rejected(self, client):
        """GH #62: offset=-1 returns 422."""
        response = client.get("/portal/thoughts?offset=-1")
        assert response.status_code == 422

    def test_detailed_score_zero_days_rejected(self, client):
        """GH #62: days=0 returns 422."""
        response = client.get("/portal/score-history/detailed?days=0")
        assert response.status_code == 422

    def test_threads_zero_limit_rejected(self, client):
        """GH #62: limit=0 returns 422."""
        response = client.get("/portal/threads?limit=0")
        assert response.status_code == 422

    def test_score_history_zero_days_rejected(self, client):
        """GH #62: days=0 returns 422."""
        response = client.get("/portal/score-history?days=0")
        assert response.status_code == 422

    def test_conversations_zero_page_rejected(self, client):
        """GH #62: page=0 returns 422."""
        response = client.get("/portal/conversations?page=0")
        assert response.status_code == 422

    def test_conversations_page_size_exceeding_max_rejected(self, client):
        """GH #62: page_size=101 returns 422."""
        response = client.get("/portal/conversations?page_size=101")
        assert response.status_code == 422

    def test_valid_boundary_values_pass(self, client):
        """GH #62: Valid boundary values (min/max) should pass."""
        with patch("nikita.api.routes.portal.get_state_store") as mock_get_store:
            mock_store = AsyncMock()
            mock_store.get_state_history.return_value = []
            mock_get_store.return_value = mock_store

            # hours=1 (minimum valid)
            response = client.get("/portal/emotional-state/history?hours=1")
            assert response.status_code == 200

            # hours=720 (maximum valid)
            response = client.get("/portal/emotional-state/history?hours=720")
            assert response.status_code == 200
