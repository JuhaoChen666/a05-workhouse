"""In-memory local fallback for the legacy resume optimization screen."""

from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response


router = APIRouter(prefix="/api/resume/optimize", tags=["本机简历优化兼容接口"])
TASKS: dict[str, dict[str, str | int]] = {}


@router.post("/import")
async def import_resume(user_id: int = Form(...), file: UploadFile = File(...)):
    content = await file.read()
    session_id = str(uuid4())
    text = f"# {file.filename or '我的简历'}\n\n本机已接收简历文件，共 {len(content)} 字节。"
    TASKS[session_id] = {"user_id": user_id, "progress": 100, "status": "completed", "result": text}
    return {"code": 200, "message": "简历上传并解析成功", "data": {"session_id": session_id, "text_preview": text}}


@router.post("/{session_id}")
async def start_optimization(session_id: str, target_job: str = Form("IT工程师")):
    task = TASKS.get(session_id)
    if task is None:
        return {"code": 404, "message": "任务不存在", "data": None}
    task["status"] = "completed"
    task["progress"] = 100
    return {"code": 200, "message": "本机优化已完成", "data": {"session_id": session_id}}


@router.get("/status/{session_id}")
async def optimization_status(session_id: str):
    task = TASKS.get(session_id)
    if task is None:
        return {"code": 404, "message": "任务不存在", "data": None}
    return {"code": 200, "message": "success", "data": {
        "session_id": session_id,
        "progress": task["progress"],
        "status": task["status"],
        "result_markdown": task["result"],
    }}


@router.get("/export/{session_id}")
async def export_optimization(session_id: str):
    task = TASKS.get(session_id)
    if task is None:
        return Response(content="任务不存在", status_code=404, media_type="text/plain")
    html = f"<html><body><pre>{task['result']}</pre></body></html>"
    return Response(content=html, media_type="text/html",
                    headers={"Content-Disposition": f'inline; filename="optimized_resume_{session_id[:8]}.html"'})
