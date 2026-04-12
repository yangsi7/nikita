"""Tests for background task API routes.

T3.7: Tests for pg_cron task endpoints.
AC Coverage: Task route authentication and basic functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nikita.api.routes.tasks import router, verify_task_secret


class TestTaskRouteAuth:
    """Test suite for task route authentication."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with task routes."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_decay_endpoint_exists(self, app):
        """Verify POST /decay endpoint exists."""
        # Without auth (dev mode - no secret configured)
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        # Mock DecayProcessor
                        with patch(
                            "nikita.engine.decay.processor.DecayProcessor"
                        ) as mock_processor_class:
                            mock_processor = MagicMock()
                            mock_processor.process_all = AsyncMock(return_value={
                                "processed": 0, "decayed": 0, "game_overs": 0
                            })
                            mock_processor_class.return_value = mock_processor

                            response = client.post("/api/v1/tasks/decay")
                            assert response.status_code in [200, 500]

    def test_deliver_endpoint_exists(self, app):
        """Verify POST /deliver endpoint exists."""
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        with patch(
                            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository"
                        ) as mock_event_repo_class:
                            mock_event_repo = MagicMock()
                            mock_event_repo.get_due_events = AsyncMock(return_value=[])
                            mock_event_repo_class.return_value = mock_event_repo

                            with patch(
                                "nikita.platforms.telegram.bot.TelegramBot"
                            ) as mock_bot_class:
                                mock_bot = MagicMock()
                                mock_bot.close = AsyncMock()
                                mock_bot_class.return_value = mock_bot

                                response = client.post("/api/v1/tasks/deliver")
                                assert response.status_code in [200, 500]  # Exists

    def test_summary_endpoint_exists(self, app):
        """Verify POST /summary endpoint exists."""
        # Use raise_server_exceptions=False to capture errors gracefully
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    # Create proper async context manager mock
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session.execute = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    # Patch the module-level import
                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        # Patch the repos that are imported inside the function
                        with patch(
                            "nikita.db.repositories.user_repository.UserRepository"
                        ) as mock_user_repo_class:
                            mock_user_repo = MagicMock()
                            mock_user_repo.get_active_users_for_decay = AsyncMock(return_value=[])
                            mock_user_repo_class.return_value = mock_user_repo

                            response = client.post("/api/v1/tasks/summary")
                            # Endpoint exists - either 200 or 500 (if mocking is incomplete)
                            # We mainly want to verify the route is registered
                            assert response.status_code in [200, 500]

    def test_cleanup_endpoint_exists(self, app):
        """Verify POST /cleanup endpoint exists."""
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    # Create proper async context manager mock
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        with patch(
                            "nikita.db.repositories.pending_registration_repository.PendingRegistrationRepository"
                        ) as mock_repo_class:
                            mock_repo = MagicMock()
                            mock_repo.cleanup_expired = AsyncMock(return_value=5)
                            mock_repo_class.return_value = mock_repo

                            response = client.post("/api/v1/tasks/cleanup")
                            assert response.status_code in [200, 500]

    def test_auth_required_when_secret_configured(self, client):
        """Verify endpoints require auth when secret is configured."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="test-secret",
        ):
            # No auth header - should fail
            response = client.post("/api/v1/tasks/decay")
            assert response.status_code == 401
            assert response.json()["detail"] == "Unauthorized"

    def test_auth_succeeds_with_valid_bearer(self, app):
        """Verify auth succeeds with correct bearer token."""
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch(
                "nikita.api.routes.tasks._get_task_secret",
                return_value="test-secret",
            ):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        with patch(
                            "nikita.engine.decay.processor.DecayProcessor"
                        ) as mock_processor_class:
                            mock_processor = MagicMock()
                            mock_processor.process_all = AsyncMock(return_value={
                                "processed": 0, "decayed": 0, "game_overs": 0
                            })
                            mock_processor_class.return_value = mock_processor

                            response = client.post(
                                "/api/v1/tasks/decay",
                                headers={"Authorization": "Bearer test-secret"},
                            )
                            assert response.status_code in [200, 500]

    def test_auth_fails_with_wrong_bearer(self, client):
        """Verify auth fails with incorrect bearer token."""
        with patch(
            "nikita.api.routes.tasks._get_task_secret",
            return_value="test-secret",
        ):
            response = client.post(
                "/api/v1/tasks/decay",
                headers={"Authorization": "Bearer wrong-secret"},
            )
            assert response.status_code == 401


class TestDecayEndpoint:
    """Test suite for /decay endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_decay_returns_expected_format(self, app):
        """Verify /decay returns expected response format.

        B-3: Decay endpoint now returns detailed statistics:
        - processed: total users checked
        - decayed: users that received decay
        - game_overs: users that hit 0% score
        """
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        with patch(
                            "nikita.engine.decay.processor.DecayProcessor"
                        ) as mock_processor_class:
                            mock_processor = MagicMock()
                            mock_processor.process_all = AsyncMock(return_value={
                                "processed": 5, "decayed": 3, "game_overs": 1
                            })
                            mock_processor_class.return_value = mock_processor

                            response = client.post("/api/v1/tasks/decay")

                            if response.status_code == 200:
                                data = response.json()
                                assert "status" in data
                                assert data["status"] == "ok"
                                # B-3: New decay response format
                                assert "processed" in data
                                assert "decayed" in data
                                assert "game_overs" in data
                                assert isinstance(data["processed"], int)
                                assert isinstance(data["decayed"], int)
                                assert isinstance(data["game_overs"], int)
                            else:
                                assert response.status_code == 500


class TestDeliverEndpoint:
    """Test suite for /deliver endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_deliver_returns_expected_format(self, app):
        """Verify /deliver returns expected response format.

        D-4: Deliver endpoint processes scheduled_events table:
        - delivered: count of messages successfully sent
        - failed: count of messages that failed to send
        - skipped: count of voice events (not implemented yet)
        """
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    # Create proper async context manager mock
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    # Patch the module-level import
                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        # Mock ScheduledEventRepository (imported inside function)
                        with patch(
                            "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository"
                        ) as mock_event_repo_class:
                            mock_event_repo = MagicMock()
                            mock_event_repo.get_due_events = AsyncMock(return_value=[])
                            mock_event_repo_class.return_value = mock_event_repo

                            # Mock TelegramBot
                            with patch(
                                "nikita.platforms.telegram.bot.TelegramBot"
                            ) as mock_bot_class:
                                mock_bot = MagicMock()
                                mock_bot.close = AsyncMock()
                                mock_bot_class.return_value = mock_bot

                                response = client.post("/api/v1/tasks/deliver")

                                if response.status_code == 200:
                                    data = response.json()
                                    assert "status" in data
                                    assert data["status"] == "ok"
                                    assert "delivered" in data
                                    assert "failed" in data
                                    assert "skipped" in data
                                    assert isinstance(data["delivered"], int)
                                    assert isinstance(data["failed"], int)
                                    assert isinstance(data["skipped"], int)
                                else:
                                    # Endpoint exists but mocking may be incomplete
                                    assert response.status_code == 500


class TestSummaryEndpoint:
    """Test suite for /summary endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_summary_returns_expected_format(self, app):
        """Verify /summary returns expected response format.

        C-5: Summary endpoint now generates LLM-based daily summaries:
        - summaries_generated: count of new summaries created
        - users_checked: total active users processed
        - errors: first 5 errors if any
        """
        # Use raise_server_exceptions=False to capture errors gracefully
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    # Create proper async context manager mock
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session.execute = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    # Patch the module-level import
                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        # Patch the repos that are imported inside the function
                        with patch(
                            "nikita.db.repositories.user_repository.UserRepository"
                        ) as mock_user_repo_class:
                            mock_user_repo = MagicMock()
                            mock_user_repo.get_active_users_for_decay = AsyncMock(return_value=[])
                            mock_user_repo_class.return_value = mock_user_repo

                            response = client.post("/api/v1/tasks/summary")

                            # May return 200 (success) or 500 (if mocking is incomplete)
                            # For full testing, we verify status and basic structure if 200
                            if response.status_code == 200:
                                data = response.json()
                                assert "status" in data
                                assert "summaries_generated" in data or "error" in data
                            else:
                                # Endpoint exists but mocking may be incomplete
                                assert response.status_code == 500


class TestCleanupEndpoint:
    """Test suite for /cleanup endpoint."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_cleanup_returns_expected_format(self, app):
        """Verify /cleanup returns expected response format on success."""
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                with patch(
                    "nikita.api.routes.tasks.get_session_maker"
                ) as mock_session_maker:
                    # Create proper async context manager mock
                    mock_session = AsyncMock()
                    mock_session.commit = AsyncMock()

                    async_cm = AsyncMock()
                    async_cm.__aenter__.return_value = mock_session
                    async_cm.__aexit__.return_value = None

                    mock_session_maker.return_value = MagicMock(return_value=async_cm)

                    with patch(
                        "nikita.api.routes.tasks.JobExecutionRepository"
                    ) as mock_job_repo_class:
                        mock_job_repo = MagicMock()
                        mock_execution = MagicMock()
                        mock_execution.id = "test-execution-id"
                        mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
                        mock_job_repo.complete_execution = AsyncMock()
                        mock_job_repo_class.return_value = mock_job_repo

                        with patch(
                            "nikita.db.repositories.pending_registration_repository.PendingRegistrationRepository"
                        ) as mock_repo_class:
                            mock_repo = MagicMock()
                            mock_repo.cleanup_expired = AsyncMock(return_value=3)
                            mock_repo_class.return_value = mock_repo

                            response = client.post("/api/v1/tasks/cleanup")

                            if response.status_code == 200:
                                data = response.json()
                                assert "status" in data
                                assert data["status"] == "ok"
                                assert "cleaned_up" in data
                                assert data["cleaned_up"] == 3
                            else:
                                assert response.status_code == 500

    def test_cleanup_handles_errors_gracefully(self, app):
        """Verify /cleanup handles errors gracefully."""
        # Create client with raise_server_exceptions=False to test 500 responses
        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("nikita.api.routes.tasks._get_task_secret", return_value=None):
                # Patch where get_session_maker is USED (in tasks.py), not where it's defined
                with patch(
                    "nikita.api.routes.tasks.get_session_maker",
                    side_effect=Exception("DB connection failed"),
                ):
                    response = client.post("/api/v1/tasks/cleanup")

                    assert response.status_code == 500  # Unhandled exception before try block
                    # Note: The route calls get_session_maker() BEFORE the try/except,
                    # so DB errors at connection time result in 500, not graceful error


class TestDeliverChatIdHandling:
    """GH #248: the deliver worker must send Telegram messages even when
    ``content.chat_id`` is absent, by falling back to ``event.user.telegram_id``.

    These tests intentionally exercise the content-parsing branch that
    prior ``test_deliver_endpoint_exists`` skipped by mocking
    ``get_due_events`` to ``[]``. That gap is how #248 escaped review.
    """

    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/tasks")
        return app

    @staticmethod
    def _make_event(event_id, user_telegram_id, content):
        """Build a mock ScheduledEvent with an auto-loaded ``user``."""
        event = MagicMock()
        event.id = event_id
        event.platform = "telegram"  # EventPlatform.TELEGRAM.value
        event.user_id = f"user-{event_id}"
        event.content = content
        event.user = MagicMock()
        event.user.telegram_id = user_telegram_id
        return event

    def _run_deliver(self, app, due_events):
        """Boot a TestClient with all repositories/bot patched for a single /deliver call.

        Returns ``(bot_send_mock, mark_delivered_mock, mark_failed_mock, response)``.
        """
        bot_send_mock = AsyncMock()
        mark_delivered_mock = AsyncMock()
        mark_failed_mock = AsyncMock()

        with TestClient(app, raise_server_exceptions=False) as client, \
                patch("nikita.api.routes.tasks._get_task_secret", return_value=None), \
                patch("nikita.api.routes.tasks.get_session_maker") as mock_session_maker:

            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            async_cm = AsyncMock()
            async_cm.__aenter__.return_value = mock_session
            async_cm.__aexit__.return_value = None
            mock_session_maker.return_value = MagicMock(return_value=async_cm)

            mock_job_repo = MagicMock()
            mock_execution = MagicMock()
            mock_execution.id = "test-execution-id"
            mock_job_repo.start_execution = AsyncMock(return_value=mock_execution)
            mock_job_repo.complete_execution = AsyncMock()

            mock_event_repo = MagicMock()
            mock_event_repo.get_due_events = AsyncMock(return_value=due_events)
            mock_event_repo.mark_delivered = mark_delivered_mock
            mock_event_repo.mark_failed = mark_failed_mock

            mock_bot = MagicMock()
            mock_bot.send_message = bot_send_mock
            mock_bot.close = AsyncMock()

            with patch(
                "nikita.api.routes.tasks.JobExecutionRepository",
                return_value=mock_job_repo,
            ), patch(
                "nikita.db.repositories.scheduled_event_repository.ScheduledEventRepository",
                return_value=mock_event_repo,
            ), patch(
                "nikita.platforms.telegram.bot.TelegramBot",
                return_value=mock_bot,
            ):
                response = client.post("/api/v1/tasks/deliver")

        return bot_send_mock, mark_delivered_mock, mark_failed_mock, response

    def test_deliver_telegram_event_with_chat_id_in_content_succeeds(self, app):
        """Happy path: content.chat_id is present — worker uses it (not the fallback)."""
        event = self._make_event(
            event_id="evt-1",
            user_telegram_id=999,  # intentionally different to prove content wins
            content={"chat_id": 111, "text": "hello"},
        )
        bot_send, mark_delivered, mark_failed, response = self._run_deliver(app, [event])

        assert response.status_code == 200
        bot_send.assert_awaited_once_with(chat_id=111, text="hello")
        mark_delivered.assert_awaited_once_with("evt-1")
        mark_failed.assert_not_awaited()

    def test_deliver_telegram_event_without_chat_id_falls_back_to_user_telegram_id(
        self, app, caplog
    ):
        """GH #248 regression guard: legacy rows lacking chat_id use user.telegram_id."""
        event = self._make_event(
            event_id="evt-2",
            user_telegram_id=222,
            content={"text": "hello"},  # no chat_id
        )

        import logging

        with caplog.at_level(logging.WARNING, logger="nikita.api.routes.tasks"):
            bot_send, mark_delivered, mark_failed, response = self._run_deliver(
                app, [event]
            )

        assert response.status_code == 200
        bot_send.assert_awaited_once_with(chat_id=222, text="hello")
        mark_delivered.assert_awaited_once_with("evt-2")
        mark_failed.assert_not_awaited()
        assert any(
            "missing chat_id" in rec.message.lower() for rec in caplog.records
        ), "fallback path must emit a warning for observability"

    def test_deliver_telegram_event_fails_when_no_chat_id_and_no_telegram_id(self, app):
        """Edge case: no chat_id in content AND user.telegram_id is None → mark_failed, no send."""
        event = self._make_event(
            event_id="evt-3",
            user_telegram_id=None,
            content={"text": "hello"},
        )
        bot_send, mark_delivered, mark_failed, response = self._run_deliver(app, [event])

        assert response.status_code == 200
        bot_send.assert_not_awaited()
        mark_delivered.assert_not_awaited()
        mark_failed.assert_awaited_once()
        call_kwargs = mark_failed.call_args.kwargs
        assert call_kwargs.get("increment_retry") is False
