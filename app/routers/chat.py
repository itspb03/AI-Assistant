from uuid import UUID
from fastapi import APIRouter, Depends

from app.schemas.chat import ChatRequest, ChatResponse
from app.ai.claude.orchestrator import ChatOrchestrator
from app.dependencies import get_orchestrator

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    project_id: UUID,
    body: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_orchestrator),
):
    """
    Send a message to Claude about this project.
    Pass conversation_id to continue an existing conversation,
    or omit it to start a new one.
    """
    return await orchestrator.run(project_id=project_id, request=body)