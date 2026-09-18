"""Real source file validation and ASGI confirmation, with database operations isolated."""
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import httpx
import pytest
from app.api.experience_app import create_experience_app
from app.api.experience_dependencies import experience_session, private_store as store_dependency
from app.services.experience_import_service import ExperienceImportService
from app.models.resume_storage_models import utcnow
from test_phase2_boundaries import jwt_config, auth, text_pdf


class IsolatedSession:
    def __init__(self):
        self.info = {}
        self.active = False
        self.commits = self.rollbacks = 0

    def in_transaction(self):
        return self.active

    async def begin(self):
        self.active = True
        return self

    async def commit(self):
        self.active = False
        self.commits += 1

    async def rollback(self):
        self.active = False
        self.rollbacks += 1


@pytest.mark.parametrize("failure", ["digest", "size", "missing", "media", "metadata"])
async def test_confirm_invalid_source_returns_409_before_draft_writes(
    private_store, jwt_config, monkeypatch, failure
):
    original = text_pdf()
    asset = private_store.write(71, original, "pdf")
    path = private_store.path(71, asset.key)
    metadata = asset.model_dump(mode="json")
    if failure == "digest":
        path.write_bytes(b"x" + original[1:])  # Same length, different SHA256.
    elif failure == "size":
        path.write_bytes(original[:-1])
    elif failure == "missing":
        path.unlink()  # Only this test's freshly generated file.
    elif failure == "media":
        metadata["media_type"] = "application/octet-stream"
    else:
        metadata["sha256"] = "invalid"

    session = IsolatedSession()
    batch = SimpleNamespace(status="READY", expires_at=utcnow() + timedelta(days=1),
                            source_asset=metadata, confirmation_digest=None, confirmation_result=None)
    owned_batch = AsyncMock(return_value=batch)
    owned_draft = AsyncMock(side_effect=AssertionError("Source must be checked before draft writes"))
    monkeypatch.setattr(ExperienceImportService, "owned_batch", owned_batch)
    monkeypatch.setattr(ExperienceImportService, "owned_draft", owned_draft)

    @asynccontextmanager
    async def isolated_mutex(*args):
        yield

    # Keep the real transaction coordinator; only the MySQL advisory lock is isolated.
    monkeypatch.setattr("app.infrastructure.private_resume_assets.root_mutex", isolated_mutex)

    async def db():
        yield session

    app = create_experience_app()
    app.dependency_overrides[experience_session] = db
    app.dependency_overrides[store_dependency] = lambda: private_store
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                base_url="http://test") as client:
        response = await client.post(f"/api/experience-imports/{uuid4()}/confirm", headers=auth(),
            json={"items": [{"id": str(uuid4()), "expected_revision": 1}]})

    assert response.status_code == 409, response.text
    assert response.json() == {"detail": {"code": "PDF_SOURCE_UNAVAILABLE", "message": "Import source unavailable"}}
    owned_draft.assert_not_awaited()
    assert session.commits == 0 and session.rollbacks == 1
    assert batch.status == "READY" and batch.confirmation_result is None
    assert "resume_private_assets" not in session.info
