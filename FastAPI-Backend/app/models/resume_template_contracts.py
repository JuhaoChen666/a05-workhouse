"""Public contracts for the versioned LaTeX template protocol."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


TEMPLATE_PROTOCOL_VERSION = "1.0"
FIXED_SECTIONS = (
    "basic_info",
    "education",
    "skills",
    "work",
    "projects",
    "certificates",
    "competitions",
)


class ProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BasicInfo(ProtocolModel):
    name: str = Field(min_length=1, max_length=200)
    title: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=254)
    github: str = Field(default="", max_length=200)
    city: str = Field(default="", max_length=100)
    avatar_path: str = Field(default="", max_length=500)

    @field_validator("avatar_path")
    @classmethod
    def safe_avatar_path(cls, value: str) -> str:
        if value and (value.startswith("/") or ":" in value or ".." in value.replace("\\", "/").split("/") or any(c in value for c in "{}\n\r\\")):
            raise ValueError("avatar_path must be a safe relative asset path")
        return value


class EducationEntry(ProtocolModel):
    school: str = Field(min_length=1, max_length=200)
    major: str = Field(default="", max_length=200)
    degree: str = Field(default="", max_length=100)
    date_range: str = Field(default="", max_length=100)
    gpa: str = Field(default="", max_length=50)


class SkillEntry(ProtocolModel):
    category: str = Field(min_length=1, max_length=100)
    items: str = Field(min_length=1, max_length=1000)


class WorkEntry(ProtocolModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(default="", max_length=100)
    date_range: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)
    city: str = Field(default="", max_length=100)
    bullets: list[str] = Field(default_factory=list, max_length=30)


class ProjectEntry(ProtocolModel):
    title: str = Field(min_length=1, max_length=200)
    role: str = Field(default="", max_length=100)
    date_range: str = Field(default="", max_length=100)
    tech_stack: str = Field(default="", max_length=1000)
    project_url: str = Field(default="", max_length=500)
    bullets: list[str] = Field(default_factory=list, max_length=30)


class CertificateEntry(ProtocolModel):
    title: str = Field(min_length=1, max_length=200)
    authority: str = Field(default="", max_length=200)
    issue_date: str = Field(default="", max_length=100)
    certificate_no: str = Field(default="", max_length=200)
    category: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=2000)


class CompetitionEntry(ProtocolModel):
    title: str = Field(min_length=1, max_length=200)
    award_level: str = Field(default="", max_length=100)
    award_date: str = Field(default="", max_length=100)
    organization: str = Field(default="", max_length=200)
    rank: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=2000)


class TemplateRenderData(ProtocolModel):
    basic_info: BasicInfo
    education: list[EducationEntry] = Field(default_factory=list, max_length=20)
    skills: list[SkillEntry] = Field(default_factory=list, max_length=30)
    work: list[WorkEntry] = Field(default_factory=list, max_length=30)
    projects: list[ProjectEntry] = Field(default_factory=list, max_length=30)
    certificates: list[CertificateEntry] = Field(default_factory=list, max_length=50)
    competitions: list[CompetitionEntry] = Field(default_factory=list, max_length=50)


class TemplatePreviewOptions(ProtocolModel):
    show_avatar: bool = False


class TemplatePreviewRequest(ProtocolModel):
    data: TemplateRenderData
    options: TemplatePreviewOptions = Field(default_factory=TemplatePreviewOptions)


class TemplateCompatibilityRequest(ProtocolModel):
    language: Literal["zh", "en"] = "zh"
    target_pages: Literal[1, 2] = 1
    show_avatar: bool = False
    sections: list[Literal["basic_info", "education", "skills", "work", "projects", "certificates", "competitions"]] = Field(default_factory=lambda: list(FIXED_SECTIONS))

    @field_validator("sections")
    @classmethod
    def unique_sections(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate sections")
        return value


class TemplateValidationIssue(ProtocolModel):
    code: str
    message: str


class TemplateValidationReport(ProtocolModel):
    valid: bool
    protocol_version: str = TEMPLATE_PROTOCOL_VERSION
    required_sections: list[str] = Field(default_factory=lambda: list(FIXED_SECTIONS))
    referenced_roots: list[str] = Field(default_factory=list)
    issues: list[TemplateValidationIssue] = Field(default_factory=list)


class TemplateCompatibilityResponse(ProtocolModel):
    compatible: bool
    issues: list[TemplateValidationIssue] = Field(default_factory=list)


class TemplatePreviewResponse(ProtocolModel):
    template_id: str
    version: str
    content_digest: str
    source_sha256: str
    latex_source: str


class TemplateSummary(ProtocolModel):
    id: str
    version: str
    name: str
    description: str = ""
    protocol_version: str = TEMPLATE_PROTOCOL_VERSION
    supported_sections: list[str]
    supported_pages: list[int]
    supported_languages: list[str]
    supports_avatar: bool
    validation_status: str
    is_enabled: bool


class TemplateDetail(TemplateSummary):
    metadata: dict[str, Any]
    content_digest: str
    validation_details: dict[str, Any]
    available_versions: list[str]
