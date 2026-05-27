from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.api.deps import chat_orchestrator
from app.core.exceptions import AppError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    try:
        orchestrator = chat_orchestrator()
        return await orchestrator.run(body)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)