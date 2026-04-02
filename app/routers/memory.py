from uuid import UUID
from fastapi import APIRouter, Depends

from app.schemas.memory import MemorySnapshot
from app.services.memory_service import MemoryService
from app.dependencies import get_memory_service

router = APIRouter(prefix="/projects/{project_id}/memory", tags=["Memory"])


@router.get("", response_model=MemorySnapshot)
async def get_memory(
    project_id: UUID,
    svc: MemoryService = Depends(get_memory_service),
):
    """
    Returns all structured memory for this project,
    grouped by category (context, decisions, entities, constraints).
    """
    return await svc.get_snapshot(project_id)


@router.delete("", status_code=204)
async def clear_memory(
    project_id: UUID,
    svc: MemoryService = Depends(get_memory_service),
):
    """Wipe all memory for this project. Useful for resets during development."""
    await svc.clear(project_id)