"""Embedding models configuration."""

from functools import lru_cache
from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider:
    """Provider for embedding models."""

    def __init__(self) -> None:
        """Initialize embedding provider."""
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    def get_embeddings(self) -> Embeddings:
        """Get embedding model instance."""
        if "text-embedding" in self.model:
            # OpenAI embeddings (compatible with DeepSeek)
            return OpenAIEmbeddings(
                model=self.model,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            )
        else:
            # Default to OpenAI embeddings
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
            )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Get cached embedding provider."""
    return EmbeddingProvider()


def get_embeddings() -> Embeddings:
    """Get embeddings instance."""
    return get_embedding_provider().get_embeddings()
