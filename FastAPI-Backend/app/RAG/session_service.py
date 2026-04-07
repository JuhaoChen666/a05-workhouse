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

    async def create_session(self, resume: str, position: str, user_id: int = None, difficulty: str = "Normal") -> str:
        """创建新会话（写入数据库）"""
        session_id = str(uuid.uuid4())
        await SessionMapper.insert_session({
            "session_id": session_id,
            "user_id": user_id,
            "resume": resume,
            "position": position,
            "difficulty": difficulty,
            "status": "initializing"
        })
        return session_id

    async def get_session(self, session_id: str) -> Optional['InterviewSession']:
        """获取会话（从数据库拉取并组装）"""
        session_model = await SessionMapper.get_session_with_history(session_id)
        if not session_model:
            return None
        
        # 将DB模型重组为InterviewSession业务对象
        session = InterviewSession(
            session_id, 
            session_model.resume, 
            session_model.position, 
            self.rag_service, 
            user_id=session_model.user_id,
            difficulty=session_model.difficulty or "Normal"
        )
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

    def __init__(self, session_id: str, resume: str, position: str, rag_service: RAGService, user_id: Optional[int] = None, difficulty: str = "Normal"):
        self.session_id = session_id
        self.user_id = user_id
        self.resume = resume
        self.position = position
        self.rag_service = rag_service
        self.difficulty = difficulty
        self.conversation_history: List[Dict] = []
        self.current_topic: Optional[str] = None
        self.current_question: Optional[str] = None
        self.status: str = "initializing"  # initializing, questioning, analyzing, completed
        
        # 行为矩阵配置 (V3.0)
        difficulty_configs = {
            "Easy": {"max_depth": 2, "threshold": 7.5},
            "Normal": {"max_depth": 3, "threshold": 8.5},
            "Hard": {"max_depth": 5, "threshold": 9.0}
        }
        config = difficulty_configs.get(self.difficulty, difficulty_configs["Normal"])
        self.max_depth_per_topic: int = config["max_depth"]
        self.threshold: float = config["threshold"]
        
        # 淘汰计数
        self.consecutive_failed_rounds: int = 0  # 单话题连续失败轮次 (< 7.0)
        self.failed_topics_streak: int = 0         # 累计失败话题数

    async def initialize(self) -> str:
        """初始化面试，生成第一个问题"""
        # 生成初始问题
        self.current_question = await self.rag_service.generate_initial_question(
            self.resume, self.position, self.difficulty
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
            data={"message": f"正在进行{self.difficulty}模式深度分析" + (" (结合情感分析)" if emotion_data else "") + "..."},
            timestamp=datetime.now().isoformat()
        )

        analysis = await self.rag_service.analyze_answer_depth(
            self.current_question, answer, difficulty=self.difficulty, emotion_data=emotion_data
        )
        
        depth_score = analysis.get("depth_score", 5)
        # 精准阈值修正：如果分数未达到当前难度的阈值，则强制标记为需要追问（除非已达最大深度）
        need_followup_by_score = depth_score < self.threshold
        
        # Hard 模式特殊计数
        is_hard_fail = self.difficulty == "Hard" and depth_score < 7.0
        if is_hard_fail:
            self.consecutive_failed_rounds += 1
        else:
            self.consecutive_failed_rounds = 0

        yield StreamEvent(
            type="analysis_result",
            data={
                "depth_score": depth_score,
                "is_vague": analysis.get("is_vague", False),
                "need_followup": need_followup_by_score,
                "feedback": analysis.get("feedback_to_candidate", "")
            },
            timestamp=datetime.now().isoformat()
        )
        
        # Hard 模式断路控制：如果单话题连续 2 轮不达标 (< 7.0)，强制结束本话题
        force_stop_topic = self.difficulty == "Hard" and self.consecutive_failed_rounds >= 2

        # 获取当前主题的 QA 历史
        topic_qa_history = [q for q in self.conversation_history
                            if q['topic'] == self.current_topic]

        # 检查是否已达到当前主题的最大深度
        is_max_depth_reached = len(topic_qa_history) >= self.max_depth_per_topic
        
        # 判断是否需要追问（但不超过最大深度）
        if not force_stop_topic and need_followup_by_score and not is_max_depth_reached:
            yield StreamEvent(
                type="followup",
                data={"message": "表现未达标，继续深入考察..." if self.difficulty == "Hard" else "回答不够深入，准备追问..."},
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
        if completeness.get("is_sufficient", False) or is_max_depth_reached or force_stop_topic:
            # Hard 模式记录失败话题数
            if force_stop_topic:
                self.failed_topics_streak += 1
                self.consecutive_failed_rounds = 0 # 重置单轮计数

            # 当前主题结束
            yield StreamEvent(
                type="topic_completed",
                data={
                    "topic": self.current_topic,
                    "reason": "考核通过" if not force_stop_topic else "由于表现不佳强制切题"
                },
                timestamp=datetime.now().isoformat()
            )

            completed_topics = list(set([q['topic'] for q in self.conversation_history]))

            # 检查是否已经覆盖足够主题 或 硬淘汰逻辑
            is_eliminated = self.difficulty == "Hard" and self.failed_topics_streak >= 2
            is_finished = len(completed_topics) >= 5 or is_eliminated

            if is_finished:
                bye_message = "由于您多次未能清晰回答核心技术点，本次面试提前结束。建议针对简历中的技术栈进行更深入的学习。" if is_eliminated else "面试考察完成"
                
                yield StreamEvent(
                    type="interview_complete",
                    data={
                        "message": bye_message,
                        "total_rounds": len(self.conversation_history),
                        "covered_topics": completed_topics,
                        "is_eliminated": is_eliminated
                    },
                    timestamp=datetime.now().isoformat()
                )

                # 生成最终评价
                evaluation = await self.rag_service.generate_final_evaluation(
                    self.position, self.conversation_history
                )
                
                # 持久化到数据库 (修复 bug: 之前未在此保存，且现在加入了 user_id)
                evaluation["session_id"] = self.session_id
                await SessionMapper.insert_evaluation(self.session_id, evaluation, user_id=self.user_id)
                
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
                history_summary,
                self.difficulty
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