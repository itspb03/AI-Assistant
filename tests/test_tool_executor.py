import pytest
import uuid
from unittest.mock import MagicMock, patch
from app.ai.groq.tools.executor import ToolExecutor


def make_executor():
    project_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    return ToolExecutor(
        project_id=project_id,
        conversation_id=conversation_id,
        brief_repo=MagicMock(),
        image_repo=MagicMock(),
        tool_exec_repo=MagicMock(),
        memory_svc=MagicMock(),
        storage_svc=MagicMock(),
    ), project_id


def test_get_project_brief_no_brief():
    executor, _ = make_executor()
    executor.brief_repo.get.return_value = None
    result = executor._tool_get_project_brief({})
    assert result["brief"] is None


def test_write_memory():
    executor, _ = make_executor()
    executor.memory_svc.upsert.return_value = None
    result = executor._tool_write_memory({"key": "decisions", "content": "Use FastAPI"})
    assert result["written"] is True
    executor.memory_svc.upsert.assert_called_once()


def test_unknown_tool_returns_error():
    executor, _ = make_executor()
    result = executor.execute("nonexistent_tool", "tu_123", {})
    assert "error" in result