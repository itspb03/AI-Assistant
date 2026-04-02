from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: Optional[UUID] = Field(
        None,
        description="Pass an existing ID to continue a conversation. "
                    "Leave null to start a new one."
    )


class ChatResponse(BaseModel):
    conversation_id: UUID
    assistant_message: str
    tool_calls_made: list[str] = Field(
        default_factory=list,
        description="Names of tools Claude invoked during this turn."
    )
    images: list[dict] = Field(
        default_factory=list,
        description="Metadata for images generated or retrieved during this turn."
    )