from uuid import UUID
from typing import Optional
from app.repositories.base import BaseRepository


class BriefRepo(BaseRepository):

    TABLE = "briefs"

    async def get_by_project(self, project_id: UUID) -> Optional[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )
        return res.data[0] if res.data else None

    async def upsert(self, project_id: UUID, fields: dict) -> dict:
        """
        Creates brief if none exists, updates if one does.
        Increments version on each update.
        """
        existing = await self.get_by_project(project_id)

        if existing:
            fields["version"] = existing["version"] + 1
            res = (
                await self.db.table(self.TABLE)
                .update(fields)
                .eq("project_id", str(project_id))
                .execute()
            )
        else:
            fields["project_id"] = str(project_id)
            res = (
                await self.db.table(self.TABLE)
                .insert(fields)
                .execute()
            )

        return res.data[0]