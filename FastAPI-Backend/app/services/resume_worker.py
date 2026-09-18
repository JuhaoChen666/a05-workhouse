"""Durable database queue. A MySQL connection lock fences each execution/recovery."""
from __future__ import annotations

import argparse
import asyncio
import logging
import hashlib
import os
from uuid import uuid4

from sqlalchemy import select, text
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
    scope = hashlib.sha256(factory.kw["bind"].url.database.casefold().encode()).hexdigest()[:16]
    async with factory() as session:
        async with session.begin():
            candidates = (await session.execute(select(Job.id, Job.user_id).where(
                Job.status.in_(("PENDING", "PROCESSING"))).order_by(Job.status, Job.created_at, Job.id).limit(100))).all()
    for job_id, owner in candidates:
        # Keep a dedicated connection for the entire execution. A crash releases its lock;
        # the next worker explicitly fails orphaned PROCESSING tasks, preserving snapshots.
        async with factory.kw["bind"].connect() as lease:
            lock = "resume-job:" + job_id
            if not (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": lock})).scalar():
                continue
            slot = None
            try:
                for index in range(capacity):
                    candidate = f"resume-worker-slot:{scope}:{index}"
                    if (await lease.execute(text("SELECT GET_LOCK(:key, 0)"), {"key": candidate})).scalar():
                        slot = candidate
                        break
                if slot is None:
                    continue
                token = str(uuid4())
                async with factory() as session:
                    async with session.begin():
                        mapper = ResumeStorageMapper(session, owner)
                        row = await mapper.owned(Job, job_id, lock=True)
                        if row.status == "PROCESSING":
                            await mapper.update_job(job_id, status="FAILED", stage="INTERRUPTED", progress=0,
                                error={"code": "WORKER_INTERRUPTED", "message": "执行服务中断，请重试冻结的输入", "retryable": True})
                            row.run_token = None
                            return True
                        if row.status != "PENDING":
                            continue
                        row.run_token = token
                        await mapper.update_job(job_id, status="PROCESSING", stage="CLAIMED", progress=1)
                await run_generation_job(job_id, owner, token=token, factory=factory, store=store, compiler=compiler)
                async with factory() as session, session.begin():
                    result = await session.get(Job, job_id)
                    duration = (result.finished_at - result.started_at).total_seconds() if result.finished_at and result.started_at else None
                    logger.info("resume job=%s status=%s duration_seconds=%s error_code=%s ai_status=%s retries=%s",
                        job_id, result.status, duration, (result.error or {}).get("code"),
                        (result.result_metadata or {}).get("ai_status"), result.retry_count)
                return True
            finally:
                if slot:
                    await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": slot})
                await lease.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": lock})
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
