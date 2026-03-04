"""LLM Router for intelligent model selection."""

from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.llm.deepseek import get_deepseek_provider
from app.llm.modelscope import get_modelscope_provider

logger = get_logger(__name__)


class TaskType(str, Enum):
    """Task types for routing."""

    CHAT = "chat"
    CODE = "code"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    EMOTION = "emotion"
    SPEECH = "speech"
    VISION = "vision"


class ModelRouter:
    """Router for selecting appropriate models."""

    def __init__(self) -> None:
        """Initialize model router."""
        self.deepseek = get_deepseek_provider()
        self.modelscope = get_modelscope_provider()

    async def route_task(
        self,
        task_type: TaskType,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Route task to appropriate model."""
        logger.info("Routing task", task_type=task_type)

        if task_type == TaskType.EMOTION:
            return await self.modelscope.analyze_emotion(str(input_data))

        elif task_type == TaskType.SPEECH:
            if isinstance(input_data, str):
                return await self.modelscope.speech_to_text(input_data)
            return {"error": "Invalid input for speech task"}

        elif task_type in [TaskType.CHAT, TaskType.CODE, TaskType.ANALYSIS, TaskType.CREATIVE]:
            # Use DeepSeek for general LLM tasks
            from langchain_core.messages import HumanMessage, SystemMessage

            messages: List[Any] = []
            if context and "system_prompt" in context:
                messages.append(SystemMessage(content=context["system_prompt"]))
            messages.append(HumanMessage(content=str(input_data)))

            response = await self.deepseek.chat(
                messages,
                temperature=context.get("temperature") if context else None,
                max_tokens=context.get("max_tokens") if context else None,
            )
            return response

        else:
            return {"error": f"Unsupported task type: {task_type}"}

    async def enrich_with_auxiliary(
        self,
        text: str,
        include_emotion: bool = True,
    ) -> Dict[str, Any]:
        """Enrich input with auxiliary model outputs."""
        enrichment: Dict[str, Any] = {"original_text": text}

        if include_emotion:
            emotion_result = await self.modelscope.analyze_emotion(text)
            enrichment["emotion"] = emotion_result

        return enrichment


# Singleton instance
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get model router singleton."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
