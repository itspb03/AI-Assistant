import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from datetime import datetime

from app.main import app

PROJECT_ID      = UUID("00000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("00000000-0000-0000-0000-000000000002")
IMAGE_ID        = UUID("00000000-0000-0000-0000-000000000003")

# ── Helpers ────────────────────────────────────────────────────────────────

def _mock_project_row(name: str = "Test Project") -> dict:
    return {
        "id": str(PROJECT_ID),
        "name": name,
        "description": None,
        "status": "active",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

def _mock_brief_row() -> dict:
    return {
        "id": "00000000-0000-0000-0000-000000000010",
        "project_id": str(PROJECT_ID),
        "goals": "Build an AI assistant",
        "target_audience": "Developers",
        "constraints": "Free tier only",
        "deliverables": "REST API",
        "tone": None,
        "reference_links": [],
        "open_questions": [],
        "version": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

def _mock_conversation_row() -> dict:
    return {
        "id": str(CONVERSATION_ID),
        "project_id": str(PROJECT_ID),
        "title": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }

def _mock_image_row() -> dict:
    return {
        "id": str(IMAGE_ID),
        "project_id": str(PROJECT_ID),
        "prompt": "a futuristic dashboard",
        "url": "https://picsum.photos/seed/42/800/600",
        "provider": "mock",
        "analysis": None,
        "analyzed_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


# ══════════════════════════════════════════════════════════════════════════
# 1. HEALTH
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ══════════════════════════════════════════════════════════════════════════
# 2. PROJECTS
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_project_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.create",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ):
            resp = await client.post("/projects", json={"name": "Test Project"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_project_empty_name_fails():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/projects", json={"name": ""})
    # Pydantic min_length=1 rejects this
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_project_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ):
            resp = await client.get(f"/projects/{PROJECT_ID}")

    assert resp.status_code == 200
    assert resp.json()["id"] == str(PROJECT_ID)


@pytest.mark.asyncio
async def test_get_project_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(f"/projects/{PROJECT_ID}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_projects():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.list_all",
            new_callable=AsyncMock,
            return_value=[_mock_project_row("Project A"), _mock_project_row("Project B")],
        ):
            resp = await client.get("/projects")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_update_project():
    updated_row = _mock_project_row("Updated Name")
    updated_row["name"] = "Updated Name"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.project_repo.ProjectRepo.update",
            new_callable=AsyncMock,
            return_value=updated_row,
        ):
            resp = await client.patch(
                f"/projects/{PROJECT_ID}",
                json={"name": "Updated Name"},
            )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_project():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.project_repo.ProjectRepo.delete",
            new_callable=AsyncMock,
        ):
            resp = await client.delete(f"/projects/{PROJECT_ID}")

    assert resp.status_code == 204


# ══════════════════════════════════════════════════════════════════════════
# 3. BRIEFS
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_upsert_brief_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.brief_repo.BriefRepo.upsert",
            new_callable=AsyncMock,
            return_value=_mock_brief_row(),
        ), patch(
            "app.repositories.brief_repo.BriefRepo.get_by_project",
            new_callable=AsyncMock,
            return_value=None,   # no existing brief → insert path
        ):
            resp = await client.put(
                f"/projects/{PROJECT_ID}/brief",
                json={
                    "goals": "Build an AI assistant",
                    "target_audience": "Developers",
                    "constraints": "Free tier only",
                    "deliverables": "REST API",
                },
            )

    assert resp.status_code == 200
    assert resp.json()["goals"] == "Build an AI assistant"
    assert resp.json()["version"] == 1


@pytest.mark.asyncio
async def test_get_brief_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.brief_repo.BriefRepo.get_by_project",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(f"/projects/{PROJECT_ID}/brief")

    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# 4. CONVERSATIONS
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_conversations():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.conversation_repo.ConversationRepo.list_by_project",
            new_callable=AsyncMock,
            return_value=[_mock_conversation_row()],
        ):
            resp = await client.get(f"/projects/{PROJECT_ID}/conversations")

    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_messages_for_conversation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.conversation_repo.ConversationRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_conversation_row(),
        ), patch(
            "app.repositories.message_repo.MessageRepo.get_by_conversation",
            new_callable=AsyncMock,
            return_value=[
                {
                    "id": "00000000-0000-0000-0000-000000000020",
                    "conversation_id": str(CONVERSATION_ID),
                    "project_id": str(PROJECT_ID),
                    "role": "user",
                    "content": "Hello!",
                    "tool_name": None,
                    "tool_use_id": None,
                    "tool_input": None,
                    "tool_output": None,
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ],
        ):
            resp = await client.get(
                f"/projects/{PROJECT_ID}/conversations/{CONVERSATION_ID}/messages"
            )

    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello!"


# ══════════════════════════════════════════════════════════════════════════
# 5. CHAT
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_chat_creates_new_conversation():
    from app.schemas.chat import ChatResponse

    mock_response = ChatResponse(
        conversation_id=CONVERSATION_ID,
        assistant_message="Hello! How can I help with your project?",
        tool_calls_made=[],
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.ai.claude.orchestrator.ChatOrchestrator.run",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = await client.post(
                f"/projects/{PROJECT_ID}/chat",
                json={"user_message": "What is this project about?"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == str(CONVERSATION_ID)
    assert "Hello!" in data["assistant_message"]
    assert data["tool_calls_made"] == []


@pytest.mark.asyncio
async def test_chat_continues_existing_conversation():
    from app.schemas.chat import ChatResponse

    mock_response = ChatResponse(
        conversation_id=CONVERSATION_ID,
        assistant_message="The target audience is developers.",
        tool_calls_made=["get_project_brief"],
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.ai.claude.orchestrator.ChatOrchestrator.run",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = await client.post(
                f"/projects/{PROJECT_ID}/chat",
                json={
                    "user_message": "Who is the target audience?",
                    "conversation_id": str(CONVERSATION_ID),
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == str(CONVERSATION_ID)
    assert "get_project_brief" in data["tool_calls_made"]


@pytest.mark.asyncio
async def test_chat_empty_message_fails():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/projects/{PROJECT_ID}/chat",
            json={"user_message": ""},
        )
    # Pydantic min_length=1 rejects empty message
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# 6. IMAGES
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_generate_image_success():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.ai.providers.image_generator.MockImageProvider.generate",
            new_callable=AsyncMock,
            return_value="https://picsum.photos/seed/42/800/600",
        ), patch(
            "app.repositories.image_repo.ImageRepo.create",
            new_callable=AsyncMock,
            return_value=_mock_image_row(),
        ):
            resp = await client.post(
                f"/projects/{PROJECT_ID}/images",
                json={"prompt": "a futuristic dashboard"},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["prompt"] == "a futuristic dashboard"
    assert data["provider"] == "mock"


@pytest.mark.asyncio
async def test_list_images():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.image_repo.ImageRepo.list_by_project",
            new_callable=AsyncMock,
            return_value=[_mock_image_row()],
        ):
            resp = await client.get(f"/projects/{PROJECT_ID}/images")

    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_analyze_image_returns_analysis():
    analyzed_row = _mock_image_row()
    analyzed_row["analysis"] = "A clean dark UI dashboard with teal accents."
    analyzed_row["analyzed_at"] = "2026-01-01T01:00:00+00:00"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.image_repo.ImageRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_image_row(),   # analysis is None → triggers Gemini
        ), patch(
            "app.ai.gemini.image_analyzer.GeminiImageAnalyzer.analyze",
            new_callable=AsyncMock,
            return_value="A clean dark UI dashboard with teal accents.",
        ), patch(
            "app.repositories.image_repo.ImageRepo.update_analysis",
            new_callable=AsyncMock,
            return_value=analyzed_row,
        ):
            resp = await client.post(
                f"/projects/{PROJECT_ID}/images/{IMAGE_ID}/analyze"
            )

    assert resp.status_code == 200
    assert resp.json()["analysis"] == "A clean dark UI dashboard with teal accents."


# ══════════════════════════════════════════════════════════════════════════
# 7. MEMORY
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_memory_snapshot():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.memory_repo.MemoryRepo.list_by_project",
            new_callable=AsyncMock,
            return_value=[],   # empty memory is valid
        ):
            resp = await client.get(f"/projects/{PROJECT_ID}/memory")

    assert resp.status_code == 200
    data = resp.json()
    # All four categories must be present
    assert "context"     in data
    assert "decisions"   in data
    assert "entities"    in data
    assert "constraints" in data


# ══════════════════════════════════════════════════════════════════════════
# 8. AGENT RUNS
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_trigger_agent_run_returns_202():
    run_row = {
        "id": "00000000-0000-0000-0000-000000000099",
        "project_id": str(PROJECT_ID),
        "status": "pending",
        "triggered_by": "api",
        "started_at": None,
        "completed_at": None,
        "error_message": None,
        "output": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.project_repo.ProjectRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=_mock_project_row(),
        ), patch(
            "app.repositories.agent_run_repo.AgentRunRepo.create",
            new_callable=AsyncMock,
            return_value=run_row,
        ), patch(
            # Prevent background task from actually firing
            "app.services.agent_run_service.AgentRunService.execute_run",
            new_callable=AsyncMock,
        ):
            resp = await client.post(f"/projects/{PROJECT_ID}/agent-runs")

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["triggered_by"] == "api"


@pytest.mark.asyncio
async def test_get_agent_run_status():
    run_row = {
        "id": "00000000-0000-0000-0000-000000000099",
        "project_id": str(PROJECT_ID),
        "status": "completed",
        "triggered_by": "api",
        "started_at": "2026-01-01T00:00:01+00:00",
        "completed_at": "2026-01-01T00:00:05+00:00",
        "error_message": None,
        "output": {"entries_written": {"context": 1}},
        "created_at": "2026-01-01T00:00:00+00:00",
    }

    run_id = "00000000-0000-0000-0000-000000000099"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch(
            "app.repositories.agent_run_repo.AgentRunRepo.get_by_id",
            new_callable=AsyncMock,
            return_value=run_row,
        ):
            resp = await client.get(
                f"/projects/{PROJECT_ID}/agent-runs/{run_id}"
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["output"]["entries_written"]["context"] == 1