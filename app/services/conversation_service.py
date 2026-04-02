from uuid import UUID
from fastapi import HTTPException, status

from app.repositories.conversation_repo import ConversationRepo
from app.repositories.message_repo import MessageRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.conversation import ConversationOut
from app.schemas.message import MessageOut


class ConversationService:

    def __init__(
        self,
        conversation_repo: ConversationRepo,
        message_repo: MessageRepo,
        project_repo: ProjectRepo,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.project_repo = project_repo

    async def list_by_project(self, project_id: UUID) -> list[ConversationOut]:
        await self._assert_project_exists(project_id)
        rows = await self.conversation_repo.list_by_project(project_id)
        return [ConversationOut(**r) for r in rows]

    async def get_messages(
        self, project_id: UUID, conversation_id: UUID
    ) -> list[MessageOut]:
        await self._assert_project_exists(project_id)
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if not conv or str(conv["project_id"]) != str(project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found.",
            )
        rows = await self.message_repo.get_by_conversation(conversation_id)
        return [MessageOut(**r) for r in rows]

    async def _assert_project_exists(self, project_id: UUID) -> None:
        row = await self.project_repo.get_by_id(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )