"""
语音服务模块
提供音频处理、语音识别等核心功能
"""

import os
import uuid
from typing import Optional

import speech_recognition as sr

from app.core.logging import get_logger
from app.llm.modelscope import get_modelscope_provider, get_emotion_emo2vec
from app.utils.audio_utils import (
    generate_audio_path,
    save_wav_file,
    validate_audio_file,
    get_audio_duration,
    get_audio_info,
)

# 获取日志记录器
logger = get_logger(__name__)


class VoiceService:
    """
    语音服务类

    负责处理音频上传、保存、识别等完整流程
    """

    def __init__(self) -> None:
        """
        初始化语音服务

        创建语音识别器实例
        """
        # 创建 SpeechRecognition 识别器
        # 这是 Google  speech recognition 的封装
        self.recognizer = sr.Recognizer()

        # 获取 ModelScope 提供商（备用识别方案）
        self.modelscope = get_modelscope_provider()

        logger.info("VoiceService initialized")

    async def process_uploaded_audio(
            self,
            audio_bytes: bytes,
            user_id: str,
            original_filename: Optional[str] = None
    ) -> dict:
        """
        处理上传的音频文件（支持 WebM 自动转 WAV）
        """
        logger.info(
            "Processing uploaded audio",
            user_id=user_id,
            original_filename=original_filename,
            size_bytes=len(audio_bytes)
        )

        try:
            # 生成存储路径
            audio_path = generate_audio_path(user_id)

            # 判断文件类型并转换
            # 前端上传的是 webm 格式（MediaRecorder 默认格式）
            if original_filename and (
                original_filename.endswith('.webm') or 
                original_filename.endswith('.wav')  # 前端可能伪装成 wav 但实际是 webm
            ):
                # 尝试用 pydub 自动检测格式并转换
                try:
                    from app.utils.audio_utils import convert_webm_to_wav
                    saved_path = convert_webm_to_wav(audio_bytes, audio_path)
                    logger.info("Converted audio to WAV", path=saved_path, source=original_filename)
                except Exception as convert_err:
                    logger.warning("Auto-convert failed, trying direct save", error=str(convert_err))
                    # 如果转换失败，直接保存原始字节
                    saved_path = save_wav_file(
                        audio_bytes=audio_bytes,
                        filepath=audio_path,
                        channels=1,
                        sample_width=2,
                        framerate=16000
                    )
            else:
                # 直接保存为 WAV（假设已经是正确格式）
                saved_path = save_wav_file(
                    audio_bytes=audio_bytes,
                    filepath=audio_path,
                    channels=1,
                    sample_width=2,
                    framerate=16000
                )

            # 验证文件
            if not validate_audio_file(saved_path):
                os.remove(saved_path)
                return {
                    "success": False,
                    "error": "音频文件验证失败，可能已损坏"
                }

            # 获取音频信息
            audio_info = get_audio_info(saved_path)

            logger.info(
                "Audio saved successfully",
                path=saved_path,
                duration=audio_info["duration"]
            )

            return {
                "success": True,
                "audio_path": saved_path,
                "duration": audio_info["duration"],
                "file_size": audio_info["file_size"],
                "file_size_mb": audio_info["file_size_mb"]
            }

        except Exception as e:
            logger.error("Failed to process audio", error=str(e))
            return {
                "success": False,
                "error": f"处理音频失败: {str(e)}"
            }

    async def recognize_with_speechrecognition(
            self,
            audio_path: str
    ) -> dict:
        """
        使用 SpeechRecognition 进行语音识别（Google 接口）

        注意：需要能访问 Google 服务，国内可能需要代理

        参数:
            audio_path: WAV 音频文件路径

        返回:
            识别结果字典
        """
        logger.info("Recognizing with SpeechRecognition", path=audio_path)

        try:
            # 使用 AudioFile 加载音频文件
            with sr.AudioFile(audio_path) as source:
                # record() 读取整个音频文件
                audio_data = self.recognizer.record(source)

            # 使用 Google 语音识别（中文）
            # language='zh-CN' 表示识别中文
            text = self.recognizer.recognize_google(
                audio_data,
                language='zh-CN'
            )

            logger.info("Recognition successful", text=text[:50])

            return {
                "success": True,
                "text": text,
                "engine": "google",
                "language": "zh-CN"
            }

        except sr.UnknownValueError:
            # 音频无法识别
            logger.warning("Could not understand audio")
            return {
                "success": False,
                "error": "无法识别音频内容，请检查音频质量",
                "text": ""
            }

        except sr.RequestError as e:
            # 请求失败（网络问题）
            logger.error("Recognition service error", error=str(e))
            return {
                "success": False,
                "error": f"识别服务不可用: {str(e)}",
                "text": ""
            }

    async def recognize_with_modelscope(
            self,
            audio_path: str
    ) -> dict:
        """
        使用 ModelScope 进行语音识别（国内可用）

        这是备用方案，不依赖 Google 服务

        参数:
            audio_path: WAV 音频文件路径

        返回:
            识别结果字典
        """
        logger.info("Recognizing with ModelScope", path=audio_path)

        try:
            # 调用 ModelScope 的语音识别
            result = await self.modelscope.speech_to_text(audio_path)

            text = result.get("text", "")
            confidence = result.get("confidence", 0.0)

            logger.info(
                "ModelScope recognition successful",
                text=text[:50],
                confidence=confidence
            )

            return {
                "success": True,
                "text": text,
                "confidence": confidence,
                "engine": "modelscope",
                "language": "zh-CN"
            }

        except Exception as e:
            logger.error("ModelScope recognition failed", error=str(e))
            return {
                "success": False,
                "error": f"ModelScope 识别失败: {str(e)}",
                "text": ""
            }

    async def recognize_audio(
            self,
            audio_path: str,
            engine: str = "auto"
    ) -> dict:
        """
        语音识别主方法

        支持多引擎自动选择

        参数:
            audio_path: 音频文件路径
            engine: 识别引擎，可选 "auto"(自动), "google", "modelscope"

        返回:
            识别结果
        """
        # 先验证文件
        if not validate_audio_file(audio_path):
            return {
                "success": False,
                "error": "音频文件无效",
                "text": ""
            }

        # 根据引擎选择识别方式
        if engine == "google":
            # 强制使用 Google
            return await self.recognize_with_speechrecognition(audio_path)

        elif engine == "modelscope":
            # 强制使用 ModelScope
            return await self.recognize_with_modelscope(audio_path)

        else:  # auto
            # 自动选择：先尝试 Google，失败则用 ModelScope
            result = await self.recognize_with_speechrecognition(audio_path)

            if result["success"]:
                return result

            # Google 失败，尝试 ModelScope
            logger.info("Google failed, trying ModelScope")
            return await self.recognize_with_modelscope(audio_path)

    async def analyze_emotion(
            self,
            audio_path: str
    ) -> dict:
        """
        使用 emotion2vec 分析音频情感

        参数:
            audio_path: WAV 音频文件路径

        返回:
            完整情感分析结果（包含所有情感分数）
        """
        logger.info("Analyzing emotion with emotion2vec", path=audio_path)

        try:
            # 调用 modelscope.py 中的 get_emotion_emo2vec 函数
            # 返回完整结果：dominant_emotion, confidence, all_emotions
            emotion_result = get_emotion_emo2vec(audio_path)

            if emotion_result.get("success"):
                logger.info(
                    "Emotion analysis successful",
                    dominant_emotion=emotion_result["dominant_emotion"],
                    confidence=emotion_result["confidence"]
                )
            
            return emotion_result  # 直接返回完整结果

        except Exception as e:
            logger.error("Emotion analysis failed", error=str(e))
            return {
                "success": False,
                "error": f"情感分析失败: {str(e)}",
                "dominant_emotion": "unknown",
                "confidence": 0.0,
                "all_emotions": {}
            }

    async def upload_and_recognize(
            self,
            audio_bytes: bytes,
            user_id: str,
            original_filename: Optional[str] = None,
            engine: str = "auto"
    ) -> dict:
        """
        完整流程：上传 + 情感识别

        一站式完成音频处理和情感分析

        参数:
            audio_bytes: 音频二进制数据
            user_id: 用户标识
            original_filename: 原始文件名
            engine: 保留参数，当前版本使用 emotion2vec

        返回:
            完整结果，包含文件信息和情感识别结果
        """
        # 步骤1：保存音频文件
        save_result = await self.process_uploaded_audio(
            audio_bytes=audio_bytes,
            user_id=user_id,
            original_filename=original_filename
        )

        # 检查保存是否成功
        if not save_result["success"]:
            return save_result

        # 步骤2：情感识别（使用 emotion2vec）
        audio_path = save_result["audio_path"]
        emotion_result = await self.analyze_emotion(audio_path)

        # 合并结果返回（包含完整情感分析数据）
        return {
            "success": emotion_result["success"],
            "dominant_emotion": emotion_result.get("dominant_emotion", "unknown"),
            "confidence": emotion_result.get("confidence", 0.0),
            "all_emotions": emotion_result.get("all_emotions", {}),
            "audio_path": audio_path,
            "duration": save_result["duration"],
            "file_size": save_result["file_size"],
            "file_size_mb": save_result["file_size_mb"],
            "engine": "emotion2vec",
            "error": emotion_result.get("error")
        }


# 单例模式，全局复用
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """
    获取 VoiceService 单例实例

    使用单例避免重复创建识别器
    """
    global _voice_service

    if _voice_service is None:
        _voice_service = VoiceService()

    return _voice_service