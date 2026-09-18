"""Opt-in real Linux Docker integration; absence is explicitly reported as skipped."""
import os
import pytest
from app.services.isolated_latex import compile_isolated, SandboxError
from app.services.resume_generation_service import pdf_page_count

pytestmark = pytest.mark.skipif(os.environ.get("RUN_RESUME_DOCKER_INTEGRATION") != "1",
    reason="explicit RUN_RESUME_DOCKER_INTEGRATION=1 with trusted immutable image and Linux daemon required")


@pytest.mark.asyncio
async def test_real_container_compiles_pdf():
    source = r"\documentclass{article}\begin{document}Isolated compilation\end{document}"
    assert pdf_page_count(await compile_isolated(source), 1) == 1


@pytest.mark.asyncio
async def test_real_container_cannot_read_absolute_host_path():
    source = r"\documentclass{article}\begin{document}\input{/etc/passwd}\end{document}"
    with pytest.raises(SandboxError, match="COMPILE_FAILED"):
        await compile_isolated(source)


@pytest.mark.asyncio
async def test_real_container_timeout():
    source = r"\documentclass{article}\begin{document}\loop\iftrue\repeat\end{document}"
    with pytest.raises(SandboxError, match="COMPILE_TIMEOUT"):
        await compile_isolated(source)
