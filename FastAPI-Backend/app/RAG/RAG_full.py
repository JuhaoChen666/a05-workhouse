import os
import re
import json
from typing import List, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from app.llm.deepseek import DeepSeek_LLM
from .embeddings import get_embedding
from .Chromadb import get_Chroma_db


class RAGService:
    """RAG核心服务类"""

    def __init__(self):
        self.embeddings = get_embedding()
        self.db_kb = None
        self.db_qb = None
        self.collection_name = None
        self._initialize_prompts()

    def _initialize_prompts(self):
        """初始化所有提示模板"""

        # 答案深度评估器
        self.answer_depth_analyzer_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，需要评估候选人对技术问题的回答深度。

        问题: {question}
        候选人的回答: {answer}
        标准答案参考: {knowledge_base}

        请分析候选人的回答，判断：
        1. 回答是否过于概括/模糊？（是/否）
        2. 回答的深度评分（1-10分，1=完全模糊，10=非常详细）
        3. 是否需要追问？（是/否）
        4. 如果需要追问，应该追问哪个具体的技术点？（从回答中缺失或不够深入的点中选择）
        5. 追问的方向是什么？

        输出JSON格式：
        {{
            "is_vague": true/false,
            "depth_score": 1-10,
            "need_followup": true/false,
            "followup_point": "具体技术点",
            "followup_direction": "详细的追问问题"
        }}
        """)

        # 追问问题生成器
        self.followup_question_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，基于候选人的回答，需要提出一个更深入、更具体的问题。

        原始问题: {original_question}
        候选人的回答: {answer}
        需要追问的技术点: {followup_point}
        岗位要求: {position}

        请生成一个具体的追问问题，要求：
        1. 问题要具体、有针对性
        2. 考察候选人对该技术点的深入理解
        3. 引导候选人提供更详细的技术细节
        4. 语气保持专业但友好

        只输出问题内容，不要有其他内容。
        """)

        # 问题完成度评估器
        self.topic_completeness_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，需要判断某个技术主题的考察是否已经足够深入。

        技术主题: {topic}
        已经提问和回答的历史:
        {qa_history}
        标准知识库: {knowledge_base}

        请判断并输出JSON格式：
        {{
            "is_sufficient": true/false,
            "missing_points": ["知识点1", "知识点2"],
            "suggestion": "继续深入/结束本话题/转换到新话题"
        }}
        """)

        # 初始问题生成器
        self.initial_question_prompt = ChatPromptTemplate.from_template("""
        根据候选人的简历和岗位，生成第一个面试问题。

        简历: {resume}
        岗位: {position}
        问题库参考: {questions}

        要求：
        1. 从基础开始，难度适中
        2. 问题要开放，便于深入追问
        3. 与简历中的技术栈相关

        只输出问题内容，不要有其他说明。
        """)

        # 下一个主题生成器
        self.next_topic_prompt = ChatPromptTemplate.from_template("""
        根据以下信息，生成下一个面试问题：

        候选人简历: {resume}
        岗位: {position}
        已考察的主题: {completed_topics}
        对话历史: {history}

        要求：
        1. 选择新的技术主题，不要重复已考察的内容
        2. 难度逐步提升
        3. 与简历中的技术栈相关

        只输出问题内容。
        """)

        # 最终评价生成器
        self.final_evaluation_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，请根据整个面试过程给出综合评价。

        岗位: {position}
        面试对话历史:
        {full_history}

        请输出JSON格式：
        {{
            "technical_evaluation": "技术能力评价",
            "communication_evaluation": "沟通表达能力评价",
            "overall_score": 85,
            "recommendation": "强烈推荐/推荐/待定/不推荐",
            "strengths": ["优点1", "优点2"],
            "weaknesses": ["不足1", "不足2"],
            "detailed_comment": "详细评语"
        }}
        """)

    def initialize_database(self, collection_name: str):
        """初始化数据库连接"""
        if self.collection_name != collection_name:
            self.collection_name = collection_name
            self.db_kb = get_Chroma_db(self.embeddings, collection_name + "_kb")
            self.db_qb = get_Chroma_db(self.embeddings, collection_name + "_qb")
            return {
                "kb_count": self.db_kb._collection.count(),
                "qb_count": self.db_qb._collection.count()
            }
        return None

    def retrieve_questions(self, query: str, k: int = 5) -> str:
        """从问题库检索问题"""
        docs = self.db_qb.similarity_search(query, k=k)
        return "\n\n".join([doc.page_content for doc in docs])

    def retrieve_knowledge(self, query: str, k: int = 3) -> str:
        """检索知识库"""
        docs = self.db_kb.similarity_search(query, k=k)
        return "\n".join([doc.page_content for doc in docs])

    async def generate_initial_question(self, resume: str, position: str) -> str:
        """生成初始问题"""
        retrieval_query = f"{resume} {position} 基础问题 难度0.2"
        questions_text = self.retrieve_questions(retrieval_query, k=5)

        chain = self.initial_question_prompt | DeepSeek_LLM | StrOutputParser()
        question = await chain.ainvoke({
            "resume": resume,
            "position": position,
            "questions": questions_text
        })

        return question.strip()

    async def extract_topic(self, question: str) -> str:
        """从问题中提取主题"""
        topic_prompt = ChatPromptTemplate.from_template("""
        从以下面试问题中提取核心技术主题（2-4个词）：
        问题: {question}

        只输出主题，不要有其他内容。
        """)

        chain = topic_prompt | DeepSeek_LLM | StrOutputParser()
        topic = await chain.ainvoke({"question": question})
        return topic.strip()

    async def analyze_answer_depth(self, question: str, answer: str) -> dict:
        """分析回答深度"""
        knowledge = self.retrieve_knowledge(f"{question} {answer}", k=3)

        chain = self.answer_depth_analyzer_prompt | DeepSeek_LLM | StrOutputParser()
        result = await chain.ainvoke({
            "question": question,
            "answer": answer,
            "knowledge_base": knowledge
        })

        # 尝试解析JSON
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "is_vague": False,
                    "depth_score": 5,
                    "need_followup": False,
                    "followup_point": "",
                    "followup_direction": ""
                }
        except:
            analysis = {
                "is_vague": False,
                "depth_score": 5,
                "need_followup": False,
                "followup_point": "",
                "followup_direction": ""
            }

        return analysis

    async def generate_followup_question(self, original_question: str, answer: str,
                                         followup_point: str, position: str) -> str:
        """生成追问问题"""
        chain = self.followup_question_prompt | DeepSeek_LLM | StrOutputParser()
        question = await chain.ainvoke({
            "original_question": original_question,
            "answer": answer,
            "followup_point": followup_point,
            "position": position
        })
        return question.strip()

    async def check_topic_completeness(self, topic: str, qa_history: List[Dict]) -> dict:
        """检查主题完整性"""
        history_text = "\n".join([
            f"Q: {item['question']}\nA: {item['answer']}"
            for item in qa_history[-3:]
        ])

        knowledge = self.retrieve_knowledge(topic, k=3)

        chain = self.topic_completeness_prompt | DeepSeek_LLM | StrOutputParser()
        result = await chain.ainvoke({
            "topic": topic,
            "qa_history": history_text,
            "knowledge_base": knowledge
        })

        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                completeness = json.loads(json_match.group())
            else:
                completeness = {
                    "is_sufficient": False,
                    "missing_points": [],
                    "suggestion": "继续深入"
                }
        except:
            completeness = {
                "is_sufficient": False,
                "missing_points": [],
                "suggestion": "继续深入"
            }

        return completeness

    async def generate_next_question(self, resume: str, position: str,
                                     completed_topics: List[str],
                                     history: str) -> str:
        """生成下一个问题"""
        chain = self.next_topic_prompt | DeepSeek_LLM | StrOutputParser()
        question = await chain.ainvoke({
            "resume": resume,
            "position": position,
            "completed_topics": ", ".join(completed_topics),
            "history": history
        })
        return question.strip()

    async def generate_final_evaluation(self, position: str,
                                        conversation_history: List[Dict]) -> dict:
        """生成最终评价"""
        full_history = "\n".join([
            f"Q{q.get('round', i + 1)}: {q['question']}\nA: {q['answer']}"
            for i, q in enumerate(conversation_history)
        ])

        chain = self.final_evaluation_prompt | DeepSeek_LLM | StrOutputParser()
        result = await chain.ainvoke({
            "position": position,
            "full_history": full_history
        })

        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
            else:
                evaluation = {
                    "technical_evaluation": "评价生成失败",
                    "communication_evaluation": "评价生成失败",
                    "overall_score": 0,
                    "recommendation": "待定",
                    "strengths": [],
                    "weaknesses": [],
                    "detailed_comment": result[:500]
                }
        except:
            evaluation = {
                "technical_evaluation": "评价生成失败",
                "communication_evaluation": "评价生成失败",
                "overall_score": 0,
                "recommendation": "待定",
                "strengths": [],
                "weaknesses": [],
                "detailed_comment": result[:500]
            }

        return evaluation