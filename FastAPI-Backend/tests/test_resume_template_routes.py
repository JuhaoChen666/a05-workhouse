"""HTTP contracts without importing the heavyweight AI application lifespan."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_resume_templates import sample

from app.api.resume_template_routes import router
from app.infrastructure.database import get_db_session
from app.infrastructure.resume_template_store import BUILTIN_ROOT, read_bundle
from app.models.resume_storage_models import ResumeTemplateModel


class Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self.rows


class Session:
    def __init__(self):
        self.rows = []
        for name in ("billryan-classic", "billryan-classic-v1.1.0", "modern-twocol-v1.1.0"):
            values = read_bundle(BUILTIN_ROOT / name)
            available = values["version"] == "1.1.0"
            self.rows.append(ResumeTemplateModel(**values, validation_status="VALIDATED" if available else "INVALID",
                is_enabled=available, validation_details={}))

    async def get(self, model, identity):
        return next((row for row in self.rows if (row.id, row.version) == identity), None)

    async def execute(self, statement):
        rows = self.rows
        parameters = statement.compile().params
        if "id_1" in parameters:
            rows = [row for row in rows if row.id == parameters["id_1"]]
        if "is_enabled" in str(statement.whereclause):
            rows = [row for row in rows if row.is_enabled]
        return Result(sorted(rows, key=lambda row: (row.id, row.version)))


def test_template_http_catalog_detail_validation_and_preview():
    app = FastAPI()
    app.include_router(router)
    session = Session()
    app.dependency_overrides[get_db_session] = lambda: session
    with TestClient(app) as client:
        catalog = client.get("/api/resume-templates").json()
        assert len(catalog) == 2 and all(row["is_enabled"] for row in catalog)
        detail = client.get("/api/resume-templates/tpl-billryan-classic").json()
        assert detail["version"] == "1.1.0" and detail["available_versions"] == ["1.0.0", "1.1.0"]
        path = "/api/resume-templates/tpl-billryan-classic/versions/1.1.0"
        assert client.get(path).json()["version"] == "1.1.0"
        assert client.get(path + "/validate").json()["valid"]
        assert not client.post(path + "/compatibility", json={"language": "en"}).json()["compatible"]
        preview = client.post(path + "/preview", json=sample().model_dump(mode="json"))
        assert preview.status_code == 200 and "Ada \\& Bob" in preview.json()["latex_source"]
        assert client.post(path + "/preview", json={"data": {"basic_info": {"name": "Ada", "extra": "bad"}}}).status_code == 422
        assert client.post("/api/resume-templates/tpl-billryan-classic/versions/1.0.0/preview", json=sample().model_dump(mode="json")).status_code == 409
        assert client.get("/api/resume-templates/unknown").status_code == 404
