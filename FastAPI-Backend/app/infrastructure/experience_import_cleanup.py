"""Bounded maintenance, never automatically scheduled. Default is dry-run."""
from sqlalchemy import select, or_, and_, delete
from app.infrastructure.private_resume_assets import root_mutex, assets_in
from app.models.resume_storage_contracts import owner_id
from app.models.experience_import_models import ExperienceImportBatch as Batch, ExperienceImportDraft as Draft
from app.models.resume_storage_models import ExperienceItemModel as Experience, ResumeDocumentModel as Document, ResumeGenerationJobModel as Job, utcnow
from app.services.experience_import_service import PROCESSING_LEASE


async def cleanup_imports(session, store, owner, *, dry_run=True, now=None, limit=100, after=None):
    owner_id(owner)
    if session.in_transaction() or not 1 <= limit <= 1000:
        raise ValueError("fresh session and bounded limit required")
    now = now or utcnow()
    if now.tzinfo is not None:
        raise ValueError("expected UTC naive time")
    if after is not None and (not isinstance(after, str) or len(after) != 36):
        raise ValueError("expected import UUID cursor")
    async with root_mutex(session, store):
        async with session.begin():
            stmt = select(Batch).where(Batch.user_id == owner, Batch.files_purged_at.is_(None),
                or_(Batch.status.in_(["FAILED", "CONFIRMED", "CANCELLED", "EXPIRED"]), Batch.expires_at <= now,
                    and_(Batch.status == "PROCESSING", Batch.updated_at <= now - PROCESSING_LEASE)))
            if after:
                stmt = stmt.where(Batch.id > after)
            rows = list((await session.execute(stmt.order_by(Batch.id).limit(limit + 1)
                .with_for_update().execution_options(populate_existing=True))).scalars())
            has_more, rows = len(rows) > limit, rows[:limit]
            candidates = {row.id: list(assets_in(row.source_asset)) for row in rows}
            # Failed processing can be retried within TTL. Do not purge such files.
            eligible = [row for row in rows if row.status in ("CONFIRMED", "CANCELLED", "EXPIRED") or row.expires_at <= now]
            protected = set()
            for model, field in ((Experience, Experience.source_locator),):
                values = (await session.execute(select(field).where(model.user_id == owner).with_for_update())).scalars()
                for value in values:
                    protected.update(a.key for a in assets_in(value))
            living = (await session.execute(select(Document).where(Document.user_id == owner,
                or_(Document.deleted_at.is_(None), Document.purge_after > now))
                .with_for_update().execution_options(populate_existing=True))).scalars()
            for row in living:
                protected.update(a.key for a in assets_in([row.snapshot, row.pdf_asset, row.latex_asset]))
            running = (await session.execute(select(Job).where(Job.user_id == owner, Job.status.in_(["PENDING", "PROCESSING"]))
                .with_for_update().execution_options(populate_existing=True))).scalars()
            for row in running:
                protected.update(a.key for a in assets_in([row.personal_info_snapshot, row.experience_snapshot, row.traces]))
            other_sources = (await session.execute(select(Batch.source_asset).where(Batch.user_id == owner,
                Batch.files_purged_at.is_(None), Batch.id.not_in([r.id for r in eligible]))
                .with_for_update())).scalars()
            for value in other_sources:
                protected.update(a.key for a in assets_in(value))
            removable = {a.key: a for row in eligible for a in candidates[row.id] if a.key not in protected}
            for asset in removable.values():
                if store.path(owner, asset.key).exists():
                    store.read(owner, asset)
            if not dry_run:
                for asset in removable.values():
                    store.remove(owner, asset)
                for row in rows:
                    if row.status in ("READY", "PROCESSING", "FAILED") and row.expires_at <= now:
                        row.status, row.updated_at = "EXPIRED", now
                    elif row.status == "PROCESSING" and row.updated_at <= now - PROCESSING_LEASE:
                        row.status, row.updated_at = "FAILED", now
                        row.error = {"code": "PROCESSING_INTERRUPTED", "message": "Processing interrupted; retry is available"}
                    if row in eligible and not {a.key for a in candidates[row.id]} & protected:
                        row.source_asset, row.source_resume_id, row.pages = None, None, []
                        row.files_purged_at = now
                        await session.execute(delete(Draft).where(Draft.batch_id == row.id, Draft.user_id == owner))
                await session.flush()
            return {"dry_run": dry_run, "import_ids": [r.id for r in rows], "removable_keys": sorted(removable),
                    "protected_keys": sorted({a.key for v in candidates.values() for a in v} & protected),
                    "has_more": has_more, "next_cursor": rows[-1].id if has_more else None}
