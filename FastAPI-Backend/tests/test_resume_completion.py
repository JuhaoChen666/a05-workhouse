"""Behavioral acceptance for generation options and source/fact boundaries."""
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from pypdf import PdfWriter
from app.infrastructure.resume_template_store import BUILTIN_ROOT, read_bundle
from app.models.resume_template_contracts import FIXED_SECTIONS, TemplatePreviewRequest
from app.services.resume_template_service import render_snapshot, validate_snapshot
from app.services.resume_template_service import TemplateProtocolError
from app.services import resume_generation_service as generation
from app.services.isolated_latex import SandboxError, compile_isolated, container_command, docker_environment


def item(id="owned"):
    return {"id": id, "type": "PROJECT", "title": "事实项目", "attributes": {"bullets": ["使用 Python 提升吞吐量 20%"]}}


@pytest.mark.asyncio
async def test_manual_preserves_selection_order_and_never_calls_ai(monkeypatch):
    ai = AsyncMock(side_effect=AssertionError("manual must not call AI"))
    monkeypatch.setattr(generation, "request_structured_ai_plan", ai)
    data, traces, plan = await generation.build_ai_plan(jd_text="Python", experiences=[item("a"), item("b")],
        personal_info={"name": "张三"}, selected_item_ids=["b", "a"], mode="MANUAL_ONLY")
    assert [trace.source_item_id for trace in traces] == ["b", "a"]
    assert plan["ai_status"] == "NOT_REQUESTED"
    ai.assert_not_awaited()


@pytest.mark.parametrize("selected,original,rewritten", [
    (["other-user"], "使用 Python 提升吞吐量 20%", "使用 Python 提升吞吐量 20%"),
    (["owned"], "虚构原文", "虚构原文"),
    (["owned"], "使用 Python 提升吞吐量 20%", "使用 Python 提升吞吐量 90%"),
])
def test_fabricated_source_or_fact_is_rejected(selected, original, rewritten):
    ai = generation.StructuredAIPlan(selected_item_ids=selected, module_order=list(FIXED_SECTIONS),
        tailored_bullets=[{"source_item_id": selected[0], "original_bullet": original, "tailored_bullet": rewritten}])
    with pytest.raises(generation.LatexCompileError):
        generation.validated_plan(ai, [item()])


@pytest.mark.asyncio
async def test_unverified_semantic_rewrite_preserves_original_and_reports_it(monkeypatch):
    ai = generation.StructuredAIPlan(selected_item_ids=["owned"], module_order=list(FIXED_SECTIONS),
        tailored_bullets=[{"source_item_id": "owned", "original_bullet": item()["attributes"]["bullets"][0],
                          "tailored_bullet": "在虚构公司领导 Python 团队，提升吞吐量 20%"}])
    monkeypatch.setattr(generation, "request_structured_ai_plan", AsyncMock(return_value=ai))
    data, traces, plan = await generation.build_ai_plan(jd_text="Python", experiences=[item()],
        personal_info={}, selected_item_ids=None)
    assert traces[0].tailored_bullet == traces[0].original_bullet
    assert "虚构公司" not in str(data)
    assert plan["unverified_rewrites_preserved"] == 1


@pytest.mark.asyncio
async def test_ai_failure_is_explicit_degradation(monkeypatch):
    monkeypatch.setattr(generation, "request_structured_ai_plan", AsyncMock(side_effect=generation.AIUnavailable("AI_NOT_CONFIGURED")))
    _, _, plan = await generation.build_ai_plan(jd_text="Python", experiences=[item()], personal_info={}, selected_item_ids=None)
    assert plan["ai_status"] == "DEGRADED" and plan["ai_error_code"] == "AI_NOT_CONFIGURED"


@pytest.mark.parametrize("name", ["billryan-classic-v1.2.0", "modern-twocol-v1.2.0"])
def test_versioned_templates_render_real_order_and_language(name):
    bundle = read_bundle(BUILTIN_ROOT / name)
    report = validate_snapshot(bundle)
    assert report.valid, report.issues
    order = ["basic_info", "projects", "education", "skills", "work", "certificates", "competitions"]
    request = TemplatePreviewRequest(data={"basic_info": {"name": "中 & 文"},
        "education": [{"school": "学校"}], "projects": [{"title": "项目", "bullets": ["50%_test"]}]},
        options={"language": "en", "module_order": order})
    source = render_snapshot(bundle, request).latex_source
    assert source.index("Projects") < source.index("Education")
    assert "中 \\& 文" in source and "50\\%\\_test" in source
    zh = render_snapshot(bundle, request.model_copy(update={"options": request.options.model_copy(update={"language": "zh"})})).latex_source
    assert "项目经历" in zh and source != zh


def test_target_pages_checks_actual_pdf_not_saved_option():
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=595, height=842)
    output = BytesIO()
    writer.write(output)
    assert generation.pdf_page_count(output.getvalue(), 2) == 2
    with pytest.raises(generation.LatexCompileError, match="PAGE_LIMIT_EXCEEDED"):
        generation.pdf_page_count(output.getvalue(), 1)


def test_sandbox_command_limits_and_secret_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "must-not-inherit")
    monkeypatch.setenv("DATABASE_URL", "must-not-inherit")
    assert not {"DEEPSEEK_API_KEY", "DATABASE_URL"} & docker_environment().keys()
    command = container_command("docker", "sha256:" + "a" * 64, tmp_path, "test")
    for flag in ("--network=none", "--read-only", "--cap-drop=ALL", "--memory=512m", "--pids-limit=32", "--user=65532:65532"):
        assert flag in command
    assert "--privileged" not in command and "--env" not in command


@pytest.mark.asyncio
async def test_missing_isolation_fails_closed(monkeypatch):
    monkeypatch.delenv("RESUME_LATEX_IMAGE", raising=False)
    with pytest.raises(SandboxError, match="SANDBOX_UNAVAILABLE"):
        await compile_isolated("source")


def test_historical_version_does_not_silently_ignore_new_options():
    bundle = read_bundle(BUILTIN_ROOT / "billryan-classic-v1.1.0")
    request = TemplatePreviewRequest(data={"basic_info": {"name": "Candidate"}})
    original = render_snapshot(bundle, request).latex_source
    assert "Candidate" in original
    with pytest.raises(TemplateProtocolError):
        render_snapshot(bundle, request.model_copy(update={"options": request.options.model_copy(update={"language": "en"})}))


@pytest.mark.asyncio
async def test_container_timeout_removes_only_verified_task_container(monkeypatch, tmp_path):
    import asyncio
    import json
    from app.services import isolated_latex as sandbox
    monkeypatch.setenv("RESUME_LATEX_IMAGE", "sha256:" + "a" * 64)
    monkeypatch.setenv("RESUME_COMPILE_WORK_ROOT", str(tmp_path))
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: "docker")
    calls, task = [], []
    async def capture(command, **kwargs):
        calls.append(command)
        if command[1] == "info":
            return 0, json.dumps({"OSType": "linux", "CgroupDriver": "systemd", "MemoryLimit": True, "SwapLimit": True, "CpuCfsQuota": True,
                "PidsLimit": True, "SecurityOptions": ["name=seccomp,profile=builtin"]}).encode()
        if command[1] == "run":
            from pathlib import Path
            Path(command[command.index("--cidfile") + 1]).write_text("b" * 64)
            task.append(command[command.index("--label") + 1].split("=", 1)[1])
            raise asyncio.TimeoutError()
        if command[1] == "inspect":
            return 0, task[0].encode()
        assert command == ["docker", "rm", "--force", "b" * 64]
        return 0, b""
    monkeypatch.setattr(sandbox, "_capture", capture)
    with pytest.raises(SandboxError, match="COMPILE_TIMEOUT"):
        await sandbox.compile_isolated("source")
    assert calls[-1] == ["docker", "rm", "--force", "b" * 64]


@pytest.mark.asyncio
async def test_container_owner_mismatch_refuses_removal(monkeypatch, tmp_path):
    from app.services import isolated_latex as sandbox
    (tmp_path / "container.id").write_text("a" * 64)
    calls = []
    async def capture(command, **kwargs):
        calls.append(command)
        return 0, b"other-task"
    monkeypatch.setattr(sandbox, "_capture", capture)
    with pytest.raises(SandboxError, match="OWNER_MISMATCH"):
        await sandbox._remove_owned("docker", tmp_path, "this-task")
    assert len(calls) == 1 and calls[0][1] == "inspect"


def test_resume_app_explicit_development_origin(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.resume_app import create_resume_app
    monkeypatch.setenv("RESUME_FRONTEND_ORIGINS", "http://127.0.0.1:5173")
    with TestClient(create_resume_app()) as client:
        response = client.options("/api/resume-documents", headers={"Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "Authorization"})
        assert response.status_code == 200 and response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


@pytest.mark.asyncio
async def test_linux_daemon_without_required_limits_refuses_compile(monkeypatch, tmp_path):
    import json
    from app.services import isolated_latex as sandbox
    monkeypatch.setenv("RESUME_LATEX_IMAGE", "sha256:" + "a" * 64)
    monkeypatch.setenv("RESUME_COMPILE_WORK_ROOT", str(tmp_path))
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: "docker")
    calls = []
    async def capture(command, **kwargs):
        calls.append(command)
        return 0, json.dumps({"OSType": "linux", "MemoryLimit": False}).encode()
    monkeypatch.setattr(sandbox, "_capture", capture)
    with pytest.raises(SandboxError, match="SANDBOX_UNAVAILABLE"):
        await sandbox.compile_isolated("source")
    assert len(calls) == 1 and calls[0][1] == "info"
