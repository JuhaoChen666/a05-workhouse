from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey, BigInteger
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
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 建立与聊天历史的一对多关系，方便级联或查询
    history_records = relationship("ChatHistoryModel", back_populates="session", cascade="all, delete-orphan", lazy="selectin")

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
