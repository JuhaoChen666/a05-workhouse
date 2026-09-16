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
        当前面试难度：{difficulty}
        评分标准：{scoring_standard}

        问题: {question}
        候选人的回答: {answer}
        标准答案参考: {knowledge_base}

        请分析候选人的回答，判断：
        1. 回答是否过于概括/模糊？（是/否）
        2. 回答的深度评分（1-10分，请严格遵守难度对应的评分标准）
        3. 是否需要追问？（根据评分标准判断，达标则否，不达标则是）
        4. 如果需要追问，应该追问哪个具体的技术点？
        5. 追问的方向是什么？
        6. 给候选人的反馈（如果是 Hard 模式且评分 < 7.0，请生成一段刻意刁难、严苛的反馈内容）

        输出JSON格式：
        {{
            "is_vague": true/false,
            "depth_score": 1-10,
            "need_followup": true/false,
            "followup_point": "具体技术点",
            "followup_direction": "详细的追问问题",
            "feedback_to_candidate": "反馈内容"
        }}
        """)

        # 语音版结果深度评估器 (包含情感分析)
        self.voice_answer_depth_analyzer_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，正在通过语音与候选人进行技术面试。
        你需要评估候选人对技术问题的回答深度及其情感表现。
        当前面试难度：{difficulty}
        评分标准：{scoring_standard}

        问题: {question}
        候选人的回答（ASR自动转写）: {answer}
        候选人的情感分析结果: {emotion_data}
        标准答案参考: {knowledge_base}

        请结合回答内容（ASR文本可能会有小误差）和候选人的情感特征（如自信、犹豫、紧张等），分析并判断：
        1. 回答内容是否达到了要求的深度？（考虑ASR转写可能存在错别字）
        2. 情感状态是否影响了表达？（如过于紧张导致逻辑不清）
        3. 回答的深度评分（1-10分）
        4. 是否需要针对未说清的点进行追问？
        5. 对候选人给出一个口语化的、兼顾技术与情绪的简短反馈（feedback）。

        输出JSON格式：
        {{
            "is_vague": true/false,
            "depth_score": 1-10,
            "need_followup": true/false,
            "followup_point": "具体技术点",
            "followup_direction": "详细的追问问题",
            "feedback_to_candidate": "给候选人的口语化反馈"
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
        当前难度系数：{difficulty_factor} (1.0为标准)

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
        当前难度系数：{difficulty_factor} (1.0为标准)

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

        self.final_evaluation_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的面试官，请根据整个面试过程给出综合评价。

        岗位：{position}
        面试对话历史:
        {full_history}

        要求：
        1. 所有评分量程均为 0-10 分（0为最差，10为满分）。
        2. 如果候选人回答内容极少、重复或与问题无关，总分应在 0-3 分之间。
        3. 建议（recommendation）若为“不推荐”，总分必须小于 4 分。

        请输出 JSON 格式：
        {{
            "technical_evaluation": "技术能力评价",
            "communication_evaluation": "沟通表达能力评价",
            "overall_score": 2.5,
            "recommendation": "强烈推荐/推荐/待定/不推荐",
            "strengths": ["优点 1", "优点 2"],
            "weaknesses": ["不足 1", "不足 2"],
            "overall_comment": "详细评语"
        }}
        """)

        # 综合评价生成器（多维度、多主题、分轮次）
        self.comprehensive_evaluation_prompt = ChatPromptTemplate.from_template("""
        你是资深技术面试官，请基于完整的面试过程生成 comprehensive 综合评价。

        岗位：{position}
        面试概况:
        - 总轮次：{total_rounds}轮
        - 时长：{duration_minutes:.1f}分钟
        - 涉及主题：{topics}

        要求：
        1. 所有评分量程（包括主评分和各子维度）均为 0-10 分。
        2. 如果 candidate 回答缺乏内容、逻辑混乱或重复，各维度评分应在 0-4 分之间。
        3. 严禁出现子维度分均为 0 但总分为 10 的逻辑错误。

        详细面试记录:
        {full_history}

        请从以下维度进行评价并输出 JSON 格式：
        {{
            "overall_score": 0-10,
            "technical_competency": 0-10,
            "communication_skill": 0-10,
            "problem_solving": 0-10,
            "depth_of_knowledge": 0-10,
            "topic_coverage": ["主题 1", "主题 2"],
            "strong_topics": ["掌握好的主题"],
            "weak_topics": ["需要加强的主题"],
            "strengths": ["优势 1", "优势 2"],
            "weaknesses": ["不足 1", "不足 2"],
            "suggestions": ["建议 1", "建议 2"],
            "technical_evaluation": "详细的技术能力评价（100-300 字）",
            "communication_evaluation": "详细的沟通能力评价（100-300 字）",
            "overall_comment": "综合点评（200-500 字，包含具体例子）",
            "recommendation": "强烈推荐/推荐/待定/不推荐",
            "confidence_level": "高/中/低",
            "round_evaluations": [
                {{
                    "round": 1,
                    "topic": "主题名",
                    "comment": "本轮点评（50-100 字，指出亮点和改进点）"
                }}
            ]
        }}
        """)

        # 岗位自动映射器
        self.category_mapping_prompt = ChatPromptTemplate.from_template("""
        你是一个专业的技术猎头。请根据候选人的简历内容，从给定的岗位类别列表中选择一个最匹配的。
        注意：如果简历内容与所有类别都不太匹配，请选择最接近的一个。

        可用岗位类别：{available_categories}

        简历内容：{resume_text}

        请只输出岗位类别的名称（例如：backend_engineer），不要有任何其他文字说明或标点符号。
        """)

        # 简历评估器（用于动态分配 10 道题的难度）
        self.resume_evaluation_prompt = ChatPromptTemplate.from_template("""
        你是一个资深技术总监。请根据候选人的简历（申请岗位：{position}），评估其技术水平，并为接下来的面试分配恰好 10 道题的难度比例。
        
        分配要求：
        - 总题数必须刚好是 10 道。
        - 难度分为：简单（easy）、中等（normal）、困难（hard）。
        - 初中级候选人：更多分配 easy 和 normal。
        - 高级/资深候选人：更多分配 normal 和 hard。
        
        简历内容：
        {resume_text}
        
        请只输出 JSON 格式，不要包含 Markdown 标记或其他多余字符，格式如下：
        {{
            "easy": 4,
            "normal": 4,
            "hard": 2
        }}
        """)

        # 押题生成器 (10道题，专为流式设计，动态难度分配)
        self.streaming_predict_questions_prompt = ChatPromptTemplate.from_template("""
        你是一个资深面试专家。请根据候选人的简历、指定的岗位、岗位知识库和历史问题，为候选人生成 10 道面试“押题”。
        
        本次面试的难度分配已决定如下：
        - 简单题：{easy_count} 道（侧重基础概念、语法和核心工具的使用）
        - 中等题：{normal_count} 道（侧重实际场景应用、常见框架原理和组件封装）
        - 困难题：{hard_count} 道（侧重底层源码分析、系统架构设计、性能优化和复杂并发问题）
        
        要求：
        1. 题目分三个梯度递进，必须严格按此顺序输出：简单题 -> 中等题 -> 困难题，共 10 道。
        2. 题目必须紧扣简历中的技术点和指定的岗位需求。
        
        【重要格式要求】
        为了方便系统实时解析，请务必严格按照以下标记格式输出每一道题。每道题独立成块，题目之间留空行。
        绝不要输出任何 JSON 或者 Markdown 代码块（如 ```json等），只需纯文本。
        
        【内容长度限制】
        由于系统限制，每一题必须极度精简！
        - [题目]：一句话概括。
        - [要点]：仅列出2-3个核心关键词。
        - [答案]：控制在 50-80 字以内，点到即止，切忌长篇大论。
        
        格式模板：
        [题目] 具体的题目内容
        [要点] 关键词1, 关键词2
        [答案] 简明扼要的答案，50字左右
        [难度] 简单/中等/困难

        参考知识：
        {kb_context}

        参考历史题：
        {qb_context}

        指定岗位：
        {position}

        候选人简历：
        {resume_text}
        
        请直接开始输出第一道题，不要寒暄。
        """)

        # 技术点卡片生成器（用于综合评价中的技术点展示）
        self.technical_cards_prompt = ChatPromptTemplate.from_template("""
        你是一个资深技术面试官，请基于面试对话历史，提取关键的技术点并生成用于前端展示的技术点卡片数据。

        岗位：{position}
        面试对话历史：
        {conversation_history}

        请按照以下要求提取和生成技术点卡片：
        1. 从对话历史中提取所有涉及的技术点（如编程语言、框架、工具、概念等）
        2. 将技术点分为两类：
           - 已掌握的技术点（候选人表现出较好理解的部分）
           - 待提升的技术点（候选人理解不足或需要加强的部分）
        3. 为每个技术点生成简要描述和详细解析
        4. 评估每个技术点的相关度（0.0-1.0，基于对话中提及的频率和深度）

        输出严格的JSON格式：
        {{
            "technical_cards": [
                {{
                    "id": 1,
                    "title": "技术点名称",
                    "type": "mastered" 或 "needs_improvement",
                    "brief_description": "简短描述（1-2句话）",
                    "detailed_explanation": "详细解析（3-5句话，包含：定义、重要性、候选人表现、学习建议）",
                    "relevance_score": 0.0-1.0,
                    "category": "技术类别（如：后端开发、前端开发、数据库等）"
                }}
            ],
            "technical_summary": {{
                "total_cards": 总数,
                "mastered_count": 已掌握数量,
                "needs_improvement_count": 待提升数量,
                "primary_technology": "主要技术栈"
            }}
        }}

        注意：
        1. 技术点数量控制在8-15个之间
        2. 确保技术点具体明确，避免过于宽泛
        3. 详细解析要实用，能帮助候选人理解该技术点
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

    async def generate_initial_question(self, resume: str, position: str, difficulty: str = "Normal") -> str:
        """生成初始问题"""
        factors = {"Easy": 0.5, "Normal": 1.0, "Hard": 1.5}
        factor = factors.get(difficulty, 1.0)
        retrieval_query = f"{resume} {position} 基础问题 难度{factor}"
        questions_text = self.retrieve_questions(retrieval_query, k=5)

        chain = self.initial_question_prompt | DeepSeek_LLM | StrOutputParser()
        question = await chain.ainvoke({
            "resume": resume,
            "position": position,
            "questions": questions_text,
            "difficulty_factor": factor
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

    async def analyze_answer_depth(self, question: str, answer: str, difficulty: str = "Normal", emotion_data: Optional[Dict] = None) -> dict:
        """分析回答深度 (支持语音情感数据)"""
        knowledge = self.retrieve_knowledge(f"{question} {answer}", k=3)
        
        standards = {
            "Easy": "要求较低，只要答对核心概念即可给高分（7.5分及以上视为达标）",
            "Normal": "要求标准，需要有一定逻辑和细节（8.5分及以上视为达标）",
            "Hard": "要求严苛，必须深入底层原理，且逻辑完美（9.0分及以上视为达标）"
        }
        scoring_standard = standards.get(difficulty, standards["Normal"])

        if emotion_data:
            # 使用语音专用的评估提示词
            chain = self.voice_answer_depth_analyzer_prompt | DeepSeek_LLM | StrOutputParser()
            input_data = {
                "question": question,
                "answer": answer,
                "knowledge_base": knowledge,
                "difficulty": difficulty,
                "scoring_standard": scoring_standard,
                "emotion_data": json.dumps(emotion_data, ensure_ascii=False)
            }
        else:
            # 使用标准文本评估提示词
            chain = self.answer_depth_analyzer_prompt | DeepSeek_LLM | StrOutputParser()
            input_data = {
                "question": question,
                "answer": answer,
                "knowledge_base": knowledge,
                "difficulty": difficulty,
                "scoring_standard": scoring_standard
            }

        result = await chain.ainvoke(input_data)

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
                                     history: str, difficulty: str = "Normal") -> str:
        """生成下一个问题"""
        factors = {"Easy": 0.5, "Normal": 1.0, "Hard": 1.5}
        factor = factors.get(difficulty, 1.0)
        chain = self.next_topic_prompt | DeepSeek_LLM | StrOutputParser()
        question = await chain.ainvoke({
            "resume": resume,
            "position": position,
            "completed_topics": ", ".join(completed_topics),
            "history": history,
            "difficulty_factor": factor
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
                    "overall_comment": result[:500]
                }
        except:
            evaluation = {
                "technical_evaluation": "评价生成失败",
                "communication_evaluation": "评价生成失败",
                "overall_score": 0,
                "recommendation": "待定",
                "strengths": [],
                "weaknesses": [],
                "overall_comment": result[:500]
            }

        return evaluation

    async def generate_technical_cards(self, position: str, conversation_history: List[Dict]) -> dict:
        """生成技术点卡片数据，用于前端展示"""
        # 构建对话历史文本
        full_history = "\n".join([
            f"第{qa.get('round', i+1)}轮 - 主题：{qa.get('topic', '未知')}\n"
            f"问：{qa.get('question', '')}\n"
            f"答：{qa.get('answer', '')}"
            for i, qa in enumerate(conversation_history)
        ])

        chain = self.technical_cards_prompt | DeepSeek_LLM | StrOutputParser()
        result = await chain.ainvoke({
            "position": position,
            "conversation_history": full_history
        })

        # 解析JSON结果
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                technical_data = json.loads(json_match.group())
            else:
                technical_data = {
                    "technical_cards": [],
                    "technical_summary": {
                        "total_cards": 0,
                        "mastered_count": 0,
                        "needs_improvement_count": 0,
                        "primary_technology": "未知"
                    }
                }
        except Exception as e:
            print(f"解析技术点卡片数据失败: {e}, 原始结果: {result[:200]}")
            technical_data = {
                "technical_cards": [],
                "technical_summary": {
                    "total_cards": 0,
                    "mastered_count": 0,
                    "needs_improvement_count": 0,
                    "primary_technology": "未知"
                }
            }

        return technical_data

    async def generate_comprehensive_evaluation(
        self, 
        position: str,
        conversation_history: List[Dict],
        total_rounds: int,
        duration_minutes: float
    ) -> dict:
        """生成 comprehensive 综合评价（多维度、多主题、分轮次）"""
        
        # 提取所有主题
        topics = list(set([q.get('topic', '未知') for q in conversation_history]))
        
        # 构建详细的面试历史记录
        full_history = "\n\n".join([
            f"第{qa.get('round', i+1)}轮 - 主题：{qa.get('topic', '未知')}\n"
            f"问：{qa.get('question', '')}\n"
            f"答：{qa.get('answer', '')}"
            for i, qa in enumerate(conversation_history)
        ])
        
        # 使用 LCEL 链式调用（与现有代码风格一致）
        chain = self.comprehensive_evaluation_prompt | DeepSeek_LLM | StrOutputParser()
        
        result = await chain.ainvoke({
            "position": position,
            "total_rounds": total_rounds,
            "duration_minutes": duration_minutes,
            "topics": ", ".join(topics),
            "full_history": full_history
        })
        
        # 解析 JSON 结果（与现有代码相同的解析逻辑）
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                llm_evaluation = json.loads(json_match.group())
            else:
                llm_evaluation = {}
        except:
            llm_evaluation = {}
        
        # 计算基础统计数据用于补充评分
        round_scores = []
        last_answer = ""
        for qa in conversation_history:
            answer = qa.get('answer', '').strip()
            answer_length = len(answer)
            
            # 检测复读机行为（如果本次回答与上次高度相似，或者字数极少）
            is_repetitive = (answer == last_answer) and answer_length > 0
            is_empty_or_too_short = answer_length < 10
            
            has_technical_terms = any(term in answer.lower() 
                                    for term in ['java', 'android', 'api', 'code', 'system', 'data', 'spring', 'vue'])
            
            # 基础分降低，严厉打击低质量回答
            base_score = 1.0
            if is_repetitive:
                base_score = 0.5
            elif is_empty_or_too_short:
                base_score = 0.2

            technical_score = min(10, max(base_score, (answer_length / 100) + (1.5 if has_technical_terms else 0)))
            if is_repetitive:
                technical_score *= 0.5

            depth_score = min(10, max(base_score, (answer_length / 150) + 1.0))
            clarity_score = min(10, max(base_score, 3.0 + (1.0 if "\n" in answer else 0)))
            
            round_scores.append({
                "round": qa.get('round', 1),
                "topic": qa.get('topic', '未知'),
                "technical_score": round(technical_score, 1),
                "depth_score": round(depth_score, 1),
                "clarity_score": round(clarity_score, 1)
            })
            last_answer = answer
        
        # 合并 LLM 评价和计算评分（自动检测百分制并修正）
        avg_technical = sum([r['technical_score'] for r in round_scores]) / len(round_scores) if round_scores else 0
        
        raw_overall = float(llm_evaluation.get("overall_score", avg_technical))
        # 修正百分制 bug：如果分值 > 10，自动视为百分制并压缩
        overall_score = raw_overall / 10.0 if raw_overall > 10 else raw_overall
        
        raw_tech_comp = float(llm_evaluation.get("technical_competency", avg_technical))
        technical_competency = raw_tech_comp / 10.0 if raw_tech_comp > 10 else raw_tech_comp

        # 生成技术点卡片数据
        technical_cards_data = {}
        try:
            technical_cards_data = await self.generate_technical_cards(position, conversation_history)
        except Exception as e:
            print(f"生成技术点卡片数据失败: {e}")
            technical_cards_data = {
                "technical_cards": [],
                "technical_summary": {
                    "total_cards": 0,
                    "mastered_count": 0,
                    "needs_improvement_count": 0,
                    "primary_technology": "未知"
                }
            }

        comprehensive_result = {
            "overall_score": round(overall_score, 1),
            "technical_competency": round(technical_competency, 1),
            "communication_skill": float(llm_evaluation.get("communication_skill", 5.0)),
            "problem_solving": float(llm_evaluation.get("problem_solving", 5.0)),
            "depth_of_knowledge": float(llm_evaluation.get("depth_of_knowledge", 5.0)),
            "topic_coverage": llm_evaluation.get("topic_coverage", topics),
            "strong_topics": llm_evaluation.get("strong_topics", []),
            "weak_topics": llm_evaluation.get("weak_topics", []),
            "strengths": llm_evaluation.get("strengths", ["面试表现良好"]),
            "weaknesses": llm_evaluation.get("weaknesses", ["仍有提升空间"]),
            "suggestions": llm_evaluation.get("suggestions", ["继续深入学习相关知识"]),
            "technical_evaluation": llm_evaluation.get("technical_evaluation", "技术能力评价"),
            "communication_evaluation": llm_evaluation.get("communication_evaluation", "沟通能力评价"),
            "overall_comment": llm_evaluation.get("overall_comment", "综合评价"),
            "recommendation": llm_evaluation.get("recommendation", "待定"),
            "confidence_level": llm_evaluation.get("confidence_level", "中"),
            "round_evaluations": llm_evaluation.get("round_evaluations", []),
            "total_rounds": total_rounds,
            "duration_minutes": round(duration_minutes, 1),
            # 合并技术点卡片数据
            "technical_cards": technical_cards_data.get("technical_cards", []),
            "technical_summary": technical_cards_data.get("technical_summary", {
                "total_cards": 0,
                "mastered_count": 0,
                "needs_improvement_count": 0,
                "primary_technology": "未知"
            })
        }

        return comprehensive_result

    async def match_resume_to_collection(self, resume_text: str) -> str:
        """根据简历内容自动匹配现有的向量库集合"""
        # 后续可以改为从 chroma_db 目录动态读取，目前先手动指定可用岗位
        available_categories = ["backend_engineer", "android_engineer"]
        
        chain = self.category_mapping_prompt | DeepSeek_LLM | StrOutputParser()
        result = await chain.ainvoke({
            "available_categories": ", ".join(available_categories),
            "resume_text": resume_text[:2000]  # 防止简历过长
        })
        
        # 简单清理结果
        mapped_category = result.strip().lower()
        if mapped_category not in available_categories:
            # 如果没匹配上，默认返回第一个
            return available_categories[0]
            
        return mapped_category

    async def stream_predict_interview_questions(self, resume_text: str, position: str):
        """流式生成 10 道预测题 (动态评估难度)"""
        # 0. 评估简历，获取难度分配
        eval_chain = self.resume_evaluation_prompt | DeepSeek_LLM | StrOutputParser()
        eval_result = await eval_chain.ainvoke({
            "position": position,
            "resume_text": resume_text[:2000] # 截断避免超长
        })
        
        easy_count, normal_count, hard_count = 4, 4, 2 # 默认值
        try:
            # 清理可能的 markdown
            import re
            json_str = eval_result
            json_match = re.search(r'\{.*\}', eval_result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            distribution = json.loads(json_str)
            easy_count = int(distribution.get("easy", 4))
            normal_count = int(distribution.get("normal", 4))
            hard_count = int(distribution.get("hard", 2))
            
            # 确保总和为 10
            total = easy_count + normal_count + hard_count
            if total != 10:
                easy_count, normal_count, hard_count = 4, 4, 2
        except Exception as e:
            print(f"Error parsing resume evaluation: {e}, Raw: {eval_result}")
        
        # 1. 检索相关背景知识
        kb_context = self.retrieve_knowledge(resume_text[:500], k=10)
        # 2. 检索历史题目参考
        qb_context = self.retrieve_questions(resume_text[:500], k=10)
        
        # 3. 准备流式调用链
        chain = self.streaming_predict_questions_prompt | DeepSeek_LLM | StrOutputParser()
        
        # 用于缓存流式文本，便于按块截断解析
        buffer = ""
        question_count = 0
        
        # 4. 执行流式生成
        async for chunk in chain.astream({
            "easy_count": easy_count,
            "normal_count": normal_count,
            "hard_count": hard_count,
            "kb_context": kb_context,
            "qb_context": qb_context,
            "position": position,
            "resume_text": resume_text
        }):
            buffer += chunk
            
            # 简单的基于关键字的状态机解析
            # 寻找一个完整的区块：包含 [题目], [要点], [答案], [难度]，并且已经遇到了下一个 [题目] 或到达终点（这比较难流式判断）
            # 改进策略：尝试匹配单个块。如果能在 buffer 中解析出一个完整的块信息，提取后清空那部分 buffer。
            
            while "[题目]" in buffer and "[要点]" in buffer and "[答案]" in buffer and "[难度]" in buffer:
                # 定位当前块的起点和终点要素
                q_idx = buffer.find("[题目]")
                p_idx = buffer.find("[要点]", q_idx)
                a_idx = buffer.find("[答案]", p_idx)
                d_idx = buffer.find("[难度]", a_idx)
                
                # 寻找下一个题目的起点作为当前题目的终点界限
                next_q_idx = buffer.find("[题目]", d_idx)
                
                # 如果没找到下一个 [题目]，说明当前这个题目的 [难度] 部分不一定输出完了（大模型还在生成字符）
                # 只有当找到了下一个 [题目]，或者虽然没找到 [题目] 但是 buffer 长效没变化（通常最后一块不好靠这个判断），我们才安全提取。
                # 为了流式顺畅，我们只要 [难度] 后面出现了换行符，就认为这一题结束了。
                
                end_idx = -1
                if next_q_idx != -1:
                    end_idx = next_q_idx
                else:
                    # 尝试寻找 [难度] 行的末尾
                    newline_after_d = buffer.find("\n", d_idx)
                    if newline_after_d != -1 and len(buffer) > newline_after_d + 1:
                        # 给点缓冲区确保确实写完了
                        end_idx = newline_after_d + 1
                        
                if end_idx != -1:
                    # 提取区块
                    block = buffer[q_idx:end_idx]
                    
                    # 截断 Buffer
                    buffer = buffer[end_idx:]
                    
                    # 提取具体字段
                    question_count += 1
                    
                    q_text = block[block.find("[题目]")+4 : block.find("[要点]")].strip()
                    p_text = block[block.find("[要点]")+4 : block.find("[答案]")].strip()
                    a_text = block[block.find("[答案]")+4 : block.find("[难度]")].strip()
                    d_text = block[block.find("[难度]")+4 :].strip()
                    
                    # 清理可能携带的多余换行
                    d_text = d_text.split('\n')[0].strip()
                    
                    yield {
                        "id": question_count,
                        "question": q_text,
                        "key_points": p_text,
                        "answer": a_text,
                        "difficulty": d_text
                    }
                else:
                    break # 当前块还不完整，等下一批 chunk

        # 处理最后一个残留在 buffer 中的题目 (如果正常没被 flush 掉的话)
        if "[题目]" in buffer and "[要点]" in buffer and "[答案]" in buffer and "[难度]" in buffer:
            q_idx = buffer.find("[题目]")
            p_idx = buffer.find("[要点]")
            a_idx = buffer.find("[答案]")
            d_idx = buffer.find("[难度]")
            
            question_count += 1
            
            q_text = buffer[q_idx+4 : p_idx].strip()
            p_text = buffer[p_idx+4 : a_idx].strip()
            a_text = buffer[a_idx+4 : d_idx].strip()
            d_text = buffer[d_idx+4 :].strip()
            
            yield {
                "id": question_count,
                "question": q_text,
                "key_points": p_text,
                "answer": a_text,
                "difficulty": d_text
            }
