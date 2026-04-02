from uuid import UUID
from typing import Optional
from app.repositories.base import BaseRepository


class ProjectRepo(BaseRepository):

    TABLE = "projects"

    async def create(self, name: str, description: Optional[str]) -> dict:
        res = (
            await self.db.table(self.TABLE)
            .insert({"name": name, "description": description})
            .execute()
        )
        return res.data[0]

    async def get_by_id(self, project_id: UUID) -> Optional[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("id", str(project_id))
            .execute()
        )
        return res.data[0] if res.data else None

    async def list_all(self) -> list[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data

    async def update(self, project_id: UUID, fields: dict) -> Optional[dict]:
        res = (
            await self.db.table(self.TABLE)
            .update(fields)
            .eq("id", str(project_id))
            .execute()
        )
        return res.data[0] if res.data else None

    async def delete(self, project_id: UUID) -> None:
        await (
            self.db.table(self.TABLE)
            .delete()
            .eq("id", str(project_id))
            .execute()
        )