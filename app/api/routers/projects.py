from fastapi import APIRouter, HTTPException
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from app.api.deps import project_repo
from app.core.exceptions import NotFoundError
import uuid

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate):
    return project_repo().create(body)


@router.get("", response_model=list[ProjectOut])
def list_projects(status: str | None = None):
    return project_repo().list(status=status)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID):
    try:
        return project_repo().get(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, body: ProjectUpdate):
    try:
        return project_repo().update(project_id, body)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID):
    project_repo().delete(project_id)