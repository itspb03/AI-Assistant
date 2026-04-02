from uuid import UUID
from typing import Optional, Any
from app.repositories.base import BaseRepository


class MessageRepo(BaseRepository):

    TABLE = "messages"

    async def create_user_message(
        self, conversation_id: UUID, project_id: UUID, content: str
    ) -> dict:
        return await self._insert({
            "conversation_id": str(conversation_id),
            "project_id": str(project_id),
            "role": "user",
            "content": content,
        })

    async def create_assistant_message(
        self, conversation_id: UUID, project_id: UUID, content: str
    ) -> dict:
        return await self._insert({
            "conversation_id": str(conversation_id),
            "project_id": str(project_id),
            "role": "assistant",
            "content": content,
        })

    async def create_tool_use_message(
        self,
        conversation_id: UUID,
        project_id: UUID,
        tool_name: str,
        tool_use_id: str,
        tool_input: dict,
    ) -> dict:
        return await self._insert({
            "conversation_id": str(conversation_id),
            "project_id": str(project_id),
            "role": "tool_use",
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "tool_input": tool_input,
        })

    async def create_tool_result_message(
        self,
        conversation_id: UUID,
        project_id: UUID,
        tool_use_id: str,
        tool_name: str,
        tool_output: Any,
    ) -> dict:
        return await self._insert({
            "conversation_id": str(conversation_id),
            "project_id": str(project_id),
            "role": "tool_result",
            "tool_name": tool_name,
            "tool_use_id": tool_use_id,
            "tool_output": tool_output,
        })

    async def get_by_conversation(self, conversation_id: UUID) -> list[dict]:
        """Returns full message history ordered oldest → newest."""
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=False)
            .execute()
        )
        return res.data

    async def get_recent_by_project(
        self, project_id: UUID, limit: int = 100
    ) -> list[dict]:
        """Used by the organizer agent to read recent chat context."""
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("project_id", str(project_id))
            .in_("role", ["user", "assistant"])   # skip tool noise
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(res.data))           # return chronological order

    async def _insert(self, payload: dict) -> dict:
        res = await self.db.table(self.TABLE).insert(payload).execute()
        return res.data[0]
    
    async def get_recent_by_conversation(
        self, conversation_id: UUID, limit: int = 20
    ) -> list[dict]:
        """
        Returns only the last N messages for a conversation.
        Older messages stay in DB but are NOT sent to Claude.
        This is the primary token cost control for chat.
        Default limit=20 covers ~10 back-and-forth turns — enough context.
        """
        res = (
            await self.db.table(self.TABLE)
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=True)   # newest first
            .limit(limit)
            .execute()
        )
        return list(reversed(res.data))       # return chronological order