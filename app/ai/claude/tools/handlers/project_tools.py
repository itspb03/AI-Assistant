from uuid import UUID
from app.repositories.brief_repo import BriefRepo
from app.repositories.image_repo import ImageRepo
from app.services.image_service import ImageService


class ProjectToolHandlers:
    """
    Handles tools that read/write project data.
    Injected into ToolExecutor at startup.
    """

    def __init__(
        self,
        brief_repo: BriefRepo,
        image_repo: ImageRepo,
        image_service: ImageService,
    ):
        self.brief_repo = brief_repo
        self.image_repo = image_repo
        self.image_service = image_service

    async def get_project_brief(
        self, _input: dict, project_id: UUID
    ) -> dict:
        row = await self.brief_repo.get_by_project(project_id)
        if not row:
            return {"error": "No brief found for this project."}
        # Remove internal DB fields before returning to Claude
        row.pop("id", None)
        row.pop("project_id", None)
        return row

    async def generate_image(
        self, tool_input: dict, project_id: UUID
    ) -> dict:
        prompt = tool_input.get("prompt", "")
        image = await self.image_service.generate(project_id, prompt)
        return {
            "image_id": str(image.id),
            "url": image.url,
            "provider": image.provider,
            "prompt": image.prompt,
        }

    async def analyze_image(
        self, tool_input: dict, project_id: UUID
    ) -> dict:
        from uuid import UUID as _UUID
        image_id = _UUID(tool_input["image_id"])
        image = await self.image_service.analyze(project_id, image_id)
        return {
            "image_id": str(image.id),
            "analysis": image.analysis,
            "prompt": image.prompt,
        }

    async def list_project_images(
        self, _input: dict, project_id: UUID
    ) -> dict:
        images = await self.image_service.list_by_project(project_id)
        return {
            "images": [
                {
                    "image_id": str(img.id),
                    "prompt": img.prompt,
                    "url": img.url,
                    "analyzed": img.analysis is not None,
                }
                for img in images
            ]
        }