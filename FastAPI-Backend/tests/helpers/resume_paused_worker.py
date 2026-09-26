"""Test-only child process: pause a claimed job; never used by the deployed worker."""
import asyncio
import os
from pathlib import Path
from app.services.resume_worker import run_once
from app.services.resume_generation_service import LatexCompileError


async def paused_compiler(*args):
    Path(os.environ["RESUME_WORKER_TEST_MARKER"]).write_text("claimed", encoding="ascii")
    await asyncio.sleep(20)
    raise LatexCompileError("TEST_PAUSE_EXPIRED")


asyncio.run(run_once(compiler=paused_compiler))
