"""Chat API endpoints."""

from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas.chat import ChatRequest, ChatResponse
from app.models.schemas.common import DataResponse
from app.services.chat_service import get_chat_service

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/completions", response_model=DataResponse[ChatResponse])
async def chat_completion(request: ChatRequest) -> DataResponse[ChatResponse]:
    """Create a chat completion."""
    try:
        service = get_chat_service()
        response = await service.chat(request)
        return DataResponse(data=response)
    except Exception as e:
        logger.error("Chat completion error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat completion failed: {str(e)}",
        )


@router.post("/completions/stream")
async def chat_completion_stream(request: ChatRequest) -> StreamingResponse:
    """Stream a chat completion."""

    async def event_generator() -> AsyncIterator[str]:
        service = get_chat_service()
        try:
            async for chunk in service.stream_chat(request):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Stream error", error=str(e))
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.post("/analyze-emotion")
async def analyze_emotion(text: str) -> DataResponse[dict]:
    """Analyze emotion of text using ModelScope."""
    try:
        service = get_chat_service()
        result = await service.enrich_with_emotion(text)
        return DataResponse(data=result)
    except Exception as e:
        logger.error("Emotion analysis error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emotion analysis failed: {str(e)}",
        )
