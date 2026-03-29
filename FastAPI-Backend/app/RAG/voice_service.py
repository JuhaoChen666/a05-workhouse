import os
import re
import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

try:
    from faster_whisper import WhisperModel
except ImportError:
    pass

try:
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
except ImportError:
    pass

from app.llm.deepseek import DeepSeek_LLM


class VoiceRAGService:
    """语音输入的 RAG 核心服务类"""

    def __init__(self, model_size: str = "medium", device: str = "cpu", compute_type: str = "int8"):
        """初始化语音服务"""
        # 初始化情感分析模型 (Emotion2Vec)
        print("正在加载 emotion2vec_plus_large 模型...")
        self.emotion_pipeline = pipeline(
            task=Tasks.emotion_recognition,
            model="iic/emotion2vec_plus_large"
        )
        
        # 初始化语音识别模型 (Faster-Whisper)
        print(f"正在加载 Whisper {model_size} 模型...")
        self.asr_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        
        self._initialize_prompts()

    def _initialize_prompts(self):
        """初始化语音相关的提示模板"""
        
        # 语音回答分析器
        self.voice_answer_analyzer_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，正在与候选人进行语音面试。
        你现在收到了候选人的语音回答文本，以及从语音中分析出的情感特征字典。

        候选人回答内容（ASR转写文本）: 
        {asr_text}

        候选人语音情感分析结果（Emotion2Vec提供的情感得分字典）: 
        {emotion_dict}

        请根据候选人的回答内容，结合其在回答时的情感状态（如紧张、自信、犹豫等），给出你的综合判断，并决定下一步是深入追问还是进入下一个话题。

        要求：
        1. 评价内容要结合候选人的回答质量和情感特征。
        2. 如果候选人展现出紧张或不确定，可以给予适当的安抚或引导。
        3. 给出针对该回答的专业且兼顾情感的反馈直接回复。

        输出JSON格式：
        {{
            "emotion_analysis": "对情感状态的分析",
            "content_evaluation": "对回答内容的评价",
            "feedback_to_candidate": "给候选人的直接回复（专业且兼顾情感的反馈）"
        }}
        """)

    def analyze_emotion(self, audio_path: str) -> list:
        """调用 Emotion2Vec 进行情感分析"""
        print(f"开始进行情感分析: {audio_path}")
        rec_result = self.emotion_pipeline(audio_path, granularity="utterance")
        return rec_result

    def transcribe_audio(self, audio_path: str) -> str:
        """调用 Faster-Whisper 进行语音转文字"""
        print(f"开始进行语音识别: {audio_path}")
        segments, info = self.asr_model.transcribe(audio_path, beam_size=5, language="zh")
        
        full_text = ""
        for segment in segments:
            full_text += segment.text + " "
            
        return full_text.strip()

    def _convert_to_json_serializable(self, obj):
        """将对象转换为 JSON 可序列化的格式 (处理 numpy.ndarray 等)"""
        try:
            import numpy as np
        except ImportError:
            return obj

        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(v) for v in obj]
        elif isinstance(obj, (np.int64, np.int32, np.int16)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        return obj

    async def process_voice_input(self, audio_path: str) -> dict:
        """处理完整的语音输入流程"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"未找到音频文件: {audio_path}")
            
        # 1. 调用emotion2vec模型做情感分析
        raw_emotion_result = self.analyze_emotion(audio_path)
        # 确保情感结果是 JSON 可序列化的 (处理可能存在的 ndarray)
        emotion_result = self._convert_to_json_serializable(raw_emotion_result)
        
        # 2. 调用ASR来把wav转成文字
        asr_text = self.transcribe_audio(audio_path)
        
        # 3. 将文字 + 情感字典 全部传给同用的LLM
        chain = self.voice_answer_analyzer_prompt | DeepSeek_LLM | StrOutputParser()
        result = await chain.ainvoke({
            "asr_text": asr_text,
            "emotion_dict": json.dumps(emotion_result, ensure_ascii=False)
        })
        
        # 解析返回的 JSON
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "emotion_analysis": "无法分析",
                    "content_evaluation": "无法评价",
                    "feedback_to_candidate": result
                }
        except Exception:
            analysis = {
                "emotion_analysis": "无法解析返回结果",
                "content_evaluation": "无法解析返回结果",
                "feedback_to_candidate": result
            }
            
        return {
            "asr_text": asr_text,
            "emotion_features": emotion_result,
            "llm_analysis": analysis
        }
