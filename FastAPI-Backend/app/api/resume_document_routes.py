"""Document identity owns management and downloads, including copied documents."""
from copy import deepcopy
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from app.api.experience_dependencies import experience_session, private_store, trusted_owner
from app.infrastructure.mapper.resume_storage_mapper import AssetNotFound, ResumeStorageMapper
from app.infrastructure.private_resume_assets import private_asset_transaction, verify_references
from app.models.resume_storage_contracts import DocumentName
from app.models.resume_storage_models import ResumeGenerationJobModel, utcnow
from app.models.resume_latex_contracts import ResumeGenerationRequest
from app.services.resume_generation_service import build_render_data
from app.api.resume_generation_routes import _job_response
from app.api.experience_http import ExperienceRoute
from sqlalchemy import select
from app.models.session_models import ResumeOptimizationModel

router = APIRouter(prefix="/api/resume-documents", tags=["简历库"], route_class=ExperienceRoute)
Owner = Annotated[int, Depends(trusted_owner)]
Session = Annotated[object, Depends(experience_session)]
Store = Annotated[object, Depends(private_store)]


class NameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: DocumentName


class EditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jd_text: str | None = Field(None, min_length=1, max_length=100000)
    personal_info: dict[str, Any] | None = None
    selected_item_ids: list[str] | None = None
    target_pages: int | None = Field(None, ge=1, le=2)
    language: str | None = Field(None, pattern="^(zh|en)$")
    ai_recommendation_mode: str | None = Field(None, pattern="^(MANUAL_ONLY|JD_AUTO_SELECT_AND_TAILOR)$")


def public_snapshot(value):
    if isinstance(value, list):
        return [public_snapshot(entry) for entry in value]
    if isinstance(value, dict):
        return {key: public_snapshot(entry) for key, entry in value.items()
            if key not in {"key", "local_path", "path", "resources", "main_source"}}
    return value


def summary(row):
    return {"id": row.id, "name": row.name, "format": row.format, "generation_job_id": row.generation_job_id,
            "copied_from_id": row.copied_from_id, "created_at": row.created_at, "updated_at": row.updated_at}


async def get_document(mapper, id):
    try:
        return await mapper.get_document(str(id))
    except AssetNotFound:
        raise HTTPException(404, detail="简历不存在") from None


@router.get("")
async def list_documents(owner: Owner, session: Session):
    async with session.begin():
        return [summary(row) for row in await ResumeStorageMapper(session, owner).list_documents()]


@router.get("/legacy-markdown")
async def legacy_markdown(owner: Owner, session: Session):
    async with session.begin():
        rows = (await session.execute(select(ResumeOptimizationModel).where(
            ResumeOptimizationModel.user_id == owner).order_by(ResumeOptimizationModel.created_at.desc()))).scalars()
        return [{"id": row.session_id, "format": "markdown", "content": row.optimized_text,
            "created_at": row.created_at} for row in rows]


@router.get("/{document_id}")
async def detail(document_id: UUID, owner: Owner, session: Session):
    async with session.begin():
        row = await get_document(ResumeStorageMapper(session, owner), document_id)
        return {**summary(row), "snapshot": public_snapshot(row.snapshot), "markdown_content": row.markdown_content}


@router.patch("/{document_id}")
async def rename(document_id: UUID, request: NameRequest, owner: Owner, session: Session):
    async with session.begin():
        mapper = ResumeStorageMapper(session, owner)
        await get_document(mapper, document_id)
        return summary(await mapper.rename_document(str(document_id), request.name))


@router.post("/{document_id}/copy", status_code=201)
async def copy_document(document_id: UUID, request: NameRequest, owner: Owner, session: Session, store: Store):
    async with private_asset_transaction(session, store, owner):
        mapper = ResumeStorageMapper(session, owner)
        await get_document(mapper, document_id)
        return summary(await mapper.copy_document(str(document_id), request.name))


@router.delete("/{document_id}", status_code=204)
async def delete(document_id: UUID, owner: Owner, session: Session):
    async with session.begin():
        mapper = ResumeStorageMapper(session, owner)
        await get_document(mapper, document_id)
        await mapper.delete_document(str(document_id))
    return Response(status_code=204)


async def download(document_id, owner, session, store, field):
    async with session.begin():
        row = await get_document(ResumeStorageMapper(session, owner), document_id)
        if row.format != "latex":
            raise HTTPException(409, detail="历史 Markdown 请先确认事实并重新生成")
        asset = getattr(row, field)
    try:
        return store.read(owner, asset)
    except (ValueError, FileNotFoundError, PermissionError):
        raise HTTPException(410, detail="文件不可用，请联系维护人员或按原快照重试") from None


@router.get("/{document_id}/pdf")
async def pdf(document_id: UUID, owner: Owner, session: Session, store: Store):
    return Response(await download(document_id, owner, session, store, "pdf_asset"), media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="resume-{document_id}.pdf"'})


@router.get("/{document_id}/latex")
async def latex(document_id: UUID, owner: Owner, session: Session, store: Store):
    return Response(await download(document_id, owner, session, store, "latex_asset"), media_type="text/x-tex",
        headers={"Content-Disposition": f'attachment; filename="resume-{document_id}.tex"'})


@router.post("/{document_id}/regenerate", status_code=202)
async def regenerate(document_id: UUID, request: EditRequest, owner: Owner, session: Session, store: Store):
    async with private_asset_transaction(session, store, owner):
        mapper = ResumeStorageMapper(session, owner)
        document = await get_document(mapper, document_id)
        if document.format != "latex":
            raise HTTPException(409, detail="历史 Markdown 必须先进入草稿确认")
        snapshot = deepcopy(document.snapshot)
        options = snapshot["options_snapshot"]
        personal = request.personal_info if request.personal_info is not None else snapshot["personal_info_snapshot"]
        experiences = snapshot["experience_snapshot"]
        selected = request.selected_item_ids if request.selected_item_ids is not None else options.get("selected_item_ids")
        if selected is not None and (len(selected) != len(set(selected)) or set(selected) - {row["id"] for row in experiences}):
            raise HTTPException(422, detail="只能选择该文档原快照中的经历")
        template = snapshot["template_snapshot"]
        language = request.language or options["language"]
        pages = request.target_pages or options["target_pages"]
        if language not in template["supported_languages"] or pages not in template["supported_pages"]:
            raise HTTPException(422, detail="原模板版本不支持所选语言或页数")
        jd = {"source_type": "TEXT", "text": request.jd_text} if request.jd_text is not None else snapshot["jd_snapshot"]
        values = dict(options, selected_item_ids=selected, target_pages=pages, language=language,
            jd_source_type=jd["source_type"], ai_recommendation_mode=request.ai_recommendation_mode or options["ai_recommendation_mode"])
        ResumeGenerationRequest.model_validate({**values, "jd_text": jd["text"] if jd["source_type"] == "TEXT" else None,
            "job_id": (jd.get("job") or {}).get("id") if jd["source_type"] == "JOB_ID" else None,
            "jd_source_type": jd["source_type"], "personal_info": personal})
        build_render_data(experiences, personal)
        verify_references(session, owner, [experiences, personal])
        now = utcnow()
        row = ResumeGenerationJobModel(id=str(uuid4()), user_id=owner, template_id=template["id"], template_version=template["version"],
            jd_source_type=jd["source_type"], job_id=(jd.get("job") or {}).get("id"), jd_snapshot=jd,
            experience_snapshot=experiences, personal_info_snapshot=deepcopy(personal), template_snapshot=template,
            options_snapshot=values, target_pages=pages, language=language, status="PENDING", stage="PENDING",
            progress_percentage=0, error=None, traces=[], retry_count=0, created_at=now, updated_at=now)
        session.add(row)
        await session.flush()
        return _job_response(row)
