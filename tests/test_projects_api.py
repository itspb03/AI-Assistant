import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


@patch("app.api.deps.get_supabase")
def test_create_project(mock_db):
    mock_table = MagicMock()
    mock_db.return_value.table.return_value = mock_table
    mock_table.insert.return_value.execute.return_value.data = [{
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Test Project",
        "description": None,
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }]
    response = client.post("/projects", json={"name": "Test Project"})
    assert response.status_code == 201
    assert response.json()["name"] == "Test Project"