import uuid
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from app.RAG.RAG_full import RAGService
from app.RAG.voice_service import VoiceRAGService
from app.models.interview_models import ConversationRecord, StreamEvent
from app.infrastructure.mapper.session_mapper import SessionMapper

class SessionService:
    """会话管理服务"""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        # 不再使用本地内存存储：
        # self.sessions: Dict[str, 'InterviewSession'] = {}

    async def create_session(self, resume: str, position: str, user_id: int = None) -> str:
        """创建新会话（写入数据库）"""
        session_id = str(uuid.uuid4())
        await SessionMapper.insert_session({
            "session_id": session_id,
            "user_id": user_id,
            "resume": resume,
            "position": position,
            "status": "initializing"
        })
        return session_id

    async def get_session(self, session_id: str) -> Optional['InterviewSession']:
        """获取会话（从数据库拉取并组装）"""
        session_model = await SessionMapper.get_session_with_history(session_id)
        if not session_model:
            return None
        
        # 将DB模型重组为InterviewSession业务对象
        session = InterviewSession(session_id, session_model.resume, session_model.position, self.rag_service)
        session.status = session_model.status
        session.current_topic = session_model.current_topic
        session.current_question = session_model.current_question
        
        # 根据round排序组合历史记录
        records = sorted(session_model.history_records, key=lambda x: x.round)
        session.conversation_history = [
            {
                "round": r.round,
                "question": r.question,
                "answer": r.answer,
                "topic": r.topic,
                "emotion": r.emotion,
                "timestamp": r.timestamp.isoformat() if r.timestamp else datetime.now().isoformat()
            } for r in records
        ]
        return session

    async def delete_session(self, session_id: str):
        """删除会话"""
        # 注意：这里可以选择实现数据库软删除/硬删除，或者为了合规保留记录。
        # 暂时只重置状态即可
        await SessionMapper.update_session(session_id, {"status": "completed"})


class InterviewSession:
    """面试会话类"""

    def __init__(self, session_id: str, resume: str, position: str, rag_service: RAGService):
        self.session_id = session_id
        self.resume = resume
        self.position = position
        self.rag_service = rag_service
        self.conversation_history: List[Dict] = []
        self.current_topic: Optional[str] = None
        self.current_question: Optional[str] = None
        self.status: str = "initializing"  # initializing, questioning, analyzing, completed
        self.max_depth_per_topic: int = 3

    async def initialize(self) -> str:
        """初始化面试，生成第一个问题"""
        # 生成初始问题
        self.current_question = await self.rag_service.generate_initial_question(
            self.resume, self.position
        )
        self.current_topic = await self.rag_service.extract_topic(self.current_question)
        self.status = "questioning"
        
        # 同步数据库
        await SessionMapper.update_session(self.session_id, {
            "current_question": self.current_question,
            "current_topic": self.current_topic,
            "status": self.status
        })
        return self.current_question

    async def process_answer(self, answer: str) -> AsyncGenerator[StreamEvent, None]:
        """处理用户文字回答"""
        async for event in self._process_answer_logic(answer):
            yield event

    async def _process_answer_logic(self, answer: str, emotion_data: Optional[Dict] = None) -> AsyncGenerator[StreamEvent, None]:
        """核心业务逻辑：处理回答，分析深度，生成追问或切换主题"""
        
        if self.status != "questioning":
            yield StreamEvent(
                type="error",
                data={"message": "当前状态无法接收回答"},
                timestamp=datetime.now().isoformat()
            )
            return

        # 记录回答
        qa_record = {
            "round": len(self.conversation_history) + 1,
            "question": self.current_question,
            "answer": answer,
            "topic": self.current_topic,
            "emotion": emotion_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查是否已经在 history 中（由 process_voice_answer 事先存入）
        if not any(h['round'] == qa_record['round'] for h in self.conversation_history):
            self.conversation_history.append(qa_record)
            # 持久化到 MySQL 对话记录表
            await SessionMapper.insert_chat_record(self.session_id, qa_record)

        # 分析回答深度
        yield StreamEvent(
            type="analyzing",
            data={"message": "正在分析回答深度" + (" (结合情感分析)" if emotion_data else "") + "..."},
            timestamp=datetime.now().isoformat()
        )

        analysis = await self.rag_service.analyze_answer_depth(
            self.current_question, answer, emotion_data=emotion_data
        )

        yield StreamEvent(
            type="analysis_result",
            data={
                "depth_score": analysis.get("depth_score", 5),
                "is_vague": analysis.get("is_vague", False),
                "need_followup": analysis.get("need_followup", False),
                "feedback": analysis.get("feedback_to_candidate", "")
            },
            timestamp=datetime.now().isoformat()
        )

        # 获取当前主题的 QA 历史
        topic_qa_history = [q for q in self.conversation_history
                            if q['topic'] == self.current_topic]

        # 检查是否已达到当前主题的最大深度
        is_max_depth_reached = len(topic_qa_history) >= self.max_depth_per_topic
        
        # 判断是否需要追问（但不超过最大深度）
        if analysis.get("need_followup", False) and not is_max_depth_reached:
            yield StreamEvent(
                type="followup",
                data={"message": "回答不够深入，准备追问..."},
                timestamp=datetime.now().isoformat()
            )

            followup_point = analysis.get("followup_point", "")
            followup_question = await self.rag_service.generate_followup_question(
                self.current_question,
                answer,
                followup_point,
                self.position
            )

            self.current_question = followup_question
            self.status = "questioning"
            
            # 持久化新的问题和状态
            await SessionMapper.update_session(self.session_id, {
                "current_question": self.current_question,
                "status": self.status
            })

            yield StreamEvent(
                type="question",
                data={
                    "question": self.current_question,
                    "is_followup": True,
                    "topic": self.current_topic,
                    "round": len(self.conversation_history) + 1
                },
                timestamp=datetime.now().isoformat()
            )
            return

        # 检查主题完整性
        yield StreamEvent(
            type="checking_completeness",
            data={"message": "检查主题完整性..."},
            timestamp=datetime.now().isoformat()
        )

        completeness = await self.rag_service.check_topic_completeness(
            self.current_topic, topic_qa_history
        )

        yield StreamEvent(
            type="completeness_result",
            data=completeness,
            timestamp=datetime.now().isoformat()
        )

        # 决定下一步
        if completeness.get("is_sufficient", False) or is_max_depth_reached:
            # 当前主题结束
            yield StreamEvent(
                type="topic_completed",
                data={"topic": self.current_topic},
                timestamp=datetime.now().isoformat()
            )

            completed_topics = list(set([q['topic'] for q in self.conversation_history]))

            # 检查是否已经覆盖足够主题
            if len(completed_topics) >= 5:
                yield StreamEvent(
                    type="interview_complete",
                    data={
                        "message": "面试考察完成",
                        "total_rounds": len(self.conversation_history),
                        "covered_topics": completed_topics
                    },
                    timestamp=datetime.now().isoformat()
                )

                # 生成最终评价
                evaluation = await self.rag_service.generate_final_evaluation(
                    self.position, self.conversation_history
                )
                yield StreamEvent(
                    type="evaluation",
                    data=evaluation,
                    timestamp=datetime.now().isoformat()
                )

                self.status = "completed"
                # 更新状态为 completed
                await SessionMapper.update_session(self.session_id, {"status": self.status})
                return

            # 生成下一个主题的问题
            history_summary = "\n".join([
                f"Q: {q['question']}\nA: {q['answer'][:100]}..."
                for q in self.conversation_history[-3:]
            ])

            next_question = await self.rag_service.generate_next_question(
                self.resume,
                self.position,
                completed_topics,
                history_summary
            )

            self.current_question = next_question
            self.current_topic = await self.rag_service.extract_topic(self.current_question)
            self.status = "questioning"
            
            # 持久化下一个主题和问题
            await SessionMapper.update_session(self.session_id, {
                "current_question": self.current_question,
                "current_topic": self.current_topic,
                "status": self.status
            })

            yield StreamEvent(
                type="question",
                data={
                    "question": self.current_question,
                    "is_followup": False,
                    "topic": self.current_topic,
                    "round": len(self.conversation_history) + 1
                },
                timestamp=datetime.now().isoformat()
            )
        else:
            # 继续深入当前主题
            missing_points = completeness.get("missing_points", [])
            if missing_points:
                yield StreamEvent(
                    type="missing_points",
                    data={"points": missing_points},
                    timestamp=datetime.now().isoformat()
                )

                followup_question = await self.rag_service.generate_followup_question(
                    self.current_question,
                    answer,
                    missing_points[0],
                    self.position
                )
                self.current_question = followup_question
                self.status = "questioning"
                
                # 持久化新的问题
                await SessionMapper.update_session(self.session_id, {
                    "current_question": self.current_question,
                    "status": self.status
                })

                yield StreamEvent(
                    type="question",
                    data={
                        "question": self.current_question,
                        "is_followup": True,
                        "topic": self.current_topic,
                        "round": len(self.conversation_history) + 1
                    },
                    timestamp=datetime.now().isoformat()
                )

    async def process_voice_answer(self, audio_path: str, voice_rag_service: VoiceRAGService) -> AsyncGenerator[StreamEvent, None]:
        """处理语音回答，返回流式事件"""

        if self.status != "questioning":
            yield StreamEvent(
                type="error",
                data={"message": "当前状态无法接收回答"},
                timestamp=datetime.now().isoformat()
            )
            return

        # 1. 语音处理（ASR + 情感分析）
        yield StreamEvent(
            type="voice_processing",
            data={"message": "正在录音转写并分析情感..."},
            timestamp=datetime.now().isoformat()
        )
        
        voice_result = await voice_rag_service.process_voice_input(audio_path)
        asr_text = voice_result["asr_text"]
        emotion_features = voice_result["emotion_features"]

        # 2. 发送转写和情感结果 (提前给前端反馈)
        yield StreamEvent(
            type="voice_result",
            data={
                "asr_text": asr_text,
                "emotion_features": emotion_features
            },
            timestamp=datetime.now().isoformat()
        )

        # 3. 调用核心面试逻辑 (传入 ASR 文本和情感数据)
        async for event in self._process_answer_logic(asr_text, emotion_data=emotion_features):
            yield event

        yield StreamEvent(
            type="complete",
            data={"message": "语音回答处理完成"},
            timestamp=datetime.now().isoformat()
        )

    def get_session_info(self) -> dict:
        """获取会话信息"""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "total_rounds": len(self.conversation_history),
            "current_topic": self.current_topic,
            "current_question": self.current_question,
            "history": self.conversation_history
        }