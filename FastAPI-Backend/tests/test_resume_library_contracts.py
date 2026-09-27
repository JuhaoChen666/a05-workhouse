from datetime import datetime, timezone
from io import BytesIO
import multiprocessing
from types import SimpleNamespace

import pytest

from app.api.resume_library_routes import _api_time, merge_resume_items
from app.models.resume_storage_contracts import FileAsset
from app.services import resume_thumbnails
from app.services.resume_thumbnails import MAX_PIXELS
from app.infrastructure.private_resume_assets import thumbnail_cleanup_plan
from app.infrastructure.mapper.resume_storage_mapper import copy_thumbnail_state
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4


def test_merge_keeps_complete_pages_and_numeric_upload_ids():
    same_time = datetime(2026, 9, 27, 12, 0)
    uploads = [SimpleNamespace(id=i, filename=f"u{i}.pdf", uploaded_at=same_time) for i in range(1, 236)]
    generated = [SimpleNamespace(id=f"00000000-0000-0000-0000-{i:012x}", name=f"g{i}",
        format="latex", generation_job_id=f"job-{i}", copied_from_id=None,
        created_at=datetime(2026, 9, 27, 4, 0), updated_at=datetime(2026, 9, 27, 4, 0))
        for i in range(1, 19)]

    first = merge_resume_items(uploads[:], generated[:], page=1, page_size=100)
    second = merge_resume_items(uploads[:], generated[:], page=2, page_size=100)
    third = merge_resume_items(uploads[:], generated[:], page=3, page_size=100)
    all_items = first + second + third

    assert len(all_items) == 253
    assert len({item["key"] for item in all_items}) == 253
    uploaded_ids = [item["id"] for item in all_items if item["kind"] == "uploaded"]
    assert uploaded_ids == list(range(235, 0, -1))
    assert all(item["updated_at"].endswith("+00:00") for item in all_items)
    assert all(item["document"]["id"] == item["id"] for item in all_items if item["kind"] == "generated")


def test_legacy_and_generated_timezones_are_explicit(monkeypatch):
    monkeypatch.setenv("RESUME_LEGACY_TIMEZONE", "Asia/Shanghai")
    local, local_sort = _api_time(datetime(2026, 9, 27, 12, 0), legacy=True)
    generated, generated_sort = _api_time(datetime(2026, 9, 27, 4, 0))

    assert local.endswith("+00:00")
    assert generated.endswith("+00:00")
    assert local_sort == generated_sort
    assert _api_time(datetime(2026, 9, 27, 4, 0, tzinfo=timezone.utc))[0] == generated


def test_file_asset_accepts_png_contract():
    value = {"key": "71/" + "a" * 32 + ".png", "sha256": "b" * 64,
        "size_bytes": 12, "media_type": "image/png"}
    assert FileAsset.model_validate(value).media_type == "image/png"


def test_copy_reuses_png_without_sharing_mutable_metadata():
    source = SimpleNamespace(source_sha256="a" * 64,
        asset={"key": "71/" + "b" * 32 + ".png", "sha256": "c" * 64,
            "size_bytes": 5, "media_type": "image/png"},
        status="READY", attempt_count=1, error_code=None)
    target = SimpleNamespace()

    copy_thumbnail_state(source, target)
    source.asset["size_bytes"] = 99

    assert target.asset["size_bytes"] == 5
    target.asset = None
    assert source.asset is not None


def test_thumbnail_cleanup_releases_expired_copy_reference_in_stages():
    shared = {"key": "71/" + "b" * 32 + ".png", "sha256": "c" * 64,
        "size_bytes": 5, "media_type": "image/png"}
    first = SimpleNamespace(source_kind="generated", source_id="first", asset=shared)
    second = SimpleNamespace(source_kind="generated", source_id="second", asset=shared)

    candidates, protected = thumbnail_cleanup_plan([first], [first, second])
    assert set(candidates) == {shared["key"]}
    assert protected == {shared["key"]}

    first.asset = None  # The first expired document releases only its own reference.
    candidates, protected = thumbnail_cleanup_plan([second], [second])
    assert set(candidates) == {shared["key"]}
    assert not protected


@pytest.mark.asyncio
async def test_thumbnail_worker_failure_isolated_from_generation_cycle(monkeypatch):
    from app.services import resume_worker

    async def failure(*args, **kwargs):
        raise RuntimeError("thumbnail store unavailable")
    monkeypatch.setattr(resume_worker, "run_thumbnail_once", failure)

    assert await resume_worker._thumbnail_slot(object(), object()) is False


def _make_test_pdf():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    pdf.drawString(40, 400, "first page")
    pdf.showPage()
    pdf.drawString(40, 400, "second page")
    pdf.save()
    return buffer.getvalue()


def test_pdf_renderer_creates_bounded_png():
    source = _make_test_pdf()
    class Capture:
        data = None
        def send_bytes(self, data):
            self.data = data
        def close(self):
            pass
    pipe = Capture()
    resume_thumbnails._render_child(pipe, source)
    png = pipe.data

    from PIL import Image
    with Image.open(BytesIO(png)) as image:
        assert image.format == "PNG"
        assert image.width * image.height <= MAX_PIXELS
        assert image.width <= 1200 and image.height <= 1200



def test_hard_timeout_stops_owned_child_or_reports_sandbox_block(monkeypatch):
    class Child:
        pid = 12345
        name = "resume-thumbnail-render"
        alive = True
        def join(self, timeout=None):
            pass
        def is_alive(self):
            return self.alive
        def terminate(self):
            self.alive = False
        def kill(self):
            self.alive = False

    child = Child()
    monkeypatch.setattr(resume_thumbnails, "process_identity", lambda pid: "same-process")
    resume_thumbnails._stop_owned_process(child, "same-process")
    assert not child.is_alive()

    monkeypatch.setattr(resume_thumbnails, "process_identity", lambda pid: "different-process")
    child.alive = True
    with pytest.raises(RuntimeError, match="identity_unconfirmed"):
        resume_thumbnails._stop_owned_process(child, "same-process")
    assert child.is_alive()


def test_renderer_timeout_leaves_no_child_when_process_creation_is_available():
    try:
        render = resume_thumbnails.render_first_page(_make_test_pdf(), timeout=0.001)
    except PermissionError as error:
        if getattr(error, "winerror", None) == 5:
            pytest.skip("Windows sandbox denies the renderer's private named pipe")
        raise
    except TimeoutError:
        pass
    else:
        assert render  # Some hosts may start the bounded renderer before the timeout.
    assert not any(child.name == "resume-thumbnail-render" and child.is_alive()
        for child in multiprocessing.active_children())


@pytest.mark.asyncio
async def test_upload_survives_thumbnail_registration_commit_failure(monkeypatch):
    from app.api import resume_routes

    class Output:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *exc):
            return False
        async def write(self, data):
            self.data = data
    class Session:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
        def add(self, row):
            self.row = row
        async def flush(self):
            self.row.id = 42
        async def commit(self):
            self.commits += 1
            if self.commits > 1:
                raise RuntimeError("thumbnail registration commit failed")
        async def rollback(self):
            self.rollbacks += 1
    class Upload:
        filename = "resume.pdf"
        async def read(self):
            return b"test pdf bytes"

    removed = []
    monkeypatch.setattr(resume_routes, "UPLOAD_DIR", "virtual-upload")
    monkeypatch.setattr(resume_routes.aiofiles, "open", lambda *args, **kwargs: Output())
    monkeypatch.setattr(resume_routes, "extract_text_from_pdf", lambda path: "parsed")
    async def registration_failure(*args, **kwargs):
        return None
    monkeypatch.setattr(resume_routes, "register_thumbnail", registration_failure)
    monkeypatch.setattr(resume_routes.os, "remove", lambda path: removed.append(path))

    db = Session()
    result = await resume_routes.upload_resume(user_id=71, file=Upload(), db=db)

    assert result["data"]["id"] == 42
    assert db.commits == 2 and db.rollbacks == 1
    assert not removed


def test_thumbnail_read_hides_cross_owner_and_deleted_sources():
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.experience_dependencies import experience_session, private_store, trusted_owner
    from app.api.resume_library_routes import router
    from app.infrastructure.database import get_db_session

    class Result:
        def __init__(self, row):
            self.row = row
        def scalar_one_or_none(self):
            return self.row
    class FakeSession:
        def __init__(self, results):
            self.results = list(results)
        @asynccontextmanager
        async def begin(self):
            yield
        async def execute(self, statement):
            return Result(self.results.pop(0))
    class NeverReadStore:
        def read(self, *args):
            raise AssertionError("unavailable thumbnail must not reach storage")

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[trusted_owner] = lambda: 71
    app.dependency_overrides[experience_session] = lambda: FakeSession([None])
    app.dependency_overrides[get_db_session] = lambda: FakeSession([])
    app.dependency_overrides[private_store] = lambda: NeverReadStore()
    with TestClient(app) as client:
        assert client.get("/api/resume-library/thumbnail/generated/00000000-0000-0000-0000-000000000001").status_code == 404

        app.dependency_overrides[experience_session] = lambda: FakeSession([
            SimpleNamespace(asset={"key": "71/" + "a" * 32 + ".png"}), None,
        ])
        response = client.get("/api/resume-library/thumbnail/generated/00000000-0000-0000-0000-000000000001")
        assert response.status_code == 404
