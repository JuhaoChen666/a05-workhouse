import base64
import hashlib
import json
from uuid import UUID
import pytest
from pydantic import ValidationError
from app.models.resume_storage_contracts import ExperienceInput, GenerationInput, owner_id
from app.infrastructure.resume_template_store import BUILTIN_ROOT, read_bundle
from app.infrastructure.private_resume_assets import PrivateAssets

EXAMPLES = [
    {"type": "CERTIFICATE", "title": "Certificate", "issue_date": "2025-01"},
    {"type": "COMPETITION_AWARD", "title": "Award", "award_level": "Gold", "award_date": "2025-02"},
    {"type": "PROJECT", "title": "Project", "role": "Developer", "bullets": ["Delivered"], "start_date": "2025-01", "end_date": "present"},
    {"type": "WORK", "title": "Company", "role": "Engineer", "bullets": ["Shipped"]},
    {"type": "SKILL", "title": "Backend", "category": "Backend", "skills": ["Python"]},
]


@pytest.mark.parametrize("data", EXAMPLES)
def test_five_discriminated_inputs(data):
    assert ExperienceInput.validate_python(data).model_dump(mode="json")["type"] == data["type"]


@pytest.mark.parametrize("field,value", [("id", "client"), ("user_id", 1), ("revision", 99), ("created_at", "2025-01-01"), ("updated_at", "2025-01-01")])
def test_managed_fields_rejected(field, value):
    with pytest.raises(ValidationError):
        ExperienceInput.validate_python({**EXAMPLES[2], field: value})


@pytest.mark.parametrize("change", [{"start_date": "2025-13"}, {"start_date": "present"}, {"end_date": "2024-01"}, {"type": "SKILL"}, {"sort_order": -1}, {"source_resume_id": 1}])
def test_input_invariants(change):
    with pytest.raises(ValidationError):
        ExperienceInput.validate_python({**EXAMPLES[2], **change})


@pytest.mark.parametrize("owner", [True, "71", 0, -1, 2147483648])
def test_trusted_identity_type(owner):
    with pytest.raises(ValueError):
        owner_id(owner)


@pytest.mark.parametrize("change", [{"jd_text": None}, {"job_id": "1"}, {"jd_source_type": "JOB_ID"}, {"language": "fr"}, {"selected_item_ids": ["x", "x"]}])
def test_generation_validation(change):
    with pytest.raises(ValidationError):
        GenerationInput.model_validate({"template_version": "1.0.0", "jd_text": "JD", **change})


@pytest.mark.parametrize("directory", ["billryan-classic", "modern-twocol", "altacv", "jakes-resume", "huajh-resume", "zheyuye-chinese"])
def test_six_master_bundles_exact_bytes(directory):
    bundle = read_bundle(BUILTIN_ROOT / directory)
    assert bundle["id"] == "tpl-" + directory
    for name, asset in bundle["resources"].items():
        original = (BUILTIN_ROOT / directory / name).read_bytes()
        assert base64.b64decode(asset["content"]) == original
        assert asset["sha256"] == hashlib.sha256(original).hexdigest()
    if directory in ("altacv", "billryan-classic"):
        assert any(name.endswith(".cls") for name in bundle["resources"])
    assert bundle["metadata_json"]["placeholders"]


@pytest.mark.parametrize("entry", ["../outside", "/absolute", "C:/file", "folder\\file", "missing"])
def test_template_escape_and_missing_resources(tmp_path, entry):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    metadata = json.loads((BUILTIN_ROOT / "modern-twocol/template.json").read_text(encoding="utf8"))
    metadata["entry_file"] = entry
    (bundle / "template.json").write_text(json.dumps(metadata), encoding="utf8")
    with pytest.raises(ValueError):
        read_bundle(bundle)


@pytest.mark.parametrize("key", ["../outside.pdf", "/file.pdf", "C:/file.pdf", "71/../../file.pdf", "71/x.pdf"])
def test_private_key_boundary(tmp_path, key):
    with pytest.raises(ValueError):
        PrivateAssets(tmp_path / "private").path(71, key)


def test_private_integrity_owner_and_collision(tmp_path, monkeypatch):
    from app.infrastructure import private_resume_assets as module
    monkeypatch.setattr(module, "uuid4", lambda: UUID(int=1))
    store = PrivateAssets(tmp_path / "private")
    asset = store.write(71, b"original", "pdf")
    with pytest.raises(FileExistsError):
        store.write(71, b"replacement", "pdf")
    assert store.read(71, asset) == b"original"
    with pytest.raises(PermissionError):
        store.read(72, asset)
    path = store.path(71, asset.key)
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        store.remove(71, asset)
    assert path.read_bytes() == b"tampered"


def test_links_and_size_limits(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    store = PrivateAssets(tmp_path / "private", max_bytes=2)
    with pytest.raises(ValueError):
        store.write(71, b"large", "pdf")
    try:
        (store.root / "71").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS forbids creating test symlink")
    with pytest.raises(ValueError):
        store.write(71, b"ok", "pdf")
    assert not list(outside.iterdir())


def test_private_root_excludes_actual_legacy_directories():
    from app.infrastructure.private_resume_assets import BACKEND_ROOT
    for root in (BACKEND_ROOT, BACKEND_ROOT.parent, BACKEND_ROOT / "data", BACKEND_ROOT / "data/resumes/subdir", BACKEND_ROOT / "data/optimizations"):
        with pytest.raises(ValueError):
            PrivateAssets(root)


def test_mysql_schema_json_and_scope():
    from alembic import command
    from alembic.config import Config
    from io import StringIO
    import os
    output = StringIO()
    config = Config(str(__import__('pathlib').Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output)
    old = os.environ.get("RESUME_DATABASE_URL")
    os.environ["RESUME_DATABASE_URL"] = "mysql+aiomysql://unused@localhost/unused"
    try:
        command.upgrade(config, "head", sql=True)
    finally:
        if old is None: os.environ.pop("RESUME_DATABASE_URL", None)
        else: os.environ["RESUME_DATABASE_URL"] = old
    sql = output.getvalue()
    assert sql.count("CREATE TABLE") == 7  # Version table + four P1 tables + two P2 tables.
    assert "CREATE TABLE experience_import_batches" in sql and "CREATE TABLE experience_import_drafts" in sql
    assert " JSON " in sql and "RESTRICT" in sql
    assert "ALTER TABLE resumes" not in sql and "DROP TABLE" not in sql
