from uuid import UUID
from typing import Optional
from datetime import datetime, timezone
from app.repositories.base import BaseRepository


class AgentRunRepo(BaseRepository):

    TABLE = "agent_runs"

    async def create(self, project_id: UUID, triggered_by: str = "api") -> dict:
        res = (
            await self.db.table(self.TABLE)
            .insert({
                "project_id": str(project_id),
                "status": "pending",
                "triggered_by": triggered_by,
            })
            .execute()
        )
        return res.data[0]

    async def get_by_id(self, run_id: UUID) -> Optional[dict]:
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("id", str(run_id))
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

    async def set_running(self, run_id: UUID) -> None:
        await (
            self.db.table(self.TABLE)
            .update({
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(run_id))
            .execute()
        )

    async def set_completed(self, run_id: UUID, output: dict) -> None:
        await (
            self.db.table(self.TABLE)
            .update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "output": output,
            })
            .eq("id", str(run_id))
            .execute()
        )

    async def set_failed(self, run_id: UUID, error: str) -> None:
        await (
            self.db.table(self.TABLE)
            .update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": error,
            })
            .eq("id", str(run_id))
            .execute()
        )