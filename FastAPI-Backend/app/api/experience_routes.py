"""Authenticated P2 experience maintenance."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.api.experience_dependencies import trusted_owner, experience_session, private_store
from app.api.experience_http import ExperienceRoute, experience_response
from app.infrastructure.mapper.experience_mapper import ExperienceMapper
from app.infrastructure.private_resume_assets import private_asset_transaction
from app.models.resume_latex_contracts import ExperienceTypeEnum, ExperienceItemResponse
from app.models.experience_api_contracts import (
    ExperienceContent, EditExperience, ArchiveRequest, OrderRequest, SortBatch,
    ManualBatch, ExperiencePage, ArchiveFilter,
)
from app.services.experience_errors import ExperienceError

router = APIRouter(prefix="/api/experiences", tags=["个人经历库"], route_class=ExperienceRoute)
Owner = Annotated[int, Depends(trusted_owner)]
Session = Annotated[object, Depends(experience_session)]
Store = Annotated[object, Depends(private_store)]


@router.get("", response_model=ExperiencePage)
async def list_experiences(owner: Owner, session: Session,
    page: int = Query(1, ge=1, le=1000000), page_size: int = Query(20, ge=1, le=100),
    type: ExperienceTypeEnum | None = None, tag: list[str] = Query(default=[]),
    keyword: str | None = Query(None, max_length=200), archive: ArchiveFilter = "active"):
    tags = list(dict.fromkeys(t.strip() for t in tag))
    if len(tags) > 50 or any(not t or len(t) > 100 for t in tags):
        raise ExperienceError("INVALID_TAGS", "At most 50 nonblank tags of 100 characters")
    async with session.begin():
        rows, total = await ExperienceMapper(session, owner).page(page=page, page_size=page_size,
            type_=type, tags=tags, keyword=keyword.strip() if keyword else None, archive=archive)
        return ExperiencePage(items=[experience_response(r) for r in rows], page=page, page_size=page_size, total=total)


@router.post("", response_model=ExperienceItemResponse, status_code=201)
async def create_experience(item: ExperienceContent, owner: Owner, session: Session):
    async with session.begin():
        return experience_response(await ExperienceMapper(session, owner).create_experience(item.model_dump(mode="json")))


@router.post("/batch", response_model=list[ExperienceItemResponse], status_code=201)
async def import_manual(request: ManualBatch, owner: Owner, session: Session):
    async with session.begin():
        mapper = ExperienceMapper(session, owner)
        return [experience_response(await mapper.create_experience(item.model_dump(mode="json"))) for item in request.items]


@router.put("/order", response_model=list[ExperienceItemResponse])
async def reorder(request: SortBatch, owner: Owner, session: Session):
    async with session.begin():
        mapper = ExperienceMapper(session, owner)
        # Consistent lock order across concurrent reorder batches.
        results = {}
        for entry in sorted(request.items, key=lambda item: str(item.id)):
            results[str(entry.id)] = experience_response(await mapper.set_order(str(entry.id), entry.sort_order, entry.expected_revision))
        return [results[str(entry.id)] for entry in request.items]


@router.get("/{item_id}", response_model=ExperienceItemResponse)
async def get_experience(item_id: UUID, owner: Owner, session: Session):
    async with session.begin():
        return experience_response(await ExperienceMapper(session, owner).get_experience(str(item_id)))


@router.put("/{item_id}", response_model=ExperienceItemResponse)
async def edit_experience(item_id: UUID, request: EditExperience, owner: Owner, session: Session, store: Store):
    async with private_asset_transaction(session, store, owner):
        mapper = ExperienceMapper(session, owner)
        old = await mapper.get_experience(str(item_id))
        if old.type != request.item.type:
            raise ExperienceError("TYPE_IMMUTABLE", "Experience type cannot change")
        return experience_response(await mapper.replace_content(str(item_id), request.item.model_dump(mode="json"), request.expected_revision))


@router.patch("/{item_id}/archive", response_model=ExperienceItemResponse)
async def archive_experience(item_id: UUID, request: ArchiveRequest, owner: Owner, session: Session):
    async with session.begin():
        return experience_response(await ExperienceMapper(session, owner).set_archive(str(item_id), request.is_archived, request.expected_revision))


@router.patch("/{item_id}/order", response_model=ExperienceItemResponse)
async def order_experience(item_id: UUID, request: OrderRequest, owner: Owner, session: Session):
    async with session.begin():
        return experience_response(await ExperienceMapper(session, owner).set_order(str(item_id), request.sort_order, request.expected_revision))


@router.delete("/{item_id}", status_code=204)
async def delete_experience(item_id: UUID, owner: Owner, session: Session,
                            expected_revision: int = Query(..., ge=1, le=2147483647)):
    async with session.begin():
        await ExperienceMapper(session, owner).remove(str(item_id), expected_revision)
