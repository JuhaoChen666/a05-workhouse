"""ModelScope model provider for auxiliary tasks."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelScopeProvider:
    """ModelScope provider for auxiliary models."""

    def __init__(self) -> None:
        """Initialize ModelScope provider."""
        self.cache_dir = settings.MODELSCOPE_CACHE_DIR
        self.device = settings.MODELSCOPE_DEVICE
        self._models: Dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _load_model(self, model_id: str, task: Optional[str] = None) -> Any:
        """Load a ModelScope model."""
        try:
            from modelscope.pipelines import pipeline
            from modelscope.utils.constant import Tasks

            if model_id not in self._models:
                logger.info("Loading ModelScope model", model_id=model_id)
                if task:
                    self._models[model_id] = pipeline(
                        task=task,
                        model=model_id,
                        device=self.device,
                        model_revision="master",
                    )
                else:
                    self._models[model_id] = pipeline(
                        model=model_id,
                        device=self.device,
                        model_revision="master",
                    )
            return self._models[model_id]
        except Exception as e:
            logger.error("Failed to load ModelScope model", model_id=model_id, error=str(e))
            raise

    async def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """Analyze emotion of text."""
        try:
            model_id = settings.EMOTION_MODEL
            model = self._load_model(model_id, "text-classification")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, model, text)

            return {
                "text": text,
                "emotions": result,
                "dominant_emotion": max(result, key=lambda x: x.get("score", 0)).get("label")
                if result
                else None,
            }
        except Exception as e:
            logger.error("Emotion analysis error", error=str(e))
            return {"text": text, "emotions": [], "dominant_emotion": None, "error": str(e)}

    async def speech_to_text(self, audio_path: str) -> Dict[str, Any]:
        """Convert speech to text."""
        try:
            model_id = settings.ASR_MODEL
            model = self._load_model(model_id, "auto-speech-recognition")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, model, audio_path)

            return {
                "audio_path": audio_path,
                "text": result.get("text", ""),
                "confidence": result.get("confidence", 0.0),
            }
        except Exception as e:
            logger.error("Speech recognition error", error=str(e))
            return {"audio_path": audio_path, "text": "", "confidence": 0.0, "error": str(e)}

    async def text_to_speech(self, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Convert text to speech."""
        # TODO: Implement TTS using ModelScope
        logger.warning("TTS not yet implemented")
        return {"text": text, "output_path": output_path, "status": "not_implemented"}

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_id": model_id,
            "cached": model_id in self._models,
            "cache_dir": self.cache_dir,
        }

    def clear_cache(self) -> None:
        """Clear loaded models from memory."""
        self._models.clear()
        logger.info("ModelScope cache cleared")


# Singleton instance
_modelscope_provider: Optional[ModelScopeProvider] = None


def get_modelscope_provider() -> ModelScopeProvider:
    """Get ModelScope provider singleton."""
    global _modelscope_provider
    if _modelscope_provider is None:
        _modelscope_provider = ModelScopeProvider()
    return _modelscope_provider


from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import numpy as np
def get_emotion_emo2vec(audio_path: str) -> dict:
    """
    使用 emotion2vec 分析音频文件的情感状态

    参数:
        audio_path: WAV音频文件的完整路径（如 "data/audio/20250223/user_xxx.wav"）

    返回:
        包含完整情感分析结果的字典:
        {
            "dominant_emotion": "生气/angry",  # 主导情感
            "confidence": 0.9732,               # 置信度
            "all_emotions": {                   # 所有情感分数
                "生气/angry": 0.9732,
                "厌恶/disgusted": 0.0000,
                "恐惧/fearful": 0.0000,
                ...
            }
        }
    """
    inference_pipeline = pipeline(
        task=Tasks.emotion_recognition,
        model="iic/emotion2vec_plus_large"
    )

    result = inference_pipeline(
        audio_path,
        granularity="utterance",
        extract_embedding=False
    )

    # 解析结果
    if result and len(result) > 0:
        item = result[0]
        labels = item['labels']
        scores = item['scores']
        
        # 转换为Python原生类型（避免numpy类型导致JSON序列化问题）
        labels = [str(label) for label in labels]
        scores = [float(score) for score in scores]

        # 找出得分最高的情感
        max_score_idx = int(np.argmax(scores))
        dominant_emotion = labels[max_score_idx]
        confidence = float(scores[max_score_idx])

        # 构建所有情感的字典
        all_emotions = {label: score for label, score in zip(labels, scores)}

        # 打印详细结果（调试用）
        print(f"\n🎯 主导情感: {dominant_emotion}")
        print(f"📊 置信度: {confidence:.2%}")
        print(f"\n所有情感得分:")
        print(audio_path)
        for label, score in zip(labels, scores):
            print(f"  {label}: {score:.4f}")

        # 返回完整结果
        return {
            "success": True,
            "dominant_emotion": dominant_emotion,
            "confidence": float(confidence),
            "all_emotions": all_emotions,
            "audio_path": audio_path
        }
    else:
        return {
            "success": False,
            "error": "情感识别失败，无返回结果",
            "audio_path": audio_path
        }