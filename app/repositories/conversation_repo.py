from uuid import UUID
from typing import Optional
from app.repositories.base import BaseRepository


class ConversationRepo(BaseRepository):

    TABLE = "conversations"

    async def create(self, project_id: UUID, title: Optional[str] = None) -> dict:
        res = (
            await self.db.table(self.TABLE)
            .insert({"project_id": str(project_id), "title": title})
            .execute()
        )
        return res.data[0]

    async def get_by_id(self, conversation_id: UUID) -> Optional[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("id", str(conversation_id))
            .execute()
        )
        return res.data[0] if res.data else None

    async def list_by_project(self, project_id: UUID) -> list[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .execute()
        )
        return res.data

    async def update_title(self, conversation_id: UUID, title: str) -> None:
        await (
            self.db.table(self.TABLE)
            .update({"title": title})
            .eq("id", str(conversation_id))
            .execute()
        )