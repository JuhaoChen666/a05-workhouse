"""Application lifecycle events."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    configure_logging()
    logger.info(
        "Application starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )

    # Initialize infrastructure
    await _init_infrastructure()

    yield

    # Shutdown
    logger.info("Application shutting down")
    await _shutdown_infrastructure()


async def _init_infrastructure() -> None:
    """Initialize infrastructure components."""
    try:
        # Initialize vector store
        from app.infrastructure.vector_store.chroma_client import init_chroma
        await init_chroma()
        logger.info("Vector store initialized")

        # Initialize cache
        from app.infrastructure.cache.redis_client import init_redis
        await init_redis()
        logger.info("Cache initialized")

    except Exception as e:
        logger.warning("Infrastructure initialization warning", error=str(e))


async def _shutdown_infrastructure() -> None:
    """Shutdown infrastructure components."""
    try:
        # Close cache connections
        from app.infrastructure.cache.redis_client import close_redis
        await close_redis()
        logger.info("Cache connections closed")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))
