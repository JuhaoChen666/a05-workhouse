"""Persistent, bounded PDF first-page thumbnail rendering."""
from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import hashlib
import time
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.private_resume_assets import LEGACY_ROOTS, PrivateAssets, private_asset_transaction
from app.infrastructure.resume_template_store import safe_path
from app.models.resume_storage_models import ResumeDocumentModel, ResumeThumbnailModel, utcnow
from app.models.session_models import ResumeModel
from app.services.resume_process_identity import process_identity

logger = logging.getLogger(__name__)
MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_PNG_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 1_000_000
MAX_EDGE = 1200
RENDER_TIMEOUT_SECONDS = 8
MAX_ATTEMPTS = 3
_render_slots = asyncio.Semaphore(1)


def _render_child(connection, pdf_bytes: bytes):
    try:
        import pypdfium2 as pdfium
        from PIL import Image

        document = pdfium.PdfDocument(pdf_bytes)
        try:
            if len(document) < 1:
                raise ValueError("empty_pdf")
            page = document[0]
            try:
                width, height = page.get_size()
                if width <= 0 or height <= 0 or width * height > 200_000_000:
                    raise ValueError("page_dimensions_invalid")
                scale = min(1.0, MAX_EDGE / max(width, height), (MAX_PIXELS / (width * height)) ** 0.5)
                bitmap = page.render(scale=scale, rotation=0)
                image = bitmap.to_pil().convert("RGB")
                try:
                    output = BytesIO()
                    image.save(output, format="PNG", optimize=True)
                    data = output.getvalue()
                    if len(data) > MAX_PNG_BYTES or image.width * image.height > MAX_PIXELS:
                        raise ValueError("thumbnail_limits_exceeded")
                    connection.send_bytes(data)
                finally:
                    image.close()
                    bitmap.close()
            finally:
                page.close()
        finally:
            document.close()
    except BaseException as error:
        try:
            connection.send_bytes(("ERROR:" + type(error).__name__).encode("ascii", "replace"))
        except (BrokenPipeError, OSError):
            pass
    finally:
        connection.close()


def render_first_page(pdf_bytes: bytes, *, timeout: float = RENDER_TIMEOUT_SECONDS) -> bytes:
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes or len(pdf_bytes) > MAX_SOURCE_BYTES:
        raise ValueError("source_size_invalid")
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_render_child, args=(send, pdf_bytes), name="resume-thumbnail-render")
    try:
        process.start()
        send.close()
        identity = process_identity(process.pid)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if receive.poll(min(0.05, max(0.0, deadline - time.monotonic()))):
                result = receive.recv_bytes(MAX_PNG_BYTES + 128)
                process.join(timeout=2)
                _stop_owned_process(process, identity)
                if result.startswith(b"ERROR:"):
                    raise ValueError(result[6:].decode("ascii", "replace"))
                return result
            if not process.is_alive():
                process.join(timeout=0)
                raise ValueError("renderer_exited_without_result")
        _stop_owned_process(process, identity)
        raise TimeoutError("thumbnail_render_timeout")
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            _stop_owned_process(process, locals().get("identity"))


def _stop_owned_process(process, identity):
    if process.pid is None:
        return
    process.join(timeout=0)
    if not process.is_alive():
        return
    current = process_identity(process.pid)
    if identity is None or current != identity:
        raise RuntimeError("renderer_identity_unconfirmed")
    process.terminate()
    process.join(timeout=2)
    if process.is_alive():
        current = process_identity(process.pid)
        if current != identity:
            raise RuntimeError("renderer_identity_unconfirmed")
        process.kill()
        process.join(timeout=2)
    if process.is_alive():
        raise RuntimeError("renderer_stop_unconfirmed")


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def register_thumbnail(session, owner: int, kind: str, source_id: str | int, source_sha256: str):
    """Best-effort registration in a savepoint so a derived failure never rolls back the source."""
    if kind not in {"uploaded", "generated"} or len(source_sha256) != 64:
        raise ValueError("invalid thumbnail source")
    now = utcnow()
    try:
        async with session.begin_nested():
            row = (await session.execute(select(ResumeThumbnailModel).where(
                ResumeThumbnailModel.user_id == owner, ResumeThumbnailModel.source_kind == kind,
                ResumeThumbnailModel.source_id == str(source_id)).with_for_update())).scalar_one_or_none()
            if row is None:
                row = ResumeThumbnailModel(user_id=owner, source_kind=kind, source_id=str(source_id),
                    source_sha256=source_sha256, asset=None, status="PENDING", attempt_count=0,
                    error_code=None, available_at=now, created_at=now, updated_at=now)
                session.add(row)
            elif row.source_sha256 != source_sha256:
                row.source_sha256, row.asset, row.status = source_sha256, None, "PENDING"
                row.attempt_count, row.error_code, row.available_at, row.updated_at = 0, None, now, now
            await session.flush()
    except Exception as error:
        logger.warning("thumbnail registration failed kind=%s error=%s", kind, type(error).__name__)


async def _source_bytes(session, store: PrivateAssets, owner: int, task, *, lock=False):
    lock_clause = lambda statement: statement.with_for_update() if lock else statement
    if task.source_kind == "uploaded":
        try:
            source_id = int(task.source_id)
        except ValueError:
            raise ValueError("uploaded_source_invalid") from None
        statement = select(ResumeModel).where(ResumeModel.id == source_id, ResumeModel.user_id == owner)
        row = (await session.execute(lock_clause(statement))).scalar_one_or_none()
        if row is None:
            raise ValueError("source_missing")
        path = safe_path(Path(row.local_path)).resolve(strict=True)
        allowed = False
        for root in LEGACY_ROOTS:
            canonical = safe_path(root).resolve()
            if path != canonical and canonical in path.parents:
                allowed = True
                break
        if not allowed or not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("source_unavailable")
        content = path.read_bytes()
    elif task.source_kind == "generated":
        statement = select(ResumeDocumentModel).where(
            ResumeDocumentModel.id == task.source_id, ResumeDocumentModel.user_id == owner,
            ResumeDocumentModel.deleted_at.is_(None))
        row = (await session.execute(lock_clause(statement))).scalar_one_or_none()
        if row is None or row.format != "latex" or not row.pdf_asset:
            raise ValueError("source_missing")
        content = store.read(owner, row.pdf_asset)
    else:
        raise ValueError("source_kind_invalid")
    if _digest(content) != task.source_sha256:
        raise ValueError("source_changed")
    return content


async def run_thumbnail_once(factory, store: PrivateAssets | None = None) -> bool:
    """Process at most one durable thumbnail task; SQL/asset errors stay isolated."""
    database = factory.kw["bind"].url.database
    scope = hashlib.sha256(database.casefold().encode()).hexdigest()[:16]
    async with factory.kw["bind"].connect() as lease:
        lock = f"resume-thumbnail:{scope}"
        if not (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": lock})).scalar():
            return False
        try:
            return await _run_thumbnail_once_locked(factory, store)
        finally:
            await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": lock})


async def _run_thumbnail_once_locked(factory, store: PrivateAssets | None) -> bool:
    now = utcnow()
    try:
        async with factory() as session, session.begin():
            stale_before = now - timedelta(minutes=2)
            stale = (await session.execute(select(ResumeThumbnailModel).where(
                ResumeThumbnailModel.status == "PROCESSING", ResumeThumbnailModel.updated_at < stale_before
            ).order_by(ResumeThumbnailModel.updated_at).limit(16).with_for_update(skip_locked=True))).scalars().all()
            for row in stale:
                if row.attempt_count >= MAX_ATTEMPTS:
                    row.status, row.error_code = "FAILED", "WORKER_INTERRUPTED"
                else:
                    row.status, row.available_at, row.error_code = "PENDING", now, "WORKER_INTERRUPTED"
                row.updated_at = now
            task = (await session.execute(select(ResumeThumbnailModel).where(
                ResumeThumbnailModel.status == "PENDING", ResumeThumbnailModel.available_at <= now
            ).order_by(ResumeThumbnailModel.created_at, ResumeThumbnailModel.id).limit(1)
                .with_for_update(skip_locked=True))).scalar_one_or_none()
            if task is None:
                return bool(stale)
            task.status, task.attempt_count, task.updated_at = "PROCESSING", task.attempt_count + 1, now
            owner, task_id = task.user_id, task.id
            kind, source_id, source_hash = task.source_kind, task.source_id, task.source_sha256
    except SQLAlchemyError as error:
        logger.info("thumbnail queue unavailable error=%s", type(error).__name__)
        return False

    try:
        if store is None:
            from app.infrastructure.resume_runtime import asset_store
            store = asset_store()
        async with _render_slots:
            async with factory() as session:
                async with session.begin():
                    task = await session.get(ResumeThumbnailModel, task_id)
                    if task is None or task.status != "PROCESSING":
                        return True
                    pdf_bytes = await _source_bytes(session, store, owner, task)
            png_bytes = await asyncio.to_thread(render_first_page, pdf_bytes)
        async with factory() as session:
            async with private_asset_transaction(session, store, owner) as batch:
                task = (await session.execute(select(ResumeThumbnailModel).where(
                    ResumeThumbnailModel.id == task_id).with_for_update())).scalar_one_or_none()
                if task is None or task.status != "PROCESSING" or task.source_sha256 != source_hash:
                    return True
                # Re-check the source while holding the private-asset mutex and
                # database transaction so deletion/retention cannot race the write.
                await _source_bytes(session, store, owner, task, lock=True)
                asset = batch.write(png_bytes, "png").model_dump(mode="json")
                task.asset, task.status, task.error_code, task.updated_at = asset, "READY", None, utcnow()
    except Exception as error:
        logger.warning("thumbnail render failed task=%s error=%s", task_id, type(error).__name__)
        async with factory() as session, session.begin():
            task = (await session.execute(select(ResumeThumbnailModel).where(
                ResumeThumbnailModel.id == task_id).with_for_update())).scalar_one_or_none()
            if task is not None and task.status == "PROCESSING":
                task.status = "FAILED" if task.attempt_count >= MAX_ATTEMPTS else "PENDING"
                task.error_code = type(error).__name__[:64]
                task.available_at = utcnow() + timedelta(seconds=min(300, 2 ** task.attempt_count))
                task.updated_at = utcnow()
    return True
