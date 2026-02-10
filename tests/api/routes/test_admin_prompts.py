"""Tests for admin prompt endpoints (Task 4)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAdminPromptsList:
    """Tests for GET /admin/prompts."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app with admin router and mocked dependencies."""
        from nikita.api.routes.admin import router, get_current_admin_user_id
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_list_prompts_returns_paginated_results(self, mock_session, client):
        """Test listing prompts returns paginated results."""
        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        # Mock prompt data
        mock_prompts = []
        for i in range(3):
            prompt = MagicMock()
            prompt.id = uuid4()
            prompt.user_id = uuid4()
            prompt.conversation_id = uuid4()
            prompt.prompt_content = f"Test prompt {i}"
            prompt.token_count = 100 + i
            prompt.generation_time_ms = 50.0 + i
            prompt.meta_prompt_template = "system_prompt.j2"
            prompt.created_at = datetime.now(timezone.utc)
            mock_prompts.append(prompt)

        prompts_result = MagicMock()
        prompts_result.scalars.return_value.all.return_value = mock_prompts

        mock_session.execute.side_effect = [count_result, prompts_result]

        response = client.get("/admin/prompts?page=1&page_size=50")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert len(data["prompts"]) == 3
        assert data["prompts"][0]["prompt_content"] == "Test prompt 0"
        assert data["prompts"][0]["token_count"] == 100

    def test_list_prompts_filters_by_user_id(self, mock_session, client):
        """Test filtering prompts by user_id."""
        user_id = uuid4()

        # Mock count
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        # Mock prompts
        mock_prompt = MagicMock()
        mock_prompt.id = uuid4()
        mock_prompt.user_id = user_id
        mock_prompt.conversation_id = uuid4()
        mock_prompt.prompt_content = "Filtered prompt"
        mock_prompt.token_count = 150
        mock_prompt.generation_time_ms = 75.0
        mock_prompt.meta_prompt_template = "system_prompt.j2"
        mock_prompt.created_at = datetime.now(timezone.utc)

        prompts_result = MagicMock()
        prompts_result.scalars.return_value.all.return_value = [mock_prompt]

        mock_session.execute.side_effect = [count_result, prompts_result]

        response = client.get(f"/admin/prompts?user_id={user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["user_id"] == str(user_id)

    def test_list_prompts_filters_by_template(self, mock_session, client):
        """Test filtering prompts by template name."""
        # Mock count
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        # Mock prompt
        mock_prompt = MagicMock()
        mock_prompt.id = uuid4()
        mock_prompt.user_id = uuid4()
        mock_prompt.conversation_id = uuid4()
        mock_prompt.prompt_content = "Voice prompt"
        mock_prompt.token_count = 200
        mock_prompt.generation_time_ms = 100.0
        mock_prompt.meta_prompt_template = "voice_prompt.j2"
        mock_prompt.created_at = datetime.now(timezone.utc)

        prompts_result = MagicMock()
        prompts_result.scalars.return_value.all.return_value = [mock_prompt]

        mock_session.execute.side_effect = [count_result, prompts_result]

        response = client.get("/admin/prompts?template=voice_prompt.j2")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["prompts"][0]["meta_prompt_template"] == "voice_prompt.j2"

    def test_list_prompts_empty_results(self, mock_session, client):
        """Test listing prompts when no results."""
        # Mock count
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # Mock empty prompts
        prompts_result = MagicMock()
        prompts_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [count_result, prompts_result]

        response = client.get("/admin/prompts")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["prompts"] == []


class TestAdminPromptDetail:
    """Tests for GET /admin/prompts/{prompt_id}."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app."""
        from nikita.api.routes.admin import router, get_current_admin_user_id
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_get_prompt_detail_returns_prompt(self, mock_session, client):
        """Test getting prompt detail returns full prompt data."""
        prompt_id = uuid4()
        user_id = uuid4()

        # Mock prompt
        mock_prompt = MagicMock()
        mock_prompt.id = prompt_id
        mock_prompt.user_id = user_id
        mock_prompt.conversation_id = uuid4()
        mock_prompt.prompt_content = "Full prompt content here"
        mock_prompt.token_count = 500
        mock_prompt.generation_time_ms = 150.0
        mock_prompt.meta_prompt_template = "system_prompt.j2"
        mock_prompt.created_at = datetime.now(timezone.utc)

        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_prompt

        mock_session.execute.return_value = result

        response = client.get(f"/admin/prompts/{prompt_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(prompt_id)
        assert data["user_id"] == str(user_id)
        assert data["prompt_content"] == "Full prompt content here"
        assert data["token_count"] == 500
        assert data["generation_time_ms"] == 150.0

    def test_get_prompt_detail_404_when_not_found(self, mock_session, client):
        """Test getting non-existent prompt returns 404."""
        prompt_id = uuid4()

        result = MagicMock()
        result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = result

        response = client.get(f"/admin/prompts/{prompt_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAdminPromptPreview:
    """Tests for POST /admin/debug/prompts/{user_id}/preview."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_session):
        """Create isolated test app."""
        from nikita.api.routes.admin_debug import router, get_current_admin_user
        from nikita.db.database import get_async_session

        test_app = FastAPI()
        test_app.include_router(router, prefix="/admin/debug")

        async def mock_admin_auth():
            return uuid4()

        async def mock_get_session():
            return mock_session

        test_app.dependency_overrides[get_current_admin_user] = mock_admin_auth
        test_app.dependency_overrides[get_async_session] = mock_get_session

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch("nikita.pipeline.stages.prompt_builder.PromptBuilderStage")
    @patch("nikita.db.repositories.conversation_repository.ConversationRepository")
    @patch("nikita.db.repositories.user_repository.UserRepository")
    def test_preview_prompt_generates_preview(
        self, mock_user_repo_class, mock_conv_repo_class, mock_stage_class, mock_session, client
    ):
        """Test preview generates prompt without saving to DB."""
        user_id = uuid4()
        conversation_id = uuid4()

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.chapter = 2
        mock_user.relationship_score = 65.0
        mock_user.game_status = "active"

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user
        mock_user_repo_class.return_value = mock_user_repo

        # Mock conversation
        mock_conv = MagicMock()
        mock_conv.id = conversation_id

        mock_conv_repo = AsyncMock()
        mock_conv_repo.get_recent.return_value = [mock_conv]
        mock_conv_repo_class.return_value = mock_conv_repo

        # Mock stage
        mock_stage = AsyncMock()
        mock_stage._run.return_value = {"generated": True}

        mock_stage_class.return_value = mock_stage

        response = client.post(f"/admin/debug/prompts/{user_id}/preview")

        assert response.status_code == 200
        data = response.json()
        assert data["is_preview"] is True
        assert data["user_id"] == str(user_id)
        assert "prompt_content" in data

    @patch("nikita.db.repositories.user_repository.UserRepository")
    def test_preview_prompt_404_when_user_not_found(
        self, mock_user_repo_class, mock_session, client
    ):
        """Test preview returns 404 when user doesn't exist."""
        user_id = uuid4()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = None
        mock_user_repo_class.return_value = mock_user_repo

        response = client.post(f"/admin/debug/prompts/{user_id}/preview")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
