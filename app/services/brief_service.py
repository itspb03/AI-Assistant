from uuid import UUID
from fastapi import HTTPException, status

from app.repositories.brief_repo import BriefRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.brief import BriefCreate, BriefUpdate, BriefOut


class BriefService:

    def __init__(self, brief_repo: BriefRepo, project_repo: ProjectRepo):
        self.brief_repo = brief_repo
        self.project_repo = project_repo

    async def get(self, project_id: UUID) -> BriefOut:
        await self._assert_project_exists(project_id)
        row = await self.brief_repo.get_by_project(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No brief found for project {project_id}.",
            )
        return BriefOut(**row)

    async def upsert(self, project_id: UUID, body: BriefCreate) -> BriefOut:
        await self._assert_project_exists(project_id)

        # Serialize references and open_questions for JSONB storage
        fields = body.model_dump(exclude_none=True)
        if "references" in fields:
            fields["references"] = [
                r if isinstance(r, dict) else r.model_dump()
                for r in (body.references or [])
            ]

        row = await self.brief_repo.upsert(project_id, fields)
        return BriefOut(**row)

    async def _assert_project_exists(self, project_id: UUID) -> None:
        row = await self.project_repo.get_by_id(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )