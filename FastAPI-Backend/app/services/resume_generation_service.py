"""Asynchronous JD-tailored resume planning, rendering and compilation."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
from typing import Any
from pydantic import BaseModel, Field, ValidationError

from app.infrastructure.resume_runtime import session_factory, asset_store
from app.infrastructure.mapper.resume_storage_mapper import ResumeStorageMapper
from app.infrastructure.private_resume_assets import private_asset_transaction
from app.models.resume_storage_models import ResumeGenerationJobModel as Job
from app.models.resume_latex_contracts import (
    AITailoredBulletTrace,
)
from app.models.resume_template_contracts import FIXED_SECTIONS, TemplatePreviewRequest, TemplateRenderData
from app.services.resume_template_service import TemplateProtocolError, render_snapshot


MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 12 * 1024 * 1024
COMPILE_SLOTS = asyncio.Semaphore(max(1, int(os.getenv("LATEX_COMPILE_CONCURRENCY", "2"))))

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#._-]{1,}|[\u4e00-\u9fff]{2,}")


class LatexCompileError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True, location: str | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.location = location


class StructuredAIPlan(BaseModel):
    model_config = {"extra": "forbid"}
    selected_item_ids: list[str] = Field(default_factory=list, max_length=16)
    module_order: list[str] = Field(default_factory=list, max_length=7)
    tailored_bullets: list["StructuredAIBullet"] = Field(default_factory=list, max_length=60)
    keyword_matches: dict[str, list[str]] = Field(default_factory=dict)
    trim_suggestions: list[str] = Field(default_factory=list, max_length=100)


class StructuredAIBullet(BaseModel):
    model_config = {"extra": "forbid"}
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


class AIUnavailable(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


async def request_structured_ai_plan(*, jd_text, experiences, fallback, language="zh"):
    import httpx
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise AIUnavailable("AI_NOT_CONFIGURED")
    prompt = "Only use supplied facts. Return JSON: selected_item_ids, module_order, tailored_bullets " \
        "(source_item_id,original_bullet,tailored_bullet,keywords_matched), keyword_matches, trim_suggestions. " \
        "Do not invent metrics, employers, dates or technologies. Requested language: " + language
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", os.environ.get("RESUME_AI_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + key}, json={"model": os.environ.get("RESUME_AI_MODEL", "deepseek-chat"),
                "response_format": {"type": "json_object"}, "temperature": 0, "max_tokens": 12000,
                "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(
                    {"jd": jd_text[:12000], "experiences": experiences}, ensure_ascii=False)}]}) as response:
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 512000:
                        raise AIUnavailable("AI_RESPONSE_TOO_LARGE")
                content = json.loads(body)["choices"][0]["message"]["content"]
            return StructuredAIPlan.model_validate(json.loads(content))
    except AIUnavailable:
        raise
    except ValidationError:
        raise AIUnavailable("AI_INVALID_OUTPUT") from None
    except Exception:
        raise AIUnavailable("AI_REQUEST_FAILED") from None


def validated_plan(ai, experiences):
    source = {str(item["id"]): item for item in experiences}
    ids = ai.selected_item_ids
    if len(ids) != len(set(ids)) or any(id_ not in source for id_ in ids):
        raise LatexCompileError("AI_SOURCE_VIOLATION: unknown or duplicate experience", retryable=False)
    if len(ai.module_order) != len(set(ai.module_order)) or any(s not in FIXED_SECTIONS for s in ai.module_order):
        raise LatexCompileError("AI_SOURCE_VIOLATION: invalid module order", retryable=False)
    preserved = 0
    seen = set()
    for bullet in ai.tailored_bullets:
        original = _attributes(source.get(bullet.source_item_id, {})).get("bullets", [])
        pair = (bullet.source_item_id, bullet.original_bullet)
        if bullet.source_item_id not in ids or bullet.original_bullet not in original or pair in seen:
            raise LatexCompileError("AI_SOURCE_VIOLATION: fabricated original bullet", retryable=False)
        seen.add(pair)
        # Numerical facts are rejectable; other semantic rewriting cannot be proven
        # safe automatically. Preserve original text rather than claiming verification.
        numbers = set(re.findall(r"\d+(?:[.,]\d+)*%?", bullet.tailored_bullet))
        if not numbers <= set(re.findall(r"\d+(?:[.,]\d+)*%?", bullet.original_bullet)):
            raise LatexCompileError("AI_FACT_VIOLATION: unsupported numerical fact", retryable=False)
        frozen_text = json.dumps(source[bullet.source_item_id], ensure_ascii=False).lower()
        # Conservative guards for explicit entity claims. These do not claim to
        # prove semantic equivalence; all remaining changes still require review.
        entities = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}(?:公司|集团|银行)", bullet.tailored_bullet)
        technologies = {"aws", "azure", "kubernetes", "docker", "react", "java", "python", "mysql", "redis", "tensorflow"}
        added_tech = technologies & set(re.findall(r"[a-z]+", bullet.tailored_bullet.lower()))
        if any(entity.lower() not in frozen_text for entity in entities) or any(
                tech not in set(re.findall(r"[a-z]+", frozen_text)) for tech in added_tech):
            raise LatexCompileError("AI_FACT_VIOLATION: unsupported entity claim", retryable=False)
        preserved += bullet.tailored_bullet != bullet.original_bullet
    order = ["basic_info"] + [s for s in ai.module_order if s != "basic_info"]
    order += [s for s in FIXED_SECTIONS if s not in order]
    return [copy.deepcopy(source[id_]) for id_ in ids], order, preserved


async def build_ai_plan(*, jd_text, experiences, personal_info, selected_item_ids,
                        mode="JD_AUTO_SELECT_AND_TAILOR", language="zh"):
    allowed = experiences if selected_item_ids is None else [item for item in experiences if str(item["id"]) in selected_item_ids]
    if selected_item_ids is not None and {str(item["id"]) for item in allowed} != set(selected_item_ids):
        raise LatexCompileError("SOURCE_UNAVAILABLE: selected experience missing", retryable=False)
    if mode == "MANUAL_ONLY":
        by_id = {str(item["id"]): item for item in allowed}
        chosen = allowed if selected_item_ids is None else [by_id[id_] for id_ in selected_item_ids]
        plan = {"selected_item_ids": [str(i["id"]) for i in chosen], "module_order": list(FIXED_SECTIONS),
                "recommendation_engine": "manual", "ai_status": "NOT_REQUESTED"}
    else:
        _, _, fallback = plan_resume(jd_text=jd_text, experiences=allowed,
            personal_info=personal_info, selected_item_ids=selected_item_ids)
        try:
            ai = await request_structured_ai_plan(jd_text=jd_text, experiences=allowed, fallback=fallback, language=language)
            chosen, order, preserved = validated_plan(ai, allowed)
            plan = {"selected_item_ids": ai.selected_item_ids, "module_order": order,
                "recommendation_engine": "deepseek_structured_json", "ai_status": "SUCCEEDED",
                "unverified_rewrites_preserved": preserved, "keyword_matches": ai.keyword_matches,
                "trim_suggestions": ai.trim_suggestions, "tailored_bullets": [row.model_dump(mode="json") for row in ai.tailored_bullets],
                "review_required": bool(preserved), "review_status": "PENDING" if preserved else "NOT_REQUIRED"}
            # Keyword claims are displayed only when they actually occur in the frozen source.
            plan["keyword_matches"] = {id_: [word for word in words if word.lower() in json.dumps(_attributes(next(item for item in chosen if str(item['id']) == id_)), ensure_ascii=False).lower()]
                for id_, words in ai.keyword_matches.items() if id_ in ai.selected_item_ids}
        except AIUnavailable as error:
            chosen, _, _ = rank_experiences(allowed, jd_text, selected_item_ids)
            plan = {**fallback, "ai_status": "DEGRADED", "ai_error_code": error.code}
    traces = [AITailoredBulletTrace(source_item_id=str(item["id"]), original_bullet=str(bullet),
        tailored_bullet=str(bullet), keywords_matched=[word for word in jd_keywords(jd_text) if word in str(bullet).lower()])
        for item in chosen for bullet in _attributes(item).get("bullets", [])]
    plan.update(language=language, fact_policy="original_text_only; unverified semantic rewrites are not applied",
                content_language_policy="localized headings; original facts remain in their source language")
    return build_render_data(chosen, personal_info), traces, plan


def review_version(plan):
    return hashlib.sha256(json.dumps({k: v for k, v in plan.items() if k != "version"},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf8")).hexdigest()


def apply_review(plan, decision, experiences, personal):
    """Apply only the exact, explicitly reviewed plan to a copy of frozen facts."""
    if plan.get("version") != review_version(plan) or decision.get("version") != plan["version"]:
        raise LatexCompileError("REVIEW_VERSION_CONFLICT", retryable=False)
    ai = StructuredAIPlan.model_validate({key: plan.get(key, [] if key != "keyword_matches" else {})
        for key in StructuredAIPlan.model_fields})
    chosen, order, _ = validated_plan(ai, experiences)
    accepted = decision["accepted_indices"]
    if len(accepted) != len(set(accepted)) or any(type(index) is not int or index < 0 or index >= len(ai.tailored_bullets) for index in accepted):
        raise LatexCompileError("REVIEW_DECISION_INVALID", retryable=False)
    by_id = {str(item["id"]): item for item in chosen}
    originals = {str(item["id"]): list(_attributes(item).get("bullets", [])) for item in chosen}
    replacements = {}
    for index in accepted:
        row = ai.tailored_bullets[index]
        item = by_id[row.source_item_id]
        attrs = _attributes(item)
        bullet_index = originals[row.source_item_id].index(row.original_bullet)
        attrs["bullets"][bullet_index] = row.tailored_bullet
        replacements[(row.source_item_id, row.original_bullet)] = row.tailored_bullet
    traces = [AITailoredBulletTrace(source_item_id=id_, original_bullet=bullet,
        tailored_bullet=replacements.get((id_, bullet), bullet),
        keywords_matched=[word for word in plan.get("keyword_matches", {}).get(id_, []) if word.lower() in bullet.lower()])
        for id_, bullets in originals.items() for bullet in bullets]
    metadata = {**plan, "module_order": order, "review_status": "CONFIRMED", "review_required": False,
        "accepted_rewrites": len(accepted), "unverified_rewrites_preserved": sum(row.tailored_bullet != row.original_bullet for index, row in enumerate(ai.tailored_bullets) if index not in accepted),
        "fact_policy": "source-bound proposals; semantic changes explicitly confirmed by user"}
    return build_render_data(chosen, personal), traces, metadata


async def compile_latex(source: str, resources: dict[str, Any] | None = None) -> bytes:
    from app.services.isolated_latex import SandboxError, compile_isolated
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise LatexCompileError("SOURCE_TOO_LARGE", retryable=False)
    async with COMPILE_SLOTS:
        try:
            return await compile_isolated(source, resources)
        except SandboxError as error:
            raise LatexCompileError(str(error), location=error.location) from None


def pdf_page_count(pdf: bytes, target_pages: int) -> int:
    from io import BytesIO
    from pypdf import PdfReader
    try:
        count = len(PdfReader(BytesIO(pdf), strict=True).pages)
    except Exception:
        raise LatexCompileError("PDF_OUTPUT_INVALID", retryable=False) from None
    if count < 1:
        raise LatexCompileError("PDF_OUTPUT_INVALID", retryable=False)
    if count > target_pages:
        raise LatexCompileError(f"PAGE_LIMIT_EXCEEDED: actual={count}, maximum={target_pages}; select fewer experiences or increase maximum pages", retryable=False)
    return count


async def _transition(job_id: str, token: str, status: str, stage: str, progress: int, *, owner_id: int, factory, metadata=None, **kwargs) -> None:
    async with factory() as session:
        async with session.begin():
            mapper = ResumeStorageMapper(session, owner_id)
            row = await mapper.owned(Job, job_id, lock=True)
            if row.run_token != token or row.status != "PROCESSING":
                raise LatexCompileError("WORKER_LEASE_LOST", retryable=False)
            if metadata is not None:
                row.result_metadata = copy.deepcopy(metadata)
            await mapper.update_job(job_id, status=status, stage=stage, progress=progress, **kwargs)


async def run_generation_job(job_id: str, owner_id: int, *, token: str, factory=None, store=None, compiler=None) -> None:
    factory = factory or session_factory()
    transition = lambda status, stage, progress, **kw: _transition(job_id, token, status, stage, progress, owner_id=owner_id, factory=factory, **kw)
    try:
        async with factory() as session:
            async with session.begin():
                job = await ResumeStorageMapper(session, owner_id).get_job(job_id)
                if job.status != "PROCESSING" or job.run_token != token:
                    return
                snapshot = {key: copy.deepcopy(getattr(job, key)) for key in
                    ("jd_snapshot", "experience_snapshot", "personal_info_snapshot", "template_snapshot", "options_snapshot", "review_plan", "review_decision")}
                language, target_pages = job.language, job.target_pages
        options = snapshot["options_snapshot"] or {}
        await transition("PROCESSING", "CONTENT_SELECTION", 5)
        if snapshot["review_plan"] is not None:
            if snapshot["review_decision"] is not None:
                data, traces, plan = apply_review(snapshot["review_plan"], snapshot["review_decision"], snapshot["experience_snapshot"], snapshot["personal_info_snapshot"])
            else:
                data, traces, plan = None, [], copy.deepcopy(snapshot["review_plan"])
        else:
            data, traces, plan = await build_ai_plan(
                jd_text=str((snapshot["jd_snapshot"] or {}).get("text") or ""),
                experiences=list(snapshot["experience_snapshot"] or []),
                personal_info=dict(snapshot["personal_info_snapshot"] or {}),
                selected_item_ids=options.get("selected_item_ids"),
                mode=options.get("ai_recommendation_mode", "JD_AUTO_SELECT_AND_TAILOR"), language=language)
        if plan.get("review_required"):
            plan["version"] = review_version(plan)
            async with factory() as session, session.begin():
                mapper = ResumeStorageMapper(session, owner_id)
                row = await mapper.owned(Job, job_id, lock=True)
                if row.run_token != token or row.status != "PROCESSING":
                    raise LatexCompileError("WORKER_LEASE_LOST", retryable=False)
                row.review_plan = copy.deepcopy(plan)
                row.result_metadata = copy.deepcopy(plan)
                await mapper.update_job(job_id, status="WAITING_REVIEW", stage="REVIEW_REQUIRED", progress=25)
                row.run_token = None
            return
        trace_values = [trace.model_dump(mode="json") for trace in traces]
        await transition("PROCESSING", "LATEX_RENDER", 35, traces=trace_values, metadata=plan)
        template = snapshot["template_snapshot"]
        capabilities = template.get("metadata_json", {}).get("generation_options", {})
        if language not in template.get("supported_languages", []) or (not capabilities.get("module_order") and plan["module_order"] != list(FIXED_SECTIONS)):
            raise LatexCompileError("TEMPLATE_OPTIONS_UNSUPPORTED: select a version 1.2 template", retryable=False)
        if not capabilities.get("module_order"):
            plan["template_option_policy"] = "legacy fixed section order; original version preserved"
        request = TemplatePreviewRequest(data=data, options={"show_avatar": bool(options.get("show_avatar", False)),
            "language": language, "module_order": plan["module_order"]})
        rendered = render_snapshot(template, request)
        await transition("PROCESSING", "ISOLATED_COMPILE", 60, traces=trace_values)
        pdf = await (compiler or compile_latex)(rendered.latex_source, template.get("resources"))
        count = pdf_page_count(pdf, target_pages)
        plan.update(actual_pages=count, maximum_pages=target_pages, page_policy="upper_bound")
        await transition("PROCESSING", "PERSIST_OUTPUTS", 90, traces=trace_values, metadata=plan)
        store = store or asset_store()
        async with factory() as session:
            async with private_asset_transaction(session, store, owner_id) as batch:
                mapper = ResumeStorageMapper(session, owner_id)
                row = await mapper.owned(Job, job_id, lock=True)
                if row.status != "PROCESSING" or row.run_token != token:
                    raise LatexCompileError("WORKER_LEASE_LOST", retryable=False)
                pdf_asset = batch.write(pdf, "pdf")
                latex_asset = batch.write(rendered.latex_source.encode("utf-8"), "tex")
                row.result_metadata = copy.deepcopy(plan)
                await mapper.update_job(job_id, status="COMPILED", stage="COMPLETED", progress=100, error=None, traces=trace_values)
                await mapper.create_document({"name": f"JD简历-{job_id[:8]}", "generation_job_id": job_id},
                    pdf_asset=pdf_asset.model_dump(mode="json"), latex_asset=latex_asset.model_dump(mode="json"))
    except (LatexCompileError, TemplateProtocolError) as error:
        message = str(error) if isinstance(error, LatexCompileError) else "TEMPLATE_VALIDATION_FAILED"
        code = message.split(":", 1)[0]
        details = {"location": error.location} if getattr(error, "location", None) else {}
        await transition("FAILED", "FAILED", 0, error={"code": code, "message": message,
            "retryable": getattr(error, "retryable", False), **details})
    except ValidationError:
        await transition("FAILED", "FAILED", 0, error={"code": "CONTENT_INVALID_OR_TOO_LARGE",
            "message": "请核对个人和教育信息，或减少经历数量后创建新任务", "retryable": False})
    except Exception:
        # Never expose SQL, credential URLs or private source content in API errors.
        await transition("FAILED", "FAILED", 0, error={"code": "GENERATION_INTERNAL_ERROR",
            "message": "生成失败，请检查服务配置并重试", "retryable": True})
