"""ModelScope-based tools."""

from typing import Any, Dict, Optional

from app.agent.tools.base import BaseAgentTool, ToolMetadata, get_tool_registry
from app.core.logging import get_logger
from app.llm.modelscope import get_modelscope_provider

logger = get_logger(__name__)


class EmotionAnalysisTool(BaseAgentTool):
    """Tool for emotion analysis using ModelScope."""

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="emotion_analysis",
            description="Analyze the emotional tone of text. Returns emotion scores and dominant emotion.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to analyze for emotions",
                    }
                },
                "required": ["text"],
            },
            category="nlp",
            is_async=True,
        )

    async def execute(self, text: str) -> Dict[str, Any]:
        """Execute emotion analysis."""
        provider = get_modelscope_provider()
        result = await provider.analyze_emotion(text)
        return result


class SpeechRecognitionTool(BaseAgentTool):
    """Tool for speech recognition using ModelScope."""

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="speech_to_text",
            description="Convert audio speech to text using ASR model.",
            parameters={
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "Path to the audio file",
                    }
                },
                "required": ["audio_path"],
            },
            category="audio",
            is_async=True,
        )

    async def execute(self, audio_path: str) -> Dict[str, Any]:
        """Execute speech recognition."""
        provider = get_modelscope_provider()
        result = await provider.speech_to_text(audio_path)
        return result


def register_modelscope_tools() -> None:
    """Register all ModelScope tools."""
    registry = get_tool_registry()

    registry.register(EmotionAnalysisTool())
    logger.info("Registered emotion_analysis tool")

    registry.register(SpeechRecognitionTool())
    logger.info("Registered speech_to_text tool")
