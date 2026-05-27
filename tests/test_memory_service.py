import pytest
from unittest.mock import MagicMock
from app.services.memory_service import MemoryService


def make_service():
    repo = MagicMock()
    return MemoryService(repo), repo


def test_get_context_block_empty():
    svc, repo = make_service()
    repo.list_for_project.return_value = []
    assert svc.get_context_block("proj-1") == ""


def test_get_context_block_with_files():
    svc, repo = make_service()
    repo.list_for_project.return_value = [
        {"key": "decisions", "content": "Use FastAPI."},
        {"key": "requirements", "content": "Must support images."},
    ]
    block = svc.get_context_block("proj-1")
    assert "## Project Memory" in block
    assert "decisions" in block
    assert "Use FastAPI." in block


def test_upsert_delegates_to_repo():
    svc, repo = make_service()
    repo.upsert.return_value = {"key": "foo", "content": "bar"}
    result = svc.upsert("proj-1", "foo", "bar")
    repo.upsert.assert_called_once_with("proj-1", "foo", "bar")