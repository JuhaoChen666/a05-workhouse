"""P2 wire contracts. Public content never controls ownership or provenance."""
from typing import Annotated, Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from app.models.resume_latex_contracts import (
    CertificateItemCreate, CompetitionAwardItemCreate, ProjectItemCreate,
    WorkItemCreate, SkillItemCreate, ExperienceItemResponse,
)


class PublicContent:
    @model_validator(mode="after")
    def server_provenance(self):
        if self.source_type != "MANUAL" or self.source_resume_id is not None or self.source_locator:
            raise ValueError("PDF provenance is assigned only by import confirmation")
        if not self.title.strip():
            raise ValueError("title must not be blank")
        for name in ("role", "award_level"):
            if hasattr(self, name) and not getattr(self, name).strip():
                raise ValueError(name + " must not be blank")
        if self.type == "SKILL" and not self.category.strip():
            raise ValueError("skill category must not be blank")
        for name in ("skills", "bullets", "tech_stack"):
            if hasattr(self, name) and any(not item.strip() for item in getattr(self, name)):
                raise ValueError(name + " cannot contain blank strings")
        if self.sort_order > 2147483647:
            raise ValueError("sort_order exceeds Integer range")
        self.tags = list(dict.fromkeys(tag.strip() for tag in self.tags if tag.strip()))
        if len(self.tags) > 50 or any(len(tag) > 100 for tag in self.tags):
            raise ValueError("at most 50 tags of 100 characters")
        return self


class CertificateContent(PublicContent, CertificateItemCreate): pass
class AwardContent(PublicContent, CompetitionAwardItemCreate): pass
class ProjectContent(PublicContent, ProjectItemCreate): pass
class WorkContent(PublicContent, WorkItemCreate): pass
class SkillContent(PublicContent, SkillItemCreate): pass

ExperienceContent = Annotated[
    CertificateContent | AwardContent | ProjectContent | WorkContent | SkillContent,
    Field(discriminator="type"),
]
Revision = Annotated[StrictInt, Field(ge=1, le=2147483647)]
SortOrder = Annotated[StrictInt, Field(ge=0, le=2147483647)]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EditExperience(StrictRequest):
    expected_revision: Revision
    item: ExperienceContent


class RevisionRequest(StrictRequest):
    expected_revision: Revision


class ArchiveRequest(RevisionRequest):
    is_archived: bool


class OrderRequest(RevisionRequest):
    sort_order: SortOrder


class OrderEntry(OrderRequest):
    id: UUID


class SortBatch(StrictRequest):
    items: list[OrderEntry] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("duplicate experience IDs")
        return self


class ManualBatch(StrictRequest):
    items: list[ExperienceContent] = Field(min_length=1, max_length=100)


class ExperiencePage(BaseModel):
    items: list[ExperienceItemResponse]
    page: int
    page_size: int
    total: int


class ExistingPDF(StrictRequest):
    source_resume_id: Annotated[StrictInt, Field(gt=0)]


class DraftEdit(RevisionRequest):
    content: dict[str, Any]

    @field_validator("content")
    @classmethod
    def limited_content(cls, value):
        import json
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False)) > 32000:
            raise ValueError("draft content exceeds 32000 characters")
        return value


class ConfirmationEntry(StrictRequest):
    id: UUID
    expected_revision: Revision


class ConfirmImport(StrictRequest):
    items: list[ConfirmationEntry] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("duplicate draft IDs")
        return self


ArchiveFilter = Literal["active", "archived", "all"]
