import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends
from fastapi.responses import StreamingResponse
from app.models.interview_models import InterviewStartRequest, InterviewAnswerRequest
from app.RAG.interview_service import InterviewService

router = APIRouter(prefix="/api/interview", tags=["面试"])

def get_interview_service(request: Request) -> InterviewService:
    return request.app.state.interview_service


@router.post("/answer-voice")
async def submit_voice_answer(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    interview_service: InterviewService = Depends(get_interview_service)
):
    """提交语音回答并获取流式响应"""
    
    async def generate():
        try:
            # 读取文件字节内容
            audio_bytes = await file.read()
            
            async for event in interview_service.process_voice_answer(session_id, audio_bytes):
                # 将事件转换为JSON字符串并发送
                yield json.dumps(event.dict(), ensure_ascii=False) + "\n"
            
            # 发送占位符顶出数据帧
            yield "      \n\n"
            await asyncio.sleep(0.5)
        except Exception as e:
            # 在生成器中产生错误事件
            yield json.dumps({
                "type": "error",
                "data": {"message": str(e)},
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/start")
async def start_interview(
    request: InterviewStartRequest,
    interview_service: InterviewService = Depends(get_interview_service)
):
    """开始面试"""
    try:
        # 开始面试
        result = await interview_service.start_interview(
            request.resume,
            request.position,
            request.collection_name
        )

        session_id = result["session_id"]

        # 初始化第一个问题
        question = await interview_service.initialize_session_question(session_id)

        # 获取会话信息
        session_info = await interview_service.get_session_info(session_id)

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
async def submit_answer(
    request: InterviewAnswerRequest,
    interview_service: InterviewService = Depends(get_interview_service)
):
    """提交回答并获取流式响应"""

    async def generate():
        try:
            async for event in interview_service.process_answer(request.session_id, request.answer):
                # 将事件转换为JSON字符串并发送
                yield json.dumps(event.dict(), ensure_ascii=False) + "\n"
            
            yield "      \n\n"
            await asyncio.sleep(0.5)
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield json.dumps({
                "type": "error",
                "data": {"message": f"系统内部错误: {str(e)}"},
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    interview_service: InterviewService = Depends(get_interview_service)
):
    """获取会话信息"""
    session_info = await interview_service.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "code": 200,
        "message": "success",
        "data": session_info
    }


@router.delete("/session/{session_id}")
async def end_session(
    session_id: str,
    interview_service: InterviewService = Depends(get_interview_service)
):
    """结束会话"""
    await interview_service.end_session(session_id)
    return {
        "code": 200,
        "message": "会话已结束"
    }

@router.get("/user/{user_id}/sessions")
async def get_user_sessions(user_id: int):
    """获取用户过往的历史面试会话记录"""
    from app.infrastructure.mapper.session_mapper import SessionMapper
    sessions = await SessionMapper.get_sessions_by_user_id(user_id)
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "session_id": s.session_id,
                "position": s.position,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            } for s in sessions
        ]
    }

@router.get("/session/{session_id}/evaluation")
async def get_comprehensive_evaluation(
    session_id: str,
    interview_service: InterviewService = Depends(get_interview_service)
):
    """获取已结束会话的综合评价报告（多维度、多主题、分轮次点评）"""
    try:
        # 先检查会话是否存在
        session_info = await interview_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 检查是否已结束
        if session_info.get("status") not in ["completed", "ended"]:
            raise HTTPException(
                status_code=400, 
                detail=f"面试尚未结束，当前状态：{session_info.get('status')}"
            )
        
        # 生成综合评价（使用 LCEL 方式）
        evaluation = await interview_service.generate_session_evaluation(session_id)
        
        return {
            "code": 200,
            "message": "success",
            "data": evaluation
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成评价失败：{str(e)}")
