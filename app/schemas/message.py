from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    tool_use = "tool_use"
    tool_result = "tool_result"


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    project_id: UUID
    role: MessageRole

    # user / assistant turns
    content: Optional[str] = None

    # tool_use / tool_result turns
    tool_name: Optional[str] = None
    tool_use_id: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    tool_output: Optional[dict[str, Any]] = None

    created_at: datetime

    model_config = {"from_attributes": True}