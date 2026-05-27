from fastapi import APIRouter, HTTPException
from app.schemas.image import ImageGenerateRequest, ImageAnalyzeRequest, ImageOut
from app.api.deps import image_repo, storage_svc
from app.services.image_generation_service import generate_image as gen_image_bytes
from app.services.gemini_service import analyze_image as gemini_analyze
from app.core.exceptions import NotFoundError, AppError
import uuid

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=ImageOut, status_code=201)
def generate_image(body: ImageGenerateRequest):
    try:
        image_bytes = gen_image_bytes(body.prompt)
        svc = storage_svc()
        path, url = svc.upload_image(image_bytes, body.project_id)
        record = image_repo().create({
            "project_id": str(body.project_id),
            "conversation_id": str(body.conversation_id) if body.conversation_id else None,
            "prompt": body.prompt,
            "provider": "mock",
            "storage_url": url,
            "storage_path": path,
            "width": 1024,
            "height": 1024,
        })
        return record
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/analyze", response_model=ImageOut)
def analyze_image(body: ImageAnalyzeRequest):
    try:
        repo = image_repo()
        record = repo.get(body.image_id)
        image_bytes = storage_svc().download_image(record["storage_path"])
        analysis = gemini_analyze(image_bytes)
        return repo.update_analysis(body.image_id, analysis)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/project/{project_id}", response_model=list[ImageOut])
def list_images(project_id: uuid.UUID):
    return image_repo().list_for_project(project_id)