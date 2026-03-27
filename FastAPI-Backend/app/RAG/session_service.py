import uuid
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from app.RAG.RAG_full import RAGService
from app.models.interview_models import ConversationRecord, StreamEvent


class SessionService:
    """会话管理服务"""

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.sessions: Dict[str, 'InterviewSession'] = {}

    def create_session(self, resume: str, position: str) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        session = InterviewSession(session_id, resume, position, self.rag_service)
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional['InterviewSession']:
        """获取会话"""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]


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
        return self.current_question

    async def process_answer(self, answer: str) -> AsyncGenerator[StreamEvent, None]:
        """处理用户回答，返回流式事件"""

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
            "timestamp": datetime.now().isoformat()
        }
        self.conversation_history.append(qa_record)

        # 分析回答深度
        yield StreamEvent(
            type="analyzing",
            data={"message": "正在分析回答深度..."},
            timestamp=datetime.now().isoformat()
        )

        analysis = await self.rag_service.analyze_answer_depth(
            self.current_question, answer
        )

        yield StreamEvent(
            type="analysis_result",
            data={
                "depth_score": analysis.get("depth_score", 5),
                "is_vague": analysis.get("is_vague", False),
                "need_followup": analysis.get("need_followup", False)
            },
            timestamp=datetime.now().isoformat()
        )

        # 获取当前主题的QA历史
        topic_qa_history = [q for q in self.conversation_history
                            if q['topic'] == self.current_topic]

        # 判断是否需要追问
        if analysis.get("need_followup", False) and len(topic_qa_history) < self.max_depth_per_topic:
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
        if completeness.get("is_sufficient", False) or len(topic_qa_history) >= self.max_depth_per_topic:
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
                    data={"message": "面试考察完成"},
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