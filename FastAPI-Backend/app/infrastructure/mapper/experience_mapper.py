"""P2 DB queries and conditional writes; caller retains transaction ownership."""
import json
from sqlalchemy import select, func, or_, delete, literal
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper, RevisionConflict
from app.models.resume_storage_models import ExperienceItemModel as Experience

SEARCH_PATHS = (
    "$.authority", "$.certificate_no", "$.category", "$.description", "$.award_level",
    "$.organization", "$.rank", "$.role", "$.project_url", "$.tech_stack[*]", "$.bullets[*]",
    "$.department", "$.city", "$.skills[*]", "$.proficiency",
)


class ExperienceMapper(ResumeStorageMapper):
    async def page(self, *, page, page_size, type_=None, tags=(), keyword=None, archive="active"):
        self.transaction()
        filters = [Experience.user_id == self.owner]
        if archive != "all":
            filters.append(Experience.is_archived.is_(archive == "archived"))
        if type_ is not None:
            filters.append(Experience.type == type_)
        for tag in dict.fromkeys(tags):
            filters.append(func.json_contains(Experience.tags, json.dumps(tag, ensure_ascii=False)) == 1)
        if keyword:
            pattern = "%" + keyword.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
            search = literal(pattern).collate("utf8mb4_bin")
            filters.append(or_(Experience.title.collate("utf8mb4_bin").like(search, escape="!"),
                func.json_search(Experience.tags, "one", search, "!").is_not(None),
                func.json_search(Experience.attributes, "one", search, "!", *SEARCH_PATHS).is_not(None)))
        total = await self.session.scalar(select(func.count()).select_from(Experience).where(*filters))
        rows = list((await self.session.execute(select(Experience).where(*filters)
            .order_by(Experience.sort_order, Experience.id).offset((page - 1) * page_size).limit(page_size))).scalars())
        return rows, total

    async def set_archive(self, id_, archived, revision):
        row = await self.owned(Experience, id_, lock=True)
        return await self.compare_update(row, {"is_archived": archived}, revision)

    async def set_order(self, id_, order, revision):
        row = await self.owned(Experience, id_, lock=True)
        return await self.compare_update(row, {"sort_order": order}, revision)

    async def remove(self, id_, revision):
        await self.owned(Experience, id_, lock=True)
        result = await self.session.execute(delete(Experience).where(
            Experience.id == id_, Experience.user_id == self.owner, Experience.revision == revision))
        if result.rowcount != 1:
            raise RevisionConflict("experience changed")

    async def replace_content(self, id_, content, revision):
        row = await self.owned(Experience, id_, lock=True)
        # Public content cannot strip/replace provenance attached by confirmation.
        values = {**content, "source_type": row.source_type, "source_resume_id": row.source_resume_id,
                  "source_locator": row.source_locator}
        return await self.update_experience(id_, values, expected_revision=revision)
