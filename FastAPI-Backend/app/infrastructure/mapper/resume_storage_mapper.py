"""Owner-scoped persistence. Every operation participates in caller transaction."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select, update
from app.models.resume_storage_contracts import ExperienceInput, GenerationInput, DocumentInput, FileAsset, owner_id
from app.models.resume_storage_models import (
    ExperienceItemModel as Experience, ResumeTemplateModel as Template,
    ResumeGenerationJobModel as Job, ResumeDocumentModel as Document, utcnow,
)
from app.models.session_models import ResumeModel, ResumeOptimizationModel
from app.infrastructure.private_resume_assets import verify_references


class AssetNotFound(LookupError):
    pass


class RevisionConflict(ValueError):
    pass


COMMON = {"type", "title", "start_date", "end_date", "tags", "is_archived", "sort_order", "source_type", "source_resume_id", "source_locator"}


class ResumeStorageMapper:
    def __init__(self, session, trusted_owner):
        self.session, self.owner = session, owner_id(trusted_owner)

    def transaction(self):
        if not self.session.in_transaction():
            raise RuntimeError("caller must open transaction")

    async def owned(self, model, id_, *, lock=False, active=False):
        self.transaction()
        stmt = select(model).where(model.id == id_, model.user_id == self.owner).execution_options(populate_existing=True)
        if active:
            stmt = stmt.where(model.deleted_at.is_(None))
        if lock:
            stmt = stmt.with_for_update()
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise AssetNotFound("asset unavailable")
        return row

    async def legacy(self, model, key, id_):
        self.transaction()
        row = (await self.session.execute(select(model).where(key == id_, model.user_id == self.owner).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if row is None:
            raise AssetNotFound("asset unavailable")
        return row

    async def experience_values(self, data):
        values = ExperienceInput.validate_python(data).model_dump(mode="json")
        if values["source_resume_id"] is not None:
            await self.legacy(ResumeModel, ResumeModel.id, values["source_resume_id"])
        verify_references(self.session, self.owner, values["source_locator"])
        return {**{k: v for k, v in values.items() if k in COMMON},
            "attributes": {k: v for k, v in values.items() if k not in COMMON}}

    async def create_experience(self, data):
        self.transaction()
        values = await self.experience_values(data)
        now = utcnow()
        row = Experience(**values, id=str(uuid4()), user_id=self.owner, revision=1, created_at=now, updated_at=now)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_experience(self, id_):
        return await self.owned(Experience, id_)

    async def list_experiences(self, *, include_archived=False):
        self.transaction()
        stmt = select(Experience).where(Experience.user_id == self.owner)
        if not include_archived:
            stmt = stmt.where(Experience.is_archived.is_(False))
        return list((await self.session.execute(stmt.order_by(Experience.sort_order, Experience.id))).scalars())

    async def update_experience(self, id_, data, *, expected_revision):
        row = await self.owned(Experience, id_)
        values = await self.experience_values(data)
        if values["type"] != row.type:
            raise ValueError("experience type is immutable")
        return await self.compare_update(row, values, expected_revision)

    async def compare_update(self, row, values, expected_revision):
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("positive expected_revision required")
        result = await self.session.execute(update(Experience).where(
            Experience.id == row.id, Experience.user_id == self.owner, Experience.revision == expected_revision
        ).values(**values, revision=Experience.revision + 1, updated_at=utcnow()).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise RevisionConflict("experience changed")
        await self.session.refresh(row)
        return row

    async def archive_experience(self, id_, *, expected_revision):
        row = await self.owned(Experience, id_)
        return await self.compare_update(row, {"is_archived": True}, expected_revision)

    async def create_job(self, data, *, resolved_job=None):
        self.transaction()
        request = GenerationInput.model_validate(data)
        template = (await self.session.execute(select(Template).where(
            Template.id == request.template_id, Template.version == request.template_version
        ).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if not template or template.validation_status != "VALIDATED" or not template.is_enabled:
            raise ValueError("validated enabled template required")
        if request.target_pages not in template.supported_pages or request.language not in template.supported_languages:
            raise ValueError("unsupported pages/language")
        if request.show_avatar and not template.metadata_json["supports_avatar"]:
            raise ValueError("template does not support avatar")
        if request.jd_source_type == "JOB_ID":
            if not isinstance(resolved_job, dict) or str(resolved_job.get("id")) != request.job_id or not isinstance(resolved_job.get("jobContent"), str) or not resolved_job["jobContent"].strip():
                raise ValueError("trusted actual Job.jobContent required")
            jd = {"source_type": "JOB_ID", "text": resolved_job["jobContent"], "job": deepcopy(resolved_job)}
        else:
            jd = {"source_type": "TEXT", "text": request.jd_text}
        stmt = select(Experience).where(Experience.user_id == self.owner, Experience.is_archived.is_(False))
        if request.selected_item_ids is not None:
            stmt = stmt.where(Experience.id.in_(request.selected_item_ids))
        items = list((await self.session.execute(stmt.order_by(Experience.sort_order, Experience.id).with_for_update().execution_options(populate_existing=True))).scalars())
        if request.selected_item_ids is not None and len(items) != len(request.selected_item_ids):
            raise AssetNotFound("selected experience unavailable")
        experience = [{c.name: deepcopy(getattr(item, c.name)) for c in Experience.__table__.columns if c.name not in ("created_at", "updated_at")} for item in items]
        personal = deepcopy(request.personal_info)
        verify_references(self.session, self.owner, [experience, personal])
        options = request.model_dump(mode="json", exclude={"personal_info", "jd_text", "job_id"})
        frozen_template = {c.name: deepcopy(getattr(template, c.name)) for c in Template.__table__.columns if c.name not in ("created_at", "validation_details")}
        now = utcnow()
        row = Job(id=str(uuid4()), user_id=self.owner, template_id=template.id, template_version=template.version,
            jd_source_type=request.jd_source_type, job_id=request.job_id, jd_snapshot=jd, experience_snapshot=experience,
            personal_info_snapshot=personal, options_snapshot=options, template_snapshot=frozen_template,
            target_pages=request.target_pages, language=request.language, status="PENDING", stage="PENDING",
            progress_percentage=0, error=None, traces=[], retry_count=0, created_at=now, updated_at=now)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_job(self, id_):
        return await self.owned(Job, id_)

    async def list_jobs(self):
        self.transaction()
        return list((await self.session.execute(select(Job).where(Job.user_id == self.owner).order_by(Job.created_at, Job.id))).scalars())

    async def update_job(self, id_, *, status, stage, progress, error=None, traces=None):
        row = await self.owned(Job, id_, lock=True)
        transitions = {"PENDING": {"PENDING", "PROCESSING", "FAILED"}, "PROCESSING": {"PROCESSING", "COMPILED", "FAILED"}}
        if status not in transitions.get(row.status, set()) or type(progress) is not int or not 0 <= progress <= 100 or not stage or len(stage) > 100:
            raise ValueError("invalid task transition/progress/stage")
        if status == "COMPILED" and progress != 100 or status == "FAILED" and not isinstance(error, dict):
            raise ValueError("terminal task result required")
        if error is not None and not isinstance(error, dict) or traces is not None and not isinstance(traces, list):
            raise ValueError("error object/traces array required")
        verify_references(self.session, self.owner, traces)
        row.status, row.stage, row.progress_percentage, row.error = status, stage, progress, deepcopy(error)
        if traces is not None:
            row.traces = deepcopy(traces)
        row.updated_at = utcnow()
        if status == "PROCESSING" and row.started_at is None:
            row.started_at = row.updated_at
        if status in ("COMPILED", "FAILED"):
            row.finished_at = row.updated_at
        await self.session.flush()
        return row

    async def retry_job(self, id_):
        row = await self.owned(Job, id_, lock=True)
        if row.status != "FAILED":
            raise ValueError("only FAILED jobs can retry")
        verify_references(self.session, self.owner, [row.personal_info_snapshot, row.experience_snapshot])
        row.status, row.stage, row.progress_percentage = "PENDING", "PENDING", 0
        row.error, row.traces, row.started_at, row.finished_at = None, [], None, None
        row.retry_count += 1
        row.updated_at = utcnow()
        await self.session.flush()
        return row

    async def create_document(self, data, *, pdf_asset=None, latex_asset=None):
        data = DocumentInput.model_validate(data)
        job = await self.owned(Job, data.generation_job_id, lock=True)
        if job.status != "COMPILED":
            raise ValueError("COMPILED job required")
        files = {}
        for name, asset, media in (("pdf_asset", pdf_asset, "application/pdf"), ("latex_asset", latex_asset, "text/x-tex")):
            if asset is not None:
                asset = FileAsset.model_validate(asset)
                if asset.media_type != media:
                    raise ValueError("wrong document asset type")
                files[name] = asset.model_dump(mode="json")
        snapshot = {k: deepcopy(getattr(job, k)) for k in ("jd_snapshot", "experience_snapshot", "personal_info_snapshot", "template_snapshot", "options_snapshot", "traces")}
        verify_references(self.session, self.owner, [files, snapshot])
        return await self._add_document(name=data.name, format="latex", generation_job_id=job.id, snapshot=snapshot, **files)

    async def _add_document(self, **values):
        self.transaction()
        now = utcnow()
        row = Document(id=str(uuid4()), user_id=self.owner, created_at=now, updated_at=now, **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_document(self, id_):
        return await self.owned(Document, id_, active=True)

    async def list_documents(self):
        self.transaction()
        return list((await self.session.execute(select(Document).where(Document.user_id == self.owner, Document.deleted_at.is_(None)).order_by(Document.created_at, Document.id))).scalars())

    async def rename_document(self, id_, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError("valid document name required")
        row = await self.owned(Document, id_, active=True, lock=True)
        row.name, row.updated_at = name, utcnow()
        await self.session.flush()
        return row

    async def copy_document(self, id_, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError("valid document name required")
        row = await self.owned(Document, id_, active=True, lock=True)
        values = {k: deepcopy(getattr(row, k)) for k in ("format", "generation_job_id", "snapshot", "pdf_asset", "latex_asset", "markdown_content", "legacy_optimization_id")}
        verify_references(self.session, self.owner, [values["snapshot"], values["pdf_asset"], values["latex_asset"]])
        return await self._add_document(name=name, copied_from_id=id_, **values)

    async def delete_document(self, id_, *, retention_days=30):
        if type(retention_days) is not int or retention_days < 0:
            raise ValueError("nonnegative retention days required")
        row = await self.owned(Document, id_, lock=True)
        if row.deleted_at is None:
            row.deleted_at = utcnow()
            row.purge_after = row.deleted_at + timedelta(days=retention_days)
            row.updated_at = row.deleted_at
            await self.session.flush()
        return row

    async def read_legacy_markdown(self, id_):
        row = await self.legacy(ResumeOptimizationModel, ResumeOptimizationModel.session_id, id_)
        return row.optimized_text

    async def save_legacy_markdown(self, id_, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError("valid document name required")
        row = await self.legacy(ResumeOptimizationModel, ResumeOptimizationModel.session_id, id_)
        return await self._add_document(name=name, format="markdown", snapshot={"legacy_optimization_id": id_},
            markdown_content=row.optimized_text, legacy_optimization_id=id_)
