import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.interview_models import InterviewStartRequest, InterviewAnswerRequest
from app.RAG.interview_service import InterviewService

router = APIRouter(prefix="/api/interview", tags=["面试"])

# 创建服务实例（可以考虑使用依赖注入）
interview_service = InterviewService()


@router.post("/start")
async def start_interview(request: InterviewStartRequest):
    """开始面试"""
    try:
        # 开始面试
        result = interview_service.start_interview(
            request.resume,
            request.position,
            request.collection_name
        )

        session_id = result["session_id"]

        # 初始化第一个问题
        question = await interview_service.initialize_session_question(session_id)

        # 获取会话信息
        session_info = interview_service.get_session_info(session_id)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "session_id": session_id,
                "question": question,
                "topic": session_info["current_topic"],
                "round": 1,
                "status": "questioning",
                "db_info": result["db_info"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer")
async def submit_answer(request: InterviewAnswerRequest):
    """提交回答并获取流式响应"""

    async def generate():
        try:
            async for event in interview_service.process_answer(request.session_id, request.answer):
                # 将事件转换为JSON字符串并发送
                yield json.dumps(event.dict(), ensure_ascii=False) + "\n"
            
            # 为防止Apifox或Node底层客户端在TCP断开时丢弃缓冲区最后一个有效块
            # 我们在这里发送连续的空白换行和占位符顶出真正的数据帧
            yield "      \n\n"
            await asyncio.sleep(0.5)
        except Exception as e:
            raise e

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    session_info = interview_service.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "code": 200,
        "message": "success",
        "data": session_info
    }


@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """结束会话"""
    interview_service.end_session(session_id)
    return {
        "code": 200,
        "message": "会话已结束"
    }