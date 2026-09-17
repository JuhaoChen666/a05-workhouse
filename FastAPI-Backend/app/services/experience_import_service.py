"""Durable PDF import state machine, correction, and atomic idempotent confirmation."""
import asyncio
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
from pydantic import ValidationError
from sqlalchemy import select, delete
from app.infrastructure.mapper.resume_storage_mapper import AssetNotFound, RevisionConflict
from app.infrastructure.mapper.experience_mapper import ExperienceMapper
from app.infrastructure.private_resume_assets import private_asset_transaction, LEGACY_ROOTS
from app.infrastructure.resume_template_store import safe_path
from app.models.experience_import_models import ExperienceImportBatch as Batch, ExperienceImportDraft as Draft
from app.models.resume_storage_models import utcnow
from app.services.experience_errors import ExperienceError, validation_issues
from app.services.pdf_experience_extractor import extract_pdf, run_extractor, draft_issues, ContentAdapter, MAX_PDF_BYTES

IMPORT_TTL = timedelta(days=7)
PROCESSING_LEASE = timedelta(minutes=5)


def draft_response(row):
    return {"id": row.id, "content": row.content, "issues": row.issues, "source_locator": row.locator,
            "revision": row.revision, "sort_order": row.sort_order,
            "needs_correction": bool(row.issues)}


class ExperienceImportService:
    def __init__(self, session, owner, store, extractor, *, legacy_root=None):
        self.session, self.owner, self.store, self.extractor = session, owner, store, extractor
        self.legacy_root = safe_path(legacy_root or LEGACY_ROOTS[0]).resolve()

    async def owned_batch(self, id_, *, lock=True):
        stmt = select(Batch).where(Batch.id == id_, Batch.user_id == self.owner)
        if lock:
            stmt = stmt.with_for_update()
        row = (await self.session.execute(stmt.execution_options(populate_existing=True))).scalar_one_or_none()
        if row is None:
            raise AssetNotFound("import unavailable")
        return row

    def expire_or_recover(self, row):
        now = utcnow()
        if row.status in ("READY", "PROCESSING", "FAILED") and row.expires_at <= now:
            row.status, row.updated_at = "EXPIRED", now
        elif row.status == "PROCESSING" and row.updated_at + PROCESSING_LEASE <= now:
            row.status, row.updated_at = "FAILED", now
            row.error = {"code": "PROCESSING_INTERRUPTED", "message": "Processing interrupted; retry is available"}

    def require_editable(self, row):
        if row.expires_at <= utcnow():
            raise ExperienceError("IMPORT_EXPIRED", "Draft import has expired", 409)
        if row.status != "READY":
            raise ExperienceError("IMPORT_STATE", "Import is not editable", 409)

    async def new_batch(self, files, content, source_resume_id=None):
        if not content or len(content) > MAX_PDF_BYTES:
            raise ExperienceError("PDF_SIZE", "PDF must be nonempty and at most 16 MiB", 413)
        now = utcnow()
        asset = files.write(content, "pdf")
        row = Batch(id=str(uuid4()), user_id=self.owner, source_resume_id=source_resume_id,
                    source_asset=asset.model_dump(mode="json"), pages=[], status="PROCESSING", error=None,
                    created_at=now, updated_at=now, expires_at=now + IMPORT_TTL)
        self.session.add(row)
        await self.session.flush()
        return row.id

    async def upload(self, content):
        async with private_asset_transaction(self.session, self.store, self.owner) as files:
            id_ = await self.new_batch(files, content)
        return await self.process(id_)

    async def from_existing(self, source_resume_id):
        async with private_asset_transaction(self.session, self.store, self.owner) as files:
            from app.models.session_models import ResumeModel
            source = await ExperienceMapper(self.session, self.owner).legacy(ResumeModel, ResumeModel.id, source_resume_id)
            path = Path(source.local_path)
            if not path.is_absolute():
                # Legacy routes write data/resumes/... relative to backend's cwd.
                path = self.legacy_root.parent.parent / path
            try:
                path = safe_path(path).resolve(strict=True)
                if self.legacy_root not in path.parents or path.suffix.lower() != ".pdf":
                    raise ValueError("unsafe legacy PDF path")
                if path.stat().st_size > MAX_PDF_BYTES:
                    raise ExperienceError("PDF_SIZE", "PDF exceeds 16 MiB", 413)
                with path.open("rb") as stream:
                    content = stream.read(MAX_PDF_BYTES + 1)
            except (OSError, ValueError):
                raise ExperienceError("PDF_SOURCE_UNAVAILABLE", "Source PDF unavailable", 409) from None
            id_ = await self.new_batch(files, content, source.id)
        return await self.process(id_)

    async def process(self, id_):
        async with self.session.begin():
            row = await self.owned_batch(id_)
            if row.status != "PROCESSING":
                raise ExperienceError("IMPORT_STATE", "Import is not processing", 409)
            asset, lease = row.source_asset, row.updated_at
        try:
            content = self.store.read(self.owner, asset)
            pages = await asyncio.to_thread(extract_pdf, content)
            drafts = await run_extractor(self.extractor, pages)
        except Exception as error:
            if not isinstance(error, ExperienceError):
                error = ExperienceError("IMPORT_PROCESSING_FAILED", "PDF draft processing failed", 502)
            async with self.session.begin():
                row = await self.owned_batch(id_)
                if row.status == "PROCESSING" and row.updated_at == lease:
                    row.status, row.updated_at = "FAILED", utcnow()
                    row.error = {"code": error.code, "message": error.message}
            raise ExperienceError(error.code, error.message, error.status, details={"import_id": id_}) from None
        async with self.session.begin():
            row = await self.owned_batch(id_)
            if row.status != "PROCESSING" or row.updated_at != lease or row.expires_at <= utcnow():
                raise ExperienceError("IMPORT_STATE", "Import processing state changed; check import status", 409)
            row.pages, row.status, row.error, row.updated_at = pages, "READY", None, utcnow()
            for index, data in enumerate(drafts):
                now = utcnow()
                self.session.add(Draft(id=str(uuid4()), batch_id=id_, user_id=self.owner, **data,
                                       revision=1, sort_order=index, created_at=now, updated_at=now))
            await self.session.flush()
        return await self.get(id_)

    async def get(self, id_):
        async with self.session.begin():
            row = await self.owned_batch(id_)
            self.expire_or_recover(row)
            drafts = list((await self.session.execute(select(Draft).where(
                Draft.batch_id == id_, Draft.user_id == self.owner).order_by(Draft.sort_order, Draft.id))).scalars())
            return {"id": row.id, "status": row.status, "error": row.error,
                    "source_resume_id": row.source_resume_id,
                    "source": {"sha256": row.source_asset["sha256"], "size_bytes": row.source_asset["size_bytes"]} if row.source_asset else None,
                    "expires_at": row.expires_at, "items": [draft_response(d) for d in drafts],
                    "confirmation_result": row.confirmation_result, "files_purged_at": row.files_purged_at}

    async def retry(self, id_):
        # First commit expiry/abandoned-process recovery, even when retry is rejected.
        await self.get(id_)
        async with self.session.begin():
            row = await self.owned_batch(id_)
            if row.status != "FAILED" or row.expires_at <= utcnow() or row.source_asset is None:
                raise ExperienceError("IMPORT_STATE", "Only unexpired failed imports can be retried", 409)
            row.status, row.error, row.updated_at = "PROCESSING", None, utcnow()
        return await self.process(id_)

    async def owned_draft(self, batch_id, draft_id):
        row = (await self.session.execute(select(Draft).where(
            Draft.id == draft_id, Draft.batch_id == batch_id, Draft.user_id == self.owner)
            .with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
        if row is None:
            raise AssetNotFound("draft unavailable")
        return row

    async def edit(self, id_, draft_id, content, revision):
        async with self.session.begin():
            self.require_editable(await self.owned_batch(id_))
            row = await self.owned_draft(id_, draft_id)
            if row.revision != revision:
                raise RevisionConflict("draft changed")
            # Draft content can remain incomplete; confirmation performs strict validation.
            row.content, row.issues = content, draft_issues(content)
            row.revision, row.updated_at = row.revision + 1, utcnow()
            await self.session.flush()
            return draft_response(row)

    async def remove(self, id_, draft_id, revision):
        async with self.session.begin():
            self.require_editable(await self.owned_batch(id_))
            row = await self.owned_draft(id_, draft_id)
            if row.revision != revision:
                raise RevisionConflict("draft changed")
            await self.session.delete(row)

    async def cancel(self, id_):
        async with self.session.begin():
            row = await self.owned_batch(id_)
            if row.status == "CONFIRMED":
                raise ExperienceError("IMPORT_STATE", "Confirmed imports cannot be cancelled", 409)
            row.status, row.updated_at = "CANCELLED", utcnow()
            row.pages = []
            await self.session.execute(delete(Draft).where(Draft.batch_id == id_, Draft.user_id == self.owner))
        return await self.get(id_)

    async def confirm(self, id_, request):
        selected = sorted([{"id": str(entry.id), "revision": entry.expected_revision} for entry in request.items], key=lambda e: e["id"])
        digest = hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()
        async with private_asset_transaction(self.session, self.store, self.owner):
            batch = await self.owned_batch(id_)
            if batch.status == "CONFIRMED":
                if batch.confirmation_digest != digest:
                    raise ExperienceError("CONFIRMATION_CONFLICT", "Import already confirmed with different selection or revisions", 409)
                return batch.confirmation_result
            self.require_editable(batch)
            if not batch.source_asset:
                raise ExperienceError("PDF_SOURCE_UNAVAILABLE", "Import source unavailable", 409)
            self.store.read(self.owner, batch.source_asset)
            inputs, errors = [], []
            for entry in selected:
                draft = await self.owned_draft(id_, entry["id"])
                if draft.revision != entry["revision"]:
                    raise RevisionConflict("draft changed")
                try:
                    value = ContentAdapter.validate_python(draft.content).model_dump(mode="json")
                    value.update(source_type="PDF_IMPORT", source_resume_id=batch.source_resume_id,
                                 source_locator={**draft.locator, "asset": batch.source_asset, "import_id": batch.id,
                                                 "draft_id": draft.id, "user_confirmed": True})
                    inputs.append((draft.id, value))
                except ValidationError as error:
                    errors.append({"draft_id": draft.id, "issues": validation_issues(error)})
            if errors:
                raise ExperienceError("DRAFT_NEEDS_CORRECTION", "Correct all selected drafts before confirming", details=errors)
            mapper = ExperienceMapper(self.session, self.owner)
            result = []
            for draft_id, value in inputs:
                row = await mapper.create_experience(value)
                result.append({"draft_id": draft_id, "experience_id": row.id})
            receipt = {"import_id": id_, "status": "CONFIRMED", "items": result}
            batch.status, batch.updated_at = "CONFIRMED", utcnow()
            batch.confirmation_digest, batch.confirmation_result = digest, receipt
            # Retain original draft evidence and final revisions for audit/retry, immutable after confirmation.
            await self.session.flush()
            return receipt
