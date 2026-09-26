"""Real MySQL queue/document behavior; PDF compiler is explicitly a test substitute."""
import asyncio
from copy import deepcopy
from io import BytesIO

import httpx
import pytest
from pypdf import PdfWriter
from sqlalchemy import select
from app.api.resume_app import create_resume_app
from app.api.experience_dependencies import experience_session, private_store as store_dependency, trusted_owner
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper
from app.infrastructure.resume_template_store import initialize_templates
from app.models.resume_storage_models import ResumeGenerationJobModel as Job, ResumeDocumentModel as Document
from app.services.resume_worker import run_once
from test_storage_boundaries import EXAMPLES
from test_phase2_boundaries import auth, text_pdf, jwt_config


def fixture_pdf(pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


async def seed(factory, **options):
    async with factory() as session:
        async with session.begin():
            await initialize_templates(session)
            mapper = ResumeStorageMapper(session, 71)
            experience = await mapper.create_experience(EXAMPLES[2])
            row = await mapper.create_job({"template_id": "tpl-billryan-classic", "template_version": "1.2.0",
                "jd_text": "Python backend developer", "show_avatar": False, "selected_item_ids": [experience.id],
                "ai_recommendation_mode": "MANUAL_ONLY", "personal_info": {"name": "Candidate"}, **options})
            return row.id, experience.id


async def compiler(source, resources):
    assert "Candidate" in source
    return fixture_pdf()


@pytest.mark.asyncio
async def test_worker_persists_actual_result_and_only_one_document(sessions, private_store):
    job_id, _ = await seed(sessions)
    assert await run_once(sessions, store=private_store, compiler=compiler)
    assert not await run_once(sessions, store=private_store, compiler=compiler)
    async with sessions() as session, session.begin():
        row = await session.get(Job, job_id)
        docs = (await session.execute(select(Document))).scalars().all()
        assert row.status == "COMPILED" and row.result_metadata["actual_pages"] == 1
        assert row.result_metadata["ai_status"] == "NOT_REQUESTED" and len(docs) == 1
        assert docs[0].snapshot["result_metadata"] == row.result_metadata


@pytest.mark.asyncio
async def test_two_workers_cannot_execute_same_job(sessions, private_store):
    await seed(sessions)
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def blocked(source, resources):
        calls.append(source)
        entered.set()
        await release.wait()
        return fixture_pdf()
    running = asyncio.create_task(run_once(sessions, store=private_store, compiler=blocked))
    try:
        await asyncio.wait_for(entered.wait(), 10)
        assert not await run_once(sessions, store=private_store, compiler=blocked)
    finally:
        release.set()
        await running
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_global_worker_capacity_across_distinct_jobs(sessions, private_store, monkeypatch):
    monkeypatch.setenv("LATEX_COMPILE_CONCURRENCY", "1")
    first, _ = await seed(sessions)
    second, _ = await seed(sessions)
    entered, release = asyncio.Event(), asyncio.Event()
    async def blocked(*args):
        entered.set()
        await release.wait()
        return fixture_pdf()
    running = asyncio.create_task(run_once(sessions, store=private_store, compiler=blocked))
    try:
        await asyncio.wait_for(entered.wait(), 10)
        assert not await run_once(sessions, store=private_store, compiler=blocked)
        async with sessions() as session, session.begin():
            row = await session.get(Job, second)
            assert row.status == "PENDING"
    finally:
        release.set()
        await running


@pytest.mark.asyncio
async def test_orphan_recovery_and_retry_keep_frozen_inputs(sessions, private_store):
    id, _ = await seed(sessions)
    async with sessions() as session, session.begin():
        mapper = ResumeStorageMapper(session, 71)
        row = await mapper.update_job(id, status="PROCESSING", stage="CLAIMED", progress=1)
        row.run_token = "orphan"
        frozen = deepcopy(row.experience_snapshot)
    assert await run_once(sessions, store=private_store, compiler=compiler)
    async with sessions() as session, session.begin():
        mapper = ResumeStorageMapper(session, 71)
        row = await mapper.get_job(id)
        assert row.status == "FAILED" and row.error["code"] == "WORKER_INTERRUPTED"
        row = await mapper.retry_job(id)
        assert row.experience_snapshot == frozen and row.retry_count == 1 and row.run_token is None
    assert await run_once(sessions, store=private_store, compiler=compiler)


@pytest.mark.asyncio
async def test_page_limit_failure_does_not_save_document(sessions, private_store):
    id, _ = await seed(sessions)
    async def too_long(*args):
        return fixture_pdf(2)
    await run_once(sessions, store=private_store, compiler=too_long)
    async with sessions() as session, session.begin():
        row = await session.get(Job, id)
        assert row.status == "FAILED" and row.error["code"] == "PAGE_LIMIT_EXCEEDED"
        assert not (await session.execute(select(Document))).scalars().all()


@pytest.mark.asyncio
async def test_document_identity_copy_delete_download_and_frozen_reedit(sessions, private_store):
    id, experience_id = await seed(sessions)
    await run_once(sessions, store=private_store, compiler=compiler)
    app = create_resume_app()
    async def session_dep():
        async with sessions() as session:
            yield session
    app.dependency_overrides[experience_session] = session_dep
    app.dependency_overrides[trusted_owner] = lambda: 71
    app.dependency_overrides[store_dependency] = lambda: private_store
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        original = (await client.get("/api/resume-documents")).json()[0]
        metrics = (await client.get("/api/resume-generation/metrics")).json()
        assert metrics["status_counts"] == {"COMPILED": 1}
        assert metrics["ai_states"] == {"NOT_REQUESTED": 1}
        prefix = "/api/resume-documents/" + original["id"]
        copied = await client.post(prefix + "/copy", json={"name": "Copy"})
        assert copied.status_code == 201, copied.text
        copy_prefix = "/api/resume-documents/" + copied.json()["id"]
        assert copied.json()["generation_job_id"] == id
        assert (await client.patch(copy_prefix, json={"name": "  Renamed  "})).json()["name"] == "Renamed"
        before = (await client.get(prefix)).json()["snapshot"]
        regenerated = await client.post(prefix + "/regenerate", json={"jd_text": "New Python target job"})
        assert regenerated.status_code == 202, regenerated.text
        assert regenerated.json()["job_id"] != id
        assert (await client.get(prefix)).json()["snapshot"] == before
        assert (await client.delete(prefix)).status_code == 204
        assert (await client.get(prefix + "/pdf")).status_code == 404
        assert (await client.get(copy_prefix + "/pdf")).content == fixture_pdf()
        app.dependency_overrides[trusted_owner] = lambda: 72
        assert (await client.get(copy_prefix)).status_code == 404
        assert (await client.get(copy_prefix + "/latex")).status_code == 404
        assert (await client.post(copy_prefix + "/regenerate", json={})).status_code == 404


@pytest.mark.asyncio
async def test_markdown_requires_confirmation_and_keeps_original(sessions, private_store):
    from app.services.experience_import_service import ExperienceImportService
    from app.models.experience_api_contracts import ConfirmImport
    from app.models.session_models import ResumeOptimizationModel
    from app.models.resume_storage_models import ExperienceItemModel
    class MarkdownAI:
        async def extract(self, pages):
            assert pages[0]["text"] == "# Legacy"
            return {"items": [{"content": {"type": "SKILL", "title": "核实技能", "category": "Backend", "skills": ["待核实"]},
                "page": 1, "snippet": "Legacy"}]}
    async with sessions() as session:
        service = ExperienceImportService(session, 71, private_store, MarkdownAI())
        batch = await service.from_markdown("old")
        assert batch["source_format"] == "markdown" and batch["status"] == "READY"
        async with session.begin():
            assert not (await session.execute(select(ExperienceItemModel))).scalars().all()
        draft = batch["items"][0]
        assert "page" not in draft["source_locator"]
        receipt = await service.confirm(batch["id"], ConfirmImport(items=[{"id": draft["id"], "expected_revision": draft["revision"]}]))
        assert await service.confirm(batch["id"], ConfirmImport(items=[{"id": draft["id"], "expected_revision": draft["revision"]}])) == receipt
        async with session.begin():
            source = await session.get(ResumeOptimizationModel, "old")
            rows = (await session.execute(select(ExperienceItemModel))).scalars().all()
            assert source.optimized_text == "# Legacy" and len(rows) == 1
            assert rows[0].source_type == "MARKDOWN_IMPORT"
            assert rows[0].source_locator["legacy_optimization_id"] == "old"
            assert rows[0].source_locator["user_confirmed"] is True


@pytest.mark.asyncio
async def test_import_failure_observability_survives_successful_retry(sessions, private_store):
    from app.services.experience_import_service import ExperienceImportService
    from app.services.experience_errors import ExperienceError
    class FlakyAI:
        failed = False
        async def extract(self, pages):
            if not self.failed:
                self.failed = True
                raise ExperienceError("AI_UNAVAILABLE", "Test provider failure", 502)
            return {"items": [{"content": {"type": "SKILL", "title": "Python", "category": "Backend", "skills": ["Python"]},
                "page": 1, "snippet": "Python"}]}
    async with sessions() as session:
        service = ExperienceImportService(session, 71, private_store, FlakyAI())
        with pytest.raises(ExperienceError) as failure:
            await service.upload(text_pdf())
        id = failure.value.details["import_id"]
        failed = await service.get(id)
        assert failed["ai_attempt_count"] == failed["ai_failure_count"] == 1
        restored = await service.retry(id)
        assert restored["status"] == "READY" and restored["error"] is None
        assert restored["ai_attempt_count"] == 2 and restored["ai_failure_count"] == 1 and restored["retry_count"] == 1


@pytest.mark.asyncio
async def test_actual_worker_process_restart_recovers_interrupted_job(sessions, private_store, tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    id, _ = await seed(sessions)
    marker = tmp_path / "worker-claimed.txt"
    backend = Path(__file__).resolve().parents[1]
    environment = {key: os.environ[key] for key in ("PATH", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP", "USERNAME", "USERDOMAIN") if key in os.environ}
    environment.update(DATABASE_URL=sessions.kw["bind"].url.render_as_string(hide_password=False),
        RESUME_PRIVATE_ASSET_ROOT=str(private_store.root), RESUME_WORKER_TEST_MARKER=str(marker),
        PYTHONPATH=str(backend), LATEX_COMPILE_CONCURRENCY="1")
    child = subprocess.Popen([sys.executable, str(backend / "tests/helpers/resume_paused_worker.py")],
        cwd=backend, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(100):
            if marker.exists():
                break
            if child.poll() is not None:
                import re
                error = child.stderr.read(32768).decode("utf-8", errors="replace")
                password = sessions.kw["bind"].url.password
                if password:
                    error = error.replace(password, "<redacted>")
                error = re.sub(r"mysql\+\w+://\S+", "mysql://<redacted>", error)
                reason = next((line for line in reversed(error.splitlines()) if re.match(r"^[\w.]+(?:Error|Exception):", line)), "child startup failed")
                pytest.fail("test worker exited before compilation checkpoint: " + reason[:300])
            await asyncio.sleep(0.1)
        assert marker.exists(), "test worker did not claim the persisted job"
        async with sessions() as session, session.begin():
            row = await session.get(Job, id)
            assert row.status == "PROCESSING" and row.run_token
    finally:
        if child.poll() is None:
            child.terminate()  # exact Popen handle of this test's own process
        await asyncio.to_thread(child.wait, timeout=5)
    for _ in range(30):
        if await run_once(sessions, store=private_store, compiler=compiler):
            break
        await asyncio.sleep(0.1)
    async with sessions() as session, session.begin():
        row = await session.get(Job, id)
        assert row.status == "FAILED" and row.error["code"] == "WORKER_INTERRUPTED"
        await ResumeStorageMapper(session, 71).retry_job(id)
    assert await run_once(sessions, store=private_store, compiler=compiler)
    async with sessions() as session, session.begin():
        assert (await session.get(Job, id)).status == "COMPILED"


@pytest.mark.asyncio
async def test_owned_pdf_sources_and_batches_paginate(sessions, private_store, jwt_config):
    from datetime import timedelta
    from uuid import uuid4
    from app.models.experience_import_models import ExperienceImportBatch
    from app.models.session_models import ResumeModel
    from app.models.resume_storage_models import utcnow
    app = create_resume_app()
    async def session_dep():
        async with sessions() as session:
            yield session
    app.dependency_overrides[experience_session] = session_dep
    app.dependency_overrides[store_dependency] = lambda: private_store
    now = utcnow()
    async with sessions() as session, session.begin():
        for index in range(2, 103):
            session.add(ResumeModel(id=index, user_id=71, filename=f"fixture-{index}.pdf", local_path="not-a-public-path", uploaded_at=now))
        session.add(ResumeModel(id=103, user_id=72, filename="other.pdf", local_path="private", uploaded_at=now))
        for index in range(52):
            session.add(ExperienceImportBatch(id=str(uuid4()), user_id=71, source_asset=None, pages=[], status="FAILED",
                created_at=now, updated_at=now, expires_at=now + timedelta(days=1)))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth()) as client:
        first = (await client.get("/api/experience-imports/sources?page=1")).json()
        second = (await client.get("/api/experience-imports/sources?page=2")).json()
        assert len(first) == 100 and [row["id"] for row in second] == [2, 1]
        assert all(set(row) == {"id", "filename"} for row in first + second)
        assert len((await client.get("/api/experience-imports?page=1")).json()) == 50
        assert len((await client.get("/api/experience-imports?page=2")).json()) == 2
        assert (await client.get("/api/experience-imports/sources?page=0")).status_code == 422
        other = (await client.get("/api/experience-imports/sources", headers=auth(72))).json()
        assert [row["id"] for row in other] == [103]
        assert (await client.get("/api/experience-imports", headers=auth(72))).json() == []


@pytest.mark.asyncio
async def test_api_import_confirm_generate_save_reedit_flow(sessions, private_store, jwt_config):
    """Real JWT/ASGI/MySQL/PDF extraction/rendering; AI and compiler are substitutes."""
    from app.api.experience_dependencies import draft_extractor
    from app.models.resume_storage_models import ExperienceItemModel
    class Extractor:
        async def extract(self, pages):
            return {"items": [{"content": {"type": "PROJECT", "title": "Python project", "role": "Developer", "bullets": ["Python backend project"]},
                "page": 1, "snippet": "Python backend project"}]}
    app = create_resume_app()
    async def session_dep():
        async with sessions() as session:
            yield session
    app.dependency_overrides[experience_session] = session_dep
    app.dependency_overrides[store_dependency] = lambda: private_store
    app.dependency_overrides[draft_extractor] = lambda: Extractor()
    async with sessions() as session, session.begin():
        await initialize_templates(session)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=auth()) as client:
        upload = await client.post("/api/experience-imports/upload", files={"file": ("source.pdf", text_pdf(), "application/pdf")})
        assert upload.status_code == 201, upload.text
        batch = upload.json()
        async with sessions() as session, session.begin():
            assert not (await session.execute(select(ExperienceItemModel))).scalars().all()
        draft = batch["items"][0]
        content = {**draft["content"], "title": "Confirmed Python project"}
        corrected = await client.put(f"/api/experience-imports/{batch['id']}/items/{draft['id']}", json={"content": content, "expected_revision": draft["revision"]})
        assert corrected.status_code == 200
        receipt = await client.post(f"/api/experience-imports/{batch['id']}/confirm", json={"items": [{"id": draft["id"], "expected_revision": corrected.json()["revision"]}]})
        assert receipt.status_code == 200, receipt.text
        experience_id = receipt.json()["items"][0]["experience_id"]
        public_experience = (await client.get(f"/api/experiences/{experience_id}")).json()
        assert "key" not in public_experience["source_locator"]["asset"]
        created = await client.post("/api/resume-generation/jobs", json={"template_id": "tpl-billryan-classic", "template_version": "1.2.0",
            "jd_text": "Python backend developer", "show_avatar": False, "selected_item_ids": [experience_id],
            "ai_recommendation_mode": "MANUAL_ONLY", "personal_info": {"name": "Candidate", "education": [{"school": "University", "date_range": "2020–2024"}]}})
        assert created.status_code == 202, created.text
        await run_once(sessions, store=private_store, compiler=compiler)
        finished = await client.get(f"/api/resume-generation/jobs/{created.json()['job_id']}")
        assert finished.json()["status"] == "COMPILED", finished.text
        documents = (await client.get("/api/resume-documents")).json()
        path = "/api/resume-documents/" + documents[0]["id"]
        latex = await client.get(path + "/latex")
        assert "Confirmed Python project" in latex.text and "University" in latex.text
        assert (await client.get(path + "/pdf")).content.startswith(b"%PDF-")
        regenerated = await client.post(path + "/regenerate", json={"jd_text": "Second Python target", "personal_info": {"name": "Candidate"}})
        assert regenerated.status_code == 202, regenerated.text
        await run_once(sessions, store=private_store, compiler=compiler)
        assert len((await client.get("/api/resume-documents")).json()) == 2
        assert (await client.get(path)).json()["snapshot"]["personal_info_snapshot"]["education"][0]["school"] == "University"
