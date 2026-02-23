"""Base LLM interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def get_chat_model(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """Get the chat model instance."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a chat completion."""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        pass
