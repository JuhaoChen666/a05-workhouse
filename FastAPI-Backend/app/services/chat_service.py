"""Chat service."""

import uuid
from typing import AsyncIterator, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from app.core.logging import get_logger
from app.llm.deepseek import get_deepseek_provider
from app.llm.router import get_model_router
from app.models.schemas.chat import ChatMessage, ChatRequest, ChatResponse, MessageRole

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat operations."""

    def __init__(self) -> None:
        """Initialize chat service."""
        self.llm_provider = get_deepseek_provider()
        self.model_router = get_model_router()

    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """Process a chat request."""
        session_id = request.session_id or str(uuid.uuid4())

        logger.info(
            "Processing chat request",
            session_id=session_id,
            message_length=len(request.message),
        )

        # Build messages
        messages = self._build_messages(request)

        # Get response from LLM
        response = await self.llm_provider.chat(
            messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Create chat message
        chat_message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=response["content"],
            metadata={"finish_reason": response.get("finish_reason")},
        )

        return ChatResponse(
            session_id=session_id,
            message=chat_message,
            usage=response.get("usage"),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[str]:
        """Stream chat response."""
        session_id = request.session_id or str(uuid.uuid4())

        logger.info(
            "Processing streaming chat request",
            session_id=session_id,
        )

        # Build messages
        messages = self._build_messages(request)

        # Stream response
        async for chunk in self.llm_provider.stream_chat(
            messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            yield chunk

    def _build_messages(self, request: ChatRequest) -> List:
        """Build message list for LLM."""
        from langchain_core.messages import HumanMessage

        messages = []

        # Add context messages if provided
        if request.context:
            for msg in request.context:
                if msg.role == MessageRole.USER:
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == MessageRole.ASSISTANT:
                    messages.append(AIMessage(content=msg.content))

        # Add current message
        messages.append(HumanMessage(content=request.message))

        return messages

    async def enrich_with_emotion(
        self,
        text: str,
    ) -> Dict:
        """Enrich text with emotion analysis."""
        return await self.model_router.enrich_with_auxiliary(text)


# Singleton
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get chat service singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
