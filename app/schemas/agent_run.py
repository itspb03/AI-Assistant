from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class AgentRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentRunOut(BaseModel):
    id: UUID
    project_id: UUID
    status: AgentRunStatus
    triggered_by: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}