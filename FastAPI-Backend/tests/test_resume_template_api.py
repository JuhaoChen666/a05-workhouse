"""API integration tests for LaTeX template endpoints."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.resume_template_routes import router
from app.infrastructure.database import get_db_session
from app.infrastructure.resume_template_store import BUILTIN_ROOT, read_bundle
from app.models.resume_storage_models import ResumeTemplateModel
from app.services.resume_template_service import validate_template


@pytest.fixture
def template_bundles():
    bundles = {}
    for name in ("billryan-classic-v1.1.0", "modern-twocol-v1.1.0"):
        b = read_bundle(BUILTIN_ROOT / name)
        report = validate_template(b["metadata_json"], b["main_source"])
        row = ResumeTemplateModel(
            **b,
            validation_status="VALIDATED" if report.valid else "INVALID",
            is_enabled=report.valid,
            validation_details=report.model_dump(mode="json"),
            created_at=None,
        )
        bundles[(row.id, row.version)] = row
    return bundles


@pytest.fixture
def test_app(template_bundles):
    app = FastAPI()
    app.include_router(router)

    mock_session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        rows = list(template_bundles.values())
        mock_result.scalars.return_value = rows
        return mock_result

    async def mock_get(model, pk):
        return template_bundles.get(pk)

    mock_session.execute.side_effect = mock_execute
    mock_session.get.side_effect = mock_get

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_get_db
    return app


@pytest.mark.asyncio
async def test_list_templates(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/resume-templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        ids = {item["id"] for item in data}
        assert "tpl-billryan-classic" in ids
        assert "tpl-modern-twocol" in ids
        for item in data:
            assert item["is_enabled"] is True
            assert item["validation_status"] == "VALIDATED"
            assert item["protocol_version"] == "1.0"


@pytest.mark.asyncio
async def test_get_template_detail_and_versions(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Latest version
        response = await client.get("/api/resume-templates/tpl-billryan-classic")
        assert response.status_code == 200
        detail = response.json()
        assert detail["id"] == "tpl-billryan-classic"
        assert detail["version"] == "1.1.0"
        assert "available_versions" in detail
        assert "metadata" in detail

        # List versions
        response = await client.get("/api/resume-templates/tpl-billryan-classic/versions")
        assert response.status_code == 200
        versions = response.json()
        assert any(v["version"] == "1.1.0" for v in versions)

        # Specific version
        response = await client.get("/api/resume-templates/tpl-billryan-classic/versions/1.1.0")
        assert response.status_code == 200
        assert response.json()["version"] == "1.1.0"

        # Not found
        response = await client.get("/api/resume-templates/tpl-billryan-classic/versions/9.9.9")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_validate_version_endpoint(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/resume-templates/tpl-billryan-classic/versions/1.1.0/validate")
        assert response.status_code == 200
        report = response.json()
        assert report["valid"] is True
        assert report["protocol_version"] == "1.0"
        assert len(report["issues"]) == 0


@pytest.mark.asyncio
async def test_compatibility_endpoint(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Compatible request
        response = await client.post(
            "/api/resume-templates/tpl-billryan-classic/versions/1.1.0/compatibility",
            json={
                "language": "zh",
                "target_pages": 1,
                "show_avatar": False,
                "sections": ["basic_info", "education", "skills", "work", "projects", "certificates", "competitions"],
            },
        )
        assert response.status_code == 200
        assert response.json()["compatible"] is True

        # Incompatible request: unsupported language and avatar conflict
        response = await client.post(
            "/api/resume-templates/tpl-billryan-classic/versions/1.1.0/compatibility",
            json={
                "language": "en",
                "target_pages": 1,
                "show_avatar": True,
                "sections": ["basic_info", "work"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["compatible"] is False
        issue_codes = {issue["code"] for issue in body["issues"]}
        assert "LANGUAGE" in issue_codes
        assert "AVATAR" in issue_codes


@pytest.mark.asyncio
async def test_preview_endpoint(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid preview with 7 modules
        payload = {
            "data": {
                "basic_info": {"name": "张三", "title": "全栈开发", "email": "zhang@example.com"},
                "education": [{"school": "浙江大学", "major": "软件工程", "degree": "学士"}],
                "skills": [{"category": "后端开发", "items": "Python & Go"}],
                "work": [{"company": "阿里巴巴", "role": "工程师", "bullets": ["优化高并发架构"]}],
                "projects": [{"title": "分布式任务调度系统", "bullets": ["提高系统吞吐量"]}],
                "certificates": [{"title": "AWS 解决方案架构师"}],
                "competitions": [{"title": "ACM/ICPC 区域赛", "award_level": "银牌"}],
            },
            "options": {"show_avatar": False},
        }
        response = await client.post("/api/resume-templates/tpl-billryan-classic/versions/1.1.0/preview", json=payload)
        assert response.status_code == 200
        preview = response.json()
        assert preview["template_id"] == "tpl-billryan-classic"
        assert preview["version"] == "1.1.0"
        assert preview["source_sha256"]
        assert "张三" in preview["latex_source"]
        assert "Python \\& Go" in preview["latex_source"]

        # Avatar unsupported check (status 422)
        payload["options"]["show_avatar"] = True
        response = await client.post("/api/resume-templates/tpl-billryan-classic/versions/1.1.0/preview", json=payload)
        assert response.status_code == 422
