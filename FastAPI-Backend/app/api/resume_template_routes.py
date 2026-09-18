"""Read-only versioned template catalog and deterministic source preview."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.models.resume_template_contracts import (
    TemplateCompatibilityRequest,
    TemplateCompatibilityResponse,
    TemplateDetail,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateSummary,
    TemplateValidationReport,
)
from app.models.resume_storage_models import ResumeTemplateModel as Template
from app.services.resume_template_service import (
    TemplateProtocolError,
    compatibility,
    render_snapshot,
    validate_template,
)


router = APIRouter(prefix="/api/resume-templates", tags=["LaTeX templates"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


def snapshot(template: Template) -> dict:
    return {column.name: getattr(template, column.name) for column in Template.__table__.columns}


def summary(template: Template) -> TemplateSummary:
    return TemplateSummary(
        id=template.id,
        version=template.version,
        name=template.name,
        description=template.metadata_json.get("description", ""),
        protocol_version=template.metadata_json.get("protocol_version", "1.0"),
        supported_sections=template.supported_sections,
        supported_pages=template.supported_pages,
        supported_languages=template.supported_languages,
        supports_avatar=template.metadata_json.get("supports_avatar", False),
        validation_status=template.validation_status,
        is_enabled=template.is_enabled,
    )


async def version_or_404(session: AsyncSession, template_id: str, version: str) -> Template:
    row = await session.get(Template, (template_id, version))
    if row is None:
        raise HTTPException(status_code=404, detail="template version not found")
    return row


@router.get("", response_model=list[TemplateSummary])
async def list_templates(
    session: SessionDependency,
    include_unavailable: bool = False,
):
    statement = select(Template).order_by(Template.id, Template.version)
    if not include_unavailable:
        statement = statement.where(Template.is_enabled.is_(True), Template.validation_status == "VALIDATED")
    return [summary(row) for row in (await session.execute(statement)).scalars()]


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: str,
    session: SessionDependency,
    version: str | None = None,
):
    rows = list((await session.execute(select(Template).where(Template.id == template_id))).scalars())
    if not rows:
        raise HTTPException(status_code=404, detail="template not found")
    if version is None:
        available = [row for row in rows if row.is_enabled and row.validation_status == "VALIDATED"]
        if not available:
            raise HTTPException(status_code=404, detail="no available template version")
        row = max(available, key=lambda item: tuple(map(int, item.version.split("-", 1)[0].split("."))))
    else:
        row = next((item for item in rows if item.version == version), None)
        if row is None:
            raise HTTPException(status_code=404, detail="template version not found")
    return TemplateDetail(
        **summary(row).model_dump(),
        metadata=row.metadata_json,
        content_digest=row.content_digest,
        validation_details=row.validation_details,
        available_versions=sorted((item.version for item in rows), key=lambda value: tuple(map(int, value.split("-", 1)[0].split(".")))),
    )


@router.get("/{template_id}/versions", response_model=list[TemplateSummary])
async def list_template_versions(template_id: str, session: SessionDependency):
    rows = list((await session.execute(
        select(Template).where(Template.id == template_id).order_by(Template.version)
    )).scalars())
    if not rows:
        raise HTTPException(status_code=404, detail="template not found")
    return [summary(row) for row in rows]


@router.get("/{template_id}/versions/{version}", response_model=TemplateDetail)
async def get_template_version(template_id: str, version: str, session: SessionDependency):
    await version_or_404(session, template_id, version)
    return await get_template(template_id, session, version)


@router.get("/{template_id}/versions/{version}/validate", response_model=TemplateValidationReport)
async def validate_version(template_id: str, version: str, session: SessionDependency):
    row = await version_or_404(session, template_id, version)
    return validate_template(row.metadata_json, row.main_source)


@router.post("/{template_id}/versions/{version}/compatibility", response_model=TemplateCompatibilityResponse)
async def check_compatibility(
    template_id: str,
    version: str,
    request: TemplateCompatibilityRequest,
    session: SessionDependency,
):
    row = await version_or_404(session, template_id, version)
    return compatibility(snapshot(row), request)


@router.post("/{template_id}/versions/{version}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: str,
    version: str,
    request: TemplatePreviewRequest,
    session: SessionDependency,
):
    row = await version_or_404(session, template_id, version)
    if not row.is_enabled or row.validation_status != "VALIDATED":
        raise HTTPException(status_code=409, detail="template version is unavailable")
    if request.options.show_avatar and not row.metadata_json.get("supports_avatar", False):
        raise HTTPException(status_code=422, detail="template does not support an avatar")
    try:
        return render_snapshot(snapshot(row), request)
    except TemplateProtocolError as exc:
        raise HTTPException(status_code=409, detail=exc.report.model_dump(mode="json")) from exc
