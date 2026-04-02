"""
Dependency injection wiring.
Every service, repo, and AI component is built here and injected
into routers via FastAPI's Depends() system.

Rule: routers import from here only — never instantiate services directly.
"""

from functools import lru_cache
from fastapi import Depends
from app.config import get_settings
from app.db.client import get_supabase

# ── Repositories ───────────────────────────────────────────────────────────
from app.repositories.project_repo import ProjectRepo
from app.repositories.brief_repo import BriefRepo
from app.repositories.conversation_repo import ConversationRepo
from app.repositories.message_repo import MessageRepo
from app.repositories.image_repo import ImageRepo
from app.repositories.memory_repo import MemoryRepo
from app.repositories.agent_run_repo import AgentRunRepo

# ── AI Layer ───────────────────────────────────────────────────────────────
from app.ai.claude.client import ClaudeClient
from app.ai.claude.memory_adapter import MemoryAdapter
from app.ai.claude.tools.handlers.project_tools import ProjectToolHandlers
from app.ai.claude.tools.handlers.memory_tools import MemoryToolHandlers
from app.ai.claude.tools.executor import ToolExecutor
from app.ai.claude.orchestrator import ChatOrchestrator
from app.ai.gemini.image_analyzer import GeminiImageAnalyzer
from app.ai.providers.image_generator import get_image_provider

# ── Services ───────────────────────────────────────────────────────────────
from app.services.project_service import ProjectService
from app.services.brief_service import BriefService
from app.services.image_service import ImageService
from app.services.memory_service import MemoryService
from app.services.conversation_service import ConversationService
from app.services.agent_run_service import AgentRunService

# ── Agents ─────────────────────────────────────────────────────────────────
from app.agents.organizer_agent import OrganizerAgent


# ── Singletons (created once per process) ─────────────────────────────────
# These are stateless or hold only config — safe to cache.

@lru_cache
def _claude_client() -> ClaudeClient:
    """Sonnet — user-facing chat (quality matters)."""
    return ClaudeClient(model=get_settings().claude_chat_model)

@lru_cache
def _claude_agent_client() -> ClaudeClient:
    """Haiku — background agent (speed + cost efficiency)."""
    return ClaudeClient(model=get_settings().claude_agent_model)

@lru_cache
def _memory_adapter() -> MemoryAdapter:
    return MemoryAdapter()

@lru_cache
def _gemini_analyzer() -> GeminiImageAnalyzer:
    return GeminiImageAnalyzer()

@lru_cache
def _image_provider():
    return get_image_provider()


# ── Repository factories ───────────────────────────────────────────────────
# Repos are lightweight — new instance per request is fine.
# Supabase client inside is cached via its own lru_cache.

async def get_project_repo() -> ProjectRepo:
    return ProjectRepo(client=await get_supabase())

async def get_brief_repo() -> BriefRepo:
    return BriefRepo(client=await get_supabase())

async def get_conversation_repo() -> ConversationRepo:
    return ConversationRepo(client=await get_supabase())

async def get_message_repo() -> MessageRepo:
    return MessageRepo(client=await get_supabase())

async def get_image_repo() -> ImageRepo:
    return ImageRepo(client=await get_supabase())

async def get_memory_repo() -> MemoryRepo:
    return MemoryRepo(client=await get_supabase())

async def get_agent_run_repo() -> AgentRunRepo:
    return AgentRunRepo(client=await get_supabase())


# ── Service factories ──────────────────────────────────────────────────────

def get_project_service(
    repo: ProjectRepo = Depends(get_project_repo),
) -> ProjectService:
    return ProjectService(repo=repo)


def get_brief_service(
    brief_repo: BriefRepo = Depends(get_brief_repo),
    project_repo: ProjectRepo = Depends(get_project_repo),
) -> BriefService:
    return BriefService(brief_repo=brief_repo, project_repo=project_repo)


def get_memory_service(
    memory_repo: MemoryRepo = Depends(get_memory_repo),
    project_repo: ProjectRepo = Depends(get_project_repo),
) -> MemoryService:
    return MemoryService(
        memory_repo=memory_repo,
        project_repo=project_repo,
        adapter=_memory_adapter(),
    )


def get_image_service(
    image_repo: ImageRepo = Depends(get_image_repo),
    project_repo: ProjectRepo = Depends(get_project_repo),
) -> ImageService:
    return ImageService(
        image_repo=image_repo,
        project_repo=project_repo,
        analyzer=_gemini_analyzer(),
        generator=_image_provider(),
    )


def get_conversation_service(
    conversation_repo: ConversationRepo = Depends(get_conversation_repo),
    message_repo: MessageRepo = Depends(get_message_repo),
    project_repo: ProjectRepo = Depends(get_project_repo),
) -> ConversationService:
    return ConversationService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        project_repo=project_repo,
    )


def _get_tool_executor(
    image_service: ImageService = Depends(get_image_service),
    memory_service: MemoryService = Depends(get_memory_service),
    brief_repo: BriefRepo = Depends(get_brief_repo),
    image_repo: ImageRepo = Depends(get_image_repo),
) -> ToolExecutor:
    project_handlers = ProjectToolHandlers(
        brief_repo=brief_repo,
        image_repo=image_repo,
        image_service=image_service,
    )
    memory_handlers = MemoryToolHandlers(
        memory_service=memory_service,
    )
    return ToolExecutor(
        project_handlers=project_handlers,
        memory_handlers=memory_handlers,
    )


def get_orchestrator(
    executor: ToolExecutor = Depends(_get_tool_executor),
    conversation_repo: ConversationRepo = Depends(get_conversation_repo),
    message_repo: MessageRepo = Depends(get_message_repo),
    memory_service: MemoryService = Depends(get_memory_service),
) -> ChatOrchestrator:
    return ChatOrchestrator(
        claude=_claude_client(),
        executor=executor,
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        memory_service=memory_service,
    )


def get_organizer_agent(
    run_repo: AgentRunRepo = Depends(get_agent_run_repo),
    brief_repo: BriefRepo = Depends(get_brief_repo),
    message_repo: MessageRepo = Depends(get_message_repo),
    memory_repo: MemoryRepo = Depends(get_memory_repo),
) -> OrganizerAgent:
    return OrganizerAgent(
        claude=_claude_agent_client(),
        run_repo=run_repo,
        brief_repo=brief_repo,
        message_repo=message_repo,
        memory_repo=memory_repo,
        memory_adapter=_memory_adapter(),
    )


def get_agent_run_service(
    run_repo: AgentRunRepo = Depends(get_agent_run_repo),
    project_repo: ProjectRepo = Depends(get_project_repo),
    agent: OrganizerAgent = Depends(get_organizer_agent),
) -> AgentRunService:
    return AgentRunService(
        run_repo=run_repo,
        project_repo=project_repo,
        agent=agent,
    )