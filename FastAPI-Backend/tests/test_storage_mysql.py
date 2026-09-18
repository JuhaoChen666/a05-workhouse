from copy import deepcopy
from datetime import timedelta
import json
import pytest
from sqlalchemy import select, text, create_engine, inspect
from sqlalchemy.exc import DBAPIError, IntegrityError
from conftest import migrate
from test_storage_boundaries import EXAMPLES
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper, AssetNotFound, RevisionConflict
from app.infrastructure.resume_template_store import BUILTIN_ROOT, initialize_templates, TemplateVersionConflict
from app.infrastructure.private_resume_assets import PrivateAssets, private_asset_transaction, cleanup_documents
from app.models.resume_storage_models import ExperienceItemModel as Experience, ResumeTemplateModel as Template, ResumeGenerationJobModel as Job, ResumeDocumentModel as Document, utcnow


def request(**values):
    return {"template_version": "1.0.0", "jd_text": "Python backend developer", **values}


async def approve_fixture(session):
    await initialize_templates(session)
    template = await session.get(Template, ("tpl-billryan-classic", "1.0.0"))
    template.validation_status, template.is_enabled = "VALIDATED", True
    template.validation_details = {"test_fixture_only": True}
    await session.flush()


async def complete_fixture(mapper, **values):
    job = await mapper.create_job(request(**values))
    await mapper.update_job(job.id, status="PROCESSING", stage="FIXTURE", progress=20)
    await mapper.update_job(job.id, status="COMPILED", stage="FIXTURE", progress=100)
    return job


def document_outputs(files):
    # Storage fixtures, never a claim of successful rendering/compilation.
    return {"pdf_asset": files.write(b"pdf fixture", "pdf"),
        "latex_asset": files.write(b"latex fixture", "tex")}


async def test_categories_revision_owner_and_atomic_compare(sessions):
    async with sessions() as session:
        async with session.begin():
            owner = ResumeStorageMapper(session, 71)
            ids = [(await owner.create_experience(data)).id for data in EXAMPLES]
        async with session.begin():
            assert len(await owner.list_experiences()) == 5
            for id_, example in zip(ids, EXAMPLES):
                item = await owner.get_experience(id_)
                assert item.type == example["type"] and item.revision == 1 and isinstance(item.attributes, dict)
            item = await owner.update_experience(ids[2], {**EXAMPLES[2], "title": "Updated", "sort_order": 7}, expected_revision=1)
            assert item.revision == 2 and item.sort_order == 7
            with pytest.raises(RevisionConflict):
                await owner.update_experience(item.id, EXAMPLES[2], expected_revision=1)
            await owner.archive_experience(item.id, expected_revision=2)
            assert item.revision == 3 and len(await owner.list_experiences()) == 4
        async with session.begin():
            other = ResumeStorageMapper(session, 72)
            assert not await other.list_experiences()
            for id_ in ids:
                with pytest.raises(AssetNotFound): await other.get_experience(id_)
                with pytest.raises(AssetNotFound): await other.update_experience(id_, EXAMPLES[0], expected_revision=1)
                with pytest.raises(AssetNotFound): await other.archive_experience(id_, expected_revision=1)


async def test_transaction_rollback_and_legacy_provenance(sessions):
    async with sessions() as session:
        with pytest.raises(RuntimeError, match="intentional"):
            async with session.begin():
                await approve_fixture(session)
                mapper = ResumeStorageMapper(session, 71)
                item = await mapper.create_experience({**EXAMPLES[2], "source_type": "PDF_IMPORT", "source_resume_id": 1, "source_locator": {"page": 1}})
                await mapper.create_job(request(selected_item_ids=[item.id]))
                raise RuntimeError("intentional rollback")
        async with session.begin():
            for model in (Experience, Template, Job, Document):
                assert not list((await session.execute(select(model))).scalars())
            assert await session.scalar(text("SELECT content_text FROM resumes WHERE id=1")) == "original"
            with pytest.raises(AssetNotFound):
                await ResumeStorageMapper(session, 72).create_experience({**EXAMPLES[0], "source_type": "PDF_IMPORT", "source_resume_id": 1})


async def test_all_template_versions_seed_and_content_conflict(sessions, tmp_path):
    async with sessions() as session:
        async with session.begin():
            assert await initialize_templates(session) == 10
            assert await initialize_templates(session) == 0
            rows = list((await session.execute(select(Template))).scalars())
            assert {row.id for row in rows} == {"tpl-" + name for name in ("billryan-classic", "modern-twocol", "altacv", "jakes-resume", "huajh-resume", "zheyuye-chinese")}
            assert {(row.id, row.version) for row in rows if row.is_enabled} == {
                ("tpl-billryan-classic", "1.1.0"), ("tpl-modern-twocol", "1.1.0"),
                ("tpl-billryan-classic", "1.2.0"), ("tpl-modern-twocol", "1.2.0")}
            with pytest.raises(ValueError, match="validated"):
                await ResumeStorageMapper(session, 71).create_job(request())
            original = deepcopy((await session.get(Template, ("tpl-altacv", "1.0.0"))).resources)
        root = tmp_path / "templates"
        root.mkdir()
        bundle = root / "altacv"
        bundle.mkdir()
        for path in (BUILTIN_ROOT / "altacv").iterdir():
            (bundle / path.name).write_bytes(path.read_bytes())
        with (bundle / "altacv.cls").open("ab") as stream: stream.write(b"\n% modified fixture\n")
        with pytest.raises(TemplateVersionConflict):
            async with session.begin(): await initialize_templates(session, root)
        async with session.begin():
            assert (await session.get(Template, ("tpl-altacv", "1.0.0"))).resources == original


async def test_duplicate_template_preflight_writes_nothing(sessions, tmp_path):
    root = tmp_path / "duplicates"
    root.mkdir()
    for name in ("first", "second"):
        bundle = root / name
        bundle.mkdir()
        for path in (BUILTIN_ROOT / "modern-twocol").iterdir(): (bundle / path.name).write_bytes(path.read_bytes())
    async with sessions() as session:
        with pytest.raises(TemplateVersionConflict, match="duplicate"):
            async with session.begin(): await initialize_templates(session, root)
        async with session.begin(): assert not list((await session.execute(select(Template))).scalars())


async def test_publish_new_version_preserves_different_historical_bytes(sessions, tmp_path):
    root = tmp_path / "version-publication"
    root.mkdir()
    for name in ("billryan-classic-v1.1.0", "billryan-classic-v1.2.0"):
        bundle = root / name
        bundle.mkdir()
        for path in (BUILTIN_ROOT / name).iterdir():
            (bundle / path.name).write_bytes(path.read_bytes())
    async with sessions() as session:
        async with session.begin():
            await initialize_templates(session)
            old = await session.get(Template, ("tpl-billryan-classic", "1.1.0"))
            original_source, original_resources = old.main_source, deepcopy(old.resources)
        with (root / "billryan-classic-v1.1.0" / "resume.tex.j2").open("ab") as stream:
            stream.write(b"\n% different historical checkout bytes\n")
        async with session.begin():
            assert await initialize_templates(session, root, version="1.2.0") == 0
        with pytest.raises(TemplateVersionConflict):
            async with session.begin():
                await initialize_templates(session, root)
        async with session.begin():
            await session.refresh(old)
            assert old.main_source == original_source and old.resources == original_resources


async def test_snapshots_actual_jd_selection_and_cross_owner(sessions, private_store):
    async with sessions() as session:
        async with private_asset_transaction(session, private_store, 71) as files:
            await approve_fixture(session)
            mapper, other = ResumeStorageMapper(session, 71), ResumeStorageMapper(session, 72)
            item = await mapper.create_experience(EXAMPLES[2])
            foreign = await other.create_experience(EXAMPLES[3])
            with pytest.raises(AssetNotFound): await mapper.create_job(request(selected_item_ids=[foreign.id]))
            with pytest.raises(ValueError, match="jobContent"):
                await mapper.create_job(request(jd_source_type="JOB_ID", jd_text=None, job_id="12"), resolved_job={"id":12,"position":"Backend"})
            personal, source = {"name": "Original"}, {"id":12,"jobContent":"Actual JD"}
            job = await mapper.create_job(request(jd_source_type="JOB_ID", jd_text=None, job_id="12", personal_info=personal), resolved_job=source)
            assert len(job.experience_snapshot) == 1
            empty = await mapper.create_job(request(selected_item_ids=[]))
            assert empty.experience_snapshot == []
            frozen = deepcopy(job.experience_snapshot)
            personal["name"], source["jobContent"] = "Changed", "Changed"
            await mapper.update_experience(item.id, {**EXAMPLES[2], "bullets": ["Changed"]}, expected_revision=1)
            await mapper.update_job(job.id, status="PROCESSING", stage="TEST", progress=40)
            await mapper.update_job(job.id, status="COMPILED", stage="TEST", progress=100)
            doc = await mapper.create_document({"name":"Frozen", "generation_job_id":job.id}, **document_outputs(files))
            job_id, doc_id = job.id, doc.id
        async with session.begin():
            await session.refresh(job)
            assert job.experience_snapshot == frozen and frozen[0]["revision"] == 1
            assert job.personal_info_snapshot["name"] == "Original" and job.jd_snapshot["text"] == "Actual JD"
            assert doc.snapshot["experience_snapshot"] == frozen
            for operation in (other.get_job(job_id), other.get_document(doc_id), other.rename_document(doc_id, "Stolen"), other.delete_document(doc_id), other.copy_document(doc_id, "Stolen")):
                with pytest.raises(AssetNotFound): await operation
            assert not await other.list_jobs() and not await other.list_documents()


async def test_retry_state_rules_and_frozen_template(sessions, private_store):
    async with sessions() as session:
        async with private_asset_transaction(session, private_store, 71) as files:
            await approve_fixture(session)
            mapper = ResumeStorageMapper(session, 71)
            job = await mapper.create_job(request())
            frozen = deepcopy(job.template_snapshot)
            with pytest.raises(ValueError): await mapper.update_job(job.id, status="COMPILED", stage="BAD", progress=100)
            with pytest.raises(ValueError, match="COMPILED"): await mapper.create_document({"name":"Early", "generation_job_id":job.id}, **document_outputs(files))
            await mapper.update_job(job.id, status="FAILED", stage="TEST", progress=0, error={"message":"fixture"})
            await mapper.retry_job(job.id)
            assert job.status == "PENDING" and job.retry_count == 1 and job.error is None
            template = await session.get(Template, ("tpl-billryan-classic", "1.0.0"))
            template.is_enabled = False
            await session.flush()
            assert job.template_snapshot == frozen
            await mapper.update_job(job.id, status="PROCESSING", stage="TEST", progress=50)
            with pytest.raises(ValueError): await mapper.update_job(job.id, status="COMPILED", stage="TEST", progress=99)


async def test_json_check_fk_and_orm_immutability(sessions, private_store):
    async with sessions() as session:
        async with private_asset_transaction(session, private_store, 71) as files:
            await approve_fixture(session)
            mapper = ResumeStorageMapper(session, 71)
            item = await mapper.create_experience(EXAMPLES[2])
            job = await complete_fixture(mapper)
            doc = await mapper.create_document({"name":"Constraints", "generation_job_id":job.id}, **document_outputs(files))
            item_id, job_id, doc_id = item.id, job.id, doc.id
            assert await session.scalar(text("SELECT JSON_UNQUOTE(JSON_EXTRACT(attributes,'$.role')) FROM experience_items WHERE id=:id"), {"id":item_id}) == "Developer"
        for sql in ("UPDATE experience_items SET attributes=JSON_ARRAY() WHERE id=:id", "UPDATE experience_items SET revision=0 WHERE id=:id"):
            with pytest.raises(DBAPIError) as error:
                async with session.begin(): await session.execute(text(sql), {"id":item_id})
            assert error.value.orig.args[0] == 3819
        with pytest.raises(IntegrityError):
            async with session.begin(): await session.execute(text("UPDATE resume_documents SET user_id=72 WHERE id=:id"), {"id":doc_id})
        for field in ("pdf_asset", "latex_asset"):
            with pytest.raises(DBAPIError) as error:
                async with session.begin():
                    await session.execute(text(f"UPDATE resume_documents SET {field}=NULL WHERE id=:id"), {"id":doc_id})
            assert error.value.orig.args[0] == 3819
        for model, key, field, value in ((Template, ("tpl-billryan-classic","1.0.0"), "main_source", "changed"), (Job, job_id, "jd_snapshot", {"text":"changed"}), (Document, doc_id, "snapshot", {})):
            with pytest.raises(ValueError, match="immutable"):
                async with session.begin():
                    row = await session.get(model, key)
                    setattr(row, field, value)
                    await session.flush()


async def test_legacy_markdown_owner_and_soft_delete(sessions):
    async with sessions() as session:
        async with session.begin():
            mapper, other = ResumeStorageMapper(session, 71), ResumeStorageMapper(session, 72)
            assert await mapper.read_legacy_markdown("old") == "# Legacy"
            with pytest.raises(AssetNotFound): await other.read_legacy_markdown("old")
            with pytest.raises(AssetNotFound): await other.save_legacy_markdown("old", "Foreign")
            doc = await mapper.save_legacy_markdown("old", "History")
            await mapper.rename_document(doc.id, "Renamed")
            copy = await mapper.copy_document(doc.id, "Copy")
            assert copy.markdown_content == doc.markdown_content
            await mapper.delete_document(doc.id)
            purge = doc.purge_after
            await mapper.delete_document(doc.id, retention_days=0)
            assert doc.purge_after == purge and purge - doc.deleted_at == timedelta(days=30)
            with pytest.raises(AssetNotFound): await mapper.get_document(doc.id)
            assert len(await mapper.list_documents()) == 1
            assert await session.scalar(text("SELECT optimized_text FROM resume_optimizations WHERE session_id='old'")) == "# Legacy"


async def test_file_commit_rollback_copy_and_cleanup(sessions, tmp_path):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        async with session.begin(): await approve_fixture(session)
        with pytest.raises(RuntimeError, match="intentional"):
            async with private_asset_transaction(session, store, 71) as batch:
                asset = batch.write(b"fixture pdf", "pdf")
                await ResumeStorageMapper(session, 71).create_experience(EXAMPLES[0])
                raise RuntimeError("intentional")
        assert not store.path(71, asset.key).exists() and not list(store.root.glob("*.pending"))
        async with private_asset_transaction(session, store, 71) as batch:
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)
            pdf = batch.write(b"pdf fixture", "pdf")
            latex = batch.write(b"latex fixture", "tex")
            doc = await mapper.create_document({"name":"Files", "generation_job_id":job.id}, pdf_asset=pdf, latex_asset=latex)
            copy = await mapper.copy_document(doc.id, "Copy")
            await mapper.delete_document(doc.id, retention_days=0)
            copy_id, doc_id = copy.id, doc.id
        unknown = store.root / "unknown-file"
        unknown.write_bytes(b"preserved")
        report = await cleanup_documents(session, store, 71)
        assert report["dry_run"] and not report["removable_keys"] and len(report["protected_keys"]) == 2
        async with session.begin(): await mapper.delete_document(copy_id, retention_days=0)
        dry = await cleanup_documents(session, store, 71)
        assert set(dry["removable_keys"]) == {pdf.key, latex.key} and store.read(71, pdf)
        await cleanup_documents(session, store, 71, dry_run=False)
        assert not store.path(71, pdf.key).exists() and not store.path(71, latex.key).exists()
        assert unknown.read_bytes() == b"preserved"
        await cleanup_documents(session, store, 71, dry_run=False)
        async with session.begin():
            assert (await session.get(Document, doc_id)).files_purged_at is not None
            assert not await mapper.list_experiences()


async def test_active_job_input_protection_and_owner_file_validation(sessions, tmp_path):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        async with session.begin(): await approve_fixture(session)
        async with private_asset_transaction(session, store, 71) as batch:
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper)
            pdf = batch.write(b"fixture", "pdf")
            doc = await mapper.create_document({"name":"Protected", "generation_job_id":job.id}, pdf_asset=pdf, latex_asset=batch.write(b"latex", "tex"))
            await mapper.delete_document(doc.id, retention_days=0)
            active = await mapper.create_job(request(personal_info={"avatar_asset":pdf.model_dump()}))
            active_id = active.id
        report = await cleanup_documents(session, store, 71, dry_run=False)
        assert pdf.key in report["protected_keys"] and store.read(71, pdf)
        async with session.begin():
            with pytest.raises(RuntimeError): await mapper.create_job(request(personal_info={"avatar_asset":pdf.model_dump()}))
            with pytest.raises(AssetNotFound): await ResumeStorageMapper(session, 72).retry_job(active_id)
        async with private_asset_transaction(session, store, 72):
            with pytest.raises(PermissionError): await ResumeStorageMapper(session, 72).create_job(request(personal_info={"avatar_asset":pdf.model_dump()}))


async def test_uncertain_commit_preserves_files_and_manifest(sessions, tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSessionTransaction
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        original_commit = AsyncSessionTransaction.commit
        async def lost_ack(transaction):
            await original_commit(transaction)
            raise RuntimeError("commit acknowledgement lost")
        with monkeypatch.context() as patch:
            patch.setattr(AsyncSessionTransaction, "commit", lost_ack)
            with pytest.raises(RuntimeError, match="acknowledgement"):
                async with private_asset_transaction(session, store, 71) as batch:
                    asset = batch.write(b"keep after uncertain commit", "bin")
                    await ResumeStorageMapper(session, 71).create_experience(EXAMPLES[0])
        assert store.read(71, asset) == b"keep after uncertain commit"
        manifests = list(store.root.glob("*.pending"))
        assert len(manifests) == 1 and json.loads(manifests[0].read_text())["created"][0]["key"] == asset.key
        async with session.begin():
            assert len(await ResumeStorageMapper(session, 71).list_experiences()) == 1


async def test_document_snapshot_assets_require_boundary(sessions, tmp_path):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as session:
        async with session.begin(): await approve_fixture(session)
        async with private_asset_transaction(session, store, 71) as batch:
            avatar = batch.write(b"avatar input", "bin")
            mapper = ResumeStorageMapper(session, 71)
            job = await complete_fixture(mapper, personal_info={"avatar_asset": avatar.model_dump()})
            job_id = job.id
            outputs = document_outputs(batch)
        async with session.begin():
            with pytest.raises(RuntimeError, match="private_asset_transaction"):
                await mapper.create_document({"name":"Snapshot", "generation_job_id":job_id}, **outputs)
        async with private_asset_transaction(session, store, 71):
            doc = await mapper.create_document({"name":"Snapshot", "generation_job_id":job_id}, **outputs)
            assert doc.snapshot["personal_info_snapshot"]["avatar_asset"]["key"] == avatar.key


async def test_cleanup_refreshes_traces_from_other_session(sessions, tmp_path):
    store = PrivateAssets(tmp_path / "private")
    async with sessions() as first:
        async with first.begin(): await approve_fixture(first)
        async with private_asset_transaction(first, store, 71) as batch:
            mapper = ResumeStorageMapper(first, 71)
            output_job = await complete_fixture(mapper)
            pdf = batch.write(b"retained by trace", "pdf")
            doc = await mapper.create_document({"name":"Trace protection", "generation_job_id":output_job.id}, pdf_asset=pdf, latex_asset=batch.write(b"latex", "tex"))
            await mapper.delete_document(doc.id, retention_days=0)
            active = await mapper.create_job(request())
            active_id = active.id
        async with sessions() as second:
            async with private_asset_transaction(second, store, 71):
                await ResumeStorageMapper(second, 71).update_job(active_id, status="PENDING", stage="TRACE", progress=0, traces=[{"asset":pdf.model_dump()}])
        assert active.traces == []  # First identity map is deliberately stale.
        report = await cleanup_documents(first, store, 71, dry_run=False)
        assert pdf.key in report["protected_keys"] and store.read(71, pdf) == b"retained by trace"


def test_migration_roundtrip_preserves_legacy_schema_and_rows(mysql_schema):
    engine = create_engine(mysql_schema.set(drivername="mysql+pymysql"))
    try:
        old_columns = inspect(engine).get_columns("resumes")
        migrate(mysql_schema, "downgrade")
        assert set(inspect(engine).get_table_names()) == {"resumes", "resume_optimizations", "resume_phase1_alembic_version"}
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT content_text FROM resumes WHERE id=1")) == "original"
            assert connection.scalar(text("SELECT optimized_text FROM resume_optimizations WHERE session_id='old'")) == "# Legacy"
        migrate(mysql_schema)
        assert set(inspect(engine).get_table_names()) == {
            "resumes", "resume_optimizations", "resume_phase1_alembic_version",
            "experience_items", "resume_templates", "resume_generation_jobs", "resume_documents",
            "experience_import_batches", "experience_import_drafts",
        }
        assert [(c["name"], str(c["type"])) for c in old_columns] == [(c["name"], str(c["type"])) for c in inspect(engine).get_columns("resumes")]
    finally:
        engine.dispose()
