from fastapi import APIRouter, HTTPException
from app.schemas.brief import BriefUpsert, BriefOut
from app.api.deps import brief_repo
import uuid

router = APIRouter(prefix="/projects/{project_id}/brief", tags=["briefs"])


@router.put("", response_model=BriefOut)
def upsert_brief(project_id: uuid.UUID, body: BriefUpsert):
    return brief_repo().upsert(project_id, body)


@router.get("", response_model=BriefOut | None)
def get_brief(project_id: uuid.UUID):
    return brief_repo().get(project_id)