"""Asynchronous JD-tailored resume planning, rendering and compilation."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper
from app.infrastructure.private_resume_assets import PrivateAssets, private_asset_transaction
from app.models.resume_latex_contracts import (
    AITailoredBulletTrace,
)
from app.models.resume_template_contracts import TemplatePreviewRequest, TemplateRenderData
from app.services.resume_template_service import TemplateProtocolError, render_snapshot


MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 12 * 1024 * 1024
COMPILE_TIMEOUT_SECONDS = int(os.getenv("LATEX_COMPILE_TIMEOUT_SECONDS", "30"))
COMPILE_SLOTS = asyncio.Semaphore(max(1, int(os.getenv("LATEX_COMPILE_CONCURRENCY", "2"))))

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#._-]{1,}|[\u4e00-\u9fff]{2,}")


class LatexCompileError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True, location: str | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.location = location


class StructuredAIPlan(BaseModel):
    selected_item_ids: list[str] = Field(default_factory=list, max_length=16)
    module_order: list[str] = Field(default_factory=list, max_length=7)
    tailored_bullets: list["StructuredAIBullet"] = Field(default_factory=list, max_length=60)
    keyword_matches: dict[str, list[str]] = Field(default_factory=dict)
    trim_suggestions: list[str] = Field(default_factory=list, max_length=100)


class StructuredAIBullet(BaseModel):
    source_item_id: str = Field(min_length=1, max_length=100)
    original_bullet: str = Field(min_length=1, max_length=4000)
    tailored_bullet: str = Field(min_length=1, max_length=4000)
    keywords_matched: list[str] = Field(default_factory=list, max_length=30)


StructuredAIPlan.model_rebuild()


def jd_keywords(text: str) -> list[str]:
    """Extract stable, case-insensitive keywords without asking an LLM to invent data."""
    seen: set[str] = set()
    result: list[str] = []
    for token in TOKEN_RE.findall(text or ""):
        value = token.strip().lower()
        if len(value) < 2 or value in {"the", "and", "with", "for", "from"} or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result[:80]


def _flatten(value: Any) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for child in value.values():
            result.extend(_flatten(child))
        return result
    if isinstance(value, list):
        result: list[str] = []
        for child in value:
            result.extend(_flatten(child))
        return result
    if value is None:
        return []
    return [str(value)]


def rank_experiences(
    items: list[dict[str, Any]],
    jd_text: str,
    selected_item_ids: list[str] | None,
    *,
    limit: int = 16,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[str]]:
    """Rank existing facts; never fabricate an experience or a metric."""
    keywords = jd_keywords(jd_text)
    selected = set(selected_item_ids or [])
    scored: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for index, item in enumerate(items):
        haystack = " ".join(_flatten(item)).lower()
        matched = [keyword for keyword in keywords if keyword in haystack][:12]
        score = len(matched) * 10 + (1000 if str(item.get("id")) in selected else 0)
        scored.append((score, index, item, matched))
    scored.sort(key=lambda value: (-value[0], value[1], str(value[2].get("id", ""))))
    chosen = scored[:limit]
    selected_ids = [str(item.get("id")) for _, _, item, _ in chosen]
    matches = {str(item.get("id")): matched for _, _, item, matched in chosen}
    return [item for _, _, item, _ in chosen], matches, selected_ids


def _attributes(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("attributes")
    return value if isinstance(value, dict) else {}


def _date_range(item: dict[str, Any]) -> str:
    start, end = item.get("start_date") or "", item.get("end_date") or ""
    if start and end:
        return f"{start} - {end}"
    return start or end


def build_render_data(
    items: list[dict[str, Any]],
    personal_info: dict[str, Any],
) -> TemplateRenderData:
    basic = {
        "name": str(personal_info.get("name") or personal_info.get("username") or "求职者"),
        "title": str(personal_info.get("title") or ""),
        "phone": str(personal_info.get("phone") or ""),
        "email": str(personal_info.get("email") or ""),
        "github": str(personal_info.get("github") or ""),
        "city": str(personal_info.get("city") or ""),
        "avatar_path": str(personal_info.get("avatar_path") or ""),
    }
    result: dict[str, Any] = {
        "basic_info": basic,
        "education": list(personal_info.get("education") or []),
        "skills": [],
        "work": [],
        "projects": [],
        "certificates": [],
        "competitions": [],
    }
    for item in items:
        attrs = _attributes(item)
        item_type = item.get("type")
        if item_type == "SKILL":
            skills = attrs.get("skills") or []
            result["skills"].append({
                "category": str(attrs.get("category") or item.get("title") or "技能"),
                "items": ", ".join(str(value) for value in skills),
            })
        elif item_type == "WORK":
            result["work"].append({
                "company": str(item.get("title") or ""),
                "role": str(attrs.get("role") or ""),
                "date_range": _date_range(item),
                "department": str(attrs.get("department") or ""),
                "city": str(attrs.get("city") or ""),
                "bullets": [str(value) for value in attrs.get("bullets") or []],
            })
        elif item_type == "PROJECT":
            result["projects"].append({
                "title": str(item.get("title") or ""),
                "role": str(attrs.get("role") or ""),
                "date_range": _date_range(item),
                "tech_stack": ", ".join(str(value) for value in attrs.get("tech_stack") or []),
                "project_url": str(attrs.get("project_url") or ""),
                "bullets": [str(value) for value in attrs.get("bullets") or []],
            })
        elif item_type == "CERTIFICATE":
            result["certificates"].append({
                "title": str(item.get("title") or ""),
                "authority": str(attrs.get("authority") or ""),
                "issue_date": str(attrs.get("issue_date") or ""),
                "certificate_no": str(attrs.get("certificate_no") or ""),
                "category": str(attrs.get("category") or ""),
                "description": str(attrs.get("description") or ""),
            })
        elif item_type == "COMPETITION_AWARD":
            result["competitions"].append({
                "title": str(item.get("title") or ""),
                "award_level": str(attrs.get("award_level") or ""),
                "award_date": str(attrs.get("award_date") or ""),
                "organization": str(attrs.get("organization") or ""),
                "rank": str(attrs.get("rank") or ""),
                "description": str(attrs.get("description") or ""),
            })
    return TemplateRenderData.model_validate(result)


def plan_resume(
    *,
    jd_text: str,
    experiences: list[dict[str, Any]],
    personal_info: dict[str, Any],
    selected_item_ids: list[str] | None,
) -> tuple[TemplateRenderData, list[AITailoredBulletTrace], dict[str, Any]]:
    chosen, matches, chosen_ids = rank_experiences(experiences, jd_text, selected_item_ids)
    traces: list[AITailoredBulletTrace] = []
    for item in chosen:
        attrs = _attributes(item)
        for bullet in attrs.get("bullets") or []:
            text = str(bullet).strip()
            if text:
                traces.append(AITailoredBulletTrace(
                    source_item_id=str(item.get("id")),
                    original_bullet=text,
                    tailored_bullet=text,
                    keywords_matched=matches.get(str(item.get("id")), []),
                ))
    data = build_render_data(chosen, personal_info)
    plan = {
        "selected_item_ids": chosen_ids,
        "module_order": ["basic_info", "education", "skills", "work", "projects", "certificates", "competitions"],
        "keyword_matches": matches,
        "trimmed_item_ids": [str(item.get("id")) for item in experiences if str(item.get("id")) not in chosen_ids],
        "recommendation_engine": "keyword_ranked_safe_tailoring",
    }
    return data, traces, plan


async def request_structured_ai_plan(
    *,
    jd_text: str,
    experiences: list[dict[str, Any]],
    fallback: dict[str, Any],
) -> StructuredAIPlan | None:
    """Use the configured model when available, with a strict JSON fallback path."""
    if not os.getenv("DEEPSEEK_API_KEY"):
        return None
    try:
        from app.llm.deepseek import DeepSeek_LLM

        compact = json.dumps(experiences, ensure_ascii=False, separators=(",", ":"))[:48000]
        prompt = f"""
你是简历定制规划器。只能使用输入经历中的事实，不得编造公司、时间、数字或技术成果。
请只输出 JSON，不要 Markdown。字段必须是：
selected_item_ids(string[]), module_order(string[]),
tailored_bullets(object[]，每项包含 source_item_id/original_bullet/tailored_bullet/keywords_matched),
keyword_matches(object)，trim_suggestions(string[])。
JD:
{jd_text[:12000]}
经历 JSON:
{compact}
候选确定性结果:
{json.dumps(fallback, ensure_ascii=False)}
"""
        response = await DeepSeek_LLM.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        return StructuredAIPlan.model_validate(json.loads(content))
    except Exception:
        return None


async def build_ai_plan(
    *,
    jd_text: str,
    experiences: list[dict[str, Any]],
    personal_info: dict[str, Any],
    selected_item_ids: list[str] | None,
) -> tuple[TemplateRenderData, list[AITailoredBulletTrace], dict[str, Any]]:
    data, traces, fallback = plan_resume(
        jd_text=jd_text,
        experiences=experiences,
        personal_info=personal_info,
        selected_item_ids=selected_item_ids,
    )
    ai = await request_structured_ai_plan(jd_text=jd_text, experiences=experiences, fallback=fallback)
    if ai is None:
        return data, traces, fallback
    source_by_id = {str(item.get("id")): item for item in experiences}
    valid_ids = [item_id for item_id in ai.selected_item_ids if item_id in source_by_id][:16]
    if selected_item_ids:
        valid_ids = [item_id for item_id in valid_ids if item_id in set(selected_item_ids)]
    chosen = [copy.deepcopy(source_by_id[item_id]) for item_id in valid_ids]
    valid_id_set = set(valid_ids)
    tailored = {
        (item.source_item_id, item.original_bullet): item
        for item in ai.tailored_bullets
        if item.source_item_id in valid_id_set
    }
    for item in chosen:
        attrs = item.get("attributes")
        if not isinstance(attrs, dict) or not attrs.get("bullets"):
            continue
        bullets = []
        for original in attrs["bullets"]:
            candidate = tailored.get((str(item.get("id")), str(original)))
            bullets.append(candidate.tailored_bullet if candidate else original)
        item["attributes"] = {**attrs, "bullets": bullets}
    data = build_render_data(chosen, personal_info)
    traces = [
        AITailoredBulletTrace(
            source_item_id=item.source_item_id,
            original_bullet=item.original_bullet,
            tailored_bullet=item.tailored_bullet,
            keywords_matched=item.keywords_matched,
        )
        for item in ai.tailored_bullets
        if item.source_item_id in valid_id_set
    ]
    ai_trimmed_ids = [
        item_id for item_id in ai.trim_suggestions
        if item_id in source_by_id and item_id not in valid_id_set
    ]
    plan = {
        **fallback,
        "selected_item_ids": valid_ids,
        "module_order": [
            section for section in ai.module_order
            if section in fallback["module_order"]
        ] or fallback["module_order"],
        "keyword_matches": ai.keyword_matches or fallback["keyword_matches"],
        "trimmed_item_ids": ai_trimmed_ids or fallback["trimmed_item_ids"],
        "trim_suggestions": ai.trim_suggestions,
        "recommendation_engine": "deepseek_structured_json",
    }
    return data, traces, plan


def _error_lines(output: str) -> tuple[str, str | None]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.startswith("!"):
            location = next((item for item in lines[max(0, index - 3):index] if item.startswith("l.")), None)
            return line, location
    return (lines[-1] if lines else "XeLaTeX failed", None)


async def compile_latex(source: str) -> bytes:
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise LatexCompileError("LaTeX source exceeds the size limit", retryable=False)
    engine = os.getenv("LATEX_ENGINE", "xelatex").strip() or "xelatex"
    if shutil.which(engine) is None:
        raise LatexCompileError(f"compile engine not found: {engine}", retryable=False)
    with tempfile.TemporaryDirectory(prefix="resume-latex-") as directory:
        root = Path(directory)
        tex_path = root / "resume.tex"
        tex_path.write_text(source, encoding="utf-8")
        environment = {
            "PATH": os.getenv("PATH", ""),
            "HOME": str(root),
            "TEXMFOUTPUT": str(root),
        }
        command = [
            engine,
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory",
            str(root),
            str(tex_path),
        ]
        preexec_fn = None
        if os.name == "posix":
            memory_mb = max(128, int(os.getenv("LATEX_MEMORY_LIMIT_MB", "512")))

            def limit_resources():
                import resource

                resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024 * 1024, memory_mb * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_PDF_BYTES, MAX_PDF_BYTES))

            preexec_fn = limit_resources
        async with COMPILE_SLOTS:
            process_kwargs = {
                "cwd": str(root),
                "env": environment,
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.STDOUT,
            }
            if preexec_fn is not None:
                process_kwargs["preexec_fn"] = preexec_fn
            process = await asyncio.create_subprocess_exec(
                *command,
                **process_kwargs,
            )
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(), COMPILE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise LatexCompileError("XeLaTeX compilation timed out", retryable=True) from None
        output = stdout.decode("utf-8", errors="replace")
        pdf_path = root / "resume.pdf"
        if process.returncode != 0 or not pdf_path.exists():
            message, location = _error_lines(output)
            raise LatexCompileError(message, retryable=True, location=location)
        if pdf_path.stat().st_size > MAX_PDF_BYTES:
            raise LatexCompileError("compiled PDF exceeds the size limit", retryable=False)
        return pdf_path.read_bytes()


async def _transition(job_id: str, status: str, stage: str, progress: int, **kwargs: Any) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await ResumeStorageMapper(session, kwargs.pop("owner_id")).update_job(
                job_id, status=status, stage=stage, progress=progress, **kwargs
            )


async def run_generation_job(job_id: str, owner_id: int) -> None:
    try:
        async with AsyncSessionLocal() as session:
            job = await ResumeStorageMapper(session, owner_id).get_job(job_id)
            snapshot = {
                "jd_snapshot": job.jd_snapshot,
                "experience_snapshot": job.experience_snapshot,
                "personal_info_snapshot": job.personal_info_snapshot,
                "template_snapshot": job.template_snapshot,
                "options_snapshot": job.options_snapshot,
            }
        await _transition(job_id, "PROCESSING", "AI_RECOMMENDATION", 5, owner_id=owner_id)
        options = snapshot["options_snapshot"] or {}
        data, traces, plan = await build_ai_plan(
            jd_text=str((snapshot["jd_snapshot"] or {}).get("text") or ""),
            experiences=list(snapshot["experience_snapshot"] or []),
            personal_info=dict(snapshot["personal_info_snapshot"] or {}),
            selected_item_ids=options.get("selected_item_ids"),
        )
        await _transition(job_id, "PROCESSING", "LATEX_RENDER", 35, owner_id=owner_id, traces=[trace.model_dump(mode="json") for trace in traces])
        request = TemplatePreviewRequest(
            data=data,
            options={"show_avatar": bool(options.get("show_avatar", False))},
        )
        try:
            rendered = render_snapshot(snapshot["template_snapshot"], request)
        except TemplateProtocolError as exc:
            raise LatexCompileError(
                "template validation failed: " + "; ".join(issue.message for issue in exc.report.issues),
                retryable=False,
            ) from exc
        await _transition(job_id, "PROCESSING", "XELATEX_COMPILE", 60, owner_id=owner_id, traces=[trace.model_dump(mode="json") for trace in traces])
        pdf = await compile_latex(rendered.latex_source)
        await _transition(job_id, "PROCESSING", "PERSIST_OUTPUTS", 90, owner_id=owner_id, traces=[trace.model_dump(mode="json") for trace in traces])
        async with AsyncSessionLocal() as session:
            root = os.getenv("RESUME_PRIVATE_ASSET_ROOT")
            store = PrivateAssets(root) if root else PrivateAssets()
            async with private_asset_transaction(session, store, owner_id) as batch:
                mapper = ResumeStorageMapper(session, owner_id)
                pdf_asset = batch.write(pdf, "pdf")
                latex_asset = batch.write(rendered.latex_source.encode("utf-8"), "tex")
                await mapper.update_job(
                    job_id,
                    status="COMPILED",
                    stage="COMPLETED",
                    progress=100,
                    error=None,
                    traces=[trace.model_dump(mode="json") for trace in traces],
                )
                await mapper.create_document(
                    {"name": f"JD简历-{job_id[:8]}", "generation_job_id": job_id},
                    pdf_asset=pdf_asset.model_dump(mode="json"),
                    latex_asset=latex_asset.model_dump(mode="json"),
                )
    except LatexCompileError as exc:
        error = {"code": "GENERATION_FAILED", "message": str(exc), "retryable": exc.retryable}
        if exc.location:
            error["location"] = exc.location
        try:
            await _transition(job_id, "FAILED", "FAILED", 0, owner_id=owner_id, error=error)
        except Exception:
            pass
    except Exception as exc:
        error = {"code": "GENERATION_FAILED", "message": str(exc), "retryable": True}
        try:
            await _transition(job_id, "FAILED", "FAILED", 0, owner_id=owner_id, error=error)
        except Exception:
            pass
