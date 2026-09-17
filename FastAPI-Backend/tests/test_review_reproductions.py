"""Correct-behavior regressions for defects originally reproduced in ab20ac5.

All DB/file changes use disposable fixtures.
The legacy route business body is executed unchanged via AST, avoiding app
startup/config/AI imports. HTTPException is a small framework exception stand-in;
no HTTP/ASGI transport behavior is claimed and the database is real MySQL.
"""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from functools import partial
import pytest
from sqlalchemy import text
from uuid import uuid4
from conftest import migrate
from app.models.session_models import ResumeModel
from app.models.resume_storage_contracts import DocumentInput
from app.models.resume_storage_models import ResumeDocumentModel
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper
from app.infrastructure.private_resume_assets import PrivateAssets, private_asset_transaction, cleanup_documents
from app.infrastructure.legacy_resume_deletion import delete_legacy_resume, LegacyResumeNotFound, LegacyResumeInUse, retry_legacy_file_deletions
from test_storage_mysql import approve_fixture, complete_fixture, document_outputs
from test_storage_boundaries import EXAMPLES


class RouteHTTPError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def actual_delete_business_function(pending_root):
    source = Path(__file__).resolve().parents[1] / "app/api/resume_routes.py"
    module = ast.parse(source.read_text(encoding="utf8"), filename=str(source))
    function = next(node for node in module.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "delete_resume")
    function.decorator_list = []
    function.args.defaults = []
    for argument in function.args.args:
        argument.annotation = None
    function.returns = None
    namespace = {"HTTPException": RouteHTTPError,
        "delete_legacy_resume": partial(delete_legacy_resume, pending_root=pending_root),
        "LegacyResumeNotFound": LegacyResumeNotFound, "LegacyResumeInUse": LegacyResumeInUse}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["delete_resume"]


async def test_legacy_fk_rejects_delete_and_preserves_pdf(sessions, tmp_path):
    pdf = tmp_path / "legacy-source.pdf"
    pdf.write_bytes(b"disposable source PDF")
    async with sessions() as session:
        async with session.begin():
            record = await session.get(ResumeModel, 1)
            record.local_path = str(pdf)
            item = await ResumeStorageMapper(session, 71).create_experience({
                **EXAMPLES[2], "source_type": "PDF_IMPORT", "source_resume_id": 1,
            })
            item_id = item.id
        delete = actual_delete_business_function(tmp_path / "pending")
        with pytest.raises(RouteHTTPError) as error:
            await delete(SimpleNamespace(id=1, user_id=71, filename="sentinel.pdf"), session)
        assert error.value.status_code == 409
        assert pdf.read_bytes() == b"disposable source PDF"
        assert not list((tmp_path / "pending").iterdir())
        async with session.begin():
            assert await session.get(ResumeModel, 1) is not None
            assert (await ResumeStorageMapper(session, 71).get_experience(item_id)).source_resume_id == 1
    print("FIXED: source FK returns409, PDF and both records preserved")


@pytest.mark.parametrize("blocked_by_copy", [False, True], ids=["already-purged-head", "protected-head"])
async def test_cleanup_limit_advances_past_completed_or_protected_head(sessions, tmp_path, blocked_by_copy):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        async with session.begin():
            await approve_fixture(session)
        async with private_asset_transaction(session, store, 71) as batch:
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)
            first_asset = batch.write(b"first output", "pdf")
            second_asset = batch.write(b"second output", "pdf")
            first = await mapper.create_document({"name": "First", "generation_job_id": job.id}, pdf_asset=first_asset, latex_asset=batch.write(b"first latex", "tex"))
            if blocked_by_copy:
                await mapper.copy_document(first.id, "Living copy")
            second = await mapper.create_document({"name": "Second", "generation_job_id": job.id}, pdf_asset=second_asset, latex_asset=batch.write(b"second latex", "tex"))
            await mapper.delete_document(first.id, retention_days=0)
            await mapper.delete_document(second.id, retention_days=0)
            first_id, second_id = first.id, second.id
        one = await cleanup_documents(session, store, 71, dry_run=False, limit=1)
        assert one["document_ids"] == [first_id] and one["has_more"] and one["next_cursor"]
        # Protected heads need cursor progression. Completed heads are filtered even without a cursor.
        two = await cleanup_documents(session, store, 71, dry_run=False, limit=1, after=one["next_cursor"] if blocked_by_copy else None)
        assert two["document_ids"] == [second_id] and not two["has_more"]
        assert not store.path(71, second_asset.key).exists()
        if blocked_by_copy:
            assert store.read(71, first_asset) == b"first output"
        else:
            three = await cleanup_documents(session, store, 71, dry_run=False, limit=1)
            assert three["document_ids"] == []
        async with session.begin():
            assert (await session.get(ResumeDocumentModel, second_id)).files_purged_at is not None
            if not blocked_by_copy:
                assert (await session.get(ResumeDocumentModel, first_id)).files_purged_at is not None
    print(f"FIXED: bounded cleanup advances and removes second; protected head={blocked_by_copy}")


@pytest.mark.parametrize("archived", [False, True], ids=["active-experience", "archived-experience"])
async def test_cleanup_preserves_experience_sources(sessions, tmp_path, archived):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        async with session.begin():
            await approve_fixture(session)
        async with private_asset_transaction(session, store, 71) as batch:
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)  # No source in completed job snapshot.
            pdf = batch.write(b"source also used as output", "pdf")
            doc = await mapper.create_document({"name": "Expired output", "generation_job_id": job.id}, pdf_asset=pdf, latex_asset=batch.write(b"latex", "tex"))
            item = await mapper.create_experience({
                **EXAMPLES[2], "source_type": "PDF_IMPORT", "source_locator": {"file_asset": pdf.model_dump()},
                "is_archived": archived,
            })
            item_id = item.id
            await mapper.delete_document(doc.id, retention_days=0)
        dry = await cleanup_documents(session, store, 71)
        assert pdf.key not in dry["removable_keys"] and pdf.key in dry["protected_keys"]
        await cleanup_documents(session, store, 71, dry_run=False)
        assert store.read(71, pdf) == b"source also used as output"
        async with session.begin():
            item = await mapper.get_experience(item_id)
            assert item.source_locator["file_asset"]["key"] == pdf.key and item.is_archived == archived
        # Removing the provenance reference makes the expired output eligible again.
        async with private_asset_transaction(session, store, 71):
            await mapper.update_experience(item_id, {**EXAMPLES[2], "is_archived": archived}, expected_revision=1)
        await cleanup_documents(session, store, 71, dry_run=False)
        assert not store.path(71, pdf.key).exists()
    print(f"FIXED: source survives until reference removed; archived={archived}")


@pytest.mark.parametrize("outputs", ["none", "pdf-only", "latex-only"])
async def test_latex_documents_reject_missing_outputs(sessions, tmp_path, outputs):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        async with session.begin():
            await approve_fixture(session)
        with pytest.raises(ValueError, match="both PDF and LaTeX"):
            async with private_asset_transaction(session, store, 71) as batch:
                mapper = ResumeStorageMapper(session, 71)
                job = await complete_fixture(mapper)
                files = {}
                if outputs == "pdf-only":
                    files["pdf_asset"] = batch.write(b"pdf fixture", "pdf")
                elif outputs == "latex-only":
                    files["latex_asset"] = batch.write(b"latex fixture", "tex")
                await mapper.create_document({"name": "Incomplete", "generation_job_id": job.id}, **files)
        async with session.begin():
            assert not await mapper.list_documents()
        assert not list(store.root.rglob("*.pdf")) and not list(store.root.rglob("*.tex"))
    print(f"FIXED: outputs={outputs} rejected and fresh files compensated")


async def test_blank_name_rejected_and_all_names_normalized(sessions, private_store):
    with pytest.raises(ValueError): DocumentInput(name="   ", generation_job_id="fixture")
    async with sessions() as session:
        async with private_asset_transaction(session, private_store, 71) as files:
            await approve_fixture(session)
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)
            document = await mapper.create_document({"name": "  Created  ", "generation_job_id": job.id}, **document_outputs(files))
            document_id = document.id
        async with session.begin():
            assert (await mapper.get_document(document_id)).name == "Created"
            for operation in (mapper.rename_document(document_id, "   "), mapper.copy_document(document_id, "   "), mapper.save_legacy_markdown("old", "   ")):
                with pytest.raises(ValueError):
                    await operation
            assert (await mapper.rename_document(document_id, "  Renamed  ")).name == "Renamed"
            assert (await mapper.save_legacy_markdown("old", "  Legacy  ")).name == "Legacy"
        async with private_asset_transaction(session, private_store, 71):
            assert (await mapper.copy_document(document_id, "  Copy  ")).name == "Copy"
    print("FIXED: all four name entrypoints reject blank and trim valid names")


async def test_blank_name_contract_consistency_without_database():
    with pytest.raises(ValueError): DocumentInput(name="   ", generation_job_id="fixture")
    mapper = ResumeStorageMapper(None, 71)
    for operation in (mapper.rename_document("fixture", "   "), mapper.copy_document("fixture", "   "), mapper.save_legacy_markdown("old", "   ")):
        with pytest.raises(ValueError):
            await operation
    print("FIXED without DB: all name entrypoints reject whitespace before accessing session")


async def test_legacy_unreferenced_delete_commits_then_removes_pdf(sessions, tmp_path):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"unreferenced")
    async with sessions() as session:
        async with session.begin():
            (await session.get(ResumeModel, 1)).local_path = str(pdf)
        result = await actual_delete_business_function(tmp_path / "pending")(
            SimpleNamespace(id=1, user_id=71, filename="sentinel.pdf"), session)
        assert result["code"] == 200 and not result["data"]["file_cleanup_pending"]
        assert not pdf.exists() and not list((tmp_path / "pending").iterdir())
        async with session.begin(): assert await session.get(ResumeModel, 1) is None


async def test_legacy_commit_failure_preserves_pdf_and_retry_keeps_live_row(sessions, tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"must stay")
    async with sessions() as session:
        async with session.begin(): (await session.get(ResumeModel, 1)).local_path = str(pdf)
        async def fail_commit(): raise RuntimeError("commit failed before success")
        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", fail_commit)
            with pytest.raises(RouteHTTPError) as error:
                await actual_delete_business_function(tmp_path / "pending")(
                    SimpleNamespace(id=1, user_id=71, filename="sentinel.pdf"), session)
            assert error.value.status_code == 500
        assert pdf.read_bytes() == b"must stay"
        report = await retry_legacy_file_deletions(session, pending_root=tmp_path / "pending")
        assert len(report["retained"]) == 1 and not report["completed"]
        async with session.begin(): assert await session.get(ResumeModel, 1) is not None


async def test_legacy_file_unlink_failure_reports_pending_and_retries(sessions, tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"retry")
    async with sessions() as session:
        async with session.begin(): (await session.get(ResumeModel, 1)).local_path = str(pdf)
        original_unlink = Path.unlink
        def fail_pdf(path, *args, **kwargs):
            if path == pdf: raise PermissionError("fixture locked file")
            return original_unlink(path, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(Path, "unlink", fail_pdf)
            result = await actual_delete_business_function(tmp_path / "pending")(
                SimpleNamespace(id=1, user_id=71, filename="sentinel.pdf"), session)
        assert result["code"] == 200 and result["data"]["file_cleanup_pending"] and pdf.exists()
        async with session.begin(): assert await session.get(ResumeModel, 1) is None
        report = await retry_legacy_file_deletions(session, pending_root=tmp_path / "pending")
        assert len(report["completed"]) == 1 and not report["failed"]
        assert not pdf.exists() and not list((tmp_path / "pending").iterdir())


async def test_legacy_lost_commit_ack_preserves_pdf_until_reconciliation(sessions, tmp_path, monkeypatch):
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"lost ack")
    async with sessions() as session:
        async with session.begin(): (await session.get(ResumeModel, 1)).local_path = str(pdf)
        original_commit = session.commit
        async def lost_ack():
            await original_commit()
            raise RuntimeError("acknowledgement lost")
        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", lost_ack)
            with pytest.raises(RouteHTTPError):
                await actual_delete_business_function(tmp_path / "pending")(
                    SimpleNamespace(id=1, user_id=71, filename="sentinel.pdf"), session)
        assert pdf.exists()
        report = await retry_legacy_file_deletions(session, pending_root=tmp_path / "pending")
        assert len(report["completed"]) == 1 and not pdf.exists()


@pytest.mark.parametrize("fail_after", [0, 1])
async def test_cleanup_failed_unlink_leaves_retryable_tombstone(sessions, private_store, monkeypatch, fail_after):
    async with sessions() as session:
        async with private_asset_transaction(session, private_store, 71) as files:
            await approve_fixture(session)
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)
            outputs = document_outputs(files)
            doc = await mapper.create_document({"name":"Retry", "generation_job_id":job.id}, **outputs)
            await mapper.delete_document(doc.id, retention_days=0)
            doc_id = doc.id
        original_remove, calls = private_store.remove, 0
        def fail_remove(owner, asset):
            nonlocal calls
            if calls == fail_after: raise PermissionError("fixture unlink failure")
            calls += 1
            return original_remove(owner, asset)
        with monkeypatch.context() as patch:
            patch.setattr(private_store, "remove", fail_remove)
            with pytest.raises(PermissionError): await cleanup_documents(session, private_store, 71, dry_run=False)
        async with session.begin():
            assert (await session.get(ResumeDocumentModel, doc_id)).files_purged_at is None
        retry = await cleanup_documents(session, private_store, 71, dry_run=False)
        assert retry["document_ids"] == [doc_id]
        assert all(not private_store.path(71, a.key).exists() for a in outputs.values())
        async with session.begin():
            assert (await session.get(ResumeDocumentModel, doc_id)).files_purged_at is not None


async def test_incremental_migration_refuses_incomplete_old_document_without_changes(sessions, mysql_schema):
    async with sessions() as session:
        async with session.begin():
            await approve_fixture(session)
            job_id = (await complete_fixture(ResumeStorageMapper(session, 71))).id
        await asyncio.to_thread(migrate, mysql_schema, "downgrade", "phase1_storage_001")
        doc_id = str(uuid4())
        async with session.begin():
            await session.execute(text("INSERT INTO resume_documents (id,user_id,name,format,generation_job_id,snapshot,created_at,updated_at) VALUES (:id,71,'Old incomplete','latex',:job,JSON_OBJECT(),NOW(6),NOW(6))"), {"id":doc_id,"job":job_id})
        with pytest.raises(RuntimeError, match="1 incomplete latex documents"):
            await asyncio.to_thread(migrate, mysql_schema)
        async with session.begin():
            assert await session.scalar(text("SELECT version_num FROM resume_phase1_alembic_version")) == "phase1_storage_001"
            assert await session.scalar(text("SELECT COUNT(*) FROM resume_documents WHERE id=:id AND pdf_asset IS NULL AND latex_asset IS NULL"), {"id":doc_id}) == 1


async def test_incremental_migration_rechecks_old_purge_intent_markers(sessions, mysql_schema, private_store):
    async with sessions() as session:
        async with private_asset_transaction(session, private_store, 71) as files:
            await approve_fixture(session)
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)
            outputs = document_outputs(files)
            doc = await mapper.create_document({"name":"Old intent", "generation_job_id":job.id}, **outputs)
            await mapper.delete_document(doc.id, retention_days=0)
            doc.files_purged_at = doc.deleted_at  # Simulate001 committed intent before a failed unlink.
            doc_id = doc.id
        await asyncio.to_thread(migrate, mysql_schema, "downgrade", "phase1_storage_001")
        await asyncio.to_thread(migrate, mysql_schema)
        report = await cleanup_documents(session, private_store, 71, dry_run=False)
        assert report["document_ids"] == [doc_id]
        assert all(not private_store.path(71, asset.key).exists() for asset in outputs.values())
