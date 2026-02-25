"""
语音相关 API 接口
提供音频上传、语音识别等功能
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.services.voice_service import get_voice_service

# 创建路由
# prefix="/voice" 会在主应用中添加前缀
# tags=["Voice"] 用于 API 文档分类
router = APIRouter(prefix="/voice", tags=["Voice"])

# 获取日志记录器
logger = get_logger(__name__)

# 允许的音频文件类型（MIME 类型）
ALLOWED_AUDIO_TYPES = [
    "audio/wav",  # WAV 格式
    "audio/x-wav",  # WAV 格式（另一种表示）
    "audio/mpeg",  # MP3 格式
    "audio/mp3",  # MP3 格式（另一种表示）
    "audio/webm",  # WebM 格式（浏览器录音常用）
    "audio/ogg",  # OGG 格式
    "audio/mp4",  # M4A 格式
    "audio/x-m4a",  # M4A 格式（另一种表示）
]

# 最大文件大小：50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload")
async def upload_and_recognize_audio(
        file: UploadFile = File(..., description="音频文件"),
        user_id: str = Form(default="anonymous", description="用户ID"),
        engine: str = Form(default="auto", description="识别引擎: auto/google/modelscope")
):
    """
    上传音频文件并识别

    接收前端上传的音频文件，保存为 WAV 格式后进行语音识别

    参数:
        file: 音频文件（支持 wav, mp3, m4a, webm 等格式）
        user_id: 用户标识，用于区分不同用户的文件
        engine: 识别引擎选择
            - auto: 自动选择（推荐）
            - google: Google 语音识别
            - modelscope: ModelScope 语音识别（国内可用）

    返回:
        {
            "success": true,
            "text": "识别出的文字内容",
            "audio_path": "data/audio/20250223/user_20250223_203045.wav",
            "duration": 15.5,
            "file_size": 102400,
            "file_size_mb": 0.1,
            "engine": "google"
        }

    错误返回:
        {
            "success": false,
            "error": "错误信息"
        }
    """
    logger.info(
        "Voice upload request",
        filename=file.filename,
        content_type=file.content_type,
        user_id=user_id,
        engine=engine
    )

    # 步骤1：检查文件类型
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        logger.warning("Invalid file type", content_type=file.content_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的音频格式: {file.content_type}。请上传 WAV, MP3, M4A 等格式"
        )

    # 步骤2：读取文件内容
    try:
        # await 因为读取文件是异步操作
        audio_bytes = await file.read()

        # 检查文件大小
        if len(audio_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件过大，最大支持 {MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        # 检查文件是否为空
        if len(audio_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="音频文件为空"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to read file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取文件失败: {str(e)}"
        )

    # 步骤3：调用服务处理
    try:
        # 获取语音服务实例
        voice_service = get_voice_service()

        # 执行上传+识别
        result = await voice_service.upload_and_recognize(
            audio_bytes=audio_bytes,
            user_id=user_id,
            original_filename=file.filename,
            engine=engine
        )

        # 根据处理结果返回相应状态码
        if result["success"]:
            return result
        else:
            # 处理失败但已捕获错误
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=result
            )

    except Exception as e:
        logger.error("Voice processing error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语音处理失败: {str(e)}"
        )


@router.post("/upload-only")
async def upload_audio_only(
        file: UploadFile = File(..., description="音频文件"),
        user_id: str = Form(default="anonymous", description="用户ID")
):
    """
    仅上传音频文件，不进行识别

    适用于先保存文件，稍后识别的场景

    参数:
        file: 音频文件
        user_id: 用户标识

    返回:
        {
            "success": true,
            "audio_path": "保存的文件路径",
            "duration": 15.5,
            "file_size": 102400
        }
    """
    logger.info("Audio upload-only request", filename=file.filename, user_id=user_id)

    # 检查文件类型
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的音频格式: {file.content_type}"
        )

    try:
        # 读取文件
        audio_bytes = await file.read()

        # 获取服务
        voice_service = get_voice_service()

        # 仅保存，不识别
        result = await voice_service.process_uploaded_audio(
            audio_bytes=audio_bytes,
            user_id=user_id,
            original_filename=file.filename
        )

        if result["success"]:
            return result
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=result
            )

    except Exception as e:
        logger.error("Upload error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )


@router.post("/recognize")
async def recognize_saved_audio(
        audio_path: str,
        engine: str = "auto"
):
    """
    识别服务器上已存在的音频文件

    参数:
        audio_path: 音频文件在服务器的路径
        engine: 识别引擎

    返回:
        识别结果
    """
    logger.info("Recognize saved audio", path=audio_path, engine=engine)

    # 安全检查：确保路径在允许的目录内
    # 防止路径遍历攻击（如 ../../../etc/passwd）
    if not audio_path.startswith("data/audio/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="非法的文件路径"
        )

    # 检查文件是否存在
    import os
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="音频文件不存在"
        )

    try:
        # 获取服务
        voice_service = get_voice_service()

        # 执行识别
        result = await voice_service.recognize_audio(audio_path, engine)

        if result["success"]:
            return result
        else:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=result
            )

    except Exception as e:
        logger.error("Recognition error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"识别失败: {str(e)}"
        )


@router.get("/engines")
async def list_engines():
    """
    获取可用的语音识别引擎列表

    返回:
        {
            "engines": [
                {"name": "auto", "description": "自动选择"},
                {"name": "google", "description": "Google 语音识别"},
                {"name": "modelscope", "description": "ModelScope 语音识别"}
            ]
        }
    """
    return {
        "engines": [
            {
                "name": "auto",
                "description": "自动选择（推荐）",
                "note": "优先尝试 Google，失败则使用 ModelScope"
            },
            {
                "name": "google",
                "description": "Google Speech Recognition",
                "note": "准确率高，但需要能访问 Google 服务"
            },
            {
                "name": "modelscope",
                "description": "ModelScope 阿里达摩院",
                "note": "国内可用，无需翻墙"
            }
        ]
    }