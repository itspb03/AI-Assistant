from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class BriefReference(BaseModel):
    """A single reference link or note."""
    label: str
    url: Optional[str] = None
    note: Optional[str] = None


class BriefCreate(BaseModel):
    goals: Optional[str] = Field(
        None, description="What does success look like for this project?"
    )
    target_audience: Optional[str] = Field(
        None, description="Who is this project built for?"
    )
    constraints: Optional[str] = Field(
        None, description="Budget, timeline, or technical limits."
    )
    deliverables: Optional[str] = Field(
        None, description="What must be produced or shipped?"
    )
    tone: Optional[str] = Field(
        None, description="Voice or style if content-related."
    )
    reference_links: Optional[list[BriefReference]] = Field(
        default_factory=list
    )
    open_questions: Optional[list[str]] = Field(
        default_factory=list,
        description="Unresolved decisions or questions."
    )


class BriefUpdate(BriefCreate):
    pass


class BriefOut(BriefCreate):
    id: UUID
    project_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}