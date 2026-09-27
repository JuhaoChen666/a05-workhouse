"""Owner-authenticated view across legacy uploads and saved generated resumes."""
from typing import Annotated
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select

from app.api.experience_dependencies import experience_session, private_store, trusted_owner
from app.infrastructure.private_resume_assets import PrivateAssets
from app.models.resume_storage_models import ResumeDocumentModel, ResumeThumbnailModel
from app.models.session_models import ResumeModel
from app.infrastructure.database import get_db_session

router = APIRouter(prefix="/api/resume-library", tags=["简历库"])
Owner = Annotated[int, Depends(trusted_owner)]
LegacySession = Annotated[object, Depends(get_db_session)]
Session = Annotated[object, Depends(experience_session)]
Store = Annotated[PrivateAssets, Depends(private_store)]


def _item_key(kind, id_):
    return f"{kind}:{id_}"


def _api_time(value, *, legacy=False):
    if value is None:
        return None, datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        if legacy:
            zone_name = os.environ.get("RESUME_LEGACY_TIMEZONE")
            if zone_name:
                try:
                    zone = ZoneInfo(zone_name)
                except ZoneInfoNotFoundError:
                    raise HTTPException(503, detail="RESUME_LEGACY_TIMEZONE 未配置有效时区") from None
            else:
                zone = datetime.now().astimezone().tzinfo
            value = value.replace(tzinfo=zone)
        else:
            value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.isoformat(), value


def merge_resume_items(uploaded, generated, *, page, page_size):
    """Merge ordered source windows with a deterministic cross-source order."""
    items = []
    for row in uploaded:
        updated_at, sort_time = _api_time(row.uploaded_at, legacy=True)
        items.append({
            "key": _item_key("uploaded", row.id), "kind": "uploaded", "id": row.id,
            "name": row.filename, "format": "pdf", "updated_at": updated_at,
            "thumbnail_url": None, "_sort_time": sort_time,
        })
    for row in generated:
        updated_at, sort_time = _api_time(row.updated_at)
        created_at = _api_time(row.created_at)[0]
        items.append({
            "key": _item_key("generated", row.id), "kind": "generated", "id": row.id,
            "name": row.name, "format": row.format, "updated_at": updated_at,
            "thumbnail_url": None, "_sort_time": sort_time,
            "generation_job_id": row.generation_job_id, "copied_from_id": row.copied_from_id,
            "created_at": created_at,
            "document": {"id": row.id, "name": row.name, "format": row.format,
                "generation_job_id": row.generation_job_id, "copied_from_id": row.copied_from_id,
                "created_at": created_at, "updated_at": updated_at},
        })
    items.sort(key=lambda item: (item["_sort_time"], 1 if item["kind"] == "generated" else 0,
        (1, str(item["id"])) if item["kind"] == "generated" else (0, int(item["id"]))), reverse=True)
    offset = (page - 1) * page_size
    page_items = items[offset:offset + page_size]
    for item in page_items:
        item.pop("_sort_time", None)
    return page_items


@router.get("")
async def list_resume_library(
    owner: Owner,
    legacy: LegacySession,
    session: Session,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(24, ge=1, le=100),
):
    offset, limit = (page - 1) * page_size, page * page_size
    uploaded_total = int(await legacy.scalar(select(func.count()).select_from(ResumeModel).where(
        ResumeModel.user_id == owner)) or 0)
    generated_total = int(await session.scalar(select(func.count()).select_from(ResumeDocumentModel).where(
        ResumeDocumentModel.user_id == owner, ResumeDocumentModel.deleted_at.is_(None))) or 0)
    uploaded = list((await legacy.execute(select(ResumeModel).where(
        ResumeModel.user_id == owner).order_by(ResumeModel.uploaded_at.desc(), ResumeModel.id.desc())
        .limit(limit))).scalars())
    generated = list((await session.execute(select(ResumeDocumentModel).where(
        ResumeDocumentModel.user_id == owner, ResumeDocumentModel.deleted_at.is_(None)
        ).order_by(ResumeDocumentModel.updated_at.desc(), ResumeDocumentModel.id.desc())
        .limit(limit))).scalars())
    items = merge_resume_items(uploaded, generated, page=page, page_size=page_size)
    # SQL source windows are bounded to the requested page prefix. Equal timestamps
    # have deterministic type and identity ordering across independent data sources.
    page_items = items
    generated_ids = [item["id"] for item in page_items if item["kind"] == "generated"]
    uploaded_ids = [str(item["id"]) for item in page_items if item["kind"] == "uploaded"]
    if generated_ids or uploaded_ids:
        thumbnails = (await session.execute(select(ResumeThumbnailModel).where(
            ResumeThumbnailModel.user_id == owner, ResumeThumbnailModel.status == "READY",
            ((ResumeThumbnailModel.source_kind == "generated") & ResumeThumbnailModel.source_id.in_(generated_ids)) |
            ((ResumeThumbnailModel.source_kind == "uploaded") & ResumeThumbnailModel.source_id.in_(uploaded_ids))
        ))).scalars().all()
        ready = {(row.source_kind, row.source_id): row for row in thumbnails if row.asset}
        for item in page_items:
            thumb = ready.get((item["kind"], str(item["id"])))
            if thumb:
                item["thumbnail_url"] = f"/api/resume-library/thumbnail/{item['kind']}/{item['id']}"
    return {"items": page_items, "total": uploaded_total + generated_total, "page": page,
        "page_size": page_size, "uploaded_total": uploaded_total, "generated_total": generated_total}


@router.get("/thumbnail/{kind}/{source_id}")
async def read_thumbnail(kind: str, source_id: str, owner: Owner, session: Session,
    legacy: LegacySession, store: Store):
    if kind not in {"uploaded", "generated"}:
        raise HTTPException(404, detail="缩略图不存在")
    async with session.begin():
        task = (await session.execute(select(ResumeThumbnailModel).where(
            ResumeThumbnailModel.user_id == owner, ResumeThumbnailModel.source_kind == kind,
            ResumeThumbnailModel.source_id == source_id, ResumeThumbnailModel.status == "READY"
        ))).scalar_one_or_none()
        if task is None or task.asset is None:
            raise HTTPException(404, detail="缩略图不存在")
        if kind == "generated":
            source = (await session.execute(select(ResumeDocumentModel.id).where(
                ResumeDocumentModel.id == source_id, ResumeDocumentModel.user_id == owner,
                ResumeDocumentModel.deleted_at.is_(None)))).scalar_one_or_none()
        else:
            try:
                source_id_number = int(source_id)
            except ValueError:
                raise HTTPException(404, detail="简历不存在") from None
            source = (await legacy.execute(select(ResumeModel.id).where(
                ResumeModel.id == source_id_number, ResumeModel.user_id == owner))).scalar_one_or_none()
        if source is None:
            raise HTTPException(404, detail="简历不存在")
        asset = task.asset
    try:
        data = store.read(owner, asset)
    except (ValueError, FileNotFoundError, PermissionError):
        raise HTTPException(404, detail="缩略图不可用") from None
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})
