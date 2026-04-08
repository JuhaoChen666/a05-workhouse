from typing import List, Optional, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.infrastructure.database import AsyncSessionLocal
from app.models.session_models import SessionModel, ChatHistoryModel, InterviewEvaluationModel
from datetime import datetime

class SessionMapper:
    """操作MySQL的专门Mapper类，类似于MyBatis Interface。我们在这里封装所有DB交互以保持业务层纯净"""

    @staticmethod
    async def insert_session(session_data: Dict[str, Any]) -> None:
        """插入一条新会话记录"""
        async with AsyncSessionLocal() as db:
            new_session = SessionModel(
                session_id=session_data["session_id"],
                user_id=session_data.get("user_id"),
                resume=session_data.get("resume", ""),
                position=session_data.get("position", ""),
                status=session_data.get("status", "initializing"),
                difficulty=session_data.get("difficulty", "Normal"),
                current_topic=session_data.get("current_topic"),
                current_question=session_data.get("current_question"),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(new_session)
            await db.commit()

    @staticmethod
    async def get_sessions_by_user_id(user_id: int) -> List[SessionModel]:
        """获取某用户的所有历史会话"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SessionModel)
                .filter(SessionModel.user_id == user_id)
                .order_by(SessionModel.created_at.desc())
            )
            return result.scalars().all()

    @staticmethod
    async def get_session_by_id(session_id: str) -> Optional[SessionModel]:
        """根据ID查询会话，懒加载不会连带查出history"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SessionModel).filter(SessionModel.session_id == session_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_session_with_history(session_id: str) -> Optional[SessionModel]:
        """拉取整个会话连同对话历史（使用 selectinload 加载集合）"""
        async with AsyncSessionLocal() as db:
            stmt = select(SessionModel).options(selectinload(SessionModel.history_records)).filter(SessionModel.session_id == session_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    async def update_session(session_id: str, updates: Dict[str, Any]) -> None:
        """更新会话字段，例如status，current_topic"""
        async with AsyncSessionLocal() as db:
            session = await db.scalar(select(SessionModel).filter(SessionModel.session_id == session_id))
            if session:
                for key, value in updates.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.updated_at = datetime.now()
                await db.commit()

    @staticmethod
    async def insert_chat_record(session_id: str, record_data: Dict[str, Any]) -> None:
        """插入一条对话流水"""
        async with AsyncSessionLocal() as db:
            history = ChatHistoryModel(
                session_id=session_id,
                round=record_data["round"],
                question=record_data.get("question", ""),
                answer=record_data.get("answer", ""),
                topic=record_data.get("topic", ""),
                emotion=record_data.get("emotion"),
                timestamp=datetime.fromisoformat(record_data.get("timestamp")) if record_data.get("timestamp") else datetime.now()
            )
            db.add(history)
            await db.commit()

    @staticmethod
    async def insert_evaluation(session_id: str, evaluation_data: Dict[str, Any], user_id: Optional[int] = None) -> None:
        """保存面试评价到数据库"""
        async with AsyncSessionLocal() as db:
            evaluation = InterviewEvaluationModel(
                session_id=session_id,
                user_id=user_id,
                overall_score=evaluation_data.get("overall_score", 0.0),
                technical_competency=evaluation_data.get("technical_competency", 0.0),
                communication_skill=evaluation_data.get("communication_skill", 0.0),
                problem_solving=evaluation_data.get("problem_solving", 0.0),
                depth_of_knowledge=evaluation_data.get("depth_of_knowledge", 0.0),
                evaluation_json=evaluation_data,
                created_at=datetime.now()
            )
            db.add(evaluation)
            await db.commit()

    @staticmethod
    async def get_evaluation_by_session_id(session_id: str) -> Optional[InterviewEvaluationModel]:
        """获取某场面试的评价"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(InterviewEvaluationModel).filter(InterviewEvaluationModel.session_id == session_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def get_user_evaluation_trend(user_id: int, limit: int = 5) -> List[InterviewEvaluationModel]:
        """获取用户最近 N 次面试的评分趋势"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(InterviewEvaluationModel)
                .filter(InterviewEvaluationModel.user_id == user_id)
                .order_by(InterviewEvaluationModel.created_at.desc())
                .limit(limit)
            )
            # 返回结果改为升序，方便前端绘图
            records = result.scalars().all()
            return sorted(records, key=lambda x: x.created_at)

    @staticmethod
    async def get_sessions_paginated(user_id: int, page: int = 1, page_size: int = 10) -> List[SessionModel]:
        """按用户ID精准分页查询会话"""
        async with AsyncSessionLocal() as db:
            offset = (page - 1) * page_size
            result = await db.execute(
                select(SessionModel)
                .filter(SessionModel.user_id == user_id)
                .order_by(SessionModel.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            return result.scalars().all()

    @staticmethod
    async def get_chat_history_paginated(session_id: str, page: int = 1, page_size: int = 10) -> List[ChatHistoryModel]:
        """按会话ID分页查询聊天记录（按日期从前往后排序）"""
        async with AsyncSessionLocal() as db:
            offset = (page - 1) * page_size
            result = await db.execute(
                select(ChatHistoryModel)
                .filter(ChatHistoryModel.session_id == session_id)
                .order_by(ChatHistoryModel.timestamp.asc())
                .offset(offset)
                .limit(page_size)
            )
            return result.scalars().all()
