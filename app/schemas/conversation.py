from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class ConversationOut(BaseModel):
    id: UUID
    project_id: UUID
    title: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}