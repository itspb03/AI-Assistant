import logging
import types
import anthropic
from functools import lru_cache
from app.config import get_settings

logger = logging.getLogger(__name__)
cost_logger = logging.getLogger("app.cost")  # Change 6: dedicated cost logger


@lru_cache
def get_anthropic_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(
        api_key=get_settings().anthropic_api_key
    )


# ── Pricing Profiles (USD per 1M tokens) ──────────────────────────────────
# Updated based on Anthropic's pricing for current and future generations.
SONNET_PRICES = {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30}
HAIKU_PRICES  = {"input": 0.80, "output": 4.00,  "cache_write": 1.00, "cache_read": 0.08}
OPUS_PRICES   = {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50}
_PRICE_FALLBACK = SONNET_PRICES


def _log_cost(model: str, usage: object) -> None:
    """
    Compute and log USD cost from Anthropic usage object (Change 6).
    
    Flexibility Logic:
    1. Detects pricing based on the model's lineage (Sonnet/Haiku/Opus).
    2. Uses .env settings only to label the "Tier" (Chat vs Agent) in the logs.
    """
    settings = get_settings()
    model_lower = model.lower()

    # 1. Identify Pricing Category (independent of which tier it's assigned to)
    if "opus" in model_lower:
        prices = OPUS_PRICES
        category = "Opus"
    elif "haiku" in model_lower:
        prices = HAIKU_PRICES
        category = "Haiku"
    else:
        # Default to Sonnet pricing for Sonnet and unknown models
        prices = SONNET_PRICES
        category = "Sonnet" if "sonnet" in model_lower else "Standard"

    # 2. Identify the active Tier Label from your .env
    # This correctly labels the log even if you use the same model for both tiers.
    tier_label = "Other"
    if model == settings.claude_chat_model:
        tier_label = "Chat"
    elif model == settings.claude_agent_model:
        tier_label = "Agent"

    input_tok  = getattr(usage, "input_tokens", 0) or 0
    output_tok = getattr(usage, "output_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read  = getattr(usage, "cache_read_input_tokens", 0) or 0

    # Cache write/read tokens are included in input_tokens, so subtract 
    # to avoid double-charging the billed_input rate.
    billed_input = max(0, input_tok - cache_write - cache_read)

    cost_usd = (
        billed_input  * prices["input"]
        + output_tok  * prices["output"]
        + cache_write * prices["cache_write"]
        + cache_read  * prices["cache_read"]
    ) / 1_000_000

    cost_logger.info(
        f"tier={tier_label} group={category} model={model} "
        f"input={input_tok} output={output_tok} "
        f"cache_write={cache_write} cache_read={cache_read} "
        f"cost_usd={cost_usd:.6f}"
    )


def _mock_message(text: str = "[MOCK] This is a test response.") -> object:
    """Returns an object that quacks like anthropic.types.Message (Change 4)."""
    block = types.SimpleNamespace(type="text", text=text)
    usage = types.SimpleNamespace(
        input_tokens=0, output_tokens=0,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )
    return types.SimpleNamespace(
        stop_reason="end_turn",
        content=[block],
        usage=usage,
    )


class ClaudeClient:
    """
    Thin wrapper around the Anthropic async client.
    Keeps the raw SDK call in one place — easy to swap or mock.
    All orchestration logic lives in orchestrator.py, not here.

    Changes applied here:
      1 — Accepts a `model` param so callers can pass the right tier.
      2 — `system` accepts str | list[dict] to support cache_control blocks.
      4 — Short-circuits with a mock response when MOCK_AI=true.
      5 — max_tokens defaults pulled from config, not hardcoded.
      6 — Logs USD cost after every real call.
    """

    def __init__(self, model: str | None = None):
        self.client = get_anthropic_client()
        # Change 1: caller passes model; default to chat model if not specified
        self.model = model or get_settings().claude_chat_model

    async def messages(
        self,
        messages: list[dict],
        system: str | list[dict],           # Change 2: accept list for caching
        tools: list[dict] | None = None,
        max_tokens: int | None = None,       # Change 5: none → use config default
    ) -> object:
        settings = get_settings()

        # Change 4: mock short-circuit
        if settings.mock_ai:
            logger.debug("MOCK_AI=true — skipping Claude messages() call")
            return _mock_message()

        resolved_max = max_tokens or settings.claude_chat_max_tokens

        kwargs: dict = dict(
            model=self.model,
            max_tokens=resolved_max,
            system=system,          # str or list[dict] — SDK accepts both
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        # Change 6: log cost
        _log_cost(self.model, response.usage)

        return response

    async def simple(self, prompt: str, max_tokens: int | None = None) -> str:
        """
        Single-turn call with no tools — used by the organizer agent.
        Returns extracted text directly.
        """
        settings = get_settings()

        # Change 4: mock short-circuit
        if settings.mock_ai:
            logger.debug("MOCK_AI=true — skipping Claude simple() call")
            return '{"context": [], "decisions": [], "entities": [], "constraints": []}'

        resolved_max = max_tokens or settings.claude_agent_max_tokens

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=resolved_max,
            messages=[{"role": "user", "content": prompt}],
        )

        # Change 6: log cost
        _log_cost(self.model, response.usage)

        return self._extract_text(response)

    @staticmethod
    def _extract_text(response: object) -> str:
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
