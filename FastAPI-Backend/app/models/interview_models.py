from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

class InterviewStartRequest(BaseModel):
    """开始面试请求"""
    resume: str
    position: str
    collection_name: str

class InterviewAnswerRequest(BaseModel):
    """提交回答请求"""
    session_id: str
    answer: str

class StreamEvent(BaseModel):
    """流式事件"""
    type: str  # question, analyzing, analysis_result, followup, evaluation, complete, error
    data: Dict[str, Any]
    timestamp: str

class QuestionAnalysis(BaseModel):
    """问题分析结果"""
    is_vague: bool
    depth_score: int
    need_followup: bool
    followup_point: Optional[str] = ""
    followup_direction: Optional[str] = ""

class TopicCompleteness(BaseModel):
    """主题完整性"""
    is_sufficient: bool
    missing_points: List[str]
    suggestion: str

class InterviewEvaluation(BaseModel):
    """面试评价"""
    technical_evaluation: str
    communication_evaluation: str
    overall_score: int
    recommendation: str
    strengths: List[str]
    weaknesses: List[str]
    detailed_comment: str

class ConversationRecord(BaseModel):
    """对话记录"""
    round: int
    question: str
    answer: str
    topic: str
    timestamp: datetime