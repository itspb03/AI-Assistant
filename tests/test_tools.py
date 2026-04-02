import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from app.ai.claude.tools.handlers.project_tools import ProjectToolHandlers
from app.ai.claude.tools.handlers.memory_tools import MemoryToolHandlers

PROJECT_ID = UUID("00000000-0000-0000-0000-000000000001")


# ── Project Tools ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_project_brief_returns_brief():
    brief_repo = MagicMock()
    brief_repo.get_by_project = AsyncMock(return_value={
        "id": "some-id",
        "project_id": str(PROJECT_ID),
        "goals": "Build an AI assistant",
        "target_audience": "Developers",
        "constraints": "Must use FastAPI",
        "deliverables": "REST API",
        "tone": None,
        "reference_links": [],
        "open_questions": [],
        "version": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })

    handler = ProjectToolHandlers(
        brief_repo=brief_repo,
        image_repo=MagicMock(),
        image_service=MagicMock(),
    )

    result = await handler.get_project_brief({}, project_id=PROJECT_ID)

    # id and project_id should be stripped before returning to Claude
    assert "id" not in result
    assert "project_id" not in result
    assert result["goals"] == "Build an AI assistant"


@pytest.mark.asyncio
async def test_get_project_brief_returns_error_when_missing():
    brief_repo = MagicMock()
    brief_repo.get_by_project = AsyncMock(return_value=None)

    handler = ProjectToolHandlers(
        brief_repo=brief_repo,
        image_repo=MagicMock(),
        image_service=MagicMock(),
    )

    result = await handler.get_project_brief({}, project_id=PROJECT_ID)
    assert "error" in result


@pytest.mark.asyncio
async def test_generate_image_returns_image_data():
    from app.schemas.image import ImageOut, ImageProvider
    from datetime import datetime

    image_service = MagicMock()
    image_service.generate = AsyncMock(return_value=ImageOut(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        project_id=PROJECT_ID,
        prompt="a futuristic UI",
        url="https://picsum.photos/seed/42/800/600",
        provider=ImageProvider.mock,
        created_at=datetime.now(),
    ))

    handler = ProjectToolHandlers(
        brief_repo=MagicMock(),
        image_repo=MagicMock(),
        image_service=image_service,
    )

    result = await handler.generate_image(
        {"prompt": "a futuristic UI"}, project_id=PROJECT_ID
    )

    assert "image_id" in result
    assert "url" in result
    assert result["provider"] == "mock"


@pytest.mark.asyncio
async def test_list_project_images_returns_list():
    from app.schemas.image import ImageOut, ImageProvider
    from datetime import datetime

    image_service = MagicMock()
    image_service.list_by_project = AsyncMock(return_value=[
        ImageOut(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            project_id=PROJECT_ID,
            prompt="logo design",
            url="https://picsum.photos/seed/99/800/600",
            provider=ImageProvider.mock,
            created_at=datetime.now(),
        )
    ])

    handler = ProjectToolHandlers(
        brief_repo=MagicMock(),
        image_repo=MagicMock(),
        image_service=image_service,
    )

    result = await handler.list_project_images({}, project_id=PROJECT_ID)
    assert "images" in result
    assert len(result["images"]) == 1
    assert result["images"][0]["prompt"] == "logo design"


# ── Memory Tools ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_memory_saves_entry():
    from app.schemas.memory import MemoryEntryOut, MemoryCategory, MemorySource
    from datetime import datetime

    memory_service = MagicMock()
    memory_service.write_entry = AsyncMock(return_value=MemoryEntryOut(
        id=UUID("00000000-0000-0000-0000-000000000004"),
        project_id=PROJECT_ID,
        category=MemoryCategory.decision,
        key="chosen_stack",
        summary="The team decided to use FastAPI and Supabase.",
        source=MemorySource.claude,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    ))

    handler = MemoryToolHandlers(memory_service=memory_service)

    result = await handler.update_memory(
        {
            "category": "decision",
            "key": "chosen_stack",
            "summary": "The team decided to use FastAPI and Supabase.",
        },
        project_id=PROJECT_ID,
    )

    assert result["status"] == "saved"
    assert result["key"] == "chosen_stack"
    assert result["category"] == "decision"


@pytest.mark.asyncio
async def test_read_memory_returns_snapshot():
    from app.schemas.memory import MemorySnapshot

    memory_service = MagicMock()
    memory_service.get_snapshot = AsyncMock(return_value=MemorySnapshot(
        project_id=PROJECT_ID,
        context=[],
        decisions=[],
        entities=[],
        constraints=[],
    ))

    handler = MemoryToolHandlers(memory_service=memory_service)
    result = await handler.read_memory({}, project_id=PROJECT_ID)

    assert "project_id" in result or "context" in result


# ── Tool Executor ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_executor_returns_error_for_unknown_tool():
    from app.ai.claude.tools.executor import ToolExecutor

    executor = ToolExecutor(
        project_handlers=MagicMock(),
        memory_handlers=MagicMock(),
    )
    # Manually empty the dispatch table
    executor._dispatch = {}

    result = await executor.execute(
        tool_name="nonexistent_tool",
        tool_input={},
        project_id=PROJECT_ID,
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_executor_dispatches_to_correct_handler():
    from app.ai.claude.tools.executor import ToolExecutor

    mock_handler = AsyncMock(return_value={"status": "ok"})

    executor = ToolExecutor(
        project_handlers=MagicMock(),
        memory_handlers=MagicMock(),
    )
    executor._dispatch["test_tool"] = mock_handler

    result = await executor.execute(
        tool_name="test_tool",
        tool_input={"key": "value"},
        project_id=PROJECT_ID,
    )

    mock_handler.assert_called_once()
    assert result["status"] == "ok"