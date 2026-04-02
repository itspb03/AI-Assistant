from uuid import UUID
from fastapi import APIRouter, Depends

from app.schemas.conversation import ConversationOut
from app.schemas.message import MessageOut
from app.services.conversation_service import ConversationService
from app.dependencies import get_conversation_service

router = APIRouter(prefix="/projects/{project_id}", tags=["Conversations"])


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    project_id: UUID,
    svc: ConversationService = Depends(get_conversation_service),
):
    return await svc.list_by_project(project_id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
async def get_messages(
    project_id: UUID,
    conversation_id: UUID,
    svc: ConversationService = Depends(get_conversation_service),
):
    return await svc.get_messages(project_id, conversation_id)