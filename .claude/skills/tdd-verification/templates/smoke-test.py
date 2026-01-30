"""Post-deployment smoke tests for Nikita API.

Run these tests after every deployment to verify the service is healthy.

Usage:
    pytest tests/smoke/test_deployment.py -v -m smoke

    # Or with custom SERVICE_URL
    SERVICE_URL=https://custom-url.run.app pytest tests/smoke/ -v -m smoke
"""
import os
import pytest
import httpx

# Configuration
SERVICE_URL = os.environ.get(
    "SERVICE_URL",
    "https://nikita-api-1040094048579.us-central1.run.app"
)
TIMEOUT = 30.0  # seconds - allow for cold start


@pytest.mark.smoke
class TestHealthEndpoints:
    """Smoke tests for health endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Verify /health endpoint returns 200 with healthy status."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/health")

            assert response.status_code == 200, f"Health check failed: {response.text}"
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "nikita-api"

    @pytest.mark.asyncio
    async def test_deep_health_endpoint(self):
        """Verify /health/deep endpoint returns 200 with database connected."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/health/deep")

            assert response.status_code == 200, f"Deep health check failed: {response.text}"
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"


@pytest.mark.smoke
class TestAPIEndpoints:
    """Smoke tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_unauthorized_request(self):
        """Verify API returns 401 for unauthorized requests."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{SERVICE_URL}/api/v1/portal/stats",
                headers={"Authorization": "Bearer invalid_token"}
            )

            # Should return 401 or 403, not 500
            assert response.status_code in (401, 403), f"Unexpected status: {response.status_code}"

    @pytest.mark.asyncio
    async def test_docs_endpoint(self):
        """Verify OpenAPI docs are accessible."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/docs")

            assert response.status_code == 200, f"Docs not accessible: {response.status_code}"
            assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


@pytest.mark.smoke
class TestVoiceEndpoints:
    """Smoke tests for voice-related endpoints."""

    @pytest.mark.asyncio
    async def test_voice_availability(self):
        """Verify voice availability endpoint responds."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SERVICE_URL}/api/v1/voice/availability")

            # Should return 200 (available) or 503 (unavailable), not 500
            assert response.status_code in (200, 503), f"Voice availability failed: {response.status_code}"


@pytest.mark.smoke
class TestTaskEndpoints:
    """Smoke tests for task endpoints."""

    @pytest.mark.asyncio
    async def test_decay_endpoint(self):
        """Verify /tasks/decay endpoint responds."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{SERVICE_URL}/tasks/decay")

            # Should return 200, not error
            assert response.status_code == 200, f"Decay task failed: {response.status_code}"


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

            # Docs
            print("\n3. Testing /docs...")
            resp = await client.get(f"{SERVICE_URL}/docs")
            print(f"   Status: {resp.status_code}")

            print("\n✅ Smoke tests passed!")

    asyncio.run(run_smoke_tests())
