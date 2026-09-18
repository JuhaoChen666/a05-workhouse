"""Private filesystem boundary coordinated with caller database transactions."""
import hashlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, text, or_, and_
from app.infrastructure.resume_template_store import safe_path
from app.models.resume_storage_contracts import FileAsset, CleanupCursor, owner_id
from app.models.resume_storage_models import ExperienceItemModel, ResumeDocumentModel, ResumeGenerationJobModel, utcnow

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = BACKEND_ROOT / "data/private_resume_assets"
LEGACY_ROOTS = (BACKEND_ROOT / "data/resumes", BACKEND_ROOT / "data/optimizations")
MEDIA = {"pdf": "application/pdf", "tex": "text/x-tex", "bin": "application/octet-stream"}


class PrivateAssets:
    def __init__(self, root=DEFAULT_ROOT, max_bytes=32 * 1024 * 1024):
        self.root = safe_path(root).resolve()
        project = BACKEND_ROOT.parent
        if self.root == Path(self.root.anchor) or self.root in (BACKEND_ROOT, project):
            raise ValueError("private root must be dedicated")
        for legacy in LEGACY_ROOTS:
            legacy = legacy.resolve()
            if self.root == legacy or self.root in legacy.parents or legacy in self.root.parents:
                raise ValueError("private root overlaps legacy assets")
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, owner, key):
        owner_id(owner)
        # Validate all metadata key syntax without accepting arbitrary paths.
        FileAsset(key=key, sha256="0" * 64, size_bytes=0, media_type="application/octet-stream")
        if key.split("/")[0] != str(owner):
            raise PermissionError("asset belongs to another owner")
        path = safe_path(self.root / key)
        if self.root not in path.parents:
            raise ValueError("asset outside private root")
        return path

    def write(self, owner, content, extension):
        owner_id(owner)
        if extension not in MEDIA or not isinstance(content, bytes) or len(content) > self.max_bytes:
            raise ValueError("invalid asset bytes/type/size")
        path = self.path(owner, f"{owner}/{uuid4().hex}.{extension}")
        path.parent.mkdir(exist_ok=True)
        created = False
        try:
            with path.open("xb") as stream:
                created = True
                stream.write(content)
        except BaseException:
            if created:
                path.unlink(missing_ok=True)
            raise
        return FileAsset(key=path.relative_to(self.root).as_posix(), sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content), media_type=MEDIA[extension])

    def read(self, owner, asset):
        asset = FileAsset.model_validate(asset)
        path = self.path(owner, asset.key)
        if asset.media_type != MEDIA[path.suffix[1:]] or path.stat().st_size > self.max_bytes:
            raise ValueError("asset media/size mismatch")
        content = path.read_bytes()
        if len(content) != asset.size_bytes or hashlib.sha256(content).hexdigest() != asset.sha256:
            raise ValueError("asset integrity mismatch")
        return content

    def remove(self, owner, asset):
        path = self.path(owner, asset.key)
        if path.exists():
            self.read(owner, asset)
            path.unlink()


def assets_in(value):
    if isinstance(value, dict):
        if {"key", "sha256", "size_bytes", "media_type"} <= value.keys():
            yield FileAsset.model_validate(value)
        else:
            for child in value.values():
                yield from assets_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from assets_in(child)


def verify_references(session, owner, value):
    references = list(assets_in(value))
    if not references:
        return
    context = session.info.get("resume_private_assets")
    if not context or context[0] != owner:
        raise RuntimeError("private_asset_transaction required for asset references")
    for asset in references:
        context[1].read(owner, asset)


@asynccontextmanager
async def root_mutex(session, store):
    safe_path(store.root)
    name = "resume:" + hashlib.sha256(str(store.root).casefold().encode()).hexdigest()[:56]
    # Separate connection keeps the lock through the business commit/unlink.
    async with session.bind.connect() as connection:
        acquired = await connection.scalar(text("SELECT GET_LOCK(:name, 10)"), {"name": name})
        if acquired != 1:
            raise RuntimeError("private asset lock unavailable")
        try:
            yield
        finally:
            await connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})


class FileBatch:
    def __init__(self, store, owner):
        self.store, self.owner, self.created = store, owner, []
        self.manifest = store.root / f"{uuid4().hex}.pending"

    def write(self, content, extension):
        asset = self.store.write(self.owner, content, extension)
        self.created.append(asset)
        safe_path(self.manifest)
        self.manifest.write_text(json.dumps({"owner": self.owner, "created": [a.model_dump() for a in self.created]}), encoding="utf8")
        return asset

    def rollback_files(self):
        for asset in self.created:
            self.store.remove(self.owner, asset)
        safe_path(self.manifest).unlink(missing_ok=True)


@asynccontextmanager
async def private_asset_transaction(session, store, owner):
    owner_id(owner)
    if session.in_transaction():
        raise RuntimeError("coordinator owns transaction; do not nest begin()")
    batch = FileBatch(store, owner)
    async with root_mutex(session, store):
        transaction = await session.begin()
        session.info["resume_private_assets"] = owner, store
        try:
            try:
                yield batch
            except BaseException:
                await transaction.rollback()
                batch.rollback_files()
                raise
            else:
                # A commit exception leaves files+manifest for manual reconciliation.
                await transaction.commit()
                safe_path(batch.manifest).unlink(missing_ok=True)
        finally:
            session.info.pop("resume_private_assets", None)


async def cleanup_documents(session, store, owner, *, dry_run=True, now=None, limit=100, after=None):
    owner_id(owner)
    if session.in_transaction() or not 1 <= limit <= 1000:
        raise ValueError("cleanup requires fresh session and bounded limit")
    now = now or utcnow()
    if now.tzinfo is not None:
        raise ValueError("expected UTC naive timestamp")
    cursor = CleanupCursor.model_validate(after) if after is not None else None
    async with root_mutex(session, store):
        async with session.begin():
            stmt = select(ResumeDocumentModel).where(
                ResumeDocumentModel.user_id == owner, ResumeDocumentModel.deleted_at.is_not(None),
                ResumeDocumentModel.purge_after <= now, ResumeDocumentModel.files_purged_at.is_(None),
            )
            if cursor:
                stmt = stmt.where(or_(ResumeDocumentModel.purge_after > cursor.purge_after,
                    and_(ResumeDocumentModel.purge_after == cursor.purge_after, ResumeDocumentModel.id > cursor.id)))
            rows = list((await session.execute(stmt.order_by(ResumeDocumentModel.purge_after, ResumeDocumentModel.id)
                .limit(limit + 1).with_for_update().execution_options(populate_existing=True))).scalars())
            has_more = len(rows) > limit
            rows = rows[:limit]
            next_cursor = CleanupCursor(purge_after=rows[-1].purge_after, id=rows[-1].id).model_dump(mode="json") if has_more else None
            candidates = {}
            for row in rows:
                for asset in assets_in([row.pdf_asset, row.latex_asset]):
                    candidates[asset.key] = asset
            protected = set()
            sources = (await session.execute(select(ExperienceItemModel.source_locator).where(
                ExperienceItemModel.user_id == owner,
            ).with_for_update())).scalars()
            # Archived experiences still retain their provenance and may be reused.
            for locator in sources:
                protected.update(a.key for a in assets_in(locator))
            # Durable P2 imports keep their source protected until explicit maintenance
            # reconciles/relinquishes it, including cancelled/failed/expired batches.
            from app.models.experience_import_models import ExperienceImportBatch
            imports = (await session.execute(select(ExperienceImportBatch.source_asset).where(
                ExperienceImportBatch.user_id == owner,
                ExperienceImportBatch.files_purged_at.is_(None),
            ).with_for_update())).scalars()
            for source in imports:
                protected.update(a.key for a in assets_in(source))
            living = (await session.execute(select(ResumeDocumentModel).where(
                ResumeDocumentModel.user_id == owner,
                or_(ResumeDocumentModel.deleted_at.is_(None), ResumeDocumentModel.purge_after > now),
            ).with_for_update().execution_options(populate_existing=True))).scalars()
            for row in living:
                protected.update(a.key for a in assets_in([row.snapshot, row.pdf_asset, row.latex_asset]))
            running = (await session.execute(select(ResumeGenerationJobModel).where(
                ResumeGenerationJobModel.user_id == owner, ResumeGenerationJobModel.status.in_(["PENDING", "PROCESSING"])
            ).with_for_update().execution_options(populate_existing=True))).scalars()
            for row in running:
                protected.update(a.key for a in assets_in([row.personal_info_snapshot, row.experience_snapshot, row.traces]))
            removable = {k: a for k, a in candidates.items() if k not in protected}
            for asset in removable.values():
                if store.path(owner, asset.key).exists():
                    store.read(owner, asset)
            if not dry_run:
                # Eligibility is already a committed soft-delete. Keep its metadata
                # and hold the mutex until actual unlink and completion commit.
                # Failed unlink/commit leaves an eligible tombstone for retry.
                for asset in removable.values():
                    store.remove(owner, asset)
                for row in rows:
                    keys = {a.key for a in assets_in([row.pdf_asset, row.latex_asset])}
                    if not keys & protected:
                        row.files_purged_at = now
                await session.flush()
        return {"dry_run": dry_run, "document_ids": [r.id for r in rows],
            "removable_keys": sorted(removable), "protected_keys": sorted(set(candidates) & protected),
            "has_more": has_more, "next_cursor": next_cursor}
