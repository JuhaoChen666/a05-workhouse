"""Authenticated asynchronous JD-tailored LaTeX resume generation API."""

from __future__ import annotations

import os
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from datetime import datetime, timezone

from app.api.experience_dependencies import experience_session, private_store, trusted_owner
from app.infrastructure.mapper.resume_storage_mapper import AssetNotFound, ResumeStorageMapper
from app.infrastructure.private_resume_assets import PrivateAssets
from app.infrastructure.private_resume_assets import private_asset_transaction
from app.api.experience_http import ExperienceRoute
from app.models.resume_latex_contracts import ResumeGenerationJobResponse, ResumeGenerationRequest
from app.models.resume_storage_models import ResumeDocumentModel, ResumeGenerationJobModel, ResumeTemplateModel
from app.models.experience_import_models import ExperienceImportBatch


router = APIRouter(prefix="/api/resume-generation", tags=["JD 简历生成"], route_class=ExperienceRoute)
Owner = Annotated[int, Depends(trusted_owner)]
Session = Annotated[object, Depends(experience_session)]
Store = Annotated[PrivateAssets, Depends(private_store)]


def _job_response(job: ResumeGenerationJobModel) -> ResumeGenerationJobResponse:
    error = job.error if isinstance(job.error, dict) else {}
    compiled = job.status == "COMPILED"
    recommendation = job.result_metadata
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
        result_metadata=job.result_metadata,
    )


async def _with_document(job, session):
    result = _job_response(job)
    if job.status == "COMPILED":
        document = (await session.execute(select(ResumeDocumentModel).where(
            ResumeDocumentModel.user_id == job.user_id, ResumeDocumentModel.generation_job_id == job.id,
            ResumeDocumentModel.deleted_at.is_(None)).order_by(
            ResumeDocumentModel.copied_from_id.is_(None).desc(), ResumeDocumentModel.created_at, ResumeDocumentModel.id))).scalars().first()
        result.document_id = document.id if document else None
        result.pdf_download_url = f"/api/resume-documents/{document.id}/pdf" if document else None
        result.latex_source_url = f"/api/resume-documents/{document.id}/latex" if document else None
    return result


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
        raise HTTPException(status_code=502, detail="岗位详情服务暂不可用，请稍后重试或粘贴 JD") from None
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
    if not version:
        rows = [row for row in rows if row.is_enabled and row.validation_status == "VALIDATED"]
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
    owner: Owner,
    session: Session,
    store: Store,
):
    resolved_job = await _resolve_job(request.job_id) if request.jd_source_type == "JOB_ID" else None
    template_version = request.template_version
    async with private_asset_transaction(session, store, owner):
        template = await _latest_template(session, request.template_id, template_version)
        values = request.model_dump(mode="json")
        values["template_version"] = template.version
        values["personal_info"] = request.personal_info
        mapper = ResumeStorageMapper(session, owner)
        try:
            job = await mapper.create_job(values, resolved_job=resolved_job)
        except (ValueError, AssetNotFound) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _job_response(job)


@router.get("/jobs", response_model=list[ResumeGenerationJobResponse])
async def list_generation_jobs(owner: Owner, session: Session):
    async with session.begin():
        jobs = await ResumeStorageMapper(session, owner).list_jobs()
        return [await _with_document(job, session) for job in jobs]


@router.get("/metrics")
async def generation_metrics(owner: Owner, session: Session):
    async with session.begin():
        rows = (await session.execute(select(ResumeGenerationJobModel.status,
            ResumeGenerationJobModel.created_at, ResumeGenerationJobModel.started_at,
            ResumeGenerationJobModel.finished_at, ResumeGenerationJobModel.error,
            ResumeGenerationJobModel.result_metadata, ResumeGenerationJobModel.retry_count).where(
            ResumeGenerationJobModel.user_id == owner))).all()
        counts, failures, ai, durations = {}, {}, {}, []
        longest = 0
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for status, created, started, finished, error, metadata, retry in rows:
            counts[status] = counts.get(status, 0) + 1
            if status in ("PENDING", "PROCESSING"):
                longest = max(longest, (now - created).total_seconds())
            if started and finished:
                durations.append((finished - started).total_seconds())
            if error:
                code = error.get("code", "UNKNOWN")
                failures[code] = failures.get(code, 0) + 1
            if metadata:
                state = metadata.get("ai_status", "UNKNOWN")
                ai[state] = ai.get(state, 0) + 1
        terminal = counts.get("COMPILED", 0) + counts.get("FAILED", 0)
        imports = (await session.execute(select(ExperienceImportBatch.ai_attempt_count, ExperienceImportBatch.ai_failure_count,
            ExperienceImportBatch.retry_count).where(ExperienceImportBatch.user_id == owner))).all()
        import_attempts = sum(row.ai_attempt_count for row in imports)
        import_failures = sum(row.ai_failure_count for row in imports)
        return {"status_counts": counts, "failure_rate": counts.get("FAILED", 0) / terminal if terminal else None,
            "average_execution_seconds": sum(durations) / len(durations) if durations else None,
            "failure_codes": failures, "ai_states": ai, "retry_total": sum(row.retry_count for row in rows),
            "queue_depth": counts.get("PENDING", 0), "longest_unfinished_seconds": longest,
            "import_ai_attempts": import_attempts, "import_ai_failures": import_failures,
            "import_ai_failure_rate": import_failures / import_attempts if import_attempts else None,
            "import_retry_total": sum(row.retry_count for row in imports)}


@router.get("/jobs/{job_id}", response_model=ResumeGenerationJobResponse)
async def get_generation_job(job_id: str, owner: Owner, session: Session):
    async with session.begin():
        try:
            return await _with_document(await ResumeStorageMapper(session, owner).get_job(job_id), session)
        except AssetNotFound as exc:
            raise HTTPException(status_code=404, detail="生成任务不存在") from exc


@router.post("/jobs/{job_id}/retry", response_model=ResumeGenerationJobResponse, status_code=202)
async def retry_generation_job(
    job_id: str,
    owner: Owner,
    session: Session,
    store: Store,
):
    async with private_asset_transaction(session, store, owner):
        try:
            job = await ResumeStorageMapper(session, owner).retry_job(job_id)
        except AssetNotFound as exc:
            raise HTTPException(status_code=404, detail="生成任务不存在") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
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
        raise HTTPException(status_code=410, detail="生成文件不可用，请联系维护人员") from None


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
