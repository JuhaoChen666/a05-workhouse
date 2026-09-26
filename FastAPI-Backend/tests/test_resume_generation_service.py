from unittest.mock import AsyncMock

import pytest

from app.services.resume_generation_service import (
    build_render_data,
    jd_keywords,
    plan_resume,
    rank_experiences,
)
from app.services import resume_generation_service as generation
from app.services.resume_template_service import latex_escape


def experience(item_id, title, item_type="PROJECT", **attributes):
    return {
        "id": item_id,
        "title": title,
        "type": item_type,
        "start_date": "2025-01",
        "end_date": "present",
        "attributes": attributes,
    }


def test_keywords_and_ranking_are_stable():
    items = [
        experience("a", "支付平台", bullets=["使用 Python 和 FastAPI 重构接口"]),
        experience("b", "校园活动", bullets=["组织活动"]),
    ]
    assert jd_keywords("Python FastAPI Docker")[:2] == ["python", "fastapi"]
    chosen, matches, ids = rank_experiences(items, "Python FastAPI", None)
    assert ids == ["a", "b"]
    assert matches["a"] == ["python", "fastapi"]
    assert chosen[0]["id"] == "a"


def test_one_page_ranking_prefers_high_value_content_and_caps_density():
    items = [
        experience("work", "核心工作", "WORK", bullets=["负责 Python 服务上线，性能提升 30%"]),
        experience("project", "核心项目", "PROJECT", tech_stack=["Python", "FastAPI"],
                   bullets=["使用 FastAPI 完成接口和性能优化"]),
        *[
            experience(f"low-{index}", f"零散记录 {index}", "PROJECT",
                       bullets=["参与日常工作"] * 5)
            for index in range(6)
        ],
    ]
    chosen, _, ids = rank_experiences(items, "Python FastAPI 性能优化", None, target_pages=1)
    assert len(chosen) <= 8
    assert set(ids[:2]) == {"work", "project"}


def test_two_page_ranking_allows_more_content():
    items = [
        experience(f"item-{index}", f"项目 {index}", "PROJECT", bullets=["参与项目"])
        for index in range(10)
    ]
    chosen, _, _ = rank_experiences(items, "项目", None, target_pages=2)
    assert len(chosen) == 10


@pytest.mark.asyncio
async def test_ai_selection_is_recut_for_one_page(monkeypatch):
    facts = [
        experience("work", "工作经历", "WORK", role="工程师", bullets=["负责服务上线"]),
        experience("project-core", "核心项目", "PROJECT", bullets=["参与项目"]),
        *[
            experience(f"item-{index}", f"项目 {index}", "PROJECT", bullets=["参与项目"])
            for index in range(8)
        ],
    ]
    ai = generation.StructuredAIPlan(
        selected_item_ids=["project-core"],
        module_order=list(generation.FIXED_SECTIONS),
    )
    monkeypatch.setattr(generation, "request_structured_ai_plan", AsyncMock(return_value=ai))
    data, _, plan = await generation.build_ai_plan(
        jd_text="项目",
        experiences=facts,
        personal_info={},
        selected_item_ids=None,
        target_pages=1,
    )
    assert len(plan["selected_item_ids"]) <= 8
    assert "work" in plan["selected_item_ids"]
    assert [entry.company for entry in data.work] == ["工作经历"]
    assert plan["selection_policy"] == "quality_ranked_page_1"


def test_render_data_uses_only_structured_experience_fields():
    data, traces, plan = plan_resume(
        jd_text="Python",
        experiences=[experience("a", "支付平台", bullets=["提升吞吐量 20%"])],
        personal_info={"name": "张三"},
        selected_item_ids=None,
    )
    assert data.basic_info.name == "张三"
    assert data.projects[0].title == "支付平台"
    assert traces[0].source_item_id == "a"
    assert plan["recommendation_engine"] == "keyword_ranked_safe_tailoring"


def test_latex_escape_covers_special_user_text():
    escaped = latex_escape(r"ACME_50% {A&B} $x$")
    assert r"\_" in escaped
    assert r"\%" in escaped
    assert r"\{" in escaped and r"\}" in escaped
    assert r"\&" in escaped and r"\$" in escaped


def test_empty_experience_still_builds_valid_render_data():
    data = build_render_data([], {"name": "Candidate"})
    assert data.basic_info.name == "Candidate"
    assert data.work == []
    assert data.projects == []
