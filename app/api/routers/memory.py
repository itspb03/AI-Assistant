from fastapi import APIRouter, HTTPException
from app.schemas.memory import MemoryFileOut, MemoryFileUpsert
from app.api.deps import memory_svc
import uuid

router = APIRouter(prefix="/projects/{project_id}/memory", tags=["memory"])


@router.get("", response_model=list[MemoryFileOut])
def list_memory(project_id: uuid.UUID):
    return memory_svc().list(project_id)


@router.put("", response_model=MemoryFileOut)
def upsert_memory(project_id: uuid.UUID, body: MemoryFileUpsert):
    return memory_svc().upsert(project_id, body.key, body.content)


@router.delete("/{key}", status_code=204)
def delete_memory(project_id: uuid.UUID, key: str):
    memory_svc().delete(project_id, key)