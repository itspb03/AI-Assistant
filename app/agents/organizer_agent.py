import re
import json
import logging
from uuid import UUID

from app.ai.claude.client import ClaudeClient
from app.ai.claude.memory_adapter import MemoryAdapter
from app.repositories.agent_run_repo import AgentRunRepo
from app.repositories.brief_repo import BriefRepo
from app.repositories.memory_repo import MemoryRepo
from app.repositories.message_repo import MessageRepo

logger = logging.getLogger(__name__)


class OrganizerAgent:
    """
    A single-pass Claude call — NOT a tool loop.

    Triggered via POST /projects/{id}/agent-runs.
    Reads:  project brief + last 100 user/assistant messages + existing memory
    Writes: structured memory entries across all 4 categories
    Tracks: run status in agent_runs table (pending → running → completed/failed)

    Design note:
    This agent uses a directed summarization call. Claude is given a strict
    output schema (JSON) and asked to extract durable knowledge.
    We do not use the tool loop here because the task is fully defined upfront —
    there is no need for Claude to decide what to do next.
    """

    SYSTEM_PROMPT = """You are a project memory organizer for an AI Project Assistant.

Your job is to read a project brief and recent conversation history, then 
extract durable structured knowledge into four categories:

- context:     Background facts about the project (what it is, why it exists)
- decisions:   Confirmed choices (tech stack, platform, approach, design decisions)
- entities:    Named things — people, tools, platforms, companies, frameworks
- constraints: Hard limits — budget, timeline, team size, technical restrictions

Rules:
- Do NOT store raw conversation snippets or paraphrased chat.
- Store only facts that would still be useful weeks later.
- Each entry needs a short unique key (slug format: snake_case).
- Each entry needs a 1-2 sentence summary.
- If the conversation is vague or has no durable facts, return empty arrays.
- Merge with existing memory — do not duplicate existing keys unless updating them.

Output ONLY valid JSON in this exact format, no markdown, no explanation:
{
  "context":     [{"key": "...", "summary": "...", "detail": {}}],
  "decisions":   [{"key": "...", "summary": "...", "detail": {}}],
  "entities":    [{"key": "...", "summary": "...", "detail": {}}],
  "constraints": [{"key": "...", "summary": "...", "detail": {}}]
}
"""

    def __init__(
        self,
        claude: ClaudeClient,
        run_repo: AgentRunRepo,
        brief_repo: BriefRepo,
        message_repo: MessageRepo,
        memory_repo: MemoryRepo,
        memory_adapter: MemoryAdapter,
    ):
        self.claude = claude
        self.run_repo = run_repo
        self.brief_repo = brief_repo
        self.message_repo = message_repo
        self.memory_repo = memory_repo
        self.memory_adapter = memory_adapter

    async def run(self, run_id: UUID, project_id: UUID) -> None:
        await self.run_repo.set_running(run_id)
        logger.info(f"Organizer agent started: run={run_id} project={project_id}")

        try:
            
            brief = await self.brief_repo.get_by_project(project_id)
            messages = await self.message_repo.get_recent_by_project(
                project_id, limit=100
            )
            existing_memory = await self.memory_adapter.read(project_id)

            
            prompt = self._build_prompt(brief, messages, existing_memory)

            
            raw = await self.claude.simple(prompt)
            structured = self._parse_output(raw)

            
            counts = await self._write_memory(project_id, structured)

            logger.info(
                f"Organizer agent completed: run={run_id} "
                f"entries_written={sum(counts.values())}"
            )
            await self.run_repo.set_completed(
                run_id,
                output={"entries_written": counts, "categories": structured},
            )

        except Exception as e:
            logger.error(f"Organizer agent failed: run={run_id} error={e}")
            await self.run_repo.set_failed(run_id, error=str(e))
            raise

    

    def _build_prompt(
        self,
        brief: dict | None,
        messages: list[dict],
        existing_memory: dict,
    ) -> str:
        parts = []

        # Brief section
        if brief:
            parts.append("## Project Brief")
            for field in ["goals", "target_audience", "constraints",
                          "deliverables", "tone"]:
                if brief.get(field):
                    parts.append(f"**{field.replace('_', ' ').title()}**: {brief[field]}")
            if brief.get("open_questions"):
                parts.append(f"**Open Questions**: {brief['open_questions']}")
        else:
            parts.append("## Project Brief\n(No brief has been set yet.)")

        # Conversation history section
        parts.append("\n## Recent Conversation")
        if messages:
            for msg in messages:
                role = msg["role"].upper()
                content = msg.get("content") or ""
                if content:
                    # Truncate very long messages
                    preview = content[:500] + "..." if len(content) > 500 else content
                    parts.append(f"[{role}]: {preview}")
        else:
            parts.append("(No conversation history yet.)")

        # Existing memory section
        parts.append("\n## Existing Memory (do not duplicate these keys)")
        for category, entries in existing_memory.items():
            if entries:
                parts.append(f"### {category.capitalize()}")
                for key, val in entries.items():
                    parts.append(f"- {key}: {val.get('summary', '')}")

        parts.append(
            "\n## Task\nExtract and return structured memory as JSON per the instructions."
        )

        return "\n".join(parts)


    def _parse_output(self, raw: str) -> dict:
        """
        Parses Claude's JSON output with robust extraction.
        Finds the first '{' and last '}' to strip any preamble or fences.
        """
        # Find the bounding braces for the JSON object
        match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if not match:
            logger.error(f"No JSON block found in Claude output.\nRaw: {raw[:500]}")
            raise ValueError("Claude did not return a valid JSON block.")

        cleaned = match.group(0).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse organizer output: {e}\nCleaned: {cleaned[:300]}")
            # Log the raw output too for full context
            logger.debug(f"Full raw output: {raw}")
            raise ValueError(f"Claude returned invalid JSON: {e}")

        # Ensure all keys exist
        for key in ["context", "decisions", "entities", "constraints"]:
            data.setdefault(key, [])

        return data

    async def _write_memory(
        self, project_id: UUID, structured: dict
    ) -> dict[str, int]:
        """
        Writes all extracted entries to both file adapter and DB.
        Returns count of entries written per category.
        """
        counts = {}

        category_map = {
            "context": "context",
            "decisions": "decision",
            "entities": "entity",
            "constraints": "constraint",
        }

        for output_key, db_category in category_map.items():
            entries = structured.get(output_key, [])
            counts[output_key] = 0

            for entry in entries:
                key = entry.get("key", "").strip()
                summary = entry.get("summary", "").strip()
                detail = entry.get("detail", {})

                if not key or not summary:
                    continue

                # Write to file store
                await self.memory_adapter.write(
                    project_id=project_id,
                    category=db_category,
                    key=key,
                    summary=summary,
                    detail=detail,
                )

                # Write to DB manifest
                await self.memory_repo.upsert(
                    project_id=project_id,
                    category=db_category,
                    key=key,
                    summary=summary,
                    detail=detail,
                    source="agent",
                )

                counts[output_key] += 1

        return counts