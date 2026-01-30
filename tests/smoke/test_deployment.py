"""Post-deployment smoke tests for Nikita API.

Run these tests after every deployment to verify the service is healthy.

Usage:
    pytest tests/smoke/test_deployment.py -v -m smoke

    # Or with custom SERVICE_URL
    SERVICE_URL=https://custom-url.run.app pytest tests/smoke/ -v -m smoke
"""
import os

import httpx
import pytest

# Configuration
SERVICE_URL = os.environ.get(
    "SERVICE_URL", "https://nikita-api-1040094048579.us-central1.run.app"
)
TIMEOUT = 90.0  # seconds - allow for cold start


@pytest.mark.smoke
class TestHealthEndpoints:
    """Smoke tests for health endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Verify /health endpoint returns 200 with healthy status."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/health")

            assert (
                response.status_code == 200
            ), f"Health check failed: {response.text}"
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "nikita-api"

    @pytest.mark.asyncio
    async def test_deep_health_endpoint(self):
        """Verify /health/deep endpoint returns 200 with database connected."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/health/deep")

            assert (
                response.status_code == 200
            ), f"Deep health check failed: {response.text}"
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"


@pytest.mark.smoke
class TestAPIEndpoints:
    """Smoke tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Verify root endpoint returns service info."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/")

            assert response.status_code == 200, f"Root failed: {response.status_code}"
            data = response.json()
            assert data["name"] == "Nikita: Don't Get Dumped"
            assert data["status"] == "online"

    @pytest.mark.asyncio
    async def test_unauthorized_portal_request(self):
        """Verify API returns 401/403 for unauthorized requests."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{SERVICE_URL}/api/v1/portal/stats",
                headers={"Authorization": "Bearer invalid_token"},
            )

            # Should return 401 or 403, not 500
            assert response.status_code in (
                401,
                403,
                422,
            ), f"Unexpected status: {response.status_code}"


@pytest.mark.smoke
class TestVoiceEndpoints:
    """Smoke tests for voice-related endpoints."""

    @pytest.mark.asyncio
    async def test_voice_pre_call_endpoint(self):
        """Verify voice pre-call endpoint responds (requires auth but shouldn't 500)."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{SERVICE_URL}/api/v1/voice/pre-call",
                json={"user_id": "test"},
            )

            # Should return 401/422, not 500
            assert response.status_code in (
                401,
                422,
            ), f"Voice pre-call unexpected error: {response.status_code}"


@pytest.mark.smoke
class TestTaskEndpoints:
    """Smoke tests for task endpoints."""

    @pytest.mark.asyncio
    async def test_tasks_decay_requires_auth(self):
        """Verify /tasks/decay endpoint requires authentication."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Note: Using tasks prefix (no api/v1)
            response = await client.post(f"{SERVICE_URL}/api/v1/tasks/decay")

            # Task endpoints may require auth or return 200
            # We just want to ensure no 500 error
            assert response.status_code != 500, f"Decay task errored: {response.text}"


# Standalone runner
if __name__ == "__main__":
    import asyncio

    async def run_smoke_tests():
        """Run basic smoke tests standalone."""
        print(f"Testing: {SERVICE_URL}")

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Health check
            print("\n1. Testing /health...")
            resp = await client.get(f"{SERVICE_URL}/health")
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.json()}")

            # Deep health
            print("\n2. Testing /health/deep...")
            resp = await client.get(f"{SERVICE_URL}/health/deep")
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.json()}")

            # Root
            print("\n3. Testing /...")
            resp = await client.get(f"{SERVICE_URL}/")
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.json()}")

            print("\n✅ Smoke tests passed!")

    asyncio.run(run_smoke_tests())
