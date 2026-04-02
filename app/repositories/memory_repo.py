from uuid import UUID
from typing import Optional
from app.repositories.base import BaseRepository


class MemoryRepo(BaseRepository):

    TABLE = "memory_entries"

    async def upsert(
        self,
        project_id: UUID,
        category: str,
        key: str,
        summary: str,
        detail: Optional[dict],
        source: str = "agent",
    ) -> dict:
        """
        Insert or update a memory entry.
        Uniqueness is enforced by (project_id, category, key).
        """
        res = (
            await self.db.table(self.TABLE)
            .upsert(
                {
                    "project_id": str(project_id),
                    "category": category,
                    "key": key,
                    "summary": summary,
                    "detail": detail or {},
                    "source": source,
                },
                on_conflict="project_id,category,key",
            )
            .execute()
        )
        return res.data[0]

    async def list_by_project(self, project_id: UUID) -> list[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .order("category")
            .execute()
        )
        return res.data

    async def list_by_category(
        self, project_id: UUID, category: str
    ) -> list[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .eq("category", category)
            .execute()
        )
        return res.data

    async def delete_by_project(self, project_id: UUID) -> None:
        await (
            self.db.table(self.TABLE)
            .delete()
            .eq("project_id", str(project_id))
            .execute()
        )