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


@pytest.mark.parametrize("name", ["billryan-classic-v1.2.0", "modern-twocol-v1.2.0"])
@pytest.mark.asyncio
async def test_real_container_compiles_actual_chinese_template(name):
    from app.infrastructure.resume_template_store import BUILTIN_ROOT, read_bundle
    from app.models.resume_template_contracts import TemplatePreviewRequest
    from app.services.resume_template_service import render_snapshot
    bundle = read_bundle(BUILTIN_ROOT / name)
    source = render_snapshot(bundle, TemplatePreviewRequest(data={"basic_info": {"name": "中文测试"},
        "projects": [{"title": "项目 & 特殊字符", "bullets": ["提升效率 20%"]}]})).latex_source
    pdf = await compile_isolated(source, bundle["resources"])
    assert pdf_page_count(pdf, 2) <= 2
    from io import BytesIO
    from pypdf import PdfReader
    assert "中文测试" in "".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)


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
