import os
import uuid
import aiofiles
import markdown
import pdfkit
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.database import get_db_session
from app.models.session_models import ResumeOptimizationModel
from app.utils.pdf_utils import extract_text_from_pdf
from app.RAG.resume_optimize_service import ResumeOptimizeService

router = APIRouter(prefix="/api/resume/optimize", tags=["AI简历优化"])

UPLOAD_DIR = "data/optimizations"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/import")
async def import_resume_for_optimization(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    第一步：上传待优化的简历。利用工具抽取为纯文本，并在库中开辟进度槽（session_id）。
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="目前仅支持抽取 PDF 格式的原版简历")

    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"optimize_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        text_content = extract_text_from_pdf(file_path)
        if not text_content or len(text_content.strip()) < 20:
            raise HTTPException(status_code=400, detail="解析出的文本过少或为空，请确保这是一个文字版的PDF而不是纯图片。")

        session_id = str(uuid.uuid4())
        new_record = ResumeOptimizationModel(
            session_id=session_id,
            user_id=user_id,
            original_text=text_content,
            progress=0,
            status="pending"
        )
        
        db.add(new_record)
        await db.commit()

        # 只要抽取成功了就可以扔掉临时文件
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "code": 200,
            "message": "简历上传并解析成功，请启动优化",
            "data": {
                "session_id": session_id,
                "text_preview": text_content[:150] + "..." if len(text_content) > 150 else text_content
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"导入处理失败: {str(e)}")

@router.post("/{session_id}")
async def start_optimization(
    session_id: str,
    background_tasks: BackgroundTasks,
    target_job: str = Form("IT工程师"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    第二步：触发生命级后台 LCEL 优化任务。接口立即返回。
    """
    stmt = select(ResumeOptimizationModel).where(ResumeOptimizationModel.session_id == session_id)
    result = await db.execute(stmt)
    opt_record = result.scalar_one_or_none()

    if not opt_record:
        raise HTTPException(status_code=404, detail="并未找到对应的导入任务")
    
    if opt_record.status == "processing":
        return JSONResponse(content={"code": 200, "message": "该简历已经在优化排队中，请勿重复触发", "data": {"session_id": session_id}})

    # 后台开启 Langchain 流式推导任务
    background_tasks.add_task(ResumeOptimizeService.optimize_resume_task, session_id, opt_record.original_text, target_job)
    
    # 将初始库状态设为排队中，进度先定为 5
    opt_record.status = "processing"
    opt_record.progress = 5
    await db.commit()

    return {
        "code": 200,
        "message": "AI优化已进入后台引擎处理池，请持续轮询 /status 接口",
        "data": {"session_id": session_id}
    }

@router.get("/status/{session_id}")
async def get_optimization_status(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    （被轮询）获取优化的实时进度百分比。
    """
    stmt = select(ResumeOptimizationModel).where(ResumeOptimizationModel.session_id == session_id)
    result = await db.execute(stmt)
    opt_record = result.scalar_one_or_none()

    if not opt_record:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "code": 200,
        "data": {
            "session_id": session_id,
            "progress": opt_record.progress,
            "status": opt_record.status,
            # 如果到达 100 并且 completed，顺带返回优化好的 Markdown 原文供前端直接渲染
            "result_markdown": opt_record.optimized_text if opt_record.status == "completed" else None
        }
    }

@router.get("/export/{session_id}")
async def export_pdf(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    第三步：读取优化的结果，利用 Markdown 到 PDF 直接强制后端约束排版并下载成 PDF！
    """
    stmt = select(ResumeOptimizationModel).where(ResumeOptimizationModel.session_id == session_id)
    result = await db.execute(stmt)
    opt_record = result.scalar_one_or_none()

    if not opt_record or opt_record.status != "completed" or not opt_record.optimized_text:
        raise HTTPException(status_code=400, detail="优化未完成或未找到简历")

    md_content = opt_record.optimized_text
    
    # 强制美化CSS注入（简历风格）
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>Resume Export</title>
        <style>
            body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; }}
            h1 {{ font-size: 28px; text-align: center; border-bottom: 2px solid #5a5a5a; padding-bottom: 10px; margin-bottom: 20px; }}
            h2 {{ font-size: 20px; color: #2c3e50; border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 25px; }}
            h3 {{ font-size: 16px; color: #2980b9; margin-bottom: 5px; }}
            p {{ margin: 0 0 10px 0; }}
            ul {{ padding-left: 20px; margin-top: 5px; }}
            li {{ margin-bottom: 5px; }}
            strong {{ color: #000; }}
            .experience-header {{ display: flex; justify-content: space-between; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content, extensions=['tables', 'fenced_code'])}
    </body>
    </html>
    """
    
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None
    }
    
    try:
        pdf_bytes = pdfkit.from_string(html_template, False, options=options)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=optimized_resume_{session_id[-6:]}.pdf"
            }
        )
    except OSError as e:
        # 兜底：如果电脑上没有 wkhtmltopdf，降级返回可打印的 HTML
        print(f"[PDF导出报错] 请安装 wkhtmltopdf: {e}")
        return Response(
            content=html_template,
            media_type="text/html",
            headers={
                "Content-Disposition": f"inline; filename=optimized_resume_{session_id[-6:]}.html"
            }
        )
