import os
import re
import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

try:
    from funasr import AutoModel
except ImportError:
    AutoModel = None

from app.llm.deepseek import DeepSeek_LLM


class VoiceRAGService:
    """语音输入的 RAG 核心服务类 (使用 SenseVoiceSmall 实现 ASR 和情感分析)"""

    def __init__(self, device: str = "cpu"):
        """初始化语音服务"""
        if AutoModel is None:
            print("警告: 未安装 funasr，语音服务将无法正常工作。")
            self.model = None
        else:
            print("正在加载 SenseVoiceSmall 模型...")
            # SenseVoiceSmall 同时也包含了 ASR 和 情感分析能力
            self.model = AutoModel(
                model="iic/SenseVoiceSmall",
                trust_remote_code=True,
                device=device,
                disable_update=True
            )

        self._initialize_prompts()

    def _initialize_prompts(self):
        """初始化语音相关的提示模板"""

        # 语音回答分析器
        self.voice_answer_analyzer_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，正在与候选人进行语音面试。
        你现在收到了候选人的语音回答文本，以及从语音中分析出的情感特征字典。

        候选人回答内容（ASR转写文本）:
        {asr_text}

        候选人语音情感分析结果:
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

    def _parse_sense_voice_result(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        """解析 SenseVoiceSmall 的输出结果，分离标签和文本"""
        if not res:
            return {"asr_text": "", "emotions": []}
        
        full_text = ""
        emotions = set()
        
        # SenseVoice 的已知非情感标签
        known_non_emotion_tags = {
            'zh', 'en', 'yue', 'ja', 'ko', 'nospeech', 
            'Speech', 'withitn', 'itn', 'woitn',
            'BGM', 'Applause', 'Laughter', 'Cry'
        }
        
        for item in res:
            text_with_tags = item.get("text", "")
            # 提取标签，例如 <|zh|><|HAPPY|><|Speech|><|withitn|>
            tags = re.findall(r'<\|(.*?)\|>', text_with_tags)
            
            for tag in tags:
                # 将全大写且不在非情感列表中的标签视为情感标签
                if tag.isupper() and tag not in known_non_emotion_tags:
                    emotions.add(tag)
                # 可选：将某些特定的事件也视为情感表现
                if tag in ['Applause', 'Laughter', 'Cry']:
                    emotions.add(tag)
            
            # 移除所有标签得到纯文本
            clean_text = re.sub(r'<\|.*?\|>', '', text_with_tags)
            full_text += clean_text
            
        return {
            "asr_text": full_text.strip(),
            "emotions": list(emotions)
        }

    def analyze_emotion(self, audio_path: str) -> list:
        """调用模型进行情感分析 (为了保持向下兼容)"""
        if not self.model: return []
        res = self.model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            ban_emo_unk=False,
            batch_size=64
        )
        parsed = self._parse_sense_voice_result(res)
        return [{"label": emo, "score": 1.0} for emo in parsed["emotions"]]

    def transcribe_audio(self, audio_path: str) -> str:
        """调用模型进行语音转文字 (为了保持向下兼容)"""
        if not self.model: return ""
        res = self.model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            ban_emo_unk=False,
            batch_size=64
        )
        parsed = self._parse_sense_voice_result(res)
        return parsed["asr_text"]

    async def process_voice_input(self, audio_path: str) -> dict:
        """处理完整的语音输入流程 (ASR + 情感分析 + LLM 评价)"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"未找到音频文件: {audio_path}")

        if not self.model:
            return {
                "asr_text": "语音模型未加载",
                "emotion_features": [],
                "llm_analysis": {"feedback_to_candidate": "服务暂不可用"}
            }

        # 1. 调用 SenseVoiceSmall 模型一键完成 ASR 和情感分析
        res = self.model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            ban_emo_unk=False,
            batch_size=64
        )
        
        parsed_result = self._parse_sense_voice_result(res)
        asr_text = parsed_result["asr_text"]
        emotion_result = [{"label": emo, "score": 1.0} for emo in parsed_result["emotions"]]
        
        # 如果没有检测到明显情感，默认设为 NEUTRAL
        if not emotion_result:
            emotion_result = [{"label": "NEUTRAL", "score": 1.0}]

        # 2. 将文字 + 情感字典 全部传给 LLM 进行初步分析
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
