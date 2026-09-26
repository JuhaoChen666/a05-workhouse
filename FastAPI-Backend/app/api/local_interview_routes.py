"""Small local interview contract used when the resume-only app is running.

The full interview service needs external AI/database infrastructure.  The
local app still exposes the same frontend contract so navigation and manual
UI testing do not turn optional interview data into 404s.
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.infrastructure.resume_runtime import session_factory
from app.models.session_models import (
    ChatHistoryModel,
    InterviewEvaluationModel,
    SessionModel,
)


router = APIRouter(prefix="/api/interview", tags=["本机面试兼容接口"])
SESSIONS: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def envelope(data: Any) -> dict[str, Any]:
    return {"code": 200, "message": "success", "data": data}


def session_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "session_id",
            "user_id",
            "status",
            "total_rounds",
            "current_topic",
            "current_question",
            "history",
            "interview_mode",
            "created_at",
            "started_at",
        )
        if key in row
    }


class StartRequest(BaseModel):
    resume: str | None = None
    resume_id: int | None = None
    position: str = "通用软件工程师"
    collection_name: str | None = None
    user_id: str | int | None = None
    difficulty: str | None = "medium"
    interview_mode: str | None = "text"


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class AvatarStartRequest(BaseModel):
    session_id: str
    avatar_id: str = "110592024"


class AvatarRefreshRequest(BaseModel):
    session_id: str
    avatar_session_id: str


class AvatarSpeakRequest(BaseModel):
    session_id: str
    text: str
    interrupt: bool = True


class PredictRequest(BaseModel):
    resume_id: int
    position: str


def get_session(session_id: str) -> dict[str, Any] | None:
    return SESSIONS.get(session_id)


async def load_persisted_session(session_id: str) -> dict[str, Any] | None:
    """Expose the durable interview history to the lightweight local UI adapter."""
    async with session_factory()() as db:
        row = await db.scalar(select(SessionModel).where(SessionModel.session_id == session_id))
        if row is None:
            return None
        history = list((await db.execute(
            select(ChatHistoryModel)
            .where(ChatHistoryModel.session_id == session_id)
            .order_by(ChatHistoryModel.round, ChatHistoryModel.id)
        )).scalars())
        evaluation = await db.scalar(
            select(InterviewEvaluationModel)
            .where(InterviewEvaluationModel.session_id == session_id)
            .order_by(InterviewEvaluationModel.created_at.desc())
        )
        evaluation_data = evaluation.evaluation_json if evaluation and isinstance(evaluation.evaluation_json, dict) else {}
        return {
            "session_id": row.session_id,
            "user_id": str(row.user_id) if row.user_id is not None else "",
            "status": row.status or "ended",
            "total_rounds": len(history),
            "current_topic": row.current_topic or "",
            "current_question": row.current_question or "",
            "history": [
                {
                    "round": item.round,
                    "question": item.question or "",
                    "answer": item.answer or "",
                    "topic": item.topic or "",
                    "emotion": item.emotion,
                    "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                }
                for item in history
            ],
            "interview_mode": "text",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "started_at": row.created_at.isoformat() if row.created_at else None,
            "position": row.position or "",
            "answer_count": len(history),
            "evaluation": {
                **evaluation_data,
                "session_id": session_id,
                "overall_score": evaluation.overall_score if evaluation else 0,
                "technical_competency": evaluation.technical_competency if evaluation else 0,
                "communication_skill": evaluation.communication_skill if evaluation else 0,
                "problem_solving": evaluation.problem_solving if evaluation else 0,
                "depth_of_knowledge": evaluation.depth_of_knowledge if evaluation else 0,
            },
        }


def event(event_type: str, data: dict[str, Any]) -> str:
    return json.dumps(
        {"type": event_type, "data": data, "timestamp": now_iso()},
        ensure_ascii=False,
    ) + "\n"


async def stream_events(items: list[str]):
    for item in items:
        yield item


@router.post("/start")
async def start_interview(request: StartRequest):
    session_id = str(uuid4())
    position = request.position.strip() or "通用软件工程师"
    row = {
        "session_id": session_id,
        "user_id": str(request.user_id) if request.user_id is not None else "1",
        "status": "questioning",
        "total_rounds": 3,
        "current_topic": "项目经历",
        "current_question": f"请介绍一个与你应聘的「{position}」相关的项目，以及你在其中承担的职责。",
        "history": [],
        "interview_mode": request.interview_mode or "text",
        "created_at": now_iso(),
        "started_at": now_iso(),
        "position": position,
        "answer_count": 0,
    }
    SESSIONS[session_id] = row
    return envelope(session_public(row))


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    row = get_session(session_id)
    if row is None:
        row = await load_persisted_session(session_id)
    if row is None:
        return envelope({
            "session_id": session_id,
            "status": "ended",
            "total_rounds": 0,
            "current_topic": "",
            "current_question": "",
            "history": [],
        })
    return envelope(session_public(row))


@router.get("/session/{session_id}/evaluation")
async def get_evaluation(session_id: str):
    row = get_session(session_id)
    if row is None:
        row = await load_persisted_session(session_id)
    if row and row.get("evaluation"):
        return envelope(row["evaluation"])
    return envelope({
        "session_id": session_id,
        "strengths": ["能够围绕项目经历进行表达"],
        "weaknesses": [] if row and row["answer_count"] else ["尚未完成足够轮次的回答"],
        "suggestions": ["补充可量化的项目结果和技术取舍"],
        "strong_topics": ["项目经历"] if row and row["answer_count"] else [],
        "weak_topics": [] if row and row["answer_count"] else ["项目深挖"],
        "topic_coverage": ["项目经历"],
        "round_evaluations": [],
        "total_rounds": row["answer_count"] if row else 0,
        "overall_score": 75 if row and row["answer_count"] else 0,
        "technical_competency": 7,
        "communication_skill": 7,
        "problem_solving": 7,
        "depth_of_knowledge": 6,
        "recommendation": "继续补充更多回答后查看完整评估",
        "overall_comment": "这是本机联调模式的基础评估数据。",
        "technical_evaluation": "本机联调模式未连接外部 AI。",
        "communication_evaluation": "回答接口已连通。",
    })


@router.get("/session/{session_id}/evaluation/radar")
async def get_radar(session_id: str):
    row = get_session(session_id)
    if row is None:
        row = await load_persisted_session(session_id)
    if row and row.get("evaluation"):
        evaluation = row["evaluation"]
        values = [
            evaluation.get("technical_competency", 0),
            evaluation.get("communication_skill", 0),
            evaluation.get("problem_solving", 0),
            evaluation.get("depth_of_knowledge", 0),
            evaluation.get("overall_score", 0),
        ]
    else:
        values = [70, 70, 70, 65, 75]
    return envelope({
        "indicator": [
            {"name": "技术能力", "max": 100},
            {"name": "沟通表达", "max": 100},
            {"name": "问题解决", "max": 100},
            {"name": "知识深度", "max": 100},
            {"name": "综合表现", "max": 100},
        ],
        "value": values,
        "series": [{"value": values}],
    })


@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    row = get_session(session_id)
    if row:
        row["status"] = "ended"
    else:
        async with session_factory()() as db:
            persisted = await db.scalar(select(SessionModel).where(SessionModel.session_id == session_id))
            if persisted:
                persisted.status = "ended"
                await db.commit()
    return envelope({"session_id": session_id, "status": "ended"})


@router.get("/user/{user_id}/sessions")
async def user_sessions(user_id: str):
    rows = [
        {
            "session_id": row["session_id"],
            "position": row["position"],
            "position_name": row["position"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["created_at"],
        }
        for row in SESSIONS.values()
        if str(row["user_id"]) == str(user_id)
    ]
    async with session_factory()() as db:
        persisted = list((await db.execute(
            select(SessionModel)
            .where(SessionModel.user_id == int(user_id))
            .order_by(SessionModel.created_at.desc())
        )).scalars())
    known = {row["session_id"] for row in rows}
    rows.extend(
        {
            "session_id": row.session_id,
            "position": row.position or "",
            "position_name": row.position or "",
            "status": row.status or "ended",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in persisted
        if row.session_id not in known
    )
    rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return envelope(rows)


@router.get("/user/{user_id}/sessions/page")
async def user_sessions_page(user_id: str, page: int = 1, page_size: int = 10, pageSize: int | None = None):
    size = pageSize or page_size
    rows = (await user_sessions(user_id))["data"]
    start = max(0, page - 1) * size
    return envelope({"list": rows[start:start + size], "total": len(rows), "page": page, "pageSize": size})


@router.get("/user/{user_id}/evaluation/trend")
async def user_trend(user_id: str):
    async with session_factory()() as db:
        evaluations = list((await db.execute(
            select(InterviewEvaluationModel)
            .where(InterviewEvaluationModel.user_id == int(user_id))
            .order_by(InterviewEvaluationModel.created_at.desc())
            .limit(5)
        )).scalars())
    if evaluations:
        return envelope({
            "xAxis": {"type": "category", "data": [
                item.created_at.strftime("%Y-%m-%d") for item in reversed(evaluations)
            ]},
            "yAxis": {"type": "value"},
            "series": [{
                "data": [item.overall_score for item in reversed(evaluations)],
                "type": "line",
                "smooth": True,
            }],
        })
    return envelope({
        "xAxis": {"type": "category", "data": []},
        "yAxis": {"type": "value"},
        "series": [{"data": [], "type": "line", "smooth": True}],
    })


@router.post("/avatar/session/start")
async def start_avatar(request: AvatarStartRequest):
    return envelope({
        "session_id": request.session_id,
        "avatar_session_id": f"local-{uuid4()}",
        "vendor": "local",
        "avatar_id": request.avatar_id,
        "sdk_config": {
            "app_id": "local",
            "server_url": "",
            "signed_url": "",
            "scene_id": "local",
            "vcn": "local",
            "protocol": "xrtc",
            "alpha": 0,
            "token": "local",
            "expire_at": 4102444800,
        },
    })


@router.post("/avatar/session/refresh")
async def refresh_avatar(request: AvatarRefreshRequest):
    return envelope({"session_id": request.session_id, "avatar_session_id": request.avatar_session_id,
                     "sdk_config": {"token": "local", "expire_at": 4102444800}})


@router.post("/avatar/speak")
async def speak_avatar(request: AvatarSpeakRequest):
    return envelope({"accepted": True, "task_id": str(uuid4())})


@router.delete("/avatar/session/{session_id}")
async def end_avatar(session_id: str):
    return envelope({"session_id": session_id, "status": "ended"})


@router.post("/answer")
async def answer(request: AnswerRequest):
    row = get_session(request.session_id)
    if row is None:
        return StreamingResponse(stream_events([event("error", {"message": "面试会话不存在"})]),
                                 media_type="application/x-ndjson")
    answer = request.answer.strip()
    row["answer_count"] += 1
    row["history"].append({
        "round": row["answer_count"],
        "question": row["current_question"],
        "answer": answer,
        "topic": row["current_topic"],
        "timestamp": now_iso(),
    })
    if row["answer_count"] >= row["total_rounds"]:
        row["status"] = "completed"
        next_question = ""
    else:
        next_question = "请进一步说明这个方案的技术取舍，以及你如何验证最终效果。"
        row["current_question"] = next_question
    return StreamingResponse(stream_events([
        event("analyzing", {"message": "本机联调模式正在整理回答"}),
        event("analysis_result", {"feedback": "回答已收到", "depth_score": 7, "is_vague": False, "need_followup": False}),
        event("question", {"question": next_question, "topic": row["current_topic"]}),
        event("interview_complete", {}) if row["status"] == "completed" else event("followup", {"question": next_question}),
    ]), media_type="application/x-ndjson")


@router.post("/answer-voice")
async def answer_voice(session_id: str = Form(...), file: UploadFile = File(...)):
    await file.read()
    return await answer(AnswerRequest(session_id=session_id, answer="语音回答（本机联调模式）"))


@router.post("/opening-stream")
async def opening_stream(request: dict[str, str]):
    row = get_session(request.get("session_id", ""))
    question = row["current_question"] if row else "请介绍一下你的项目经历。"
    return StreamingResponse(stream_events([
        event("question_chunk", {"text": question}),
        event("question", {"question": question}),
    ]), media_type="application/x-ndjson")


@router.post("/predict-questions/stream")
async def predict_questions(request: PredictRequest):
    questions = [
        f"请结合你的简历说明一个「{request.position}」项目中的技术难点。",
        "你如何验证方案的稳定性、性能和可维护性？",
        "如果重新设计这个项目，你会优先改进哪些地方？",
    ]
    items = [
        event("prediction_item", {
            "id": index,
            "question": question,
            "key_points": "背景、方案、结果、复盘",
            "answer": "请结合自己的实际经历组织回答。",
            "difficulty": "medium",
        })
        for index, question in enumerate(questions, 1)
    ]
    items.append(event("prediction_complete", {"count": len(questions)}))
    return StreamingResponse(stream_events(items), media_type="application/x-ndjson")
