from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
   
    groq_api_key: str
    groq_chat_model: str = "llama3-groq-70b-8192-tool-use-preview"
    groq_agent_model: str = "llama-3.3-70b-versatile"
    llm_max_tokens: int = 2048

    
    gemini_api_key: str
    gemini_model: str 
    gemini_max_tokens: int  # image analysis capped at ~300 words

    supabase_url: str
    supabase_key: str                     # service role key
    database_url: str = ""                # postgres connection string for migrations

    image_provider: str = "mock"
    openai_api_key: str = ""              # only needed if image_provider=dalle

    memory_store_path: str = "./memory_store"


    mock_ai: bool = False

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