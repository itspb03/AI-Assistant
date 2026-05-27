import logging
import types
from functools import lru_cache
from openai import AsyncOpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)
cost_logger = logging.getLogger("app.cost")

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


@lru_cache
def get_groq_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=get_settings().groq_api_key,
        base_url=GROQ_BASE_URL,
    )


def _convert_tools(claude_tools: list[dict]) -> list[dict]:
    """
    Convert Claude-style tool definitions to OpenAI function-calling format.

    Claude:  {name, description, input_schema: {type, properties, required}}
    OpenAI:  {type: "function", function: {name, description, parameters: {type, properties, required}}}
    """
    openai_tools = []
    for tool in claude_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return openai_tools


def _mock_response(text: str = "[MOCK] This is a test response.") -> object:
    """Returns an object that mimics the normalized response shape."""
    return types.SimpleNamespace(
        stop_reason="end_turn",
        content=[types.SimpleNamespace(type="text", text=text)],
        tool_calls=[],
    )


class GroqClient:
    """
    OpenAI-compatible LLM client pointed at Groq's API.

    Provides two call styles:
    - messages()    : Chat with tool use (for the orchestrator tool loop)
    - simple_json() : Single-turn JSON extraction (for the organizer agent)
    """

    def __init__(self, model: str | None = None):
        self.client = get_groq_client()
        self.model = model or get_settings().groq_chat_model

    async def messages(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
    ) -> object:
        """
        Chat completion with optional tool use.
        
        Args:
            messages:   OpenAI-format messages list
            system:     System prompt (plain string)
            tools:      Claude-style tool defs (auto-converted to OpenAI format)
            max_tokens: Override for max output tokens
            
        Returns:
            Normalized response with:
            - stop_reason: "end_turn" | "tool_use"
            - content: list of SimpleNamespace(type="text", text=...)
            - tool_calls: list of dicts {name, id, input}
        """
        settings = get_settings()

        if settings.mock_ai:
            logger.debug("MOCK_AI=true — skipping Groq messages() call")
            return _mock_response()

        resolved_max = max_tokens or settings.llm_max_tokens

        # Prepend system message
        full_messages = [{"role": "system", "content": system}] + messages

        kwargs: dict = dict(
            model=self.model,
            max_tokens=resolved_max,
            messages=full_messages,
        )
        if tools:
            kwargs["tools"] = _convert_tools(tools)

        response = await self.client.chat.completions.create(**kwargs)

        self._log_usage(response)

        return self._normalize(response)

    async def simple_json(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """
        Single-turn call that guarantees valid JSON output.
        Used by the organizer agent — no tools, no multi-turn.
        
        Returns:
            Parsed dict directly (caller does NOT need json.loads).
        """
        import json
        settings = get_settings()

        if settings.mock_ai:
            logger.debug("MOCK_AI=true — skipping Groq simple_json() call")
            return {"context": [], "decisions": [], "entities": [], "constraints": []}

        resolved_max = max_tokens or settings.llm_max_tokens

        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=resolved_max,
            messages=msgs,
            response_format={"type": "json_object"},
        )

        self._log_usage(response)

        text = response.choices[0].message.content or ""
        return json.loads(text)

    def _log_usage(self, response) -> None:
        """Log token usage for cost tracking."""
        usage = response.usage
        if not usage:
            return

        input_tok = usage.prompt_tokens or 0
        output_tok = usage.completion_tokens or 0
        model = response.model or self.model

        cost_logger.info(
            f"model={model} "
            f"input={input_tok} output={output_tok} "
            f"total={input_tok + output_tok}"
        )

    @staticmethod
    def _normalize(response) -> object:
        """
        Converts OpenAI ChatCompletion to a normalized object matching
        what the orchestrator expects.
        """
        import json as _json
        choice = response.choices[0]
        message = choice.message

        # Determine stop reason
        if choice.finish_reason == "tool_calls":
            stop_reason = "tool_use"
        else:
            stop_reason = "end_turn"

        # Extract text content
        content = []
        if message.content:
            content.append(types.SimpleNamespace(type="text", text=message.content))

        # Extract tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "name": tc.function.name,
                    "id": tc.id,
                    "input": _json.loads(tc.function.arguments) if tc.function.arguments else {},
                })

        return types.SimpleNamespace(
            stop_reason=stop_reason,
            content=content,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _extract_text(response: object) -> str:
        """Extract text from a normalized response."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
