from uuid import UUID
from fastapi import HTTPException, status

from app.repositories.memory_repo import MemoryRepo
from app.repositories.project_repo import ProjectRepo
from app.ai.claude.memory_adapter import MemoryAdapter
from app.schemas.memory import MemoryEntryOut, MemorySnapshot, MemoryCategory


class MemoryService:

    def __init__(
        self,
        memory_repo: MemoryRepo,
        project_repo: ProjectRepo,
        adapter: MemoryAdapter,
    ):
        self.memory_repo = memory_repo
        self.project_repo = project_repo
        self.adapter = adapter

    async def get_snapshot(self, project_id: UUID) -> MemorySnapshot:
        """
        Returns full grouped memory for a project.
        Reads from DB (faster than file I/O for listing).
        """
        await self._assert_project_exists(project_id)
        rows = await self.memory_repo.list_by_project(project_id)

        snapshot = MemorySnapshot(project_id=project_id)
        for row in rows:
            entry = MemoryEntryOut(**row)
            category = row["category"]
            if category == MemoryCategory.context:
                snapshot.context.append(entry)
            elif category == MemoryCategory.decision:
                snapshot.decisions.append(entry)
            elif category == MemoryCategory.entity:
                snapshot.entities.append(entry)
            elif category == MemoryCategory.constraint:
                snapshot.constraints.append(entry)

        return snapshot

    async def write_entry(
        self,
        project_id: UUID,
        category: str,
        key: str,
        summary: str,
        detail: dict | None = None,
        source: str = "claude",
    ) -> MemoryEntryOut:
        """
        Called by the Claude tool handler when Claude invokes update_memory.
        Writes to both the file adapter and the DB index.
        """
        await self._assert_project_exists(project_id)

        # Write to file store (source of truth)
        await self.adapter.write(project_id, category, key, summary, detail or {})

        # Update DB manifest
        row = await self.memory_repo.upsert(
            project_id=project_id,
            category=category,
            key=key,
            summary=summary,
            detail=detail,
            source=source,
        )
        return MemoryEntryOut(**row)

    async def load_for_prompt(self, project_id: UUID) -> dict:
        """
        Called by the orchestrator before every chat turn.
        Returns a clean dict suitable for injection into Claude's system prompt.
        Uses file adapter — returns richer structured data than the DB summary.
        """
        return await self.adapter.read(project_id)

    async def clear(self, project_id: UUID) -> None:
        """Wipe all memory for a project. Useful in tests / reset flows."""
        await self._assert_project_exists(project_id)
        await self.memory_repo.delete_by_project(project_id)
        await self.adapter.clear(project_id)

    async def _assert_project_exists(self, project_id: UUID) -> None:
        row = await self.project_repo.get_by_id(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )