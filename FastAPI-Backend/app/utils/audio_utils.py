import re
import wave
import os
from datetime import datetime
from pathlib import Path

from pydub import AudioSegment
# 设置 FFmpeg 路径
os.environ["PATH"] += os.pathsep + "C:\\ffmpeg\\bin"

def _ensure_parent_dir(path: str) -> None:
    """Windows 上 dirname 为空时 os.makedirs('') 会触发 [Errno 22] Invalid argument。"""
    d = os.path.dirname(os.path.normpath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def _safe_path_segment(s: str, max_len: int = 80) -> str:
    """去掉 Windows 文件名非法字符，避免 open/makedirs 异常。"""
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(s).strip())
    return (t or "user")[:max_len]


def convert_webm_to_wav(webm_bytes: bytes, output_path: str) -> str:
    """
    将 WebM 音频转换为 WAV 格式

    参数:
        webm_bytes: WebM 格式的音频数据
        output_path: 输出的 WAV 文件路径

    返回:
        保存的 WAV 文件路径
    """
    import tempfile
    import os

    # 创建临时 WebM 文件
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
        temp_webm.write(webm_bytes)
        temp_webm_path = temp_webm.name

    try:
        # 使用 pydub 加载 WebM 并转换为 WAV
        audio = AudioSegment.from_file(temp_webm_path, format='webm')

        # 设置参数：单声道、16kHz、16位
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        audio = audio.set_sample_width(2)  # 16位 = 2字节

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 导出为 WAV
        audio.export(output_path, format='wav')

        return output_path

    finally:
        # 删除临时文件
        os.unlink(temp_webm_path)

def ensure_audio_dirs()->None:
    """
    确保音频文件目录存在
    如果不存在则自动创建
    """
    dirs=[
        "data/audio/uploads", # 上传的音频文件存放处
        "data/audio/temp", # 临时处理文件存放处
    ]
    for dir_path in dirs:
        #exist_ok=True 表示如果目录存在不会报错
        os.makedirs(dir_path, exist_ok=True)


def generate_audio_path(user_id: str) -> str:
    """
       生成音频文件的存储路径 (返回绝对路径以确保兼容性)

       参数:
           user_id: 用户标识，用于区分不同用户的文件

       返回:
           完整的文件绝对路径
    """
    # 获取当前日期时间
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")

    # 构建文件名：清洗 user_id 中的非法字符
    safe_user_id = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in user_id])
    filename = f"{safe_user_id}_{date_str}_{time_str}.wav"

    # 使用 Path 构建绝对路径
    base_dir = Path("data/audio") / date_str
    base_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = (base_dir / filename).absolute()

    return str(filepath)

def save_wav_file(
        audio_bytes: bytes,
        filepath: str,
        channels: int = 1,       #声道数
        sample_width: int = 2,   #采样宽度
        framerate: int = 16000   #采样率
)->str:
    """
        将音频字节数据保存为 WAV 格式文件

        参数:
            audio_bytes: 音频的二进制数据
            filepath: 保存的文件路径
            channels: 声道数，默认单声道
            sample_width: 采样宽度（字节），默认2字节（16位）
            framerate: 采样率（Hz），默认16000Hz

        返回:
            保存后的文件完整路径

        说明:
            - 16kHz 采样率是语音识别模型的标准输入
            - 16位深度提供足够的音质
            - 单声道减少数据量，适合语音
        """
    # 确保目标目录存在
    dir_path = os.path.dirname(filepath)
    os.makedirs(dir_path, exist_ok=True)

    # 使用 wave 模块写入 WAV 文件
    # 'wb' 表示以二进制写入模式打开
    with wave.open(filepath, 'wb') as wav_file:
        # 设置声道数
        wav_file.setnchannels(channels)

        # 设置采样宽度（字节数）
        # 2字节 = 16位，取值范围 -32768 到 32767
        wav_file.setsampwidth(sample_width)

        # 设置采样率（每秒采样次数）
        # 16000Hz = 每秒16000个采样点
        wav_file.setframerate(framerate)

        # 写入音频数据
        wav_file.writeframes(audio_bytes)

    # 返回保存的文件路径
    return filepath


def validate_audio_file(filepath:str)->bool:
    """
        验证音频文件是否有效

        参数:
            filepath: 音频文件路径

        返回:
            True 表示文件有效，False 表示无效

        检查项:
            - 文件是否存在
            - 文件是否能被 wave 模块正常打开
        """
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return False

    try:
        # 尝试打开文件
        with wave.open(filepath, 'rb') as wav_file:
            # 获取音频参数，如果能获取说明文件有效
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            n_frames = wav_file.getnframes()

            # 参数合理性检查
            if channels <= 0 or sample_width <= 0 or framerate <= 0:
                return False

            return True

    except wave.Error:
        # wave 模块报错，说明不是有效的 WAV 文件
        return False
    except Exception:
        # 其他异常
        return False


def get_audio_duration(filepath: str) -> float:
    """
    获取音频文件的时长（秒）

    参数:
        filepath: 音频文件路径

    返回:
        音频时长，单位秒

    计算方式:
        时长 = 总帧数 / 采样率
    """
    try:
        with wave.open(filepath, 'rb') as wav_file:
            # 获取总帧数（采样点总数）
            n_frames = wav_file.getnframes()

            # 获取采样率（每秒采样点数）
            framerate = wav_file.getframerate()

            # 计算时长
            duration = n_frames / framerate

            return duration

    except Exception:
        # 出错返回 0
        return 0.0


def get_audio_info(filepath: str) -> dict:
    """
    获取音频文件的详细信息

    参数:
        filepath: 音频文件路径

    返回:
        包含音频信息的字典
    """
    try:
        with wave.open(filepath, 'rb') as wav_file:
            # 获取各项参数
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            n_frames = wav_file.getnframes()

            # 计算时长
            duration = n_frames / framerate

            # 计算文件大小
            file_size = os.path.getsize(filepath)

            return {
                "filepath": filepath,  # 文件路径
                "channels": channels,  # 声道数
                "sample_width": sample_width,  # 采样宽度（字节）
                "framerate": framerate,  # 采样率（Hz）
                "n_frames": n_frames,  # 总帧数
                "duration": duration,  # 时长（秒）
                "file_size": file_size,  # 文件大小（字节）
                "file_size_mb": round(file_size / 1024 / 1024, 2)  # 文件大小（MB）
            }

    except Exception as e:
        return {
            "filepath": filepath,
            "error": str(e)
        }
