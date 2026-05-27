from fastapi import APIRouter, HTTPException
from app.schemas.conversation import ConversationCreate, ConversationOut, MessageOut
from app.api.deps import conv_repo, msg_repo
from app.core.exceptions import NotFoundError
import uuid

router = APIRouter(prefix="/projects/{project_id}/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(project_id: uuid.UUID, body: ConversationCreate):
    return conv_repo().create(project_id, body.title)


@router.get("", response_model=list[ConversationOut])
def list_conversations(project_id: uuid.UUID):
    return conv_repo().list_for_project(project_id)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(project_id: uuid.UUID, conversation_id: uuid.UUID):
    try:
        conv_repo().get(conversation_id)   # validates ownership
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    return msg_repo().list_for_conversation(conversation_id)