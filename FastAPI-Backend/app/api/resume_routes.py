import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db_session
from app.models.session_models import ResumeModel
from app.utils.pdf_utils import extract_text_from_pdf
from datetime import datetime
from sqlalchemy import select, func
from app.models.interview_models import ResumeDeleteRequest, ResumeListItem, ResumeListResponse
from app.infrastructure.legacy_resume_deletion import delete_legacy_resume, LegacyResumeNotFound, LegacyResumeInUse


router = APIRouter(prefix="/api/resumes", tags=["简历管理"])

# 确保存储目录存在
UPLOAD_DIR = "data/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_resume(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    """
    上传简历 PDF，保存本地并存储文本到数据库
    """
    # 1. 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式文件")

    # 2. 生成本地保存路径
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        # 3. 异步保存文件到本地
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)

        # 4. 提取文本内容
        text_content = extract_text_from_pdf(file_path)
        if not text_content:
            # 即使解析失败，至少记录为空字符串
            text_content = ""

        # 5. 存储到数据库
        new_resume = ResumeModel(
            user_id=user_id,
            filename=file.filename,
            local_path=file_path,
            content_text=text_content,
            uploaded_at=datetime.now()
        )
        
        db.add(new_resume)
        await db.commit()
        await db.refresh(new_resume)

        return {
            "code": 200,
            "message": "简历上传并解析成功",
            "data": {
                "id": new_resume.id,
                "filename": new_resume.filename,
                "text_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content
            }
        }

    except Exception as e:
        if db:
            await db.rollback()
        # 如果文件已保存但后续失败，删除本地文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"上传处理失败: {str(e)}")

@router.delete("/delete")
async def delete_resume(
    request: ResumeDeleteRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    删除简历：数据库删除提交成功后清理文件；被来源引用时返回409并保留PDF。
    """
    try:
        cleanup = await delete_legacy_resume(db, request.id, request.user_id, request.filename)
        return {
            "code": 200,
            "message": "简历删除成功，文件清理待重试" if cleanup["file_cleanup_pending"] else "简历删除成功",
            "data": {
                "id": request.id,
                "filename": request.filename,
                **cleanup,
            }
        }
    except LegacyResumeNotFound:
        await db.rollback()
        raise HTTPException(status_code=404, detail="简历不存在或无权删除")
    except LegacyResumeInUse as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除处理失败: {str(e)}")

@router.get("/list", response_model=ResumeListResponse)
async def list_resumes(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """
    分页查询简历列表
    """
    try:
        # 1. 计算总数
        count_stmt = select(func.count()).select_from(ResumeModel).where(ResumeModel.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 2. 分页查询记录
        offset = (page - 1) * page_size
        stmt = select(ResumeModel).where(
            ResumeModel.user_id == user_id
        ).order_by(ResumeModel.uploaded_at.desc()).offset(offset).limit(page_size)
        
        result = await db.execute(stmt)
        resumes = result.scalars().all()

        # 3. 封装返回内容
        items = [
            ResumeListItem(
                id=r.id,
                filename=r.filename,
                uploaded_at=r.uploaded_at
            ) for r in resumes
        ]

        return ResumeListResponse(
            total=total,
            items=items,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询列表失败: {str(e)}")

@router.get("/item/{resume_id}")
async def get_resume_by_id(
    resume_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    通过 ID 查询简历，并仅返回唯一文件名（用于下载或预览）
    """
    try:
        stmt = select(ResumeModel).where(ResumeModel.id == resume_id)
        result = await db.execute(stmt)
        resume = result.scalar_one_or_none()

        if not resume:
            raise HTTPException(status_code=404, detail="未找到该简历")

        # 从 local_path 中提取唯一文件名 (去掉 data/resumes 路径)
        unique_filename = os.path.basename(resume.local_path)

        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "id": resume.id,
                "filename": resume.filename,  # 原始文件名
                "unique_filename": unique_filename,  # 服务器上的唯一文件名
                "uploaded_at": resume.uploaded_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询简历失败: {str(e)}")



