from uuid import UUID
from fastapi import APIRouter, Depends, status

from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from app.services.project_service import ProjectService
from app.dependencies import get_project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    svc: ProjectService = Depends(get_project_service),
):
    return await svc.create(body)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    svc: ProjectService = Depends(get_project_service),
):
    return await svc.list_all()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    svc: ProjectService = Depends(get_project_service),
):
    return await svc.get(project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    svc: ProjectService = Depends(get_project_service),
):
    return await svc.update(project_id, body)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    svc: ProjectService = Depends(get_project_service),
):
    await svc.delete(project_id)