from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from enum import Enum


class ImageProvider(str, Enum):
    mock = "mock"
    dalle = "dalle"
    stability = "stability"
    replicate = "replicate"
    upload = "upload"         # user-uploaded files via POST /upload


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class ImageOut(BaseModel):
    id: UUID
    project_id: UUID
    prompt: Optional[str]
    url: str
    provider: ImageProvider
    analysis: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}