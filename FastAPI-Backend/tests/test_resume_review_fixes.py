"""Regression evidence for the independent review's integration defects."""
from unittest.mock import AsyncMock
import copy
import json
import pytest
import httpx
from app.api import resume_generation_routes as routes
from app.services import resume_generation_service as generation
from app.services import isolated_latex as sandbox
from app.models.resume_template_contracts import FIXED_SECTIONS


@pytest.mark.asyncio
async def test_actual_spring_position_contract_is_normalized(monkeypatch):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"code": "0", "msg": "ok",
        "data": {"id": 3, "responsibility": "开发后端服务", "skill_requirements": "Python 和 MySQL"}}))
    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    result = await routes._resolve_job("3")
    assert result["jobContent"] == "开发后端服务\n\nPython 和 MySQL"
    assert result["source"]["id"] == 3


@pytest.mark.asyncio
async def test_reviewed_rewrite_is_applied_with_original_trace(monkeypatch):
    facts = [{"id": "own", "title": "项目", "type": "PROJECT", "attributes": {"bullets": ["使用 Python 提升吞吐量 20%"]}}]
    ai = generation.StructuredAIPlan(selected_item_ids=["own"], module_order=list(FIXED_SECTIONS),
        tailored_bullets=[{"source_item_id": "own", "original_bullet": facts[0]["attributes"]["bullets"][0],
            "tailored_bullet": "通过 Python 优化，吞吐量提升 20%"}], keyword_matches={"own": ["Python", "AWS"]}, trim_suggestions=["减少无关项目"])
    monkeypatch.setattr(generation, "request_structured_ai_plan", AsyncMock(return_value=ai))
    original = copy.deepcopy(facts)
    _, _, plan = await generation.build_ai_plan(jd_text="Python", experiences=facts, personal_info={}, selected_item_ids=None)
    assert plan["review_required"] and plan["keyword_matches"] == {"own": ["Python"]}
    assert plan["trim_suggestions"] == ["减少无关项目"]
    plan["version"] = generation.review_version(plan)
    data, traces, confirmed = generation.apply_review(plan, {"version": plan["version"], "accepted_indices": [0]}, facts, {})
    assert data.projects[0].bullets == [ai.tailored_bullets[0].tailored_bullet]
    assert traces[0].original_bullet == original[0]["attributes"]["bullets"][0]
    assert traces[0].tailored_bullet != traces[0].original_bullet
    assert confirmed["review_status"] == "CONFIRMED" and facts == original
    rejected, _, _ = generation.apply_review(plan, {"version": plan["version"], "accepted_indices": []}, facts, {})
    assert rejected.projects[0].bullets == original[0]["attributes"]["bullets"]
    with pytest.raises(generation.LatexCompileError, match="VERSION_CONFLICT"):
        generation.apply_review(plan, {"version": "0" * 64, "accepted_indices": [0]}, facts, {})


@pytest.mark.asyncio
async def test_crash_resource_cleanup_verifies_absence_and_keeps_unknown_data(monkeypatch, tmp_path):
    task = "a" * 32
    root = tmp_path / ("resume-compile-" + task)
    root.mkdir()
    record = {"task_id": task, "work_dir": str(root), "token": "owned", "job_id": "owned-job"}
    (root / "identity.json").write_text(json.dumps(record), encoding="utf8")
    (root / "input.json").write_text("private input", encoding="utf8")
    (root / "unexpected.txt").write_text("preserve", encoding="utf8")
    monkeypatch.setenv("RESUME_COMPILE_WORK_ROOT", str(tmp_path))
    monkeypatch.setattr(sandbox.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(sandbox, "_capture", AsyncMock(return_value=(0, b"")))
    with pytest.raises(sandbox.SandboxError, match="UNEXPECTED_FILE"):
        await sandbox.recover_resources(record)
    assert (root / "input.json").exists() and (root / "unexpected.txt").read_text() == "preserve"
    # Only remove this test's known generated sentinel, then recover registered inputs.
    (root / "unexpected.txt").unlink()
    await sandbox.recover_resources(record)
    assert not root.exists()
