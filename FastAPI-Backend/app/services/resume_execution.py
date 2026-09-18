"""Persistent slot identity and task-local compile registration."""
import hashlib
import os
import socket
from contextvars import ContextVar
from app.models.resume_execution_models import ResumeExecutionSlot as Slot
from app.models.resume_storage_models import utcnow
from app.services.resume_process_identity import process_identity

execution = ContextVar("resume_execution", default=None)


def host_key():
    values = [socket.gethostname(), os.environ.get("RESUME_COMPILE_WORK_ROOT", ""),
        os.environ.get("DOCKER_HOST", ""), os.environ.get("DOCKER_CONTEXT", "")]
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


def container_name(context, task_id):
    if context is None:
        return f"resume-compile-{task_id}"
    scope = hashlib.sha256(context["factory"].kw["bind"].url.database.casefold().encode()).hexdigest()[:16]
    return f"resume-compile-{scope}-slot{context['slot']}"


async def register_compile(task_id, directory, name):
    context = execution.get()
    if context is None:
        return
    async with context["factory"]() as session, session.begin():
        slot = await session.get(Slot, context["slot"], with_for_update=True)
        if slot.token != context["token"] or slot.state != "ACTIVE":
            raise RuntimeError("execution ownership lost")
        slot.host_key, slot.task_id, slot.work_dir = host_key(), task_id, str(directory)
        slot.container_name = name
        slot.updated_at = utcnow()


async def cleanup_slot(factory, index, token, *, finished=False):
    async with factory() as session, session.begin():
        slot = await session.get(Slot, index, with_for_update=True)
        if slot is None or slot.token != token:
            return False
        record = {key: getattr(slot, key) for key in ("host_key", "task_id", "container_name", "work_dir", "token", "job_id", "worker_pid", "worker_identity")}
        slot.state = "CLEANUP_REQUIRED"
    if record["host_key"] != host_key():
        return False  # only the original compile host can verify resource absence
    try:
        identity = process_identity(record["worker_pid"])
        if finished:
            if record["worker_pid"] != os.getpid() or identity != record["worker_identity"]:
                return False
        elif identity is not None and identity == record["worker_identity"]:
            return False  # lost connection is not proof that this worker stopped
    except Exception:
        return False
    if record["task_id"]:
        from app.services.isolated_latex import recover_resources
        try:
            await recover_resources(record)
        except Exception:
            return False
    async with factory() as session, session.begin():
        slot = await session.get(Slot, index, with_for_update=True)
        if slot.token != token:
            return False
        slot.state = "FREE"
        slot.token = slot.job_id = slot.task_id = slot.container_name = slot.work_dir = slot.host_key = None
        slot.worker_pid = slot.worker_identity = None
        slot.updated_at = utcnow()
    return True
