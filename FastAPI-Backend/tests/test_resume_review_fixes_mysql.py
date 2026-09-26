"""Real MySQL review, backlog and lost-connection regression tests. Compiler/AI are substitutes."""
import asyncio
import os
from copy import deepcopy
from unittest.mock import AsyncMock
import httpx
import pytest
from sqlalchemy import select, text
from app.models.resume_storage_models import ResumeGenerationJobModel as Job, ResumeDocumentModel as Document, utcnow
from app.models.resume_execution_models import ResumeExecutionSlot as Slot
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper
from app.api.resume_app import create_resume_app
from app.api.experience_dependencies import experience_session, trusted_owner
from app.services.resume_worker import run_once
from app.services import resume_generation_service as generation
from app.services import resume_execution
from test_resume_completion_mysql import seed, fixture_pdf, compiler


@pytest.mark.asyncio
async def test_review_confirm_conflict_idempotence_retry_and_snapshot(sessions, private_store, monkeypatch):
    job_id, _ = await seed(sessions, ai_recommendation_mode="JD_AUTO_SELECT_AND_TAILOR")
    async with sessions() as session, session.begin():
        job = await session.get(Job, job_id)
        facts = deepcopy(job.experience_snapshot)
    id_ = facts[0]["id"]
    original = facts[0]["attributes"]["bullets"][0]
    ai = generation.StructuredAIPlan(selected_item_ids=[id_], tailored_bullets=[
        {"source_item_id": id_, "original_bullet": original, "tailored_bullet": "优化表述：" + original}],
        trim_suggestions=["减少无关内容"], keyword_matches={id_: []})
    mock = AsyncMock(return_value=ai)
    monkeypatch.setattr(generation, "request_structured_ai_plan", mock)
    never_compile = AsyncMock(side_effect=AssertionError("must wait for review"))
    assert await run_once(sessions, store=private_store, compiler=never_compile)
    never_compile.assert_not_awaited()
    async with sessions() as session, session.begin():
        job = await session.get(Job, job_id)
        assert job.status == "WAITING_REVIEW" and job.run_token is None
        version = job.review_plan["version"]
        assert (await session.execute(select(Slot.state))).scalars().all() == ["FREE"]
    app = create_resume_app()
    async def db():
        async with sessions() as session: yield session
    app.dependency_overrides[experience_session] = db
    app.dependency_overrides[trusted_owner] = lambda: 71
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        endpoint = f"/api/resume-generation/jobs/{job_id}/review"
        assert (await client.post(endpoint, json={"version": "0" * 64, "accepted_indices": [0]})).status_code == 409
        assert (await client.post(endpoint, json={"version": version, "accepted_indices": [0, 0]})).status_code == 422
        decision = {"version": version, "accepted_indices": [0]}
        assert (await client.post(endpoint, json=decision)).status_code == 202
        assert (await client.post(endpoint, json=decision)).status_code == 202
        assert (await client.post(endpoint, json={"version": version, "accepted_indices": []})).status_code == 409
        app.dependency_overrides[trusted_owner] = lambda: 72
        assert (await client.post(endpoint, json=decision)).status_code == 404
    async def fail(*args): raise generation.LatexCompileError("COMPILE_TIMEOUT")
    await run_once(sessions, store=private_store, compiler=fail)
    async with sessions() as session, session.begin():
        await ResumeStorageMapper(session, 71).retry_job(job_id)
    async def reviewed(source, resources):
        assert "优化表述：" in source
        return fixture_pdf()
    await run_once(sessions, store=private_store, compiler=reviewed)
    mock.assert_awaited_once()
    async with sessions() as session, session.begin():
        job = await session.get(Job, job_id)
        doc = (await session.execute(select(Document))).scalar_one()
        assert job.status == "COMPILED" and job.experience_snapshot == facts
        assert doc.snapshot["review_decision"] == decision
        assert job.traces[0]["original_bullet"] == original and job.traces[0]["tailored_bullet"] != original


@pytest.mark.asyncio
async def test_processing_recovery_is_not_starved_by_pending_backlog(sessions, private_store):
    job_id, _ = await seed(sessions)
    async with sessions() as session, session.begin():
        mapper = ResumeStorageMapper(session, 71)
        job = await mapper.update_job(job_id, status="PROCESSING", stage="CLAIMED", progress=1)
        job.run_token = "orphan"
        for _ in range(105):
            await mapper.create_job({"template_id": job.template_id, "template_version": job.template_version,
                "jd_text": "Python backend developer", "show_avatar": False, "ai_recommendation_mode": "MANUAL_ONLY"})
    await run_once(sessions, store=private_store, compiler=compiler)
    async with sessions() as session, session.begin():
        assert (await session.get(Job, job_id)).error["code"] == "WORKER_INTERRUPTED"
        assert len((await session.execute(select(Job.id).where(Job.status == "PENDING"))).all()) == 105


@pytest.mark.asyncio
async def test_lost_mysql_lease_cancels_active_execution(sessions, private_store):
    job_id, _ = await seed(sessions)
    entered, cancelled = asyncio.Event(), asyncio.Event()
    async def blocked(*args):
        entered.set()
        try: await asyncio.sleep(15)
        except asyncio.CancelledError:
            cancelled.set(); raise
    work = asyncio.create_task(run_once(sessions, store=private_store, compiler=blocked))
    try:
        await asyncio.wait_for(entered.wait(), 10)
        async with sessions() as session, session.begin():
            connection_id = await session.scalar(text("SELECT IS_USED_LOCK(:key)"), {"key": "resume-job:" + job_id})
            assert type(connection_id) is int and connection_id > 0
            # Exact connection owned by this test's worker, not a user/system process.
            await session.execute(text(f"KILL CONNECTION {connection_id}"))
        with pytest.raises(RuntimeError, match="WORKER_LEASE_LOST"):
            await asyncio.wait_for(work, 10)
        assert cancelled.is_set()
        assert await run_once(sessions, store=private_store, compiler=compiler)
        async with sessions() as session, session.begin():
            assert (await session.get(Job, job_id)).status == "FAILED"
            assert not (await session.execute(select(Document))).scalars().all()
    finally:
        work.cancel(); await asyncio.gather(work, return_exceptions=True)


@pytest.mark.asyncio
async def test_unconfirmed_resources_keep_capacity_occupied(sessions, private_store, monkeypatch):
    monkeypatch.setenv("LATEX_COMPILE_CONCURRENCY", "1")
    job_id, _ = await seed(sessions)
    async with sessions() as session, session.begin():
        session.add(Slot(slot=0, token="orphan", job_id=job_id, host_key="different-host", state="ACTIVE", updated_at=utcnow()))
    assert not await run_once(sessions, store=private_store, compiler=compiler)
    async with sessions() as session, session.begin():
        assert (await session.get(Job, job_id)).status == "PENDING"
        assert (await session.get(Slot, 0)).state == "CLEANUP_REQUIRED"


@pytest.mark.asyncio
async def test_live_old_process_blocks_slot_reuse_without_finish_ack(sessions, private_store, monkeypatch):
    from app.services.resume_process_identity import process_identity
    monkeypatch.setenv("LATEX_COMPILE_CONCURRENCY", "1")
    job_id, _ = await seed(sessions)
    async with sessions() as session, session.begin():
        session.add(Slot(slot=0, token="old-execution", job_id=job_id, host_key=resume_execution.host_key(),
            worker_pid=os.getpid(), worker_identity=process_identity(os.getpid()), state="ACTIVE", updated_at=utcnow()))
    assert not await run_once(sessions, store=private_store, compiler=compiler)
    async with sessions() as session, session.begin():
        assert (await session.get(Job, job_id)).status == "PENDING"
        assert (await session.get(Slot, 0)).state == "CLEANUP_REQUIRED"


@pytest.mark.skipif(os.environ.get("RUN_RESUME_DOCKER_INTEGRATION") != "1", reason="real Linux Docker/trusted image explicitly required")
@pytest.mark.asyncio
async def test_real_container_worker_crash_recovers_input_and_capacity(sessions, private_store, monkeypatch, tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    from app.services.isolated_latex import _capture
    work_root = tmp_path / "compile"
    work_root.mkdir()
    monkeypatch.setenv("RESUME_COMPILE_WORK_ROOT", str(work_root))
    monkeypatch.setenv("LATEX_COMPILE_CONCURRENCY", "1")
    job_id, _ = await seed(sessions)
    backend = Path(__file__).resolve().parents[1]
    keys = ("PATH", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP", "USERNAME", "USERDOMAIN", "RESUME_LATEX_IMAGE", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH")
    environment = {key: os.environ[key] for key in keys if key in os.environ}
    environment.update(DATABASE_URL=sessions.kw["bind"].url.render_as_string(hide_password=False),
        RESUME_PRIVATE_ASSET_ROOT=str(private_store.root), RESUME_COMPILE_WORK_ROOT=str(work_root),
        PYTHONPATH=str(backend), LATEX_COMPILE_CONCURRENCY="1")
    child = subprocess.Popen([sys.executable, str(backend / "tests/helpers/resume_container_worker.py")],
        cwd=backend, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    record = None
    try:
        for _ in range(100):
            async with sessions() as session, session.begin():
                slot = await session.get(Slot, 0)
                if slot and slot.task_id:
                    record = {key: getattr(slot, key) for key in ("token", "task_id", "container_name", "work_dir", "job_id")}
            if record:
                code, containers = await _capture(["docker", "ps", "-q", "--filter", f"name=^/{record['container_name']}$"], timeout=2, limit=8192)
                if code == 0 and containers.strip(): break
            assert child.poll() is None, "real test worker exited before its container was running"
            await asyncio.sleep(.1)
        else:
            pytest.fail("real task container did not start")
    finally:
        if child.poll() is None: child.terminate()  # this exact test-owned child
        await asyncio.to_thread(child.wait, timeout=5)
        # Recovery first marks the job failed, then verifies container absence and frees capacity.
        for _ in range(3): await run_once(sessions, store=private_store)
    assert record is not None
    assert not Path(record["work_dir"]).exists()
    async with sessions() as session, session.begin():
        assert (await session.get(Job, job_id)).status == "FAILED"
        assert (await session.get(Slot, 0)).state == "FREE"
