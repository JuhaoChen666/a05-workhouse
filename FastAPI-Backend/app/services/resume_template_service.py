"""Validation, compatibility checks and deterministic rendering for LaTeX templates."""

import hashlib
import re
from typing import Any

from jinja2 import StrictUndefined, meta, nodes
from jinja2.sandbox import ImmutableSandboxedEnvironment

from app.models.resume_template_contracts import (
    FIXED_SECTIONS,
    TEMPLATE_PROTOCOL_VERSION,
    TemplateCompatibilityRequest,
    TemplateCompatibilityResponse,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateRenderData,
    TemplateValidationIssue,
    TemplateValidationReport,
)


ALLOWED_ROOTS = frozenset((*FIXED_SECTIONS, "options"))
ALLOWED_FILTERS = frozenset(("latex_escape",))
FORBIDDEN_NODES = (nodes.Include, nodes.Import, nodes.FromImport, nodes.Extends, nodes.Macro, nodes.CallBlock)
ESCAPE_RE = re.compile(r"[\\{}$&#_%~^]")
ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


class TemplateProtocolError(ValueError):
    def __init__(self, report: TemplateValidationReport):
        super().__init__("template violates protocol")
        self.report = report


def latex_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return ESCAPE_RE.sub(lambda match: ESCAPES[match.group(0)], text)


class ResumeTemplateEnvironment(ImmutableSandboxedEnvironment):
    def getattr(self, obj: Any, attribute: str) -> Any:
        if isinstance(obj, dict) and attribute in obj:
            return obj[attribute]
        return super().getattr(obj, attribute)


def environment() -> ImmutableSandboxedEnvironment:
    env = ResumeTemplateEnvironment(
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["latex_escape"] = latex_escape
    return env



def _issue(code: str, message: str) -> TemplateValidationIssue:
    return TemplateValidationIssue(code=code, message=message)


def _output_is_escaped(expression: nodes.Node) -> bool:
    if isinstance(expression, nodes.Const):
        return True
    return isinstance(expression, nodes.Filter) and expression.name == "latex_escape"


def validate_template(metadata: dict[str, Any], source: str) -> TemplateValidationReport:
    issues: list[TemplateValidationIssue] = []
    sections = metadata.get("supported_sections")
    placeholders = metadata.get("placeholders")
    if metadata.get("protocol_version", TEMPLATE_PROTOCOL_VERSION) != TEMPLATE_PROTOCOL_VERSION:
        issues.append(_issue("PROTOCOL_VERSION", "unsupported template protocol version"))
    if not isinstance(sections, list) or set(sections) != set(FIXED_SECTIONS) or len(sections) != len(FIXED_SECTIONS):
        issues.append(_issue("SECTIONS", "supported_sections must contain each fixed module exactly once"))
    if not isinstance(placeholders, dict) or set(placeholders) != set(FIXED_SECTIONS):
        issues.append(_issue("PLACEHOLDERS", "placeholders must declare every fixed module"))
    elif not isinstance(placeholders["basic_info"], dict) or not all(
        isinstance(placeholders.get(section), list) and len(placeholders[section]) == 1
        and isinstance(placeholders[section][0], dict)
        for section in FIXED_SECTIONS[1:]
    ):
        issues.append(_issue("PLACEHOLDERS", "module fields must be object or one-item object array"))
    else:
        fields = {"basic_info": set(TemplateRenderData.model_fields["basic_info"].annotation.model_fields)}
        for section in FIXED_SECTIONS[1:]:
            entry_type = TemplateRenderData.model_fields[section].annotation.__args__[0]
            fields[section] = set(entry_type.model_fields)
        for section in FIXED_SECTIONS:
            declared = placeholders[section] if section == "basic_info" else placeholders[section][0]
            if set(declared) != fields[section] or any(
                value != (["string"] if field == "bullets" else "string")
                for field, value in declared.items()
            ):
                issues.append(_issue("PLACEHOLDERS", f"invalid placeholder field or type in {section}"))

    env = environment()
    try:
        ast = env.parse(source)
    except Exception as exc:
        return TemplateValidationReport(valid=False, issues=[*issues, _issue("SYNTAX", str(exc))])

    roots = sorted(meta.find_undeclared_variables(ast))
    unknown = set(roots) - ALLOWED_ROOTS
    if unknown:
        issues.append(_issue("UNKNOWN_ROOT", f"undeclared roots are not allowed: {sorted(unknown)}"))
    missing = set(FIXED_SECTIONS) - set(roots)
    if missing:
        issues.append(_issue("MISSING_MODULE", f"template must reference fixed modules: {sorted(missing)}"))
    if "options" not in roots:
        issues.append(_issue("MISSING_OPTIONS", "template must reference options.show_avatar"))
    for node in ast.find_all(FORBIDDEN_NODES):
        issues.append(_issue("FORBIDDEN_NODE", f"{type(node).__name__} is not allowed"))
    for node in ast.find_all(nodes.Filter):
        if node.name not in ALLOWED_FILTERS:
            issues.append(_issue("FILTER", f"filter is not allowed: {node.name}"))
    for output in ast.find_all(nodes.Output):
        for expression in output.nodes:
            if not isinstance(expression, nodes.TemplateData) and not _output_is_escaped(expression):
                issues.append(_issue("UNESCAPED_OUTPUT", f"line {expression.lineno}: dynamic output requires an escaping filter"))
    for node in ast.find_all(nodes.Call):
        issues.append(_issue("CALL", f"line {node.lineno}: method/function calls are not allowed"))
    for node in ast.find_all(nodes.Getattr):
        if node.attr in {"items", "keys", "values", "get", "update", "pop", "clear"}:
            issues.append(_issue("METHOD_ATTRIBUTE", f"line {node.lineno}: use bracket access for fields shadowing methods"))
    if not issues:
        try:
            sample = {
                "basic_info": {"name": "Sample"},
                "education": [{"school": "School"}],
                "skills": [{"category": "Skill", "items": "Content"}],
                "work": [{"company": "Company", "bullets": ["Result"]}],
                "projects": [{"title": "Project", "bullets": ["Result"]}],
                "certificates": [{"title": "Certificate"}],
                "competitions": [{"title": "Award"}],
            }
            context = TemplateRenderData.model_validate(sample).model_dump(mode="json")
            rendered = env.from_string(source).render(**context, options={"show_avatar": False})
            if "<built-in" in rendered or "<bound method" in rendered:
                issues.append(_issue("RENDER", "rendered method object instead of field content"))
        except Exception as exc:
            issues.append(_issue("RENDER", str(exc)))

    return TemplateValidationReport(
        valid=not issues,
        referenced_roots=roots,
        issues=issues,
    )


def validate_snapshot(snapshot: dict[str, Any]) -> TemplateValidationReport:
    return validate_template(snapshot["metadata_json"], snapshot["main_source"])


def compatibility(snapshot: dict[str, Any], request: TemplateCompatibilityRequest) -> TemplateCompatibilityResponse:
    metadata = snapshot["metadata_json"]
    issues: list[TemplateValidationIssue] = []
    if request.language not in snapshot["supported_languages"]:
        issues.append(_issue("LANGUAGE", f"language {request.language} is not supported"))
    if request.target_pages not in snapshot["supported_pages"]:
        issues.append(_issue("PAGES", f"target_pages {request.target_pages} is not supported"))
    if request.show_avatar and not metadata.get("supports_avatar", False):
        issues.append(_issue("AVATAR", "template does not support an avatar"))
    unsupported = set(request.sections) - set(snapshot["supported_sections"])
    if unsupported:
        issues.append(_issue("SECTIONS", f"sections are not supported: {sorted(unsupported)}"))
    report = validate_snapshot(snapshot)
    if not report.valid:
        issues.append(_issue("PROTOCOL", "template does not pass protocol validation"))
    return TemplateCompatibilityResponse(compatible=not issues, issues=issues)


def render_snapshot(snapshot: dict[str, Any], request: TemplatePreviewRequest) -> TemplatePreviewResponse:
    report = validate_snapshot(snapshot)
    if not report.valid:
        raise TemplateProtocolError(report)
    context = request.data.model_dump(mode="json")
    context["options"] = request.options.model_dump(mode="json")
    source = environment().from_string(snapshot["main_source"]).render(**context)
    return TemplatePreviewResponse(
        template_id=snapshot["id"],
        version=snapshot["version"],
        content_digest=snapshot["content_digest"],
        source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        latex_source=source,
    )
