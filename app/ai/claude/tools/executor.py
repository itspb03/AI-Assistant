from uuid import UUID
from app.ai.claude.tools.handlers.project_tools import ProjectToolHandlers
from app.ai.claude.tools.handlers.memory_tools import MemoryToolHandlers
import logging

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Dispatches Claude tool_use requests to the correct handler.
    New tools = add a handler method + register it in the dispatch map below.
    No tool logic lives here — only routing.
    """

    def __init__(
        self,
        project_handlers: ProjectToolHandlers,
        memory_handlers: MemoryToolHandlers,
    ):
        # Dispatch map: tool name → bound async method
        self._dispatch: dict = {
            "get_project_brief":  project_handlers.get_project_brief,
            "generate_image":     project_handlers.generate_image,
            "analyze_image":      project_handlers.analyze_image,
            "list_project_images": project_handlers.list_project_images,
            "update_memory":      memory_handlers.update_memory,
            "read_memory":        memory_handlers.read_memory,
        }

    async def execute(
        self,
        tool_name: str,
        tool_input: dict,
        project_id: UUID,
    ) -> dict:
        handler = self._dispatch.get(tool_name)

        if not handler:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return {"error": f"Tool '{tool_name}' is not registered."}

        try:
            logger.info(f"Executing tool: {tool_name} for project {project_id}")
            result = await handler(tool_input, project_id=project_id)
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"error": str(e)}