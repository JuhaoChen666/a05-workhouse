from typing import AsyncGenerator
from app.RAG.RAG_full import RAGService
from app.RAG.session_service import SessionService
from datetime import datetime
from app.models.interview_models import StreamEvent


class InterviewService:
    """面试业务服务"""

    def __init__(self):
        self.rag_service = RAGService()
        self.session_service = SessionService(self.rag_service)

    def initialize_database(self, collection_name: str):
        """初始化数据库"""
        return self.rag_service.initialize_database(collection_name)

    def start_interview(self, resume: str, position: str, collection_name: str) -> dict:
        """开始面试"""
        # 初始化数据库
        db_info = self.initialize_database(collection_name)

        # 创建会话
        session_id = self.session_service.create_session(resume, position)
        session = self.session_service.get_session(session_id)

        # 需要在异步环境中初始化，这里返回session_id，让路由层处理
        return {
            "session_id": session_id,
            "db_info": db_info
        }

    async def initialize_session_question(self, session_id: str) -> str:
        """初始化会话的第一个问题"""
        session = self.session_service.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")

        question = await session.initialize()
        return question

    async def process_answer(self, session_id: str, answer: str) -> AsyncGenerator[StreamEvent, None]:
        """处理回答并返回流式事件"""
        session = self.session_service.get_session(session_id)
        if not session:
            yield StreamEvent(
                type="error",
                data={"message": "会话不存在"},
                timestamp=datetime.now().isoformat()
            )
            return

        async for event in session.process_answer(answer):
            yield event

    def get_session_info(self, session_id: str) -> dict:
        """获取会话信息"""
        session = self.session_service.get_session(session_id)
        if not session:
            return None
        return session.get_session_info()

    def end_session(self, session_id: str):
        """结束会话"""
        self.session_service.delete_session(session_id)