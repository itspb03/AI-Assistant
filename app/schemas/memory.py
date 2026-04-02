from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class MemoryCategory(str, Enum):
    context = "context"
    decision = "decision"
    entity = "entity"
    constraint = "constraint"


class MemorySource(str, Enum):
    agent = "agent"
    user = "user"
    claude = "claude"


class MemoryEntryOut(BaseModel):
    id: UUID
    project_id: UUID
    category: MemoryCategory
    key: str
    summary: str
    detail: Optional[dict[str, Any]] = None
    source: MemorySource
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemorySnapshot(BaseModel):
    """
    Full memory state for a project — returned by GET /memory.
    Grouped by category for easy reading by Claude or humans.
    """
    project_id: UUID
    context: list[MemoryEntryOut] = []
    decisions: list[MemoryEntryOut] = []
    entities: list[MemoryEntryOut] = []
    constraints: list[MemoryEntryOut] = []