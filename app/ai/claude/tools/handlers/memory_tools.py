from uuid import UUID
from app.services.memory_service import MemoryService


class MemoryToolHandlers:

    def __init__(self, memory_service: MemoryService):
        self.memory_service = memory_service

    async def update_memory(
        self, tool_input: dict, project_id: UUID
    ) -> dict:
        entry = await self.memory_service.write_entry(
            project_id=project_id,
            category=tool_input["category"],
            key=tool_input["key"],
            summary=tool_input["summary"],
            detail=tool_input.get("detail"),
            source="claude",
        )
        return {
            "status": "saved",
            "category": entry.category,
            "key": entry.key,
            "summary": entry.summary,
        }

    async def read_memory(
        self, tool_input: dict, project_id: UUID
    ) -> dict:
        snapshot = await self.memory_service.get_snapshot(project_id)
        category = tool_input.get("category")

        if category == "context":
            return {"context": [e.model_dump() for e in snapshot.context]}
        elif category == "decision":
            return {"decisions": [e.model_dump() for e in snapshot.decisions]}
        elif category == "entity":
            return {"entities": [e.model_dump() for e in snapshot.entities]}
        elif category == "constraint":
            return {"constraints": [e.model_dump() for e in snapshot.constraints]}

        # No filter — return all
        return snapshot.model_dump()