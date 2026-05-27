import json
import logging
from uuid import UUID

from app.ai.groq.client import GroqClient
from app.ai.groq.tools.registry import TOOL_REGISTRY
from app.ai.groq.tools.executor import ToolExecutor
from app.repositories.conversation_repo import ConversationRepo
from app.repositories.message_repo import MessageRepo
from app.services.memory_service import MemoryService
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """
    Owns the full LLM agentic loop for a single chat turn:

    1. Resolve or create conversation
    2. Load message history from DB
    3. Load project memory → inject into system prompt
    4. Call LLM with tools
    5. If LLM returns tool_calls → execute each → feed results back
    6. Repeat until stop_reason == "end_turn" or MAX_TOOL_ROUNDS reached
    7. Persist all messages (user, assistant, tool_use, tool_result)
    8. Return ChatResponse

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
        llm: GroqClient,
        executor: ToolExecutor,
        conversation_repo: ConversationRepo,
        message_repo: MessageRepo,
        memory_service: MemoryService,
    ):
        self.llm = llm
        self.executor = executor
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.memory_service = memory_service

    async def run(
        self, project_id: UUID, request: ChatRequest
    ) -> ChatResponse:
        # resolving conversation
        conversation_id = await self._resolve_conversation(
            project_id, request.conversation_id
        )

        # loading history
        history = await self._build_history(conversation_id)

        # loading memory 
        memory = await self.memory_service.load_for_prompt(project_id)
        memory_text = self.memory_service.adapter.format_for_prompt(memory)

        # Build system prompt as a plain string (Groq has no prompt caching)
        system = self.SYSTEM_PROMPT_BASE
        if memory_text:
            system += "\n\n" + memory_text

        # appending the new user message
        messages = history + [
            {"role": "user", "content": request.user_message}
        ]

        tool_calls_made: list[str] = []
        final_text = ""

        # agentic tool loop
        created_images = []
        for round_num in range(self.MAX_TOOL_ROUNDS):
            response = await self.llm.messages(
                messages=messages,
                system=system,
                tools=TOOL_REGISTRY,
            )

            if response.stop_reason == "end_turn":
                final_text = self.llm._extract_text(response)
                break

            if response.stop_reason == "tool_use":
                # Build the assistant message with tool_calls for history
                assistant_msg: dict = {"role": "assistant"}

                # Include text content if present
                text_content = self.llm._extract_text(response)
                assistant_msg["content"] = text_content if text_content else None

                # Include tool_calls in the assistant message
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["input"]),
                        },
                    }
                    for tc in response.tool_calls
                ]

                messages.append(assistant_msg)

                # Execute each tool and append results as role="tool" messages
                for tc in response.tool_calls:
                    tool_calls_made.append(tc["name"])
                    result = await self.executor.execute(
                        tool_name=tc["name"],
                        tool_input=tc["input"],
                        project_id=project_id,
                    )

                    # Collect images created via generate_image tool
                    if tc["name"] == "generate_image":
                        created_images.append(result)

                    # OpenAI format: each tool result is a separate message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result),
                    })
            else:
                final_text = self.llm._extract_text(response)
                break
        else:
            logger.warning(
                f"Max tool rounds ({self.MAX_TOOL_ROUNDS}) reached "
                f"for project {project_id}"
            )
            final_text = final_text or "I reached the maximum number of tool calls. Please try again."

        # persist all messages
        await self._persist_turn(
            conversation_id=conversation_id,
            project_id=project_id,
            user_message=request.user_message,
            messages=messages,          
            tool_calls_made=tool_calls_made,
        )

        # auto-title conversation from first user message
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
        Reconstructs the OpenAI-compatible messages array from DB rows.
        Converts tool_use and tool_result rows back to their API format.
        """
        rows = await self.message_repo.get_by_conversation(conversation_id)
        messages = []

        # We need to group tool_use rows into the preceding assistant message
        # as tool_calls. Collect them and attach when we see tool_result rows.
        pending_tool_calls = []

        for row in rows:
            role = row["role"]

            if role == "user":
                messages.append({"role": "user", "content": row["content"]})

            elif role == "assistant":
                messages.append({"role": "assistant", "content": row["content"]})

            elif role == "tool_use":
                # Collect tool_use — will be embedded in an assistant message
                pending_tool_calls.append({
                    "id": row["tool_use_id"],
                    "type": "function",
                    "function": {
                        "name": row["tool_name"],
                        "arguments": json.dumps(row["tool_input"] or {}),
                    },
                })

            elif role == "tool_result":
                # If we have pending tool_calls, create the assistant message first
                if pending_tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": pending_tool_calls,
                    })
                    pending_tool_calls = []

                # Append the tool result as role="tool"
                messages.append({
                    "role": "tool",
                    "tool_call_id": row["tool_use_id"],
                    "content": json.dumps(row["tool_output"] or {}),
                })

        # Flush any remaining pending tool calls (shouldn't happen normally)
        if pending_tool_calls:
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": pending_tool_calls,
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

        await self.message_repo.create_user_message(
            conversation_id=conversation_id,
            project_id=project_id,
            content=user_message,
        )

        # Iterate through messages looking for tool-related entries and final assistant
        for msg in messages:
            role = msg.get("role")

            # Persist tool_use from assistant messages with tool_calls
            if role == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    tool_input = func.get("arguments", "{}")
                    try:
                        parsed_input = json.loads(tool_input)
                    except (json.JSONDecodeError, TypeError):
                        parsed_input = {}

                    await self.message_repo.create_tool_use_message(
                        conversation_id=conversation_id,
                        project_id=project_id,
                        tool_name=func.get("name", ""),
                        tool_use_id=tc["id"],
                        tool_input=parsed_input,
                    )

            # Persist tool results
            elif role == "tool":
                tool_output = msg.get("content", "{}")
                try:
                    parsed_output = json.loads(tool_output)
                except (json.JSONDecodeError, TypeError):
                    parsed_output = {}

                await self.message_repo.create_tool_result_message(
                    conversation_id=conversation_id,
                    project_id=project_id,
                    tool_use_id=msg.get("tool_call_id", ""),
                    tool_name="",
                    tool_output=parsed_output,
                )

        # Persist final assistant text (last assistant message with string content)
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                await self.message_repo.create_assistant_message(
                    conversation_id=conversation_id,
                    project_id=project_id,
                    content=msg["content"],
                )
                break
