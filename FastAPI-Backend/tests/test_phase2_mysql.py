"""Real MySQL + real ASGI/JWT. Only the external model is deterministic."""
import asyncio
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from sqlalchemy import select, func, event, text, create_engine, inspect
from sqlalchemy.exc import IntegrityError
from app.api.experience_app import create_experience_app
from app.api.experience_dependencies import experience_session, private_store as store_dependency, draft_extractor, legacy_pdf_root
from app.models.resume_storage_models import ExperienceItemModel as Experience, ResumeDocumentModel as Document, utcnow
from app.models.experience_import_models import ExperienceImportBatch as Batch, ExperienceImportDraft as Draft
from app.models.session_models import ResumeModel
from app.infrastructure.private_resume_assets import private_asset_transaction, cleanup_documents
from app.infrastructure.experience_import_cleanup import cleanup_imports
from app.services.experience_errors import ExperienceError
from test_phase2_boundaries import jwt_config, auth, text_pdf, image_pdf
from test_storage_boundaries import EXAMPLES
from conftest import migrate


class DeterministicAI:
    """External AI test double; PDF extraction remains real."""
    def __init__(self):
        self.calls = 0
        self.fail = False

    async def extract(self, pages):
        self.calls += 1
        if self.fail:
            raise ExperienceError("AI_UNAVAILABLE", "Test AI failure", 502)
        return {"items": [
            {"content":{"type":"SKILL", "title":"Backend", "category":"Backend", "skills":["Python"]},
             "page":1, "snippet":"Python"},
            {"content":{"type":"CERTIFICATE", "title":"Certificate"}, "page":1, "snippet":"Python"},
        ]}


@pytest.fixture
def api(sessions, private_store, jwt_config, tmp_path):
    app = create_experience_app()
    extractor = DeterministicAI()
    legacy = tmp_path / "data/resumes"
    legacy.mkdir(parents=True)
    async def db():
        async with sessions() as session:
            yield session
    app.dependency_overrides[experience_session] = db
    app.dependency_overrides[store_dependency] = lambda: private_store
    app.dependency_overrides[draft_extractor] = lambda: extractor
    app.dependency_overrides[legacy_pdf_root] = lambda: legacy
    # Never override authentication: all requests go through signed JWT checks.
    return app, extractor, legacy


def client(api):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=api[0]), base_url="http://test", headers=auth())


async def upload(http, data=None):
    response = await http.post("/api/experience-imports/upload", files={"file":("resume.pdf", data or text_pdf(), "application/pdf")})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e:e["type"])
async def test_asgi_five_categories_full_crud_and_archive(api, example):
    async with client(api) as http:
        response = await http.post("/api/experiences", json=example)
        assert response.status_code == 201, response.text
        created = response.json()
        id_ = created["id"]
        assert created["user_id"] == 71 and created["revision"] == 1
        assert (await http.get("/api/experiences/"+id_, headers=auth(72))).status_code == 404
        assert (await http.get("/api/experiences/"+id_)).json()["attributes"]
        replacement = {**example, "title":"Updated " + example["title"]}
        response = await http.put("/api/experiences/"+id_, json={"expected_revision":1, "item":replacement})
        assert response.status_code == 200, response.text
        assert response.json()["revision"] == 2
        assert (await http.put("/api/experiences/"+id_, json={"expected_revision":1,"item":replacement})).status_code == 409
        response = await http.patch(f"/api/experiences/{id_}/archive", json={"expected_revision":2,"is_archived":True})
        assert response.json()["revision"] == 3
        assert (await http.get("/api/experiences")).json()["total"] == 0
        assert (await http.get("/api/experiences?archive=archived")).json()["total"] == 1
        response = await http.patch(f"/api/experiences/{id_}/archive", json={"expected_revision":3,"is_archived":False})
        assert response.json()["revision"] == 4
        response = await http.patch(f"/api/experiences/{id_}/order", json={"expected_revision":4,"sort_order":7})
        assert response.json()["revision"] == 5 and response.json()["sort_order"] == 7
        assert (await http.delete(f"/api/experiences/{id_}?expected_revision=5", headers=auth(72))).status_code == 404
        assert (await http.delete(f"/api/experiences/{id_}?expected_revision=1")).status_code == 409
        assert (await http.delete(f"/api/experiences/{id_}?expected_revision=5")).status_code == 204
        assert (await http.get("/api/experiences/"+id_)).status_code == 404


async def test_database_pagination_combined_filters_and_literal_keyword(api):
    skill = next(e for e in EXAMPLES if e["type"] == "SKILL")
    async with client(api) as http:
        inputs = [
            {**skill,"title":"Literal 100%_Done","tags":[" Python ","SQL","Python"],"skills":["Kubernetes"]},
            {**skill,"title":"Backend other","tags":["Python"],"sort_order":1},
            {**skill,"title":"Archived","tags":["Python","SQL"],"is_archived":True},
        ]
        assert (await http.post("/api/experiences/batch", json={"items":inputs})).status_code == 201
        first = (await http.get("/api/experiences?page=1&page_size=1")).json()
        second = (await http.get("/api/experiences?page=2&page_size=1")).json()
        assert first["total"] == second["total"] == 2 and first["items"][0]["id"] != second["items"][0]["id"]
        assert (await http.get("/api/experiences?page=3&page_size=1")).json()["items"] == []
        assert (await http.get("/api/experiences?type=SKILL&tag=Python&tag=SQL&keyword=Kubernetes")).json()["total"] == 1
        assert (await http.get("/api/experiences?keyword=kubernetes")).json()["total"] == 0
        assert (await http.get("/api/experiences?tag=python")).json()["total"] == 0  # Exact JSON tag matching.
        assert (await http.get("/api/experiences?keyword=%25_")).json()["total"] == 1  # %/_ are literal.
        assert (await http.get("/api/experiences?archive=all&tag=SQL")).json()["total"] == 2
        assert (await http.get("/api/experiences?tag=SQL", headers=auth(72))).json()["total"] == 0
        for query in ("page=0", "page_size=101", "archive=invalid", "type=unknown", "tag=%20"):
            assert (await http.get("/api/experiences?"+query)).status_code == 422


async def test_asgi_rejects_forged_owner_provenance_and_type_changes(api):
    async with client(api) as http:
        for fields in ({"user_id":72}, {"id":str(uuid4())}, {"source_type":"PDF_IMPORT"},
                       {"source_locator":{"page":1}}, {"title":"  "}):
            assert (await http.post("/api/experiences", json={**EXAMPLES[0],**fields})).status_code == 422
        created = (await http.post("/api/experiences?user_id=72", json=EXAMPLES[0], headers={**auth(),"X-User-ID":"72"})).json()
        assert created["user_id"] == 71
        assert (await http.put("/api/experiences/"+created["id"],json={"expected_revision":1,"item":EXAMPLES[2]})).status_code == 422


async def test_bulk_validation_and_sort_conflict_roll_back(api, sessions):
    async with client(api) as http:
        response = await http.post("/api/experiences/batch", json={"items":[EXAMPLES[0],{"type":"WORK","title":"Incomplete"}]})
        assert response.status_code == 422
        assert response.json()["detail"]["details"][0]["field"][2] == 1
        assert (await http.get("/api/experiences")).json()["total"] == 0
        rows = (await http.post("/api/experiences/batch",json={"items":EXAMPLES[:2]})).json()
        ordered = sorted(rows,key=lambda r:r["id"])
        body = {"items":[{"id":ordered[0]["id"],"expected_revision":1,"sort_order":9},
                         {"id":ordered[1]["id"],"expected_revision":2,"sort_order":8}]}
        assert (await http.put("/api/experiences/order",json=body)).status_code == 409
        row = (await http.get("/api/experiences/"+ordered[0]["id"])).json()
        assert row["revision"] == 1 and row["sort_order"] == ordered[0]["sort_order"]
        body["items"][1]["expected_revision"] = 1
        result = await http.put("/api/experiences/order",json=body)
        assert result.status_code == 200 and all(r["revision"]==2 for r in result.json())
        assert (await http.put("/api/experiences/order",json=body,headers=auth(72))).status_code == 404


async def test_real_database_batch_insert_failure_is_atomic(api, sessions):
    async with client(api) as http:
        existing = (await http.post("/api/experiences",json=EXAMPLES[0])).json()
        def collide(mapper, connection, target):
            if target.title == "Force duplicate":
                target.id = existing["id"]
        event.listen(Experience,"before_insert",collide)
        try:
            response = await http.post("/api/experiences/batch",json={"items":[
                {**EXAMPLES[0],"title":"Must roll back"},{**EXAMPLES[0],"title":"Force duplicate"}]})
            assert response.status_code == 503
            assert "Duplicate" not in response.text and "INSERT" not in response.text
        finally:
            event.remove(Experience,"before_insert",collide)
        assert (await http.get("/api/experiences")).json()["total"] == 1


async def test_pdf_correction_confirmation_idempotency_owner_and_provenance(api, sessions, private_store):
    async with client(api) as http:
        batch = await upload(http)
        id_ = batch["id"]
        assert batch["status"] == "READY" and batch["items"][1]["needs_correction"]
        assert (await http.get("/api/experiences")).json()["total"] == 0
        assert (await http.get("/api/experience-imports/"+id_, headers=auth(72))).status_code == 404
        selection = {"items":[{"id":d["id"],"expected_revision":1} for d in batch["items"]]}
        assert (await http.post(f"/api/experience-imports/{id_}/confirm",json=selection)).status_code == 422
        assert (await http.get("/api/experiences")).json()["total"] == 0
        draft = batch["items"][1]
        edited = await http.put(f"/api/experience-imports/{id_}/items/{draft['id']}",json={
            "expected_revision":1,"content":{**draft["content"],"issue_date":"2024-05"}})
        assert edited.status_code == 200 and edited.json()["revision"] == 2 and not edited.json()["needs_correction"]
        assert (await http.post(f"/api/experience-imports/{id_}/confirm",json=selection)).status_code == 409
        selection["items"][1]["expected_revision"] = 2
        assert (await http.post(f"/api/experience-imports/{id_}/confirm",json=selection,headers=auth(72))).status_code == 404
        result = await http.post(f"/api/experience-imports/{id_}/confirm",json=selection)
        assert result.status_code == 200, result.text
        assert (await http.post(f"/api/experience-imports/{id_}/confirm",json=selection)).json() == result.json()
        assert (await http.post(f"/api/experience-imports/{id_}/confirm",json={"items":selection["items"][:1]})).status_code == 409
        rows = (await http.get("/api/experiences")).json()["items"]
        assert len(rows) == 2 and all(r["source_type"]=="PDF_IMPORT" for r in rows)
        for row in rows:
            assert row["source_locator"]["user_confirmed"] and row["source_locator"]["page"] == 1
        skill = next(r for r in rows if r["type"] == "SKILL")
        edited = await http.put("/api/experiences/"+skill["id"],json={"expected_revision":1,
            "item":{"type":"SKILL","title":"Edited","category":"Backend","skills":["Python"]}})
        assert edited.status_code == 200 and edited.json()["source_locator"] == skill["source_locator"]
        assert (await http.post(f"/api/experience-imports/{id_}/cancel")).status_code == 409
        assert (await http.put(f"/api/experience-imports/{id_}/items/{draft['id']}",json={"expected_revision":2,"content":draft["content"]})).status_code == 409
    async with sessions() as session:
        report = await cleanup_imports(session, private_store,71,dry_run=False)
        assert report["protected_keys"]
        async with session.begin():
            saved = await session.get(Batch,id_)
            assert saved.files_purged_at is None


async def test_confirm_selected_delete_unwanted_and_retry_after_experience_deleted(api):
    async with client(api) as http:
        batch = await upload(http)
        id_, keep, drop = batch["id"], batch["items"][0],batch["items"][1]
        assert (await http.delete(f"/api/experience-imports/{id_}/items/{drop['id']}?expected_revision=1",headers=auth(72))).status_code == 404
        assert (await http.delete(f"/api/experience-imports/{id_}/items/{drop['id']}?expected_revision=1")).status_code == 204
        selection = {"items":[{"id":keep["id"],"expected_revision":1}]}
        receipt = (await http.post(f"/api/experience-imports/{id_}/confirm",json=selection)).json()
        experience_id = receipt["items"][0]["experience_id"]
        assert (await http.delete(f"/api/experiences/{experience_id}?expected_revision=1")).status_code == 204
        assert (await http.post(f"/api/experience-imports/{id_}/confirm",json=selection)).json() == receipt
        assert (await http.get("/api/experiences")).json()["total"] == 0


async def test_concurrent_confirmation_creates_once(api):
    async with client(api) as http:
        batch = await upload(http)
        selection = {"items":[{"id":batch["items"][0]["id"],"expected_revision":1}]}
        results = await asyncio.gather(*[http.post(f"/api/experience-imports/{batch['id']}/confirm",json=selection) for _ in range(2)])
        assert all(r.status_code==200 for r in results), [r.text for r in results]
        assert results[0].json() == results[1].json()
        assert (await http.get("/api/experiences")).json()["total"] == 1


@pytest.mark.parametrize("failure", ["digest", "size", "missing"])
async def test_confirm_source_failure_preserves_ready_batch_and_allows_retry(
    api, sessions, private_store, failure
):
    async with client(api) as http:
        batch = await upload(http)
        async with sessions() as session, session.begin():
            stored = await session.get(Batch, batch["id"])
            asset = deepcopy(stored.source_asset)
        path = private_store.path(71, asset["key"])
        original = private_store.read(71, asset)
        if failure == "digest":
            path.write_bytes(b"x" + original[1:])
        elif failure == "size":
            path.write_bytes(original[:-1])
        else:
            path.unlink()  # Only this test upload's freshly generated source.
        selection = {"items": [{"id": batch["items"][0]["id"], "expected_revision": 1}]}
        response = await http.post(f"/api/experience-imports/{batch['id']}/confirm", json=selection)
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "PDF_SOURCE_UNAVAILABLE"
        assert (await http.get("/api/experiences")).json()["total"] == 0
        saved = (await http.get(f"/api/experience-imports/{batch['id']}")).json()
        assert saved["status"] == "READY" and saved["confirmation_result"] is None
        assert saved["items"] == batch["items"]
        # Restore only this fixture's bytes, then prove the unchanged draft can confirm.
        path.write_bytes(original)
        response = await http.post(f"/api/experience-imports/{batch['id']}/confirm", json=selection)
        assert response.status_code == 200, response.text
        assert (await http.get("/api/experiences")).json()["total"] == 1


async def test_confirmation_database_failure_rolls_back_whole_batch(api, sessions):
    async with client(api) as http:
        batch = await upload(http)
        second = batch["items"][1]
        await http.put(f"/api/experience-imports/{batch['id']}/items/{second['id']}",json={
            "expected_revision":1,"content":{**second["content"],"issue_date":"2024-05"}})
        selection = {"items":[{"id":batch["items"][0]["id"],"expected_revision":1},{"id":second["id"],"expected_revision":2}]}
        fixed = str(uuid4())
        def collide(mapper,connection,target): target.id = fixed
        event.listen(Experience,"before_insert",collide)
        try:
            response = await http.post(f"/api/experience-imports/{batch['id']}/confirm",json=selection)
            assert response.status_code == 503
        finally:
            event.remove(Experience,"before_insert",collide)
        assert (await http.get("/api/experiences")).json()["total"] == 0
        assert (await http.get("/api/experience-imports/"+batch["id"])).json()["status"] == "READY"
        assert (await http.post(f"/api/experience-imports/{batch['id']}/confirm",json=selection)).status_code == 200


async def test_failed_ai_persists_and_retry_then_cancel_and_cleanup(api,sessions,private_store):
    async with client(api) as http:
        api[1].fail = True
        response = await http.post("/api/experience-imports/upload",files={"file":("resume.pdf",text_pdf(),"application/pdf")})
        assert response.status_code == 502
        id_ = response.json()["detail"]["details"]["import_id"]
        assert (await http.get("/api/experience-imports/"+id_)).json()["status"] == "FAILED"
        api[1].fail = False
        assert (await http.post(f"/api/experience-imports/{id_}/retry")).json()["status"] == "READY"
        assert (await http.post(f"/api/experience-imports/{id_}/cancel")).json()["status"] == "CANCELLED"
    async with sessions() as session:
        report = await cleanup_imports(session,private_store,71)
        assert report["removable_keys"] and all(private_store.path(71,key).exists() for key in report["removable_keys"])
        await cleanup_imports(session,private_store,71,dry_run=False)
        assert all(not private_store.path(71,key).exists() for key in report["removable_keys"])


async def test_expiry_interrupted_processing_and_cross_batch_draft(api,sessions):
    async with client(api) as http:
        one,two = await upload(http),await upload(http)
        assert (await http.put(f"/api/experience-imports/{one['id']}/items/{two['items'][0]['id']}",json={
            "expected_revision":1,"content":two["items"][0]["content"]})).status_code == 404
        async with sessions() as session,session.begin():
            row=await session.get(Batch,one["id"])
            row.created_at=utcnow()-timedelta(days=8)
            row.expires_at=utcnow()-timedelta(days=1)
            row=await session.get(Batch,two["id"])
            row.status="PROCESSING"
            row.updated_at=utcnow()-timedelta(minutes=6)
            await session.execute(Draft.__table__.delete().where(Draft.batch_id==two["id"]))
        assert (await http.get("/api/experience-imports/"+one["id"])).json()["status"]=="EXPIRED"
        selection={"items":[{"id":one["items"][0]["id"],"expected_revision":1}]}
        assert (await http.post(f"/api/experience-imports/{one['id']}/confirm",json=selection)).status_code==409
        assert (await http.get("/api/experience-imports/"+two["id"])).json()["error"]["code"]=="PROCESSING_INTERRUPTED"
        assert (await http.post(f"/api/experience-imports/{two['id']}/retry")).status_code==200


async def test_existing_pdf_owner_and_legacy_delete_fk_protection(api,sessions):
    path=api[2]/"existing.pdf"
    path.write_bytes(text_pdf())
    async with sessions() as session,session.begin():
        record=await session.get(ResumeModel,1)
        record.local_path=str(path)
    async with client(api) as http:
        assert (await http.post("/api/experience-imports/existing",json={"source_resume_id":1},headers=auth(72))).status_code==404
        response=await http.post("/api/experience-imports/existing",json={"source_resume_id":1})
        assert response.status_code==201,response.text
        batch=response.json()
        assert batch["source_resume_id"]==1
    async with sessions() as session:
        from app.infrastructure.legacy_resume_deletion import delete_legacy_resume,LegacyResumeInUse
        with pytest.raises(LegacyResumeInUse):
            await delete_legacy_resume(session,1,71,"sentinel.pdf",pending_root=api[2].parent/"pending")
        assert path.exists()


async def test_upload_image_returns_explainable_failed_batch(api):
    async with client(api) as http:
        response=await http.post("/api/experience-imports/upload",files={"file":("image.pdf",image_pdf(),"application/pdf")})
        assert response.status_code==422 and response.json()["detail"]["code"]=="PDF_OCR_UNSUPPORTED"
        id_=response.json()["detail"]["details"]["import_id"]
        assert (await http.get("/api/experience-imports/"+id_)).json()["status"]=="FAILED"
        assert api[1].calls==0


def test_incremental_migration_preserves_p1_and_legacy(mysql_schema):
    engine=create_engine(mysql_schema.set(drivername="mysql+pymysql"),echo=False)
    try:
        migrate(mysql_schema,"downgrade","phase1_storage_002")
        assert "experience_items" in inspect(engine).get_table_names()
        assert "experience_import_batches" not in inspect(engine).get_table_names()
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO experience_items (id,user_id,type,title,tags,attributes,is_archived,sort_order,revision,source_type,source_locator,created_at,updated_at) VALUES ('fixture',71,'SKILL','Preserve',JSON_ARRAY(),JSON_OBJECT(),0,0,1,'MANUAL',JSON_OBJECT(),NOW(),NOW())"))
        migrate(mysql_schema)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT title FROM experience_items WHERE id='fixture'"))=="Preserve"
            assert connection.scalar(text("SELECT content_text FROM resumes WHERE id=1"))=="original"
            assert connection.scalar(text("SELECT version_num FROM resume_phase1_alembic_version"))=="phase2_experience_001"
    finally:
        engine.dispose()


async def test_active_draft_protects_document_asset_from_p1_cleanup(sessions,private_store):
    batch_id,document_id=str(uuid4()),str(uuid4())
    async with sessions() as session:
        async with private_asset_transaction(session,private_store,71) as files:
            asset=files.write(text_pdf(),"pdf")
            now=utcnow()
            session.add(Document(id=document_id,user_id=71,name="Fixture",format="markdown",
                snapshot={},markdown_content="# Fixture",pdf_asset=asset.model_dump(),
                created_at=now,updated_at=now,deleted_at=now,purge_after=now))
            session.add(Batch(id=batch_id,user_id=71,source_asset=asset.model_dump(),pages=[],status="READY",
                created_at=now,updated_at=now,expires_at=now+timedelta(days=7)))
        report=await cleanup_documents(session,private_store,71,dry_run=False)
        assert asset.key in report["protected_keys"] and private_store.path(71,asset.key).exists()


async def test_experience_edit_delete_preserve_history_snapshot(api,sessions):
    async with client(api) as http:
        created=(await http.post("/api/experiences",json=EXAMPLES[0])).json()
        document_id=str(uuid4())
        async with sessions() as session,session.begin():
            now=utcnow()
            session.add(Document(id=document_id,user_id=71,name="Snapshot",format="markdown",
                snapshot={"experience_snapshot":[created]},markdown_content="# Fixture",created_at=now,updated_at=now))
        edited=await http.put("/api/experiences/"+created["id"],json={"expected_revision":1,
            "item":{**EXAMPLES[0],"title":"New title"}})
        assert edited.status_code==200
        assert (await http.delete(f"/api/experiences/{created['id']}?expected_revision=2")).status_code==204
        async with sessions() as session,session.begin():
            assert (await session.get(Document,document_id)).snapshot == {"experience_snapshot":[created]}


async def test_import_cleanup_failure_keeps_marker_and_retry_handles_missing_file(api,sessions,private_store,monkeypatch):
    async with client(api) as http:
        one,two=await upload(http),await upload(http)
        await http.post(f"/api/experience-imports/{one['id']}/cancel")
        await http.post(f"/api/experience-imports/{two['id']}/cancel")
    calls=0
    original=private_store.remove
    def fail_second(owner,asset):
        nonlocal calls
        calls+=1
        if calls==2: raise OSError("test failure")
        return original(owner,asset)
    monkeypatch.setattr(private_store,"remove",fail_second)
    async with sessions() as session:
        with pytest.raises(OSError): await cleanup_imports(session,private_store,71,dry_run=False)
        async with session.begin():
            assert (await session.get(Batch,one["id"])).files_purged_at is None
            assert (await session.get(Batch,two["id"])).files_purged_at is None
        monkeypatch.setattr(private_store,"remove",original)
        await cleanup_imports(session,private_store,71,dry_run=False)
        async with session.begin():
            assert (await session.get(Batch,one["id"])).files_purged_at
            assert (await session.get(Batch,two["id"])).files_purged_at
