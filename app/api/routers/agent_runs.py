from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.schemas.agent_run import AgentRunOut
from app.api.deps import agent_run_repo, background_organizer
from app.workers.tasks import run_background_organizer
from app.core.exceptions import NotFoundError
import uuid

router = APIRouter(prefix="/projects/{project_id}/agent-runs", tags=["agent_runs"])


@router.post("", response_model=AgentRunOut, status_code=202)
def trigger_agent_run(project_id: uuid.UUID, background_tasks: BackgroundTasks):
    """
    Trigger the background organizer for a project.
    Returns immediately with status=pending; poll GET /{run_id} for updates.
    """
    repo = agent_run_repo()
    run = repo.create(project_id)
    run_id = uuid.UUID(str(run["id"]))
    organizer = background_organizer()
    background_tasks.add_task(run_background_organizer, organizer, project_id, run_id)
    return run


@router.get("", response_model=list[AgentRunOut])
def list_agent_runs(project_id: uuid.UUID):
    return agent_run_repo().list_for_project(project_id)


@router.get("/{run_id}", response_model=AgentRunOut)
def get_agent_run(project_id: uuid.UUID, run_id: uuid.UUID):
    try:
        return agent_run_repo().get(run_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)