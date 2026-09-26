"""Versioned template protocol, rendering and historical snapshot checks."""

import os
import shutil
import subprocess
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.infrastructure.resume_template_store import BUILTIN_ROOT, read_bundle
from app.models.resume_template_contracts import (
    FIXED_SECTIONS,
    TemplateCompatibilityRequest,
    TemplatePreviewRequest,
)
from app.services.resume_template_service import compatibility, render_snapshot, validate_snapshot


@pytest.fixture(params=["billryan-classic-v1.1.0", "modern-twocol-v1.1.0"])
def bundle(request):
    return read_bundle(BUILTIN_ROOT / request.param)


def sample():
    return TemplatePreviewRequest.model_validate({
        "data": {
            "basic_info": {"name": "Ada & Bob", "email": "ada_100%#@example.com", "title": "R&D"},
            "education": [{"school": "University_1", "major": "C++"}],
            "skills": [{"category": "Backend", "items": "Python & SQL"}],
            "work": [{"company": "A&B", "bullets": [r"Shipped 50% \value"]}],
            "projects": [{"title": "Project#1", "bullets": ["More_value"]}],
            "certificates": [{"title": "Cert~1"}],
            "competitions": [{"title": "Award^1"}],
        },
    })


def test_builtins_validate_and_render_all_modules(bundle):
    report = validate_snapshot(bundle)
    assert report.valid, report.issues
    assert set(report.referenced_roots) == {*FIXED_SECTIONS, "options"}
    result = render_snapshot(bundle, sample())
    assert result.version == "1.1.0" and result.source_sha256
    for escaped in (r"Ada \& Bob", r"ada\_100\%\#@example.com", r"Python \& SQL", r"Shipped 50\% \textbackslash{}value", r"Project\#1", r"Cert\textasciitilde{}1", r"Award\textasciicircum{}1"):
        assert escaped in result.latex_source
    assert "{{" not in result.latex_source and "{%" not in result.latex_source
    assert compatibility(bundle, TemplateCompatibilityRequest(show_avatar=False)).compatible


def test_reject_unknown_module_unescaped_output_and_template_call(bundle):
    metadata = bundle["metadata_json"]
    source = bundle["main_source"]
    bad = validate_snapshot({**bundle, "main_source": source + "\n{{ basic_info.name }} {{ unknown }}"})
    assert {issue.code for issue in bad.issues} >= {"UNESCAPED_OUTPUT", "UNKNOWN_ROOT"}
    bad = validate_snapshot({**bundle, "main_source": source + "\n{% include 'external.tex' %}"})
    assert "FORBIDDEN_NODE" in {issue.code for issue in bad.issues}
    bad = validate_snapshot({**bundle, "main_source": source + "\n{{ basic_info.name.upper() | latex_escape }}"})
    assert "CALL" in {issue.code for issue in bad.issues}
    bad = validate_snapshot({**bundle, "main_source": source + "\n{{ basic_info.items | latex_escape }}"})
    assert "METHOD_ATTRIBUTE" in {issue.code for issue in bad.issues}
    bad = validate_snapshot({**bundle, "metadata_json": {**metadata, "placeholders": {"basic_info": {}}}})
    assert "PLACEHOLDERS" in {issue.code for issue in bad.issues}


def test_compatibility_explains_failures(bundle):
    request = TemplateCompatibilityRequest(language="en", show_avatar=True, target_pages=2)
    result = compatibility(bundle, request)
    assert not result.compatible
    assert {issue.code for issue in result.issues} >= {"LANGUAGE", "AVATAR"}


def test_historical_snapshot_renders_original_version_after_current_changes(bundle):
    frozen = deepcopy(bundle)
    current = deepcopy(bundle)
    current["version"] = "2.0.0"
    current["main_source"] = current["main_source"].replace("工作经历", "新版工作")
    current["content_digest"] = "different"
    original = render_snapshot(frozen, sample())
    assert render_snapshot(frozen, sample()) == original
    assert render_snapshot(current, sample()).source_sha256 != original.source_sha256
    assert original.version == "1.1.0" and original.content_digest == bundle["content_digest"]


def test_preview_rejects_unknown_fields_and_unsafe_avatar():
    with pytest.raises(ValidationError):
        TemplatePreviewRequest.model_validate({"data": {"basic_info": {"name": "Ada", "unknown": "x"}}})
    with pytest.raises(ValidationError):
        TemplatePreviewRequest.model_validate({"data": {"basic_info": {"name": "Ada", "avatar_path": "../secret"}}})


def test_legacy_template_bytes_are_preserved():
    historical_digests = {
        "billryan-classic": "fb50a54664aab77ff461960ff1e0404a20e885e42b9c5562c7addd6f56fdcd1a",
        "modern-twocol": "7b0af24c85de6126ace0a2160499dd313e5b3e2988e74939db78715449f1eb88",
    }
    for name, digest in historical_digests.items():
        old = read_bundle(BUILTIN_ROOT / name)
        new = read_bundle(BUILTIN_ROOT / f"{name}-v1.1.0")
        assert old["version"] == "1.0.0" and new["version"] == "1.1.0"
        assert old["content_digest"] == digest
        assert old["content_digest"] != new["content_digest"]
        assert not validate_snapshot(old).valid


def test_only_protocol_versions_are_eligible_for_enablement():
    reports = {}
    for directory in BUILTIN_ROOT.iterdir():
        if directory.is_dir():
            bundle = read_bundle(directory)
            reports[(bundle["id"], bundle["version"])] = validate_snapshot(bundle).valid
    assert {identity for identity, valid in reports.items() if valid} == {
        ("tpl-billryan-classic", "1.1.0"),
        ("tpl-modern-twocol", "1.1.0"),
        ("tpl-billryan-classic", "1.2.0"),
        ("tpl-modern-twocol", "1.2.0"),
    }


@pytest.mark.skipif(
    os.environ.get("RUN_XELATEX_INTEGRATION") != "1" or shutil.which("xelatex") is None,
    reason="Explicit RUN_XELATEX_INTEGRATION=1 required for local LaTeX compiler test",
)
def test_builtins_compile_real_pdf(bundle, tmp_path):
    source = render_snapshot(bundle, sample()).latex_source
    (tmp_path / "preview.tex").write_text(source, encoding="utf-8")
    result = subprocess.run(
        ["xelatex", "--disable-installer", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "preview.tex"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
        env={**os.environ, "MIKTEX_AUTO_INSTALL": "0"},
    )
    assert result.returncode == 0, (result.stdout + result.stderr).decode(errors="replace")[-2000:]
    assert (tmp_path / "preview.pdf").read_bytes().startswith(b"%PDF-")
