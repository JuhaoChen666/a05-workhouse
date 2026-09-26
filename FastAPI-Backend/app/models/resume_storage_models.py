"""Reuse existing Base; guard historical identities/content in ORM updates."""
from datetime import datetime, timezone
from sqlalchemy import event, inspect
from app.models.session_models import Base
from app.models.resume_storage_schema import define_tables


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


_tables = define_tables(Base.metadata)


class ExperienceItemModel(Base):
    __table__ = _tables[0]


class ResumeTemplateModel(Base):
    __table__ = _tables[1]


class ResumeGenerationJobModel(Base):
    __table__ = _tables[2]


class ResumeDocumentModel(Base):
    __table__ = _tables[3]


def immutable_fields(model, fields):
    @event.listens_for(model, "before_update")
    def reject_change(mapper, connection, target):
        if any(inspect(target).attrs[name].history.has_changes() for name in fields):
            raise ValueError("historical identity/content is immutable")


immutable_fields(ResumeTemplateModel, set(ResumeTemplateModel.__table__.columns.keys()) - {"validation_status", "is_enabled", "validation_details"})
immutable_fields(ResumeGenerationJobModel, {"id", "user_id", "template_id", "template_version", "jd_source_type", "job_id", "jd_snapshot", "experience_snapshot", "personal_info_snapshot", "template_snapshot", "options_snapshot", "target_pages", "language", "created_at"})
immutable_fields(ResumeDocumentModel, {"id", "user_id", "format", "generation_job_id", "snapshot", "pdf_asset", "latex_asset", "markdown_content", "legacy_optimization_id", "copied_from_id", "created_at"})


@event.listens_for(ResumeGenerationJobModel, "before_update")
def freeze_review_after_creation(mapper, connection, target):
    for field in ("review_plan", "review_decision"):
        history = inspect(target).attrs[field].history
        if history.has_changes() and any(old is not None for old in history.deleted):
            raise ValueError("review plan/decision is immutable once recorded")
