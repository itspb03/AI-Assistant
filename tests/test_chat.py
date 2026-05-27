import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.create",
            new_callable=AsyncMock,
            return_value={
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "Test Project",
                "description": None,
                "status": "active",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        ):
            resp = await client.post(
                "/projects", json={"name": "Test Project"}
            )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Project"