"""Fail-closed Linux Docker compiler. The container receives only frozen inputs."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shutil
from pathlib import Path
from uuid import uuid4

MAX_OUTPUT = 18 * 1024 * 1024


class SandboxError(RuntimeError):
    def __init__(self, message, *, location=None):
        super().__init__(message)
        self.location = location


def docker_environment():
    # These configure the CLI, never the container. Do not inherit application secrets.
    names = ("PATH", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP", "DOCKER_HOST", "DOCKER_CONTEXT",
             "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH")
    return {key: os.environ[key] for key in names if key in os.environ}


async def _capture(command, *, timeout=40, limit=MAX_OUTPUT):
    process = await asyncio.create_subprocess_exec(
        *command, env=docker_environment(), stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    async def read():
        chunks, size = [], 0
        while chunk := await process.stdout.read(65536):
            size += len(chunk)
            if size > limit:
                raise SandboxError("SANDBOX_OUTPUT_LIMIT")
            chunks.append(chunk)
        await process.wait()
        return process.returncode, b"".join(chunks)
    try:
        return await asyncio.wait_for(read(), timeout)
    except BaseException:
        if process.returncode is None:
            process.kill()  # only this task's Docker CLI; the caller cleans its container
            await process.wait()
        raise


def container_command(docker, image, root, task_id):
    return [docker, "run", "--rm", "--pull=never", "--name", f"resume-compile-{task_id}",
            "--label", f"resume.compile.task={task_id}", "--cidfile", str(root / "container.id"),
            "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--user=65532:65532", "--memory=512m", "--memory-swap=512m", "--cpus=1", "--pids-limit=32",
            "--tmpfs=/work:rw,noexec,nosuid,size=128m,mode=1777",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=64m,mode=1777",
            "--mount", f"type=bind,src={root / 'input.json'},dst=/input.json,readonly",
            "--workdir=/work", image, "python3", "/opt/compile_resume.py"]


async def _remove_owned(docker, root, task_id):
    cid_file = root / "container.id"
    if not cid_file.exists():
        return
    cid = cid_file.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9]{64}", cid):
        raise SandboxError("SANDBOX_CLEANUP_ID_INVALID")
    code, output = await _capture([docker, "inspect", "--format",
        '{{ index .Config.Labels "resume.compile.task" }}', cid], timeout=10, limit=8192)
    if code == 0 and output.decode().strip() == task_id:
        code, _ = await _capture([docker, "rm", "--force", cid], timeout=10, limit=8192)
        if code:
            raise SandboxError("SANDBOX_CLEANUP_FAILED")
    elif code == 0:
        raise SandboxError("SANDBOX_CLEANUP_OWNER_MISMATCH")


async def compile_isolated(source, resources=None):
    docker = shutil.which("docker")
    image = os.environ.get("RESUME_LATEX_IMAGE", "")
    if not docker or not re.fullmatch(r"(?:sha256:[a-f0-9]{64}|[\w./:-]+@sha256:[a-f0-9]{64})", image):
        raise SandboxError("SANDBOX_UNAVAILABLE: configure Docker and an immutable trusted RESUME_LATEX_IMAGE")
    from app.infrastructure.resume_template_store import safe_path
    work_root = os.environ.get("RESUME_COMPILE_WORK_ROOT", "")
    if not work_root or not Path(work_root).is_absolute():
        raise SandboxError("SANDBOX_UNAVAILABLE: configure absolute RESUME_COMPILE_WORK_ROOT")
    work_root = safe_path(work_root).resolve(strict=True)
    if not work_root.is_dir() or work_root == Path(work_root.anchor):
        raise SandboxError("SANDBOX_UNAVAILABLE: invalid compile workspace")
    code, output = await _capture([docker, "info", "--format", "{{json .}}"], timeout=10, limit=32768)
    try:
        capabilities = json.loads(output)
    except ValueError:
        raise SandboxError("SANDBOX_UNAVAILABLE: Docker capabilities unavailable") from None
    if code or capabilities.get("OSType") != "linux" or capabilities.get("CgroupDriver") not in ("systemd", "cgroupfs") or any(capabilities.get(key) is not True
            for key in ("MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit")) or not any(
            "name=seccomp" in item and "unconfined" not in item for item in capabilities.get("SecurityOptions", [])):
        raise SandboxError("SANDBOX_UNAVAILABLE: Linux memory/swap/CPU/PID limits and seccomp required")
    task_id = uuid4().hex
    from app.services.resume_execution import register_compile, execution
    root = work_root / f"resume-compile-{task_id}"
    await register_compile(task_id, root)
    root.mkdir()
    context = execution.get()
    record = {"task_id": task_id, "work_dir": str(root), "token": context["token"] if context else None,
        "job_id": context["job_id"] if context else None}
    (root / "identity.json").write_text(json.dumps(record), encoding="utf8")
    try:
        (root / "input.json").write_text(json.dumps({"source": source, "resources": resources or {}}), encoding="utf-8")
        try:
            code, output = await _capture(container_command(docker, image, root, task_id))
            if code in (125, 126, 127):
                raise SandboxError("SANDBOX_UNAVAILABLE: container startup failed; verify image, mount and daemon limits")
            if code:
                raise SandboxError("COMPILE_FAILED: check template or reduce content")
            payload = json.loads(output)
            if "error" in payload:
                code = payload["error"]
                if code not in {"COMPILE_TIMEOUT", "COMPILE_FAILED", "COMPILE_RESOURCE_LIMIT"}:
                    code = "COMPILE_OUTPUT_INVALID"
                location = payload.get("location")
                if not isinstance(location, str) or not re.fullmatch(r"line [0-9]{1,6}", location):
                    location = None
                raise SandboxError(code, location=location)
            pdf = base64.b64decode(payload["pdf"], validate=True)
            if not pdf.startswith(b"%PDF-") or len(pdf) > 12 * 1024 * 1024:
                raise SandboxError("COMPILE_OUTPUT_INVALID")
            return pdf
        except asyncio.TimeoutError:
            raise SandboxError("COMPILE_TIMEOUT") from None
        except (ValueError, KeyError):
            raise SandboxError("COMPILE_OUTPUT_INVALID") from None
        finally:
            await asyncio.shield(recover_resources(record))
    except BaseException:
        # Do not remove inputs until container absence is verified. Persistent slot
        # remains unavailable if cleanup fails and is recovered on the same host.
        raise


async def recover_resources(record):
    """Only recover an explicitly registered task directory and its exact label."""
    from app.infrastructure.resume_template_store import safe_path
    task_id = record["task_id"]
    if not re.fullmatch(r"[a-f0-9]{32}", task_id):
        raise SandboxError("SANDBOX_CLEANUP_ID_INVALID")
    configured = os.environ.get("RESUME_COMPILE_WORK_ROOT", "")
    if not configured or not Path(configured).is_absolute():
        raise SandboxError("SANDBOX_CLEANUP_ROOT_INVALID")
    base = safe_path(configured).resolve(strict=True)
    root = safe_path(record["work_dir"]).resolve()
    if root.parent != base or root.name != f"resume-compile-{task_id}":
        raise SandboxError("SANDBOX_CLEANUP_PATH_INVALID")
    docker = shutil.which("docker")
    if not docker:
        raise SandboxError("SANDBOX_UNAVAILABLE")
    # ps must succeed: a daemon error is not evidence that the container is absent.
    code, output = await _capture([docker, "ps", "-aq", "--no-trunc", "--filter", f"name=^/resume-compile-{task_id}$"], timeout=10, limit=8192)
    if code:
        raise SandboxError("SANDBOX_CLEANUP_UNCONFIRMED")
    for cid in output.decode("ascii").split():
        if not re.fullmatch(r"[a-f0-9]{64}", cid):
            raise SandboxError("SANDBOX_CLEANUP_ID_INVALID")
        code, label = await _capture([docker, "inspect", "--format", '{{ index .Config.Labels "resume.compile.task" }}', cid], timeout=10, limit=8192)
        if code or label.decode().strip() != task_id:
            raise SandboxError("SANDBOX_CLEANUP_OWNER_MISMATCH")
        code, _ = await _capture([docker, "rm", "--force", cid], timeout=10, limit=8192)
        if code:
            # --rm may have won the race; verify absence below instead of guessing.
            pass
    code, remaining = await _capture([docker, "ps", "-aq", "--no-trunc", "--filter", f"name=^/resume-compile-{task_id}$"], timeout=10, limit=8192)
    if code or remaining.strip():
        raise SandboxError("SANDBOX_CLEANUP_UNCONFIRMED")
    if not root.exists():
        return
    marker = safe_path(root / "identity.json")
    if not marker.exists():
        # Crash between mkdir and marker: only remove an empty registered directory.
        if any(root.iterdir()):
            raise SandboxError("SANDBOX_CLEANUP_OWNER_MISMATCH")
        root.rmdir()
        return
    identity = json.loads(marker.read_text(encoding="utf8"))
    if any(identity.get(key) != record.get(key) for key in ("task_id", "work_dir", "token", "job_id")):
        raise SandboxError("SANDBOX_CLEANUP_OWNER_MISMATCH")
    # Exact known task files; never recurse or follow links into other directories.
    if any(path.name not in {"identity.json", "input.json", "container.id"} for path in root.iterdir()):
        raise SandboxError("SANDBOX_CLEANUP_UNEXPECTED_FILE")
    for name in ("input.json", "container.id", "identity.json"):
        path = safe_path(root / name)
        if path.exists():
            if not path.is_file():
                raise SandboxError("SANDBOX_CLEANUP_PATH_INVALID")
            path.unlink()
    root.rmdir()
