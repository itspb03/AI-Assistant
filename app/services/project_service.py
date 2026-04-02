from uuid import UUID
from typing import Optional
from fastapi import HTTPException, status

from app.repositories.project_repo import ProjectRepo
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut


class ProjectService:
    """
    Owns all business rules around projects.
    Repos do DB access. This layer decides what is allowed.
    """

    def __init__(self, repo: ProjectRepo):
        self.repo = repo

    async def create(self, body: ProjectCreate) -> ProjectOut:
        row = await self.repo.create(
            name=body.name,
            description=body.description,
        )
        return ProjectOut(**row)

    async def get(self, project_id: UUID) -> ProjectOut:
        row = await self.repo.get_by_id(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )
        return ProjectOut(**row)

    async def list_all(self) -> list[ProjectOut]:
        rows = await self.repo.list_all()
        return [ProjectOut(**r) for r in rows]

    async def update(self, project_id: UUID, body: ProjectUpdate) -> ProjectOut:
        # Ensure the project exists before updating
        await self.get(project_id)

        # Only send fields that were explicitly set by the caller
        fields = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update.",
            )

        row = await self.repo.update(project_id, fields)
        return ProjectOut(**row)

    async def delete(self, project_id: UUID) -> None:
        await self.get(project_id)   # 404 if missing
        await self.repo.delete(project_id)