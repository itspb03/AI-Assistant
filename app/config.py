from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Anthropic ──────────────────────────────────────────────────────────
    anthropic_api_key: str

    # Change 1: Dual model tiers
    # claude_model kept for backwards-compat; new code uses the two below
    claude_model: str = "claude-3-5-sonnet-20241022"          # legacy alias
    claude_chat_model: str = "claude-3-5-sonnet-20241022"     # user-facing chat
    claude_agent_model: str = "claude-3-5-haiku-20241022"     # background agent

    # Change 5: Per-tier output token caps
    claude_chat_max_tokens: int = 2048    # chat turns — most replies are short
    claude_agent_max_tokens: int = 4096   # organizer outputs large JSON

    # ── Google Gemini ──────────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"
    gemini_max_tokens: int = 512          # image analysis capped at ~300 words

    # ── Supabase ───────────────────────────────────────────────────────────
    supabase_url: str
    supabase_key: str                     # service role key
    database_url: str = ""                # postgres connection string for migrations

    # ── Image generation ───────────────────────────────────────────────────
    # "mock" | "dalle" | "stability"
    image_provider: str = "mock"
    openai_api_key: str = ""              # only needed if image_provider=dalle

    # ── Memory file store ──────────────────────────────────────────────────
    memory_store_path: str = "./memory_store"

    # ── Cost controls ──────────────────────────────────────────────────────
    # Change 4: Set to true to skip ALL Claude + Gemini API calls (dev/test)
    mock_ai: bool = False

    # ── App ────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()