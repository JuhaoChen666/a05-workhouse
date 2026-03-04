"""System API endpoints."""

from datetime import datetime

from fastapi import APIRouter, status

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.deepseek import get_deepseek_provider
from app.llm.modelscope import get_modelscope_provider
from app.models.schemas.common import DataResponse, HealthCheck

logger = get_logger(__name__)
router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health", response_model=DataResponse[HealthCheck])
async def health_check() -> DataResponse[HealthCheck]:
    """Check system health."""
    components = {}

    # Check DeepSeek
    try:
        deepseek = get_deepseek_provider()
        deepseek_healthy = await deepseek.health_check()
        components["deepseek"] = "healthy" if deepseek_healthy else "unhealthy"
    except Exception as e:
        logger.warning("DeepSeek health check failed", error=str(e))
        components["deepseek"] = "unhealthy"

    # Check ModelScope (just check if provider is initialized)
    try:
        get_modelscope_provider()
        components["modelscope"] = "healthy"
    except Exception as e:
        logger.warning("ModelScope health check failed", error=str(e))
        components["modelscope"] = "unhealthy"

    # Overall status
    overall_status = "healthy" if all(
        v == "healthy" for v in components.values()
    ) else "degraded"

    health = HealthCheck(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        components=components,
    )

    return DataResponse(data=health)


@router.get("/info")
async def system_info() -> DataResponse[dict]:
    """Get system information."""
    info = {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "api_prefix": settings.API_V1_PREFIX,
        "models": {
            "primary": settings.DEEPSEEK_MODEL,
            "emotion": settings.EMOTION_MODEL,
            "asr": settings.ASR_MODEL,
            "embedding": settings.EMBEDDING_MODEL,
        },
        "features": {
            "chat": True,
            "agent": True,
            "streaming": True,
            "emotion_analysis": True,
            "speech_recognition": True,
        },
    }
    return DataResponse(data=info)


@router.get("/config")
async def get_config() -> DataResponse[dict]:
    """Get public configuration (sensitive info redacted)."""
    config = {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "models": {
            "primary": settings.DEEPSEEK_MODEL,
            "emotion": settings.EMOTION_MODEL,
            "asr": settings.ASR_MODEL,
        },
        "features": {
            "streaming": True,
            "tools": True,
        },
    }
    return DataResponse(data=config)
