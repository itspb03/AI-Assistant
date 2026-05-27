import uuid
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.schemas.chat import ChatRequest, ChatResponse
from app.ai.groq.orchestrator import ChatOrchestrator
from app.dependencies import get_orchestrator, _groq_client
from app.ai.groq.client import GroqClient

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])
general_router = APIRouter(prefix="/general-chat", tags=["General Chat"])


class GeneralChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=8000)
    history: list[dict] = Field(default_factory=list)


class GeneralChatResponse(BaseModel):
    assistant_message: str


@router.post("", response_model=ChatResponse)
async def chat(
    project_id: UUID,
    body: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_orchestrator),
):
    """
    Send a message to the LLM about this project.
    Pass conversation_id to continue an existing conversation,
    or omit it to start a new one.
    """
    return await orchestrator.run(project_id=project_id, request=body)


@general_router.post("", response_model=GeneralChatResponse)
async def general_chat(
    body: GeneralChatRequest,
    llm: GroqClient = Depends(_groq_client),
):
    """
    General multi-turn chat with Llama 70B when no project is active.
    """
    system = (
        "You are a helpful, direct, and concise AI Project Assistant. "
        "Since the user has not selected a project yet, you are engaging in "
        "general discussion. Help them brainstorm project ideas, answer general questions, "
        "or explain how this app can help them manage their projects."
    )

    # Format history to LLM structure
    messages = []
    for msg in body.history:
        role = msg.get("role")
        content = msg.get("content")
        if role in ["user", "assistant"] and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": body.user_message})

    response = await llm.messages(
        messages=messages,
        system=system,
    )
    final_text = llm._extract_text(response)

    return GeneralChatResponse(assistant_message=final_text)


from fastapi import UploadFile, File, Form
from typing import Optional
from app.dependencies import _gemini_analyzer, get_supabase
from pathlib import Path


class GeneralImageAnalysisResponse(BaseModel):
    analysis: str
    image_url: str


@general_router.post("/analyze-image", response_model=GeneralImageAnalysisResponse)
async def general_analyze_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
):
    """
    Stateless image analysis using Gemini Vision for General Chat (without project context).
    Uploads the image file to a 'general-uploads' folder inside Supabase storage,
    then executes Gemini Vision analysis with the custom prompt.
    """
    # 1. Collision-free path inside bucket
    ext = Path(file.filename or "upload").suffix or ".jpg"
    storage_path = f"general-uploads/{uuid.uuid4()}{ext}"

    # 2. Upload file to Storage Bucket
    db = await get_supabase()
    file_bytes = await file.read()
    await db.storage.from_("project-images").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": file.content_type or "image/jpeg", "upsert": "false"},
    )

    # 3. Resolve public URL
    public_url_resp = await db.storage.from_("project-images").get_public_url(storage_path)
    image_url = public_url_resp if isinstance(public_url_resp, str) else public_url_resp["publicUrl"]

    # 4. Trigger Gemini analysis
    analyzer = _gemini_analyzer()
    analysis = await analyzer.analyze(image_url, context=prompt)

    return GeneralImageAnalysisResponse(analysis=analysis, image_url=image_url)