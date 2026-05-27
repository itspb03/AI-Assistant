"""
FastAPI dependency factories.
Each function returns a fully wired service/repo/agent instance.
"""
from functools import lru_cache
from supabase import Client
from app.db.client import get_supabase
from app.repositories.projects import ProjectRepository
from app.repositories.briefs import BriefRepository
from app.repositories.conversations import ConversationRepository
from app.repositories.messages import MessageRepository
from app.repositories.images import ImageRepository
from app.repositories.memory_files import MemoryFileRepository
from app.repositories.tool_executions import ToolExecutionRepository
from app.repositories.agent_runs import AgentRunRepository
from app.services.memory_service import MemoryService
from app.services.storage_service import StorageService
from app.services.project_context_service import ProjectContextService
from app.services.chat_service import ChatService
from app.agents.memory_tool_adapter import MemoryToolAdapter
from app.agents.chat_orchestrator import ChatOrchestrator
from app.agents.background_organizer import BackgroundOrganizer


def get_db() -> Client:
    return get_supabase()


# ── Repositories ──────────────────────────────────────────────────────────── #

def project_repo(db: Client = None) -> ProjectRepository:
    return ProjectRepository(db or get_db())

def brief_repo(db: Client = None) -> BriefRepository:
    return BriefRepository(db or get_db())

def conv_repo(db: Client = None) -> ConversationRepository:
    return ConversationRepository(db or get_db())

def msg_repo(db: Client = None) -> MessageRepository:
    return MessageRepository(db or get_db())

def image_repo(db: Client = None) -> ImageRepository:
    return ImageRepository(db or get_db())

def memory_file_repo(db: Client = None) -> MemoryFileRepository:
    return MemoryFileRepository(db or get_db())

def tool_exec_repo(db: Client = None) -> ToolExecutionRepository:
    return ToolExecutionRepository(db or get_db())

def agent_run_repo(db: Client = None) -> AgentRunRepository:
    return AgentRunRepository(db or get_db())


# ── Services ──────────────────────────────────────────────────────────────── #

def memory_svc(db: Client = None) -> MemoryService:
    return MemoryService(memory_file_repo(db))

def storage_svc(db: Client = None) -> StorageService:
    return StorageService(db or get_db())

def ctx_svc(db: Client = None) -> ProjectContextService:
    return ProjectContextService(brief_repo(db), memory_svc(db))


# ── Agents ────────────────────────────────────────────────────────────────── #

def chat_orchestrator(db: Client = None) -> ChatOrchestrator:
    _db = db or get_db()
    return ChatOrchestrator(
        project_repo=project_repo(_db),
        conv_repo=conv_repo(_db),
        msg_repo=msg_repo(_db),
        brief_repo=brief_repo(_db),
        image_repo=image_repo(_db),
        tool_exec_repo=tool_exec_repo(_db),
        memory_svc=memory_svc(_db),
        storage_svc=storage_svc(_db),
        ctx_svc=ctx_svc(_db),
    )

def background_organizer(db: Client = None) -> BackgroundOrganizer:
    _db = db or get_db()
    return BackgroundOrganizer(
        project_repo=project_repo(_db),
        brief_repo=brief_repo(_db),
        msg_repo=msg_repo(_db),
        image_repo=image_repo(_db),
        run_repo=agent_run_repo(_db),
        memory_adapter=MemoryToolAdapter(memory_svc(_db)),
    )