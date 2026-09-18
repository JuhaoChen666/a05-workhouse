"""Authenticated asynchronous JD-tailored LaTeX resume generation API."""

from __future__ import annotations

import os
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.experience_dependencies import experience_session, private_store, trusted_owner
from app.infrastructure.mapper.resume_storage_mapper import AssetNotFound, ResumeStorageMapper
from app.infrastructure.private_resume_assets import PrivateAssets
from app.models.resume_latex_contracts import ResumeGenerationJobResponse, ResumeGenerationRequest
from app.models.resume_storage_models import ResumeDocumentModel, ResumeGenerationJobModel, ResumeTemplateModel
from app.services.resume_generation_service import jd_keywords, rank_experiences, run_generation_job


router = APIRouter(prefix="/api/resume-generation", tags=["JD 简历生成"])
Owner = Annotated[int, Depends(trusted_owner)]
Session = Annotated[object, Depends(experience_session)]
Store = Annotated[PrivateAssets, Depends(private_store)]


def _job_response(job: ResumeGenerationJobModel) -> ResumeGenerationJobResponse:
    error = job.error if isinstance(job.error, dict) else {}
    compiled = job.status == "COMPILED"
    recommendation = None
    if isinstance(job.jd_snapshot, dict):
        chosen, matches, chosen_ids = rank_experiences(
            list(job.experience_snapshot or []),
            str(job.jd_snapshot.get("text") or ""),
            (job.options_snapshot or {}).get("selected_item_ids"),
        )
        recommendation = {
            "selected_item_ids": chosen_ids,
            "keyword_matches": matches,
            "keyword_count": len(jd_keywords(str(job.jd_snapshot.get("text") or ""))),
            "trimmed_item_ids": [
                str(item.get("id"))
                for item in (job.experience_snapshot or [])
                if str(item.get("id")) not in chosen_ids
            ],
        }
    return ResumeGenerationJobResponse(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        progress_percentage=job.progress_percentage,
        pdf_download_url=f"/api/resume-generation/jobs/{job.id}/pdf" if compiled else None,
        latex_source_url=f"/api/resume-generation/jobs/{job.id}/latex" if compiled else None,
        compile_error_message=str(error.get("message")) if error else None,
        compile_error_location=str(error.get("location")) if error.get("location") else None,
        retryable=bool(error.get("retryable", False)),
        traces=job.traces or [],
        created_at=job.created_at,
        recommendation=recommendation,
    )


async def _resolve_job(job_id: str) -> dict[str, Any]:
    base = (
        os.getenv("JOB_SOURCE_BASE_URL")
        or os.getenv("API_ORIGIN")
        or "http://127.0.0.1:8080"
    ).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{base}/positions/{job_id}")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"岗位详情获取失败: {exc}") from exc
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), dict):
            payload = payload["data"]
        elif isinstance(payload.get("result"), dict):
            payload = payload["result"]
    content = payload.get("jobContent") if isinstance(payload, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=422, detail="岗位没有可用于生成的 JD 文本")
    return {"id": job_id, "jobContent": content, "source": payload}


async def _latest_template(session, template_id: str, version: str | None):
    statement = select(ResumeTemplateModel).where(ResumeTemplateModel.id == template_id)
    rows = list((await session.execute(statement)).scalars())
    if version:
        row = next((item for item in rows if item.version == version), None)
    else:
        row = max(rows, key=lambda item: tuple(map(int, item.version.split("-", 1)[0].split(".")))) if rows else None
    if row is None or not row.is_enabled or row.validation_status != "VALIDATED":
        raise HTTPException(status_code=422, detail="模板不存在或未通过校验")
    return row


@router.post("/jobs", response_model=ResumeGenerationJobResponse, status_code=202)
async def create_generation_job(
    request: ResumeGenerationRequest,
    background_tasks: BackgroundTasks,
    owner: Owner,
    session: Session,
):
    resolved_job = await _resolve_job(request.job_id) if request.jd_source_type == "JOB_ID" else None
    template_version = request.template_version
    async with session.begin():
        template = await _latest_template(session, request.template_id, template_version)
        values = request.model_dump(mode="json")
        values["template_version"] = template.version
        values["personal_info"] = request.personal_info
        mapper = ResumeStorageMapper(session, owner)
        try:
            job = await mapper.create_job(values, resolved_job=resolved_job)
        except (ValueError, AssetNotFound) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    background_tasks.add_task(run_generation_job, job.id, owner)
    return _job_response(job)


@router.get("/jobs", response_model=list[ResumeGenerationJobResponse])
async def list_generation_jobs(owner: Owner, session: Session):
    async with session.begin():
        jobs = await ResumeStorageMapper(session, owner).list_jobs()
        return [_job_response(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ResumeGenerationJobResponse)
async def get_generation_job(job_id: str, owner: Owner, session: Session):
    async with session.begin():
        try:
            return _job_response(await ResumeStorageMapper(session, owner).get_job(job_id))
        except AssetNotFound as exc:
            raise HTTPException(status_code=404, detail="生成任务不存在") from exc


@router.post("/jobs/{job_id}/retry", response_model=ResumeGenerationJobResponse, status_code=202)
async def retry_generation_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    owner: Owner,
    session: Session,
):
    async with session.begin():
        try:
            job = await ResumeStorageMapper(session, owner).retry_job(job_id)
        except AssetNotFound as exc:
            raise HTTPException(status_code=404, detail="生成任务不存在") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(run_generation_job, job.id, owner)
    return _job_response(job)


async def _read_output(job_id: str, owner: int, session, store: PrivateAssets, field: str):
    async with session.begin():
        mapper = ResumeStorageMapper(session, owner)
        try:
            job = await mapper.get_job(job_id)
            if job.status != "COMPILED":
                raise HTTPException(status_code=409, detail="生成任务尚未完成")
            document = (await session.execute(select(ResumeDocumentModel).where(
                ResumeDocumentModel.user_id == owner,
                ResumeDocumentModel.generation_job_id == job.id,
                ResumeDocumentModel.deleted_at.is_(None),
            ).order_by(ResumeDocumentModel.created_at.desc()))).scalars().first()
            if document is None:
                raise HTTPException(status_code=404, detail="生成文档不存在")
            asset = getattr(document, field)
        except AssetNotFound as exc:
            raise HTTPException(status_code=404, detail="生成任务不存在") from exc
    try:
        return store.read(owner, asset)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        raise HTTPException(status_code=410, detail=f"生成文件不可用: {exc}") from exc


@router.get("/jobs/{job_id}/pdf")
async def download_pdf(job_id: str, owner: Owner, session: Session, store: Store):
    content = await _read_output(job_id, owner, session, store, "pdf_asset")
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="resume-{job_id[:8]}.pdf"'})


@router.get("/jobs/{job_id}/latex")
async def download_latex(job_id: str, owner: Owner, session: Session, store: Store):
    content = await _read_output(job_id, owner, session, store, "latex_asset")
    return Response(content=content, media_type="text/x-tex",
                    headers={"Content-Disposition": f'attachment; filename="resume-{job_id[:8]}.tex"'})


@router.get("/documents")
async def list_documents(owner: Owner, session: Session):
    async with session.begin():
        rows = list((await session.execute(select(ResumeDocumentModel).where(
            ResumeDocumentModel.user_id == owner,
            ResumeDocumentModel.deleted_at.is_(None),
        ).order_by(ResumeDocumentModel.created_at.desc()))).scalars())
        return [{
            "id": row.id,
            "name": row.name,
            "format": row.format,
            "generation_job_id": row.generation_job_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        } for row in rows]
