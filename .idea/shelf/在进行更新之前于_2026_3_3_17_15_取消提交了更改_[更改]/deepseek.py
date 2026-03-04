"""DeepSeek LLM provider."""

from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider."""

    def __init__(self) -> None:
        """Initialize DeepSeek provider."""
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.default_max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self.default_temperature = settings.DEEPSEEK_TEMPERATURE
        self.timeout = settings.DEEPSEEK_TIMEOUT

        if not self.api_key:
            logger.warning("DeepSeek API key not configured")

    def get_chat_model(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatOpenAI:
        """Get DeepSeek chat model."""
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
            timeout=self.timeout,
            **kwargs,
        )

    async def chat(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute chat completion."""
        try:
            model = self.get_chat_model(temperature, max_tokens, **kwargs)
            response = await model.ainvoke(messages)

            return {
                "content": response.content,
                "usage": response.usage_metadata if hasattr(response, "usage_metadata") else None,
                "finish_reason": response.response_metadata.get("finish_reason")
                if hasattr(response, "response_metadata")
                else None,
            }
        except Exception as e:
            logger.error("DeepSeek chat error", error=str(e))
            raise

    async def stream_chat(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion."""
        try:
            model = self.get_chat_model(temperature, max_tokens, **kwargs)
            async for chunk in model.astream(messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error("DeepSeek stream error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check DeepSeek API health."""
        try:
            from langchain_core.messages import HumanMessage

            model = self.get_chat_model(max_tokens=1)
            await model.ainvoke([HumanMessage(content="Hi")])
            return True
        except Exception as e:
            logger.error("DeepSeek health check failed", error=str(e))
            return False


# Singleton instance
_deepseek_provider: Optional[DeepSeekProvider] = None


def get_deepseek_provider() -> DeepSeekProvider:
    """Get DeepSeek provider singleton."""
    global _deepseek_provider
    if _deepseek_provider is None:
        _deepseek_provider = DeepSeekProvider()
    return _deepseek_provider
