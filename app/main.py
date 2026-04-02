import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.client import get_supabase
from app.routers import (
    projects,
    briefs,
    conversations,
    chat,
    images,
    memory,
    agent_runs,
)

# Configure logging once at startup
logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: validate settings and log readiness.
    Shutdown: nothing to clean up (Supabase client is stateless).
    """
    settings = get_settings()
    logger.info(f"Starting AI Project Assistant — env={settings.app_env}")
    logger.info(f"Claude chat  : {settings.claude_chat_model} (max {settings.claude_chat_max_tokens} tokens)")
    logger.info(f"Claude agent : {settings.claude_agent_model} (max {settings.claude_agent_max_tokens} tokens)")
    logger.info(f"Gemini model : {settings.gemini_model} (max {settings.gemini_max_tokens} tokens)")
    logger.info(f"Image provider: {settings.image_provider}")
    logger.info(f"Memory store  : {settings.memory_store_path}")
    logger.info(f"Mock AI       : {settings.mock_ai}")

    # NEW: Automated migrations
    from app.db.migrator import migrator
    await migrator.run_migrations()

    await get_supabase()   # ← eagerly init the async Supabase client singleton
    logger.info("Supabase client ready.")
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Project Assistant",
        description=(
            "Backend-first AI assistant for managing projects "
            "with Claude, Gemini, and persistent project memory."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — open for local dev; restrict in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all routers
    app.include_router(projects.router)
    app.include_router(briefs.router)
    app.include_router(conversations.router)
    app.include_router(chat.router)
    app.include_router(images.router)
    app.include_router(memory.router)
    app.include_router(agent_runs.router)

    # Serve static frontend files
    # Note: Mounted at '/' with html=True so it picks up index.html
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()