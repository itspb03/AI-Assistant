from uuid import UUID
from fastapi import HTTPException, status

from app.repositories.image_repo import ImageRepo
from app.repositories.project_repo import ProjectRepo
from app.schemas.image import ImageOut
from app.ai.gemini.image_analyzer import GeminiImageAnalyzer
from app.ai.providers.image_generator import ImageGeneratorProvider


class ImageService:

    def __init__(
        self,
        image_repo: ImageRepo,
        project_repo: ProjectRepo,
        analyzer: GeminiImageAnalyzer,
        generator: ImageGeneratorProvider,
    ):
        self.image_repo = image_repo
        self.project_repo = project_repo
        self.analyzer = analyzer
        self.generator = generator

    async def generate(self, project_id: UUID, prompt: str) -> ImageOut:
        await self._assert_project_exists(project_id)

        url = await self.generator.generate(prompt)
        row = await self.image_repo.create(
            project_id=project_id,
            prompt=prompt,
            url=url,
            provider=self.generator.provider_name,
        )
        return ImageOut(**row)

    async def analyze(self, project_id: UUID, image_id: UUID) -> ImageOut:
        row = await self.image_repo.get_by_id(image_id)
        if not row or str(row["project_id"]) != str(project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image {image_id} not found in project {project_id}.",
            )

        # If already analyzed, return cached result
        if row.get("analysis"):
            return ImageOut(**row)

        analysis = await self.analyzer.analyze(
            image_url=row["url"],
            context=row.get("prompt"),
        )
        updated = await self.image_repo.update_analysis(image_id, analysis)
        return ImageOut(**updated)

    async def list_by_project(self, project_id: UUID) -> list[ImageOut]:
        await self._assert_project_exists(project_id)
        rows = await self.image_repo.list_by_project(project_id)
        return [ImageOut(**r) for r in rows]

    async def get(self, project_id: UUID, image_id: UUID) -> ImageOut:
        row = await self.image_repo.get_by_id(image_id)
        if not row or str(row["project_id"]) != str(project_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image {image_id} not found.",
            )
        return ImageOut(**row)

    async def _assert_project_exists(self, project_id: UUID) -> None:
        row = await self.project_repo.get_by_id(project_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

    async def upload_file(
        self,
        project_id: UUID,
        file_bytes: bytes,
        original_filename: str,
        content_type: str,
    ) -> ImageOut:
        """Upload a raw file to Supabase Storage and record it in the `images` table."""
        await self._assert_project_exists(project_id)
        row = await self.image_repo.upload_project_image(
            project_id=project_id,
            file_bytes=file_bytes,
            original_filename=original_filename,
            content_type=content_type,
        )
        return ImageOut(**row)