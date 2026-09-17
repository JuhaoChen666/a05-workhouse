"""Actual ASGI authentication and real PDF extraction; no database needed here."""
import io
import json
import time
from uuid import uuid4
import httpx
import jwt
import pytest
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
from fastapi import Depends
from app.api.experience_app import create_experience_app
from app.api.experience_dependencies import trusted_owner
from app.services.pdf_experience_extractor import extract_pdf, normalize_ai_drafts, draft_issues
from app.services.experience_errors import ExperienceError

# Test-only key, independent of application/Spring secrets.
TEST_KEY = "phase2-only-deterministic-jwt-fixture-key-0123456789"


def token(owner=71, **claims):
    now = int(time.time())
    return jwt.encode({"id": owner, "username": "fixture", "roleId": 1, "iat": now - 1,
                       "exp": now + 300, **claims}, TEST_KEY, algorithm="HS256")


def auth(owner=71):
    return {"Authorization": "Bearer " + token(owner)}


def text_pdf(text="Python backend project"):
    stream = io.BytesIO()
    document = canvas.Canvas(stream)
    document.drawString(50, 750, text)
    document.showPage()
    document.save()
    return stream.getvalue()


def image_pdf():
    stream = io.BytesIO()
    document = canvas.Canvas(stream)
    document.drawImage(ImageReader(Image.new("RGB", (10, 10), "white")), 50, 700, 100, 100)
    document.showPage()
    document.save()
    return stream.getvalue()


@pytest.fixture
def jwt_config(monkeypatch):
    monkeypatch.setenv("RESUME_JWT_SECRET", TEST_KEY)
    monkeypatch.setenv("RESUME_JWT_ALGORITHM", "HS256")


@pytest.mark.parametrize("mode", ["missing", "bad-scheme", "wrong-key", "expired", "tampered", "none",
                                  "bad-owner", "boolean-owner", "missing-claim", "future-iat", "algorithm",
                                  "bad-role", "bad-username"])
async def test_real_auth_rejects_invalid_tokens(jwt_config, mode):
    app = create_experience_app()
    # Probe uses production authentication dependency, without override.
    @app.get("/identity")
    def identity(owner=Depends(trusted_owner)):
        return {"owner": owner}
    headers = auth()
    now = int(time.time())
    if mode == "missing": headers = {}
    elif mode == "bad-scheme": headers = {"Authorization": "Basic anything"}
    elif mode == "wrong-key": headers = {"Authorization": "Bearer " + jwt.encode({"id": 71}, "x" * 64, algorithm="HS256")}
    elif mode == "expired": headers = {"Authorization": "Bearer " + token(exp=now - 5, iat=now - 20)}
    elif mode == "tampered": headers["Authorization"] = headers["Authorization"][:-5] + "AAAAA"
    elif mode == "none": headers = {"Authorization": "Bearer " + jwt.encode({"id": 71}, key="", algorithm="none")}
    elif mode == "bad-owner": headers = {"Authorization": "Bearer " + token(-1)}
    elif mode == "boolean-owner": headers = {"Authorization": "Bearer " + token(True)}
    elif mode == "missing-claim": headers = {"Authorization": "Bearer " + jwt.encode({"id": 71, "exp": now+30, "iat": now-1}, TEST_KEY, algorithm="HS256")}
    elif mode == "future-iat": headers = {"Authorization": "Bearer " + token(iat=now+100)}
    elif mode == "algorithm": headers = {"Authorization": "Bearer " + jwt.encode({"id":71, "exp":now+300, "iat":now-1}, TEST_KEY+"x"*30, algorithm="HS512")}
    elif mode == "bad-role": headers = {"Authorization": "Bearer " + token(roleId=True)}
    elif mode == "bad-username": headers = {"Authorization": "Bearer " + token(username=" ")}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/identity", headers=headers)).status_code == 401


async def test_real_auth_ignores_client_owner(jwt_config):
    app = create_experience_app()
    @app.get("/identity")
    def identity(owner=Depends(trusted_owner)):
        return {"owner": owner}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/identity?user_id=72", headers={**auth(71), "X-User-ID":"72"})
        assert response.json() == {"owner":71}


async def test_auth_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("RESUME_JWT_SECRET", raising=False)
    app = create_experience_app()
    @app.get("/identity")
    def identity(owner=Depends(trusted_owner)):
        return {"owner":owner}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/identity", headers=auth())).status_code == 503


def test_pdf_text_and_page_locator():
    pages = extract_pdf(text_pdf())
    assert pages == [{"page":1, "text":"Python backend project"}]


@pytest.mark.parametrize("kind,code", [("image", "PDF_OCR_UNSUPPORTED"), ("damaged", "PDF_DAMAGED"),
                                       ("encrypted", "PDF_ENCRYPTED"), ("empty", "PDF_SIZE")])
def test_real_pdf_failure_states(kind, code):
    data = image_pdf() if kind == "image" else b"%PDF-1.7 damaged"
    if kind == "encrypted":
        writer = PdfWriter()
        writer.append(PdfReader(io.BytesIO(text_pdf())))
        writer.encrypt("test-only-password")
        output = io.BytesIO()
        writer.write(output)
        data = output.getvalue()
    if kind == "empty": data = b""
    with pytest.raises(ExperienceError) as error:
        extract_pdf(data)
    assert error.value.code == code


@pytest.mark.parametrize("raw,code", [
    ("not JSON", "AI_INVALID_JSON"), ({"items":[]}, "AI_NO_DRAFTS"),
    ({"items":[{"content":{"type":"UNKNOWN"},"page":1,"snippet":"Python"}]}, "AI_UNKNOWN_CATEGORY"),
    ({"items":[{"content":{"type":"SKILL"},"page":2,"snippet":"Python"}]}, "AI_INVALID_SOURCE"),
    ({"items":[{"content":{"type":"SKILL"},"page":1,"snippet":"invented"}]}, "AI_INVALID_SOURCE"),
    ({"items":[{"content":{"type":"SKILL","user_id":72},"page":1,"snippet":"Python"}]}, "AI_INVALID_OUTPUT"),
])
def test_ai_output_invalid_has_explainable_error(raw, code):
    with pytest.raises(ExperienceError) as error:
        normalize_ai_drafts(raw, extract_pdf(text_pdf()))
    assert error.value.code == code


def test_incomplete_ai_draft_retains_uncertain_fields():
    output = normalize_ai_drafts({"items":[{"content":{"type":"CERTIFICATE","title":"Certificate"},
        "page":1,"snippet":"Python"}]}, extract_pdf(text_pdf()))
    assert "issue_date" not in output[0]["content"]
    assert output[0]["issues"]


def test_openapi_routes_are_registered_without_model_loading():
    paths = create_experience_app().openapi()["paths"]
    assert "/api/experiences/{item_id}" in paths
    assert "/api/experience-imports/{import_id}/confirm" in paths


async def test_actual_p2_routes_require_auth_before_storage():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_experience_app()),base_url="http://test") as client:
        assert (await client.get("/api/experiences")).status_code == 401
        assert (await client.post("/api/experience-imports/existing",json={"source_resume_id":1})).status_code == 401


async def test_runtime_never_uses_legacy_default_database(jwt_config,monkeypatch):
    monkeypatch.delenv("DATABASE_URL",raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_experience_app()),base_url="http://test") as client:
        response=await client.get("/api/experiences",headers=auth())
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "STORAGE_NOT_CONFIGURED"


async def test_p2_body_limit_rejects_declared_and_streamed_oversize():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_experience_app()),base_url="http://test") as client:
        response=await client.post("/api/experiences",content=b"{}",headers={"content-length":str(18*1024*1024)})
        assert response.status_code==413
        async def chunks():
            for _ in range(18):
                yield b"x" * (1024*1024)
        response=await client.post("/api/experiences",content=chunks(),headers={"content-type":"application/json"})
        assert response.status_code==413


@pytest.mark.parametrize("mode,code",[("success",None),("http-error","AI_UNAVAILABLE"),
    ("timeout","AI_TIMEOUT"),("large","AI_INVALID_OUTPUT"),("invalid-json","AI_INVALID_JSON"),
    ("unknown-category","AI_UNKNOWN_CATEGORY")])
async def test_actual_ai_http_adapter_with_deterministic_transport(monkeypatch,mode,code):
    from app.services.pdf_experience_extractor import PDFExperienceAI,run_extractor
    monkeypatch.setenv("DEEPSEEK_API_KEY","fixture-only-ai-key")
    monkeypatch.setenv("RESUME_AI_BASE_URL","https://ai.test")
    original=httpx.AsyncClient
    def respond(request):
        assert str(request.url)=="https://ai.test/chat/completions"
        assert request.headers["Authorization"]=="Bearer fixture-only-ai-key"
        body=json.loads(request.content)
        assert body["temperature"]==0 and body["response_format"]=={"type":"json_object"}
        if mode=="timeout": raise httpx.ReadTimeout("fixture timeout",request=request)
        if mode=="http-error": return httpx.Response(502,json={"error":"fixture"})
        if mode=="large": return httpx.Response(200,content=b"x"*(1024*1024+1))
        content={"items":[{"content":{"type":"SKILL","title":"Backend","category":"Backend","skills":["Python"]},
                           "page":1,"snippet":"Python"}]}
        if mode=="unknown-category": content["items"][0]["content"]["type"]="UNKNOWN"
        output="not JSON" if mode=="invalid-json" else json.dumps(content)
        return httpx.Response(200,json={"choices":[{"message":{"content":output}}]})
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kwargs:original(transport=httpx.MockTransport(respond),**kwargs))
    if code:
        with pytest.raises(ExperienceError) as error:
            await run_extractor(PDFExperienceAI(),extract_pdf(text_pdf()))
        assert error.value.code==code
    else:
        drafts=await run_extractor(PDFExperienceAI(),extract_pdf(text_pdf()))
        assert len(drafts)==1 and not drafts[0]["issues"]
