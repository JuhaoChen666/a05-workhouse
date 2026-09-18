from app.services.resume_generation_service import (
    build_render_data,
    jd_keywords,
    plan_resume,
    rank_experiences,
)
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
