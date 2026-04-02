from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, status

from app.schemas.image import ImageGenerateRequest, ImageOut
from app.services.image_service import ImageService
from app.dependencies import get_image_service

router = APIRouter(prefix="/projects/{project_id}/images", tags=["Images"])


@router.post("", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def generate_image(
    project_id: UUID,
    body: ImageGenerateRequest,
    svc: ImageService = Depends(get_image_service),
):
    """Generate an image from a prompt and attach it to the project."""
    return await svc.generate(project_id, body.prompt)


@router.get("", response_model=list[ImageOut])
async def list_images(
    project_id: UUID,
    svc: ImageService = Depends(get_image_service),
):
    return await svc.list_by_project(project_id)


@router.get("/{image_id}", response_model=ImageOut)
async def get_image(
    project_id: UUID,
    image_id: UUID,
    svc: ImageService = Depends(get_image_service),
):
    return await svc.get(project_id, image_id)


@router.post("/{image_id}/analyze", response_model=ImageOut)
async def analyze_image(
    project_id: UUID,
    image_id: UUID,
    svc: ImageService = Depends(get_image_service),
):
    """Run Gemini Vision analysis on a project image."""
    return await svc.analyze(project_id, image_id)


@router.post(
    "/upload",
    response_model=ImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image file and attach it to the project",
)
async def upload_project_image(
    project_id: UUID,
    file: UploadFile = File(..., description="Image file to upload (JPEG, PNG, WebP, …)"),
    svc: ImageService = Depends(get_image_service),
):
    """
    Upload *file* to Supabase Storage (`project-images` bucket), generate a
    public URL, and persist a record in the `project_images` table.

    Returns the newly created `project_images` row with `id` and `image_url`.
    """
    file_bytes = await file.read()
    return await svc.upload_file(
        project_id=project_id,
        file_bytes=file_bytes,
        original_filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
    )