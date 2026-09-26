"""PDF -> persistent editable drafts -> explicit confirmation."""
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter, Depends, File, UploadFile, Query
from app.api.experience_dependencies import trusted_owner, experience_session, private_store, draft_extractor, legacy_pdf_root
from app.api.experience_http import ExperienceRoute
from app.models.experience_api_contracts import ExistingPDF, DraftEdit, ConfirmImport
from app.services.experience_import_service import ExperienceImportService
from app.services.experience_errors import ExperienceError
from app.services.pdf_experience_extractor import MAX_PDF_BYTES

router = APIRouter(prefix="/api/experience-imports", tags=["PDF 经历导入"], route_class=ExperienceRoute)


def import_service(owner=Depends(trusted_owner), session=Depends(experience_session),
                   store=Depends(private_store), extractor=Depends(draft_extractor), legacy_root=Depends(legacy_pdf_root)):
    return ExperienceImportService(session, owner, store, extractor, legacy_root=legacy_root)

Service = Annotated[ExperienceImportService, Depends(import_service)]


class MarkdownImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legacy_optimization_id: str = Field(min_length=1, max_length=36)


@router.post("/markdown", status_code=201)
async def import_markdown(request: MarkdownImport, service: Service):
    return await service.from_markdown(request.legacy_optimization_id)


@router.get("")
async def list_imports(service: Service, page: int = Query(1, ge=1, le=1000000)):
    from sqlalchemy import select
    from app.models.experience_import_models import ExperienceImportBatch
    async with service.session.begin():
        rows = (await service.session.execute(select(ExperienceImportBatch).where(
            ExperienceImportBatch.user_id == service.owner).order_by(ExperienceImportBatch.created_at.desc(), ExperienceImportBatch.id).offset((page - 1) * 50).limit(50))).scalars()
        return [{"id": row.id, "status": row.status, "expires_at": row.expires_at} for row in rows]


@router.get("/sources")
async def list_sources(service: Service, page: int = Query(1, ge=1, le=1000000)):
    from sqlalchemy import select
    from app.models.session_models import ResumeModel
    async with service.session.begin():
        rows = (await service.session.execute(select(ResumeModel).where(ResumeModel.user_id == service.owner)
            .order_by(ResumeModel.id.desc()).offset((page - 1) * 100).limit(100))).scalars()
        return [{"id": row.id, "filename": row.filename} for row in rows]


@router.post("/upload", status_code=201)
async def upload_pdf(service: Service, file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise ExperienceError("PDF_TYPE", "Only PDF files are accepted")
        content = await file.read(MAX_PDF_BYTES + 1)
        return await service.upload(content)
    finally:
        await file.close()


@router.post("/existing", status_code=201)
async def existing_pdf(request: ExistingPDF, service: Service):
    return await service.from_existing(request.source_resume_id)


@router.get("/{import_id}")
async def get_import(import_id: UUID, service: Service):
    return await service.get(str(import_id))


@router.post("/{import_id}/retry")
async def retry_import(import_id: UUID, service: Service):
    return await service.retry(str(import_id))


@router.post("/{import_id}/cancel")
async def cancel_import(import_id: UUID, service: Service):
    return await service.cancel(str(import_id))


@router.put("/{import_id}/items/{draft_id}")
async def edit_draft(import_id: UUID, draft_id: UUID, request: DraftEdit, service: Service):
    return await service.edit(str(import_id), str(draft_id), request.content, request.expected_revision)


@router.delete("/{import_id}/items/{draft_id}", status_code=204)
async def delete_draft(import_id: UUID, draft_id: UUID, service: Service,
                       expected_revision: int = Query(..., ge=1, le=2147483647)):
    await service.remove(str(import_id), str(draft_id), expected_revision)


@router.post("/{import_id}/confirm")
async def confirm_import(import_id: UUID, request: ConfirmImport, service: Service):
    return await service.confirm(str(import_id), request)
