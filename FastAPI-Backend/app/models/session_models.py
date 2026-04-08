from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey, BigInteger, FLOAT
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class SessionModel(Base):
    __tablename__ = 'interview_sessions'

    session_id = Column(String(36), primary_key=True)
    resume = Column(Text, nullable=True)
    position = Column(String(255), nullable=True)
    status = Column(String(50), default='initializing')
    user_id = Column(Integer, nullable=True)
    current_topic = Column(String(255), nullable=True)
    current_question = Column(Text, nullable=True)
    difficulty = Column(String(50), default='Normal')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 建立与聊天历史的一对多关系，方便级联或查询
    history_records = relationship("ChatHistoryModel", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    # 建立与评价的一对一关系
    evaluation = relationship("InterviewEvaluationModel", back_populates="session", uselist=False, cascade="all, delete-orphan", lazy="selectin")

class ChatHistoryModel(Base):
    __tablename__ = 'conversation_history'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('interview_sessions.session_id', ondelete='CASCADE'), nullable=False)
    round = Column(Integer, nullable=False)
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    topic = Column(String(255), nullable=True)
    emotion = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

    session = relationship("SessionModel", back_populates="history_records")

class InterviewEvaluationModel(Base):
    __tablename__ = 'interview_evaluations'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('interview_sessions.session_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, nullable=True)
    
    # 雷达图评分维度
    overall_score = Column(FLOAT, default=0.0)
    technical_competency = Column(FLOAT, default=0.0)
    communication_skill = Column(FLOAT, default=0.0)
    problem_solving = Column(FLOAT, default=0.0)
    depth_of_knowledge = Column(FLOAT, default=0.0)
    
    # 完整 JSON 数据
    evaluation_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("SessionModel", back_populates="evaluation")
