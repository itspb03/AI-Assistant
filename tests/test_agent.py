import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from app.agents.organizer_agent import OrganizerAgent

PROJECT_ID = UUID("00000000-0000-0000-0000-000000000001")
RUN_ID     = UUID("00000000-0000-0000-0000-000000000099")


def _make_agent(claude_response: str = None) -> OrganizerAgent:
    """Helper — builds OrganizerAgent with all dependencies mocked."""

    claude = MagicMock()
    claude.simple = AsyncMock(return_value=claude_response or json.dumps({
        "context":     [{"key": "project_type", "summary": "A REST API backend.", "detail": {}}],
        "decisions":   [{"key": "chosen_stack", "summary": "FastAPI + Supabase.", "detail": {}}],
        "entities":    [{"key": "anthropic_claude", "summary": "LLM used for chat.", "detail": {}}],
        "constraints": [{"key": "free_tier", "summary": "Must run on free Supabase tier.", "detail": {}}],
    }))

    run_repo = MagicMock()
    run_repo.set_running   = AsyncMock()
    run_repo.set_completed = AsyncMock()
    run_repo.set_failed    = AsyncMock()

    brief_repo = MagicMock()
    brief_repo.get_by_project = AsyncMock(return_value={
        "goals": "Build an AI project assistant",
        "target_audience": "Developers",
        "constraints": "Free tier only",
        "deliverables": "REST API",
        "tone": None,
        "open_questions": [],
    })

    message_repo = MagicMock()
    message_repo.get_recent_by_project = AsyncMock(return_value=[
        {"role": "user",      "content": "We decided to use FastAPI."},
        {"role": "assistant", "content": "Great choice! FastAPI is fast and async."},
    ])

    memory_repo = MagicMock()
    memory_repo.upsert = AsyncMock(return_value={})

    memory_adapter = MagicMock()
    memory_adapter.read  = AsyncMock(return_value={
        "context": {}, "decisions": {}, "entities": {}, "constraints": {}
    })
    memory_adapter.write = AsyncMock()

    return OrganizerAgent(
        claude=claude,
        run_repo=run_repo,
        brief_repo=brief_repo,
        message_repo=message_repo,
        memory_repo=memory_repo,
        memory_adapter=memory_adapter,
    )


# ── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_runs_successfully():
    agent = _make_agent()
    await agent.run(run_id=RUN_ID, project_id=PROJECT_ID)

    # Status lifecycle: running → completed
    agent.run_repo.set_running.assert_called_once_with(RUN_ID)
    agent.run_repo.set_completed.assert_called_once()
    agent.run_repo.set_failed.assert_not_called()


@pytest.mark.asyncio
async def test_agent_writes_all_four_categories():
    agent = _make_agent()
    await agent.run(run_id=RUN_ID, project_id=PROJECT_ID)

    # memory_adapter.write should be called once per entry (4 total)
    assert agent.memory_adapter.write.call_count == 4
    # memory_repo.upsert should also be called once per entry
    assert agent.memory_repo.upsert.call_count == 4


@pytest.mark.asyncio
async def test_agent_output_contains_entry_counts():
    agent = _make_agent()
    await agent.run(run_id=RUN_ID, project_id=PROJECT_ID)

    call_args = agent.run_repo.set_completed.call_args
    output = call_args.kwargs["output"]

    assert output["entries_written"]["context"]     == 1
    assert output["entries_written"]["decisions"]   == 1
    assert output["entries_written"]["entities"]    == 1
    assert output["entries_written"]["constraints"] == 1


@pytest.mark.asyncio
async def test_agent_marks_failed_on_claude_error():
    agent = _make_agent()
    # Make Claude raise an exception
    agent.claude.simple = AsyncMock(side_effect=Exception("Claude API timeout"))

    with pytest.raises(Exception):
        await agent.run(run_id=RUN_ID, project_id=PROJECT_ID)

    agent.run_repo.set_failed.assert_called_once()
    call_args = agent.run_repo.set_failed.call_args
    assert "Claude API timeout" in call_args.kwargs["error"]


@pytest.mark.asyncio
async def test_agent_handles_invalid_json_from_claude():
    agent = _make_agent(claude_response="This is not JSON at all.")

    with pytest.raises(ValueError, match="invalid JSON"):
        await agent.run(run_id=RUN_ID, project_id=PROJECT_ID)

    agent.run_repo.set_failed.assert_called_once()


@pytest.mark.asyncio
async def test_agent_skips_entries_with_missing_key_or_summary():
    """Entries with blank key or summary should be silently skipped."""
    bad_response = json.dumps({
        "context":     [{"key": "", "summary": "No key provided.", "detail": {}}],
        "decisions":   [{"key": "valid_key", "summary": "", "detail": {}}],
        "entities":    [],
        "constraints": [],
    })
    agent = _make_agent(claude_response=bad_response)
    await agent.run(run_id=RUN_ID, project_id=PROJECT_ID)

    # Both entries are invalid — nothing should be written
    assert agent.memory_adapter.write.call_count == 0


@pytest.mark.asyncio
async def test_agent_build_prompt_includes_brief_and_messages():
    agent = _make_agent()

    brief = {"goals": "Ship fast", "target_audience": "Teams"}
    messages = [
        {"role": "user",      "content": "Use PostgreSQL"},
        {"role": "assistant", "content": "Noted."},
    ]
    existing_memory = {"context": {}, "decisions": {}, "entities": {}, "constraints": {}}

    prompt = agent._build_prompt(brief, messages, existing_memory)

    assert "Ship fast" in prompt
    assert "Use PostgreSQL" in prompt
    assert "Project Brief" in prompt
    assert "Recent Conversation" in prompt