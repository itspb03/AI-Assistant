import json
import logging
from uuid import UUID

import anthropic

from app.ai.claude.client import ClaudeClient
from app.ai.claude.tools.registry import TOOL_REGISTRY
from app.ai.claude.tools.executor import ToolExecutor
from app.repositories.conversation_repo import ConversationRepo
from app.repositories.message_repo import MessageRepo
from app.services.memory_service import MemoryService
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Owns the full Claude agentic loop for a single chat turn:

    1. Resolve or create conversation
    2. Load message history from DB
    3. Load project memory → inject into system prompt
    4. Call Claude with tools
    5. If Claude returns tool_use blocks → execute each → feed results back
    6. Repeat until stop_reason == "end_turn" or MAX_TOOL_ROUNDS reached
    7. Persist all messages (user, assistant, tool_use, tool_result)
    8. Return ChatResponse

    Nothing else should call ClaudeClient directly for chat.
    """

    MAX_TOOL_ROUNDS = 8

    SYSTEM_PROMPT_BASE = """You are an AI Project Assistant helping users plan, 
manage, and execute their projects. You have access to the project brief, 
project memory, and can generate and analyze images.

Before answering questions about project details, always check the project 
brief and memory using the available tools. When the user confirms an 
important decision or fact, store it in memory using update_memory.

Be concise, direct, and helpful. Ask clarifying questions when needed.
"""

    def __init__(
        self,
        claude: ClaudeClient,
        executor: ToolExecutor,
        conversation_repo: ConversationRepo,
        message_repo: MessageRepo,
        memory_service: MemoryService,
    ):
        self.claude = claude
        self.executor = executor
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.memory_service = memory_service

    async def run(
        self, project_id: UUID, request: ChatRequest
    ) -> ChatResponse:
        # Step 1: resolve conversation
        conversation_id = await self._resolve_conversation(
            project_id, request.conversation_id
        )

        # Step 2: load history
        history = await self._build_history(conversation_id)

        # Step 3: load memory → system prompt
        memory = await self.memory_service.load_for_prompt(project_id)
        memory_text = self.memory_service.adapter.format_for_prompt(memory)

        # Change 2: Build system as a list of blocks so Anthropic can cache
        # the memory section (ephemeral cache, ~5 min TTL, ~90% token savings).
        # Block 1 — base instructions: not cached (changes rarely but varies per user)
        # Block 2 — memory/brief: cached (stable across turns in same conversation)
        system_blocks: list[dict] = [
            {"type": "text", "text": self.SYSTEM_PROMPT_BASE},
        ]
        if memory_text:
            system_blocks.append({
                "type": "text",
                "text": memory_text,
                "cache_control": {"type": "ephemeral"},
            })

        # Step 4: append the new user message
        messages = history + [
            {"role": "user", "content": request.user_message}
        ]

        tool_calls_made: list[str] = []
        final_text = ""

        # Step 5: agentic tool loop
        created_images = []
        for round_num in range(self.MAX_TOOL_ROUNDS):
            response = await self.claude.messages(
                messages=messages,
                system=system_blocks,   # Change 2: list with cache_control
                tools=TOOL_REGISTRY,
                # max_tokens omitted → ClaudeClient uses claude_chat_max_tokens from config
            )

            if response.stop_reason == "end_turn":
                final_text = self.claude._extract_text(response)
                break

            if response.stop_reason == "tool_use":
                # Collect all tool_use blocks in this response
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_calls_made.append(block.name)
                    result = await self.executor.execute(
                        tool_name=block.name,
                        tool_input=block.input,
                        project_id=project_id,
                    )
                    
                    # New: Collect images created via generate_image tool
                    if block.name == "generate_image":
                        created_images.append(result)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

                # Append assistant turn + tool results before next round
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                })
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })
            else:
                # Unexpected stop reason — treat as end
                final_text = self.claude._extract_text(response)
                break
        else:
            logger.warning(
                f"Max tool rounds ({self.MAX_TOOL_ROUNDS}) reached "
                f"for project {project_id}"
            )
            final_text = final_text or "I reached the maximum number of tool calls. Please try again."

        # Step 6: persist all messages
        await self._persist_turn(
            conversation_id=conversation_id,
            project_id=project_id,
            user_message=request.user_message,
            messages=messages,          # full updated history
            tool_calls_made=tool_calls_made,
        )

        # Step 7: auto-title conversation from first user message
        conv = await self.conversation_repo.get_by_id(conversation_id)
        if conv and not conv.get("title"):
            title = request.user_message[:60].strip()
            await self.conversation_repo.update_title(conversation_id, title)

        return ChatResponse(
            conversation_id=conversation_id,
            assistant_message=final_text,
            tool_calls_made=tool_calls_made,
            images=created_images,
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    async def _resolve_conversation(
        self, project_id: UUID, conversation_id: UUID | None
    ) -> UUID:
        if conversation_id:
            conv = await self.conversation_repo.get_by_id(conversation_id)
            if conv and str(conv["project_id"]) == str(project_id):
                return conversation_id
        # Create new conversation
        conv = await self.conversation_repo.create(project_id)
        return UUID(conv["id"])

    async def _build_history(self, conversation_id: UUID) -> list[dict]:
        """
        Reconstructs the Claude-compatible messages array from DB rows.
        Converts tool_use and tool_result rows back to their API format.
        """
        rows = await self.message_repo.get_by_conversation(conversation_id)
        messages = []

        for row in rows:
            role = row["role"]

            if role == "user":
                messages.append({"role": "user", "content": row["content"]})

            elif role == "assistant":
                messages.append({"role": "assistant", "content": row["content"]})

            elif role == "tool_use":
                # Reconstruct assistant message with tool_use block
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": row["tool_use_id"],
                        "name": row["tool_name"],
                        "input": row["tool_input"] or {},
                    }],
                })

            elif role == "tool_result":
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": row["tool_use_id"],
                        "content": json.dumps(row["tool_output"] or {}),
                    }],
                })

        return messages

    async def _persist_turn(
        self,
        conversation_id: UUID,
        project_id: UUID,
        user_message: str,
        messages: list[dict],
        tool_calls_made: list[str],
    ) -> None:
        """
        Persists only the NEW messages from this turn.
        We know the first new message is the user message — everything
        after the prior history end is new.
        """
        # Persist user message
        await self.message_repo.create_user_message(
            conversation_id=conversation_id,
            project_id=project_id,
            content=user_message,
        )

        # Walk new messages (everything after history + user message)
        # messages[-N:] where N = tool rounds * 2 + 1 (assistant final)
        # Simpler: persist the last assistant turn + any tool pairs
        new_messages = messages[
            # skip everything up to and including the new user message
            # original history length + 1 (the user message we just appended)
            :
        ]

        # Only persist messages added this turn (after original history + user msg)
        # We track by looking for tool_use / tool_result / final assistant blocks
        for msg in new_messages:
            if not isinstance(msg.get("content"), list):
                continue
            for block in msg["content"]:
                if isinstance(block, dict):
                    if block.get("type") == "tool_use":
                        await self.message_repo.create_tool_use_message(
                            conversation_id=conversation_id,
                            project_id=project_id,
                            tool_name=block["name"],
                            tool_use_id=block["id"],
                            tool_input=block.get("input", {}),
                        )
                    elif block.get("type") == "tool_result":
                        await self.message_repo.create_tool_result_message(
                            conversation_id=conversation_id,
                            project_id=project_id,
                            tool_use_id=block["tool_use_id"],
                            tool_name="",   # not stored on result side
                            tool_output=json.loads(block.get("content", "{}")),
                        )
                elif hasattr(block, "type"):
                    # SDK objects (not dicts) — from the final response
                    if block.type == "tool_use":
                        await self.message_repo.create_tool_use_message(
                            conversation_id=conversation_id,
                            project_id=project_id,
                            tool_name=block.name,
                            tool_use_id=block.id,
                            tool_input=block.input,
                        )

        # Persist final assistant text message
        from app.ai.claude.client import ClaudeClient
        for msg in reversed(new_messages):
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                await self.message_repo.create_assistant_message(
                    conversation_id=conversation_id,
                    project_id=project_id,
                    content=msg["content"],
                )
                break