"""Durable database queue. A MySQL connection lock fences each execution/recovery."""
from __future__ import annotations

import argparse
import asyncio
import logging
import hashlib
import os
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.dialects.mysql import insert
from app.models.resume_execution_models import ResumeExecutionSlot as Slot
from app.models.resume_storage_models import utcnow
from app.services.resume_execution import cleanup_slot, execution, host_key
from app.services.resume_process_identity import process_identity
from app.infrastructure.resume_runtime import session_factory, asset_store
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper
from app.models.resume_storage_models import ResumeGenerationJobModel as Job
from app.services.resume_generation_service import run_generation_job

logger = logging.getLogger(__name__)


async def run_once(factory=None, *, store=None, compiler=None):
    factory = factory or session_factory()
    capacity = int(os.environ.get("LATEX_COMPILE_CONCURRENCY", "2"))
    if not 1 <= capacity <= 16:
        raise ValueError("LATEX_COMPILE_CONCURRENCY must be 1..16")
    identity = process_identity(os.getpid())
    if not identity:
        raise RuntimeError("worker process identity unavailable")
    scope = hashlib.sha256(factory.kw["bind"].url.database.casefold().encode()).hexdigest()[:16]
    async with factory() as session:
        async with session.begin():
            interrupted = (await session.execute(select(Job.id, Job.user_id).where(
                Job.status == "PROCESSING").order_by(Job.updated_at, Job.id).limit(100))).all()
    # Recovery is independent of queue depth and does not require a free compile slot.
    for job_id, owner in interrupted:
        async with factory.kw["bind"].connect() as lease:
            key = "resume-job:" + job_id
            if not (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": key})).scalar():
                continue
            try:
                async with factory() as session, session.begin():
                    mapper = ResumeStorageMapper(session, owner)
                    row = await mapper.owned(Job, job_id, lock=True)
                    if row.status != "PROCESSING":
                        continue
                    await mapper.update_job(job_id, status="FAILED", stage="INTERRUPTED", progress=0,
                        error={"code": "WORKER_INTERRUPTED", "message": "执行服务中断，请重试冻结的输入", "retryable": True})
                    row.run_token = None
                return True
            finally:
                await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": key})
    async with factory() as session, session.begin():
        candidates = (await session.execute(select(Job.id, Job.user_id).where(Job.status == "PENDING")
            .order_by(Job.created_at, Job.id).limit(100))).all()
    # Reclaim registered orphan resources even when there are no pending jobs.
    async with factory() as session, session.begin():
        reclaim = (await session.execute(select(Slot.slot, Slot.token).where(Slot.state != "FREE").order_by(Slot.slot).limit(16))).all()
    for index, old_token in reclaim:
        if old_token:
            async with factory.kw["bind"].connect() as lease:
                key = f"resume-worker-slot:{scope}:{index}"
                if (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": key})).scalar():
                    try:
                        await cleanup_slot(factory, index, old_token)
                    finally:
                        await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": key})
    for job_id, owner in candidates:
        # Keep a dedicated connection for the entire execution. A crash releases its lock;
        # the next worker explicitly fails orphaned PROCESSING tasks, preserving snapshots.
        async with factory.kw["bind"].connect() as lease:
            lock = "resume-job:" + job_id
            if not (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": lock})).scalar():
                continue
            slot, token = None, None
            try:
                for index in range(capacity):
                    candidate = f"resume-worker-slot:{scope}:{index}"
                    if (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": candidate})).scalar():
                        async with factory() as session, session.begin():
                            await session.execute(insert(Slot).values(slot=index, state="FREE", updated_at=utcnow()).prefix_with("IGNORE"))
                            state = await session.get(Slot, index, with_for_update=True)
                            available = state.state == "FREE"
                        if available:
                            slot = candidate
                            slot_index = index
                            break
                        await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": candidate})
                if slot is None:
                    continue
                token = str(uuid4())
                async with factory() as session, session.begin():
                    state = await session.get(Slot, slot_index, with_for_update=True)
                    state.token, state.job_id, state.host_key = token, job_id, host_key()
                    state.worker_pid, state.worker_identity = os.getpid(), identity
                    state.state, state.updated_at = "ACTIVE", utcnow()
                async with factory() as session:
                    async with session.begin():
                        mapper = ResumeStorageMapper(session, owner)
                        row = await mapper.owned(Job, job_id, lock=True)
                        if row.status != "PENDING":
                            continue
                        row.run_token = token
                        await mapper.update_job(job_id, status="PROCESSING", stage="CLAIMED", progress=1)
                context_token = execution.set({"factory": factory, "slot": slot_index, "token": token, "job_id": job_id})
                async def watch_lease():
                    while True:
                        await asyncio.sleep(1)
                        valid = (await asyncio.wait_for(lease.execute(text("SELECT IS_USED_LOCK(:job) = CONNECTION_ID() AND IS_USED_LOCK(:slot) = CONNECTION_ID()"),
                            {"job": lock, "slot": slot}), 5)).scalar()
                        if not valid:
                            raise RuntimeError("WORKER_LEASE_LOST")
                work = asyncio.create_task(run_generation_job(job_id, owner, token=token, factory=factory, store=store, compiler=compiler))
                watcher = asyncio.create_task(watch_lease())
                try:
                    done, _ = await asyncio.wait((work, watcher), return_when=asyncio.FIRST_COMPLETED)
                    if watcher in done:
                        work.cancel()
                        await asyncio.gather(work, return_exceptions=True)
                        raise RuntimeError("WORKER_LEASE_LOST")
                    await work
                finally:
                    work.cancel(); watcher.cancel()
                    await asyncio.gather(work, watcher, return_exceptions=True)
                    execution.reset(context_token)
                    await asyncio.shield(cleanup_slot(factory, slot_index, token, finished=True))
                async with factory() as session, session.begin():
                    result = await session.get(Job, job_id)
                    duration = (result.finished_at - result.started_at).total_seconds() if result.finished_at and result.started_at else None
                    logger.info("resume job=%s status=%s duration_seconds=%s error_code=%s ai_status=%s retries=%s",
                        job_id, result.status, duration, (result.error or {}).get("code"),
                        (result.result_metadata or {}).get("ai_status"), result.retry_count)
                return True
            finally:
                if slot:
                    if token:
                        try:
                            if not await cleanup_slot(factory, slot_index, token, finished=True):
                                async with factory() as session, session.begin():
                                    state = await session.get(Slot, slot_index)
                                    if state and state.token == token:
                                        logger.error("resume cleanup required slot=%s job=%s", slot_index, job_id)
                        except Exception:
                            logger.error("resume cleanup unconfirmed slot=%s job=%s", slot_index, job_id)
                    try:
                        await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": slot})
                    except Exception:
                        pass  # disconnected connections have already lost their locks
                try:
                    await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": lock})
                except Exception:
                    pass
    return False


async def main(once=False):
    factory, store = session_factory(), asset_store()
    while True:
        try:
            processed = await run_once(factory, store=store)
        except Exception as error:
            logger.error("resume worker cycle failed: %s", type(error).__name__)
            if once:
                raise
            processed = False
        if once:
            return
        if not processed:
            await asyncio.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    asyncio.run(main(parser.parse_args().once))
