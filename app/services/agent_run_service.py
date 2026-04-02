from uuid import UUID
from fastapi import HTTPException, status

from app.repositories.agent_run_repo import AgentRunRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.agent_run import AgentRunOut
from app.agents.organizer_agent import OrganizerAgent


class AgentRunService:

    def __init__(
        self,
        run_repo: AgentRunRepo,
        project_repo: ProjectRepo,
        agent: OrganizerAgent,
    ):
        self.run_repo = run_repo
        self.project_repo = project_repo
        self.agent = agent

    async def create_run(self, project_id: UUID) -> AgentRunOut:
        await self._assert_project_exists(project_id)
        row = await self.run_repo.create(project_id)
        return AgentRunOut(**row)

    async def execute_run(self, run_id: UUID) -> None:
        """
        Called as a FastAPI BackgroundTask — fire and forget.
        The agent updates run status itself (running → completed/failed).
        """
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            return
        await self.agent.run(
            run_id=run_id,
            project_id=run["project_id"],
        )

    async def get(self, run_id: UUID) -> AgentRunOut:
        row = await self.run_repo.get_by_id(run_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent run {run_id} not found.",
            )
        return AgentRunOut(**row)

    async def list_by_project(self, project_id: UUID) -> list[AgentRunOut]:
        await self._assert_project_exists(project_id)
        rows = await self.run_repo.list_by_project(project_id)
        return [AgentRunOut(**r) for r in rows]

    async def _assert_project_exists(self, project_id: UUID) -> None:
        row = await self.project_repo.get_by_id(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )