"""Internal persistence inputs; no authentication or HTTP API."""
from typing import Annotated, Any, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, StringConstraints, field_validator
from app.models.resume_latex_contracts import (
    CertificateItemCreate, CompetitionAwardItemCreate, ProjectItemCreate,
    WorkItemCreate, SkillItemCreate, ResumeGenerationRequest,
)

ExperienceInput = TypeAdapter(Annotated[
    CertificateItemCreate | CompetitionAwardItemCreate | ProjectItemCreate | WorkItemCreate | SkillItemCreate,
    Field(discriminator="type"),
])


class GenerationInput(ResumeGenerationRequest):
    template_version: str = Field(min_length=1, max_length=32)
    personal_info: dict[str, Any] = Field(default_factory=dict)


class FileAsset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    key: str = Field(pattern=r"^[1-9][0-9]*/[0-9a-f]{32}\.(pdf|tex|bin)$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: Literal["application/pdf", "text/x-tex", "application/octet-stream"]


DocumentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
DocumentNameAdapter = TypeAdapter(DocumentName)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: DocumentName
    generation_job_id: str


class CleanupCursor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purge_after: datetime
    id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    @field_validator("purge_after")
    @classmethod
    def utc_naive(cls, value):
        if value.tzinfo is not None:
            raise ValueError("UTC naive cursor timestamp required")
        return value


def owner_id(value):
    if type(value) is not int or not 0 < value <= 2147483647:
        raise ValueError("trusted owner must be a positive Integer")
    return value
