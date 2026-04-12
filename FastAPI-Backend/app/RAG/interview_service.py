import asyncio
from typing import AsyncGenerator
from app.RAG.RAG_full import RAGService
from app.RAG.session_service import SessionService
from app.RAG.voice_service import VoiceRAGService
from app.utils.audio_utils import generate_audio_path, save_wav_file
from app.infrastructure.mapper.session_mapper import SessionMapper
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

    async def start_interview(self, resume_id: int, position: str, collection_name: str, user_id: int = None, difficulty: str = "Normal") -> dict:
        """开始面试"""
        # 0. 查找简历内容
        resume_record = await SessionMapper.get_resume_by_id(resume_id)
        if not resume_record:
            raise ValueError(f"简历 ID {resume_id} 不存在")
        
        resume_text = resume_record.content_text
        if not resume_text:
             raise ValueError(f"简历 ID {resume_id} 内容为空，请重新上传")

        # 1. 初始化数据库
        db_info = self.initialize_database(collection_name)

        # 2. 创建会话
        session_id = await self.session_service.create_session(resume_text, position, user_id, difficulty)

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
        """生成并保存会话的综合评价"""
        
        # 1. 尝试从数据库获取已有的评价
        existing_eval = await SessionMapper.get_evaluation_by_session_id(session_id)
        if existing_eval:
            return existing_eval.evaluation_json
            
        # 2. 如果数据库没有，则进行生成
        session_model = await SessionMapper.get_session_with_history(session_id)
        if not session_model:
            raise ValueError("会话数据库记录不存在")
        
        # 获取会话信息以便计算轮次和处理历史
        session_info = await self.get_session_info(session_id)
        
        # 计算时间
        start_time = session_model.created_at or datetime.now()
        end_time = session_model.updated_at or datetime.now()
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        # 调用 RAG 生成综合评价
        evaluation = await self.rag_service.generate_comprehensive_evaluation(
            position=session_model.position,
            conversation_history=session_info.get("history", []),
            total_rounds=len(session_info.get("history", [])),
            duration_minutes=duration_minutes
        )
        
        # 3. 填入 session_id 并保存到数据库
        evaluation["session_id"] = session_id
        await SessionMapper.insert_evaluation(session_id, evaluation, user_id=session_model.user_id)
        
        return evaluation

    async def stream_predict_questions(
        self, resume_id: int, position: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        按简历与岗位流式输出押题（NDJSON）。
        事件：prediction_item（id, question, key_points, answer, difficulty），prediction_complete，error。
        与线上一致；后续可在此接入 LLM / RAG。
        """
        resume_record = await SessionMapper.get_resume_by_id(resume_id)
        if not resume_record:
            yield StreamEvent(
                type="error",
                data={"message": f"简历 ID {resume_id} 不存在"},
                timestamp=datetime.now().isoformat(),
            )
            return

        pos = (position or "general").strip() or "general"
        preview = (resume_record.content_text or "")[:400].replace("\n", " ")

        samples = [
            {
                "question": f"结合岗位方向「{pos}」，请说明你如何保证线上服务的稳定性与可观测性？",
                "key_points": "监控指标、日志、告警、限流降级、容灾演练、STAR 法则",
                "answer": "可从监控指标、日志、告警、限流降级、容灾演练等角度作答；若有简历中的真实项目，请用 STAR 简述背景、动作与结果。",
                "difficulty": "中等",
            },
            {
                "question": "请介绍你最近一个项目中，技术方案选型的主要依据与权衡。",
                "key_points": f"简历项目、{pos} 相关经验、备选方案对比、可量化结果",
                "answer": f"建议引用简历中与「{pos}」相关的项目，对比备选方案（性能、成本、团队熟悉度、维护性），并说明最终指标是否达标。",
                "difficulty": "中等",
            },
            {
                "question": "请简述线程池的核心参数及其作用。",
                "key_points": "corePoolSize, maximumPoolSize, workQueue, keepAliveTime, threadFactory, handler",
                "answer": "核心参数包括：核心线程数（corePoolSize）、最大线程数（maximumPoolSize）、任务队列（workQueue）、非核心线程存活时间（keepAliveTime）、线程工厂（threadFactory）和拒绝策略（handler）。它们共同控制线程池的资源分配与任务调度。",
                "difficulty": "简单",
            },
        ]

        for i, row in enumerate(samples):
            yield StreamEvent(
                type="prediction_item",
                data={
                    "id": i + 1,
                    "question": row["question"],
                    "key_points": row["key_points"],
                    "answer": row["answer"],
                    "difficulty": row["difficulty"],
                    "resume_preview_hint": preview[:120] + ("…" if len(preview) > 120 else ""),
                },
                timestamp=datetime.now().isoformat(),
            )
            await asyncio.sleep(0.28)

        yield StreamEvent(
            type="prediction_complete",
            data={"total": len(samples)},
            timestamp=datetime.now().isoformat(),
        )
