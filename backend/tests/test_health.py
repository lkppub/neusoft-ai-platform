"""Smoke tests for backend health and basic API functionality."""

import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Ensure backend is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Verify the health endpoint returns 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_failure_empty():
    """Verify login returns 422 for empty body (validates request parsing)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_tickets_unauthorized():
    """Verify tickets endpoint requires auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/tickets")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_voice_endpoint_requires_auth():
    """Verify voice endpoints require authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/voice/text-to-speech", json={"text": "test"})
        assert resp.status_code == 401
