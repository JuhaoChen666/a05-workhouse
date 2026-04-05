from typing import AsyncGenerator
from app.RAG.RAG_full import RAGService
from app.RAG.session_service import SessionService
from app.RAG.voice_service import VoiceRAGService
from app.utils.audio_utils import generate_audio_path, save_wav_file
from datetime import datetime
from app.models.interview_models import StreamEvent


class InterviewService:
    """面试业务服务"""

    def __init__(self):
        self.rag_service = RAGService()
        self.session_service = SessionService(self.rag_service)
        self.voice_rag_service = VoiceRAGService()

    def initialize_database(self, collection_name: str):
        """初始化数据库"""
        return self.rag_service.initialize_database(collection_name)

    async def start_interview(self, resume: str, position: str, collection_name: str, user_id: int = None) -> dict:
        """开始面试"""
        # 初始化数据库
        db_info = self.initialize_database(collection_name)

        # 创建会话
        session_id = await self.session_service.create_session(resume, position, user_id)

        # 需要在异步环境中初始化，这里返回session_id，让路由层处理
        return {
            "session_id": session_id,
            "db_info": db_info
        }

    async def initialize_session_question(self, session_id: str) -> str:
        """初始化会话的第一个问题"""
        session = await self.session_service.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")

        question = await session.initialize()
        return question

    async def process_answer(self, session_id: str, answer: str) -> AsyncGenerator[StreamEvent, None]:
        """处理回答并返回流式事件"""
        session = await self.session_service.get_session(session_id)
        if not session:
            yield StreamEvent(
                type="error",
                data={"message": "会话不存在"},
                timestamp=datetime.now().isoformat()
            )
            return

        async for event in session.process_answer(answer):
            yield event

    async def process_voice_answer(self, session_id: str, audio_bytes: bytes) -> AsyncGenerator[StreamEvent, None]:
        """处理语音回答"""
        session = await self.session_service.get_session(session_id)
        if not session:
            yield StreamEvent(
                type="error",
                data={"message": f"会话 {session_id} 不存在"},
                timestamp=datetime.now().isoformat()
            )
            return

        try:
            # 1. 保存音频文件 (使用安全的文件名并转换为绝对路径)
            audio_path = generate_audio_path(str(session_id))
            save_wav_file(audio_bytes, audio_path)

            # 2. 调用会话的语音处理逻辑
            async for event in session.process_voice_answer(audio_path, self.voice_rag_service):
                yield event
        except Exception as e:
            import traceback
            error_msg = f"语音处理系统错误: {str(e)}"
            print(f"Error in process_voice_answer: {error_msg}")
            traceback.print_exc()
            yield StreamEvent(
                type="error",
                data={"message": error_msg},
                timestamp=datetime.now().isoformat()
            )

    async def get_session_info(self, session_id: str) -> dict:
        """获取会话信息"""
        session = await self.session_service.get_session(session_id)
        if not session:
            return None
        return session.get_session_info()

    async def end_session(self, session_id: str):
        """结束会话"""
        await self.session_service.delete_session(session_id)

    async def generate_session_evaluation(self, session_id: str) -> dict:
        """生成会话的综合评价（多维度、多主题、分轮次）"""
        session_info = await self.get_session_info(session_id)
        if not session_info:
            raise ValueError(f"会话 {session_id} 不存在")
        
        # 获取会话的数据库记录（包含时间信息）
        from app.infrastructure.mapper.session_mapper import SessionMapper
        session_model = await SessionMapper.get_session_with_history(session_id)
        if not session_model:
            raise ValueError("会话数据库记录不存在")
        
        # 计算时间
        start_time = session_model.created_at or datetime.now()
        end_time = session_model.updated_at or datetime.now()
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        # 生成综合评价（使用 LCEL 方式）
        evaluation = await self.rag_service.generate_comprehensive_evaluation(
            position=session_model.position,
            conversation_history=session_info.get("history", []),
            total_rounds=len(session_info.get("history", [])),
            duration_minutes=duration_minutes
        )
        
        # 填入 session_id
        evaluation["session_id"] = session_id
        
        return evaluation
