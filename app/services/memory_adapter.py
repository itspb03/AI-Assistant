import json
import asyncio
from uuid import UUID
from pathlib import Path
from typing import Any

from app.config import get_settings


CATEGORIES = ["context", "decisions", "entities", "constraints"]


class MemoryAdapter:
    

    def __init__(self):
        self.base_path = Path(get_settings().memory_store_path)

    def _project_dir(self, project_id: UUID) -> Path:
        path = self.base_path / str(project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _file(self, project_id: UUID, category: str) -> Path:
        filename = category if category.endswith("s") else f"{category}s"
        return self._project_dir(project_id) / f"{filename}.json"

    async def read(self, project_id: UUID) -> dict[str, Any]:
        """
        Returns the full memory snapshot for a project.
        Used to build the LLM's system prompt context.
        """
        result = {}
        for category in CATEGORIES:
            path = self._file(project_id, category)
            if path.exists():
                content = await asyncio.to_thread(path.read_text, encoding="utf-8")
                result[category] = json.loads(content)
            else:
                result[category] = {}
        return result

    async def write(
        self,
        project_id: UUID,
        category: str,
        key: str,
        summary: str,
        detail: dict,
    ) -> None:
        """
        Upserts a single entry into the correct category file.
        Thread-safe for single-process deployments.
        """
        path = self._file(project_id, category)

        
        if path.exists():
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
            data = json.loads(content)
        else:
            data = {}

        data[key] = {"summary": summary, "detail": detail}

        tmp = path.with_suffix(".tmp")
        await asyncio.to_thread(
            tmp.write_text, json.dumps(data, indent=2), encoding="utf-8"
        )
        await asyncio.to_thread(tmp.replace, path)

    async def clear(self, project_id: UUID) -> None:
        """Wipe all memory files for a project."""
        project_dir = self._project_dir(project_id)
        for category in CATEGORIES:
            path = self._file(project_id, category)
            if path.exists():
                await asyncio.to_thread(path.unlink)

    def format_for_prompt(self, memory: dict[str, Any]) -> str:
        """
        Converts memory dict into a compact string for injection
        into the LLM's system prompt.
        """
        lines = ["## Project Memory\n"]
        for category, entries in memory.items():
            if not entries:
                continue
            lines.append(f"### {category.capitalize()}")
            for key, value in entries.items():
                lines.append(f"- **{key}**: {value.get('summary', '')}")
        return "\n".join(lines) if len(lines) > 1 else ""
