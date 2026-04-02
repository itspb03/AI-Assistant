from uuid import UUID
from fastapi import APIRouter, Depends

from app.schemas.brief import BriefCreate, BriefOut
from app.services.brief_service import BriefService
from app.dependencies import get_brief_service

router = APIRouter(prefix="/projects/{project_id}/brief", tags=["Briefs"])


@router.get("", response_model=BriefOut)
async def get_brief(
    project_id: UUID,
    svc: BriefService = Depends(get_brief_service),
):
    return await svc.get(project_id)


@router.put("", response_model=BriefOut)
async def upsert_brief(
    project_id: UUID,
    body: BriefCreate,
    svc: BriefService = Depends(get_brief_service),
):
    """Creates the brief if none exists, updates it if one does."""
    return await svc.upsert(project_id, body)