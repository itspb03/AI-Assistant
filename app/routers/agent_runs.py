from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.schemas.agent_run import AgentRunOut
from app.services.agent_run_service import AgentRunService
from app.dependencies import get_agent_run_service

router = APIRouter(
    prefix="/projects/{project_id}/agent-runs",
    tags=["Agent Runs"],
)


@router.post("", response_model=AgentRunOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_agent_run(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    svc: AgentRunService = Depends(get_agent_run_service),
):
    """
    Triggers the organizer agent for this project.
    Returns immediately with a pending run record.
    Poll GET /{run_id} to track status.
    """
    run = await svc.create_run(project_id)
    background_tasks.add_task(svc.execute_run, run.id)
    return run


@router.get("", response_model=list[AgentRunOut])
async def list_agent_runs(
    project_id: UUID,
    svc: AgentRunService = Depends(get_agent_run_service),
):
    return await svc.list_by_project(project_id)


@router.get("/{run_id}", response_model=AgentRunOut)
async def get_agent_run(
    project_id: UUID,
    run_id: UUID,
    svc: AgentRunService = Depends(get_agent_run_service),
):
    """Poll this endpoint to check run status: pending → running → completed/failed."""
    return await svc.get(run_id)